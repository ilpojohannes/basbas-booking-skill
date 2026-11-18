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
