from typing import Tuple, Dict
import pulp as pl

def circle_pairs(n: int):
    """Return A[w][k], B[w][k] (0-based lists) per the circle method."""
    W, P = n - 1, n // 2
    A = [[0] * P for _ in range(W)]
    B = [[0] * P for _ in range(W)]
    for w in range(1, W + 1):
        for p in range(1, P + 1):
            a_raw = n if p == 1 else ((w - 1) + (p - 1)) % (n - 1) + 1
            b_raw = w if p == 1 else ((n - 1) - (p - 1) + (w - 1)) % (n - 1) + 1
            # canonical ordering: higher-numbered team in HomeTeams, lower in AwayTeams
            A[w - 1][p - 1] = max(a_raw, b_raw)
            B[w - 1][p - 1] = min(a_raw, b_raw)
    return A, B

class MIPModelRR:
    @staticmethod
    def build_model(n: int, use_symmetry_breaking_constraints: bool, optimize: bool):
        assert n % 2 == 0 and n >= 2, "n must be even and ≥2"

        # ====================================================================
        #  VARIABLES & DOMAINS
        # ====================================================================
        W = n - 1
        P = n // 2

        Teams = list(range(1, n + 1))
        Weeks = list(range(1, W + 1))
        Periods = list(range(1, P + 1))
        Ks = range(1, P + 1)  # match indices

        Home, Away = circle_pairs(n)

        # ====================================================================
        #  PROBLEM DEFINITION
        # ====================================================================
        name = "MIP_RR_OPT" if optimize else "MIP_RR"
        model = pl.LpProblem(name, pl.LpMinimize)

        # ====================================================================
        # DECISION VARIABLES
        # ====================================================================
        # pos[(w,p,k)] : 1 if match k is scheduled in week w, period p
        pos = {
            (w, p, k): pl.LpVariable(f"pos_{w}_{p}_{k}", lowBound=0, upBound=1, cat=pl.LpBinary)
            for w in Weeks for p in Periods for k in Ks
        }

        # swap[(w,p)] : 1 if home/away teams are swapped in slot (w,p) [opt. only]
        swap = {
            (w, p): pl.LpVariable(f"swap_{w}_{p}", lowBound=0, upBound=1, cat=pl.LpBinary)
            for w in Weeks for p in Periods
        } if optimize else None

        # ====================================================================
        # OPTIMIZATION VARIABLES
        # ====================================================================
        if optimize:
            home_count = {
                t: pl.LpVariable(f"home_cnt_{t}", lowBound=0, upBound=W, cat=pl.LpInteger)
                for t in Teams
            }
            max_imb = pl.LpVariable("max_imb", lowBound=0, upBound=W, cat=pl.LpInteger)
        else:
            home_count, max_imb = None, None
            model += 0  # feasibility problem, no objective function


        # ====================================================================
        # CONSTRAINTS
        # ====================================================================

        # --- Main constraint: exactly one match index per slot
        for w in Weeks:
            for p in Periods:
                model += pl.lpSum(pos[(w, p, k)] for k in Ks) == 1, f"slot_unique_w{w}_p{p}"

        # --- Main constraint: per-week permutation of match indices
        for w in Weeks:
            for k in Ks:
                model += pl.lpSum(pos[(w, p, k)] for p in Periods) == 1, f"perm_w{w}_k{k}"

        #--- Main constraint: each team appears in the same period at most twice
        for p in Periods:
            for t in Teams:
                expr = []
                for w in Weeks:
                    for k in Ks:
                        if Home[w - 1][k - 1] == t or Away[w - 1][k - 1] == t:
                            expr.append(pos[(w, p, k)])
                if expr: model += pl.lpSum(expr) <= 2, f"period_cap_t{t}_p{p}"
                else: pass

        if use_symmetry_breaking_constraints:
            #--- Symmetry breaking: fix week 1 to identity permutation
            for p in Periods:
                # enforce pos[1,p,p] == 1 and pos[1,p,k!=p] == 0
                for k in Ks:
                    if k == p:
                        model += pos[(1, p, k)] == 1, f"week1_fix_pos_1_{p}_{k}"
                    else:
                        model += pos[(1, p, k)] == 0, f"week1_fix_pos_1_{p}_{k}"
                if optimize:
                    model += swap[(1, p)] == 0, f"week1_fix_swap_p{p}"

            # # Build integer expressions lHome[w,p] and lAway[w,p] as linear combinations
            # lHome = {
            #     (w, p): pl.lpSum(Home[w - 1][k - 1] * pos[(w, p, k)] for k in Ks)
            #     for w in Weeks for p in Periods
            # }
            # lAway = {
            #     (w, p): pl.lpSum(Away[w - 1][k - 1] * pos[(w, p, k)] for k in Ks)
            #     for w in Weeks for p in Periods
            # }

            # M = n  # big-M (safe upper bound for differences in team ids)
            #
            # #--- Symmetry breaking: strict lex between periods (rows)
            # for p_idx in range(1, P):
            #     Xp = [lAway[(w, p_idx)] for w in Weeks] + [lHome[(w, p_idx)] for w in Weeks]
            #     Yp = [lAway[(w, p_idx + 1)] for w in Weeks] + [lHome[(w, p_idx + 1)] for w in Weeks]
            #
            #     L = len(Xp)
            #     diff_vars = [pl.LpVariable(f"lexdiff_period{p_idx}_pos{k}", cat=pl.LpBinary) for k in range(L)]
            #     model += pl.lpSum(diff_vars) == 1, f"lex_period_decision_p{p_idx}"
            #
            #     for k in range(L):
            #         for j in range(k):
            #             model += Xp[j] - Yp[j] <= M * (1 - diff_vars[k]), f"lex_eq1_p{p_idx}_k{k}_j{j}"
            #             model += Yp[j] - Xp[j] <= M * (1 - diff_vars[k]), f"lex_eq2_p{p_idx}_k{k}_j{j}"
            #         model += Xp[k] - Yp[k] <= -1 + M * (1 - diff_vars[k]), f"lex_less_p{p_idx}_k{k}"
            #
            # #--- Symmetry breaking: strict lex between weeks (columns)
            # for w_idx in range(1, W):
            #     Xw = [lAway[(w_idx, p)] for p in Periods] + [lHome[(w_idx, p)] for p in Periods]
            #     Yw = [lAway[(w_idx + 1, p)] for p in Periods] + [lHome[(w_idx + 1, p)] for p in Periods]
            #
            #     L = len(Xw)
            #     diff_vars = [pl.LpVariable(f"lexdiff_week{w_idx}_pos{k}", cat=pl.LpBinary) for k in range(L)]
            #     model += pl.lpSum(diff_vars) == 1, f"lex_week_decision_w{w_idx}"
            #
            #     for k in range(L):
            #         for j in range(k):
            #             model += Xw[j] - Yw[j] <= M * (1 - diff_vars[k]), f"lex_eq1_w{w_idx}_k{k}_j{j}"
            #             model += Yw[j] - Xw[j] <= M * (1 - diff_vars[k]), f"lex_eq2_w{w_idx}_k{k}_j{j}"
            #         model += Xw[k] - Yw[k] <= -1 + M * (1 - diff_vars[k]), f"lex_less_w{w_idx}_k{k}"


        # ====================================================================
        # OPTIMIZATION
        # ====================================================================
        if optimize:
            # create binary auxiliaries yA[(w,p,k)] and yB[(w,p,k)]
            yHome = {}
            yAway = {}

            for w in Weeks:
                for p in Periods:
                    for k in Ks:
                        yHome[(w, p, k)] = pl.LpVariable(f"yHome_{w}_{p}_{k}", lowBound=0, upBound=1, cat=pl.LpBinary)
                        model += yHome[(w, p, k)] <= pos[(w, p, k)], f"yHome_le_pos_w{w}_p{p}_k{k}"
                        model += yHome[(w, p, k)] <= 1 - swap[(w, p)], f"yHome_le_notswap_w{w}_p{p}_k{k}"
                        model += yHome[(w, p, k)] >= pos[(w, p, k)] - swap[(w, p)], f"yHome_ge_pos_minus_swap_w{w}_p{p}_k{k}"

                        yAway[(w, p, k)] = pl.LpVariable(f"yAway_{w}_{p}_{k}", lowBound=0, upBound=1, cat=pl.LpBinary)
                        model += yAway[(w, p, k)] <= pos[(w, p, k)], f"yAway_le_pos_w{w}_p{p}_k{k}"
                        model += yAway[(w, p, k)] <= swap[(w, p)], f"yAway_le_swap_w{w}_p{p}_k{k}"
                        model += yAway[(w, p, k)] >= pos[(w, p, k)] + swap[(w, p)] - 1, f"yAway_ge_pos_plus_swap_minus1_w{w}_p{p}_k{k}"

            # Sum to home_count[t]
            for t in Teams:
                terms = []
                for w in Weeks:
                    for p in Periods:
                        for k in Ks:
                            if Home[w - 1][k - 1] == t:
                                terms.append(yHome[(w, p, k)])
                            if Away[w - 1][k - 1] == t:
                                terms.append(yAway[(w, p, k)])
                if terms:
                    model += home_count[t] == pl.lpSum(terms), f"home_cnt_def_t{t}"
                else:
                    model += home_count[t] == 0, f"home_cnt_zero_t{t}"

            # max_imb constraints and objective
            for t in Teams:
                model += max_imb >= 2 * home_count[t] - W, f"max_imb_ge_pos_t{t}"
                model += max_imb >= W - 2 * home_count[t], f"max_imb_ge_neg_t{t}"

            model += max_imb, "Minimize_maxImbalance"

        return model, pos, swap, Home, Away