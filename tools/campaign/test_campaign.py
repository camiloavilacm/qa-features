"""Specification fixtures exercise aggregation; they are not QA execution evidence."""
import copy,json,shutil,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tracker'))
from test_tracker import fixture
from aggregate import aggregate,write,digest,TrackerError,SLOTS
class CampaignTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name).resolve();self.inbox=self.root/'inbox';self.inbox.mkdir();artifacts=self.root/'fixture';artifacts.mkdir();value=fixture(artifacts)
  self.expected={'campaign_id':value['campaign_id'],'attempt':1,'feature_ref':value['feature_ref'],'tooling_ref':'e'*40,'repositories':{'sut-python':'1'*40,'sut-node':'2'*40,'qa-python':'3'*40,'qa-typescript':'4'*40},'runner_fingerprints':{'qa-python':'d'*64,'qa-typescript':'c'*64},'images':{'sut-python':{'config_id':'a'*64,'registry_digest':'ghcr.io/owner/python@sha256:'+'a'*64},'sut-node':{'config_id':'b'*64,'registry_digest':'ghcr.io/owner/node@sha256:'+'b'*64}},'report_repository':'owner/repo','report_issue':1}
  for slot in value['slots']:
   name=slot['slot_id'];directory=self.inbox/('slot-1-'+name.replace(':','-'));shutil.copytree(artifacts/name.replace(':','-'),directory);result=slot['result'];result['tooling_ref']=self.expected['tooling_ref'];write(directory/'results.json',result);self.receipt(name)
 def receipt(self,slot):
  sut,driver=slot.split(':');family='qa-typescript'if driver=='cypress'else 'qa-python';directory=self.inbox/('slot-1-'+slot.replace(':','-'))
  write(directory/'receipt.json',{'campaign_id':self.expected['campaign_id'],'attempt':1,'slot_id':slot,'tooling_ref':self.expected['tooling_ref'],'runner_source_ref':self.expected['repositories'][family],'sut_source_ref':self.expected['repositories'][sut],'sut_image_id':self.expected['images'][sut]['config_id'],'sut_registry_digest':self.expected['images'][sut]['registry_digest'],'result_sha256':digest((directory/'results.json').read_bytes())})
 def run_aggregate(self):return aggregate(self.inbox,self.expected,self.root/'output')
 def test_six_slots_eighteen_scenarios_pass(self):
  value=self.run_aggregate();self.assertEqual(value['status'],'passed');self.assertEqual(sum(len(s['result']['scenarios'])for s in value['slots']),18)
 def test_missing_slot_is_explicit_and_incomplete(self):
  shutil.rmtree(self.inbox/'slot-1-sut-python-playwright');value=self.run_aggregate();self.assertEqual(value['status'],'incomplete');self.assertEqual(value['slots'][0],{'slot_id':SLOTS[0],'state':'missing','result':None})
 def test_previous_attempt_results_are_never_reused(self):
  self.expected['attempt']=2;value=self.run_aggregate();self.assertEqual(value['status'],'incomplete');self.assertTrue(all(s['state']=='missing'for s in value['slots']))
 def test_corrupt_result_becomes_error_without_accepting_pass(self):
  p=self.inbox/'slot-1-sut-python-playwright/results.json';p.write_text('{}');value=self.run_aggregate();self.assertEqual(value['status'],'error');self.assertTrue(all(s['status']=='error'for s in value['slots'][0]['result']['scenarios']))
 def test_partial_observation_cannot_pass_even_with_updated_receipt(self):
  p=self.inbox/'slot-1-sut-python-playwright/results.json';v=json.loads(p.read_text());v['scenarios'][0]['observer']['state']='partial';write(p,v);self.receipt(SLOTS[0]);self.assertEqual(self.run_aggregate()['status'],'error')
 def test_wrong_attempt_or_source_is_rejected(self):
  p=self.inbox/'slot-1-sut-python-playwright/receipt.json';v=json.loads(p.read_text());v['runner_source_ref']='f'*40;write(p,v);self.assertEqual(self.run_aggregate()['status'],'error')
 def test_artifact_tampering_is_rejected_and_not_retained(self):
  p=self.inbox/'slot-1-sut-python-playwright/AC-1/network.json';p.write_text('tampered');self.assertEqual(self.run_aggregate()['status'],'error');self.assertFalse((self.root/'output/artifacts/sut-python-playwright').exists())
 def test_unexpected_slot_is_rejected(self):
  (self.inbox/'slot-1-unknown').mkdir()
  with self.assertRaises(TrackerError):self.run_aggregate()
 def test_attempt_outputs_cannot_be_overwritten(self):
  self.run_aggregate()
  with self.assertRaises(TrackerError):self.run_aggregate()
if __name__=='__main__':unittest.main()
