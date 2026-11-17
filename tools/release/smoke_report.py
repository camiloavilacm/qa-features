"""Update one smoke-attempt report even when evidence collection or publication fails."""
import argparse,json,os,sys
from pathlib import Path
from release_core import ROOT,manifest,write
from receipts import identity,require_upstream
sys.path.insert(0,str(ROOT/'tools/tracker'))
from tracker import publish,render,marker,validate_campaign,GitHub

def build_report(directory, env):
    m,digest=manifest()
    execution=identity({'campaign_id':'smoke-gh-'+env['GITHUB_REPOSITORY_ID']+'-'+env['GITHUB_RUN_ID'],'run_id':int(env['GITHUB_RUN_ID']),'attempt':int(env['GITHUB_RUN_ATTEMPT']),'tooling_ref':env['GITHUB_SHA']})
    repo=env['GITHUB_REPOSITORY'];issue=int(env['QA_REPORT_ISSUE']);campaign=None;qa_status='not_run'
    try:
        value=json.loads((directory/'campaign.json').read_text())
        validate_campaign(value,directory/'artifacts',m['feature_ref'])
        if value['campaign_id']!=execution['campaign_id']:raise ValueError('Campaign identity differs')
        provenance=json.loads((directory/'provenance.json').read_text())['expected']
        if any(provenance.get(k)!=v for k,v in execution.items()):raise ValueError('Campaign attempt differs')
        campaign=value;qa_status=value['status']
    except (OSError,ValueError,KeyError,TypeError):
        if (directory/'campaign.json').exists():qa_status='error'
    upstream={key:env.get('QA_UPSTREAM_'+key.upper(),'unknown') for key in ('baseline','qa','rollback')}
    verification=env.get('QA_RELEASE_VERIFICATION','unknown');publication=env.get('QA_BUNDLE_PUBLICATION','unknown');verified=False;bundle=None
    try:
        require_upstream(upstream)
        if verification!='success' or publication!='success' or qa_status!='passed':raise ValueError('Release did not pass')
        record=json.loads((directory/'release-record.json').read_text());published=json.loads((directory/'published.json').read_text())
        if any(record.get({'tooling_ref':'release_tooling_ref'}.get(k,k))!=v for k,v in execution.items()):raise ValueError('Release execution differs')
        if record.get('release_status')!='verified' or record.get('manifest_sha256')!=digest or published.get('manifest_sha256')!=digest or published.get('release_tooling_ref')!=execution['tooling_ref']:raise ValueError('Release provenance differs')
        bundle=published['bundle'];verified=True
    except (OSError,ValueError,KeyError,TypeError):pass
    status='verified' if verified else 'failed'
    lines=[marker(repo,issue,execution['campaign_id']),'### Synthetic smoke release attempt', '',f'Release outcome: **{status}**',f'Attempt: **{execution["attempt"]}**',f'QA outcome: **{qa_status}**',f'Tooling: `{execution["tooling_ref"]}`',f'Run: https://github.com/{repo}/actions/runs/{execution["run_id"]}/attempts/{execution["attempt"]}', '', 'Upstream jobs: '+', '.join(key+'='+value for key,value in upstream.items()),f'Release verification: {verification}; bundle publication: {publication}.','']
    if verified:lines += ['Verified immutable synthetic smoke bundle: `'+bundle+'`.','Both execution-bound rollback sequences passed.']
    else:lines += ['This attempt did not produce a verified smoke release. Earlier passing attempts do not establish success for this attempt.']
    if campaign:
        lines += ['',render(campaign,repo,issue).split('\n',1)[1]]
    else:lines += ['','Current-attempt QA evidence is unavailable or invalid; no passing scenarios are claimed.']
    lines += ['','No production deployment or issue status transition is requested.','']
    return {'campaign_id':execution['campaign_id']},'\n'.join(lines),{**execution,'release_status':status,'qa_status':qa_status,'upstream':upstream,'verification':verification,'bundle_publication':publication,'bundle':bundle}

def main():
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);a=p.parse_args()
    campaign,body,status=build_report(a.directory,os.environ)
    receipt=publish(campaign,os.environ['GITHUB_REPOSITORY'],int(os.environ['QA_REPORT_ISSUE']),body,GitHub())
    write(a.directory/'report-status.json',status);write(a.directory/'publication.json',receipt);(a.directory/'smoke-report.md').write_text(body)
    print(receipt['comment_url'])
if __name__=='__main__':main()
