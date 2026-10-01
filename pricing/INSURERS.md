# Residual value and insurance: what this library can support

The main surface values operating cash flows plus an **assumed** salvage amount. It does not independently estimate salvage. Substituting that output for observed sale proceeds would conflate operating value with recovery value, and using the same assumed residual to validate itself would be circular.

An insurer needs a dated, conditional distribution of net recovery for a precisely specified asset and policy. For a residual-value guarantee this is different from physical-damage replacement cost, book value, current income value, or a quoted GPU-hour rental rate. Policy terms govern which losses are covered.

## A defensible workflow

1. **Define the asset and settlement.** Record GPU SKU and memory, board/module/server configuration, serial cohort and deployment age, condition, warranty, interconnect, location and transfer restrictions. Specify settlement date, permitted sale process and whether racks, power rights or contracts transfer. A system sale is not automatically a chip price.
2. **Anchor recovery to completed transactions.** Collect realized secondary-market sales, auction outcomes and remarketing costs. Record unsold lots and time to sale as well as successful sales. Asking prices and rental indexes are auxiliary features, not realized residuals.
3. **Use the DCF as a diagnostic.** Test whether a buyer's plausible workload margins can support the proposed price. Stress software compatibility, quality-matched throughput, rental rates, utilization, power, rack opportunity cost and repair costs. The installed owner's margins need not be available to a new buyer. Do not count the remaining service stream twice, both as income and a separate resale value at the same date.
4. **Estimate joint recovery scenarios.** Fit and backtest against held-out device cohorts and future calendar periods. Reflect architecture launches, oversupply, export restrictions, failure, liquidation timing and shared market shocks. Add uncertainty for thinly traded SKUs instead of treating a fitted mean as a guaranteed floor. In a fleet, obsolescence and forced-sale losses are correlated.
5. **Apply the actual contract.** Convert recovery scenarios into covered shortfalls, deductibles, caps and exclusions. Expected loss is only one component of a premium; expenses, capital, dependence, reinsurance, profit and other contract risks are separate.

This approach can replace a single age-based residual assumption with an auditable range, expose portfolios that depend on optimistic software gains, and help choose guarantee levels or deductibles. It does not make the current synthetic surface a calibrated underwriting model.

For orientation, IFRS 13 describes fair value as an orderly market-participant exit price. That is a useful distinction from owner-specific continuation value, not a claim that this code implements IFRS valuation or insurance regulation. [IFRS Foundation, IFRS 13 overview](https://www.ifrs.org/issued-standards/list-of-standards/ifrs-13-fair-value-measurement/).

## Illustrative shortfall calculator

The package keeps recovery evidence separate from asset DCF inputs. Given externally supplied net recoveries and probabilities:

```python
from gpu_valuation import RecoveryScenario, residual_guarantee

result = residual_guarantee(
    scenarios=[
        RecoveryScenario(net_recovery=20000, probability=0.60),
        RecoveryScenario(net_recovery=8000, probability=0.30),
        RecoveryScenario(net_recovery=0, probability=0.10),
    ],
    guarantee=15000,
    deductible=1000,
    limit=10000,
    discount_rate=0.05,
    horizon=3,
)
print(result.scenario_payouts)               # (0.0, 6000.0, 10000.0)
print(result.expected_payout)                # 2800.0
print(result.probability_of_payout)           # 0.4
print(result.present_value_expected_payout)  # approximately 2409.98
```

Every number above is invented. Recovery is net of selling costs at the common settlement date and floored at zero in the supplied scenarios. Negative disposal liabilities are outside this example. The example contract pays:

```text
min(limit, max(guarantee - net_recovery - deductible, 0))
```

Probabilities must sum to one; the function will not normalize arbitrary stress weights into probabilities. Currency must be common to recovery, guarantee, deductible and limit. Horizon and continuous discount rate use matching time units. No insurer-specific coverage, premium, tail capital estimate or dependence model is inferred. The calculator concerns economic shortfall only; it does not assume every economic loss is insured.

## What is still missing

The repo contains no calibrated resale panel, residual probability model, claims data, mortality/repair model, stochastic retirement policy, policy-language engine or insurer validation. Before operational use, publish data provenance, model version, calibration date, held-out errors and interval coverage, and obtain independent model and underwriting review. The current tests establish numerical behavior under explicit assumptions, not adequacy of those assumptions for an insured portfolio.
