#!/usr/bin/env python3
# --------------------------------------------------------------------------- #
#  CDMO 2024/25  –  Round-robin STS  (optimisation version, merged)
#
#  • deterministic circle tables  +  first-row swap  (faithful to MiniZinc)
#  • sequential “exactly-one” (Or + AtMost 1)  → compact CNF
#  • MiniZinc ‘already_ok’ shortcut locks the identity permutation
#  • Boolean Swap[w][p] to balance home/away
#  • objective  min maxImbalance  solved with Z3 Optimize (5-min cap)
#  • live “Solving … mm:ss” ticker
#  • JSON result  +  DIMACS dump when available
# --------------------------------------------------------------------------- #
import sys, time, json, pathlib, threading
from z3 import (
    Optimize, Bool, Not, Or, AtMost, If, Int, IntVal, sat, And, AtLeast, Sum
)


# --------------------------------------------------------------------------- #
# tiny helper: sequential (Or ∧ AtMost 1)  “exactly-one”
# --------------------------------------------------------------------------- #
def exactly_one(bool_vars):
    """Z3 encoding of "Exactly k" over bool_vars."""
    return And(AtLeast(*bool_vars, 1), AtMost(*bool_vars, 1))


# --------------------------------------------------------------------------- #
# live progress bar
# --------------------------------------------------------------------------- #
_stop = threading.Event()


def _ticker():
    start = time.time()
    while not _stop.is_set():
        m, s = divmod(int(time.time() - start), 60)
        sys.stderr.write(f"\rSolving … {m:02d}:{s:02d}")
        sys.stderr.flush()
        time.sleep(1)
    sys.stderr.write("\n")


# --------------------------------------------------------------------------- #
# deterministic circle-method  (raw orientation, NO max/min swap)
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
            A[w][p], B[w][p] = (a, b) if a > b and w % 2 == 0 else (b, a)

    # heuristic swap
    for w in range(1, W):
        tgt = n - w
        row = next(r for r in range(1, P)
                   if A[w][r] == tgt or B[w][r] == tgt)
        A[w][0], A[w][row] = A[w][row], A[w][0]
        B[w][0], B[w][row] = B[w][row], B[w][0]

    return A, B


# --------------------------------------------------------------------------- #
# build optimisation model
# --------------------------------------------------------------------------- #
def build_opt_solver(n: int, timeout_ms: int = 300_000):
    assert n % 2 == 0 and n >= 2, "n must be even ≥ 2"
    A, B = circle_tables(n)
    W, P = n-1, n//2

    # already_ok  (row capacity check only)
    already_ok = all(
        max(sum(1 for w in range(W)
                if A[w][p] == t or B[w][p] == t)
            for t in range(1, n + 1)) <= 2
        for p in range(P)
    )

    opt = Optimize()
    opt.set(timeout=timeout_ms)  # 5 min (ms)

    X = [[[Bool(f"x_{w}_{p}_{m}") for m in range(P)]
          for p in range(P)]
         for w in range(W)]
    Swap = [[Bool(f"swap_{w}_{p}") for p in range(P)]
            for w in range(W)]

    # 3.1  exactly-one per slot
    for w in range(W):
        for p in range(P):
            opt.add(exactly_one(X[w][p]))

    # 3.2  permutation: each match appears once per week
    for w in range(W):
        for m in range(P):
            opt.add(exactly_one([X[w][p][m] for p in range(P)]))

    # 3.3  ≤ 2 occurrences of every team in every row
    for p in range(P):
        for t in range(1, n + 1):
            lits = [X[w][p][m]
                    for w in range(W)
                    for m in range(P)
                    if A[w][m] == t or B[w][m] == t]
            if len(lits) > 2:
                opt.add(AtMost(*lits, 2))

    # 3. identity permutation if table already feasible
    if already_ok:
        for w in range(W):
            for p in range(P):
                for m in range(P):
                    opt.add(X[w][p][m] if m == p else Not(X[w][p][m]))

    for p in range(P):
        for m in range(P):
            opt.add(X[0][p][m] if m == p else Not(X[0][p][m]))

    # 4. home counts
    home = [Int(f"home_{t}") for t in range(1, n + 1)]
    Wint = IntVal(W)

    for idx, t in enumerate(range(1, n + 1)):
        terms = []
        for w in range(W):
            for p in range(P):
                for m in range(P):
                    if A[w][m] == t:
                        terms.append(If(X[w][p][m] & Not(Swap[w][p]), 1, 0))
                    if B[w][m] == t:
                        terms.append(If(X[w][p][m] & Swap[w][p], 1, 0))
        opt.add(home[idx] == sum(terms))

    # 5. maxImbalance objective
    maxI = Int("maxImbalance")
    for hc in home:
        diff = hc * 2 - Wint  # home-away difference
        opt.add(maxI >= diff)
        opt.add(maxI >= -diff)
    opt.minimize(maxI)
    return opt, X, Swap, A, B, maxI


# --------------------------------------------------------------------------- #
# decode timetable
# --------------------------------------------------------------------------- #
def decode(model, X, Swap, A, B):
    W, P = len(X), len(X[0])
    tbl = [[None] * W for _ in range(P)]
    for w in range(W):
        for p in range(P):
            swp = model.eval(Swap[w][p], model_completion=True)
            for m, lit in enumerate(X[w][p]):
                if model.eval(lit, model_completion=True):
                    a, b = (B[w][m], A[w][m]) if swp else (A[w][m], B[w][m])
                    tbl[p][w] = [a, b]
                    break
    return tbl


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage:  python sat_rr_opt_merged.py <even n>")

    n = int(sys.argv[1])
    ticker = threading.Thread(target=_ticker, daemon=True)
    ticker.start()

    opt, X, Swap, A, B, maxI = build_opt_solver(n)
    res = opt.check()

    _stop.set()
    ticker.join()

    if res != sat:
        print("[]")  # unsat / timeout
        sys.exit(0)

    mdl = opt.model()
    sched = decode(mdl, X, Swap, A, B)
    k_opt = mdl.evaluate(maxI).as_long()

    # # try dumping DIMACS (not available in some Z3 builds)
    # try:
    #     pathlib.Path(f"sat_rr_opt_n{n}.cnf").write_text(opt.dimacs())
    # except AttributeError:
    #     pass

    # JSON output
    out = {
        "z3": {
            "optimal": True,
            "obj": k_opt,
            "time_ms": int(opt.statistics().get_key_value("time")),
            "sol": sched,
        }
    }
    # print(json.dumps(out, indent=2))
    print(k_opt, '\n\n')
    print(sched)