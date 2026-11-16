"""Mutation checks of validators, not framework-specific business step definitions."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
import validate

class SpecificationValidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='qa-spec-validation-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for name in ('openapi.yml', 'selectors.json', 'api-expectations.yaml', 'api', 'data', 'features', 'schemas'):
            source = validate.ROOT / name
            if source.is_dir(): shutil.copytree(source, self.root / name)
            else: shutil.copyfile(source, self.root / name)
        self.override = patch.object(validate, 'ROOT', self.root)
        self.override.start(); self.addCleanup(self.override.stop)

    def mutate_json(self, name, transform):
        path = self.root / name
        data = json.loads(path.read_text()); transform(data); path.write_text(json.dumps(data, indent=2) + '\n')

    def test_valid_specification_and_schema_adversarial_fixtures(self):
        for check in (validate.check_openapi, validate.check_hurl, validate.check_gherkin, validate.check_selectors, validate.check_baseline, validate.check_schemas):
            check()

    def test_css_selector_is_rejected(self):
        self.mutate_json('selectors.json', lambda v: v['selectors']['login.email'].update(by='css'))
        with self.assertRaises(ValueError): validate.check_selectors()

    def test_missing_selector_is_rejected(self):
        self.mutate_json('selectors.json', lambda v: v['selectors'].pop('login.error'))
        with self.assertRaises(ValueError): validate.check_selectors()

    def test_mutable_baseline_is_rejected(self):
        self.mutate_json('data/baseline.json', lambda v: v.update(immutable=False))
        with self.assertRaises(ValueError): validate.check_baseline()

    def test_bearer_authentication_drift_is_rejected(self):
        self.mutate_json('api-expectations.yaml', lambda v: v['authentication'].update(scheme='Bearer'))
        with self.assertRaises(ValueError): validate.check_openapi()

    def test_ac3_no_session_check_cannot_be_dropped(self):
        p = self.root / 'features/auth/login.feature'
        p.write_text(p.read_text().replace('    And the browser still has no authentication state\n', ''))
        with self.assertRaises(ValueError): validate.check_gherkin()

    def test_unauthenticated_hurl_status_cannot_be_weakened(self):
        p = self.root / 'api/auth.hurl'
        p.write_text(p.read_text().replace('HTTP 401', 'HTTP 200', 1))
        with self.assertRaises(ValueError): validate.check_hurl()

if __name__ == '__main__':
    unittest.main()
