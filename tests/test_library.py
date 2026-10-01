"""Public API contracts, economics, numerical checks and export reproducibility."""
import csv
from dataclasses import FrozenInstanceError, replace
from importlib import resources
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from gpu_valuation import (AssetInputs, RecoveryScenario, asset_value,
                           residual_guarantee, value_asset, value_batch)
from gpu_valuation.surface import build_surface, load_config
from anc.verify import grid_dp
from reproduce import compare

ROOT = Path(__file__).resolve().parents[1]
BASE = AssetInputs(1, .08, .25, 2.5, .1)


class ValuationTests(unittest.TestCase):
    def test_known_values_and_legacy_api(self):
        result = value_asset(BASE)
        self.assertAlmostEqual(result.value, 3.989884905837461)
        self.assertAlmostEqual(result.retirement, 8.664339756999317)
        self.assertEqual(result.to_dict(), asset_value(1, .08, .25, 2.5, .1))
        self.assertAlmostEqual(result.value, result.cashflow_pv + result.salvage_pv)

    def test_immutable_inputs_and_results(self):
        for instance, field in [(BASE, 'revenue'), (value_asset(BASE), 'value')]:
            with self.assertRaises(FrozenInstanceError):
                setattr(instance, field, 2)

    def test_invalid_inputs(self):
        for name in ('revenue', 'erosion', 'operating_cost', 'salvage', 'discount_rate'):
            for bad in (True, '1', None, float('nan'), float('inf'), -1):
                with self.subTest(name=name, bad=bad), self.assertRaises(ValueError):
                    replace(BASE, **{name: bad})
        for name in ('erosion', 'salvage', 'discount_rate'):
            with self.assertRaises(ValueError):
                replace(BASE, **{name: 0})

    def test_numeric_overflow_is_rejected(self):
        with self.assertRaises(ValueError):
            value_asset(AssetInputs(1e308, .1, 0, 1e308, 1e308))

    def test_immediate_exit_and_boundary_continuity(self):
        for revenue in (0, .49, .5):
            result = value_asset(replace(BASE, revenue=revenue))
            self.assertEqual(result.value, BASE.salvage)
            self.assertEqual(result.retirement, 0)
            self.assertEqual(result.revenue_delta, 0)
        near = value_asset(replace(BASE, revenue=.5*(1+1e-8)))
        self.assertAlmostEqual(near.value, BASE.salvage, places=12)
        self.assertLess(near.erosion_sensitivity, 0)
        self.assertGreater(near.erosion_sensitivity, -1e-10)

    def test_value_and_life_can_diverge(self):
        old, new = value_batch([BASE, replace(BASE, revenue=.65, erosion=.02)])
        self.assertGreater(new.retirement, old.retirement)
        self.assertLess(new.value, old.value)

    def test_increasing_revenue_and_cost_effects(self):
        result = value_asset(BASE)
        self.assertGreater(value_asset(replace(BASE, revenue=1.2)).value, result.value)
        self.assertLess(value_asset(replace(BASE, operating_cost=.35)).value, result.value)
        self.assertLess(value_asset(replace(BASE, erosion=.10)).value, result.value)

    def test_currency_and_time_scaling(self):
        result = value_asset(BASE)
        dollars = value_asset(AssetInputs(10000, .08, 2500, 25000, .1))
        monthly = value_asset(AssetInputs(1/12, .08/12, .25/12, 2.5, .1/12))
        self.assertAlmostEqual(dollars.value/10000, result.value)
        self.assertAlmostEqual(monthly.value, result.value)
        self.assertAlmostEqual(monthly.retirement/12, result.retirement)

    def test_independent_stopping_and_sensitivities(self):
        import random
        rng = random.Random(20261001)
        for _ in range(40):
            inputs = AssetInputs(rng.uniform(.6, 3), rng.uniform(.01, .4),
                                 rng.uniform(.05, .3), rng.uniform(.5, 3), rng.uniform(.03, .2))
            result = value_asset(inputs)
            _, numerical, _ = grid_dp([(inputs.revenue, inputs.erosion)],
                                     inputs.operating_cost, inputs.salvage, inputs.discount_rate)
            self.assertLess(abs(numerical-result.value), .001)
            for field, derivative in [('revenue', result.revenue_delta),
                                      ('erosion', result.erosion_sensitivity)]:
                h = 1e-6
                plus = value_asset(replace(inputs, **{field: getattr(inputs, field)+h})).value
                minus = value_asset(replace(inputs, **{field: getattr(inputs, field)-h})).value
                self.assertTrue(math.isclose((plus-minus)/(2*h), derivative,
                                            rel_tol=1e-5, abs_tol=1e-6))

    def test_batch_and_dependency_injection(self):
        calls = []
        def custom(inputs):
            calls.append(inputs)
            return value_asset(inputs)
        output = value_batch(iter([BASE, BASE]), pricer=custom)
        self.assertEqual(len(calls), 2)
        self.assertEqual(output[0], output[1])
        self.assertEqual(value_batch([]), ())


class InsuranceTests(unittest.TestCase):
    def test_weighted_shortfalls_and_discount(self):
        rows = [RecoveryScenario(20000, .6), RecoveryScenario(8000, .3), RecoveryScenario(0, .1)]
        result = residual_guarantee(rows, guarantee=15000, deductible=1000,
                                    limit=10000, discount_rate=.05, horizon=3)
        self.assertEqual(result.scenario_payouts, (0, 6000, 10000))
        self.assertAlmostEqual(result.expected_payout, 2800)
        self.assertAlmostEqual(result.probability_of_payout, .4)
        self.assertAlmostEqual(result.present_value_expected_payout, 2800*math.exp(-.15))

    def test_no_silent_probability_normalization(self):
        for rows in ([], [RecoveryScenario(0, .9)], [RecoveryScenario(0, .6)]*2):
            with self.assertRaises(ValueError):
                residual_guarantee(rows, 100)

    def test_zero_limit_and_full_recovery(self):
        self.assertEqual(residual_guarantee([RecoveryScenario(0, 1)], 100, limit=0).expected_payout, 0)
        self.assertEqual(residual_guarantee([RecoveryScenario(200, 1)], 100).expected_payout, 0)
        self.assertEqual(residual_guarantee([RecoveryScenario(0, 1)], 100).expected_payout, 100)

    def test_validation(self):
        for bad in (-1, float('nan'), True):
            with self.assertRaises(ValueError):
                RecoveryScenario(bad, 1)
        for bad in (1.1, -1, True):
            with self.assertRaises(ValueError):
                RecoveryScenario(10, bad)
        for field in ('deductible', 'limit', 'discount_rate', 'horizon'):
            with self.assertRaises(ValueError):
                residual_guarantee([RecoveryScenario(0, 1)], 100, **{field: -1})


class ExportTests(unittest.TestCase):
    def test_packaged_defaults_match_documented_example(self):
        embedded = json.loads(resources.files('gpu_valuation').joinpath('default_surface.json').read_text())
        self.assertEqual(embedded, load_config(ROOT/'pricing/example.json'))

    def test_export_matches_published_surface(self):
        config = load_config(ROOT/'pricing/example.json')
        with tempfile.TemporaryDirectory() as temp:
            summary = build_surface(config, temp)
            expected = json.loads((ROOT/'pricing/output/summary.json').read_text())
            compare(expected, summary)
            with (Path(temp)/'surface.csv').open() as actual_file, (ROOT/'pricing/output/surface.csv').open() as expected_file:
                actual_rows = list(csv.DictReader(actual_file))
                expected_rows = list(csv.DictReader(expected_file))
            self.assertEqual(len(actual_rows), len(expected_rows))
            for actual, expected in zip(actual_rows, expected_rows):
                self.assertEqual(actual.keys(), expected.keys())
                for key in actual:
                    if key == 'longer_life_lower_value':
                        self.assertEqual(actual[key], expected[key])
                    else:
                        self.assertTrue(math.isclose(float(actual[key]), float(expected[key]),
                                                   rel_tol=1e-9, abs_tol=1e-10), key)

    def test_custom_pricer_and_invalid_config(self):
        config = load_config(ROOT/'pricing/example.json')
        config['grid_points'] = 3
        calls = []
        def custom(inputs):
            calls.append(inputs)
            return value_asset(inputs)
        with tempfile.TemporaryDirectory() as temp:
            summary = build_surface(config, temp, pricer=custom)
            self.assertEqual(summary['rows'], 9)
            self.assertEqual(summary['model'], 'caller-supplied pricing callable')
            self.assertEqual(len(calls), 20)
            config['erosion_min'] = 0
            with self.assertRaises(ValueError):
                build_surface(config, temp)

    def test_module_cli_from_another_directory(self):
        import os
        with tempfile.TemporaryDirectory() as temp:
            env = dict(os.environ, PYTHONPATH=str(ROOT))
            result = subprocess.run([sys.executable, '-m', 'gpu_valuation', '--output', temp],
                                    cwd=temp, env=env, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((Path(temp)/'summary.json').is_file())


if __name__ == '__main__':
    unittest.main()
