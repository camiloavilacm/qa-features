"""Negative integrity fixtures; these do not constitute hosted QA acceptance."""
import copy,json,sys,tempfile,unittest
from pathlib import Path
from receipts import identity,validate_rollback,require_upstream
from release_core import ROOT,manifest,write
from smoke_report import build_report
sys.path.insert(0,str(ROOT/'tools/tracker'))
from test_tracker import fixture,FakeAPI
from tracker import publish

class RollbackIdentity(unittest.TestCase):
    def setUp(self):
        self.base,self.bsha=manifest('baseline');self.candidate,self.csha=manifest()
        self.context={'campaign_id':'smoke-gh-123-100','run_id':100,'attempt':1,'tooling_ref':'a'*40}
        phases=[]
        for phase,m in [('baseline',self.base),('candidate',self.candidate),('rollback',self.base)]:
            image=m['images']['sut-python'];phases.append({'phase':phase,'image_id':image['config_id'],'registry_digest':image['registry_digest'],'runtime_config_sha256':'b'*64,'baseline_row_sha256':'c'*64,'database_container':'d'*64,'hurl_7_requests':'PASS','unauthenticated_user_401':'PASS','served_frontend_hashes':'PASS'})
        self.record={**identity(self.context),'status':'PASS','sut':'sut-python','baseline_manifest_sha256':self.bsha,'candidate_manifest_sha256':self.csha,'phases':phases}
    def validate(self,record=None,context=None):
        return validate_rollback(record or self.record,'sut-python',context or self.context,self.base,self.candidate,self.bsha,self.csha)
    def test_current_execution_accepted(self):self.validate()
    def test_another_attempt_run_tooling_or_campaign_rejected(self):
        for field,value in [('attempt',2),('run_id',101),('tooling_ref','b'*40),('campaign_id','smoke-gh-999-100')]:
            with self.subTest(field=field):
                record=copy.deepcopy(self.record);record[field]=value
                with self.assertRaisesRegex(ValueError,'another execution'):self.validate(record)
    def test_legacy_receipt_without_identity_rejected(self):
        record={k:v for k,v in self.record.items()if k not in self.context}
        with self.assertRaises(ValueError):self.validate(record)
    def test_image_drift_and_incomplete_or_changed_state_rejected(self):
        for field,value in [('image_id','f'*64),('registry_digest','wrong'),('hurl_7_requests','FAIL'),('runtime_config_sha256','e'*64),('baseline_row_sha256','e'*64),('database_container','different')]:
            with self.subTest(field=field):
                record=copy.deepcopy(self.record);record['phases'][1][field]=value
                with self.assertRaises(ValueError):self.validate(record)
    def test_failed_missing_skipped_or_cancelled_upstream_is_rejected(self):
        require_upstream(dict.fromkeys(('baseline','qa','rollback'),'success'))
        for value in ('failure','skipped','cancelled',''):
            with self.assertRaises(ValueError):require_upstream({'baseline':'success','qa':'success','rollback':value})

class AttemptReporting(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.directory=Path(self.temp.name)
        self.env={'GITHUB_REPOSITORY':'camiloavilacm/qa-features','GITHUB_REPOSITORY_ID':'123','GITHUB_RUN_ID':'100','GITHUB_RUN_ATTEMPT':'1','GITHUB_SHA':'a'*40,'QA_REPORT_ISSUE':'2','QA_UPSTREAM_BASELINE':'success','QA_UPSTREAM_QA':'success','QA_UPSTREAM_ROLLBACK':'success','QA_RELEASE_VERIFICATION':'success','QA_BUNDLE_PUBLICATION':'success'}
        self.context={'campaign_id':'smoke-gh-123-100','run_id':100,'attempt':1,'tooling_ref':'a'*40}
        artifacts=self.directory/'artifacts';artifacts.mkdir();value=fixture(artifacts);value['campaign_id']=self.context['campaign_id']
        for slot in value['slots']:slot['result']['campaign_id']=value['campaign_id'];slot['result']['tooling_ref']='a'*40
        write(self.directory/'campaign.json',value);write(self.directory/'provenance.json',{'expected':self.context})
        _,digest=manifest();write(self.directory/'release-record.json',{'campaign_id':self.context['campaign_id'],'run_id':100,'attempt':1,'release_tooling_ref':'a'*40,'release_status':'verified','manifest_sha256':digest});write(self.directory/'published.json',{'manifest_sha256':digest,'release_tooling_ref':'a'*40,'bundle':'ghcr.io/camiloavilacm/qa-smoke-release@sha256:'+'b'*64})
    def test_success_then_failure_updates_same_comment_without_issue_transition(self):
        api=FakeAPI();campaign,body,status=build_report(self.directory,self.env);first=publish(campaign,self.env['GITHUB_REPOSITORY'],2,body,api)
        self.assertEqual(status['release_status'],'verified')
        self.env.update(GITHUB_RUN_ATTEMPT='2',QA_UPSTREAM_ROLLBACK='failure',QA_RELEASE_VERIFICATION='failure',QA_BUNDLE_PUBLICATION='skipped')
        campaign,body,status=build_report(self.directory,self.env);second=publish(campaign,self.env['GITHUB_REPOSITORY'],2,body,api)
        self.assertEqual(first['comment_id'],second['comment_id']);self.assertEqual(second['action'],'updated');self.assertEqual(status['release_status'],'failed');self.assertEqual(len(api.rows),1);self.assertEqual(api.issue['state'],'open');self.assertIn('Attempt: **2**',body);self.assertNotIn('Verified immutable synthetic smoke bundle:',body);self.assertEqual(status['qa_status'],'error')
    def test_passed_qa_with_failed_rollback_is_failed_release(self):
        self.env.update(QA_UPSTREAM_ROLLBACK='failure',QA_RELEASE_VERIFICATION='failure',QA_BUNDLE_PUBLICATION='skipped')
        _,body,status=build_report(self.directory,self.env)
        self.assertEqual(status['qa_status'],'passed');self.assertEqual(status['release_status'],'failed');self.assertIn('Release outcome: **failed**',body);self.assertIsNone(status['bundle'])
    def test_unavailable_or_invalid_campaign_still_has_failure_report(self):
        for content in (None,'{}','not-json'):
            p=self.directory/'campaign.json'
            if content is None:p.unlink(missing_ok=True)
            else:p.write_text(content)
            _,body,status=build_report(self.directory,self.env);self.assertEqual(status['release_status'],'failed');self.assertIn('no passing scenarios are claimed',body)
    def test_failed_bundle_publication_cannot_reuse_earlier_success(self):
        self.env['QA_BUNDLE_PUBLICATION']='failure';_,body,status=build_report(self.directory,self.env);self.assertEqual(status['release_status'],'failed');self.assertNotIn('Verified immutable synthetic smoke bundle:',body)

class HostedOutcomeSemantics(unittest.TestCase):
    def test_continued_error_uses_outcome_instead_of_rest_conclusion(self):
        import importlib.util
        spec=importlib.util.spec_from_file_location('smoke_acceptance',ROOT/'tools/release/verify.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        steps={'Verify release before publication':{'conclusion':'success'},'Publish content-addressed bundle':{'conclusion':'skipped'},'Publish private smoke report':{'conclusion':'success'}}
        module.failed_release_steps(steps,{'verification':'failure'})
        with self.assertRaises(AssertionError):module.failed_release_steps(steps,{'verification':'success'})
        steps['Publish content-addressed bundle']['conclusion']='success'
        with self.assertRaises(AssertionError):module.failed_release_steps(steps,{'verification':'failure'})

if __name__=='__main__':unittest.main()
