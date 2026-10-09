# Multidimensional multi-knapsack

## Model

Choose a subset of items and assign each chosen item to at most one of $m$
knapsacks. Every knapsack has $d$ resource dimensions (weight, volume, ...),
each with its own capacity. Maximise total profit.

**Sets and indices**

| Symbol | Meaning |
|---|---|
| $j \in J = \lbrace 1, \dots, n \rbrace$ | items |
| $k \in K = \lbrace 1, \dots, m \rbrace$ | knapsacks |
| $r \in R = \lbrace 1, \dots, d \rbrace$ | resource dimensions |

**Data**

| Symbol | Meaning |
|---|---|
| $p_j \ge 0$ | profit of item $j$ |
| $w_{jr} \ge 0$ | consumption of resource $r$ by item $j$ |
| $c_{kr} > 0$ | capacity of resource $r$ in knapsack $k$ |

**Decision variables**

$x_{jk} = 1$ if item $j$ is placed in knapsack $k$, otherwise $0$.

**Formulation**

Objective:

$$
\max \sum_{k \in K} \sum_{j \in J} p_j x_{jk}
$$

**(1)** every capacity of every knapsack is respected:

$$
\sum_{j \in J} w_{jr} x_{jk} \le c_{kr} \quad \forall k \in K, \forall r \in R
$$

**(2)** every item is placed at most once:

$$
\sum_{k \in K} x_{jk} \le 1 \quad \forall j \in J
$$

**(3)** the assignment is binary:

$$
x_{jk} \in \lbrace 0, 1 \rbrace \quad \forall j \in J, \forall k \in K
$$

**Special cases**

* $m = 1$: the classical multidimensional knapsack problem (MKP), which is the
  format of the OR-Library `mknap*` instances. The index $k$ drops out and the
  model becomes $\max \sum_j p_j x_j$ s.t. $\sum_j w_{jr} x_j \le c_r$,
  $x \in \lbrace 0, 1 \rbrace^n$.
* $d = 1$: the multiple knapsack problem (several knapsacks, one
  constraint each).
* $m = d = 1$: the plain 0-1 knapsack problem.

## Instances

Benchmark instances are fetched with [`download_instances.py`](download_instances.py):

```sh
python3 families/knapsack/download_instances.py            # all sources
python3 families/knapsack/download_instances.py orlib      # OR-Library only
python3 families/knapsack/download_instances.py pisinger   # Pisinger only
```

Files are saved under `families/knapsack/instances/`, which is git-ignored.
Never commit downloaded instance files; re-run the script to get them.

* **OR-Library** (J. E. Beasley): `mknap1`, `mknap2` and `mknapcb1`-`mknapcb9`
  (single knapsack, $d$ constraints).
* **Pisinger**: D. Pisinger's knapsack instance and code page,
  <https://hjemmesider.diku.dk/~pisinger/codes.html>.

## Pipeline

```
generate/generate.py ──► data/instances/*.json ──► labels/make_labels.py ──► data/labels/*.label.json
download_instances.py ─► instances/orlib/*.txt ─► labels/orlib_to_json.py ─┘
```

Instances use the `shared/formats` *instance* layout (`id`, `family`, `sense`,
`variables`, `constraints`, `meta`). Variable `type` is one of `real`,
`integer`, `binary`; the knapsack family only uses `binary`. `data/` holds
generated output and is git-ignored (regenerate it from the seeds).

### Generate

```sh
cd families/knapsack
python3 generate/generate.py --type uncorrelated --n 100 --seed 42 --out data/instances/a.json
python3 generate/generate.py --type strong --n 500 --seed 1 --count 20 --out-dir data/instances
# multidimensional (Chu-Beasley), any m >= 1
python3 generate/generate.py --type chu-beasley --n 250 --m 10 --tightness 0.25 --seed 1 --out-dir data/instances
```

| `--type` | profits | `m` |
|---|---|---|
| `uncorrelated` | $p_j \sim U[1,R]$ | 1 |
| `weak` | $p_j \sim U[w_j - R/10, w_j + R/10]$, $\ge 1$ | 1 |
| `strong` | $p_j = w_j + R/10$ | 1 |
| `chu-beasley` | $p_j = \lfloor \tfrac1m\sum_i a_{ij} + 500 q_j \rceil$, $q_j\sim U(0,1)$ | $\ge 1$ |

For the first three, $w_j \sim U[1,R]$ (`--range`, default 1000) and the
capacity is $\lfloor \texttt{--capacity-ratio} \cdot \sum_j w_j \rfloor$
(default 0.5). For Chu-Beasley, $a_{ij}$ is a uniform integer in $[0, 1000]$ and
$b_i = \lfloor \alpha \sum_j a_{ij} \rfloor$ with `--tightness` $\alpha$
(OR-Library uses 0.25, 0.5, 0.75).

The same arguments always give a byte-identical file (only `random.Random(seed)`
is used, the output has no timestamps). Tests: `python3 -m unittest -v test_generate`
inside `generate/`.

### Label

```sh
python3 labels/make_labels.py data/instances                    # prove optimality
python3 labels/make_labels.py data/instances --time-limit 60    # keep the final gap
```

Needs `gurobipy` (`pip install gurobipy`; the pip license is limited to 2000
variables and 2000 constraints). One `<id>.label.json` per instance:

| key | content |
|---|---|
| `variables`, `constraints` | names; every vector below follows this order |
| `lp_relaxation` | `objective`, `x`, `reduced_costs`, `duals` (one per constraint, i.e. each capacity row), `slacks`, `time_s` |
| `mip.solution`, `mip.objective` | best solution found (the optimum when `status` is `OPTIMAL`) |
| `mip.best_bound`, `mip.gap`, `mip.status`, `mip.time_limit_hit` | final bound, relative gap and status (gap is saved even when the time limit hits) |
| `mip.time_s`, `mip.nodes` | solve time and node count |
| `mip.incumbents` | every improving solution: `time_s`, `objective`, `nodes`, `x` |
| `gurobi`, `instance_sha256` | version, parameters (threads=1, seed=0 by default) and a hash of the instance file |

Duals and reduced costs follow Gurobi's sign convention for the instance's
sense: for max with $\le$ rows, duals are $\ge 0$ and the LP bound equals
$\sum_i \pi_i b_i + \sum_j \max(\bar c_j, 0)$. Tests: `python3 -m unittest -v
test_make_labels` inside `labels/`.

### OR-Library check (`mknapcb`)

```sh
python3 download_instances.py orlib
python3 -I labels/orlib_to_json.py --best-known best_known.csv   # lines: orlib-mknapcb1-01,<value>
python3 labels/make_labels.py data/instances/orlib --time-limit 600
```

`make_labels.py` prints `= best_known`, `BETTER than best_known` or `below
best_known` per instance (a proven-optimal result below the best-known value
exits with status 1). The `mknapcb` headers usually contain 0 for the optimum,
hence the `--best-known` CSV. Every `mknapcb` size (up to n=500, m=30) fits the
restricted Gurobi license.
