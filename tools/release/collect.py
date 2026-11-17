"""Retain measured QA toolchain and non-secret application configuration provenance."""
import argparse,json,os,shutil,subprocess,sys
from pathlib import Path
from release_core import ROOT,manifest,sha,write,load
p=argparse.ArgumentParser();p.add_argument('--context',type=Path,required=True);p.add_argument('--result',type=Path,required=True);p.add_argument('--runner',type=Path,required=True);p.add_argument('--sut',type=Path,required=True);p.add_argument('--driver',required=True);p.add_argument('--container',required=True);a=p.parse_args()
subprocess.run([sys.executable,str(ROOT/'tools/campaign/collect.py'),'--context',str(a.context),'--result',str(a.result),'--runner',str(a.runner),'--sut',str(a.sut),'--driver',a.driver,'--container',a.container],check=True)
if a.driver=='cypress':assert sha(Path(shutil.which('node')))==load('assets.json')['node']['binary_sha256']
m,digest=manifest();value=json.loads((a.result/'results.json').read_text());name=value['slot_id'].split(':')[0]
for path,expected in m['configuration'][name]['files'].items():assert sha(a.sut/path)==expected
shutil.copyfile(Path(os.environ['RUNNER_TEMP'])/'release-toolchain.json',a.result/'toolchain.json')
write(a.result/'configuration.json',{'source_ref':m['repositories'][name],'source_file_hashes':m['configuration'][name]['files'],'runtime_config_sha256':sha(a.sut/'.env'),'release_manifest_sha256':digest,'secret_values_exported':False})
