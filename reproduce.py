"""Reproduce the paper's checks in a temporary copy, without changing inputs.

Run: python3 reproduce.py
Uses only the standard library. Does not fetch data or require GPU hardware.
"""
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent


def compare(expected, actual, location='result'):
    """Compare structure exactly and floating-point values within roundoff."""
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or expected.keys() != actual.keys():
            raise ValueError(f'{location}: different fields')
        for key in expected:
            compare(expected[key], actual[key], f'{location}.{key}')
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(expected) != len(actual):
            raise ValueError(f'{location}: different list length')
        for index, (left, right) in enumerate(zip(expected, actual)):
            compare(left, right, f'{location}[{index}]')
    elif type(expected) is float:
        if not isinstance(actual, (int, float)) or not math.isclose(expected, actual, rel_tol=1e-9, abs_tol=1e-10):
            raise ValueError(f'{location}: expected {expected}, got {actual}')
    elif type(expected) is not type(actual) or expected != actual:
        raise ValueError(f'{location}: expected {expected!r}, got {actual!r}')


def main():
    print(f'Python {sys.version.split()[0]}', flush=True)
    source = ROOT / 'anc'
    expected = {name: json.loads((source / name).read_text()) for name in
                ('results.json', 'data_audit.json', 'screen-example-output.json')}
    digest = hashlib.sha256((source / 'data' / 'weekly.json').read_bytes()).hexdigest()
    if digest != expected['data_audit.json']['sha256']:
        raise ValueError('Frozen dataset checksum differs from the recorded audit')
    print('PASS: frozen dataset checksum', flush=True)
    with tempfile.TemporaryDirectory(prefix='gpu-reproduction-') as temporary:
        work = Path(temporary)
        shutil.copytree(source, work / 'anc', ignore=shutil.ignore_patterns('__pycache__'))
        def run(script, *args):
            process = subprocess.run([sys.executable, str(work / 'anc' / script), *args],
                                     cwd=work, text=True, capture_output=True)
            if process.returncode:
                raise RuntimeError(f'{script} failed:\n{process.stdout}\n{process.stderr}')
            return process.stdout
        run('verify.py')
        compare(expected['results.json'], json.loads((work / 'anc' / 'results.json').read_text()))
        print('PASS: theoretical examples match reference results', flush=True)
        print(run('check_screen.py').strip(), flush=True)
        compare(expected['data_audit.json'], json.loads(run('audit_data.py')))
        print('PASS: frozen data coverage audit matches reference', flush=True)
        actual = json.loads(run('retention_screen.py', str(work / 'anc' / 'screen-example.json')))
        compare(expected['screen-example-output.json'], actual)
        print('PASS: stationary screen matches reference output', flush=True)
    print('All checks passed. These are reproduction checks, not empirical validation.')


if __name__ == '__main__':
    main()
