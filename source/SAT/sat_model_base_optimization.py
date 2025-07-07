#!/usr/bin/env python3
# --------------------------------------------------------------------------- #
#  CDMO 2024/25 –  Round-robin STS  (optimisation version, faithful to MiniZinc)
#
#  • deterministic circle tables *without* extra row-swap heuristic – identical
#    to the MiniZinc pre-computed arrays A (home) and B (away)
#  • Boolean decision vars:
#        X[w][p][m]  → match *m* placed in row *p* of week *w*
#        Swap[w][p]  → flip home/away in that slot
#  • Constraints:
#        (1) weekly permutation            – exactly-one row / column
#        (2) team ≤2 appearances per row   – AtMost 2 over all weeks
#        (3) symmetry breaking             – first week fixed & Swap[0,*]=False
#  • Objective: minimise  maxImbalance = max_t |2·homeCount[t] – W|
#  • Z3 Optimize with 5-min cap, optional DIMACS dump if build supports it
# --------------------------------------------------------------------------- #

import sys, time, json, pathlib, threading
from z3 import (
    Optimize, Bool, Not, Or, AtMost, If,
    Int, IntVal, sat, And, AtLeast
)

from z3 import Bool, Not, Or, And

# --------------------------------------------------------------------------- #
# helper: sequential “exactly-one”  (Or ∧ AtMost 1)
# --------------------------------------------------------------------------- #
def exactly_one(bool_vars):
    """Z3 encoding of "Exactly k" over bool_vars."""
    return And(AtLeast(*bool_vars, 1), AtMost(*bool_vars, 1))


# --------------------------------------------------------------------------- #
# progress ticker (stderr)
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
# circle-method tables  (ordered larger,smaller) – exactly as in MiniZinc
# --------------------------------------------------------------------------- #

def circle_tables(n: int):
    """Return tables A (home) and B (away) identical to the MiniZinc arrays."""
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
    return A, B


# --------------------------------------------------------------------------- #
# build optimisation model
# --------------------------------------------------------------------------- #

def build_opt_solver(n: int):
    assert n % 2 == 0 and n >= 2, "n must be even ≥ 2"
    A, B = circle_tables(n)
    W, P = len(A), len(A[0])

    opt = Optimize()
    opt.set(timeout=300_000)  # 5 minutes (ms)

    # Boolean variables
    X    = [[[Bool(f"x_{w}_{p}_{m}") for m in range(P)] for p in range(P)] for w in range(W)]
    Swap = [[Bool(f"swap_{w}_{p}") for p in range(P)] for w in range(W)]

    # 1. permutation constraints (weekly)
    for w in range(W):
        # each row hosts exactly one match
        for p in range(P):
            opt.add(exactly_one(X[w][p]))
        # each match used once per week
        for m in range(P):
            opt.add(exactly_one([X[w][p][m] for p in range(P)]))

    # 2. capacity ≤2 per team per row (across weeks)
    for p in range(P):
        for t in range(1, n + 1):
            lits = [X[w][p][m]
                    for w in range(W)
                    for m in range(P)
                    if A[w][m] == t or B[w][m] == t]
            opt.add(AtMost(*lits, 2))
            # sequential_at_most_2(opt, lits, f"c_p{p}_t{t}")


    # 3. symmetry breaking – week 0 fixed, Swap[0][*] = False
    for p in range(P):
        for m in range(P):
            opt.add(X[0][p][m] if m == p else Not(X[0][p][m]))
        opt.add(Not(Swap[0][p]))

    # 4. home counts per team
    home = [Int(f"home_{t}") for t in range(1, n + 1)]
    Wval = IntVal(W)

    for idx, t in enumerate(range(1, n + 1)):
        terms = []
        for w in range(W):
            for p in range(P):
                for m in range(P):
                    # A is home when Swap false, B when Swap true
                    if A[w][m] == t:
                        terms.append(If(X[w][p][m] & Not(Swap[w][p]), 1, 0))
                    if B[w][m] == t:
                        terms.append(If(X[w][p][m] & Swap[w][p], 1, 0))
        opt.add(home[idx] == sum(terms))

    # 5. objective: minimise maximum imbalance
    maxI = Int("maxImbalance")
    for hc in home:
        diff = hc * 2 - Wval  # home-away difference
        opt.add(maxI >= diff)
        opt.add(maxI >= -diff)
    opt.minimize(maxI)

    return opt, X, Swap, A, B, maxI, home


# --------------------------------------------------------------------------- #
# decode schedule to [[period][week] = [home, away]]
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
# CLI entry-point
# --------------------------------------------------------------------------- #

def main():
    if len(sys.argv) != 2:
        sys.exit("usage:  python sat_rr_optim.py <even n>")

    n = int(sys.argv[1])
    ticker = threading.Thread(target=_ticker, daemon=True)
    ticker.start()

    opt, X, Swap, A, B, maxI, hc = build_opt_solver(n)
    res = opt.check()

    _stop.set()
    ticker.join()

    if res != sat:
        print("[]")  # UNSAT / timeout
        sys.exit(0)

    mdl = opt.model()
    sched = decode(mdl, X, Swap, A, B)
    k_opt = mdl.evaluate(maxI).as_long()

    for h in hc:
        # print home counts
        print(mdl.evaluate(h).as_long(), end=" ")

    # # try DIMACS dump (depends on Z3 build)
    # try:
    #     pathlib.Path(f"sat_rr_opt_n{n}.cnf").write_text(opt.dimacs())
    # except AttributeError:
    #     pass

    # JSON output (solver stats + solution)
    out = {
        "z3": {
            "optimal": True,
            "obj": k_opt,
            "time_ms": int(opt.statistics().get_key_value("time")),
            "sol": sched,
        }
    }
    # print(json.dumps(out, indent=2))
    print("IMBALANCE", k_opt)
    print(sched)


if __name__ == "__main__":
    main()
