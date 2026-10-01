# Contributing

Changes to the Python library, numerical checks, input provenance and documentation are welcome. Open an issue or pull request with the problem, the proposed change and its assumptions. Contributors retain copyright in their original contributions; contributions to the software are provided under its MIT license.

Keep numerical valuation separate from plotting, filesystem and exchange adapters. Add a regression test for a substantive fix or economic change. Use externally supplied data and probabilities explicitly rather than silently treating synthetic assumptions as calibration. Maintain the existing dictionary API in `pricing_surface.py` and document any incompatible change.

Run from the repository root:

```sh
python3 -m unittest discover -s tests -v
python3 pricing/check_pricing.py
python3 reproduce.py
```

For a packaging change, build a wheel with `python3 -m pip wheel . --no-deps --wheel-dir dist`, install it into a clean environment, and run `gpu-valuation-surface` from outside this checkout. The public package must not depend on the research scripts, data snapshot, Matplotlib, pandas or NumPy. Optional plotting dependencies stay optional.

The software and its usage documentation are MIT-licensed. The paper retains its separate publication license. The GetDeploying data retains its CC BY 4.0 attribution and terms. A software contribution does not transfer ownership of third-party material or license anyone's trademarks.
