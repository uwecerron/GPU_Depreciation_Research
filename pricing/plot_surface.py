"""Render CSV from pricing_surface.py. Optional dependency: matplotlib.

Run after generating the CSV: python3 pricing/plot_surface.py
"""
import argparse
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from matplotlib.lines import Line2D
import numpy as np

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=ROOT / 'output')
    args = parser.parse_args()
    summary = json.loads((args.input / 'summary.json').read_text())
    cfg, base = summary['inputs'], summary['baseline']
    with (args.input / 'surface.csv').open() as stream:
        rows = list(csv.DictReader(stream))
    n = cfg['grid_points']
    def matrix(key):
        return np.array([float(row[key]) for row in rows]).reshape(n, n)
    x, y = matrix('revenue_multiplier'), matrix('erosion') * 100
    v, t, change = matrix('value'), matrix('retirement'), matrix('value_change_pct')
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10})
    fig, axes = plt.subplots(1, 2, figsize=(14, 7.8), constrained_layout=False)
    fig.subplots_adjust(top=.76, bottom=.25, left=.065, right=.965, wspace=.32)
    fig.suptitle('Longer GPU life can coexist with lower asset value', fontsize=21, x=.065, ha='left', y=.97)
    fig.text(.065, .905, 'LIQUID LABOR  /  Uwe Jens Cerron\nDeterministic valuation surface • Synthetic inputs, not market quotes', fontsize=11, linespacing=1.8, va='top')
    im = axes[0].pcolormesh(x, y, v, shading='auto', cmap='viridis', rasterized=True)
    fig.colorbar(im, ax=axes[0], label=f"Present value ({cfg['currency']})", fraction=.05, pad=.03)
    lower, upper = min(float(change.min()), -1), max(float(change.max()), 1)
    im2 = axes[1].pcolormesh(x, y, change, shading='auto', cmap='RdBu', rasterized=True, norm=TwoSlopeNorm(vmin=lower, vcenter=0, vmax=upper))
    fig.colorbar(im2, ax=axes[1], label='Value change versus baseline (%)', fraction=.05, pad=.03)
    for ax in axes:
        contours = ax.contour(x, y, t, levels=[2, 5, 10, 20, 40], colors='white', linewidths=.7)
        ax.clabel(contours, fmt='%g', fontsize=8)
        ax.set_xlabel('Current revenue multiplier, G / H')
        ax.set_ylabel(f"Subsequent revenue erosion (% per {cfg['time_unit']})")
        ax.set_xlim(x.min(), x.max())
        ax.set_ylim(y.min(), y.max())
        ax.plot(1, cfg['baseline_erosion'] * 100, 'o', color='black', markeredgecolor='white', ms=7)
        ax.plot(.65, 2, '*', color='#ffcf33', markeredgecolor='black', ms=13)
    mask = (t > base['retirement']) & (v < base['value'])
    if np.any(mask):
        axes[1].contourf(x, y, mask.astype(float), levels=[.5, 1.5], colors='none', hatches=['////'])
    if t.min() < base['retirement'] < t.max():
        axes[1].contour(x, y, t, levels=[base['retirement']], colors='black', linewidths=1.5, linestyles='--')
    if v.min() < base['value'] < v.max():
        axes[1].contour(x, y, v, levels=[base['value']], colors='black', linewidths=1.5)
    axes[0].set_title('Asset value, with retirement-date contours', loc='left', fontsize=12, pad=12)
    axes[1].set_title('Hatched region: longer life, lower value', loc='left', fontsize=12, pad=12)
    fig.legend(handles=[Line2D([], [], color='black', lw=1.5, label='Unchanged value'),
                        Line2D([], [], color='black', ls='--', label='Unchanged retirement date'),
                        Line2D([], [], marker='o', color='black', ls='', label='Baseline'),
                        Line2D([], [], marker='*', color='#ffcf33', markeredgecolor='black', ls='', markersize=12, label='Counterexample')],
               loc='lower center', bbox_to_anchor=(.5, .15), ncol=4, frameon=False)
    ce = summary['counterexample']
    fig.text(.065, .105, f"Baseline: {base['retirement']:.2f} {cfg['time_unit']}s / {cfg['currency']} {base['value']:,.0f}.  "
             f"Star: {ce['retirement']:.2f} {cfg['time_unit']}s / {cfg['currency']} {ce['value']:,.0f}.  White contours: retirement in model time units.", fontsize=10)
    fig.text(.065, .045, f"R₀={cfg['revenue']:g}/{cfg['time_unit']}; c={cfg['operating_cost']:g}/{cfg['time_unit']}; S={cfg['salvage']:g}; ρ={cfg['discount_rate']:.0%}. "
             "Constant costs and salvage; no failure, switching costs or capacity constraint.\n"
             "G = old-device throughput multiplier; H = competitor-driven service-price divisor. "
             "G/H changes current revenue; d = γ − g controls its subsequent erosion.", fontsize=9, linespacing=1.6)
    fig.savefig(args.input / 'price_surface.png', dpi=170)
    fig.savefig(args.input / 'price_surface.svg')
    plt.close(fig)
    print(f'Wrote PNG and SVG to {args.input}')


if __name__ == '__main__':
    main()
