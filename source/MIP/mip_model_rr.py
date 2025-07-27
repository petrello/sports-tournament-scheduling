from pickletools import optimize

import pulp as pl
from itertools import combinations

def circle_pairs(n):
    """Return A[w][k], B[w][k] (0-based lists) per the circle method."""
    W, P = n - 1, n // 2
    A = [[0] * P for _ in range(W)]
    B = [[0] * P for _ in range(W)]
    for w in range(1, W + 1):
        for p in range(1, P + 1):
            a_raw = n if p == 1 else ((w - 1) + (p - 1)) % (n - 1) + 1
            b_raw = w if p == 1 else ((n - 1) - (p - 1) + (w - 1)) % (n - 1) + 1
            A[w - 1][p - 1] = max(a_raw, b_raw)
            B[w - 1][p - 1] = min(a_raw, b_raw)
    return A, B

class MIPModelHA:
    @staticmethod
    def build_model(n: int, optimize: bool, name="BalancedSchedule_HomeAway"):
        assert n % 2 == 0 and n >= 2, "n must be even and ≥ 2"
        W, P = n - 1, n // 2

        Weeks = range(1, W + 1)  # 1-based
        Periods = range(1, P + 1)
        Ks = range(1, P + 1)
        Teams = range(1, n + 1)

        A, B = circle_pairs(n)  # 0-based Python lists

        # -------- variables --------
        pos = pl.LpVariable.dicts("pos", (Weeks, Periods), lowBound=1, upBound=P, cat=pl.LpInteger)
        x = pl.LpVariable.dicts("x", (Weeks, Periods, Ks), lowBound=0, upBound=1, cat=pl.LpBinary)
        swap = (
            pl.LpVariable.dicts("swap", (Weeks, Periods), lowBound=0, upBound=1, cat=pl.LpBinary)
            if optimize
            else None
        )

        model = pl.LpProblem(name, pl.LpMinimize)

        if optimize:
            home_count = pl.LpVariable.dicts("homeCnt", Teams, lowBound=0, upBound=W, cat=pl.LpInteger)
            max_imb = pl.LpVariable("maxImbalance", lowBound=0, upBound=W, cat=pl.LpInteger)
        else:
            home_count, max_imb = None, None
            model += 0  # feasibility

        # -------- permutation each week --------
        for w in Weeks:
            # exactly one k in each slot
            for p in Periods:
                model += pl.lpSum(x[w][p][k] for k in Ks) == 1, f"OneK_w{w}_p{p}"
                model += pos[w][p] == pl.lpSum(k * x[w][p][k] for k in Ks), f"LinkPos_w{w}_p{p}"

            # each k used once across periods
            for k in Ks:
                model += pl.lpSum(x[w][p][k] for p in Periods) == 1, f"Perm_w{w}_k{k}"

        # -------- row-wise <= 2 appearances per team --------
        # For each row p, team t: sum over weeks of appearances (in A or B) <= 2
        for p in Periods:
            for t in Teams:
                model += pl.lpSum(
                    # TODO: try to replace or with +
                    x[w][p][k] * ((A[w - 1][k - 1] == t) or (B[w - 1][k - 1] == t))
                    for w in Weeks for k in Ks
                ) <= 2, f"RowCap_t{t}_p{p}"

        # -------- symmetry break week 1 identity --------
        for p in Periods:
            model += pos[1][p] == p, f"Week1Fix_p{p}"
            if optimize:
                model += swap[1][p] == 0, f"Week1SwapFix_p{p}"

        if optimize:
            # -------- home count linearization --------
            #
            # For each slot (w,p,k) and team t:
            #   contribute 1 to homeCnt[t] if:
            #     - A[w,k]==t AND swap[w,p]==0  OR
            #     - B[w,k]==t AND swap[w,p]==1
            #
            # Let yA[w,p,k,t] = x[w,p,k] * (1 - swap[w,p])  when A[w,k]==t
            #     yB[w,p,k,t] = x[w,p,k] * swap[w,p]        when B[w,k]==t
            #
            # We create those only when the constant match actually contains t as A or B.
            yA = {}
            yB = {}

            for w in Weeks:
                for p in Periods:
                    for k in Ks:
                        a_t = A[w - 1][k - 1]
                        b_t = B[w - 1][k - 1]
                        # yA
                        yA[(w, p, k, a_t)] = pl.LpVariable(f"yA_{w}_{p}_{k}_{a_t}", lowBound=0, upBound=1,
                                                           cat=pl.LpBinary)
                        # Constraints: yA <= x ; yA <= 1 - swap ; yA >= x - swap
                        model += yA[(w, p, k, a_t)] <= x[w][p][k]
                        model += yA[(w, p, k, a_t)] <= 1 - swap[w][p]
                        model += yA[(w, p, k, a_t)] >= x[w][p][k] - swap[w][p]
                        # yB
                        yB[(w, p, k, b_t)] = pl.LpVariable(f"yB_{w}_{p}_{k}_{b_t}", lowBound=0, upBound=1,
                                                           cat=pl.LpBinary)
                        # Constraints: yB <= x ; yB <= swap ; yB >= x + swap - 1
                        model += yB[(w, p, k, b_t)] <= x[w][p][k]
                        model += yB[(w, p, k, b_t)] <= swap[w][p]
                        model += yB[(w, p, k, b_t)] >= x[w][p][k] + swap[w][p] - 1

            # Sum to homeCnt
            for t in Teams:
                model += home_count[t] == pl.lpSum(
                    yA.get((w, p, k, t), 0) + yB.get((w, p, k, t), 0)
                    for w in Weeks for p in Periods for k in Ks
                )

            # -------- objective: minimize maxImb --------
            # max_imb >= |2*homeCnt[t] - W|
            for t in Teams:
                model += max_imb >= 2 * home_count[t] - W
                model += max_imb >= W - 2 * home_count[t]

            model += max_imb

        return model, pos, swap, x, A, B, Weeks, Periods, Ks, max_imb