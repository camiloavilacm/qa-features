"""Aggregate one immutable campaign attempt; missing or invalid evidence cannot pass."""
from __future__ import annotations
import argparse,datetime as dt,hashlib,json,shutil,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tracker'))
from tracker import validate_campaign,render,TrackerError,canonical,digest,REQUIRED
SLOTS=tuple(f'{sut}:{driver}'for sut in ('sut-python','sut-node')for driver in ('playwright','selenium','cypress'))
def write(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2)+'\n')
def priority(statuses):return 'error'if 'error'in statuses else 'failed'if 'failed'in statuses else 'incomplete'if any(s in ('missing','not_run')for s in statuses)else 'passed'
def unverified(slot,expected):
    now=dt.datetime.now(dt.timezone.utc).isoformat();sut,driver=slot.split(':');family='qa-typescript'if driver=='cypress'else 'qa-python'
    return {'schema_version':'1.0','issue_id':'SEED-1','campaign_id':expected['campaign_id'],'execution_id':f'unverified-{expected["attempt"]}-{slot}','feature_ref':expected['feature_ref'],'tooling_ref':expected['tooling_ref'],'slot_id':slot,'sut_revision':expected['images'][sut]['config_id'],'runner_revision':expected['runner_fingerprints'][family],'started_at':now,'finished_at':now,'status':'error','scenarios':[{'id':ac,'status':'error','duration_ms':0,'observer':{'state':'error','events':[],'detail':'Execution evidence could not be verified'},'artifacts':[],'error':'Execution was not accepted; no passing assertion is claimed'}for ac in ('AC-1','AC-2','AC-3')]}
def aggregate(inbox,expected,output):
    inbox,output=Path(inbox).resolve(),Path(output).resolve()
    if output.exists():raise TrackerError('Refusing to overwrite an attempt')
    output.mkdir(parents=True);artifacts=output/'artifacts';artifacts.mkdir()
    campaign={'schema_version':'1.0','issue_id':'SEED-1','campaign_id':expected['campaign_id'],'feature_ref':expected['feature_ref'],'status':'incomplete','slots':[]}
    prefix=f'slot-{expected["attempt"]}-';allowed={prefix+slot.replace(':','-')for slot in SLOTS}
    if inbox.exists() and any(p.is_dir()and p.name.startswith(prefix)and p.name not in allowed for p in inbox.iterdir()):raise TrackerError('Unexpected slot artifact')
    findings=[]
    for slot in SLOTS:
        directory=inbox/(prefix+slot.replace(':','-'));value=None
        if directory.exists():
            target=artifacts/slot.replace(':','-')
            try:
                if directory.is_symlink():raise TrackerError('Symlink slot rejected')
                raw=(directory/'results.json').read_bytes();value=json.loads(raw);receipt=json.loads((directory/'receipt.json').read_text())
                sut,driver=slot.split(':');family='qa-typescript'if driver=='cypress'else 'qa-python'
                checks={'campaign_id':expected['campaign_id'],'attempt':expected['attempt'],'slot_id':slot,'tooling_ref':expected['tooling_ref'],'runner_source_ref':expected['repositories'][family],'sut_source_ref':expected['repositories'][sut],'sut_image_id':expected['images'][sut]['config_id'],'sut_registry_digest':expected['images'][sut]['registry_digest'],'result_sha256':digest(raw)}
                if any(receipt.get(k)!=v for k,v in checks.items()):raise TrackerError('Receipt differs from pinned attempt')
                if value['runner_revision']!=expected['runner_fingerprints'][family] or value['sut_revision']!=checks['sut_image_id'] or value['tooling_ref']!=expected['tooling_ref'] or value['slot_id']!=slot:raise TrackerError('Execution provenance differs')
                target=artifacts/slot.replace(':','-');target.mkdir()
                for scenario in value['scenarios']:
                    for item in scenario['artifacts']:
                        source=directory/item['path'];resolved=source.resolve()
                        if not resolved.is_relative_to(directory.resolve())or any(p.is_symlink()for p in [source,*source.parents]if p!=directory.parent):raise TrackerError('Artifact containment failed')
                        destination=target/item['path'];destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,destination)
                partial={**campaign,'slots':[{'slot_id':s,'state':'complete'if s==slot else 'missing','result':value if s==slot else None}for s in SLOTS]}
                partial['status']=priority([value['status'],'missing']);validate_campaign(partial,artifacts,expected['feature_ref'])
            except (TrackerError,OSError,ValueError,KeyError,TypeError):
                if target.exists():shutil.rmtree(target)
                value=unverified(slot,expected);findings.append({'slot_id':slot,'finding':'Invalid or unavailable execution evidence'})
        campaign['slots'].append({'slot_id':slot,'state':'complete'if value else 'missing','result':value})
    campaign['status']=priority([s['result']['status']if s['result']else 'missing'for s in campaign['slots']])
    validate_campaign(campaign,artifacts,expected['feature_ref'])
    write(output/'campaign.json',campaign);write(output/'provenance.json',{'expected':expected,'findings':findings})
    (output/'campaign.md').write_text(render(campaign,expected['report_repository'],max(1,expected['report_issue'])))
    return campaign
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--inbox',type=Path,required=True);p.add_argument('--context',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    try:campaign=aggregate(a.inbox,json.loads(a.context.read_text()),a.output);print('CAMPAIGN',campaign['status'])
    except Exception:print('Campaign aggregation could not validate its inputs',file=sys.stderr);raise SystemExit(1)
