import sys, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import host_adapter

class ReadinessTests(unittest.TestCase):
 def setUp(self):
  self.job={'id':'fictional-job','at':'2030-01-01T00:00:00+02:00','argv':['python','safe.py']}
  job=self.job
  class Host:
   def capabilities(self):return {'durable':True,'timezone':'Europe/Helsinki'}
   def read(self,id):return dict(job)
  self.host=Host()
  self.args=dict(scope_hash='fictional-scope',scope_authorized=True,contacts_private=True,provider_preflight={'scope_hash':'fictional-scope','outcome':'compatibility-ready','mode':'dry-run'},delivery_verified=True)
 def check(self,**changes):
  return host_adapter.readiness(self.host,self.job,**dict(self.args,**changes))
 def test_preparation_not_inventory_or_release_permission(self):
  result=self.check()
  self.assertEqual(result['outcome'],'preparation-ready')
  self.assertFalse(result['inventory_verified'])
  self.assertFalse(result['commit_allowed'])
 def test_each_gate_fails_closed(self):
  for key in ['scope_authorized','contacts_private','delivery_verified']:
   for value in [False,None,1,'yes']:
    with self.subTest(key=key,value=value):self.assertEqual(self.check(**{key:value})['outcome'],'preparation-blocked')
  for evidence in [{},{'scope_hash':'other','outcome':'compatibility-ready','mode':'dry-run'},{'scope_hash':'fictional-scope','outcome':'dry-run-ready','mode':'dry-run'},{'scope_hash':'fictional-scope','outcome':'compatibility-ready','mode':'mock'}]:
   with self.subTest(evidence=evidence):self.assertEqual(self.check(provider_preflight=evidence)['outcome'],'preparation-blocked')
 def test_scheduler_readback_and_capabilities(self):
  for actual in [{},dict(self.job,at='2030-01-02T00:00:00+02:00')]:
   with patch.object(self.host,'read',return_value=actual):self.assertEqual(self.check()['outcome'],'preparation-blocked')
  with patch.object(self.host,'read',side_effect=RuntimeError('private')):self.assertEqual(self.check()['outcome'],'preparation-blocked')
  with patch.object(self.host,'capabilities',return_value={'durable':False}):self.assertEqual(self.check()['outcome'],'preparation-blocked')
