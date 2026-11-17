"""Content-addressed synthetic smoke release metadata; no deployment of production data."""
from pathlib import Path
import hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/campaign'))
from aggregate import write

def sha(path):
 with Path(path).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':')).encode()
def load(name):return json.loads((ROOT/'tools/release'/name).read_text())
def manifest(name='candidate'):
 path=ROOT/'tools/release'/f'{name}.json';value=json.loads(path.read_text())
 assert value['schema_version']=='1.0' and value['kind']=='synthetic-smoke' and value['platform']=='linux/amd64'
 assert value['feature_ref']=='12a55fb4b9312303378af72f96a28734b6b9ec9a'
 assert sha(ROOT/'tools/release/assets.json')==value['assets_sha256']
 for name,expected in value['lock_hashes'].items():assert sha(ROOT/name)==expected
 for name,expected in value['approved_contract_hashes'].items():
  data=subprocess.check_output(['git','-C',str(ROOT),'show',value['feature_ref']+':'+name]);assert hashlib.sha256(data).hexdigest()==expected
 return value,sha(path)
def governance():
 names=[]
 for directory in ['harness/scripts','harness/config','harness/schemas','.agents','.codex','.claude']:
  names.extend(p for p in (ROOT/directory).rglob('*')if p.is_file()and '__pycache__'not in p.parts)
 values={str(p.relative_to(ROOT)):sha(p)for p in sorted(names)}
 return {'files':values,'sha256':hashlib.sha256(canonical(values)).hexdigest()}
