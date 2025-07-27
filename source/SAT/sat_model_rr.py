from typing import List
from z3 import Solver, And, Bool, Not, Or, Implies, PbEq

from sat_encodings import exactly_one, at_most_k, at_most_one


class SATModelRR:
    @staticmethod
    def build_solver(
            n: int, optimization: bool
    ) -> tuple[Solver, List[List[List[Bool]]], List[List[Bool]], List[List[int]], List[List[int]], List[Bool]]:
        assert n % 2 == 0 and n >= 2, "n must be even and >= 2"

        W = n - 1   # number of weeks
        P = n // 2  # number of periods

        solver = Solver()

        # --------------------------------------------------------------
        # 1) pre‑compute A and B (circle method, 0‑based Python indices)
        # --------------------------------------------------------------
        A: list[list[int]] = [[0] * P for _ in range(W)]
        B: list[list[int]] = [[0] * P for _ in range(W)]

        for w in range(1, W + 1):
            for p in range(1, P + 1):
                a_raw = n if p == 1 else ((w - 1) + (p - 1)) % (n - 1) + 1
                b_raw = w if p == 1 else ((n - 1) - (p - 1) + (w - 1)) % (n - 1) + 1
                if optimization:
                    A[w - 1][p - 1] = a_raw
                    B[w - 1][p - 1] = b_raw
                else:
                    A[w - 1][p - 1] = max(a_raw, b_raw)
                    B[w - 1][p - 1] = min(a_raw, b_raw)

        # ---------- 2) Decision variables: Pos[w][p][k] ----------
        # Pos[w][p][k] is one-hot over k = 1..P
        pos: List[List[List[Bool]]] = [
            [[Bool(f"pos_{w + 1}_{p + 1}_{k + 1}") for k in range(P)] for p in range(P)] for w in range(W)
        ]

        swap = (
            [[Bool(f"swap_{w + 1}_{p + 1}") for p in range(P)] for w in range(W)]
            if optimization
            else None
        )

        # One-hot per slot: for each (w,p), exactly one k
        for w in range(W):
            for p in range(P):
                solver.add(exactly_one(pos[w][p]))

        # ---------- 3a) Each week uses every match index exactly once ----------
        # Distinct(pos[w]) → permutation. Boolean encoding:
        # For each week w and each k, exactly one period p selects k.
        for w in range(W):
            for k in range(P):
                solver.add(exactly_one([pos[w][p][k] for p in range(P)]))

        # ---------- 3b) <= 2 appearances per team in the same row p over weeks ----------
        # For each row p and team t (1...n),
        #   occurrences across "weeks" where the chosen match index k has that team in A[w][k] or B[w][k].
        # Build a boolean occ[w] = OR_k ( Pos[w][p][k] ∧ (team in {A[w][k],B[w][k]}) )
        for p in range(P):
            for t in range(1, n + 1):
                occ = []
                for w in range(W):
                    # For each k, team t may appear in [A[w][k], B[w][k]] (1-based teams)
                    ks = [pos[w][p][k] for k in range(P) if A[w][k] == t or B[w][k] == t]
                    # If team never appears in any k at this week/row, then no contribution
                    if ks: occ.append(Or(*ks))
                solver.add(at_most_k(occ, 2, name=f"t{t}_p{p}"))

        # ---------- 3c) Symmetry break: week 1 is identity permutation ----------
        # pos[0][p] = p+1 → Pos[0][p][p] = True and all other Pos[0][p][k!=p] = False
        for p in range(P):
            for k in range(P):
                solver.add(pos[0][p][k] if k == p else Not(pos[0][p][k]))
            if optimization:
                solver.add(Not(swap[0][p]))  # No swap in week 1

        # -------- "Optimisation" variables as constraints ------------------
        # Boolean ladder bits: maxImb_ge[m]  <=>  maxImbalance >= m
        max_imbalance: List[Bool] = (
            [Bool(f"maxImb_{m}") for m in range(W + 1)] if optimization else None
        )

        if optimization:
            # ---------- home/away balancing ----------
            for m in range(W):
                solver.add(Implies(max_imbalance[m + 1], max_imbalance[m]))

            # For each team t, create eq-flags "homeCnt_t_eq_v"
            for t in range(1, n + 1):
                home_lits = []
                for w in range(W):
                    for p in range(P):
                        for k in range(P):
                            if A[w][k] == t:
                                home_lits.append(And(pos[w][p][k], Not(swap[w][p])))
                            if B[w][k] == t:
                                home_lits.append(And(pos[w][p][k], swap[w][p]))

                eq_flags = []
                for v in range(W + 1):
                    f = Bool(f"homeCnt_{t}_eq_{v}")
                    eq_flags.append(f)
                    solver.add(Implies(f, PbEq([(b, 1) for b in home_lits], v)))
                solver.add(at_most_one(eq_flags))
                solver.add(exactly_one(eq_flags))

                # Link to maxImb ladder: if homeCnt=v then maxImb ≥ |2v-W|
                for v in range(W + 1):
                    dev = abs(2 * v - W)
                    solver.add(Implies(eq_flags[v], max_imbalance[dev]))

        return solver, pos, swap, A, B, max_imbalance
