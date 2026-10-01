# GPU Depreciation Research

Reproduction code for **When Software Extends GPU Life: Workload Choice and Economic Retirement** by **Uwe Jens Cerron, Liquid Labor**.

[Read the SSRN preprint](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7549859)

## Run

Python 3 is required. All scripts use the standard library; no packages need installing. Run these commands from this repository directory:

```sh
python3 anc/verify.py
python3 anc/check_screen.py
python3 anc/audit_data.py
python3 anc/retention_screen.py anc/screen-example.json
```

## Files

- `anc/verify.py`: reproduces theoretical examples and checks the retirement model.
- `anc/retention_screen.py`: computes a stationary economic retention screen.
- `anc/check_screen.py`: boundary and input validation checks for that screen.
- `anc/audit_data.py`: audits the coverage of the included frozen rental-price dataset. The optional `--fetch` flag downloads a fresh snapshot and changes the audit inputs.
- `anc/screen-example.json`: synthetic screen inputs.
- `anc/results.json`, `anc/data_audit.json`, and `anc/screen-example-output.json`: reference outputs.
- `anc/proposed-protocol.txt`: proposed empirical protocol, unregistered and unexecuted.

## Scope

Numerical examples are synthetic, not estimates of GPU lifetimes. Algebra and numerical checks do not establish an empirical causal effect. The data audit does not validate contractability, asset value, or a software-release effect. The stationary screen is not a retirement-date forecast.

## Data attribution

The unmodified frozen `anc/data/weekly.json` snapshot comes from [GetDeploying GPU rental price history](https://getdeploying.com/dataset/gpu-prices), distributed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). No endorsement is implied. See `anc/data_audit.json` for provenance and its SHA-256 checksum.

## AI disclosure

OpenAI Codex assisted with derivations, drafting, code, literature searches, and internal adversarial review. That review was not external peer review.
