"""Boundary and input checks for the economic screen, not empirical tests."""
import json
from pathlib import Path
from math import isclose
from retention_screen import screen

rows=json.loads((Path(__file__).parent/'screen-example.json').read_text())['cases']
r=[screen(row) for row in rows]
assert r[0]['break_even_service_price'] is None
assert r[3]['break_even_service_price'] is None
assert isclose(r[0]['retention_margin'],r[3]['retention_margin'])
assert r[1]['stationary_retention_strictly_preferred']
assert not r[2]['stationary_retention_strictly_preferred']
row=dict(rows[1]); threshold=r[1]['break_even_service_price']
row['service_price']=threshold
assert abs(screen(row)['retention_margin'])<1e-12
row['service_price']=threshold*1.01
assert screen(row)['retention_margin']>0
row['service_price']=threshold*.99
assert screen(row)['retention_margin']<0
for key,value in [('utilization',-1),('salvage',0),('throughput',0),('service_price',float('nan')),('feasible','true')]:
    bad=dict(rows[1]);bad[key]=value
    try:screen(bad)
    except ValueError:pass
    else:raise AssertionError(key)
print('PASS: infeasibility, idle option, break-even crossing, adverse price response and input checks')
