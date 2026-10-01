"""Independent numerical checks of valuation and sensitivities. Standard library."""
import math
from pathlib import Path
import random
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pricing_surface import asset_value
from anc.verify import grid_dp


def main():
    rng = random.Random(20261001)
    for _ in range(40):
        revenue = rng.uniform(.6, 3)
        erosion = rng.uniform(.01, .4)
        cost = rng.uniform(.05, .3)
        salvage = rng.uniform(.5, 3)
        rho = rng.uniform(.03, .2)
        result = asset_value(revenue, erosion, cost, salvage, rho)
        _, grid_value, _ = grid_dp([(revenue, erosion)], cost, salvage, rho)
        assert abs(result['value'] - grid_value) < .001
        h = 1e-6
        dr = (asset_value(revenue+h, erosion, cost, salvage, rho)['value'] -
              asset_value(revenue-h, erosion, cost, salvage, rho)['value'])/(2*h)
        dd = (asset_value(revenue, erosion+h, cost, salvage, rho)['value'] -
              asset_value(revenue, erosion-h, cost, salvage, rho)['value'])/(2*h)
        assert math.isclose(dr, result['revenue_delta'], rel_tol=1e-5, abs_tol=1e-6)
        assert math.isclose(dd, result['erosion_sensitivity'], rel_tol=1e-5, abs_tol=1e-6)
        scaled = asset_value(revenue*10000, erosion, cost*10000, salvage*10000, rho)
        assert math.isclose(scaled['value'], result['value']*10000, rel_tol=1e-12)
        assert math.isclose(scaled['retirement'], result['retirement'], abs_tol=1e-12)
    baseline = asset_value(1, .08, .25, 2.5, .1)
    adverse = asset_value(.65, .02, .25, 2.5, .1)
    assert adverse['retirement'] > baseline['retirement']
    assert adverse['value'] < baseline['value']
    for revenue in [0, .49, .5]:
        result = asset_value(revenue, .08, .25, 2.5, .1)
        assert result['value'] == 2.5 and result['retirement'] == 0
    for erosion in [0, -.1, float('nan'), float('inf'), True]:
        try:
            asset_value(1, erosion, .25, 2.5, .1)
        except ValueError:
            pass
        else:
            raise AssertionError('Invalid erosion was accepted')
    # Near the retirement boundary, the erosion sensitivity should approach zero.
    near = asset_value(.5*(1+1e-8), .08, .25, 2.5, .1)
    assert -1e-10 < near['erosion_sensitivity'] < 0
    print('PASS: 40 independent stopping optimizations, sensitivity differences, '
          'currency scaling, exit boundary, input validation and counterexample')


if __name__ == '__main__':
    main()
