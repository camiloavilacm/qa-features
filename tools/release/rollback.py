"""Restore baseline image digests while preserving the same synthetic database/configuration."""
import argparse,json,os,re,subprocess,sys,tempfile,urllib.request,uuid
from pathlib import Path
from release_core import ROOT,manifest,sha,write,load
from release_context import context
from receipts import identity
p=argparse.ArgumentParser();p.add_argument('--sut-name',choices=['sut-python','sut-node'],required=True);p.add_argument('--sut',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();sut=a.sut.resolve();baseline,bsha=manifest('baseline');candidate,csha=manifest();name=a.sut_name;execution=identity(context(os.environ.get('QA_REPRODUCE_BUNDLE','')))
project='rollback-'+name+'-'+os.environ['GITHUB_RUN_ID']+'-'+os.environ['GITHUB_RUN_ATTEMPT'];override=Path(os.environ['RUNNER_TEMP'])/'rollback-override.json';compose=['docker','compose','--project-name',project,'-f',str(sut/'compose.yaml'),'-f',str(override)]
def run(args,**kw):return subprocess.run(args,cwd=sut,check=True,**kw)
def capture(args):return subprocess.check_output(args,cwd=sut,text=True).strip()
def fingerprint():
 row=subprocess.check_output(compose+['exec','-T','db','psql','-U','qa','-d','qa','-Atc','SELECT row_to_json(u)::text FROM users u WHERE baseline'],cwd=sut)
 assert row.strip();count=capture(compose+['exec','-T','db','psql','-U','qa','-d','qa','-Atc','SELECT count(*) FROM users WHERE baseline']);assert count=='1'
 import hashlib
 return hashlib.sha256(row).hexdigest()
def api_contract():
 fixture=json.loads((sut/'contracts/data/baseline.json').read_text());u=fixture['users'][0];identity=uuid.uuid4().hex;base='http://localhost:'+('8001'if name=='sut-python'else'8002')
 variables={'base_url':base+'/api','baseline_email':u['email'],'baseline_username':u['username'],'baseline_password':u['password'],'registration_username':'qa_'+identity,'registration_email':'qa.'+identity+'@example.test','registration_password':fixture['registration_identity']['password'],'invalid_password':fixture['invalid_login_password']}
 with tempfile.NamedTemporaryFile(mode='w',prefix='hurl-synthetic-',delete=True)as f:
  f.write('\n'.join(k+'='+v for k,v in variables.items())+'\n');f.flush();os.chmod(f.name,0o600)
  hurl=Path(os.environ['QA_HURL_BINARY']);assert sha(hurl)==load('assets.json')['hurl']['binary_sha256']
  result=subprocess.run([str(hurl),'--test','--variables-file',f.name,str(sut/'contracts/api/auth.hurl')],cwd=sut,capture_output=True,text=True)
  assert result.returncode==0,'Pinned Hurl authentication contract failed'
 for path,expected in candidate['configuration'][name]['frontend']['files'].items():
  import hashlib
  with urllib.request.urlopen(base+'/'+path if path!='index.html'else base+'/login',timeout=10)as response:data=response.read()
  assert hashlib.sha256(data).hexdigest()==expected
 return True
phases=[]
try:
 run([sys.executable,str(sut/'tools/configure.py')]);config=sha(sut/'.env')
 for phase,m in [('baseline',baseline),('candidate',candidate),('rollback',baseline)]:
  image=m['images'][name];run(['docker','pull',image['registry_digest']]);write(override,{'services':{'app':{'image':image['registry_digest']}}});run(compose+['up','-d','--no-build','--wait','--wait-timeout','150'])
  app=capture(compose+['ps','-q','app']);db=capture(compose+['ps','-q','db']);actual=capture(['docker','inspect','--format','{{.Image}}',app]).removeprefix('sha256:');assert actual==image['config_id'];assert sha(sut/'.env')==config
  labels=json.loads(capture(['docker','inspect','--format','{{json .Config.Labels}}',app]));assert labels['org.opencontainers.image.revision']==m['repositories'][name]
  row=fingerprint();assert not phases or row==phases[0]['baseline_row_sha256'];assert not phases or db==phases[0]['database_container']
  assert api_contract()
  phases.append({'phase':phase,'registry_digest':image['registry_digest'],'image_id':actual,'app_container':app,'database_container':db,'baseline_row_sha256':row,'runtime_config_sha256':config,'hurl_7_requests':'PASS','unauthenticated_user_401':'PASS','served_frontend_hashes':'PASS'})
 assert phases[0]['image_id']!=phases[1]['image_id']and phases[2]['image_id']==phases[0]['image_id']
 write(a.output,{**execution,'status':'PASS','sut':name,'baseline_manifest_sha256':bsha,'candidate_manifest_sha256':csha,'phases':phases,'scope':'Image-artifact rollback against unchanged application schema; no schema-migration rollback is claimed'})
 print('PASS: baseline -> candidate -> baseline, same database/baseline/config',name)
finally:
 if override.exists():subprocess.run(compose+['down','--volumes','--remove-orphans'],cwd=sut,check=True)
