import unittest,sys,json,copy,tempfile,os
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import safety
import runner
C=json.loads((Path(__file__).resolve().parents[1]/'templates/campaign.example.json').read_text())
class SafetyTests(unittest.TestCase):
 def test_note_contract(self):
  for note in ['', 'FICTIONAL: allergy', '  exact text\n ', 'x'*2000]:
   self.assertEqual(safety.validate_config(dict(C,note=note))['note'],note)
  for note in [None,False,[], '   ', '\n\t', 'x'*2001, '😀'*1001]:
   with self.subTest(note_type=type(note).__name__),self.assertRaises(ValueError):safety.validate_config(dict(C,note=note))
  self.assertNotEqual(safety.scope_hash(C),safety.scope_hash(dict(C,note='FICTIONAL: allergy')))
 def test_note_exact_outbound(self):
  for note in ['FICTIONAL: allergy',' exact\ntext ']:
   runner.validate_note({'note':note},dict(C,note=note),'write')
   for customer in [{},{'note':None},{'note':note.strip()+'changed'}]:
    with self.assertRaises(runner.Stop):runner.validate_note(customer,dict(C,note=note),'write')
  runner.validate_note({},C,'write')
 def test_note_readback(self):
  runner.validate_note({},C,'readback')
  runner.validate_note({'note':None},C,'readback')
  c=dict(C,note='FICTIONAL: allergy')
  runner.validate_note({'note':c['note']},c,'readback')
  for customer in [{},{'note':None},{'note':'different'}]:
   with self.assertRaises(runner.Stop):runner.validate_note(customer,c,'readback')
 def test_config(self):self.assertEqual(safety.validate_config(C),C)
 def test_party(self):
  for n in [True,0,8,-1,'4']:
   with self.subTest(n=n),self.assertRaises(ValueError):safety.validate_config(dict(C,party=n))
 def test_year(self):
  with self.assertRaises(ValueError):safety.validate_config(dict(C,date='11-25'))
 def test_weekday(self):self.assertEqual(datetime.fromisoformat(C['date']).strftime('%A'),'Wednesday')
 def test_phone(self):
  self.assertEqual(runner.phone_e164('0400000000'),'+358400000000')
  for n in ['+12025550123','00358400000000','hello','040 000 0000']:
   with self.subTest(n=n),self.assertRaises(runner.Stop):runner.phone_e164(n)
 def test_rank(self):
  slots=[{'time':C['date']+'T'+s+':00','tables':[{'area':{'name':'Bistro'},'waitlist_only':False,'promotions':[]}]} for s in ['17:00','19:00']]
  self.assertEqual(runner.pick(slots,C),'19:00')
 def test_no_interpolation(self):
  self.assertNotIn('18:15',C['slot_preferences'])
  self.assertEqual(runner.preferences('18:00','19:00','18:30')[0],'18:30')
 def test_duplicate_ranking(self):
  with self.assertRaises(ValueError):safety.validate_config(dict(C,slot_preferences=['18:00','18:00']))
 def test_time(self):
  for s in ['24:00','18:60','8:00']:
   with self.subTest(s=s),self.assertRaises(ValueError):safety.minutes(s)
 def test_email_optin(self):
  self.assertFalse(C['email_check_opt_in'])
  with self.assertRaises(ValueError):safety.validate_config(dict(C,email_check_opt_in='yes'))
 def test_finances(self):
  for k in ['no_show_fee','minimum_spend','deposit','card_guarantee','cancellation_fee']:
   with self.subTest(k=k),self.assertRaises(runner.Stop):runner.no_money({'nested':{k:1}})
 def test_reserved_utc(self):
  d={'id':'test','restaurant_id':runner.RID,'module_id':runner.MID,'date':C['date'],'persons':4,'status':'reserved','state':{'current':'reserved','ttl':None,'missing_criteria':{'fields':[],'promotions':[]}},'time':[C['date']+'T16:00:00Z',C['date']+'T18:30:00Z'],'payment':{'charges':0,'total':0,'balance':0},'guarantee':None}
  runner.validate_readback(d,C,'18:00','test')
  for status in ['pending','canceled','unknown']:
   with self.subTest(status=status),self.assertRaises(runner.Stop):runner.validate_readback(dict(d,status=status),C,'18:00','test')
 def test_summer(self):
  self.assertEqual(datetime(2030,7,1,18,tzinfo=safety.HELSINKI).astimezone(timezone.utc).hour,15)
 def test_single_attempt(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'attempt.json';safety.exclusive_private_json(p,{'stage':'submitted-or-ambiguous'})
   with self.assertRaises(FileExistsError):safety.exclusive_private_json(p,{'stage':'confirmed'})
   self.assertEqual(json.loads(p.read_text())['stage'],'submitted-or-ambiguous')
 def test_window(self):
  a={'expires_at':'2026-10-26T00:08:00+02:00','not_before':C['release_at']}
  self.assertFalse(safety.active_window(a,C,datetime.fromisoformat('2026-10-26T01:00:00+02:00')))
 def test_evidence_failclosed(self):
  with self.assertRaises((ValueError,FileNotFoundError)):safety.evidence_gate(C)
 def test_private_contact(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'contact.json';p.write_text('{}');p.chmod(0o644)
   with self.assertRaises(ValueError):safety.load_contact(p)
 def test_terms_changed(self):
  self.assertNotEqual(runner.fingerprint({'steps':[],'consents':{}}),runner.fingerprint({'steps':[{'type':'payment','required':True}],'consents':{}}))
 def test_date_weekday_guard(self):
  safety.parse_dining_date(C['date'],'keskiviikko')
  with self.assertRaises(ValueError):safety.parse_dining_date(C['date'],'perjantai')
 def test_window_preference_guard(self):
  with self.assertRaises(runner.Stop):runner.preferences('19:00','18:00','18:30')
 def test_approval_scope_and_reuse(self):
  from datetime import timedelta
  now=datetime.now(safety.HELSINKI)
  c=dict(C,release_at=(now-timedelta(minutes=1)).isoformat(),windows=[{'start':(now-timedelta(minutes=1)).isoformat(),'end':(now+timedelta(minutes=3)).isoformat()}])
  module={'steps':[],'consents':{}}
  a=dict(c,approved=True,approve_standard_terms=True,module_id=runner.MID,restaurant_id=runner.RID,venue_name='Baskeri & Basso Bistro',terms_fingerprint=runner.fingerprint(module),not_before=c['release_at'],expires_at=c['windows'][0]['end'])
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'approval.json'
   def put(data):p.write_text(json.dumps(data));p.chmod(0o600)
   put(a);runner.approval(p,c,module)
   for changes in [{'note':'unapproved note'},{'party':3},{'approved':False},{'used_at':now.isoformat()},{'terms_fingerprint':'changed'}]:
    with self.subTest(changes=list(changes)),self.assertRaises(runner.Stop):put(dict(a,**changes));runner.approval(p,c,module)
 def test_contact_fake_json(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'contact.json';p.write_text((Path(__file__).resolve().parents[1]/'templates/contact.example.json').read_text());p.chmod(0o600)
   self.assertEqual(safety.load_contact(p)['BASBAS_EMAIL'],'diner@example.invalid')
 def test_note_report_caveat(self):
  import cli,io
  from unittest.mock import patch
  from contextlib import redirect_stdout
  with tempfile.TemporaryDirectory() as t:
   state=Path(t)/'state';config=Path(t)/'config.json';config.write_text(json.dumps(C))
   safety.atomic_private_json(state/'attempts'/(C['campaign_id']+'.json'),{'stage':'submitted-or-ambiguous','note_delivery':'unverified','reason':'readback_note_unknown','note':'DO_NOT_EXPOSE','booking_token':'DO_NOT_EXPOSE'})
   output=io.StringIO()
   with patch.object(cli,'STATE',state),patch('sys.argv',['cli','report','--config',str(config)]),redirect_stdout(output):
    self.assertEqual(cli.main(),0)
   result=json.loads(output.getvalue())
   self.assertEqual(result['note_delivery'],'unverified')
   self.assertEqual(result['reason'],'readback_note_unknown')
   self.assertNotIn('DO_NOT_EXPOSE',output.getvalue())
 def test_report_privacy(self):
  import privacy_scan
  self.assertEqual(privacy_scan.scan(),[])
 def test_rehearsal_evidence_dates(self):
  from datetime import timedelta
  now=datetime.now(safety.HELSINKI);release=now.replace(hour=0,minute=0,second=0,microsecond=0)
  c=dict(C,release_at=release.isoformat())
  previous=safety.STATE
  with tempfile.TemporaryDirectory() as t:
   try:
    safety.STATE=Path(t)
    records={
     'previous-day':{'outcome':'compatibility-ready','at':(release-timedelta(hours=12)).isoformat()},
     'release-rehearsal':{'outcome':'dry-run-ready','at':now.isoformat()},
    }
    for name,d in records.items():safety.atomic_private_json(safety.STATE/c['campaign_id']/c['date']/(name+'.json'),dict(d,scope_hash=safety.scope_hash(c),mode='dry-run'))
    safety.evidence_gate(c)
    safety.atomic_private_json(safety.STATE/c['campaign_id']/c['date']/'previous-day.json',{'outcome':'compatibility-blocked','at':now.isoformat(),'scope_hash':safety.scope_hash(c),'mode':'dry-run'})
    with self.assertRaises(ValueError):safety.evidence_gate(c)
   finally:safety.STATE=previous
 def test_rehearsal_crash_replaces_success(self):
  import cli,io
  from unittest.mock import patch
  from contextlib import redirect_stdout
  with tempfile.TemporaryDirectory() as t:
   state=Path(t)/'state';config=Path(t)/'config.json';config.write_text(json.dumps(C))
   report=state/C['campaign_id']/C['date']/'previous-day.json'
   safety.atomic_private_json(report,{'outcome':'compatibility-ready'})
   with patch.object(cli,'STATE',state),patch('sys.argv',['cli','previous-day','--config',str(config)]),patch('runner.run',side_effect=RuntimeError('DO_NOT_LOG_PRIVATE_DATA')),redirect_stdout(io.StringIO()):
    self.assertEqual(cli.main(),11)
   result=json.loads(report.read_text())
   self.assertEqual(result['outcome'],'fatal-before-write')
   self.assertNotIn('DO_NOT_LOG_PRIVATE_DATA',report.read_text())
if __name__=='__main__':unittest.main()
