"""Bind a publication receipt to the destination selected for its campaign."""
import re
from urllib.parse import urlsplit
from release_core import ROOT
from tracker import marker

def validate_publication(publication, context, body):
    repo=context.get('report_repository');issue=context.get('report_issue')
    if not isinstance(repo,str) or not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repo):
        raise ValueError('Invalid configured report repository')
    if type(issue)is not int or issue<=0:
        raise ValueError('Invalid configured report issue')
    comment=publication.get('comment_id');url=publication.get('comment_url')
    if type(comment)is not int or comment<=0 or not isinstance(url,str):
        raise ValueError('Invalid publication comment identity')
    parsed=urlsplit(url)
    if (parsed.scheme!='https' or parsed.netloc!='github.com' or parsed.query
        or parsed.path.casefold()!=f'/{repo}/issues/{issue}'.casefold()
        or parsed.fragment!=f'issuecomment-{comment}'):
        raise ValueError('Publication differs from configured report destination')
    if publication.get('issue_fields_unchanged')is not True:
        raise ValueError('Publication changed issue fields')
    if body.splitlines()[:1]!=[marker(repo,issue,context['campaign_id'])]:
        raise ValueError('Report marker differs from configured destination or campaign')
    return publication
