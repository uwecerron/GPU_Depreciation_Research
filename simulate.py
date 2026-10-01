"""Export the dashboard's synthetic scenarios. Python 3.9+, no dependencies.

Run: python3 simulate.py
Outputs go to visuals/scenarios.csv. This does not fetch data or fit a model.
"""
import csv
from math import exp
from pathlib import Path

from anc.verify import retirement

ROOT = Path(__file__).resolve().parent
SCENARIOS = {
    'baseline': (0.04, 0.12),
    'paper_improvement': (0.08, 0.14),
    'faster_price_erosion': (0.08, 0.30),
}


def main():
    output = ROOT / 'visuals' / 'scenarios.csv'
    output.parent.mkdir(exist_ok=True)
    with output.open('w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['scenario', 'year', 'productivity_growth',
                         'price_erosion', 'revenue_erosion', 'gross_revenue',
                         'retention_threshold', 'asset_retirement_year',
                         'cohort_survival'])
        for name, (growth, price_erosion) in SCENARIOS.items():
            erosion = price_erosion - growth
            # Same single-asset parameters as anc/verify.py.
            exit_year = retirement([(1.0, erosion)], 0.25, 2.5, 0.10)
            for step in range(301):
                year = step / 10
                revenue = exp(-erosion * year)
                # The cohort assumes an exponential log-buffer with mean one.
                # Its survival happens to equal this asset's gross revenue.
                survival = exp(-erosion * year)
                writer.writerow([name, year, growth, price_erosion, erosion,
                                 revenue, 0.5, exit_year, survival])
            print(f'{name}: retirement={exit_year:.2f} model years; '
                  f'cohort survival at year 10={exp(-10 * erosion):.1%}')
    print(f'Wrote {output}')


if __name__ == '__main__':
    main()
