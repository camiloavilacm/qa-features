"""Prepare and execute a slot using pinned images; no development harness or model calls."""
import argparse,json,os,subprocess,sys
from pathlib import Path
from aggregate import write
p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','run','cleanup']);p.add_argument('--context',type=Path,required=True);p.add_argument('--sut-name',required=True);p.add_argument('--sut',type=Path,required=True);p.add_argument('--runner',type=Path,required=True);p.add_argument('--driver',required=True);p.add_argument('--state',type=Path,required=True);a=p.parse_args()
expected=json.loads(a.context.read_text());sut=a.sut.resolve();runner=a.runner.resolve();name=a.sut_name;project='qa-'+name+'-'+a.driver
compose=['docker','compose','--project-name',project,'-f',str(sut/'compose.yaml'),'-f',str(a.state.with_suffix('.override.json').resolve())]
def call(args,**kwargs):return subprocess.run(args,check=True,**kwargs)
if a.action=='prepare':
 image=expected['images'][name]['registry_digest'];call(['docker','pull',image]);call([sys.executable,str(sut/'tools/configure.py')],cwd=sut)
 write(a.state.with_suffix('.override.json'),{'services':{'app':{'image':image}}})
 call(compose+['up','-d','--no-build','--wait','--wait-timeout','150'],cwd=sut)
 container=subprocess.check_output(compose+['ps','-q','app'],cwd=sut,text=True).strip();assert container
 config=subprocess.check_output(['docker','inspect','--format','{{.Image}}',container],text=True).strip().removeprefix('sha256:');assert config==expected['images'][name]['config_id']
 labels=json.loads(subprocess.check_output(['docker','inspect','--format','{{json .Config.Labels}}',container],text=True));assert labels['org.opencontainers.image.revision']==expected['repositories'][name]
 write(a.state,{'container':container,'image_id':config});print('PASS: pinned image is running',name)
elif a.action=='run':
 directory=runner/'reports/slot';base='http://localhost:'+('8001'if name=='sut-python'else'8002');env=dict(os.environ,QA_TOOLING_REF=expected['tooling_ref'])
 if a.driver=='cypress':
  env.update(QA_SUT=name,QA_RESULT_DIR=str(directory),QA_CAMPAIGN_ID=expected['campaign_id']);env['QA_'+name.upper().replace('-','_')+'_REVISION']=expected['images'][name]['config_id']
  cmd=['node','tools/run.cjs']
 else:cmd=[str(runner/'.venv/bin/python'),'-m','pytest','--driver',a.driver,'--sut',name,'--base-url',base,'--sut-revision',expected['images'][name]['config_id'],'--tooling-ref',expected['tooling_ref'],'--campaign-id',expected['campaign_id'],'--result-dir',str(directory)]
 process=subprocess.run(cmd,cwd=runner,env=env,timeout=300);raise SystemExit(process.returncode)
else:
 if a.state.with_suffix('.override.json').exists():subprocess.run(compose+['down','--volumes','--remove-orphans'],cwd=sut,check=True)
