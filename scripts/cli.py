"""Safe CLI: validation, public rehearsal, reports; never creates approval."""
import argparse,json,sys
from pathlib import Path
from datetime import datetime
from safety import validate_config,STATE,scope_hash,atomic_private_json,HELSINKI

def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=['validate','dry-run','mock','report','previous-day','release-rehearsal']);p.add_argument('--config',required=True);p.add_argument('--report');p.add_argument('--mock-status',choices=['reserved','pending','canceled'],default='reserved');a=p.parse_args()
 c=None
 try:
  c=validate_config(json.loads(Path(a.config).read_text()))
  if a.action=='validate':info={'outcome':'valid','scope_hash':scope_hash(c)};code=0
  elif a.action=='report':
   attempt=STATE/'attempts'/(c['campaign_id']+'.json')
   if attempt.exists():
    from safety import private_file
    private_file(attempt);d=json.loads(attempt.read_text());info={k:v for k,v in d.items() if k in {'stage','date','party','slot','provider_status','booking_id'}}
   else:info={'outcome':'no_attempt'}
   code=0
  else:
   from runner import run
   mode='mock' if a.action=='mock' else 'dry-run'
   info,code=run(c,mode,mock_status=a.mock_status)
   if a.action=='previous-day':
    live_compatible=bool(info.get('terms_fingerprint')) and (info.get('outcome')=='dry-run-ready' or (info.get('outcome')=='retryable-before-write' and info.get('reason') in (None,'target_day_not_released','no_authorized_slot')))
    checks=[]
    for status,slots in [('reserved',None),('reserved',c['slot_preferences'][1:]),('pending',None),('canceled',None)]:
     m,mc=run(c,'mock',mock_status=status,mock_slots=slots)
     expected='mock-confirmed' if status=='reserved' and slots!=[] else ('retryable-before-write' if slots==[] else 'submitted-or-ambiguous')
     checks.append(m.get('outcome')==expected)
    info['mock_checks']=checks
    info['outcome']='compatibility-ready' if live_compatible and all(checks) else 'compatibility-blocked'
    code=0 if info['outcome']=='compatibility-ready' else 11
   if a.action in ('previous-day','release-rehearsal'):
    info.update(at=datetime.now(HELSINKI).isoformat(),scope_hash=scope_hash(c))
    atomic_private_json(STATE/c['campaign_id']/c['date']/(a.action+'.json'),info)
  if a.report:atomic_private_json(a.report,info)
  print(json.dumps(info,ensure_ascii=False));return code
 except Exception as e:
  info={'outcome':'fatal-before-write','reason':type(e).__name__,'at':datetime.now(HELSINKI).isoformat()}
  if c is not None and a.action in ('previous-day','release-rehearsal'):
   info.update(scope_hash=scope_hash(c),mode='dry-run')
   try:atomic_private_json(STATE/c['campaign_id']/c['date']/(a.action+'.json'),info)
   except Exception:info['warning']='failure_evidence_not_persisted_do_not_launch'
  print(json.dumps(info));return 11
if __name__=='__main__':sys.exit(main())
