#!/usr/bin/env python3
"""Migrated provider browser driver. One exact POST maximum; no pending retry/cleanup.
Live dry-run never fills contacts. Mock uses live public UI, local provider responses.
A pending/unknown response is terminal ambiguous, NEVER a reason to retry.
"""
import argparse, hashlib, json, re, sys, time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlsplit, parse_qs, urlencode
from playwright.sync_api import sync_playwright, expect
from safety import (HELSINKI, private_file, atomic_private_json, exclusive_private_json,
                         commit_lock, load_contact, minutes)
from safety import append_event, private_error_text, STATE, active_window
MID='mod_0VWSE3bovStZfY'
RID='res_0VWSAUspRta7lU'
API='https://api.tableonline.com'
REST='/restaurant/'+RID
URL='https://book.tableonline.com/'+MID

class Stop(RuntimeError):pass

def phone_e164(value):
 # Accept two explicitly supported Finnish representations; never guess another country.
 if re.fullmatch(r'\+358\d{7,10}',value):return value
 if re.fullmatch(r'0\d{7,10}',value):return '+358'+value[1:]
 raise Stop('phone_requires_manual_country_validation')

def preferences(first,last,ideal):
 if minutes(first)>minutes(last) or not minutes(first)<=minutes(ideal)<=minutes(last):raise Stop('invalid_window_ranking')
 values=range(minutes(first),minutes(last)+1,15)
 return [f'{v//60:02}:{v%60:02}' for v in sorted(values,key=lambda v:(abs(v-minutes(ideal)),v))]

def release_for(c):
 return datetime.fromisoformat(c['release_at'])

def campaign_directory(c):
 return STATE/c['campaign_id']/c['date']

def validate_scope(c):
 from safety import validate_config
 validate_config(c)

def fingerprint(module):
 # Bind documents, versions, messages and every substantive step. The exact
 # empty optional voucher widget adds no obligation or consent. Ignore ONLY
 # this observed shape; required vouchers, extra fields/messages remain bound.
 # Preserve the historical approved hash: no approval rewriting is necessary.
 steps=module.get('steps')
 if isinstance(steps,list):
  steps=[s for s in steps if not (isinstance(s,dict) and set(s)=={'type','required'} and s.get('type')=='voucher' and s.get('required') is False)]
 d={'steps':steps,'consents':module.get('consents')}
 def norm(x):
  if isinstance(x,str):return ' '.join(x.split())
  if isinstance(x,list):return [norm(v) for v in x]
  if isinstance(x,dict):return {k:norm(v) for k,v in x.items()}
  return x
 return hashlib.sha256(json.dumps(norm(d),sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

def no_money(d):
 if isinstance(d,list):
  for v in d:no_money(v)
 elif isinstance(d,dict):
  for k,v in d.items():
   if k in {'guarantee','prepayment','card_guarantee','no_show_guarantee','cancellation_fee','no_show_fee','noshow_fee','late_cancellation_fee','service_fee','deposit','minimum_spend'} and v:raise Stop('financial_guarantee')
   if k in {'total','total_amount','balance','price','fixed_amount','per_person_amount','amount_due','unit_price','charges'} and v not in (0,None,False,'0','0.00'):raise Stop('financial_charge')
   if k in {'payment_required','requires_acceptance'} and v is True:raise Stop('financial_required')
   no_money(v)

def safe_read(url,booking_id=None):
 u=urlsplit(url)
 if u.scheme!='https' or u.netloc!='api.tableonline.com':return False
 paths={'/module/'+MID+'/book',REST,REST+'/availability',REST+'/availability/calendar',REST+'/book/items',REST+'/book/promotions'}
 if booking_id:paths|={REST+'/book/'+booking_id,REST+'/book/'+booking_id+'/items',REST+'/book/'+booking_id+'/promotions',REST+'/book/'+booking_id+'/cart'}
 if u.path not in paths:return False
 q=parse_qs(u.query,keep_blank_values=True)
 allowed={'locale','include_translations','persons','date','start_date','end_date','module_id','time','include_items','exclude_booking_id'}
 if set(q)-allowed or any(len(v)!=1 for v in q.values()):return False
 for k,vals in q.items():
  v=vals[0]
  if k=='locale' and v!='en':return False
  if k in ('include_translations','include_items') and v!='true':return False
  if k=='persons' and not re.fullmatch(r'[1-9][0-9]?',v):return False
  if k=='module_id' and v!=MID:return False
  if k=='exclude_booking_id' and v!=booking_id:return False
  if k in ('date','start_date','end_date') and not re.fullmatch(r'\d{4}-\d{2}-\d{2}',v):return False
  if k=='time' and not re.fullmatch(r'(?:[01][0-9]|2[0-3]):[0-5][0-9]',v):return False
 return True

def pick(slots,c):
 available=set()
 for s in slots:
  t=s.get('time','')
  if not re.fullmatch(re.escape(c['date'])+r'T\d{2}:\d{2}:00',t):continue
  for table in s.get('tables',[]):
   if table.get('waitlist_only') is not False:continue
   if table.get('area',{}).get('name')!='Bistro' or table.get('promotions'):continue
   no_money(table);available.add(t[11:16])
 return next((v for v in c['slot_preferences'] if v in available),None)

def validate_note(customer,c,stage):
 # Preserve legacy no-note readback semantics; never trim approved text.
 if stage=='readback' and not c['note']:return
 if not isinstance(customer,dict):raise Stop(stage+'_note_unknown')
 if c['note'] and 'note' not in customer:raise Stop(stage+'_note_unknown')
 if customer.get('note','')!=c['note']:raise Stop(stage+'_note_mismatch')

def prepare_details(page,contact,note,arm):
 # The note is revealed only after contacts. Keep terms OFF until it is filled;
 # the network guard independently rejects every premature submission.
 terms=page.locator('#terms_accepted')
 if terms.is_checked():raise Stop('terms_prematurely_checked')
 page.locator('#first_name').fill(contact['BASBAS_FIRSTNAME'])
 page.locator('#last_name').fill(contact['BASBAS_LASTNAME'])
 page.locator('#email').fill(contact['BASBAS_EMAIL'])
 page.locator('#phone').fill(phone_e164(contact['BASBAS_MOBILE'])[4:])
 page.locator('#phone').blur()
 if note:
  field=page.locator('textarea#note')
  expect(field).to_be_visible()
  if field.get_attribute('maxlength')!='2000':raise Stop('note_field_contract')
  field.fill(note)
  expect(field).to_have_value(note)
 arm()

def validate_readback(d,c,slot,bid):
 no_money(d)
 validate_note(d.get('customer',{}),c,'readback')
 expected={'id':bid,'restaurant_id':RID,'module_id':MID,'date':c['date'],'persons':c['party']}
 if any(type(d.get(k)) is not type(v) or d.get(k)!=v for k,v in expected.items()) or d.get('status') not in ('confirmed','reserved'):raise Stop('readback_scope_or_status')
 state=d.get('state')
 if not isinstance(state,dict) or state.get('current')!=d['status'] or 'ttl' not in state or state['ttl'] is not None:raise Stop('readback_state')
 if state.get('missing_criteria')!={'fields':[],'promotions':[]}:raise Stop('readback_missing_criteria')
 try:
  times=d['time']
  if not isinstance(times,list) or len(times)!=2:raise ValueError()
  actual=datetime.fromisoformat(times[0].replace('Z','+00:00'))
  end=datetime.fromisoformat(times[1].replace('Z','+00:00'))
  wanted=datetime.fromisoformat(c['date']+'T'+slot+':00').replace(tzinfo=HELSINKI)
  if actual.tzinfo is None or end.tzinfo is None or actual!=wanted or end<=actual:raise ValueError()
 except (KeyError,TypeError,ValueError,AttributeError):raise Stop('readback_time')
 if 'payment' not in d or 'guarantee' not in d:raise Stop('readback_financial_state_unknown')
 if d['guarantee'] is not None or not isinstance(d['payment'],dict):raise Stop('readback_financial_state_unknown')
 if any(k not in d['payment'] or type(d['payment'][k]) not in (int,float) or d['payment'][k]!=0 for k in ('charges','total','balance')):raise Stop('readback_financial_state_unknown')
 if any(d.get('customer',{}).get('consents',{}).get(k) is True for k in ('marketing_email','marketing_sms','restaurant_marketing')):raise Stop('marketing_enabled')

def validate_identity(module,restaurant,body):
 if module.get('id')!=MID or module.get('restaurant_id')!=RID or restaurant.get('id')!=RID or restaurant.get('name')!='Baskeri & Basso':raise Stop('venue_identity')
 if 'Baskeri & Basso Bistro, located within the courtyard of Tehtaankatu.' not in body:raise Stop('bistro_welcome_identity')
 if not module.get('consents',{}).get('terms_of_use',{}).get('document',{}).get('markdown'):raise Stop('missing_terms')
 no_money(module)
 for step in module.get('steps',[]):
  if step.get('type') in ('payment','guarantee') and step.get('required'):raise Stop('required_payment_step')

def approval(path,c,module):
 private_file(path);a=json.loads(Path(path).read_text())
 if a.get('approved') is not True or a.get('approve_standard_terms') is not True or a.get('used_at'):raise Stop('approval_not_authorized')
 if a.get('module_id')!=MID or a.get('restaurant_id')!=RID or a.get('venue_name')!='Baskeri & Basso Bistro':raise Stop('approval_venue')
 if any(type(a.get(k)) is not type(v) or a.get(k)!=v for k,v in c.items()):raise Stop('approval_scope')
 if a.get('terms_fingerprint')!=fingerprint(module):raise Stop('terms_changed')
 expiry=datetime.fromisoformat(a['expires_at']);release=datetime.fromisoformat(a['not_before'])
 if expiry.tzinfo is None or release.tzinfo is None:raise Stop('approval_timezone')
 now=datetime.now(HELSINKI)
 if not active_window(a,c,now):raise Stop('outside_authorized_release_window')
 if release!=release_for(c):raise Stop('release_scope')
 if not re.fullmatch(r'[A-Za-z0-9._-]{6,80}',a.get('campaign_id','')):raise Stop('campaign_id')
 return a

def _run(c,mode,approval_path=None,contact_path=None,report=None,mock_status='reserved',mock_slots=None):
 validate_scope(c)
 if mode not in ('dry-run','mock','commit'):raise Stop('invalid_mode')
 if mode=='commit':
  from safety import evidence_gate
  evidence_gate(c)
 sensitive=False; submission_ready=False; wrote=False; bid=None; token=None; selected=None; failed=[]; seen={}; blocked=0
 attempt=None;ap=None;record={};mock_payload=None;asset_urls=set();module=None
 def persist(stage,**extra):
  record.update(stage=stage,at_helsinki=datetime.now(HELSINKI).isoformat(),**extra)
  if attempt:atomic_private_json(attempt,record)
 def gate(route):
  nonlocal blocked,wrote,mock_payload,bid,token
  req=route.request;u=urlsplit(req.url)
  try:
   # Every mock-provider call is fulfilled locally after private/fake contact entry.
   if mode=='mock' and u.netloc=='api.tableonline.com':
    if req.method=='OPTIONS':
     route.fulfill(status=204,headers={'Access-Control-Allow-Origin':'https://book.tableonline.com','Access-Control-Allow-Methods':'GET,POST,OPTIONS','Access-Control-Allow-Headers':req.headers.get('access-control-request-headers','*'),'Access-Control-Allow-Credentials':'true'});return
    if u.path=='/module/'+MID+'/book':
     fixture=json.loads((Path(__file__).resolve().parents[1]/'references/module.fixture.json').read_text());fixture['last_bookable_date']=c['date'];route.fulfill(json=fixture);return
    if u.path==REST:
     route.fulfill(json={'id':RID,'name':'Baskeri & Basso','slug':'baskeri-basso','timezone':'Europe/Helsinki','currency':'EUR'});return
    if req.method=='POST' and u.path==REST+'/book':
     check_post(req);mock_payload=req.post_data_json;wrote=True;bid='bkg_00000000000001';token='local-mock-token'
     route.fulfill(json={'id':bid,'status':mock_status,'booking_token':token});return
    if mock_payload and u.path.startswith(REST+'/book/'+str(bid)):
     suffix=u.path[len(REST+'/book/'+bid):]
     if suffix=='/items':data={'items':[],'selected_items':[]}
     elif suffix=='/promotions':data={'promotions':[]}
     elif suffix=='/cart':data={'carts':[]}
     elif suffix=='':data={'id':bid,'restaurant_id':RID,'module_id':MID,'date':c['date'],'time':[(datetime.fromisoformat(c['date']+'T'+selected).replace(tzinfo=HELSINKI)+timedelta(minutes=n)).astimezone(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z') for n in (0,165)],'persons':c['party'],'status':mock_status,'customer':mock_payload['customer'],'guarantee':None,'allergies':None,'source':'website','state':{'current':mock_status,'available_transitions':[],'missing_criteria':{'fields':[],'promotions':[]},'ttl':None},'payment':{'charges':0,'discounts':0,'payments':0,'refunds':0,'total':0,'paid':0,'balance':0,'currency':'EUR'}}
     else:raise Stop('mock_unknown_booking_path')
     route.fulfill(json=data);return
    if u.path==REST+'/availability/calendar':
     q=parse_qs(u.query);start=q['start_date'][0];end=q['end_date'][0]
     from datetime import date
     day=date.fromisoformat(start);out=[]
     while day.isoformat()<=end:
      out.append({'date':day.isoformat(),'persons':{str(c['party']):{'total_slots':1,'available_slots':1,'waitlist':False,'promotions':[]}}});day+=timedelta(days=1)
     route.fulfill(json=out);return
    if u.path==REST+'/availability':
     route.fulfill(json=[{'time':c['date']+'T'+mock_time+':00','shift':{'name':'Dinner','category':['dinner']},'tables':[{'area':{'id':'ara_00000000000001','name':'Bistro'},'duration':'02:30:00','priority':1,'table_ids':['tbl_00000000000001'],'promotions':[],'service_id':'svc_00000000000001','waitlist_only':False}]} for mock_time in (mock_slots if mock_slots is not None else c['slot_preferences'])]);return
    if u.path in (REST+'/book/items',REST+'/book/promotions'):
     route.fulfill(json={'items':[],'promotions':[],'booking_context':{}});return
    raise Stop('unhandled_mock_provider_request')
   if req.method not in ('GET','HEAD','OPTIONS'):
    if mode=='commit' and req.method=='POST' and u.scheme=='https' and u.netloc=='api.tableonline.com' and u.path==REST+'/book':
     check_post(req)
     if wrote:raise Stop('duplicate_write')
     # Atomic no-duplicate marker precedes network dispatch, even if request later fails.
     exclusive_private_json(attempt,{**record,'stage':'submitted-or-ambiguous','slot':selected})
     wrote=True;ap['used_at']=datetime.now(HELSINKI).isoformat();atomic_private_json(approval_path,ap)
     route.continue_();return
    blocked+=1;route.abort();return
   if u.netloc=='api.tableonline.com':
    if not safe_read(req.url,bid):raise Stop('unexpected_api_read')
    route.continue_();return
   if u.scheme=='https' and u.netloc=='book.tableonline.com' and (u.path=='/'+MID or u.path=='/'+MID+'/'+str(bid) or u.path.startswith('/_next/') or u.path.startswith('/assets/')):
    if sensitive and req.url not in asset_urls and not u.path.startswith('/'+MID):raise Stop('new_asset_after_contact')
    asset_urls.add(req.url);route.continue_();return
   blocked+=1;route.abort()
  except Exception as e:
   blocked+=1
   failed.append(str(e) if isinstance(e,Stop) else type(e).__name__);route.abort()
 def check_post(req):
  if not submission_ready:raise Stop('premature_write_blocked')
  if mode=='commit':approval(approval_path,c,module)
  if failed:raise Stop('prewrite_provider_failure')
  # Recheck the completed response data at dispatch, not only before contact entry.
  for suffix,key in (('/book/items','items'),('/book/promotions','promotions')):
   data=seen.get(REST+suffix)
   if not isinstance(data,dict) or data.get(key)!=[]:raise Stop('prewrite_data_unknown')
   no_money(data)
  no_money(module)
  if not sensitive or not selected or wrote:raise Stop('write_not_armed')
  q=parse_qs(urlsplit(req.url).query)
  if q!={'lang':['en']}:raise Stop('write_query')
  d=req.post_data_json
  if set(d)!={'date','time','persons','customer','module_id','consents'}:raise Stop('write_keys')
  if any(d.get(k)!=v for k,v in {'date':c['date'],'time':c['date']+'T'+selected+':00','persons':c['party'],'module_id':MID}.items()):raise Stop('write_scope')
  if d['consents']!={'terms_of_use':{'version':module['consents']['terms_of_use']['version'],'locale':'en'}}:raise Stop('write_consents')
  customer=d['customer']
  expected={'first_name':contact['BASBAS_FIRSTNAME'],'last_name':contact['BASBAS_LASTNAME'],'email':contact['BASBAS_EMAIL'],'phone':phone_e164(contact['BASBAS_MOBILE'])}
  if any(customer.get(k)!=v for k,v in expected.items()):raise Stop('write_contact_mismatch')
  if set(customer)-set(expected)-{'address','extra_address','postcode','city','company','country','accept_email','accept_sms','locale','note'}:raise Stop('write_customer_keys')
  validate_note(customer,c,'write')
  if any(customer.get(k) not in ('',None) for k in ('address','extra_address','postcode','city','company','country')):raise Stop('write_unapproved_customer_fields')
  if customer.get('accept_email') is not True or customer.get('accept_sms') is not True:raise Stop('transactional_notifications_contract')
  no_money(d)
 def observe(r):
  nonlocal bid,token
  if urlsplit(r.url).netloc!='api.tableonline.com' or r.request.method=='OPTIONS':return
  path=urlsplit(r.url).path
  if r.status<200 or r.status>=300:failed.append('provider_http_'+str(r.status));return
  try:data=r.json()
  except Exception:failed.append('provider_non_json');return
  seen[path]=data
  if path==REST+'/book' and r.request.method=='POST':
   if not re.fullmatch(r'bkg_[A-Za-z0-9]{14}',str(data.get('id',''))):failed.append('unknown_booking_id');return
   bid=data['id'];token=data.get('booking_token')
   if mode=='commit':persist('submitted-or-ambiguous',booking_id=bid,booking_token=token,slot=selected)
 with sync_playwright() as p:
  b=p.chromium.launch(headless=True);ctx=b.new_context(service_workers='block',locale='en-US',timezone_id='Europe/Helsinki')
  ctx.route_web_socket('**/*',lambda ws:ws.close());ctx.route('**/*',gate);page=ctx.new_page();page.set_default_timeout(20000);page.on('response',observe)
  try:
   with page.expect_response(lambda r:urlsplit(r.url).path==REST and r.request.method=='GET'):
    page.goto(URL+'?lang=en',wait_until='domcontentloaded')
   expect(page.get_by_role('button',name='Continue',exact=True)).to_be_visible()
   module=seen['/module/'+MID+'/book'];restaurant=seen[REST]
   validate_identity(module,restaurant,page.locator('body').inner_text())
   limits=module.get('persons_settings',{})
   if type(limits.get('min_persons')) is not int or type(limits.get('max_persons')) is not int or not limits['min_persons']<=c['party']<=limits['max_persons']:raise Stop('party_not_live_supported')
   if module.get('last_bookable_date','')<c['date']:raise Stop('target_day_not_released')
   if mode=='commit':
    ap=approval(approval_path,c,module);attempt=STATE/'attempts'/(ap['campaign_id']+'.json')
    if attempt.exists():raise Stop('existing_attempt_terminal')
    for prior in (STATE/'attempts').glob('*.json'):
     private_file(prior);previous=json.loads(prior.read_text())
     if previous.get('date')==c['date'] and previous.get('party',previous.get('persons'))==c['party']:raise Stop('prior_same_scope_attempt_terminal')
    record.update(campaign_id=ap['campaign_id'],provider='migrated',date=c['date'],party=c['party'])
   page.get_by_role('button',name='Continue',exact=True).click()
   if c['party'] > 5:page.locator('button[aria-haspopup="menu"]').click()
   page.get_by_text(str(c['party']) if c['party'] <= 5 else f"{c['party']} guests",exact=True).click()
   with page.expect_response(lambda r:urlsplit(r.url).path==REST+'/availability/calendar'):
    page.get_by_role('button',name='Continue',exact=True).click()
   # Calendar's arrows lack accessible names. Match the observed icon; never positional guessing.
   caption=datetime.fromisoformat(c['date']).strftime('%B %Y')
   for calendar_step in range(13):
    if caption in page.locator('body').inner_text():break
    with page.expect_response(lambda r:urlsplit(r.url).path==REST+'/availability/calendar' ):
     page.locator('button').filter(has=page.locator('svg.lucide-chevron-right')).click()
   expect(page.get_by_text(caption,exact=True)).to_be_visible()
   day=page.get_by_role('button',name=str(int(c['date'][-2:])),exact=True).last
   if day.is_disabled():raise Stop('no_authorized_slot')
   with page.expect_response(lambda r:urlsplit(r.url).path==REST+'/availability' and parse_qs(urlsplit(r.url).query).get('date')==[c['date']]):day.click()
   selected=pick(seen.get(REST+'/availability',[]),c)
   info={'mode':mode,'provider':'migrated','restaurant_id':RID,'module_id':MID,'date':c['date'],'party':c['party'],'slot':selected,'terms_fingerprint':fingerprint(module),'blocked_requests':blocked,'outcome':'retryable-before-write' if not selected else 'dry-run-ready'}
   if not selected:
    if report:atomic_private_json(report,info)
    return info,10
   expect(page.get_by_text(selected.replace(':','.'),exact=True)).to_be_visible()
   with page.expect_response(lambda r:urlsplit(r.url).path==REST+'/book/items'), page.expect_response(lambda r:urlsplit(r.url).path==REST+'/book/promotions'):
    page.get_by_text(selected.replace(':','.'),exact=True).click()
    page.get_by_role('button',name='Continue',exact=True).click()
   expect(page.locator('#email')).to_be_visible()
   # GET prebook data must have completed and show no goods/promotions/fee obligations.
   for suffix,key in (('/book/items','items'),('/book/promotions','promotions')):
    if REST+suffix not in seen:raise Stop('missing_prebook_response')
    data=seen[REST+suffix];no_money(data)
    if data.get(key)!=[]:raise Stop('unknown_items_or_promotions')
   if failed:raise Stop(failed[0])
   if mode=='dry-run':
    info['outcome']='dry-run-ready'
    if report:atomic_private_json(report,info)
    return info,0
   # The UI may auto-create the real booking on completion of required contact fields,
   # NOT on a final confirmation button. Arm once before the first contact field.
   if mode=='mock':contact={'BASBAS_FIRSTNAME':'Automation','BASBAS_LASTNAME':'Rehearsal','BASBAS_EMAIL':'rehearsal@example.invalid','BASBAS_MOBILE':'0400000000'}
   else:contact=load_contact(contact_path)
   phone=phone_e164(contact['BASBAS_MOBILE'])
   text=page.locator('body').inner_text().lower()
   if any(x in text for x in ('captcha','card guarantee','cancellation fee','prepayment','pay now','credit card')):raise Stop('fee_or_challenge_ui')
   marketing=page.locator('#restaurant_marketing')
   if marketing.count() and marketing.is_checked():raise Stop('marketing_checked')
   sensitive=True
   def arm_submission():
    nonlocal submission_ready
    if failed:raise Stop(failed[0])
    if mode=='commit':approval(approval_path,c,module)
    submission_ready=True
   prepare_details(page,contact,c['note'],arm_submission)
   with page.expect_response(lambda r:r.request.method=='POST' and urlsplit(r.url).path==REST+'/book'):
    page.locator('#terms_accepted').check()
    # If checking terms itself submitted, never click again.
    if not wrote:page.get_by_role('button',name='Continue',exact=True).click()
   if failed:raise Stop(failed[0])
   if not bid:raise Stop('missing_booking_id')
   # Read back exact booking through browser fetch (routes still enforce read allowlist).
   data=page.evaluate('''async ({url,token})=>{const r=await fetch(url,{headers:token?{'X-Booking-Token':token,'X-Guarantee-Terms':'booking-noshow-v2'}:{'X-Guarantee-Terms':'booking-noshow-v2'}});if(!r.ok)throw Error('readback HTTP '+r.status);return await r.json()}''',{'url':API+REST+'/book/'+bid,'token':token})
   validate_readback(data,c,selected,bid)
   # Corroborate the provider confirmation UI when it is exposed. Never click
   # Continue again: it may issue another provider write.
   ui=page.get_by_text(re.compile(r'Your table is (reserved|confirmed)\.'))
   try:expect(ui).to_be_visible(timeout=5000)
   except AssertionError:info['warning']='confirmation_ui_unavailable_readback_validated'
   else:
    body=page.locator('body').inner_text()
    if 'Baskeri & Basso' not in body or selected.replace(':','.') not in body or f"{c['party']} guest" not in body or datetime.fromisoformat(c['date']).strftime('%-d %B %Y') not in body:raise Stop('confirmation_ui_scope')
   if mode=='commit':persist('confirmed',booking_id=bid,slot=selected,provider_status=data['status'],note_delivery='verified-provider-readback' if c['note'] else 'not-requested')
   info.update(local_datetime=c['date']+'T'+selected, timezone='Europe/Helsinki', provider_status=data['status'],note_delivery=('verified-mock-readback' if mode=='mock' else 'verified-provider-readback') if c['note'] else 'not-requested')
   info.update(outcome='confirmed' if mode=='commit' else 'mock-confirmed',booking_id=bid,blocked_requests=blocked)
   if report:atomic_private_json(report,info)
   return info,0
  except Exception as e:
   if record.get('stage')=='confirmed':
    return {'mode':mode,'outcome':'confirmed','booking_id':bid,'slot':selected,'warning':'optional_report_failed'},0
   if mode in ('commit','dry-run'):
    try:append_event(campaign_directory(c)/'diagnostics.jsonl','guarded_error',mode=mode,detail=private_error_text(str(e),Path(contact_path) if contact_path else Path('unused')))
    except Exception:pass
   if mode=='mock':atomic_private_json(campaign_directory(c)/'mock-diagnostic.json',{'error':str(e) if isinstance(e,Stop) else type(e).__name__,'failed':failed})
   reason=failed[0] if failed else (str(e) if isinstance(e,Stop) else type(e).__name__)
   if mode=='commit' and wrote:persist('submitted-or-ambiguous',reason=reason,booking_id=bid,slot=selected,note_delivery='unverified' if c['note'] else 'not-requested')
   info={'mode':mode,'outcome':'submitted-or-ambiguous' if wrote else 'fatal-before-write','reason':reason,'blocked_requests':blocked,'terms_fingerprint':fingerprint(module) if module else None,'last_bookable_date':module.get('last_bookable_date') if module else None}
   if c['note']:
    info['note_delivery']='unverified'
    if wrote:info['warning']='note_delivery_not_verified_do_not_retry_reconcile_booking'
   retryable=not wrote and not (attempt and attempt.exists()) and (reason in ('target_day_not_released','no_authorized_slot') or (mode=='dry-run' and reason in ('TimeoutError','Error')))
   if retryable:info['outcome']='retryable-before-write'
   if report:atomic_private_json(report,info)
   return info,2 if wrote else (10 if retryable else 11)
  finally:ctx.close();b.close()

def run(c,mode,approval_path=None,contact_path=None,report=None,mock_status='reserved',mock_slots=None):
 # Validate note/scope before browser startup, private state or contacts.
 validate_scope(c)
 if mode=='commit':
  with commit_lock():return _run(c,mode,approval_path,contact_path,report,mock_status,mock_slots)
 return _run(c,mode,approval_path,contact_path,report,mock_status,mock_slots)

def main():
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--mode',choices=['dry-run','mock','commit'],default='dry-run');p.add_argument('--approval-file');p.add_argument('--contact-file',default=None);p.add_argument('--report');p.add_argument('--mock-status',default='reserved',choices=['confirmed','reserved','pending','canceled'])
 a=p.parse_args();private_file(a.config);c=json.loads(Path(a.config).read_text())
 if a.mode=='commit':
  if not a.approval_file:p.error('--approval-file required')
  info,code=run(c,a.mode,a.approval_file,a.contact_file,a.report)
 else:info,code=run(c,a.mode,report=a.report,mock_status=a.mock_status)
 print(json.dumps(info));return code
if __name__=='__main__':sys.exit(main())
