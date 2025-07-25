from typing import List, Union
from z3 import Solver, Optimize, Int, Distinct, Sum, And, If, IntVal, Bool, Not, Abs


# ----------------------------------------------------------------------
# helper function
# ----------------------------------------------------------------------

def select_const(values: List[int], idx: Int) -> Int:
    """
    Deterministic “array read” for a *constant* list `values`
    where idx ∈ {1..len(values)}:  nested Ite chain that is pure SMT‑LIB.
    """
    expr = IntVal(values[-1])          # default/else branch
    for k in range(len(values) - 2, -1, -1):
        expr = If(idx == k + 1, IntVal(values[k]), expr)
    return expr

class SMTModelRR:
    @staticmethod
    def build_solver(
            n: int, optimization: bool
    ) -> tuple[Union[Solver, Optimize], List[List[Int]], List[List[Bool]], List[List[Int]], List[List[Int]], List[List[Int]]]:
        assert n % 2 == 0 and n >= 2, "n must be even and >= 2"

        W = n - 1   # number of weeks
        P = n // 2  # number of periods

        if optimization:
            solver = Optimize()
        else:
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

        # --------------------------------------------------------------
        # 2) decision variables  pos[w][p]  ∈ 1..P
        # --------------------------------------------------------------
        pos: List[List[Int]] = [[ Int(f"pos_{w+1}_{p+1}") for p in range(P) ] for w in range(W)]
        swap: List[List[Bool]] = (
            [[Bool(f"swap_{w + 1}_{p + 1}") for p in range(P)] for w in range(W)]
            if optimization
            else None
        )

        for w in range(W):
            for p in range(P):
                solver.add(And(1 <= pos[w][p], pos[w][p] <= P))


        # --------------------------------------------------------------
        # 3a) each week uses every match exactly once   (permutation)
        # --------------------------------------------------------------
        for w in range(W):
            solver.add(Distinct(*pos[w]))

        # --------------------------------------------------------------
        # 3b) <= 2 appearances per team in the same row p across weeks
        # --------------------------------------------------------------
        for p in range(P):
            for t in range(1, n + 1):
                terms = []
                for w in range(W):
                    idx = pos[w][p]
                    a_val = select_const(A[w], idx)
                    b_val = select_const(B[w], idx)
                    terms.extend([
                        If(And(a_val == t), 1, 0),
                        If(And(b_val == t), 1, 0)
                    ])
                solver.add(Sum(*terms) <= 2)

        # --------------------------------------------------------------
        # 3c) symmetry break: week‑1 identity permutation (pos[1,p] = p)
        # --------------------------------------------------------------
        for p in range(P):
            solver.add(pos[0][p] == p + 1)
            if optimization:
                solver.add(swap[0][p] == False)

        # Define the max_imbalance variable for optimization
        max_imbalance: Int = (
            Int("maxImbalance") if optimization else None
        )

        if optimization:
            # ---------- 4. home/away balancing ----------
            home_count = [Int(f"home_{t}") for t in range(1, n + 1)]
            for t, hc in enumerate(home_count, start=1):
                terms = []
                for w in range(W):
                    for p in range(P):
                        idx = pos[w][p]
                        a_val = select_const(A[w], idx)
                        b_val = select_const(B[w], idx)
                        terms.extend([
                            If(And(a_val == t, Not(swap[w][p])), 1, 0),
                            If(And(b_val == t, swap[w][p]),      1, 0)
                        ])
                solver.add(hc == Sum(*terms))

            solver.add(max_imbalance >= 0, max_imbalance <= W)
            for hc in home_count:
                solver.add(max_imbalance >= Abs(2 * hc - W))

            solver.minimize(max_imbalance)

        return solver, pos, swap, A, B, max_imbalance
