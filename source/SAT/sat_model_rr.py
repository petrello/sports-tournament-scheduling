from typing import List
from z3 import Solver, And, Bool, Not, Or

from sat_encodings import (
    exactly_one,
    at_most_k,
    lex_less_onehot_seq,     # strict lex on sequences of one-hot vectors
    team_onehot_from_pos,    # derived team one-hot from (table,pos)
)

class SATModelRR:
    @staticmethod
    def build_solver(
            n: int,
            optimization: bool,
            use_symmetry_breaking_constraints: bool
    ) -> tuple[
        Solver,
        List[List[List[Bool]]],          # pos
        List[List[Bool]] | None,         # swap (None if opt=False)
        List[List[int]],                 # Home (precomputed)
        List[List[int]],                 # Away (precomputed)
        List[List[Bool]] | None          # H weekly home literals (None if opt=False)
    ]:
        #====================================================================
        # INSTANCE PARAMETER
        #====================================================================
        assert n % 2 == 0 and n >= 2, "n must be even and ≥2"
        W = n - 1                         # number of weeks
        P = n // 2                        # number of periods

        solver = Solver()

        #====================================================================
        # PRECOMPUTED MATCH TABLES (circle method, canonicalized unordered)
        #====================================================================
        Home: list[list[int]] = [[0] * P for _ in range(W)]
        Away: list[list[int]] = [[0] * P for _ in range(W)]
        for w in range(1, W + 1):
            for p in range(1, P + 1):
                home_raw = n if p == 1 else ((w - 1) + (p - 1)) % (n - 1) + 1
                away_raw = w if p == 1 else ((n - 1) - (p - 1) + (w - 1)) % (n - 1) + 1
                # canonical: higher-numbered team in Home, lower in Away
                Home[w - 1][p - 1] = max(home_raw, away_raw)
                Away[w - 1][p - 1] = min(home_raw, away_raw)

        #====================================================================
        # DECISION VARIABLES
        #====================================================================
        # pos[w][p][k] : one-hot → which match index k is placed at (week w, period p)
        pos: List[List[List[Bool]]] = [
            [[Bool(f"pos_{w + 1}_{p + 1}_{k + 1}") for k in range(P)] for p in range(P)]
            for w in range(W)
        ]

        # swap[w][p] : flips Home ↔ Away at (w,p) [only if optimization=True]
        swap = (
            [[Bool(f"swap_{w + 1}_{p + 1}") for p in range(P)] for w in range(W)]
            if optimization else None
        )

        #====================================================================
        # CONSTRAINTS
        #====================================================================

        #--- Main constraint: exactly one match index per slot
        for w in range(W):
            for p in range(P):
                solver.add(exactly_one(pos[w][p]))

        #--- Main constraint: per-week permutation of match indices
        for w in range(W):
            for k in range(P):
                solver.add(exactly_one([pos[w][p][k] for p in range(P)]))

        #--- Main constraint: each team appears in the same period at most twice
        for p in range(P):
            for t in range(1, n + 1):
                occ = []
                for w in range(W):
                    ks = [pos[w][p][k] for k in range(P) if Home[w][k] == t or Away[w][k] == t]
                    if ks:
                        occ.append(Or(*ks))
                solver.add(*at_most_k(occ, 2, name=f"t{t}_p{p}"))

        if use_symmetry_breaking_constraints:
            #--- Symmetry breaking: fix week 1 to identity permutation
            for p in range(P):
                for k in range(P):
                    solver.add(pos[0][p][k] if k == p else Not(pos[0][p][k]))
                if optimization:
                    solver.add(Not(swap[0][p]))  # fixed orientation in week 1 if optimizing

            #--- Symmetry breaking: strict lex between periods (rows)
            # Compare concatenation [Away[w,p]] for w ++ [Home[w,p]] for w   vs  p+1
            for p in range(P - 1):
                Xp = [team_onehot_from_pos(Away, pos, w, p,   n, P) for w in range(W)] + \
                     [team_onehot_from_pos(Home, pos, w, p,   n, P) for w in range(W)]
                Yp = [team_onehot_from_pos(Away, pos, w, p+1, n, P) for w in range(W)] + \
                     [team_onehot_from_pos(Home, pos, w, p+1, n, P) for w in range(W)]
                solver.add(lex_less_onehot_seq(Xp, Yp))

            #--- Symmetry breaking: strict lex between weeks (columns)
            # Compare concatenation [Away[w,p]] for p ++ [Home[w,p]] for p   vs  w+1
            for w in range(W - 1):
                Xw = [team_onehot_from_pos(Away, pos, w,   p, n, P) for p in range(P)] + \
                     [team_onehot_from_pos(Home, pos, w,   p, n, P) for p in range(P)]
                Yw = [team_onehot_from_pos(Away, pos, w+1, p, n, P) for p in range(P)] + \
                     [team_onehot_from_pos(Home, pos, w+1, p, n, P) for p in range(P)]
                solver.add(lex_less_onehot_seq(Xw, Yw))

        #====================================================================
        # WEEKLY HOME LITERALS (for optimization bounding)
        #====================================================================
        H: List[List[Bool]] | None = None
        if optimization:
            # H[t][w] = “team t plays at home in week w”
            H = [[None] * W for _ in range(n + 1)]  # teams are 1..n
            for t in range(1, n + 1):
                for w in range(W):
                    kA = next((k for k in range(P) if Home[w][k] == t), None)
                    kB = next((k for k in range(P) if Away[w][k] == t), None)
                    if kA is not None:
                        H[t][w] = Or(*[And(pos[w][p][kA], Not(swap[w][p])) for p in range(P)])
                    else:
                        H[t][w] = Or(*[And(pos[w][p][kB],      swap[w][p]) for p in range(P)])

        return solver, pos, swap, Home, Away, H
