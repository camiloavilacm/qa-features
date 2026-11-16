"""Run allowlisted checks and verify captured evidence, without authorizing/completing steps."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import uuid
from common import ROOT, state, validate, preflight, now, digest, source_digest, git_context, write, read, safe_relative, cli_error, audit, sign_evidence, verify_signature, config, location

def command(root, check_id):
    spec = root if location(root).get('repository') == 'qa-features' else root / 'qa-features'
    if check_id in config(root, 'steps')['steps']['1']['verification_checks']:
        return [sys.executable, str(spec / 'tools/validate/validate.py'), '--check', check_id]
    commands = {
        'adapters': [sys.executable, 'harness/scripts/validate_adapters.py'],
        'evals': [sys.executable, '-m', 'unittest', 'discover', '-s', 'harness/evals', '-p', 'test_*.py', '-v'],
        'codex-native': [sys.executable, 'harness/scripts/native_probe.py', 'codex'],
        'claude-native': [sys.executable, 'harness/scripts/native_probe.py', 'claude'],
        'claude-artifacts': [sys.executable, 'harness/scripts/validate_adapters.py'],
        'antigravity-native': [sys.executable, 'harness/scripts/native_probe.py', 'antigravity'],
        'native-cycle': [sys.executable, 'harness/scripts/native_acceptance.py'],
    }
    if check_id not in commands:
        raise ValueError('Check is not registered; no arbitrary command evidence')
    return commands[check_id]

def run(root, check_id):
    s = state(root)
    preflight(root, s['authorized_step'], s['owner']['provider'], s['owner']['id'])
    if s['authorized_step'] not in ('0.5', '1'):
        raise ValueError('Only Phase 0.5 and Step 1 checks are implemented')
    if check_id not in config(root, 'steps')['steps'][s['authorized_step']]['verification_checks']:
        raise ValueError('Check is outside the active step')
    args = command(root, check_id)
    started = now()
    before = source_digest(root)
    sign_evidence(root, {})  # Fail before executing if external recorder is unavailable.
    try:
        proc = subprocess.run(args, cwd=root, capture_output=True, timeout=300 if check_id == 'native-cycle' else 120)
        code, log = proc.returncode, proc.stdout + b'\nSTDERR:\n' + proc.stderr
    except subprocess.TimeoutExpired as e:
        code, log = None, (e.stdout or b'') + (e.stderr or b'') + b'\nTIMEOUT'
    # Native probes use exit 3 to indicate missing instrumentation or live evidence.
    status = 'NOT RUN' if code in (None, 3) else 'PASS' if code == 0 else 'FAIL'
    if before != source_digest(root):
        status = 'FAIL'
        log += b'\nSource changed during check'
    stem = 'harness/evidence/' + check_id + '-' + uuid.uuid4().hex
    (root / (stem + '.log')).write_bytes(log)
    evidence = {'version': 1, 'step': s['authorized_step'], 'provider': s['owner']['provider'], 'owner': s['owner']['id'], 'check_id': check_id, 'command': args, 'cwd': str(root), 'started_at': started, 'finished_at': now(), 'exit_code': code, 'status': status, 'log': stem + '.log', 'log_sha256': digest(log), 'source_sha256': before, 'git': git_context(root), 'instrumentation': 'subprocess-capture'}
    evidence['signature'] = sign_evidence(root, evidence)
    validate(root, 'evidence', evidence)
    write(root / (stem + '.json'), evidence)
    s['evidence'].append(stem + '.json')
    write(root / 'harness/state.json', s)
    return evidence

def validate_evidence(root, evidence):
    validate(root, 'evidence', evidence)
    verify_signature(root, evidence)
    if evidence['command'] != command(root, evidence['check_id']):
        raise ValueError('Evidence command differs from registered check')
    if evidence['instrumentation'] != 'subprocess-capture' or evidence['exit_code'] is None:
        raise ValueError('Check was not executed to completion')
    log = safe_relative(root, evidence['log'])
    if not evidence['log'].startswith('harness/evidence/') or digest(log.read_bytes()) != evidence['log_sha256']:
        raise ValueError('Log missing or modified')
    if evidence['source_sha256'] != source_digest(root):
        raise ValueError('Evidence is stale for current source')
    if evidence['cwd'] != str(root) or evidence['step'] != state(root)['authorized_step']:
        raise ValueError('Evidence belongs to a different workspace or step')
    return evidence['status']

def gate(root):
    s = state(root)
    preflight(root, s['authorized_step'], s['owner']['provider'], s['owner']['id'])
    if s['authorized_step'] not in ('0.5', '1'):
        raise ValueError('No product-step completion implementation')
    latest = {}
    for path in s['evidence']:
        e = read(safe_relative(root, path))
        if e['step'] == s['authorized_step']:
            latest[e['check_id']] = e
    required = config(root, 'steps')['steps'][s['authorized_step']]['verification_checks']
    failures = []
    if s['authorized_step'] == '1':
        spec = root if location(root).get('repository') == 'qa-features' else root / 'qa-features'
        for name in config(root, 'steps')['steps']['1']['required_outputs']:
            if not (spec / name).exists():
                failures.append('Missing required specification output: ' + name)
    for name in required:
        try:
            if name not in latest or validate_evidence(root, latest[name]) != 'PASS':
                failures.append(name + ': missing/non-PASS evidence')
        except Exception as e:
            failures.append(name + ': ' + str(e))
    baseline = safe_relative(root, s['baseline'])
    if not baseline.exists() or audit(root, read(baseline))['status'] != 'PASS':
        failures.append('Mandatory scope audit missing/failed')
    return failures

def main():
    p = argparse.ArgumentParser()
    p.add_argument('action', choices=['run', 'validate', 'gate'])
    p.add_argument('--check')
    a = p.parse_args()
    try:
        if a.action == 'run':
            result = run(ROOT, a.check)
            print(json.dumps(result, indent=2))
            return 0 if result['status'] == 'PASS' else 1
        if a.action == 'validate':
            s = state(ROOT)
            if not s['evidence']:
                raise ValueError('No evidence')
            latest = {}
            for path in s['evidence']:
                e = read(safe_relative(ROOT, path))
                if e['step'] == s['authorized_step']:
                    latest[e['check_id']] = e
            for e in latest.values():
                print(e['check_id'], validate_evidence(ROOT, e))
            return int(any(e['status'] != 'PASS' for e in latest.values()))
        failures = gate(ROOT)
        print(json.dumps({'status': 'FAIL' if failures else 'PASS', 'blockers': failures}, indent=2))
        return int(bool(failures))
    except Exception as e:
        return cli_error(e)

if __name__ == '__main__':
    raise SystemExit(main())
