"""Deterministic specification checks only: no SUT, runner or model invocation."""
import argparse
import copy
import datetime as dt
import json
import hashlib
from pathlib import Path
import re
import subprocess
import sys
import yaml
from gherkin.parser import Parser
from openapi_spec_validator import validate as validate_openapi
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[2]
CHECKS = ('openapi', 'hurl', 'gherkin', 'selectors', 'baseline', 'json-schemas', 'governance')

def load(name):
    return yaml.safe_load((ROOT / name).read_text())

def require(condition, message):
    if not condition:
        raise ValueError(message)

def feature():
    return Parser().parse((ROOT / 'features/auth/login.feature').read_text())['feature']

def check_openapi():
    doc = load('openapi.yml')
    validate_openapi(doc)
    expectations = load('api-expectations.yaml')
    require(set(doc['paths']) == {'/users', '/users/login', '/user'}, 'Unexpected API scope')
    scheme = doc['components']['securitySchemes']['TokenAuth']
    require(scheme['type'] == 'apiKey' and scheme['in'] == 'header' and scheme['name'] == 'Authorization', 'Token header contract changed')
    require(expectations['authentication']['scheme'] == 'Token', 'Bearer must not replace Token')
    require(doc['servers'][0]['url'].endswith('/api'), 'Server prefix must include /api')
    for entry in expectations['checks'].values():
        op = doc['paths'][entry['path']][entry['method'].lower()]
        require(str(entry['status']) in op['responses'], 'Expectation status missing in OpenAPI')
    require(doc['paths']['/user']['get']['security'] == [{'TokenAuth': []}], 'GET /user must require authentication')
    return {'operations': 3, 'expectations': len(expectations['checks'])}

def check_hurl():
    file = ROOT / 'api/auth.hurl'
    commands = []
    for args in (['hurlfmt', '--check', str(file)], ['hurlfmt', '--out', 'json', str(file)]):
        proc = subprocess.run(args, capture_output=True, text=True, timeout=20)
        commands.append({'command': args, 'exit_code': proc.returncode})
        require(proc.returncode == 0, proc.stderr or proc.stdout)
    parsed = json.loads(proc.stdout)
    entries = parsed['entries']
    require(len(entries) == 7, 'Expected independent unauthenticated, registration, authenticated-user, login, authenticated-user, invalid-login, unauthenticated entries')
    expected = [('GET', '/user', 401), ('POST', '/users', 201), ('GET', '/user', 200), ('POST', '/users/login', 200), ('GET', '/user', 200), ('POST', '/users/login', 422), ('GET', '/user', 401)]
    for item, (method, path, status) in zip(entries, expected):
        require(item['request']['method'] == method and item['request']['url'] == '{{base_url}}' + path and item['response']['status'] == status, 'Hurl API expectations drifted')
    for index in (0, 6):
        require(not any(h['name'].lower() == 'authorization' for h in entries[index]['request'].get('headers', [])), 'Unauthenticated check leaked Authorization')
    text = file.read_text()
    require('Authorization: Token {{registered_token}}' in text and 'Authorization: Token {{baseline_token}}' in text, 'Authenticated checks absent')
    require('registered_token: jsonpath "$.user.token" redact' in text and 'baseline_token: jsonpath "$.user.token" redact' in text, 'Tokens must be redacted')
    require('{{registration_email}}' in text and '{{registration_username}}' in text, 'Registration must use generated identities')
    return {'entries': len(entries), 'commands': commands, 'live_http_execution': 'NOT RUN'}

def check_gherkin():
    f = feature()
    require([x['name'] for x in f['tags']] == ['@SEED-1'], 'Preserve story tag')
    scenarios = [x['scenario'] for x in f['children'] if 'scenario' in x]
    require(len(scenarios) == 3, 'Exactly three scenarios required')
    require([s['tags'][0]['name'] for s in scenarios] == ['@AC-1', '@AC-2', '@AC-3'], 'AC coverage drift')
    for s in scenarios:
        require(len(s['tags']) == 1 and s['steps'] and not s.get('examples'), 'Unexpected scenario structure')
    ac3 = ' '.join(x['text'] for x in scenarios[2]['steps'])
    for phrase in ('login.error', 'no authentication state', 'protected settings page', 'access is denied', 'redirected to the login page', 'account.identity'):
        require(phrase in ac3, 'AC-3 lost a frozen requirement: ' + phrase)
    return {'story': 'SEED-1', 'scenarios': 3, 'mapping_status': load('api-expectations.yaml')['status']}

def check_selectors():
    selectors = load('selectors.json')['selectors']
    used = set(re.findall(r'"([a-z]+\.[a-z]+)"', (ROOT / 'features/auth/login.feature').read_text()))
    require(used == set(selectors), 'Missing or unused selector keys')
    for key, value in selectors.items():
        require(value['by'] in ('role', 'label', 'data-testid') and value['value'], 'Disallowed selector: ' + key)
        require(set(value) <= {'by', 'value', 'name'}, 'Unexpected selector field')
    return {'covered_selectors': len(used)}

def check_baseline():
    b = load('data/baseline.json')
    require(b['immutable'] is True and b['synthetic_only'] is True and len(b['users']) == 1, 'Baseline must be one immutable synthetic user')
    u = b['users'][0]
    require(u['username'] == 'qa_baseline' and u['email'] == 'qa.baseline@example.test', 'Baseline identity drifted')
    require(u['bio'] is None and u['image'] is None and len(u['password']) >= 8 and 'token' not in u, 'Invalid baseline shape')
    policy = b['registration_identity']
    require('<uuid4hex>' in policy['username_template'] and '<uuid4hex>' in policy['email_template'], 'Generated identities must be unique per attempt')
    require(policy['password'] != u['password'], 'Baseline and registration credentials must be separate')
    require(policy['email_template'].endswith('@example.test'), 'Synthetic reserved domain required')
    return {'immutable_users': 1, 'registration_uniqueness': 'fresh UUID v4 per attempt'}

def semantic_result(value):
    require(value['finished_at'] >= value['started_at'], 'Result timestamps out of order')
    statuses = [s['status'] for s in value['scenarios']]
    expected = next(s for s in ('error', 'failed', 'not_run', 'passed') if s in statuses)
    require(value['status'] == expected, 'Overall result status disagrees with scenarios')
    required = {'AC-1': {('POST', '/users', 201, False), ('GET', '/user', 200, True)}, 'AC-2': {('POST', '/users/login', 200, False), ('GET', '/user', 200, True)}, 'AC-3': {('POST', '/users/login', 422, False)}}
    for scenario in value['scenarios']:
        if scenario['status'] == 'passed':
            events = {(e['method'], e['path'], e['status'], e['authorization_present']) for e in scenario['observer']['events']}
            require(required[scenario['id']] <= events, 'Complete observation missing required API events')

def semantic_campaign(value):
    for slot in value['slots']:
        result = slot['result']
        if result is not None:
            require(result['slot_id'] == slot['slot_id'], 'Nested result slot mismatch')
            for key in ('issue_id', 'campaign_id', 'feature_ref'):
                require(result[key] == value[key], 'Campaign/result mismatch: ' + key)
            semantic_result(result)
    statuses = [s['result']['status'] if s['result'] else 'missing' for s in value['slots']]
    expected = 'error' if 'error' in statuses else 'failed' if 'failed' in statuses else 'incomplete' if any(s in ('missing', 'not_run') for s in statuses) else 'passed'
    require(value['status'] == expected, 'Campaign status disagrees with slot outcomes')

def check_schemas():
    results, campaigns = load('schemas/results.schema.json'), load('schemas/campaign.schema.json')
    for schema in (results, campaigns):
        Draft202012Validator.check_schema(schema)
    registry = Registry().with_resource('results.schema.json', Resource.from_contents(results))
    rv = Draft202012Validator(results, registry=registry, format_checker=FormatChecker())
    cv = Draft202012Validator(campaigns, registry=registry, format_checker=FormatChecker())
    slot_ids = results['properties']['slot_id']['enum']
    expected = {f'{sut}:{driver}' for sut in ('sut-python', 'sut-node') for driver in ('playwright', 'selenium', 'cypress')}
    require(set(slot_ids) == expected and len(slot_ids) == 6, 'Six matrix slots required')
    scenario = {'id': 'AC-1', 'status': 'passed', 'duration_ms': 1, 'observer': {'state': 'complete', 'events': [{'method': 'POST', 'path': '/users', 'status': 201, 'authorization_present': False}], 'detail': None}, 'artifacts': [{'path': 'evidence/probe.png', 'sha256': 'b' * 64, 'kind': 'screenshot'}], 'error': None}
    result = {'schema_version': '1.0', 'issue_id': 'SEED-1', 'campaign_id': 'fixture-campaign', 'execution_id': 'fixture-execution', 'feature_ref': 'a' * 40, 'tooling_ref': None, 'slot_id': slot_ids[0], 'sut_revision': 'c' * 40, 'runner_revision': 'd' * 40, 'started_at': '2026-01-01T00:00:00Z', 'finished_at': '2026-01-01T00:00:01Z', 'status': 'passed', 'scenarios': []}
    for id in ('AC-1', 'AC-2', 'AC-3'):
        item = copy.deepcopy(scenario); item['id'] = id
        if id != 'AC-1':
            item['observer']['events'][0].update(path='/users/login', status=200 if id == 'AC-2' else 422)
        if id != 'AC-3':
            item['observer']['events'].append({'method': 'GET', 'path': '/user', 'status': 200, 'authorization_present': True})
        result['scenarios'].append(item)
    rv.validate(result); semantic_result(result)
    campaign = {'schema_version': '1.0', 'issue_id': 'SEED-1', 'campaign_id': result['campaign_id'], 'feature_ref': result['feature_ref'], 'status': 'passed', 'slots': []}
    for slot in slot_ids:
        item = copy.deepcopy(result); item['slot_id'] = slot; item['execution_id'] = 'fixture-' + slot
        campaign['slots'].append({'slot_id': slot, 'state': 'complete', 'result': item})
    cv.validate(campaign); semantic_campaign(campaign)
    negatives = []
    def reject(validator, value, label, semantic=None):
        try:
            validator.validate(value)
            if semantic: semantic(value)
        except Exception:
            negatives.append(label); return
        raise ValueError('Invalid fixture incorrectly accepted: ' + label)
    for field, value in [('state', 'partial'), ('state', 'unavailable'), ('state', 'error'), ('state', 'invented')]:
        bad = copy.deepcopy(result); bad['scenarios'][0]['observer'][field] = value; reject(rv, bad, 'observer-' + value)
    for label, transform in [('missing-scenario', lambda v: v['scenarios'].pop()), ('duplicate-ac', lambda v: v['scenarios'][1].update(id='AC-1')), ('missing-artifacts', lambda v: v['scenarios'][0].update(artifacts=[])), ('unknown-field', lambda v: v.update(secret_token='forbidden')), ('nonmatching-status', lambda v: v.update(status='failed')), ('backwards-time', lambda v: v.update(finished_at='2025-01-01T00:00:00Z')), ('absolute-artifact', lambda v: v['scenarios'][0]['artifacts'][0].update(path='/tmp/probe')), ('traversal-artifact', lambda v: v['scenarios'][0]['artifacts'][0].update(path='../probe'))]:
        bad = copy.deepcopy(result); transform(bad); reject(rv, bad, label, semantic_result)
    for label, transform in [('missing-slot', lambda v: v['slots'].pop()), ('duplicate-slot', lambda v: v['slots'][1].update(slot_id=v['slots'][0]['slot_id'])), ('nested-slot-mismatch', lambda v: v['slots'][0]['result'].update(slot_id=slot_ids[1])), ('nested-campaign-mismatch', lambda v: v['slots'][0]['result'].update(campaign_id='other')), ('false-campaign-pass', lambda v: v['slots'][0].update(state='missing', result=None))]:
        bad = copy.deepcopy(campaign); transform(bad); reject(cv, bad, label, semantic_campaign)
    missing = copy.deepcopy(campaign); missing['status'] = 'incomplete'; missing['slots'][0].update(state='missing', result=None)
    cv.validate(missing); semantic_campaign(missing)
    failed = copy.deepcopy(result); failed['status'] = 'failed'; failed['scenarios'][0].update(status='failed', observer={'state': 'unavailable', 'events': [], 'detail': 'instrumentation unavailable'}, artifacts=[], error='No observation')
    rv.validate(failed); semantic_result(failed)
    return {'positive_fixtures': 4, 'negative_fixtures': len(negatives), 'rejected': negatives, 'fixtures_are_execution_evidence': False}

def check_governance():
    manifest = load('governance/manifest.json')
    for name, expected in manifest['generated_files'].items():
        for prefix in ('', 'governance/source/'):
            require(hashlib.sha256((ROOT / (prefix + name)).read_bytes()).hexdigest() == expected, 'Generated governance drift: ' + prefix + name)
    for name, expected in manifest['preserved_files'].items():
        require(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, 'Preserved governance changed: ' + name)
    require((ROOT / '.claude/skills/qa-contract-author/SKILL.md').read_bytes() == (ROOT / '.agents/skills/qa-contract-author/SKILL.md').read_bytes(), 'Mirrored contract skill drift')
    require(load('harness/location.json') == {'kind': 'repository', 'repository': 'qa-features'}, 'Adapter must be repository-local')
    return {'generated_files': len(manifest['generated_files']), 'preserved_files': len(manifest['preserved_files']), 'claude_live': 'NOT RUN (approved exception)'}

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--check', choices=(*CHECKS, 'all'), default='all')
    args = p.parse_args()
    methods = dict(zip(CHECKS, (check_openapi, check_hurl, check_gherkin, check_selectors, check_baseline, check_schemas, check_governance)))
    records = []
    for name in CHECKS if args.check == 'all' else [args.check]:
        try:
            records.append({'check': name, 'status': 'PASS', 'details': methods[name]()})
        except Exception as e:
            records.append({'check': name, 'status': 'FAIL', 'error': str(e)})
    print(json.dumps({'status': 'PASS' if all(r['status'] == 'PASS' for r in records) else 'FAIL', 'checks': records}, indent=2))
    return int(any(r['status'] != 'PASS' for r in records))

if __name__ == '__main__':
    raise SystemExit(main())
