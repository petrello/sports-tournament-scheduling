#!/usr/bin/env python3
# --------------------------------------------------------------------------- #
#  CDMO 2024/25  –  SAT encoding of the STS *decision* problem
#
#  Features inherited from both earlier prototypes:
#    • deterministic circle-method tables + first-row swap (MiniZinc-faithful)
#    • (max,min) ordering inside each match  →  symmetry breaking
#    • sequential “exactly-one” (Or + AtMost 1)  →  slim CNF
#    • MiniZinc’s  ‘already_ok’  shortcut: lock identity permutation if legal
#    • 5-minute Z3 timeout  +  live progress ticker
#    • DIMACS dump  +  JSON schedule
#
#  Usage:   python sat_rr_merged.py <even n>
# --------------------------------------------------------------------------- #
import sys, json, pathlib, time, threading
from z3 import Solver, Bool, Or, Not, AtMost, sat, And, AtLeast


# --------------------------------------------------------------------------- #
# 1.  Circle-method tables + swap heuristic (0-based lists)
# --------------------------------------------------------------------------- #
def circle_tables(n: int):
    W, P = n - 1, n // 2
    A = [[0] * P for _ in range(W)]
    B = [[0] * P for _ in range(W)]

    for w in range(W):
        for p in range(P):
            if p == 0:  # team n is fixed
                a, b = n, w + 1
            else:
                a = (w + p) % (n - 1) + 1
                b = ((n - 1) - p + w) % (n - 1) + 1
            A[w][p], B[w][p] = (a, b) if a > b else (b, a)

    # first-row swap to mitigate repetitions
    for w in range(1, W):
        tgt = n - w
        row = next(r for r in range(1, P)
                   if A[w][r] == tgt or B[w][r] == tgt)
        A[w][0], A[w][row] = A[w][row], A[w][0]
        B[w][0], B[w][row] = B[w][row], B[w][0]

    return A, B


# --------------------------------------------------------------------------- #
# 2.  Minimal “exactly-one” encoding:  Or(vars) ∧ AtMost(vars,1)
# --------------------------------------------------------------------------- #
def exactly_one(bool_vars):
    """Z3 encoding of "Exactly k" over bool_vars."""
    return And(AtLeast(*bool_vars, 1), AtMost(*bool_vars, 1))


# --------------------------------------------------------------------------- #
# 3.  Build Z3 model
# --------------------------------------------------------------------------- #
def build_solver(n: int, timeout_ms: int = 300_000):
    assert n % 2 == 0 and n >= 2
    A, B = circle_tables(n)
    W, P = n-1, n//2

    # MiniZinc’s “already_ok” test
    row_ok = all(
        max(sum(1 for w in range(W)
                if A[w][p] == t or B[w][p] == t)
            for t in range(1, n + 1)) <= 2
        for p in range(P)
    )

    s = Solver()
    s.set(timeout=timeout_ms)

    X = [[[Bool(f"x_{w}_{p}_{m}") for m in range(P)]
          for p in range(P)]
         for w in range(W)]

    # 3.1  exactly-one per slot
    for w in range(W):
        for p in range(P):
            s.add(exactly_one(X[w][p]))

    # 3.2  permutation: each match appears once per week
    for w in range(W):
        for m in range(P):
            s.add(exactly_one([X[w][p][m] for p in range(P)]))

    # 3.3  ≤ 2 occurrences of every team in every row
    for p in range(P):
        for t in range(1, n + 1):
            lits = [X[w][p][m]
                    for w in range(W)
                    for m in range(P)
                    if A[w][m] == t or B[w][m] == t]
            if len(lits) > 2:
                s.add(AtMost(*lits, 2))

    # 3.4  lock identity permutation if already feasible
    if row_ok:
        for w in range(W):
            for p in range(P):
                for m in range(P):
                    s.add(X[w][p][m] if m == p else Not(X[w][p][m]))


    for p in range(P):
        for m in range(P):
            s.add(X[0][p][m] if m == p else Not(X[0][p][m]))

    return s, X, A, B


# --------------------------------------------------------------------------- #
# 4.  Decode schedule
# --------------------------------------------------------------------------- #
def decode(model, X, A, B):
    W, P = len(X), len(X[0])
    table = [[None] * W for _ in range(P)]
    for w in range(W):
        for p in range(P):
            for m, lit in enumerate(X[w][p]):
                if model.eval(lit, model_completion=True):
                    table[p][w] = [A[w][m], B[w][m]]
                    break
    return table


# --------------------------------------------------------------------------- #
# 5.  Simple live “Solving … mm:ss” ticker
# --------------------------------------------------------------------------- #
_stop = threading.Event()


def _ticker():
    start = time.time()
    while not _stop.is_set():
        e = int(time.time() - start)
        m, s = divmod(e, 60)
        sys.stderr.write(f"\rSolving … {m:02d}:{s:02d}")
        sys.stderr.flush()
        time.sleep(1)
    sys.stderr.write("\n")


# --------------------------------------------------------------------------- #
# 6.  Main
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python sat_rr_merged.py <even n>")

    n = int(sys.argv[1])
    t = threading.Thread(target=_ticker, daemon=True)
    t.start()
    solver, X, A, B = build_solver(n)
    res = solver.check()
    _stop.set()
    t.join()

    if res != sat:  # unsat or timeout
        print("[]")
        sys.exit(0)

    schedule = decode(solver.model(), X, A, B)

    # dump DIMACS
    pathlib.Path(f"sat_rr_n{n}.cnf").write_text(solver.dimacs())

    # JSON result
    js = {
        "z3": {
            "time_ms": int(solver.statistics().get_key_value('time')),
            "optimal": True,
            "obj": None,
            "sol": schedule
        }
    }
    # print(json.dumps(js, indent=2))
    print(schedule)