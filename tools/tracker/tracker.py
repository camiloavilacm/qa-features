"""Deterministic campaign validation and comment-only GitHub publishing."""
from __future__ import annotations
import argparse, datetime as dt, fcntl, hashlib, html, json, os, re, subprocess, sys, tempfile
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
ROOT = Path(__file__).resolve().parents[2]
REQUIRED = {'AC-1': {('POST','/users',201,False),('GET','/user',200,True)}, 'AC-2': {('POST','/users/login',200,False),('GET','/user',200,True)}, 'AC-3': {('POST','/users/login',422,False)}}
class TrackerError(ValueError): pass

def canonical(value): return json.dumps(value,sort_keys=True,separators=(',',':')).encode()
def digest(value): return hashlib.sha256(value).hexdigest()
def require(condition,message):
    if not condition: raise TrackerError(message)
def approved_ref():
    return subprocess.check_output(['git','-C',str(ROOT),'rev-parse','seed-1-approved-v1^{commit}'],text=True).strip()
def schema(name,ref):
    return json.loads(subprocess.check_output(['git','-C',str(ROOT),'show',ref+':schemas/'+name+'.schema.json']))
def validate_campaign(campaign,artifacts,feature_ref=None):
    ref=feature_ref or approved_ref()
    require(re.fullmatch(r'[a-f0-9]{40}([a-f0-9]{24})?',ref),'Immutable feature revision required')
    result_schema=schema('results',ref)
    registry=Registry().with_resource('results.schema.json',Resource.from_contents(result_schema))
    try: Draft202012Validator(schema('campaign',ref),registry=registry,format_checker=FormatChecker()).validate(campaign)
    except Exception: raise TrackerError('Campaign does not match the approved schema') from None
    require(campaign['feature_ref']==ref,'Campaign feature revision differs')
    require(not re.search(r'eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+',campaign['campaign_id']),'Sensitive campaign identity rejected')
    roots=Path(artifacts).resolve();require(roots.is_dir(),'Artifact root must be a directory')
    statuses=[];executions=set();tooling=set();runners={};suts={}
    for slot in campaign['slots']:
        value=slot['result']
        if value is None: statuses.append('missing'); continue
        require(value['slot_id']==slot['slot_id'],'Nested slot mismatch')
        for key in ('issue_id','campaign_id','feature_ref'): require(value[key]==campaign[key],'Nested campaign metadata differs')
        require(value['execution_id'] not in executions,'Duplicate execution identity');executions.add(value['execution_id'])
        sut,driver=slot['slot_id'].split(':');runner='typescript' if driver=='cypress' else 'python'
        for mapping,key,revision in ((suts,sut,value['sut_revision']),(runners,runner,value['runner_revision'])):
            require(key not in mapping or mapping[key]==revision,'Mixed revisions within one campaign');mapping[key]=revision
        tooling.add(value['tooling_ref'])
        started,finished=(dt.datetime.fromisoformat(value[k].replace('Z','+00:00')) for k in ('started_at','finished_at'))
        require(started.tzinfo is not None and finished.tzinfo is not None and started<=finished,'Invalid result time ordering')
        priority=next(s for s in ('error','failed','not_run','passed') if any(row['status']==s for row in value['scenarios']))
        require(value['status']==priority,'Result outcome disagrees with scenarios');statuses.append(priority)
        for row in value['scenarios']:
            observer=row['observer']
            if observer['state']=='complete' or row['status']=='passed':
                events={(e['method'],e['path'],e['status'],e['authorization_present']) for e in observer['events']}
                require(observer['state']=='complete' and REQUIRED[row['id']]<=events,'Complete observation lacks required events')
            for item in row['artifacts']:
                # Artifact paths are relative to an explicit per-slot directory, never cwd.
                raw=roots/slot['slot_id'].replace(':','-')/item['path'];path=raw.resolve()
                require(path.is_relative_to(roots) and not any(p.is_symlink() for p in [raw,*raw.parents] if p!=roots.parent),'Artifact escapes its root or uses a symlink')
                require(path.is_file(),'Missing artifact');data=path.read_bytes()
                require(digest(data)==item['sha256'],'Artifact digest differs')
                require(not re.search(rb'eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+|Authorization: Token ',data),'Sensitive artifact rejected')
                if item['kind']=='network':
                    try: require(json.loads(data)==observer,'Network artifact differs from observation')
                    except json.JSONDecodeError: raise TrackerError('Invalid network artifact') from None
    require(len(tooling)<=1,'Mixed tooling revisions')
    expected='error' if 'error' in statuses else 'failed' if 'failed' in statuses else 'incomplete' if any(s in ('missing','not_run') for s in statuses) else 'passed'
    require(campaign['status']==expected,'Campaign outcome disagrees with slots')
    return campaign

def marker(repo,issue,campaign):
    return '<!-- qa-campaign:v1:'+digest(canonical([repo.lower(),issue,'SEED-1',campaign]))+' -->'
def render(campaign,repo,issue,fixture=False):
    require(re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repo) is not None and issue>0,'Repository and positive issue number required')
    title='Specification fixture — not an executed QA campaign' if fixture else 'QA campaign report'
    campaign_name=html.escape(campaign['campaign_id']).replace('@','&#64;').replace('`','&#96;').replace('\n',' ')
    lines=[marker(repo,issue,campaign['campaign_id']), '### '+title, '', 'Issue: SEED-1', 'Campaign: '+campaign_name, 'Outcome: **'+campaign['status']+'**', 'Feature: `'+campaign['feature_ref']+'`', '', '| Slot | Outcome |', '|---|---|']
    for slot in sorted(campaign['slots'],key=lambda row:row['slot_id']):lines.append('| '+slot['slot_id']+' | '+(slot['result']['status'] if slot['result'] else 'missing')+' |')
    lines+=['','Campaign input SHA-256: `'+digest(canonical(campaign))+'`','No issue status transition is requested.']
    return '\n'.join(lines)+'\n'

class GitHub:
    """Uses gh authentication; no token is read, printed or stored by this CLI."""
    def request(self,method,route,payload=None):
        args=['gh','api','--method',method,'-H','Accept: application/vnd.github+json','-H','X-GitHub-Api-Version: 2026-03-10',route]
        if payload is not None:args+=['--input','-']
        try:p=subprocess.run(args,input=None if payload is None else json.dumps(payload),capture_output=True,text=True,timeout=30)
        except subprocess.TimeoutExpired:raise TrackerError('GitHub request outcome uncertain') from None
        require(p.returncode==0,'GitHub request failed; check authentication, permission and availability')
        try:return json.loads(p.stdout)
        except json.JSONDecodeError:raise TrackerError('GitHub returned invalid JSON') from None
    def comments(self,repo,issue):
        values=[]
        for page in range(1,101):
            rows=self.request('GET',f'repos/{repo}/issues/{issue}/comments?per_page=100&page={page}')
            require(isinstance(rows,list),'Invalid comments response');values.extend(rows)
            if len(rows)<100:return values
        raise TrackerError('Comment pagination limit reached; refusing an incomplete search')

def snapshot(issue):
    require('pull_request' not in issue,'Target must be an issue, not a pull request')
    return {key:issue.get(key) for key in ('title','body','state','state_reason','labels','assignees','milestone','locked')}
def publish(campaign,repo,issue,body,api):
    key=marker(repo,issue,campaign['campaign_id'])
    actor=api.request('GET','user')['id']
    before=snapshot(api.request('GET',f'repos/{repo}/issues/{issue}'))
    def find():
        matches=[c for c in api.comments(repo,issue) if c.get('body','').splitlines()[:1]==[key]]
        require(len(matches)<=1,'Duplicate campaign markers require review')
        if matches: require(matches[0]['user']['id']==actor,'Campaign marker belongs to another publisher')
        return matches[0] if matches else None
    current=find();action='noop' if current and current['body']==body else 'updated' if current else 'created'
    if action!='noop':
        method='PATCH' if current else 'POST'
        route=f'repos/{repo}/issues/comments/{current["id"]}' if current else f'repos/{repo}/issues/{issue}/comments'
        try: api.request(method,route,{'body':body})
        except TrackerError:
            # Reconcile an uncertain write; never blindly retry a comment creation.
            current=find()
            require(current is not None and current['body']==body,'Uncertain publication was not reconciled; no retry was attempted')
            action='reconciled'
    current=find();require(current is not None and current['body']==body,'Published comment could not be verified')
    require(snapshot(api.request('GET',f'repos/{repo}/issues/{issue}'))==before,'Issue fields changed during publication')
    return {'action':action,'comment_id':current['id'],'comment_url':current.get('html_url'),'body_sha256':digest(body.encode()),'issue_fields_unchanged':True}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaign',required=True,type=Path);parser.add_argument('--artifacts',required=True,type=Path)
    parser.add_argument('--repository',required=True);parser.add_argument('--issue',required=True,type=int)
    parser.add_argument('--feature-ref');parser.add_argument('--fixture',action='store_true');parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    try:
        value=validate_campaign(json.loads(args.campaign.read_text()),args.artifacts,args.feature_ref)
        body=render(value,args.repository,args.issue,args.fixture)
        if not args.apply:sys.stdout.write(body);return 0
        # This lock serializes local publishers. Cross-host callers require one CI writer.
        lockroot=Path(tempfile.gettempdir())/'qa-tracker-locks';lockroot.mkdir(mode=0o700,exist_ok=True)
        require(not lockroot.is_symlink() and lockroot.owner()==Path.home().owner(),'Unsafe publisher lock directory')
        lockpath=lockroot/(digest(marker(args.repository,args.issue,value['campaign_id']).encode())+'.lock')
        fd=os.open(lockpath,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'w') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX);receipt=publish(value,args.repository,args.issue,body,GitHub())
        print(json.dumps(receipt,sort_keys=True));return 0
    except (TrackerError,OSError,ValueError,subprocess.SubprocessError):
        print('Tracker operation failed: invalid input, integrity check, or GitHub operation. No automatic retry.',file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
