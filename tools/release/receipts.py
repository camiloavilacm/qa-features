"""Execution-bound rollback evidence shared by its producer and acceptance validators."""
import re

def require(condition, message):
    if not condition:
        raise ValueError(message)

def identity(context):
    value = {key: context[key] for key in ('campaign_id', 'run_id', 'attempt', 'tooling_ref')}
    require(isinstance(value['run_id'], int) and value['run_id'] > 0, 'Invalid rollback run identity')
    require(type(value['attempt']) is int and value['attempt'] > 0, 'Invalid rollback attempt')
    require(value['campaign_id'].endswith('-' + str(value['run_id'])), 'Rollback campaign/run mismatch')
    require(re.fullmatch('[a-f0-9]{40}', value['tooling_ref']) is not None, 'Invalid rollback tooling revision')
    return value

def validate_rollback(record, sut, context, baseline, candidate, baseline_sha, candidate_sha):
    expected = identity(context)
    require(all(record.get(key) == value for key, value in expected.items()), 'Rollback receipt belongs to another execution')
    require(record.get('status') == 'PASS' and record.get('sut') == sut, 'Rollback did not pass for this SUT')
    require(record.get('baseline_manifest_sha256') == baseline_sha and record.get('candidate_manifest_sha256') == candidate_sha, 'Rollback manifests differ')
    phases = record.get('phases', [])
    require([p.get('phase') for p in phases] == ['baseline', 'candidate', 'rollback'], 'Rollback phases incomplete')
    images = [baseline['images'][sut], candidate['images'][sut], baseline['images'][sut]]
    for phase, image in zip(phases, images):
        require(phase.get('image_id') == image['config_id'] and phase.get('registry_digest') == image['registry_digest'], 'Rollback image provenance differs')
        require(all(phase.get(key) == 'PASS' for key in ('hurl_7_requests', 'unauthenticated_user_401', 'served_frontend_hashes')), 'Rollback phase checks did not pass')
    for field in ('runtime_config_sha256', 'baseline_row_sha256', 'database_container'):
        require(all(p.get(field) for p in phases) and len({p[field] for p in phases}) == 1, 'Rollback did not preserve ' + field)
    require(images[0]['config_id'] != images[1]['config_id'], 'Distinct rollback image artifacts required')
    return record

def require_upstream(outcomes):
    require(set(outcomes) == {'baseline', 'qa', 'rollback'} and all(v == 'success' for v in outcomes.values()), 'Upstream smoke jobs did not all succeed')
