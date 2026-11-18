"""Conservative share-package scan. Emits filenames/rules, never matched secrets."""
import json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RULES={
 'absolute_home':r'/home/[^\s\"\']+|/Users/[^\s\"\']+',
 'delivery_destination':r'telegram:-?\d+|chat_id\s*[:=]\s*[\"\']?-?\d+',
 'credential':r'\b(?:sk-|ghp_|github_pat_|xoxb-)[A-Za-z0-9_-]{15,}',
}
def scan():
 findings=[]
 for p in ROOT.rglob('*'):
  if not p.is_file() or '__pycache__' in p.parts or '.git' in p.parts:continue
  if p.name in {'.env','auth.json'}:findings.append({'file':str(p.relative_to(ROOT)),'rule':'private_filename'})
  try:s=p.read_text()
  except UnicodeError:findings.append({'file':str(p.relative_to(ROOT)),'rule':'unreviewed_binary'});continue
  # Pattern definitions themselves are not payloads.
  if p==Path(__file__).resolve():continue
  for rule,pattern in RULES.items():
   if re.search(pattern,s,re.I):findings.append({'file':str(p.relative_to(ROOT)),'rule':rule})
  for email in re.findall(r'[\w.+-]+@[\w.-]+\.[A-Za-z]+',s):
   if not email.endswith('@example.invalid'):findings.append({'file':str(p.relative_to(ROOT)),'rule':'nonfictional_email'})
 return findings
if __name__=='__main__':
 findings=scan();print(json.dumps({'ok':not findings,'findings':findings}));sys.exit(bool(findings))
