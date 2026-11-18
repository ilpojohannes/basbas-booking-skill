"""Local smoke check only: never installs or starts a scheduler."""
import json,shutil
from pathlib import Path

def check():
 result={'python':True,'scheduler_candidates':{x:bool(shutil.which(x)) for x in ['crontab','systemctl','hermes']},'durable_scheduler_verified':False,'auto_installs':False}
 try:
  from playwright.sync_api import sync_playwright
  with sync_playwright() as p:
   b=p.chromium.launch(headless=True);page=b.new_page();page.set_content('<h1>Smoke</h1>');result['browser_smoke']=page.locator('h1').inner_text()=='Smoke';b.close()
 except Exception as e:result.update(browser_smoke=False,blocker=type(e).__name__)
 return result
if __name__=='__main__':print(json.dumps(check()))
