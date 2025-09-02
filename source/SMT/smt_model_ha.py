from typing import List
from z3 import Solver, Int, And, Or, If, Distinct, Sum

#====================================================================
# Helper: deterministic array read over a constant Python list
#====================================================================
def lex_less_seq(X: List[Int], Y: List[Int]):
    """ Strict lexicographic comparison of two sequences X and Y.
        Returns True if X < Y in lexicographic order.
    """
    terms = []
    for k in range(len(X)):
        prefix_eq = And(*[X[i] == Y[i] for i in range(k)]) if k > 0 else True
        terms.append(And(prefix_eq, X[k] < Y[k]))
    return Or(*terms)


class SMTModelHA:
    @staticmethod
    def build_solver(
        n: int,
        use_symmetry_breaking_constraints: bool
    ) -> tuple[Solver, List[List[Int]], List[List[Int]], int, int]:
        #====================================================================
        # INSTANCE PARAMETER
        #====================================================================
        assert n % 2 == 0 and n >= 2, "n must be even and ≥2"
        W = n - 1                         # number of weeks
        P = n // 2                        # number of periods

        solver = Solver()

        #====================================================================
        # DECISION VARIABLES (team number in each slot)
        #====================================================================
        Home: List[List[Int]] = [
            [Int(f"H_{p + 1}_{w + 1}") for w in range(W)]
            for p in range(P)
        ]
        Away: List[List[Int]] = [
            [Int(f"A_{p + 1}_{w + 1}") for w in range(W)]
            for p in range(P)
        ]


        #====================================================================
        # CONSTRAINTS
        #====================================================================
        #--- Main constraint: set domains
        for p in range(P):
            for w in range(W):
                solver.add(And(1 <= Home[p][w], Home[p][w] <= n))
                solver.add(And(1 <= Away[p][w], Away[p][w] <= n))

        #--- Main constraint: every unordered pair {i,j} occurs exactly once
        pair_codes = []
        for p in range(P):
            for w in range(W):
                h, a = Home[p][w], Away[p][w]
                mn = If(h < a, h, a)
                mx = If(h < a, a, h)
                pair_codes.append(mn * n + mx)
        solver.add(Distinct(*pair_codes))

        #--- Main constraint: each team plays exactly once per week
        for w in range(W):
            week_vals = [Home[p][w] for p in range(P)] + [Away[p][w] for p in range(P)]
            solver.add(Distinct(*week_vals))

        #--- Main constraint: each team appears in the same period at most twice
        for p in range(P):
            for t in range(1, n + 1):
                occs = [If(Home[p][w] == t, 1, 0) + If(Away[p][w] == t, 1, 0) for w in range(W)]
                solver.add(Sum(occs) <= 2)

        #====================================================================
        # SYMMETRY BREAKING
        #====================================================================
        if use_symmetry_breaking_constraints:
            #--- Symmetry breaking: canonical orientation (home < away)
            for p in range(P):
                for w in range(W):
                    solver.add(Home[p][w] < Away[p][w])

            #--- Symmetry breaking: fix week 1 to (1,2), (3,4), …, (n-1,n)
            for p in range(P):
                solver.add(Home[p][0] == 2 * p + 1)
                solver.add(Away[p][0] == 2 * p + 2)

            #--- Symmetry breaking: strict lex between periods (rows)
            for p in range(P - 1):
                Xp = [Away[p][w]     for w in range(W)] + [Home[p][w]     for w in range(W)]
                Yp = [Away[p + 1][w] for w in range(W)] + [Home[p + 1][w] for w in range(W)]
                solver.add(lex_less_seq(Xp, Yp))

            #--- Symmetry breaking: strict lex between weeks (columns)
            for w in range(W - 1):
                Xw = [Away[p][w]     for p in range(P)] + [Home[p][w]     for p in range(P)]
                Yw = [Away[p][w + 1] for p in range(P)] + [Home[p][w + 1] for p in range(P)]
                solver.add(lex_less_seq(Xw, Yw))

        return solver
