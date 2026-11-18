"""Host-neutral scheduler contract. No built-in host mutation."""
from typing import Protocol
from safety import aware
class Scheduler(Protocol):
 def capabilities(self)->dict:...
 def create_once(self,at:str,argv:list[str])->str:...
 def read(self,id:str)->dict:...
def install(host:Scheduler,at:str,argv:list[str],approved:bool=False)->dict:
 if approved is not True:raise PermissionError('scheduler_change_requires_user_approval')
 aware(at)
 caps=host.capabilities()
 if caps.get('durable') is not True or caps.get('timezone')!='Europe/Helsinki':raise ValueError('durable_helsinki_scheduler_required')
 if not argv or any(not isinstance(a,str) for a in argv):raise ValueError('argv_required')
 id=host.create_once(at,argv);actual=host.read(id)
 if actual!={'id':id,'at':at,'argv':argv}:raise RuntimeError('scheduler_readback_mismatch')
 return actual

def readiness(host:Scheduler,expected_job:dict,*,scope_hash:str,
              scope_authorized:bool=False,contacts_private:bool=False,
              provider_preflight:dict|None=None,delivery_verified:bool=False)->dict:
 """Read-only preparation snapshot, NOT a commit gate or inventory promise.

 The caller must verify authorization, private contacts and delivery with its
 own integrations; these explicit attestations default to blocked. No contacts
 or delivery identifiers are returned. The provider evidence must be from a
 writes-blocked previous-day compatibility check for this exact scope.
 """
 checks={'scope_authorized':scope_authorized is True and bool(scope_hash),
         'contacts_private':contacts_private is True,
         'delivery_verified':delivery_verified is True}
 evidence=provider_preflight or {}
 checks['provider_preflight']=bool(scope_hash) and evidence.get('scope_hash')==scope_hash and evidence.get('outcome')=='compatibility-ready' and evidence.get('mode')=='dry-run'
 checks['scheduler_readback']=False
 try:
  caps=host.capabilities()
  aware(expected_job['at'])
  valid_job=set(expected_job)=={'id','at','argv'} and bool(expected_job['id']) and isinstance(expected_job['argv'],list) and bool(expected_job['argv']) and all(isinstance(v,str) and v for v in expected_job['argv'])
  checks['scheduler_readback']=valid_job and caps.get('durable') is True and caps.get('timezone')=='Europe/Helsinki' and host.read(expected_job['id'])==expected_job
 except Exception:
  pass  # Never echo host exceptions, which may contain private delivery data.
 return {'outcome':'preparation-ready' if all(checks.values()) else 'preparation-blocked',
         'checks':checks,'inventory_verified':False,'commit_allowed':False}
