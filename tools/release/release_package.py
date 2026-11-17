"""Publish content-addressed, private release bundles without creating Git tags."""
from pathlib import Path
import argparse,hashlib,json,os,shutil,subprocess,tempfile
from release_core import ROOT,canonical,sha,write

def seal(directory,role,manifest_sha):
 files={str(p.relative_to(directory)):sha(p)for p in sorted(directory.rglob('*'))if p.is_file()and p!=directory/'payload.json'}
 for p in directory.rglob('*'):assert not p.is_symlink()
 value={'schema_version':'1.0','role':role,'manifest_sha256':manifest_sha,'release_tooling_ref':os.environ['GITHUB_SHA'],'files':files};write(directory/'payload.json',value);return sha(directory/'payload.json')

def verify_payload(directory):
 assert all(not p.is_symlink()for p in directory.rglob('*'))
 value=json.loads((directory/'payload.json').read_text());assert value['schema_version']=='1.0'
 actual={str(p.relative_to(directory))for p in directory.rglob('*')if p.is_file()and p!=directory/'payload.json'};assert actual==set(value['files'])
 for name,expected in value['files'].items():
  path=directory/name;assert path.resolve().is_relative_to(directory.resolve())and not path.is_symlink()and sha(path)==expected
 return value

def publish_bundle(directory,role,manifest_sha):
 payload_sha=seal(directory,role,manifest_sha);owner=os.environ['GITHUB_REPOSITORY_OWNER'].lower();tag=f'ghcr.io/{owner}/qa-smoke-release:{role}-{payload_sha}'
 with tempfile.TemporaryDirectory(prefix='smoke-package-')as temp:
  dockerfile=Path(temp)/'Dockerfile';dockerfile.write_text('FROM scratch\nCOPY . /release/\n')
  subprocess.run(['docker','build','-f',str(dockerfile),'--label','org.opencontainers.image.source=https://github.com/'+os.environ['GITHUB_REPOSITORY'],'--label','org.opencontainers.image.revision='+os.environ['GITHUB_SHA'],'--label','io.qa.manifest.sha256='+manifest_sha,'--label','io.qa.payload.sha256='+payload_sha,'-t',tag,str(directory)],check=True)
 subprocess.run(['docker','push',tag],check=True)
 image=subprocess.check_output(['docker','image','inspect','--format','{{index .RepoDigests 0}}',tag],text=True).strip()
 assert '@sha256:'in image
 return {'bundle':image,'manifest_sha256':manifest_sha,'payload_sha256':payload_sha,'release_tooling_ref':os.environ['GITHUB_SHA'],'role':role}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);p.add_argument('--role',choices=['baseline','candidate'],required=True);p.add_argument('--manifest-sha',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();value=publish_bundle(a.directory.resolve(),a.role,a.manifest_sha);write(a.output,value)
 if os.environ.get('GITHUB_OUTPUT'):
  with open(os.environ['GITHUB_OUTPUT'],'a')as f:f.write('bundle='+value['bundle']+'\n')
 print('Published immutable private bundle',value['bundle'])
