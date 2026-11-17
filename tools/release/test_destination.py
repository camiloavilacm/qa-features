"""Configured destinations must work for successful and failed report receipts."""
import copy,unittest
from publication_destination import validate_publication
from tracker import marker

class PublicationDestination(unittest.TestCase):
    def setUp(self):
        self.context={'report_repository':'camiloavilacm/qa-features','report_issue':3,'campaign_id':'smoke-gh-123-456'}
        self.receipt={'comment_id':789,'comment_url':'https://github.com/camiloavilacm/qa-features/issues/3#issuecomment-789','issue_fields_unchanged':True}
    def body(self,context=None,status='verified'):
        c=context or self.context
        return marker(c['report_repository'],c['report_issue'],c['campaign_id'])+'\nRelease outcome: **'+status+'**\n'
    def test_default_and_nondefault_destinations_are_accepted(self):
        for issue in (2,3,42):
            for status in ('verified','failed'):
                with self.subTest(issue=issue,status=status):
                    c={**self.context,'report_issue':issue};p={**self.receipt,'comment_url':f'https://github.com/camiloavilacm/qa-features/issues/{issue}#issuecomment-789'}
                    validate_publication(p,c,self.body(c,status))
    def test_wrong_issue_repository_host_scheme_or_comment_rejected(self):
        for url in ('https://github.com/camiloavilacm/qa-features/issues/2#issuecomment-789','https://github.com/camiloavilacm/other/issues/3#issuecomment-789','https://github.com.evil.test/camiloavilacm/qa-features/issues/3#issuecomment-789','http://github.com/camiloavilacm/qa-features/issues/3#issuecomment-789','https://github.com/camiloavilacm/qa-features/issues/3?x=1#issuecomment-789','https://github.com/camiloavilacm/qa-features/issues/3#issuecomment-790'):
            with self.subTest(url=url),self.assertRaises(ValueError):validate_publication({**self.receipt,'comment_url':url},self.context,self.body())
    def test_invalid_configuration_and_unverified_transition_rejected(self):
        for value in (0,-1,True,'3',None):
            with self.subTest(value=value),self.assertRaises(ValueError):validate_publication(self.receipt,{**self.context,'report_issue':value},self.body())
        with self.assertRaises(ValueError):validate_publication({**self.receipt,'issue_fields_unchanged':False},self.context,self.body())
    def test_body_must_bind_the_same_destination_and_campaign(self):
        for c in ({**self.context,'report_issue':2},{**self.context,'campaign_id':'another-campaign'}):
            with self.assertRaises(ValueError):validate_publication(self.receipt,self.context,self.body(c))

if __name__=='__main__':unittest.main()
