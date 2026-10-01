"""Illustrative residual-guarantee settlement, not a resale estimator or tariff.

Recovery scenarios and probabilities must come from external evidence. There is
no implied calibration, coverage interpretation, diversification, or premium.
"""
from dataclasses import dataclass
import math
from typing import Iterable, Tuple
from .models import finite_number


@dataclass(frozen=True)
class RecoveryScenario:
    """Net sale proceeds at a common settlement date; same currency as guarantee."""
    net_recovery: float
    probability: float

    def __post_init__(self):
        for name in ('net_recovery', 'probability'):
            object.__setattr__(self, name, finite_number(name, getattr(self, name)))
        if self.probability > 1:
            raise ValueError('probability must be <= 1')


@dataclass(frozen=True)
class GuaranteeResult:
    expected_payout: float
    present_value_expected_payout: float
    probability_of_payout: float
    scenario_payouts: Tuple[float, ...]


def residual_guarantee(scenarios: Iterable[RecoveryScenario], guarantee: float,
                       deductible: float = 0, limit: float = float('inf'),
                       discount_rate: float = 0, horizon: float = 0) -> GuaranteeResult:
    """Pay min(limit, max(guarantee - net_recovery - deductible, 0)).

    This illustrative deductible applies to the shortfall. Policy wording can
    differ. No probabilities are inferred or silently normalized. Expected loss
    excludes expenses, capital, profit, tax, reinsurance and default risk.
    """
    guarantee = finite_number('guarantee', guarantee)
    deductible = finite_number('deductible', deductible)
    horizon = finite_number('horizon', horizon)
    discount_rate = finite_number('discount_rate', discount_rate)
    if limit != float('inf') or isinstance(limit, bool):
        limit = finite_number('limit', limit)
    rows = tuple(scenarios)
    if not rows or any(not isinstance(row, RecoveryScenario) for row in rows):
        raise ValueError('Supply at least one RecoveryScenario')
    if not math.isclose(math.fsum(row.probability for row in rows), 1,
                        rel_tol=0, abs_tol=1e-12):
        raise ValueError('Scenario probabilities must sum to one')
    payouts = tuple(min(limit, max(guarantee-row.net_recovery-deductible, 0))
                    for row in rows)
    expected = math.fsum(row.probability*payout for row, payout in zip(rows, payouts))
    probability = math.fsum(row.probability for row, payout in zip(rows, payouts) if payout > 0)
    return GuaranteeResult(expected, expected*math.exp(-discount_rate*horizon), probability, payouts)
