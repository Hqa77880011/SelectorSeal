# SelectorSeal implementation

Implementation of **Resolution-closed authorization for late-bound bulk effects**.

The existing finite-model algorithms are retained. This revision adds field-sensitive irrelevant-write detection, immutable nonce/plan binding, correct committed-object violation denominators, and negative-domain/generation/race replay checks. These are implementation and functional-validation artifacts; they are not the raw experimental code or evidence behind the manuscript's reported numbers.

## Installation

Requires Python >=3.11. From the repository root in an activated environment:

```bash
python -m pip install -e .
python -m unittest discover -s tests
```

Installed validation environment: Windows, Python 3.13.5, numpy 2.1.3, scipy 1.15.3, matplotlib 3.10.0, psutil 7.1.0. Existing CI installs dependencies and runs the regression checks on Python 3.11.

## Data

The bundled generator produces synthetic finite-model scenarios for functional checks. It does not download a native benchmark, reproduce manuscript result tables or fit any parameters. Retain one generated input for paired comparisons:

```bash
python -m selectorseal prepare --count 6 --seed 17 --output data/generated.jsonl
```

Each UTF-8 JSONL line has a unique `id`, optional `family`, and `cluster` identifying the actual independent policy/history family. The generator records `generation_seed` and conservatively clusters repeated examples by family. Imported independent data should supply its reviewed cluster IDs. Input fields are:

`initial.objects`: stable id/generation/name/tenant/member rows; `initial.denies`: tenant/principal deny rows; `query`: equality selector; `principal`, `id`: requester and nonce; `writes`, `late_writes`: before/after state updates around the gate. Approval fixes a nonempty canonical manifest and action/destination. Display names do not replace stable identities.

`core.generate` is an executable complete schema example. Use the same schema for reviewed recorded cases; keep native, mutation-derived and synthetic strata separate. No private data, manuscript, pretrained weights or original server logs are distributed. The algorithms use explicit policy/configuration inputs rather than learned models, and do not tune on test labels.

## Execution

```bash
python -m selectorseal run --data data/generated.jsonl --output runs/main
```

## Evaluation

```bash
python -m selectorseal evaluate --records runs/main/selectorseal/records.jsonl --output runs/evaluated.json
```

`uar` is per attack episode, retaining no-commit episodes. `object_level_violation` uses committed objects and checks both original scope and current policy. `policy_violation` is separate. `false_denial` conditions on the full oracle allowing the original task. `false_reuse` uses reuse attempts and `false_invalidation` all validations; retry and reconsent remain separate. Raw counts preserve object-level micro aggregation.

Rates are fractions in [0,1]. `null` means an inapplicable or unresolved denominator, not zero failures. `metrics.json` gives conditional per-case means, SD and quantiles; rate fields with explicit `metric_counts` also contain pooled `micro` numerator/denominator/rate. Whole-case `latency_ms` includes local construction and audits; stage metrics identify the narrower compilation/runtime path. `rss_mib` is a sampled resident value, not a measured peak. Throughput is local finite-model useful effects per whole-case wall second, not the manuscript's server throughput.

The same `evaluate` command accepts independently recorded JSONL with `id`, `method`, `cluster`, numerical-or-null `metrics`, and optional `metric_counts` mapping each rate name to `[numerator, denominator]`. Thus backend-only paper measurements can be aggregated when genuinely collected; missing lock waits, network latency, maintenance, attacker recovery or native task outcomes are not assigned invented values.

## Comparisons and ablations

```bash
python -m selectorseal suite --data data/generated.jsonl --output runs/comparison
python -m selectorseal.statistics --records runs/comparison/selectorseal/records.jsonl --reference runs/comparison/full_exact/records.jsonl --resamples 10000 --seed 17 --primary uar --output runs/paired.json
```

Select a subset with `--methods`. Implemented configurations: `selectorseal`, `full_exact`, `whole_table`, `query_cache`, `no_negative_domains`, `display_name`, `split_check_effect`. Deliberately lossy, unbound, feasibility-disabled and race variants are sandbox diagnostic controls, not safe deployments. The comparison implementations use this repository's declared finite semantics; they are not unmodified upstream systems.

Statistics first aggregate within each independent family and then bootstrap whole families. Paired analysis requires identical case IDs and excludes metrics undefined on either side. One eligible family yields no bootstrap interval. The zero-event bound concerns an event in an independent eligible cluster, not an iid per-request rate. McNemar is used only for independent single-record binary pairs; other paired summaries use Wilcoxon. Holm correction applies only to explicitly selected `--primary` endpoints. Small synthetic examples are not a source of experimental confidence intervals.

## Outputs and visualizations

```bash
python -m selectorseal plot --inputs runs/comparison/selectorseal runs/comparison/full_exact --metrics uar latency_ms --output runs/figures
```

Each method directory contains `records.jsonl` (actual outcomes and conditional metrics), `metrics.json`, and `config.json` (command, environment and seeds). Plotting writes `summary.csv` plus selected metric PNGs; undefined metrics produce no misleading empty plot. All paths are configurable. Choose fresh output directories for reruns; generation/evaluation do not silently overwrite retained inputs or records.

## Paper-to-code map

| Paper module or metric | Code entry | Configuration / command |
|---|---|---|
| Canonical exact approval scope | `core.resolve / identities / State.approve` | id and generation; query |
| Positive/control/negative write domains | `core.affected` | old/new images; deny insertion; relevant fields |
| Atomic local gate and nonce receipt replay | `core.State.execute` | selectorseal / split_check_effect |
| Full recomputation and scope-change outcomes | `core.State.execute` | full_exact / whole_table; RECONSENT / RETRY / DENIED |
| Episode and committed-object metrics | `core.score / metric_counts` | evaluate; plot |
| Aggregation, paired intervals and visualization | `cli.summarize; statistics.analyze; cli.plot` | evaluate / statistics / plot |

## Validation and implementation scope

Validated locally: editable installation, syntax/import and regression checks, six seed-17 cases through every suite configuration, retained-record re-evaluation, 10,000-resample paired analysis, selected metric PNG/CSV output, and wheel/source-distribution builds. No full paper campaign was run. Local functional records are retained under `runs/smoke/` (Git-ignored).

Regression checks cover hand-computable rates and eligible denominators, the algorithm's safety boundary, and applicable replay/serialization paths. The documented small-data preparation, execution, suite, evaluation, statistics and plotting commands are the validation entry points. No complete training or large experimental campaign is required for these checks.

Object keys must match stable IDs and generations are positive integers. The
local journal retains generation tombstones: recreating a deleted ID requires a
strictly newer generation. Canonical JSON binding rejects Boolean/integer changes
inside a stored approval. Equality selectors distinguish absent attributes from
explicit null and preserve JSON types in invalidation as well as resolution.

The selector grammar is finite equality conjunctions, with simple member/tenant-deny policies. The RLock backend is atomic within one Python State instance; it is not a PostgreSQL serializable adapter or cross-process durable nonce journal. Receipt replay is an executable local state model, not a committed external export. General ranges/traversals/NOT EXISTS, signed approval envelopes, index watermarks and write-side server performance require adapters and are not claimed as validated.

The source retains its existing MIT license. Data and external systems remain subject to their own licenses and access rules.
