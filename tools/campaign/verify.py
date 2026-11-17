"""Step 6 registered checks; actual hosted evidence is required for completion."""
from pathlib import Path
import argparse,ast,hashlib,io,json,os,re,subprocess,sys,tarfile
import yaml
from aggregate import SLOTS,validate_campaign
ROOT=Path(__file__).resolve().parents[2]
def runs():
 path=os.environ.get('QA_STEP6_RUNS_FILE')
 if not path:print('NOT RUN: hosted campaign acceptance evidence is not configured');raise SystemExit(3)
 return json.loads(Path(path).read_text())
def load(directory):
 p=Path(directory);value=json.loads((p/'campaign.json').read_text());expected=json.loads((p/'provenance.json').read_text())['expected'];validate_campaign(value,p/'artifacts',expected['feature_ref'])
 run=json.loads((p/'github-run.json').read_text());jobs=json.loads((p/'github-jobs.json').read_text())['jobs'];assert run['head_sha']==expected['tooling_ref'] and run['id']==int(expected['campaign_id'].split('-')[-1]) and run['run_attempt']==expected['attempt']
 return p,value,expected,run,jobs

def six_jobs():
 data=runs()
 for label in ['normal','rerun']:
  p,value,expected,run,jobs=load(data[label]);qa=[j for j in jobs if j['name'].startswith('QA ')]
  assert len(qa)==6 and all(j['conclusion']=='success'for j in qa) and run['conclusion']=='success'
  assert value['status']=='passed'and len(value['slots'])==6 and sum(len(s['result']['scenarios'])for s in value['slots'])==18
  for slot in value['slots']:
   result=slot['result'];assert result['tooling_ref']==expected['tooling_ref'] and result['sut_revision']==expected['images'][slot['slot_id'].split(':')[0]]['config_id']
 print('PASS: actual six hosted matrix jobs and 18 passes on initial run and full rerun')

def single_report():
 data=runs();initial=load(data['normal']);rerun=load(data['rerun']);assert initial[1]['campaign_id']==rerun[1]['campaign_id'] and initial[2]['attempt']<rerun[2]['attempt']
 ids=[]
 for item in [initial,rerun]:
  p,value,expected,run,jobs=item;reports=[j for j in jobs if j['name']=='One campaign report'];assert len(reports)==1 and reports[0]['conclusion']=='success'
  artifacts=json.loads((p/'github-artifacts.json').read_text())['artifacts'];assert sum(a['name']==f'campaign-{run["id"]}-{expected["attempt"]}'for a in artifacts)==1
  publication=json.loads((p/'publication.json').read_text());assert publication['issue_fields_unchanged'];ids.append(publication['comment_id'])
  assert expected['report_issue']>0 and publication['comment_url'].startswith(f'https://github.com/{expected["report_repository"]}/issues/{expected["report_issue"]}#')
  publishing=[s for s in reports[0]['steps']if s['name']=='Publish selected private issue comment'];assert len(publishing)==1 and publishing[0]['conclusion']=='success'
 assert len(set(ids))==1
 print('PASS: one always-running report job/artifact per attempt, same campaign and one verified issue comment across rerun')

def failure_paths():
 p=subprocess.run([sys.executable,'-m','unittest','discover','-s','tools/campaign','-p','test_*.py','-v'],cwd=ROOT);assert p.returncode==0
 data=runs();directory,value,expected,run,jobs=load(data['failure']);assert expected['observer_fault']=='unavailable' and run['conclusion']=='failure' and value['status']=='error'
 affected=next(s['result']for s in value['slots']if s['slot_id']=='sut-python:playwright');assert all(s['observer']['state']=='unavailable' and s['status']=='error'for s in affected['scenarios'])
 assert len([j for j in jobs if j['name']=='One campaign report'])==1 and (directory/'campaign.md').exists()
 print('PASS: real failed matrix still reports error; fixture checks reject stale/missing/tampered/mixed evidence')

def no_model_calls():
 roots=[ROOT/'tools/tracker/tracker.py']+list((ROOT/'tools/campaign').glob('*.py'))
 runtime=[p for p in roots if p.name not in ['verify.py','test_campaign.py']]
 # Inspect the committed runner sources, with no parent-workspace dependency.
 lock=json.loads((ROOT/'tools/campaign/repositories.json').read_text());remote_sources=[]
 for repo in ('qa-python','qa-typescript'):
  result=subprocess.run(['gh','api',f'repos/camiloavilacm/{repo}/tarball/{lock["repositories"][repo]}'],capture_output=True)
  assert result.returncode==0,'Pinned runner source inspection unavailable'
  count=0
  with tarfile.open(fileobj=io.BytesIO(result.stdout))as archive:
   for member in archive.getmembers():
    name='/'.join(member.name.split('/')[1:])
    selected=name.startswith(('runner/','tests/')) if repo=='qa-python'else name.startswith(('runner/','cypress/'))or name in ('tools/run.cjs','tools/contracts.cjs','tools/typecheck.cjs','cypress.config.ts')
    if member.isfile() and selected and Path(name).suffix in ('.py','.ts','.cjs'):
     remote_sources.append((repo+'/'+name,archive.extractfile(member).read().decode()));count+=1
  assert count>0,'Missing runtime instrumentation sources'
 forbidden={'openai','anthropic','langchain','ollama','litellm'}
 for path,source in [(str(p),p.read_text())for p in runtime]+remote_sources:
  if Path(path).suffix=='.py':
   tree=ast.parse(source)
   for node in ast.walk(tree):
    names=[a.name for a in node.names]if isinstance(node,ast.Import)else[node.module or '']if isinstance(node,ast.ImportFrom)else[]
    assert not any(n.split('.')[0]in forbidden for n in names),str(path)
  else:assert not re.search(r'(?:require\(|from\s+)[\'\"](?:openai|anthropic|langchain|ollama)',source)
  assert not any(domain in source for domain in ['api.openai.com','api.anthropic.com','generativelanguage.googleapis.com'])
 workflow=yaml.safe_load((ROOT/'.github/workflows/campaign.yml').read_text());assert workflow['jobs']['qa']['strategy']['fail-fast']is False
 assert all(re.fullmatch(r'[a-f0-9]{40}',step['uses'].split('@')[1])for job in workflow['jobs'].values()for step in job['steps']if 'uses'in step)
 print('PASS: pinned deterministic workflow and committed runtime sources contain no model client/domain; fixed assertions are preserved')
def verify_saved():
 data=runs();hashes={}
 head=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
 subprocess.run(['git','-C',str(ROOT),'diff','--quiet','HEAD','--','.github','tools/campaign','tools/tracker'],check=True)
 assert not subprocess.check_output(['git','-C',str(ROOT),'ls-files','--others','--exclude-standard','--','.github','tools/campaign','tools/tracker'],text=True).strip(),'Runtime source is uncommitted'
 for label in ('normal','rerun','failure'):
  directory=Path(data[label]).resolve();assert directory.is_relative_to(ROOT/'harness/evidence')
  _,_,expected,_,_=load(directory);assert expected['tooling_ref']==head,'Hosted evidence is stale for the current tooling commit'
  for path in sorted(directory.rglob('*')):
   if path.is_file():
    assert not path.is_symlink();hashes[str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
 result=hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()
 print('CAMPAIGN_RECEIPT_SHA256',result);return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--check',choices=['six-jobs','single-report','failure-paths','no-model-calls'],required=True);a=p.parse_args()
 try:{'six-jobs':six_jobs,'single-report':single_report,'failure-paths':failure_paths,'no-model-calls':no_model_calls}[a.check]();verify_saved()
 except Exception as error:print('FAIL:',type(error).__name__,'acceptance evidence was not sufficient',file=sys.stderr);raise SystemExit(1)
