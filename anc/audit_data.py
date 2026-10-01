"""Public data feasibility audit; no causal claim or fitted release effect."""
import json, hashlib, urllib.request, sys
from pathlib import Path
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parent
URL='https://getdeploying.com/dataset/gpu-prices/weekly.json'
snapshot=ROOT/'data'/'weekly.json'
if '--fetch' in sys.argv or not snapshot.exists():
    req=urllib.request.Request(URL,headers={'User-Agent':'Research data coverage audit'})
    raw=urllib.request.urlopen(req,timeout=45).read()
    snapshot.write_bytes(raw)
    retrieved=datetime.now(timezone.utc).isoformat()
else:
    raw=snapshot.read_bytes()
    previous=json.loads((ROOT/'data_audit.json').read_text())
    retrieved=previous['retrieved_utc']
obj=json.loads(raw)
rows=obj if isinstance(obj,list) else obj.get('data',obj.get('rows',[]))
if not isinstance(rows,list) or not rows:
    raise ValueError('Inspect source schema: '+str(type(obj)))
summary={}
for gpu in ['nvidia-v100','nvidia-a100','nvidia-h100']:
    rr=[r for r in rows if r.get('gpu_slug')==gpu and r.get('billing_type')=='ON_DEMAND']
    summary[gpu]={'rows':len(rr),'first_date':min((r['date'] for r in rr),default=None),'last_date':max((r['date'] for r in rr),default=None)}
events={'FlashAttention paper v1':'2022-05-27','GPTQ paper v1':'2022-10-31','PagedAttention paper v1':'2023-09-12'}
result={'url':URL,'retrieved_utc':retrieved,'sha256':hashlib.sha256(raw).hexdigest(),'total_rows':len(rows),'columns':list(rows[0]),'selected_on_demand_series':summary,'paper_publication_dates_not_adoption_dates':events,'provider_identifier_present':'provider' in rows[0],'all_target_events_precede_selected_series':all(s['first_date'] is None or max(events.values())<s['first_date'] for s in summary.values()),'conclusion':'Coverage audit only. No provider-matched release effect identified. Posted aggregates do not verify contractability or asset value.','attribution':'GetDeploying, GPU rental price history, https://getdeploying.com/dataset/gpu-prices, CC BY 4.0 https://creativecommons.org/licenses/by/4.0/'}
(ROOT/'data_audit.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
