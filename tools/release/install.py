"""Install and verify the frozen Linux QA toolchain in disposable release environments."""
from pathlib import Path
import argparse,contextlib,hashlib,http.server,json,os,platform,shutil,subprocess,sys,tarfile,threading,urllib.request,zipfile
from release_core import ROOT,load,manifest,sha,write

def fetch(key,root):
 value=load('assets.json')[key];suffix='.tar.gz'if key=='hurl'else'.tar.xz'if key=='node'else'.zip';p=root/(key+suffix)
 if not p.exists():
  request=urllib.request.Request(value['url'],headers={'User-Agent':'cypress/16.3.0'})
  with urllib.request.urlopen(request,timeout=60)as source,p.open('wb')as target:shutil.copyfileobj(source,target)
 assert sha(p)==value['sha256'],'Downloaded asset digest differs'
 return p

def extract(key,archive,root):
 target=root/key;target.mkdir(parents=True,exist_ok=True)
 if str(archive).endswith('.zip'):
  with zipfile.ZipFile(archive)as z:
   for info in z.infolist():
    path=target/info.filename;assert path.resolve().is_relative_to(target.resolve());z.extract(info,target)
    if not info.is_dir() and info.external_attr>>16&0o111:path.chmod(0o755)
 else:
  with tarfile.open(archive)as t:t.extractall(target,filter='data')
 value=load('assets.json')[key];binary=target/value['binary'];assert sha(binary)==value['binary_sha256'];binary.chmod(0o755)
 return binary

def package_fingerprint(python,lock):
 output=subprocess.check_output([str(python),'-m','pip','freeze','--all'],text=True)
 def normalize(s):return s.lower().replace('_','-').replace('.','-')
 expected={normalize(line.split('==')[0]):line.split('==')[1].split()[0]for line in lock.read_text().splitlines()if line and not line.startswith('#')}
 actual={normalize(line.split('==')[0]):line.split('==')[1]for line in output.splitlines()if '=='in line}
 assert actual==expected, 'Installed distributions differ from the frozen lock'
 return hashlib.sha256(output.encode()).hexdigest()

def install(driver,runner,output):
 m,_=manifest();assert platform.system()=='Linux'and platform.machine()in ('x86_64','amd64')
 assert sys.version.split()[0]==m['toolchain']['python']
 host=Path('/etc/os-release').read_text();assert 'VERSION_ID="24.04"'in host
 output=output.resolve();assert not output.exists(),'Fresh tool directory required';output.mkdir(parents=True)
 feature_packages=package_fingerprint(Path(sys.executable),ROOT/'tools/release/locks/features.txt')
 binaries={};paths=[];envfile=Path(os.environ['GITHUB_ENV']);pathfile=Path(os.environ['GITHUB_PATH'])
 hurl=extract('hurl',fetch('hurl',output),output);paths.append(str(hurl.parent));binaries['hurl']=sha(hurl)
 with envfile.open('a')as f:f.write(f'QA_HURL_BINARY={hurl}\n')
 if driver=='selenium':
  chrome=extract('chrome',fetch('chrome',output),output);driverbin=extract('chromedriver',fetch('chromedriver',output),output)
  sandbox=next((p for p in chrome.parent.iterdir()if p.name in ('chrome_sandbox','chrome-sandbox')),None)
  if sandbox:
   subprocess.run(['sudo','chown','root:root',str(sandbox)],check=True);subprocess.run(['sudo','chmod','4755',str(sandbox)],check=True)
   with envfile.open('a')as f:f.write(f'CHROME_DEVEL_SANDBOX={sandbox}\n')
  with envfile.open('a')as f:f.write(f'QA_CHROME_BINARY={chrome}\nQA_CHROMEDRIVER={driverbin}\n')
  binaries.update(chrome=sha(chrome),chromedriver=sha(driverbin))
 if driver=='playwright':
  mirror={Path(load('assets.json')[k]['url']).name:fetch(k,output)for k in ['playwright-shell','playwright-ffmpeg']}
  class Handler(http.server.BaseHTTPRequestHandler):
   def do_GET(self):
    p=mirror.get(Path(self.path).name)
    if not p:self.send_error(404);return
    self.send_response(200);self.send_header('Content-Length',str(p.stat().st_size));self.end_headers()
    with p.open('rb')as source:shutil.copyfileobj(source,self.wfile)
   def log_message(self,*args):pass
  server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  cache=Path(os.environ['PLAYWRIGHT_BROWSERS_PATH']);assert not cache.exists(),'Fresh Playwright cache required'
  env=dict(os.environ,PLAYWRIGHT_DOWNLOAD_HOST=f'http://127.0.0.1:{server.server_address[1]}')
  try:subprocess.run([str(runner/'.venv/bin/python'),'-m','playwright','install','--with-deps','--only-shell','chromium'],env=env,check=True)
  finally:server.shutdown();thread.join()
  for key in ['playwright-shell','playwright-ffmpeg']:
   value=load('assets.json')[key];matches=[p for p in cache.rglob(Path(value['binary']).name)if p.is_file()];assert len(matches)==1 and sha(matches[0])==value['binary_sha256'];binaries[key]=sha(matches[0])
 if driver=='cypress':
  node=extract('node',fetch('node',output),output);paths.append(str(node.parent));env=dict(os.environ,PATH=str(node.parent)+os.pathsep+os.environ['PATH'])
  subprocess.run([str(node.parent/'npm'),'ci','--ignore-scripts','--no-audit','--no-fund'],cwd=runner,env=env,check=True)
  cache=Path(os.environ['CYPRESS_CACHE_FOLDER']);assert not cache.exists(),'Fresh Cypress cache required'
  archive=fetch('cypress',output);env['CYPRESS_INSTALL_BINARY']=str(archive)
  subprocess.run([str(node),str(runner/'node_modules/cypress/bin/cypress'),'install'],cwd=runner,env=env,check=True)
  value=load('assets.json')['cypress'];binary=cache/m['toolchain']['cypress']/value['binary'];assert sha(binary)==value['binary_sha256'];binaries.update(node=sha(node),cypress=sha(binary))
  subprocess.run([str(node),str(runner/'tools/typecheck.cjs')],cwd=runner,env=env,check=True)
 with pathfile.open('a')as f:
  for p in paths:f.write(p+'\n')
 packages=package_fingerprint(runner/'.venv/bin/python',ROOT/'tools/release/locks/qa-python.txt')if driver in ('playwright','selenium')else None
 record={'driver':driver,'binaries':binaries,'python':sys.version.split()[0],'packages_sha256':packages,'feature_packages_sha256':feature_packages,'host':{'ImageOS':os.environ.get('ImageOS'),'ImageVersion':os.environ.get('ImageVersion'),'uname':platform.platform()},'fresh_tool_cache':True}
 write(Path(os.environ['RUNNER_TEMP'])/'release-toolchain.json',record);print('PASS: installed binaries and dependency locks verified',driver)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--driver',choices=['playwright','selenium','cypress','api'],required=True);p.add_argument('--runner',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();install(a.driver,a.runner.resolve(),a.output)
