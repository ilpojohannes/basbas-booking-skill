"""Portable, private local state and fail-closed mandate gates."""
import os,json,re,fcntl
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
HELSINKI=ZoneInfo('Europe/Helsinki')
STATE=Path(os.environ.get('BASBAS_STATE_DIR', str(Path(os.environ.get('XDG_STATE_HOME', str(Path.home()/'.local/state')))/'basbas-booking-public')))
def minutes(s):
 if not isinstance(s,str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',s):raise ValueError('invalid_time')
 return int(s[:2])*60+int(s[3:])
def private_file(path):
 p=Path(path)
 if p.is_symlink() or not p.is_file() or p.stat().st_mode&0o777!=0o600 or p.stat().st_uid!=os.getuid():raise ValueError('private_file_requires_owned_0600')
def _parent(p):
 p.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
 if p.parent.stat().st_mode&0o077:raise ValueError('state_directory_requires_0700')
def exclusive_private_json(path,data):
 p=Path(path);_parent(p)
 fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'w') as f:json.dump(data,f);f.flush();os.fsync(f.fileno())
def atomic_private_json(path,data):
 p=Path(path);_parent(p);t=p.with_name(p.name+'.new')
 fd=os.open(t,os.O_WRONLY|os.O_CREAT|os.O_TRUNC|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'w') as f:json.dump(data,f);f.flush();os.fsync(f.fileno())
 os.replace(t,p)
@contextmanager
def commit_lock():
 p=STATE/'commit.lock';_parent(p)
 fd=os.open(p,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
 try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);yield
 finally:os.close(fd)
def load_contact(path):
 if not path:raise ValueError('contact_source_required')
 private_file(path);d=json.loads(Path(path).read_text())
 keys=('BASBAS_FIRSTNAME','BASBAS_LASTNAME','BASBAS_EMAIL','BASBAS_MOBILE')
 if set(d)!=set(keys) or any(not isinstance(d[k],str) or not d[k].strip() for k in keys):raise ValueError('invalid_contact')
 if not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+',d['BASBAS_EMAIL']):raise ValueError('invalid_email')
 return d
def aware(s):
 t=datetime.fromisoformat(s)
 if t.tzinfo is None:raise ValueError('timezone_required')
 return t

def parse_dining_date(value,weekday=None):
 if not isinstance(value,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):raise ValueError('date_requires_year')
 day=datetime.strptime(value,'%Y-%m-%d').date()
 names=['maanantai','tiistai','keskiviikko','torstai','perjantai','lauantai','sunnuntai']
 if weekday is not None and weekday.lower() not in (day.strftime('%A').lower(),names[day.weekday()]):raise ValueError('date_weekday_mismatch')
 return day

def validate_config(c):
 required={'campaign_id','date','party','slot_preferences','release_at','windows','note','email_check_opt_in'}
 if set(c)!=required:raise ValueError('config_keys')
 if not re.fullmatch(r'[A-Za-z0-9_-]{6,80}',c['campaign_id']):raise ValueError('campaign_id')
 if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',c['date']):raise ValueError('date_requires_year')
 datetime.strptime(c['date'],'%Y-%m-%d')
 if type(c['party']) is not int or not 1<=c['party']<=7:raise ValueError('party_requires_live_supported_1_to_7')
 if not isinstance(c['slot_preferences'],list) or not c['slot_preferences'] or len(set(c['slot_preferences']))!=len(c['slot_preferences']):raise ValueError('ranked_times')
 for s in c['slot_preferences']:minutes(s)
 r=aware(c['release_at'])
 if r.astimezone(HELSINKI).date()>=datetime.fromisoformat(c['date']).date():raise ValueError('release_after_dining')
 if not c['windows']:raise ValueError('explicit_windows_required')
 for w in c['windows']:
  if set(w)!={'start','end'} or aware(w['start'])<r or aware(w['end'])<=aware(w['start']):raise ValueError('invalid_window')
 if type(c['email_check_opt_in']) is not bool or not isinstance(c['note'],str):raise ValueError('note_email_types')
 return c

def active_window(a,c,now):
 return any(aware(w['start'])<=now<=aware(w['end']) for w in c['windows']) and now<=aware(a['expires_at']) and now>=aware(a['not_before'])
def scope_hash(c):
 import hashlib
 return hashlib.sha256(json.dumps(c,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def evidence_gate(c):
 for name,previous in [('previous-day',True),('release-rehearsal',False)]:
  p=STATE/c['campaign_id']/c['date']/(name+'.json');private_file(p);d=json.loads(p.read_text())
  t=aware(d['at'])
  expected='compatibility-ready' if previous else 'dry-run-ready'
  if d.get('scope_hash')!=scope_hash(c) or d.get('outcome')!=expected or d.get('mode')!='dry-run':raise ValueError('rehearsal_not_ready')
  release=aware(c['release_at'])
  if previous:
   if t.astimezone(HELSINKI).date()!=release.astimezone(HELSINKI).date()-timedelta(days=1):raise ValueError('previous_day_required')
  elif not release<=t<=datetime.now(HELSINKI) or datetime.now(HELSINKI)-t>timedelta(minutes=5):raise ValueError('fresh_release_rehearsal_required')
def append_event(path,event,**kwargs):
 p=Path(path);_parent(p)
 payload={'event':event,'at':datetime.now(HELSINKI).isoformat(),'mode':kwargs.get('mode'),'detail':'diagnostic_redacted'}
 fd=os.open(p,os.O_CREAT|os.O_APPEND|os.O_WRONLY|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'a') as f:f.write(json.dumps(payload)+'\n');f.flush();os.fsync(f.fileno())

def private_error_text(*args):return 'diagnostic_redacted'
