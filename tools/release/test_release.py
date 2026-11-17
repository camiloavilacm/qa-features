import os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from release_package import seal,verify_payload
class PayloadIntegrity(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name);(self.root/'record.json').write_text('{"status":"verified"}')
  with patch.dict(os.environ,GITHUB_SHA='a'*40):seal(self.root,'candidate','b'*64)
 def test_unchanged_payload(self):self.assertEqual(verify_payload(self.root)['role'],'candidate')
 def test_modified_evidence_rejected(self):
  (self.root/'record.json').write_text('{"status":"failed"}')
  with self.assertRaises(AssertionError):verify_payload(self.root)
 def test_missing_evidence_rejected(self):
  (self.root/'record.json').unlink()
  with self.assertRaises(AssertionError):verify_payload(self.root)
 def test_extra_evidence_rejected(self):
  (self.root/'extra.json').write_text('{}')
  with self.assertRaises(AssertionError):verify_payload(self.root)
 def test_nested_payload_cannot_evade_inventory(self):
  (self.root/'nested').mkdir();(self.root/'nested/payload.json').write_text('{}')
  with self.assertRaises(AssertionError):verify_payload(self.root)
 def test_symlink_rejected(self):
  (self.root/'link').symlink_to(self.root/'record.json')
  with self.assertRaises(AssertionError):verify_payload(self.root)
if __name__=='__main__':unittest.main()
