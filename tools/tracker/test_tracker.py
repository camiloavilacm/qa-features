"""Integrity and publisher failure-path tests; fake transport is not live evidence."""
import contextlib,copy,io,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parent))
from tracker import *
SLOTS=['sut-python:playwright','sut-python:selenium','sut-python:cypress','sut-node:playwright','sut-node:selenium','sut-node:cypress']
def fixture(root):
    value={'schema_version':'1.0','issue_id':'SEED-1','campaign_id':'step5-specification-fixture-v1','feature_ref':approved_ref(),'status':'passed','slots':[]}
    for slot in SLOTS:
        rows=[]
        for ac in ('AC-1','AC-2','AC-3'):
            observer={'state':'complete','events':[dict(zip(('method','path','status','authorization_present'),event)) for event in sorted(REQUIRED[ac])],'detail':None}
            data=(json.dumps(observer,sort_keys=True)+'\n').encode();name=ac+'/network.json';p=root/slot.replace(':','-')/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
            rows.append({'id':ac,'status':'passed','duration_ms':1,'observer':observer,'artifacts':[{'path':name,'sha256':digest(data),'kind':'network'}],'error':None})
        result={'schema_version':'1.0','issue_id':'SEED-1','campaign_id':value['campaign_id'],'execution_id':'fixture-'+slot,'feature_ref':value['feature_ref'],'tooling_ref':None,'slot_id':slot,'sut_revision':'a'*64 if slot.startswith('sut-python') else 'b'*64,'runner_revision':'c'*64 if slot.endswith('cypress') else 'd'*64,'started_at':'2026-11-16T00:00:00Z','finished_at':'2026-11-16T00:00:01Z','status':'passed','scenarios':rows}
        value['slots'].append({'slot_id':slot,'state':'complete','result':result})
    return value
class FakeAPI:
    def __init__(self):self.rows=[];self.calls=[];self.issue={'title':'Sandbox','body':'fixture','state':'open','labels':[]};self.uncertain=False
    def request(self,method,route,payload=None):
        self.calls.append((method,route,payload))
        if method=='GET':return {'id':1} if route=='user' else copy.deepcopy(self.issue)
        if method=='POST':
            self.rows.append({'id':7,'body':payload['body'],'user':{'id':1},'html_url':'https://github.com/owner/repo/issues/1#issuecomment-7'})
            if self.uncertain:raise TrackerError('Timeout after persisted write')
        elif method=='PATCH':self.rows[0]['body']=payload['body']
        else:raise AssertionError('Unsupported mutation')
        return self.rows[0]
    def comments(self,repo,issue):return copy.deepcopy(self.rows)
class TrackerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name);self.value=fixture(self.root)
    def test_all_outcomes_and_missing_slots(self):
        validate_campaign(self.value,self.root)
        for status in ('failed','error','not_run'):
            value=copy.deepcopy(self.value);value['slots'][0]['result']['status']=status;row=value['slots'][0]['result']['scenarios'][0];row.update(status=status,error='Synthetic fixture outcome');value['status']='incomplete' if status=='not_run' else status
            validate_campaign(value,self.root)
        value=copy.deepcopy(self.value);value['slots'][0].update(state='missing',result=None);value['status']='incomplete';validate_campaign(value,self.root)
    def test_false_pass_and_mismatched_metadata_are_rejected(self):
        for mutate in (lambda v:v.update(status='failed'),lambda v:v['slots'][0]['result'].update(campaign_id='wrong'),lambda v:v['slots'][0]['result']['scenarios'][0]['observer'].update(state='partial'),lambda v:v['slots'][0]['result'].update(finished_at='2025-01-01T00:00:00Z'),lambda v:v['slots'][0]['result'].update(runner_revision='f'*64),lambda v:v['slots'][0]['result'].update(execution_id=v['slots'][1]['result']['execution_id'])):
            value=copy.deepcopy(self.value);mutate(value)
            with self.assertRaises(TrackerError):validate_campaign(value,self.root)
    def test_tampered_missing_and_symlink_artifacts_rejected(self):
        p=self.root/'sut-python-playwright/AC-1/network.json';data=p.read_bytes();p.write_bytes(b'corrupt')
        with self.assertRaises(TrackerError):validate_campaign(self.value,self.root)
        p.unlink()
        with self.assertRaises(TrackerError):validate_campaign(self.value,self.root)
        target=self.root/'other.json';target.write_bytes(data);p.symlink_to(target)
        with self.assertRaises(TrackerError):validate_campaign(self.value,self.root)
    def test_preview_is_deterministic_and_offline(self):
        path=self.root/'campaign.json';path.write_text(json.dumps(self.value))
        args=[sys.executable,str(Path(__file__).parent/'tracker.py'),'--campaign',str(path),'--artifacts',str(self.root),'--repository','owner/repo','--issue','1','--fixture']
        a=subprocess.run(args,capture_output=True,text=True);b=subprocess.run(args,capture_output=True,text=True)
        self.assertEqual(a.returncode,0);self.assertEqual(a.stdout,b.stdout);self.assertIn('not an executed QA campaign',a.stdout)
        with patch('tracker.GitHub',side_effect=AssertionError('Dry-run must not create transport')), patch('sys.argv',args[1:]), contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(),0)
            self.assertEqual(output.getvalue(),a.stdout)
    def test_sensitive_campaign_identity_is_rejected(self):
        value=copy.deepcopy(self.value);value['campaign_id']='eyJhbGciOiJIUzI1NiJ9.payload.signature'
        for slot in value['slots']:slot['result']['campaign_id']=value['campaign_id']
        with self.assertRaises(TrackerError):validate_campaign(value,self.root)
    def test_apply_cli_is_wired_to_verified_comment_publisher(self):
        path=self.root/'campaign.json';path.write_text(json.dumps(self.value));api=FakeAPI()
        args=['tracker.py','--campaign',str(path),'--artifacts',str(self.root),'--repository','owner/repo','--issue','1','--fixture','--apply']
        with patch('sys.argv',args),patch('tracker.GitHub',return_value=api),contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(),0)
        self.assertEqual(json.loads(output.getvalue())['action'],'created');self.assertEqual(len(api.rows),1)
    def test_create_repeat_update_no_issue_transition(self):
        api=FakeAPI();body=render(self.value,'owner/repo',1,True)
        self.assertEqual(publish(self.value,'owner/repo',1,body,api)['action'],'created')
        self.assertEqual(publish(self.value,'owner/repo',1,body,api)['action'],'noop')
        self.assertEqual(publish(self.value,'owner/repo',1,body+'\n',api)['action'],'updated')
        self.assertEqual(len(api.rows),1)
        self.assertTrue(all('comments' in route for method,route,_ in api.calls if method!='GET'))
        self.assertEqual(api.issue['state'],'open')
    def test_duplicate_and_foreign_markers_fail_without_writes(self):
        api=FakeAPI();body=render(self.value,'owner/repo',1,True);publish(self.value,'owner/repo',1,body,api)
        api.rows*=2;api.calls=[]
        with self.assertRaises(TrackerError):publish(self.value,'owner/repo',1,body,api)
        self.assertFalse(any(method!='GET'for method,_,_ in api.calls))
        api.rows=api.rows[:1];api.rows[0]['user']['id']=2
        with self.assertRaises(TrackerError):publish(self.value,'owner/repo',1,body,api)
    def test_uncertain_create_is_reconciled_without_second_post(self):
        api=FakeAPI();api.uncertain=True;body=render(self.value,'owner/repo',1,True)
        self.assertEqual(publish(self.value,'owner/repo',1,body,api)['action'],'reconciled')
        self.assertEqual(sum(method=='POST'for method,_,_ in api.calls),1)
    def test_issue_field_mutation_is_detected(self):
        api=FakeAPI();original=api.request
        def mutate(method,route,payload=None):
            result=original(method,route,payload)
            if method=='POST':api.issue['state']='closed'
            return result
        api.request=mutate
        with self.assertRaises(TrackerError):publish(self.value,'owner/repo',1,render(self.value,'owner/repo',1,True),api)
    def test_real_transport_paginates_and_denies_incomplete_search(self):
        api=GitHub()
        with patch.object(api,'request',side_effect=[[{}]*100,[{'id':101}]]) as request:
            self.assertEqual(len(api.comments('owner/repo',1)),101);self.assertIn('page=2',request.call_args.args[1])
        with patch.object(api,'request',return_value=[{}]*100):
            with self.assertRaises(TrackerError):api.comments('owner/repo',1)
if __name__=='__main__':unittest.main()
