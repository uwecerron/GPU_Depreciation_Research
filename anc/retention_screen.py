"""Stationary screening only. No empirical lifetime or asset-price forecast.
Usage: python3 anc/retention_screen.py anc/screen-example.json
All flow quantities must use the declared common currency and time unit.
"""
import json
import math
import sys
from pathlib import Path


def screen(row):
    feasible = row['feasible']
    if type(feasible) is not bool:
        raise ValueError('feasible must be a Boolean')
    keys = ['utilization', 'active_cost', 'fixed_cost', 'discount_rate', 'salvage', 'service_price']
    for key in keys:
        if isinstance(row[key], bool) or not isinstance(row[key], (int, float)) or not math.isfinite(row[key]):
            raise ValueError(f'{key} must be a finite number')
    u, c, F, rho, S, p = (row[k] for k in keys)
    if not 0 <= u <= 1 or min(c,F,p) < 0 or min(rho,S) <= 0:
        raise ValueError('Require 0<=u<=1; c,F,p>=0; rho,S>0')
    q = row.get('throughput')
    if feasible and (isinstance(q, bool) or not isinstance(q, (int,float)) or not math.isfinite(q) or q <= 0):
        raise ValueError('Feasible service requires positive finite throughput')
    carry = F + rho*S
    operating = max(0., u*(p*q-c)) if feasible and u>0 else 0.
    threshold = (u*c+carry)/(u*q) if feasible and u>0 else None
    return {'label':row['label'], 'best_operating_surplus':operating,
            'retention_margin':operating-carry,'break_even_service_price':threshold,
            'stationary_retention_strictly_preferred':operating>carry,
            'interpretation':'Stationary screen, not a retirement date or empirical result.'}


def run():
    source = Path(sys.argv[1])
    payload = json.loads(source.read_text())
    if not payload.get('currency') or not payload.get('time_unit') or not payload.get('evidence_status'):
        raise ValueError('Declare currency, time_unit and evidence_status')
    results=[screen(r) for r in payload['cases']]
    print(json.dumps({'evidence_status':payload['evidence_status'],'currency':payload['currency'],
                      'time_unit':payload['time_unit'],'results':results},indent=2,allow_nan=False))

if __name__ == '__main__':
    run()
