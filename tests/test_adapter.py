import unittest,sys,subprocess,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
class AdapterTests(unittest.TestCase):
 def test_host_adapter(self):
  import host_adapter
  events=[]
  class Host:
   def capabilities(self):return {'durable':True,'timezone':'Europe/Helsinki'}
   def create_once(self,at,argv):events.append((at,argv));return 'local-test'
   def read(self,id):return {'id':id,'at':events[0][0],'argv':events[0][1]}
  with self.assertRaises(PermissionError):host_adapter.install(Host(),'2030-01-01T00:00:00+02:00',['python','safe.py'],False)
  self.assertEqual(host_adapter.install(Host(),'2030-01-01T00:00:00+02:00',['python','safe.py'],True)['id'],'local-test')
if __name__=='__main__':unittest.main()
