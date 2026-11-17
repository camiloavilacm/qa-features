"""Verify smoke/rollback evidence and assemble a secret-free immutable release payload."""
import argparse,json,os,shutil,sys
from pathlib import Path
from release_core import ROOT,manifest,load,sha,write,governance
sys.path.insert(0,str(ROOT/'tools/tracker'));from tracker import validate_campaign
p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);p.add_argument('--inbox',type=Path,required=True);p.add_argument('--rollback',type=Path,required=True);p.add_argument('--baseline',required=True);p.add_argument('--payload',type=Path,required=True);a=p.parse_args()
m,digest=manifest();base,bsha=manifest('baseline');context=json.loads((a.directory/'provenance.json').read_text())['expected'];campaign=json.loads((a.directory/'campaign.json').read_text());validate_campaign(campaign,a.directory/'artifacts',m['feature_ref'])
assert campaign['status']=='passed' and len(campaign['slots'])==6 and sum(len(s['result']['scenarios'])for s in campaign['slots'])==18
assert context['release_manifest_sha256']==digest and context['images']==m['images'] and context['tooling_ref']==os.environ['GITHUB_SHA']
rollback={};toolchains={};configurations={};assets=load('assets.json')
for slot in campaign['slots']:
 identity=slot['slot_id'];sut,driver=identity.split(':');source=a.inbox/(f'slot-{context["attempt"]}-'+identity.replace(':','-'))
 tool=json.loads((source/'toolchain.json').read_text());configuration=json.loads((source/'configuration.json').read_text());assert tool['driver']==driver and tool['fresh_tool_cache'] and tool['python']==m['toolchain']['python']
 for key,value in tool['binaries'].items():assert value==assets[key]['binary_sha256']
 required={'hurl','node','cypress'}if driver=='cypress'else{'hurl','chrome','chromedriver'}if driver=='selenium'else{'hurl','playwright-shell','playwright-ffmpeg'}
 assert set(tool['binaries'])==required and tool['feature_packages_sha256']
 assert configuration['source_file_hashes']==m['configuration'][sut]['files'] and configuration['release_manifest_sha256']==digest and not configuration['secret_values_exported']
 toolchains[identity]=tool;configurations[identity]=configuration
for sut in ['sut-python','sut-node']:
 record=json.loads((a.rollback/('rollback-'+sut)/'rollback.json').read_text());assert record['status']=='PASS'and record['sut']==sut and record['baseline_manifest_sha256']==bsha and record['candidate_manifest_sha256']==digest
 phases=record['phases'];assert [v['phase']for v in phases]==['baseline','candidate','rollback']
 assert [v['image_id']for v in phases]==[base['images'][sut]['config_id'],m['images'][sut]['config_id'],base['images'][sut]['config_id']]
 assert len({v['runtime_config_sha256']for v in phases})==len({v['baseline_row_sha256']for v in phases})==len({v['database_container']for v in phases})==1
 assert all(v['hurl_7_requests']==v['unauthenticated_user_401']==v['served_frontend_hashes']=='PASS'for v in phases);rollback[sut]=record
record={'schema_version':'1.0','release_status':'verified','kind':'synthetic-smoke','manifest_sha256':digest,'baseline_manifest_sha256':bsha,'release_tooling_ref':os.environ['GITHUB_SHA'],'run_id':int(os.environ['GITHUB_RUN_ID']),'attempt':int(os.environ['GITHUB_RUN_ATTEMPT']),'reproduction_bundle':context.get('reproduction_bundle'),'previous_bundle':a.baseline,'image_digests':m['images'],'qa_campaign_sha256':sha(a.directory/'campaign.json'),'qa_scenarios_passed':18,'rollback':rollback,'toolchains':toolchains,'configuration':configurations,'development_harness':governance(),'secret_values_exported':False,'production_deployment':False}
write(a.directory/'release-record.json',record)
assert not a.payload.exists();a.payload.mkdir(parents=True)
for name in ['baseline.json','candidate.json','assets.json','README.md']:shutil.copyfile(ROOT/'tools/release'/name,a.payload/name)
shutil.copytree(ROOT/'tools/release/locks',a.payload/'locks');shutil.copytree(a.directory,a.payload/'evidence');shutil.copyfile(a.directory/'release-record.json',a.payload/'release-record.json')
write(a.payload/'previous.json',{'bundle':a.baseline,'manifest_sha256':bsha,'role':'baseline'})
print('PASS: 18 smoke scenarios, both actual rollback sequences, toolchain/configuration/harness provenance')
