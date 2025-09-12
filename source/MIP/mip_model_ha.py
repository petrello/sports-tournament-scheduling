import pulp as pl
from itertools import combinations

class MIPModelHA:
    @staticmethod
    def build_model(n: int, use_symmetry_breaking_constraints: bool):
        assert n % 2 == 0 and n >= 2, "n must be even and ≥2"


        #====================================================================
        #  VARIABLES & DOMAINS
        #====================================================================
        W = n - 1
        P = n // 2

        Teams = list(range(1, n + 1))
        Weeks = list(range(1, W + 1))
        Periods = list(range(1, P + 1))

        # Generate pairs based on symmetry breaking setting
        if use_symmetry_breaking_constraints:
            # Only canonical pairs (i,j) where i < j
            Pairs = [(i, j) for i, j in combinations(Teams, 2)]
        else:
            # All ordered pairs except (i,i): both (i,j) and (j,i) where i != j
            Pairs = [(i, j) for i in Teams for j in Teams if i != j]

        # integer Home/Away per (p,w)
        Home = {
            (p, w): pl.LpVariable(f"Home_{p}_{w}", lowBound=1, upBound=n, cat=pl.LpInteger)
            for p in Periods for w in Weeks
        }
        Away = {
            (p, w): pl.LpVariable(f"Away_{p}_{w}", lowBound=1, upBound=n, cat=pl.LpInteger)
            for p in Periods for w in Weeks
        }


        # ====================================================================
        #  PROBLEM DEFINITION
        # ====================================================================
        model = pl.LpProblem("MIP_HA", pl.LpMinimize)
        model += 0  # feasibility problem, no objective function


        # ====================================================================
        # DECISION VARIABLES
        # ====================================================================
        # binary assignment y[(i,j,w,p)] = 1 iff pair (i,j) assigned to week w, period p
        y = {
            (i, j, w, p): pl.LpVariable(f"y_{i}_{j}_w{w}_p{p}", lowBound=0, upBound=1, cat=pl.LpBinary)
            for (i, j) in Pairs for w in Weeks for p in Periods
        }

        # %--- Main constraint: every unordered pair occurs exactly once
        # %    linearize (i,j) to integer (i-1)*n + j, then all-different
        for w in Weeks:
            for p in Periods:
                model += Home[(p, w)] == pl.lpSum(i * y[(i, j, w, p)] for (i, j) in Pairs), f"link_H_p{p}_w{w}"
                model += Away[(p, w)] == pl.lpSum(j * y[(i, j, w, p)] for (i, j) in Pairs), f"link_A_p{p}_w{w}"



        #====================================================================
        # CONSTRAINTS
        #====================================================================

        #--- Main constraint: exactly one match per slot
        for w in Weeks:
            for p in Periods:
                model += pl.lpSum(y[(i, j, w, p)] for (i, j) in Pairs) == 1, f"slot_unique_w{w}_p{p}"

        #--- Main constraint: every unordered pair {i,j} occurs exactly once
        if use_symmetry_breaking_constraints:
            for (i, j) in Pairs:
                model += pl.lpSum(y[(i, j, w, p)] for w in Weeks for p in Periods) == 1, f"pair_once_{i}_{j}"
        else:
            for i in range(1, n + 1):
                for j in range(i + 1, n + 1):  # Ensure i < j to avoid duplicates
                    model += (pl.lpSum(y[(i, j, w, p)] for w in Weeks for p in Periods) +
                              pl.lpSum(y[(j, i, w, p)] for w in Weeks for p in Periods) == 1,
                              f"pair_once_{i}_{j}")

        # --- Main constraint: each team plays exactly once per week
        for t in Teams:
            for w in Weeks:
                model += (pl.lpSum(y[(i, j, w, p)]
                                   for p in Periods for (i, j) in Pairs
                                   if t in (i, j)) == 1,
                          f"one_game_per_week_t{t}_w{w}")

        #--- Main constraint: each team appears in the same period at most twice
        for t in Teams:
            for p in Periods:
                model += (pl.lpSum(y[(i, j, w, p)]
                                   for w in Weeks for (i, j) in Pairs
                                   if t in (i, j)) <= 2,
                          f"period_cap_t{t}_p{p}")


        if use_symmetry_breaking_constraints:
            # --- Symmetry breaking: canonical orientation (home < away)
            for w in Weeks:
                for p in Periods:
                    # enforce a canonical orientation (home < away)
                    model += Home[(p, w)] + 1 <= Away[(p, w)], f"home_lt_away_p{p}_w{w}"


            # --- Symmetry breaking: fix week 1 to (1,2), (3,4), …, (n-1,n)
            for p in Periods:
                model += y[(2 * p - 1, 2 * p, 1, p)] == 1, f"fix_week1_pair_p{p}"

        return model, Home, Away
