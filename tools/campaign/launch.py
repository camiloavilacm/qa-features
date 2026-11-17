"""Deterministic operator CLI for dispatch, attempt download and authorized reporting."""
import argparse,datetime as dt,json,subprocess,time,sys
from pathlib import Path
from aggregate import write
REPO='camiloavilacm/qa-features'
def gh(*args):
 p=subprocess.run(['gh',*args],capture_output=True,text=True,timeout=60)
 if p.returncode:raise RuntimeError('GitHub operation failed; inspect authentication and run availability')
 return p.stdout

def api(route):return json.loads(gh('api',route))
def dispatch(fault,record,issue=1):
 prior={r['id']for r in api(f'repos/{REPO}/actions/workflows/campaign.yml/runs?per_page=50')['workflow_runs']}
 gh('workflow','run','campaign.yml','--repo',REPO,'--ref','main','-f','observer_fault='+fault,'-f','report_issue='+str(issue))
 for _ in range(20):
  runs=[r for r in api(f'repos/{REPO}/actions/workflows/campaign.yml/runs?per_page=50')['workflow_runs']if r['id']not in prior]
  if len(runs)==1:
   r=runs[0];value={'repository':REPO,'run_id':r['id'],'tooling_ref':r['head_sha'],'run_url':r['html_url'],'observer_fault':fault,'report_issue':issue};write(record,value);print(json.dumps(value));return
  if len(runs)>1:raise RuntimeError('Ambiguous concurrent dispatches; refusing to select a run')
  time.sleep(2)
 raise RuntimeError('Dispatched workflow did not become observable')
def wait(record,attempt):
 value=json.loads(record.read_text());deadline=time.monotonic()+2400
 while time.monotonic()<deadline:
  r=api(f'repos/{REPO}/actions/runs/{value["run_id"]}')
  print('Run',value['run_id'],'attempt',r['run_attempt'],r['status'],r.get('conclusion'),flush=True)
  if r['run_attempt']>=attempt and r['status']=='completed':
   assert r['head_sha']==value['tooling_ref'];value.update(attempt=r['run_attempt'],conclusion=r['conclusion']);write(record,value);return
  time.sleep(20)
 raise RuntimeError('Workflow did not complete in the bounded observation window')
def download(record,output):
 value=json.loads(record.read_text());run=value['run_id'];attempt=value['attempt'];assert not output.exists(),'Refusing to overwrite archived attempt'
 gh('run','download',str(run),'--repo',REPO,'--name',f'campaign-{run}-{attempt}','--dir',str(output))
 write(output/'github-run.json',api(f'repos/{REPO}/actions/runs/{run}'))
 write(output/'github-jobs.json',api(f'repos/{REPO}/actions/runs/{run}/attempts/{attempt}/jobs?per_page=100'))
 artifacts=api(f'repos/{REPO}/actions/runs/{run}/artifacts?per_page=100');write(output/'github-artifacts.json',artifacts)
 print('Archived attempt',output)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['dispatch','wait','download','rerun']);p.add_argument('--record',type=Path,required=True);p.add_argument('--fault',choices=['none','unavailable'],default='none');p.add_argument('--attempt',type=int,default=1);p.add_argument('--report-issue',type=int,default=1);p.add_argument('--output',type=Path);a=p.parse_args()
 try:
  if a.action=='dispatch':dispatch(a.fault,a.record,a.report_issue)
  elif a.action=='wait':wait(a.record,a.attempt)
  elif a.action=='download':download(a.record,a.output)
  else:
   value=json.loads(a.record.read_text());gh('run','rerun',str(value['run_id']),'--repo',REPO);print('Rerun requested for same campaign',value['run_id'])
 except Exception as e:print(str(e),file=sys.stderr);raise SystemExit(1)
