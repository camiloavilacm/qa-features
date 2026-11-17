"""Publish the verified smoke artifact report to the selected private issue."""
import argparse,json,os,sys
from pathlib import Path
from release_core import ROOT,write
sys.path.insert(0,str(ROOT/'tools/tracker'));from tracker import publish,render,GitHub
p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);a=p.parse_args()
record=json.loads((a.directory/'release-record.json').read_text());published=json.loads((a.directory/'published.json').read_text());campaign=json.loads((a.directory/'campaign.json').read_text());assert record['release_status']=='verified'and published['manifest_sha256']==record['manifest_sha256']
repo=os.environ['GITHUB_REPOSITORY'];issue=int(os.environ['QA_REPORT_ISSUE']);body=render(campaign,repo,issue)+'\nVerified immutable **synthetic smoke** artifact. No production deployment.\n\nManifest SHA-256: `'+record['manifest_sha256']+'`\n\nBundle: `'+published['bundle']+'`\n\nRollback: both SUTs restored the baseline image while preserving configuration and baseline data.\n'
body+='\nMode: '+('independent clean-machine reproduction from the prior bundle.'if record['reproduction_bundle']else'initial smoke and rollback validation; independent reproduction is a separate gate.')+'\n'
receipt=publish(campaign,repo,issue,body,GitHub());write(a.directory/'publication.json',receipt);print(receipt['comment_url'])
