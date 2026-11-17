"""Bind a smoke attempt to its frozen release manifest and optional reproduction bundle."""
import argparse,json,os,re,subprocess,tempfile
from pathlib import Path
from release_core import ROOT,manifest,sha,write

def pull_bundle(image,destination):
 assert re.fullmatch(r'ghcr.io/camiloavilacm/qa-smoke-release@sha256:[a-f0-9]{64}',image),'Immutable release bundle digest required'
 subprocess.run(['docker','pull',image],check=True)
 cid=subprocess.check_output(['docker','create',image,'/not-executed'],text=True).strip()
 try:subprocess.run(['docker','cp',cid+':/release/.',str(destination)],check=True)
 finally:subprocess.run(['docker','rm',cid],check=True,capture_output=True)
 from release_package import verify_payload
 verify_payload(destination)

def context(bundle=''):
 m,digest=manifest();origin=None
 if bundle:
  with tempfile.TemporaryDirectory(prefix='release-reproduction-')as temp:
   pull_bundle(bundle,Path(temp));p=Path(temp);assert sha(p/'candidate.json')==digest
   origin=json.loads((p/'release-record.json').read_text());assert origin['release_status']=='verified'and origin['release_tooling_ref']==os.environ['GITHUB_SHA'];assert origin['manifest_sha256']==digest
 run=os.environ['GITHUB_RUN_ID'];attempt=int(os.environ['GITHUB_RUN_ATTEMPT']);tooling=os.environ['GITHUB_SHA'];assert re.fullmatch('[a-f0-9]{40}',tooling)
 return {'campaign_id':'smoke-gh-'+os.environ['GITHUB_REPOSITORY_ID']+'-'+run,'attempt':attempt,'feature_ref':m['feature_ref'],'tooling_ref':tooling,'repositories':m['repositories'],'runner_fingerprints':m['runner_fingerprints'],'images':m['images'],'report_repository':os.environ['GITHUB_REPOSITORY'],'report_issue':int(os.environ.get('QA_REPORT_ISSUE','2')),'release_manifest_sha256':digest,'reproduction_bundle':bundle or None,'previous_bundle':os.environ.get('QA_BASELINE_BUNDLE',''),'kind':'immutable-synthetic-smoke','observer_fault':'none'}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--bundle',default='');p.add_argument('--output',type=Path,default=Path('context.json'));a=p.parse_args();write(a.output,context(a.bundle))
