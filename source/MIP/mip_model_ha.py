import pulp as pl
from itertools import combinations

class MIPModelHA:
    @staticmethod
    def build_model(n: int, use_symmetry_breaking_constraints: bool, name="BalancedSchedule_HomeAway"):
        assert n % 2 == 0 and n >= 2, "n must be even and ≥ 2"

        weeks   = n - 1
        periods = n // 2

        Teams   = range(1, n + 1)
        Weeks   = range(1, weeks + 1)
        Periods = range(1, periods + 1)

        # unordered pairs i<j
        Pairs = [(i, j) for i, j in combinations(Teams, 2)]

        # Binary assignment: pair -> slot
        y = pl.LpVariable.dicts(
            "y",
            (Pairs, Weeks, Periods),
            lowBound=0, upBound=1, cat=pl.LpBinary
        )

        # Explicit integer vars for Home/Away in each slot
        Home = pl.LpVariable.dicts(
            "Home", (Periods, Weeks), lowBound=1, upBound=n, cat=pl.LpInteger
        )
        Away = pl.LpVariable.dicts(
            "Away", (Periods, Weeks), lowBound=1, upBound=n, cat=pl.LpInteger
        )

        # optional lex helper
        if use_symmetry_breaking_constraints:
            H1 = pl.LpVariable.dicts("H1", Weeks, lowBound=1, upBound=n, cat=pl.LpInteger)

        model = pl.LpProblem(name, pl.LpMinimize)
        model += 0  # feasibility

        # (slot) exactly one pair per (w,p)
        for w in Weeks:
            for p in Periods:
                model += pl.lpSum(y[(i, j)][w][p] for (i, j) in Pairs) == 1

        # (2) each pair once overall
        for (i, j) in Pairs:
            model += pl.lpSum(y[(i, j)][w][p] for w in Weeks for p in Periods) == 1

        # Link Home/Away to y (linear, no big-M)
        for w in Weeks:
            for p in Periods:
                model += Home[p][w] == pl.lpSum(i * y[(i, j)][w][p] for (i, j) in Pairs)
                model += Away[p][w] == pl.lpSum(j * y[(i, j)][w][p] for (i, j) in Pairs)
                if use_symmetry_breaking_constraints:
                    # (1) explicit Home < Away
                    model += Home[p][w] + 1 <= Away[p][w]

        # (3) team plays exactly once per week
        for t in Teams:
            for w in Weeks:
                model += pl.lpSum(
                    y[(i, j)][w][p]
                    for p in Periods
                    for (i, j) in Pairs
                    if t in (i, j)
                ) == 1

        # (4) team plays in same period at most twice
        for t in Teams:
            for p in Periods:
                model += pl.lpSum(
                    y[(i, j)][w][p]
                    for w in Weeks
                    for (i, j) in Pairs
                    if t in (i, j)
                ) <= 2
        if use_symmetry_breaking_constraints:
            # (5) symmetry: fix week 1 = (1,2),(3,4),...
            for p in Periods:
                i, j = 2*p - 1, 2*p
                model += y[(i, j)][1][p] == 1
                # No need to force the others to 0: slot constraint already does it.

            # (6) optional lex breaker on first period (p=1) Home row
            for w in Weeks:
                model += H1[w] == Home[1][w]   # period index 1
            for w in Weeks:
                if w < weeks:
                    model += H1[w] <= H1[w + 1]

        return model, Home, Away, y, Teams, Weeks, Periods, Pairs