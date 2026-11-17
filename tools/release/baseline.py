"""Establish the first immutable baseline from previously verified Step 6 evidence."""
import argparse,json,os,shutil,subprocess,tempfile,sys
from pathlib import Path
from release_core import ROOT,manifest,sha,write
from context import pull_bundle
from release_package import publish_bundle
sys.path.insert(0,str(ROOT/'tools/tracker'));from tracker import validate_campaign
p=argparse.ArgumentParser();p.add_argument('--reproduce-bundle',default='');p.add_argument('--output',type=Path,required=True);a=p.parse_args();base,digest=manifest('baseline')
with tempfile.TemporaryDirectory(prefix='establish-smoke-baseline-')as temp:
 root=Path(temp);payload=root/'payload';payload.mkdir()
 if a.reproduce_bundle:
  candidate=root/'candidate';candidate.mkdir();pull_bundle(a.reproduce_bundle,candidate);previous=json.loads((candidate/'previous.json').read_text());baseline=root/'baseline';baseline.mkdir();pull_bundle(previous['bundle'],baseline)
  assert sha(baseline/'baseline.json')==digest
  value=previous
 else:
  evidence=payload/'evidence';subprocess.run(['gh','run','download',str(base['origin']['run_id']),'--repo',os.environ['GITHUB_REPOSITORY'],'--name',base['origin']['artifact'],'--dir',str(evidence)],check=True)
  campaign=json.loads((evidence/'campaign.json').read_text());expected=json.loads((evidence/'provenance.json').read_text())['expected'];assert campaign['status']=='passed'and expected['attempt']==base['origin']['attempt']and expected['tooling_ref']==base['origin']['tooling_ref']and expected['images']==base['images']
  validate_campaign(campaign,evidence/'artifacts',base['feature_ref']);shutil.copyfile(ROOT/'tools/release/baseline.json',payload/'baseline.json')
  value=publish_bundle(payload,'baseline',digest)
 write(a.output,value)
 with open(os.environ['GITHUB_OUTPUT'],'a')as f:f.write('bundle='+value['bundle']+'\n')
 print('PASS: immutable first-release baseline is available',value['bundle'])
