# Multidimensional multi-knapsack

## Model

Choose a subset of items and assign each chosen item to at most one of $K$
knapsacks. Every knapsack has $d$ resource dimensions (weight, volume, ...),
each with its own capacity. Maximise total profit.

**Sets and indices**

| Symbol | Meaning |
|---|---|
| $j \in J = \{1,\dots,n\}$ | items |
| $k \in K = \{1,\dots,m\}$ | knapsacks |
| $r \in R = \{1,\dots,d\}$ | resource dimensions |

**Data**

| Symbol | Meaning |
|---|---|
| $p_j \ge 0$ | profit of item $j$ |
| $w_{jr} \ge 0$ | consumption of resource $r$ by item $j$ |
| $c_{kr} > 0$ | capacity of resource $r$ in knapsack $k$ |

**Decision variables**

$x_{jk} = 1$ if item $j$ is placed in knapsack $k$, otherwise $0$.

**Formulation**

$$
\max \sum_{k \in K} \sum_{j \in J} p_j \, x_{jk}
$$

subject to

$$
\sum_{j \in J} w_{jr} \, x_{jk} \le c_{kr} \qquad \forall k \in K,\ r \in R \tag{1}
$$

$$
\sum_{k \in K} x_{jk} \le 1 \qquad \forall j \in J \tag{2}
$$

$$
x_{jk} \in \{0,1\} \qquad \forall j \in J,\ k \in K \tag{3}
$$

(1) respects every capacity in every knapsack, (2) places each item at most
once, and (3) makes the assignment binary.

**Special cases**

* $m = 1$: the classical multidimensional knapsack problem (MKP), which is the
  format of the OR-Library `mknap*` instances. The index $k$ drops out and the
  model becomes $\max \sum_j p_j x_j$ s.t. $\sum_j w_{jr} x_j \le c_r$,
  $x \in \{0,1\}^n$.
* $d = 1$: the multiple knapsack problem (MKP with several knapsacks, one
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
