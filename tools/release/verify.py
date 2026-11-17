"""Step 7 acceptance requires two real, independently hosted immutable smoke runs."""
import argparse,hashlib,json,os,subprocess,sys
from pathlib import Path
from release_core import ROOT,manifest,sha,governance
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
  for sut,receipt in r['rollback'].items():
   assert receipt['status']=='PASS'and receipt['baseline_manifest_sha256']==bsha and receipt['candidate_manifest_sha256']==digest
   phases=receipt['phases'];assert [p['phase']for p in phases]==['baseline','candidate','rollback']
   assert [p['image_id']for p in phases]==[base['images'][sut]['config_id'],m['images'][sut]['config_id'],base['images'][sut]['config_id']]
   assert [p['registry_digest']for p in phases]==[base['images'][sut]['registry_digest'],m['images'][sut]['registry_digest'],base['images'][sut]['registry_digest']]
   for field in ('runtime_config_sha256','baseline_row_sha256','database_container'):assert len({p[field]for p in phases})==1 and phases[0][field]
   assert all(p['hurl_7_requests']==p['unauthenticated_user_401']==p['served_frontend_hashes']=='PASS'for p in phases)
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
def verify_saved():
 head=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
 paths=['.github','tools/release','tools/campaign','tools/tracker','harness/scripts','harness/config']
 subprocess.run(['git','-C',str(ROOT),'diff','--quiet','HEAD','--',*paths],check=True)
 assert not subprocess.check_output(['git','-C',str(ROOT),'ls-files','--others','--exclude-standard','--',*paths],text=True).strip()
 hashes={}
 for label in ('initial','reproduction'):
  row=load(label);assert row[5]['head_sha']==head,'Hosted smoke evidence is stale for current tooling commit'
  for path in sorted(row[0].rglob('*')):
   if path.is_file():assert not path.is_symlink();hashes[str(path.relative_to(ROOT))]=sha(path)
 receipt=hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest();print('SMOKE_RECEIPT_SHA256',receipt);return receipt
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--check',choices=['image-digests','reproduction','18-passes','rollback'],required=True);a=p.parse_args()
 try:{'image-digests':image_digests,'reproduction':reproduction,'18-passes':passes,'rollback':rollback}[a.check]();verify_saved()
 except Exception as e:print('FAIL:',type(e).__name__,str(e),file=sys.stderr);raise SystemExit(1)
