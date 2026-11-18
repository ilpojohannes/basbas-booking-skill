"""Public UI assets; every provider request intercepted locally, no contact files."""
import unittest,sys,json,os,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import runner
C=json.loads((Path(__file__).resolve().parents[1]/'templates/campaign.example.json').read_text())
class BrowserTests(unittest.TestCase):
 def test_flows(self):
  cases=[('success','reserved',None,'mock-confirmed','18:00'),('fallback','reserved',['19:00','17:00'],'mock-confirmed','19:00'),('pending','pending',None,'submitted-or-ambiguous',None),('canceled','canceled',None,'submitted-or-ambiguous',None),('empty','reserved',[],'retryable-before-write',None)]
  with tempfile.TemporaryDirectory() as t:
   runner.STATE=Path(t)
   for label,status,slots,outcome,selected in cases:
    with self.subTest(label=label):
     result,code=runner.run(dict(C,campaign_id='mock-'+label),'mock',mock_status=status,mock_slots=slots)
     self.assertEqual(result['outcome'],outcome,result)
     if selected:self.assertEqual(result['slot'],selected)
     if outcome=='submitted-or-ambiguous':self.assertNotEqual(code,0)
   for party in [1,6]:
    with self.subTest(party=party):
     result,code=runner.run(dict(C,campaign_id='mock-party-'+str(party),party=party),'mock')
     self.assertEqual(result['outcome'],'mock-confirmed',result)
   with self.subTest(note='unsupported'):
    result,code=runner.run(dict(C,campaign_id='mock-note',note='TEST ONLY: vegetarian'),'mock')
    self.assertEqual(result.get('reason'),'note_field_unknown',result)
    self.assertEqual(result['outcome'],'fatal-before-write')
if __name__=='__main__':unittest.main()
