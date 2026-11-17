"""Step 7 acceptance requires two real, independently hosted immutable smoke runs."""
import argparse,hashlib,json,os,subprocess,sys
from pathlib import Path
from release_core import ROOT,manifest,sha,governance
from receipts import validate_rollback
sys.path.insert(0,str(ROOT/'tools/tracker'))
from tracker import validate_campaign

def saved():
 path=os.environ.get('QA_STEP7_RUNS_FILE')
 if not path:print('NOT RUN: hosted smoke and independent reproduction evidence is not configured');raise SystemExit(3)
 return json.loads(Path(path).read_text())
def load(label):
 directory=Path(saved()[label]).resolve();assert directory.is_relative_to(ROOT/'harness/evidence')
 def read(name):return json.loads((directory/name).read_text())
 campaign=read('campaign.json');context=read('provenance.json')['expected'];record=read('release-record.json');published=read('published.json');run=read('github-run.json');jobs=read('github-jobs.json')['jobs'];publication=read('publication.json')
 validate_campaign(campaign,directory/'artifacts',context['feature_ref'])
 m,digest=manifest();assert run['id']==record['run_id']==int(context['campaign_id'].split('-')[-1]) and run['run_attempt']==record['attempt']==context['attempt']
 assert run['head_sha']==record['release_tooling_ref']==context['tooling_ref'] and run['conclusion']=='success'
 assert record['release_status']=='verified' and record['manifest_sha256']==published['manifest_sha256']==context['release_manifest_sha256']==digest
 assert publication['body_sha256']==sha(directory/'smoke-report.md') and json.loads((directory/'report-status.json').read_text())['release_status']=='verified'
 assert record['qa_campaign_sha256']==sha(directory/'campaign.json') and record['image_digests']==context['images']==m['images']
 assert record['development_harness']==governance() and not record['secret_values_exported']and not record['production_deployment']
 assert publication['issue_fields_unchanged'] and publication['comment_url'].startswith('https://github.com/camiloavilacm/qa-features/issues/2#')
 assert len(jobs)==10 and all(j['conclusion']=='success'for j in jobs)
 assert len([j for j in jobs if j['name'].startswith('QA ')])==6
 return directory,campaign,context,record,published,run,jobs

def image_digests():
 m,_=manifest();base,bsha=manifest('baseline');assert m['previous_manifest_sha256']==bsha
 for label in ('initial','reproduction'):
  p,c,ctx,r,*_=load(label)
  assert set(r['configuration'])==set(r['toolchains'])=={s['slot_id']for s in c['slots']}
  for slot in c['slots']:
   sut=slot['slot_id'].split(':')[0];assert slot['result']['sut_revision']==m['images'][sut]['config_id']
   assert r['configuration'][slot['slot_id']]['source_file_hashes']==m['configuration'][sut]['files']
  assert all(base['images'][s]['config_id']!=m['images'][s]['config_id']for s in m['images'])
 print('PASS: exact image digests, actual container IDs, immutable frontend/configuration/harness provenance')
def passes():
 for label in ('initial','reproduction'):
  _,c,ctx,r,*_=load(label)
  assert c['status']=='passed' and len(c['slots'])==6 and r['qa_scenarios_passed']==18
  assert sum(len(s['result']['scenarios'])for s in c['slots'])==18
  for slot in c['slots']:
   assert all(s['status']=='passed'and s['observer']['state']=='complete'for s in slot['result']['scenarios'])
 print('PASS: 18 actual unchanged scenarios with complete observers on each independent hosted run')
def rollback():
 base,bsha=manifest('baseline');m,digest=manifest()
 for label in ('initial','reproduction'):
  r=load(label)[3];assert set(r['rollback'])=={'sut-python','sut-node'}
  context=load(label)[2]
  for sut,receipt in r['rollback'].items():validate_rollback(receipt,sut,context,base,m,bsha,digest)
 print('PASS: actual baseline -> candidate -> baseline on both SUTs in both runs, unchanged database/config/baseline row')
def reproduction():
 a=load('initial');b=load('reproduction');assert a[5]['id']!=b[5]['id'] and a[5]['head_sha']==b[5]['head_sha']
 assert not a[3]['reproduction_bundle'] and b[3]['reproduction_bundle']==a[4]['bundle']
 assert a[3]['previous_bundle']==b[3]['previous_bundle']
 for identity,tool in a[3]['toolchains'].items():
  other=b[3]['toolchains'][identity]
  for field in ('binaries','python','packages_sha256','feature_packages_sha256'):assert tool[field]==other[field]
  assert tool['fresh_tool_cache'] and other['fresh_tool_cache']
 assert subprocess.run([sys.executable,'-m','unittest','discover','-s','tools/release','-p','test_*.py','-v'],cwd=ROOT).returncode==0
 print('PASS: independently dispatched fresh machines reproduced the sealed OCI bundle with identical images/tools; tamper checks reject invalid payloads')
def load_failure():
 directory=Path(saved()['failure']).resolve();assert directory.is_relative_to(ROOT/'harness/evidence')
 def read(name):return json.loads((directory/name).read_text())
 campaign=read('campaign.json');context=read('provenance.json')['expected'];run=read('github-run.json');jobs=read('github-jobs.json')['jobs'];report=read('report-status.json');publication=read('publication.json')
 validate_campaign(campaign,directory/'artifacts',context['feature_ref'])
 assert run['id']==report['run_id']==context['run_id'] and run['run_attempt']==report['attempt']==context['attempt'] and run['conclusion']=='failure'
 assert run['head_sha']==report['tooling_ref']==context['tooling_ref']
 assert report['release_status']=='failed' and report['bundle']is None and report['upstream']['rollback']=='failure'
 assert not(directory/'published.json').exists() and not(directory/'release-record.json').exists()
 assert publication['issue_fields_unchanged'] and publication['body_sha256']==sha(directory/'smoke-report.md')
 assert 'Release outcome: **failed**'in(directory/'smoke-report.md').read_text()
 return directory,campaign,context,report,publication,run,jobs

def failed_release_steps(steps,report):
 # REST conclusion reflects continue-on-error; the report retains steps.verify.outcome.
 assert 'Verify release before publication'in steps and report['verification']=='failure'
 assert steps['Publish content-addressed bundle']['conclusion']=='skipped'and steps['Publish private smoke report']['conclusion']=='success'

def failure_reporting():
 initial=load('initial');failure=load_failure()
 assert initial[5]['id']==failure[5]['id'] and initial[2]['attempt']<failure[2]['attempt']
 initial_publication=json.loads((initial[0]/'publication.json').read_text())
 assert failure[4]['comment_id']==initial_publication['comment_id'] and failure[4]['action']=='updated'
 assert failure[1]['status']=='passed'and failure[3]['qa_status']=='passed'
 qa=[j for j in failure[6]if j['name'].startswith('QA ')];rollbacks=[j for j in failure[6]if j['name'].startswith('Rollback ')]
 assert len(qa)==6 and all(j['conclusion']=='success'for j in qa)and len(rollbacks)==2 and all(j['conclusion']=='failure'for j in rollbacks)
 release=next(j for j in failure[6]if j['name']=='Publish immutable smoke bundle');steps={s['name']:s for s in release['steps']}
 failed_release_steps(steps,failure[3])
 assert subprocess.run([sys.executable,'-m','unittest','discover','-s','tools/release','-p','test_*.py','-v'],cwd=ROOT).returncode==0
 print('PASS: actual passing campaign rerun fails closed with unavailable current-attempt rollback, publishes no bundle, and updates the same private comment to failed')

def verify_saved():
 head=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
 paths=['.github','tools/release','tools/campaign','tools/tracker','harness/scripts','harness/config']
 subprocess.run(['git','-C',str(ROOT),'diff','--quiet','HEAD','--',*paths],check=True)
 assert not subprocess.check_output(['git','-C',str(ROOT),'ls-files','--others','--exclude-standard','--',*paths],text=True).strip()
 hashes={}
 for label in ('initial','reproduction','failure'):
  row=load_failure()if label=='failure'else load(label);assert row[5]['head_sha']==head,'Hosted smoke evidence is stale for current tooling commit'
  for path in sorted(row[0].rglob('*')):
   if path.is_file():assert not path.is_symlink();hashes[str(path.relative_to(ROOT))]=sha(path)
 receipt=hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest();print('SMOKE_RECEIPT_SHA256',receipt);return receipt
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--check',choices=['image-digests','reproduction','18-passes','rollback','failure-reporting'],required=True);a=p.parse_args()
 try:{'image-digests':image_digests,'reproduction':reproduction,'18-passes':passes,'rollback':rollback,'failure-reporting':failure_reporting}[a.check]();verify_saved()
 except Exception as e:print('FAIL:',type(e).__name__,str(e),file=sys.stderr);raise SystemExit(1)
