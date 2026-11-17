"""Verify downloaded showcase evidence without Docker, model calls or recorder keys."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
ROOT = Path(__file__).resolve().parents[2]
CHECKS = ('image-digests', 'reproduction', '18-passes', 'rollback', 'failure-reporting')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True, help='Extracted initial/reproduction/failure directories under harness/evidence')
    args = parser.parse_args()
    base = args.evidence.resolve()
    if not base.is_relative_to(ROOT / 'harness/evidence'):
        parser.error('Extract the evidence under this checkout\'s harness/evidence directory')
    for label in ('initial', 'reproduction', 'failure'):
        if not (base / label / 'github-run.json').is_file():
            parser.error('Missing archived attempt: ' + label)
    with tempfile.TemporaryDirectory(prefix='qa-review-selector-') as td:
        selector = Path(td) / 'runs.json'
        selector.write_text(json.dumps({label: str(base / label) for label in ('initial', 'reproduction', 'failure')}))
        env = dict(os.environ, QA_STEP7_RUNS_FILE=str(selector))
        for check in CHECKS:
            result = subprocess.run([sys.executable, str(ROOT / 'tools/release/verify.py'), '--check', check], cwd=ROOT, env=env)
            if result.returncode:
                return result.returncode
    print('PASS: evidence matches this exact tooling checkout; no development authorization or recorder key used')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
