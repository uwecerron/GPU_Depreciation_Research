"""Pure deterministic valuation; no filesystem, plotting, or network access."""
import math
from typing import Iterable, Protocol, Tuple
from .models import AssetInputs, ValuationResult


class Pricer(Protocol):
    """Replaceable pricing callable for batch/surface clients."""
    def __call__(self, inputs: AssetInputs) -> ValuationResult: ...


def _calculate(revenue, erosion, operating_cost, salvage, discount_rate):
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
    if not math.isfinite(threshold) or threshold <= 0 or not math.isfinite(discount_rate + erosion):
        raise ValueError("Inputs exceed the supported floating-point domain")
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


def value_asset(inputs: AssetInputs) -> ValuationResult:
    """Price an asset under constant-cost, constant-salvage assumptions.

    No financing, taxes, stochastic prices, physical failures or transaction
    costs are inferred. Raises ValueError outside the supported numeric domain.
    """
    if not isinstance(inputs, AssetInputs):
        raise TypeError('inputs must be AssetInputs')
    try:
        result = _calculate(inputs.revenue, inputs.erosion, inputs.operating_cost,
                            inputs.salvage, inputs.discount_rate)
    except (OverflowError, ZeroDivisionError) as error:
        raise ValueError('Inputs exceed the supported floating-point domain') from error
    if not all(math.isfinite(v) for v in result.values()):
        raise ValueError('Inputs exceed the supported floating-point domain')
    return ValuationResult(**result)


def value_batch(inputs: Iterable[AssetInputs], pricer: Pricer = value_asset) -> Tuple[ValuationResult, ...]:
    """Preserve scenario order. No shared mutable state or implicit parallelism."""
    return tuple(pricer(item) for item in inputs)


def asset_value(revenue, erosion, operating_cost, salvage, discount_rate):
    """Backward-compatible dictionary API; new clients can use value_asset."""
    return value_asset(AssetInputs(revenue, erosion, operating_cost,
                                  salvage, discount_rate)).to_dict()
