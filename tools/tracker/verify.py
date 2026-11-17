"""Registered Step 5 checks. Live checks require a concrete external approval."""
from pathlib import Path
import argparse,json,os,subprocess,sys,tempfile
sys.path.insert(0,str(Path(__file__).parent))
from tracker import ROOT,GitHub,TrackerError,approved_ref,digest,marker,publish,render,snapshot,validate_campaign
HERE=Path(__file__).parent
REPOSITORY='camiloavilacm/ai-qa-agent'
def load(name):return json.loads((HERE/'fixtures'/name).read_text())
def write(name,value):(ROOT/'harness/evidence'/name).write_text(json.dumps(value,indent=2)+'\n')
def approval():
    value=os.environ.get('QA_TRACKER_SANDBOX_APPROVAL_FILE')
    if not value:print('NOT RUN: live sandbox issue/comment approval is pending');raise SystemExit(3)
    path=Path(value)
    assert not path.is_symlink() and not path.resolve().is_relative_to(ROOT) and path.stat().st_mode&0o077==0
    receipt=json.loads(path.read_text());assert receipt['source']=='human' and receipt['repository']==REPOSITORY and isinstance(receipt['issue'],int) and receipt['issue']>0
    for name in ('missing.json','not-run.json'):
        assert receipt['fixtures'][name]==digest((HERE/'fixtures'/name).read_bytes())
    return receipt

def dry_run():
    p=subprocess.run([sys.executable,'-m','unittest','discover','-s','tools/tracker','-p','test_*.py','-v'],cwd=ROOT);assert p.returncode==0
    with tempfile.TemporaryDirectory() as temp:
        for fixture_name,output_name in [('missing.json','step5-sandbox-comment.md'),('not-run.json','step5-sandbox-update.md')]:
            args=[sys.executable,str(HERE/'tracker.py'),'--campaign',str(HERE/'fixtures'/fixture_name),'--artifacts',temp,'--repository',REPOSITORY,'--issue','1','--fixture']
            a=subprocess.run(args,cwd=ROOT,capture_output=True,text=True);b=subprocess.run(args,cwd=ROOT,capture_output=True,text=True)
            assert a.returncode==b.returncode==0 and a.stdout==b.stdout
            assert 'Specification fixture' in a.stdout and 'not an executed QA campaign' in a.stdout
            (ROOT/'harness/evidence'/output_name).write_text(a.stdout)
    print('PASS: actual offline CLI previews, deterministic rendering and integrity/publisher regression scenarios')

def publication():
    receipt=approval();api=GitHub();before=snapshot(api.request('GET',f'repos/{REPOSITORY}/issues/{receipt["issue"]}'))
    with tempfile.TemporaryDirectory() as temp:
        campaign=validate_campaign(load('missing.json'),temp);body=render(campaign,REPOSITORY,receipt['issue'],True)
        result=publish(campaign,REPOSITORY,receipt['issue'],body,api)
    write('step5-publication.json',{'repository':REPOSITORY,'issue':receipt['issue'],'before':before,'publication':result,'fixture_sha256':digest((HERE/'fixtures/missing.json').read_bytes())})
    print('PASS: real sandbox comment verified',result['comment_url'])

def idempotency():
    receipt=approval();api=GitHub();results=[]
    with tempfile.TemporaryDirectory() as temp:
        for filename,expected in [('missing.json','noop'),('missing.json','noop'),('not-run.json','updated'),('not-run.json','noop'),('missing.json','updated')]:
            campaign=validate_campaign(load(filename),temp);body=render(campaign,REPOSITORY,receipt['issue'],True)
            result=publish(campaign,REPOSITORY,receipt['issue'],body,api);assert result['action']==expected;results.append(result)
    assert len({r['comment_id']for r in results})==1
    write('step5-idempotency.json',results);print('PASS: real repeat/no-op/update/restore use one comment ID')

def no_transition():
    receipt=approval();prior=json.loads((ROOT/'harness/evidence/step5-publication.json').read_text())
    assert prior['issue']==receipt['issue'] and prior['repository']==REPOSITORY
    after=snapshot(GitHub().request('GET',f'repos/{REPOSITORY}/issues/{receipt["issue"]}'))
    assert after==prior['before']
    write('step5-no-transition.json',{'before':prior['before'],'after':after,'unchanged':True});print('PASS: real issue title/body/state/labels/assignees/milestone/lock unchanged')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--check',choices=['dry-run','sandbox-comment','idempotency','no-transition'],required=True);a=p.parse_args()
    try:{'dry-run':dry_run,'sandbox-comment':publication,'idempotency':idempotency,'no-transition':no_transition}[a.check]()
    except Exception:print('FAIL: tracker verification did not satisfy acceptance; inspect retained diagnostics',file=sys.stderr);raise SystemExit(1)
