# SelectorSeal

Implementation of **Resolution-closed authorization for late-bound bulk effects**.

Implements snapshot approvals, canonical object generations, positive and negative dependency invalidation, full scope/PDP rechecks and atomic effect receipts.

## Install

Use Python 3.11 or newer.

```bash
git clone https://github.com/Hqa77880011/SelectorSeal.git
cd SelectorSeal
python -m venv .venv
```

Activate with `source .venv/bin/activate` on Linux/macOS or `.venv\Scripts\Activate.ps1` in PowerShell.

```bash
python -m pip install -e .
```

## Prepare the workload

```bash
python -m selectorseal prepare --count 200 --seed 17 --output data/workload.jsonl
```

The seeded generator constructs finite scenarios from the formal problem. Independently generated or recorded cases may be imported with the same JSONL schema.

`initial` holds object and deny tables. Objects have canonical ID, generation, name, tenant, tag and members. The selector is a finite field-equality conjunction. `writes` precedes gate execution; `late_writes` models writes at the validation/commit boundary. Deny entries bind principal and tenant.

## Execute and compare

```bash
python -m selectorseal run --data data/workload.jsonl --output runs/main
python -m selectorseal suite --data data/workload.jsonl --output runs/comparison
```

`--methods` selects one or more method names. There are no learned parameters or model training in these finite algorithms.

`selectorseal` invalidates on relevant old/new write images; `full_exact` always resolves and authorizes; `whole_table` invalidates conservatively. `query_cache`, `no_negative_domains`, `display_name` and `split_check_effect` remove the named safeguards.

## Metrics and plots

Episode UAR, scope and policy violations, benign task success/false denial, reauthorization, false reuse/invalidation, retry/reconsent rates, certificate bytes and runtime.

Each method writes `records.jsonl` and `metrics.json` under its output subdirectory. Conditional rates omit cases outside their denominator. Summary fields include means, sample standard deviations, P50/P95/P99 and usable sample counts. Independent scoring runs after the method timer. RSS includes the process runtime; serialized sizes measure JSON bytes.

```bash
python -m selectorseal plot --inputs runs/comparison/selectorseal --output figures
```

Supply multiple method directories after `--inputs` for comparison. Plotting writes `summary.csv` and metric PNGs.

## Implementation conventions

The in-memory state service serializes operations with an RLock and retains a complete write journal. It models local transaction semantics rather than PostgreSQL throughput. Snapshot scope is exact: growth requires reconsent, shrinkage retries, and generation replacement is a new identity. A nonce returns its existing receipt on replay.


## Uncertainty and paired comparisons

```bash
python -m selectorseal.statistics --records runs/main/selectorseal/records.jsonl --output results/intervals.json
```

Supply --reference with a matched record file for paired differences. Resampling uses independent case IDs, or explicit cluster IDs when provided. Repeated observations from one source unit must share cluster. Zero-event bounds refer to an event in an independent cluster.

## Fixed reproduction setting

Equality selectors and explicit object generations in an atomic in-process RLock backend; finite adversarial writes and receipt effects.

The checked-in entry point fixes data seeds, methods, budgets and output paths. Inspect its commands without starting any computation:

```bash
python reproduce.py --plan
```

Remove `--plan` to execute the registered pipeline in a fresh output directory. The entry point calls the existing implementation; it does not insert paper results. Installation uses the package instructions above.
