"""Publish one validated report to an explicitly selected existing issue."""
import argparse,json,sys
from pathlib import Path
from aggregate import write
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tracker'))
from tracker import validate_campaign,render,publish,GitHub
p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);p.add_argument('--repository',required=True);p.add_argument('--issue',type=int,required=True);a=p.parse_args()
try:
 expected=json.loads((a.directory/'provenance.json').read_text())['expected'];value=validate_campaign(json.loads((a.directory/'campaign.json').read_text()),a.directory/'artifacts',expected['feature_ref'])
 body=render(value,a.repository,a.issue)+'Development verification campaign; this is not a smoke release.\n'
 result=publish(value,a.repository,a.issue,body,GitHub());write(a.directory/'publication.json',result);print(json.dumps(result,sort_keys=True))
except Exception:print('Campaign publication could not be verified',file=sys.stderr);raise SystemExit(1)
