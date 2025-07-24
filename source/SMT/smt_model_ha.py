from typing import List, Tuple
from z3 import Solver, Int, Distinct, Sum, And, If, Implies


class SMTModelHA:
    @staticmethod
    def build_solver(
            n: int, use_symmetry_breaking_constraints: bool
    ) -> Tuple[Solver, List[List[Int]], List[List[Int]]]:
        assert n % 2 == 0 and n >= 2, "n must be even and ≥2"

        W = n - 1  # number of weeks
        P = n // 2  # number of periods

        solver = Solver()

        # ------------------------------------------------------------------
        # variables  (1‑based indices in comments for human readability)
        Home: List[List[Int]] = [
            [ Int(f"H_{p+1}_{w+1}") for w in range(W) ]
            for p in range(P)
        ]
        Away: List[List[Int]] = [
            [ Int(f"A_{p+1}_{w+1}") for w in range(W) ]
            for p in range(P)
        ]

        # domain 1..n
        for p in range(P):
            for w in range(W):
                solver.add(And(1 <= Home[p][w], Home[p][w] <= n))
                solver.add(And(1 <= Away[p][w], Away[p][w] <= n))

        # (2) every unordered pair occurs exactly once
        pair_codes = [ Home[p][w] * n + Away[p][w]
                       for p in range(P) for w in range(W) ]
        solver.add(Distinct(*pair_codes))

        # (3) each team plays exactly once per week  (all‑different inside week)
        for w in range(W):
            week_slots = [ Home[p][w] for p in range(P) ] + \
                         [ Away[p][w] for p in range(P) ]
            solver.add(Distinct(*week_slots))

        # (4) each team plays in the same period at most twice
        for p in range(P):
            slots = [ Home[p][w] for w in range(W) ] + \
                    [ Away[p][w] for w in range(W) ]
            for t in range(1, n+1):
                solver.add(Sum([ If(slot == t, 1, 0) for slot in slots ]) <= 2)

        if use_symmetry_breaking_constraints:
            # (1) unordered pair: Home < Away
            for p in range(P):
                for w in range(W):
                    solver.add(Home[p][w] < Away[p][w])

            # (5) symmetry break: week 1 is (1,2),(3,4),…
            for p in range(P):
                solver.add(Home[p][0] == 2*p + 1)
                solver.add(Away[p][0] == 2*p + 2)

            # (6) lex_lesseq on first row of Home (period 1)
            for w in range(W - 1):
                prefix_equal = And([ Home[0][k] == Home[0][k+1] for k in range(w) ])
                solver.add(Implies(prefix_equal, Home[0][w] <= Home[0][w+1]))

        return solver, Home, Away