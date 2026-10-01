# A valuation surface for compute researchers

This is a deterministic asset DCF with optimal retirement. It prices the right to operate one device under specified cash-flow paths and then collect salvage. It does not price a futures contract, estimate a market-consistent fair value, or fit observed GPU prices.

## Reproduce or supply your own inputs

From the repository root:

```sh
python3 pricing_surface.py
python3 pricing/check_pricing.py
```

These commands need only Python 3.9+ and its standard library. Copy `pricing/example.json`, replace the assumptions, and run:

```sh
python3 pricing_surface.py --config my-inputs.json --output my-surface
```

`output/surface.csv` has 14,641 rows in the default example; `output/summary.json` records the exact inputs and baseline. `evidence_status` must describe the provenance honestly. Default USD figures are a synthetic 10,000-fold scaling of the paper's normalized example, not a quote or a calibration.

To redraw the PNG and vector SVG, install the optional plotting dependencies in an environment of your choice:

```sh
python3 -m pip install -r pricing/requirements-plot.txt
python3 pricing/plot_surface.py
# For a custom output directory:
python3 pricing/plot_surface.py --input my-surface
```

## What is being priced?

Let current revenue be `R = R0 × G/H`. Here `G` is the legacy GPU's one-time throughput gain and `H` is the divisor by which competitive service prices fall. Utilization must already be included in `R0`. Subsequent throughput growth `g` and service price decline `gamma` imply net revenue erosion `d = gamma - g`.

Revenue follows `R exp(-d t)`. With constant running cost `c`, constant salvage `S`, and continuous discount rate `rho`, the optimal retirement time is:

```text
T = max(0, log(R / (c + rho*S)) / d)
V = R * (1 - exp(-(rho+d)*T)) / (rho+d)
    - c * (1 - exp(-rho*T)) / rho
    + S * exp(-rho*T)
```

When `R <= c + rho*S`, take salvage immediately: `T=0`, `V=S`. The implementation uses `expm1` for numerical stability. It accepts only `d>0`, `rho>0`, `S>0`, nonnegative revenue and cost. Non-eroding or growing revenue requires a different horizon/terminal assumption and is rejected, not silently truncated.

Inputs share a currency and time unit. With annual inputs, `revenue` and `operating_cost` are currency/year; salvage and value are currency; rates are continuous annual rates. The example uses years. A constant hourly rate can be converted to annual revenue using billable hours, but a GPU-hour rental already incorporates the device's throughput economics: do not multiply it by a software throughput gain again without a contractual reason. For service-priced inference, price × measured throughput × utilization is the relevant mapping.

The axes vary the initial revenue level and its subsequent decay independently. They are **scenario coordinates**, not estimated causal responses to a software release. The same `G/H` can arise from different technical and price changes.

## Use the valuation function directly

```python
from pricing_surface import asset_value

quote = asset_value(
    revenue=10000, erosion=0.08, operating_cost=2500,
    salvage=25000, discount_rate=0.10,
)
print(quote["value"])          # 39898.84905837462
print(quote["retirement"])     # 8.664339756999317
```

The discount rate is supplied by the analyst, not inferred from traded assets. These are conditional cash-flow valuations, not arbitrage-free derivative prices. Price history, expected cash flows and discount-rate assumptions should be kept distinct.

## Outputs a quant can use

| CSV field | Interpretation |
|---|---|
| `value` | Discounted net operating cash flows plus terminal salvage |
| `cashflow_pv`, `salvage_pv` | Separate sources of asset value |
| `retirement` | Optimal remaining operating time |
| `revenue_delta` | dV/dR, in time units; sensitivity to current revenue per time unit |
| `erosion_sensitivity` | dV/dd; multiply by 0.01 for a local +1 percentage-point rate approximation |
| `value_change_erosion_plus_1pp` | Exact repricing for d+0.01, allowing retirement to change |
| `value_change_pct`, `life_change` | Changes relative to the input baseline |
| `longer_life_lower_value` | Flags the region where life improves but value falls |

The envelope derivatives account for optimal retirement. `revenue_delta` is an asset cash-flow sensitivity, not a futures hedge ratio. For index exposure, one would also need the mapping from index moves to realized device revenue, basis risk, contract multiplier, funding/settlement rules, and utilization response. A perpetually funded instrument is not a dated forward quote. Neither can be substituted mechanically for an expected rental-price path.

For a prospective purchase, compare the model value with the all-in acquisition and deployment cost. A positive operating margin can justify retaining sunk equipment while failing to justify buying it at today's asking price. Do not count interest both in cash flow and in the discount rate. Costs of power, rack rights, maintenance, downtime, taxes, switching, financing constraints and failure must be treated consistently before using this for a transaction. The present benchmark does not estimate them. It also excludes contracts, stochastic waiting options, and endogenous entry.

## The counterexample region

At the default baseline, value is USD 39,898.85 and remaining life is 8.66 model years. At `G/H=0.65`, `d=0.02`, value is USD 31,411.08 and life is 13.12 years. These are synthetic scenarios: a 51.4% life extension coexists with a 21.3% value reduction.

White contours show retirement times. The right panel hatches the longer-life/lower-value region, bounded by equal-value and equal-life curves. This is a counterexample to inferring value preservation from a longer life; it does not establish a faster subsequent percentage depreciation rate or an accounting impairment.

The chart uses normalized economics scaled into USD, not GPU purchase-price observations. A book-value comparison additionally needs acquisition date, historical cost, residual estimate and accounting policy. It is deliberately omitted here.

## Compute markets worth following

Architect's work on compute markets is worth following if you want this research to meet actual price discovery. Its [AX exchange page](https://architect.co/ax/) describes GPU-hour perpetuals, and its [January 2026 announcement with Ornn](https://architect.co/insights/press/architect-ornn-compute-futures/) explains the rental-price index approach. That is a useful direction for researchers looking for tradable references alongside physical rental data.

This repository does not use Architect quotes, connect to the exchange, or establish contract availability, liquidity or hedge effectiveness. Index-to-device basis still matters: GPU variant, location, service level, utilization and contract tenor can make the realized cash flow differ from the reference price. The link is an independent mention, not an exchange endorsement of this model. Source pages checked October 1, 2026.
