#!/usr/bin/env python3
"""Real, synthetic-data integration smoke. Requires a running loopback API and Nemotron."""
import json,time,threading
from pathlib import Path
from datetime import datetime,timezone
import httpx
ROOT=Path(__file__).resolve().parents[1]
BASE='http://127.0.0.1:8000'
evidence={'timestamp':datetime.now(timezone.utc).isoformat(),'base_url':BASE,'mode':'real local inference / fictional fixtures','offline_wan_test':'not performed'}
sse=[]
def listen():
 try:
  with httpx.stream('GET',BASE+'/api/events',timeout=200,trust_env=False) as r:
   event=''
   for line in r.iter_lines():
    if line.startswith('event: '):event=line[7:]
    if line.startswith('data: '):
     payload=json.loads(line[6:]);sse.append({'event':event,'data':payload})
 except Exception as e:evidence['sse_connection_error']=str(e)
threading.Thread(target=listen,daemon=True).start()
with httpx.Client(base_url=BASE,timeout=200,trust_env=False) as c:
 def get(path):
  r=c.get(path);r.raise_for_status();return r.json()
 def post(path,body):
  r=c.post(path,json=body);r.raise_for_status();return r.json()
 evidence['health']=get('/api/health');assert evidence['health']['local_inference']['available']
 evidence['system']=get('/api/system')
 evidence['jobs']=[]
 for agent,prompt in [('hr','How many days of PTO do full-time employees receive?'),('finance','Analyze our invoices for duplicates, overdue amounts, and totals.'),('support','A fictional customer cannot sign into the portal before a meeting. Draft a helpful response.')]:
  print('Submitting real '+agent+' job',flush=True)
  job=post('/api/jobs',{'agent_id':agent,'prompt':prompt,'priority':'urgent' if agent=='support' else 'standard'})
  until=time.monotonic()+195
  while time.monotonic()<until:
   job=get('/api/jobs/'+job['id'])
   if job['status'] in ['completed','error','blocked']:break
   time.sleep(.25)
  evidence['jobs'].append(job)
  assert job['status']=='completed',job
  assert job['result']['source']=='local_nemotron',job
  if agent=='hr':assert '20' in job['result']['answer'] and job['result']['sources']
  if agent=='finance':
   facts=job['result']['calculations'];assert facts['overdue_total']=='4950.50' and facts['deduplicated_overdue_total']=='3750.50'
   assert job['result']['duplicate_invoices'][0]['invoice_id']=='INV-1001'
  print(agent+' passed: '+str(job['metrics'])+'\n'+job['result']['answer'],flush=True)
 evidence['benchmark']=post('/api/scenarios/compare',{'include_narrative':True})
 assert evidence['benchmark']['kind']=='measured_scheduler_microbenchmark'
 evidence['security']=post('/api/security/demo',{})
 assert evidence['security']['blocked'] and evidence['security']['executed'] is False and evidence['security']['network_request_made'] is False
 r=c.post('/api/optimizer/approve',json={'policy':'priority','approved':False});assert r.status_code==403
 evidence['unapproved_policy_rejected']=r.status_code
 evidence['events']=sse
 assert any(e['event']=='job_updated' and e['data']['status']=='running' for e in sse)
 assert any(e['event']=='job_updated' and e['data']['status']=='completed' for e in sse)
 evidence['metrics']=get('/api/metrics')
 (ROOT/'docs/evidence/live-smoke.json').write_text(json.dumps(evidence,indent=2))
 print('PASS: real HR/Finance/Support, SSE status changes, measured comparison, security block, approval refusal. Evidence saved.',flush=True)
