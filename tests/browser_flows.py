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
   with self.subTest(note='supported'):
    result,code=runner.run(dict(C,campaign_id='mock-note',note='TEST ONLY: vegetarian'),'mock')
    self.assertEqual(result['outcome'],'mock-confirmed',result)
    self.assertEqual(result['note_delivery'],'verified-mock-readback')
 def test_note_network_guards(self):
  from unittest.mock import patch
  from playwright.sync_api import Route,Request
  original_fulfill=Route.fulfill
  original_payload=Request.post_data_json.fget
  original_prepare=runner.prepare_details
  note='FICTIONAL dietary requirement\nPreserve exactly.'
  for branch in ['exact','empty','normalized','premature','outbound-omitted','outbound-wrong','readback-omitted','readback-wrong']:
   with self.subTest(branch=branch),tempfile.TemporaryDirectory() as t:
    runner.STATE=Path(t)
    accepted=[]
    def payload(req):
     data=original_payload(req)
     if req.method=='POST' and '/book?' in req.url:
      if branch=='outbound-omitted':data['customer'].pop('note',None)
      if branch=='outbound-wrong':data['customer']['note']='NOT APPROVED'
     return data
    def fulfill(route,*args,**kwargs):
     if route.request.method=='POST':accepted.append(original_payload(route.request))
     data=kwargs.get('json')
     if isinstance(data,dict) and 'customer' in data and data.get('id','').startswith('bkg_'):
      if branch=='readback-omitted':data['customer'].pop('note',None)
      if branch=='readback-wrong':data['customer']['note']='NOT APPROVED'
     return original_fulfill(route,*args,**kwargs)
    def prepare(page,contact,note,arm):
     if branch=='premature':
      # Dangerous provider behavior: submit as soon as final contact is typed,
      # even with terms off and before the newly revealed note can be filled.
      page.locator('#phone').evaluate("el=>el.addEventListener('input',()=>fetch('https://api.tableonline.com/restaurant/res_0VWSAUspRta7lU/book?lang=en',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'}).catch(()=>{}),{once:true})")
     return original_prepare(page,contact,note,arm)
    with patch.object(Route,'fulfill',fulfill),patch.object(Request,'post_data_json',property(payload)),patch.object(runner,'prepare_details',prepare):
     result,code=runner.run(dict(C,campaign_id='mock-note-guards',note='' if branch=='empty' else (' '+note+' ' if branch=='normalized' else note)),'mock')
    if branch in ['exact','empty']:
     self.assertEqual(result['outcome'],'mock-confirmed',result)
     self.assertEqual(code,0)
     self.assertEqual(len(accepted),1)
     self.assertEqual(accepted[0]['customer'].get('note',''),'' if branch=='empty' else note)
    elif branch.startswith('readback'):
     self.assertEqual(result['outcome'],'submitted-or-ambiguous',result)
     self.assertEqual(len(accepted),1)
     self.assertEqual(result['note_delivery'],'unverified')
     self.assertTrue(result['reason'].startswith('readback_note_'),result)
    else:
     self.assertEqual(result['outcome'],'fatal-before-write',result)
     self.assertEqual(accepted,[])
     self.assertGreater(result['blocked_requests'],0)
     if branch=='premature':self.assertEqual(result['reason'],'premature_write_blocked')
     if branch=='normalized':self.assertEqual(result['reason'],'write_note_mismatch')
    # Reports/diagnostics never include the user's exact dietary text.
    for file in Path(t).rglob('*.json'):
     self.assertNotIn(note,json.dumps(json.loads(file.read_text()),ensure_ascii=False))
if __name__=='__main__':unittest.main()
