from typing import List, Union, Optional
from z3 import Solver, Optimize, Int, Bool, IntVal, And, Or, If, Distinct, Sum, Abs, Not

#====================================================================
# Helper: deterministic array read over a constant Python list
#====================================================================
def select_const(values: List[int], idx: Int) -> Int:
    """
    Read values[idx] for 1-based idx ∈ {1..len(values)} using a nested If-chain.
    """
    expr = IntVal(values[-1])          # default/else branch
    for k in range(len(values) - 2, -1, -1):
        expr = If(idx == k + 1, IntVal(values[k]), expr)
    return expr

def lex_less_seq(X: List[Int], Y: List[Int]):
    """ Strict lexicographic comparison of two sequences X and Y.
        Returns True if X < Y in lexicographic order.
    """
    terms = []
    for k in range(len(X)):
        prefix_eq = And(*[X[i] == Y[i] for i in range(k)]) if k > 0 else True
        terms.append(And(prefix_eq, X[k] < Y[k]))
    return Or(*terms)

class SMTModelRR:
    @staticmethod
    def build_solver(
        n: int,
        optimization: bool,
        use_symmetry_breaking_constraints: bool
    ) -> tuple[
        Union[Solver, Optimize],
        List[List[Int]],                   # pos
        Optional[List[List[Bool]]],        # swap (None if optimization=False)
        List[List[int]],                   # A (precomputed)
        List[List[int]],                   # B (precomputed)
        Optional[Int]                      # maxImbalance (None if optimization=False)
    ]:
        #====================================================================
        # INSTANCE PARAMETER
        #====================================================================
        assert n % 2 == 0 and n >= 2, "n must be even and >= 2"
        W = n - 1                          # number of weeks
        P = n // 2                         # number of periods

        solver = Optimize() if optimization else Solver()

        #====================================================================
        # PRECOMPUTED MATCH TABLES (circle method)
        #====================================================================
        # For each week w and match index k, A[w][k] vs B[w][k] defines the pair.
        # If optimization=False, we canonicalize pairs so A[w][k] ≥ B[w][k].
        A: List[List[int]] = [[0] * P for _ in range(W)]
        B: List[List[int]] = [[0] * P for _ in range(W)]
        for w in range(1, W + 1):
            for p in range(1, P + 1):
                a_raw = n if p == 1 else ((w - 1) + (p - 1)) % (n - 1) + 1
                b_raw = w if p == 1 else ((n - 1) - (p - 1) + (w - 1)) % (n - 1) + 1
                A[w - 1][p - 1] = max(a_raw, b_raw)
                B[w - 1][p - 1] = min(a_raw, b_raw)

        #====================================================================
        # DECISION VARIABLES
        #====================================================================
        # pos[w][p] ∈ {1..P} chooses which match index k is placed at (w,p)
        pos: List[List[Int]] = [[Int(f"pos_{w+1}_{p+1}") for p in range(P)] for w in range(W)]
        for w in range(W):
            for p in range(P):
                solver.add(And(1 <= pos[w][p], pos[w][p] <= P))

        # swap[w][p] toggles A↔B at (w,p) (only when optimizing balance)
        swap: Optional[List[List[Bool]]] = (
            [[Bool(f"swap_{w+1}_{p+1}") for p in range(P)] for w in range(W)]
            if optimization else None
        )

        #====================================================================
        # CONSTRAINTS
        #====================================================================

        #--- Main constraint: per-week permutation of match indices
        for w in range(W):
            solver.add(Distinct(*pos[w]))

        #--- Main constraint: each team appears in the same period at most twice
        for p in range(P):
            for t in range(1, n + 1):
                terms = []
                for w in range(W):
                    idx = pos[w][p]
                    a_val = select_const(A[w], idx)
                    b_val = select_const(B[w], idx)
                    terms.append(If(a_val == t, 1, 0))
                    terms.append(If(b_val == t, 1, 0))
                solver.add(Sum(*terms) <= 2)

        #====================================================================
        # SYMMETRY BREAKING
        #====================================================================
        if use_symmetry_breaking_constraints:
            #--- Symmetry breaking: fix week 1 to identity permutation
            for p in range(P):
                solver.add(pos[0][p] == p + 1)
                if swap is not None:
                    solver.add(swap[0][p] == False)

            #--- Symmetry breaking: strict lex between periods (rows)
            for p in range(P - 1):
                Xp = [select_const(B[w], pos[w][p])     for w in range(W)] + \
                    [select_const(A[w], pos[w][p])     for w in range(W)]
                Yp = [select_const(B[w], pos[w][p + 1]) for w in range(W)] + \
                    [select_const(A[w], pos[w][p + 1]) for w in range(W)]
                solver.add(lex_less_seq(Xp, Yp))

            #--- Symmetry breaking: strict lex between weeks (columns)
            for w in range(W - 1):
                Xw = [select_const(B[w],     pos[w][p])     for p in range(P)] + \
                    [select_const(A[w],     pos[w][p])     for p in range(P)]
                Yw = [select_const(B[w + 1], pos[w + 1][p]) for p in range(P)] + \
                    [select_const(A[w + 1], pos[w + 1][p]) for p in range(P)]
                solver.add(lex_less_seq(Xw, Yw))

        #====================================================================
        # OPTIMIZATION (optional): minimize maximum home/away imbalance
        #====================================================================
        max_imbalance: Optional[Int] = None
        if optimization:
            assert swap is not None
            max_imbalance = Int("maxImbalance")
            solver.add(And(0 <= max_imbalance, max_imbalance <= W))

            # home_count[t] = number of weeks where team t is at home
            home_count = [Int(f"home_{t}") for t in range(1, n + 1)]
            for t, hc in enumerate(home_count, start=1):
                terms = []
                for w in range(W):
                    for p in range(P):
                        idx = pos[w][p]
                        a_val = select_const(A[w], idx)
                        b_val = select_const(B[w], idx)
                        # A at home if not swapped; B at home if swapped
                        terms.append(If(And(a_val == t, Not(swap[w][p])), 1, 0))
                        terms.append(If(And(b_val == t,     swap[w][p]), 1, 0))
                solver.add(hc == Sum(*terms))

            # maxImbalance ≥ |2 * home_count[t] - W| for all teams
            for hc in home_count:
                solver.add(max_imbalance >= Abs(2 * hc - W))

            solver.minimize(max_imbalance)

        return solver, pos, swap, A, B, max_imbalance
