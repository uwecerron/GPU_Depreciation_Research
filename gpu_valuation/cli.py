"""Command-line adapter; wheel includes its default config."""
import argparse
from importlib import resources
import json
from pathlib import Path
from .surface import build_surface, load_config, validate_config


def main(default_output=None):
    parser = argparse.ArgumentParser(description='Export a synthetic GPU valuation surface.')
    parser.add_argument('--config', type=Path)
    parser.add_argument('--output', type=Path, default=default_output or Path('gpu-surface'))
    args = parser.parse_args()
    config = (load_config(args.config) if args.config else validate_config(
        json.loads(resources.files('gpu_valuation').joinpath('default_surface.json').read_text())))
    summary = build_surface(config, args.output)
    print(json.dumps(summary, indent=2))
    print(f'Wrote CSV and metadata to {args.output}')
