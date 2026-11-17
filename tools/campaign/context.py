"""Build an attempt context from pinned repository/image metadata, never caller labels alone."""
import json,os,re
from pathlib import Path
from aggregate import write
ROOT=Path(__file__).resolve().parents[2]
def context():
 lock=json.loads((ROOT/'tools/campaign/repositories.json').read_text());run=os.environ['GITHUB_RUN_ID'];attempt=int(os.environ['GITHUB_RUN_ATTEMPT']);tooling=os.environ['GITHUB_SHA']
 assert re.fullmatch('[a-f0-9]{40}',tooling)and run.isdigit()and attempt>0
 images={}
 for sut,key in [('sut-python','PYTHON'),('sut-node','NODE')]:
  image=os.environ.get('QA_'+key+'_IMAGE','');config=os.environ.get('QA_'+key+'_CONFIG','')
  if image and config:
   assert re.fullmatch('[a-f0-9]{64}',config)and re.fullmatch(r'ghcr.io/[a-z0-9_./-]+@sha256:[a-f0-9]{64}',image)
   images[sut]={'registry_digest':image,'config_id':config}
 return {'campaign_id':'gh-'+os.environ['GITHUB_REPOSITORY_ID']+'-'+run,'attempt':attempt,'feature_ref':lock['feature_ref'],'tooling_ref':tooling,'repositories':lock['repositories'],'runner_fingerprints':lock['runner_fingerprints'],'images':images,'observer_fault':os.environ.get('QA_OBSERVER_VALIDATION','none'),'report_repository':os.environ['GITHUB_REPOSITORY'],'report_issue':int(os.environ.get('QA_REPORT_ISSUE','0'))}
if __name__=='__main__':write(Path(os.environ.get('QA_CONTEXT','context.json')),context())
