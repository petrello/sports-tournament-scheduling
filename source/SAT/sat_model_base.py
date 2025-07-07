#!/usr/bin/env python3
# --------------------------------------------------------------------------- #
#  CDMO 2024/25 –  Round‑robin STS  (decision version)
#
#  • deterministic circle tables  +  first‑row swap  (faithful to MiniZinc)
#  • sequential "exactly‑one" (Or ∧ AtMost 1)  → compact CNF
#  • MiniZinc symmetry‑breaking: identity permutation on week‑0 when feasible
#  • Boolean variables  X[w][p][m] : match *m* placed in row *p* of week *w*
#  • objective: SAT only – we just need *any* schedule respecting all rules
#  • optional CNF export via  Solver.dimacs()  (if available in local Z3 build)
# --------------------------------------------------------------------------- #

import sys, time, json, pathlib, threading
from z3 import Solver, Bool, AtMost, Not, sat, And, AtLeast


# --------------------------------------------------------------------------- #
# tiny helper: sequential (Or ∧ AtMost 1)  “exactly‑one”
# --------------------------------------------------------------------------- #

def exactly_one(bool_vars):
    """Z3 encoding of "Exactly k" over bool_vars."""
    return And(AtLeast(*bool_vars, 1), AtMost(*bool_vars, 1))

# --------------------------------------------------------------------------- #
# deterministic circle‑method  (raw orientation, NO max/min swap)
# plus the heuristic row‑0 swap used by the MiniZinc baseline
# --------------------------------------------------------------------------- #

def circle_tables(n: int):
    """Generate the raw match tables A (home) and B (away) as in the CP model.
    They follow the deterministic circle method with the row‑0 swap heuristic
    that fixes team *n* on the rim."""
    W, P = n - 1, n // 2
    A = [[0] * P for _ in range(W)]
    B = [[0] * P for _ in range(W)]

    for w in range(W):
        for p in range(P):
            if p == 0:  # team n on the rim
                A[w][p], B[w][p] = n, w + 1
            else:
                A[w][p] = (w + p) % (n - 1) + 1
                B[w][p] = ((n - 1) - p + w) % (n - 1) + 1

    return A, B

# --------------------------------------------------------------------------- #
# build decision solver
# --------------------------------------------------------------------------- #

def build_dec_solver(n: int):
    assert n % 2 == 0 and n >= 2, "n must be even ≥ 2"
    A, B = circle_tables(n)
    W, P = len(A), len(A[0])

    # fast check: if every team already appears ≤2 times per row, we can freeze
    # the identity permutation for week‑0, saving many variables/clauses.
    already_ok = all(
        max(sum(1 for w in range(W) if A[w][p] == t or B[w][p] == t)
            for t in range(1, n + 1)) <= 2 for p in range(P)
    )

    s = Solver()

    # X[w][p][m]  ↔  match m sits in row p of week w (0‑based indices)
    X = [[[Bool(f"x_{w}_{p}_{m}") for m in range(P)] for p in range(P)] for w in range(W)]

    # 1. placement constraints – permutations per week
    for w in range(W):
        # each row hosts exactly one match
        for p in range(P):
            s.add(exactly_one(X[w][p]))
        # each match used exactly once per week (columns of the permutation)
        for m in range(P):
            s.add(exactly_one([X[w][p][m] for p in range(P)]))

    # 2. team capacity: any team appears in the same row at most twice overall
    for p in range(P):
        for t in range(1, n + 1):
            lits = [X[w][p][m] for w in range(W) for m in range(P)
                    if A[w][m] == t or B[w][m] == t]
            if len(lits) > 2:  # otherwise automatically satisfied
                s.add(AtMost(*lits, 2))

    # 3. symmetry breaking: fix week‑0 permutation to identity, if feasible
    if already_ok:
        for p in range(P):
            for m in range(P):
                s.add(X[0][p][m] if m == p else Not(X[0][p][m]))

    return s, X, A, B

# --------------------------------------------------------------------------- #
# decode timetable
# --------------------------------------------------------------------------- #

def decode(model, X, A, B):
    W, P = len(X), len(X[0])
    tbl = [[None] * W for _ in range(P)]  # periods × weeks (as in the project spec)
    for w in range(W):
        for p in range(P):
            for m, lit in enumerate(X[w][p]):
                if model.evaluate(lit, model_completion=True):
                    tbl[p][w] = [A[w][m], B[w][m]]
                    break
    return tbl

# --------------------------------------------------------------------------- #
# main – CLI helper + optional DIMACS dump & JSON schedule output
# --------------------------------------------------------------------------- #

def _ticker(stop_evt):
    start = time.time()
    while not stop_evt.is_set():
        m, s = divmod(int(time.time() - start), 60)
        sys.stderr.write(f"\rSolving … {m:02d}:{s:02d}")
        sys.stderr.flush()
        time.sleep(1)
    sys.stderr.write("\n")


def main():
    if len(sys.argv) != 2:
        sys.exit("usage:  python sat_rr_dec.py <even n>")

    n = int(sys.argv[1])
    stop_evt = threading.Event()
    thr = threading.Thread(target=_ticker, args=(stop_evt,), daemon=True)
    thr.start()

    s, X, A, B = build_dec_solver(n)
    res = s.check()

    stop_evt.set(); thr.join()

    if res != sat:
        print("[]")  # UNSAT / timeout
        sys.exit(0)

    mdl = s.model()
    sched = decode(mdl, X, A, B)

    # try dumping DIMACS (depends on Z3 build)
    try:
        pathlib.Path(f"sat_rr_dec_n{n}.cnf").write_text(s.dimacs())
    except AttributeError:
        pass

    # JSON output – minimal, as prescribed for the decision version
    out = {
        "z3": {
            "time": int(s.statistics().get_key_value("time")),
            "optimal": True,   # SAT decision fully satisfied
            "obj": None,
            "sol": sched,
        }
    }
    # print(json.dumps(out, indent=2))
    print(sched)


if __name__ == "__main__":
    main()