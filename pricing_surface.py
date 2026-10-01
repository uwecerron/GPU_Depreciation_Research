"""Compatibility entry point. Prefer the installable gpu_valuation package."""
from pathlib import Path
from gpu_valuation import asset_value
from gpu_valuation.surface import build_surface, load_config, value_for
from gpu_valuation.cli import main as package_main


def main():
    package_main(default_output=Path(__file__).resolve().parent / 'pricing/output')


if __name__ == '__main__':
    main()
