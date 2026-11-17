"""Bind a real slot result to checked-out sources and the running Docker container."""
import argparse,json,subprocess,sys
from pathlib import Path
from aggregate import digest,write
p=argparse.ArgumentParser();p.add_argument('--context',type=Path,required=True);p.add_argument('--result',type=Path,required=True);p.add_argument('--runner',type=Path,required=True);p.add_argument('--sut',type=Path,required=True);p.add_argument('--driver',required=True);p.add_argument('--container',required=True);a=p.parse_args()
try:
 expected=json.loads(a.context.read_text());value=json.loads((a.result/'results.json').read_text());slot=value['slot_id'];sut,driver=slot.split(':');family='qa-typescript'if driver=='cypress'else 'qa-python'
 def git(root):return subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
 actual=subprocess.check_output(['docker','inspect','--format','{{.Image}}',a.container],text=True).strip().removeprefix('sha256:')
 assert actual==expected['images'][sut]['config_id']==value['sut_revision']
 assert git(a.runner)==expected['repositories'][family] and git(a.sut)==expected['repositories'][sut]
 assert driver==a.driver and value['campaign_id']==expected['campaign_id'] and value['tooling_ref']==expected['tooling_ref'] and value['feature_ref']==expected['feature_ref']
 assert value['runner_revision']==expected['runner_fingerprints'][family]
 repo_digests=json.loads(subprocess.check_output(['docker','image','inspect','--format','{{json .RepoDigests}}',expected['images'][sut]['registry_digest']],text=True))
 assert expected['images'][sut]['registry_digest'] in repo_digests
 receipt={'campaign_id':expected['campaign_id'],'attempt':expected['attempt'],'slot_id':slot,'tooling_ref':expected['tooling_ref'],'runner_source_ref':git(a.runner),'sut_source_ref':git(a.sut),'sut_image_id':actual,'sut_registry_digest':expected['images'][sut]['registry_digest'],'result_sha256':digest((a.result/'results.json').read_bytes())}
 write(a.result/'receipt.json',receipt);print('PASS: actual container and checked-out source provenance',slot)
except Exception:print('Slot provenance could not be verified',file=sys.stderr);raise SystemExit(1)
