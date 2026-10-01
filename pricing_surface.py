"""Deterministic GPU asset valuation, not a traded derivative pricing model.

Python 3.9+, standard library. Run python3 pricing_surface.py --help.
All flow inputs use the same currency and time unit. Rates are continuous.
"""
import argparse
import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def asset_value(revenue, erosion, operating_cost, salvage, discount_rate):
    """Value optimal operation then salvage with exponentially declining revenue.

    Revenue is the current gross cash flow per time unit, already adjusted for
    utilization. Operating cost is the corresponding constant cash cost. Fixed
    ownership charges, idle costs, physical failure and switching are excluded.
    This finite-retirement benchmark requires erosion > 0, rho > 0 and S > 0.
    """
    values = (revenue, erosion, operating_cost, salvage, discount_rate)
    if any(isinstance(x, bool) or not isinstance(x, (int, float))
           or not math.isfinite(x) for x in values):
        raise ValueError('Inputs must be finite numbers')
    if min(revenue, operating_cost) < 0 or min(erosion, salvage, discount_rate) <= 0:
        raise ValueError('Require revenue/cost >= 0; erosion/salvage/discount > 0')
    threshold = operating_cost + discount_rate * salvage
    if revenue <= threshold:
        return dict(value=salvage, retirement=0.0, cashflow_pv=0.0,
                    salvage_pv=salvage, revenue_delta=0.0, erosion_sensitivity=0.0)
    retirement = math.log(revenue / threshold) / erosion
    k = discount_rate + erosion
    annuity = -math.expm1(-k * retirement) / k
    cashflow = (revenue * annuity - operating_cost *
                (-math.expm1(-discount_rate * retirement)) / discount_rate)
    salvage_pv = salvage * math.exp(-discount_rate * retirement)
    # Envelope derivatives: the optimized terminal-time term cancels.
    x = k * retirement
    if x < 1e-3:
        duration_integral = retirement**2 * sum(
            (-x)**n / (math.factorial(n) * (n + 2)) for n in range(8))
    else:
        duration_integral = (-math.expm1(-x) - x * math.exp(-x)) / k**2
    return dict(value=cashflow + salvage_pv, retirement=retirement,
                cashflow_pv=cashflow, salvage_pv=salvage_pv,
                revenue_delta=annuity,
                erosion_sensitivity=-revenue * duration_integral)


def load_config(path):
    config = json.loads(Path(path).read_text())
    for key in ('currency', 'time_unit', 'evidence_status'):
        if not isinstance(config.get(key), str) or not config[key].strip():
            raise ValueError(f'{key} must be a nonempty string')
    keys = ('revenue', 'operating_cost', 'salvage', 'discount_rate',
            'baseline_erosion', 'revenue_multiplier_min',
            'revenue_multiplier_max', 'erosion_min', 'erosion_max')
    for key in keys:
        value = config[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f'{key} must be finite')
    if not (0 <= config['revenue_multiplier_min'] < config['revenue_multiplier_max']):
        raise ValueError('Require 0 <= multiplier min < max')
    if not (0 < config['erosion_min'] < config['erosion_max']):
        raise ValueError('Require 0 < erosion min < max')
    n = config['grid_points']
    if type(n) is not int or not 3 <= n <= 501:
        raise ValueError('grid_points must be an integer from 3 to 501')
    if config['revenue'] <= 0:
        raise ValueError('Baseline revenue must be positive')
    value_for(config, 1, config['baseline_erosion'])
    return config


def value_for(config, multiplier, erosion):
    return asset_value(config['revenue'] * multiplier, erosion,
                       config['operating_cost'], config['salvage'],
                       config['discount_rate'])


def build_surface(config, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    baseline = value_for(config, 1, config['baseline_erosion'])
    n = config['grid_points']
    def grid(low, high):
        return [low + (high - low) * i / (n - 1) for i in range(n)]
    rows = []
    for erosion in grid(config['erosion_min'], config['erosion_max']):
        for multiplier in grid(config['revenue_multiplier_min'], config['revenue_multiplier_max']):
            result = value_for(config, multiplier, erosion)
            row = dict(revenue_multiplier=multiplier, erosion=erosion, **result)
            row['value_change_pct'] = 100 * (result['value'] / baseline['value'] - 1)
            row['life_change'] = result['retirement'] - baseline['retirement']
            # Exact repricing after +1 percentage point of erosion (not a Greek).
            row['value_change_erosion_plus_1pp'] = (
                value_for(config, multiplier, erosion + .01)['value'] - result['value'])
            row['longer_life_lower_value'] = (
                row['life_change'] > 1e-10 and row['value_change_pct'] < -1e-10)
            rows.append(row)
    with (output / 'surface.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = dict(inputs=config, baseline=baseline,
                   counterexample=value_for(config, .65, .02),
                   rows=len(rows), model='deterministic one-tier optimal retirement')
    (output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=ROOT / 'pricing/example.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'pricing/output')
    args = parser.parse_args()
    summary = build_surface(load_config(args.config), args.output)
    print(json.dumps(summary, indent=2))
    print(f'Wrote CSV and metadata to {args.output}')


if __name__ == '__main__':
    main()
