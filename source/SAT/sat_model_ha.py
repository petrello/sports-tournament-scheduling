from typing import List

from z3 import Solver, And, Bool, Not, Or

from sat_encodings import (
    exactly_one,
    at_most_k,
    lex_less_onehot_seq     # strict lex on sequences of one-hot vectors
)


class SATModelHA:
    @staticmethod
    def build_solver(
            n: int, use_symmetry_breaking_constraints: bool
    ) -> Solver:
        #====================================================================
        # INSTANCE PARAMETER
        #====================================================================
        assert n % 2 == 0 and n >= 2, "n must be even and ≥2"
        W = n - 1
        P = n // 2

        solver = Solver()

        #====================================================================
        # DECISION VARIABLES (one-hot per slot)
        #====================================================================
        # Home[p][w][t] / Away[p][w][t] indicate team t placed at (p,w)
        Home: List[List[List[Bool]]] = [
            [[Bool(f"H_{p + 1}_{w + 1}_{t + 1}") for t in range(n)] for w in range(W)]
            for p in range(P)
        ]
        Away: List[List[List[Bool]]] = [
            [[Bool(f"A_{p + 1}_{w + 1}_{t + 1}") for t in range(n)] for w in range(W)]
            for p in range(P)
        ]

        #====================================================================
        # CONSTRAINTS
        #====================================================================

        #--- Main constraint: exactly one home and one away per slot
        #    If SB is ON: also enforce a canonical orientation (home < away)
        for p in range(P):
            for w in range(W):
                solver.add(exactly_one(Home[p][w]))
                solver.add(exactly_one(Away[p][w]))
                # forbid equal team at both Home and Away in the same slot
                for i in range(n):
                    solver.add(Or(Not(Home[p][w][i]), Not(Away[p][w][i])))
                    if use_symmetry_breaking_constraints:
                        # canonical orientation home < away: forbid j <= i
                        for j in range(i + 1):
                            solver.add(Or(Not(Home[p][w][i]), Not(Away[p][w][j])))

        #--- Main constraint: every unordered pair {i,j} occurs exactly once
        for i in range(n):
            for j in range(i + 1, n):
                pair_codes = [
                    Or(
                        And(Home[p][w][i], Away[p][w][j]),  # i home, j away
                        And(Home[p][w][j], Away[p][w][i])   # j home, i away
                    )
                    for p in range(P) for w in range(W)
                ]
                solver.add(exactly_one(pair_codes))

        #--- Main constraint: each team plays exactly once per week
        for w in range(W):
            for t in range(n):
                week_slots_t = [Home[p][w][t] for p in range(P)] + \
                               [Away[p][w][t] for p in range(P)]
                solver.add(exactly_one(week_slots_t))

        #--- Main constraint: each team appears in the same period at most twice
        for p in range(P):
            for t in range(n):
                slots_t = [Home[p][w][t] for w in range(W)] + \
                          [Away[p][w][t] for w in range(W)]
                solver.add(*at_most_k(slots_t, 2, name=f"t{t}_p{p}"))

        if use_symmetry_breaking_constraints:
            #--- Symmetry breaking: fix week 1 to (1,2), (3,4), …, (n-1,n)
            for p in range(P):
                h_t = 2 * p
                a_t = 2 * p + 1
                # force exactly these to be true; others false at week 1
                for t in range(n):
                    solver.add(Home[p][0][t] if t == h_t else Not(Home[p][0][t]))
                    solver.add(Away[p][0][t] if t == a_t else Not(Away[p][0][t]))

            #--- Symmetry breaking: strict lex between periods (rows)
            # Compare concatenation [Away[p][w] for w] ++ [Home[p][w] for w]  vs  p+1
            for p in range(P - 1):
                Xp = [Away[p][w]     for w in range(W)] + [Home[p][w]     for w in range(W)]
                Yp = [Away[p + 1][w] for w in range(W)] + [Home[p + 1][w] for w in range(W)]
                solver.add(lex_less_onehot_seq(Xp, Yp))

            #--- Symmetry breaking: strict lex between weeks (columns)
            # Compare concatenation [Away[p][w] for p] ++ [Home[p][w] for p]  vs  w+1
            for w in range(W - 1):
                Xw = [Away[p][w]     for p in range(P)] + [Home[p][w]     for p in range(P)]
                Yw = [Away[p][w + 1] for p in range(P)] + [Home[p][w + 1] for p in range(P)]
                solver.add(lex_less_onehot_seq(Xw, Yw))

        return solver
