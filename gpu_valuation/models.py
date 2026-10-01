"""Immutable, validated public types. Amounts share a currency and time unit."""
from dataclasses import asdict, dataclass
import math
from numbers import Real
from typing import Dict


def finite_number(name: str, value: float, minimum: float = 0, strict: bool = False) -> float:
    """Accept real scalars (including compatible NumPy scalars), not booleans."""
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f'{name} must be a finite real number')
    try:
        number = float(value)
    except (ValueError, OverflowError) as error:
        raise ValueError(f'{name} is outside the floating-point range') from error
    if not math.isfinite(number) or number < minimum or (strict and number == minimum):
        operator = '>' if strict else '>='
        raise ValueError(f'{name} must be finite and {operator} {minimum}')
    return number


@dataclass(frozen=True)
class AssetInputs:
    """R,c: currency/time; S: currency; d,rho: continuous rates per time."""
    revenue: float
    erosion: float
    operating_cost: float
    salvage: float
    discount_rate: float

    def __post_init__(self):
        for name in ('revenue', 'erosion', 'operating_cost', 'salvage', 'discount_rate'):
            number = finite_number(name, getattr(self, name),
                                   strict=name in ('erosion', 'salvage', 'discount_rate'))
            object.__setattr__(self, name, number)


@dataclass(frozen=True)
class ValuationResult:
    """Value components: currency; retirement/delta: time; dV/dd: currency*time."""
    value: float
    retirement: float
    cashflow_pv: float
    salvage_pv: float
    revenue_delta: float
    erosion_sensitivity: float

    def __post_init__(self):
        for name in ('value', 'retirement', 'cashflow_pv', 'salvage_pv',
                     'revenue_delta', 'erosion_sensitivity'):
            minimum = 0 if name in ('value', 'retirement', 'salvage_pv') else -math.inf
            object.__setattr__(self, name, finite_number(name, getattr(self, name), minimum))

    def to_dict(self) -> Dict[str, float]:
        return asdict(self)
