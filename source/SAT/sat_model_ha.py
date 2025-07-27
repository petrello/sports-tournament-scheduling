from typing import List

from z3 import Solver, And, Implies, Bool, Not, Or, BoolVal

from sat_encodings import exactly_one, at_most_k, equiv, less_or_equal_onehot


class SATModelHA:
    @staticmethod
    def build_solver(
            n: int, use_symmetry_breaking_constraints: bool
    ) -> Solver:
        assert n % 2 == 0 and n >= 2, "n must be even and ≥2"
        W = n - 1
        P = n // 2

        solver = Solver()

        # one-hot per slot
        Home: List[List[Bool]] = [
            [[Bool(f"H_{p + 1}_{w + 1}_{t + 1}") for t in range(n)] for w in range(W)] for p in range(P)
        ]
        Away: List[List[Bool]] = [
            [[Bool(f"A_{p + 1}_{w + 1}_{t + 1}") for t in range(n)] for w in range(W)] for p in range(P)
        ]

        # (a) exactly one home & one away per slot + (1) Home < Away
        for p in range(P):
            for w in range(W):
                solver.add(exactly_one(Home[p][w]))
                solver.add(exactly_one(Away[p][w]))
                # forbid equal indices and enforce home<away: for all i >= j: not(H_i & A_j)
                for i in range(n):
                    # not equal
                    solver.add(Implies(Home[p][w][i], Not(Away[p][w][i])))
                    # j <= i forbidden
                    for j in range(i + 1):
                        solver.add(Or(Not(Home[p][w][i]), Not(Away[p][w][j])))

        # (2) every unordered pair occurs exactly once
        for i in range(n):
            for j in range(i + 1, n):
                pair_codes = [
                    And(Home[p][w][i], Away[p][w][j])
                    for p in range(P) for w in range(W)
                ]
                solver.add(exactly_one(pair_codes))

        # (3) each team plays exactly once per week
        for w in range(W):
            for t in range(n):
                week_slots_t = [Home[p][w][t] for p in range(P)] + \
                               [Away[p][w][t] for p in range(P)]
                solver.add(exactly_one(week_slots_t))

        # (4) each team appears in the same period at most twice
        for p in range(P):
            for t in range(n):
                slots_t = [Home[p][w][t] for w in range(W)] + \
                          [Away[p][w][t] for w in range(W)]
                solver.add(at_most_k(slots_t, 2, name=f"team_{t}_period_{p}"))

        if use_symmetry_breaking_constraints:
            # (5) symmetry break: week 1 fixed
            for p in range(P):
                h_t = 2 * p
                a_t = 2 * p + 1
                solver.add(Home[p][0][h_t])
                solver.add(Away[p][0][a_t])
                for t in range(n):
                    if t != h_t:
                        solver.add(Not(Home[p][0][t]))
                    if t != a_t:
                        solver.add(Not(Away[p][0][t]))

                    # (6) lex_lesseq on first row of Home (period 1)
                    for w in range(W - 1):
                        prefix_eq = And(*[
                            equiv(Home[0][k][t], Home[0][k + 1][t])
                            for k in range(w) for t in range(n)
                        ]) if w > 0 else BoolVal(True)
                        solver.add(Implies(prefix_eq, less_or_equal_onehot(Home[0][w], Home[0][w + 1])))

        return solver