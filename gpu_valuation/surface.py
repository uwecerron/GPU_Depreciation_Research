"""Configuration and CSV export, separate from the pricing kernel."""
import csv
import json
import math
from pathlib import Path
from .models import AssetInputs
from .valuation import value_asset


def load_config(path):
    return validate_config(json.loads(Path(path).read_text()))


def validate_config(config):
    config = dict(config)
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


def value_for(config, multiplier, erosion, pricer=value_asset):
    return pricer(AssetInputs(config['revenue'] * multiplier, erosion,
                              config['operating_cost'], config['salvage'],
                              config['discount_rate'])).to_dict()


def build_surface(config, output, pricer=value_asset):
    config = validate_config(config)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    baseline = value_for(config, 1, config['baseline_erosion'], pricer)
    if baseline['value'] <= 0:
        raise ValueError('Surface percentage comparisons require positive baseline value')
    n = config['grid_points']
    def grid(low, high):
        return [low + (high - low) * i / (n - 1) for i in range(n)]
    rows = []
    for erosion in grid(config['erosion_min'], config['erosion_max']):
        for multiplier in grid(config['revenue_multiplier_min'], config['revenue_multiplier_max']):
            result = value_for(config, multiplier, erosion, pricer)
            row = dict(revenue_multiplier=multiplier, erosion=erosion, **result)
            row['value_change_pct'] = 100 * (result['value'] / baseline['value'] - 1)
            row['life_change'] = result['retirement'] - baseline['retirement']
            # Exact repricing after +1 percentage point of erosion (not a Greek).
            row['value_change_erosion_plus_1pp'] = (
                value_for(config, multiplier, erosion + .01, pricer)['value'] - result['value'])
            row['longer_life_lower_value'] = (
                row['life_change'] > 1e-10 and row['value_change_pct'] < -1e-10)
            rows.append(row)
    with (output / 'surface.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = dict(inputs=config, baseline=baseline,
                   counterexample=value_for(config, .65, .02, pricer),
                   rows=len(rows), model=('deterministic one-tier optimal retirement' if pricer is value_asset
                          else 'caller-supplied pricing callable'))
    (output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    return summary

