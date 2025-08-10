from typing import List
from z3 import And, Or, Not, Bool, BoolRef

# ====================================================================
# Pure SAT helpers (Boolean-only; easy to CNF via Tseitin)
# ====================================================================

def at_least_one(bs: List[BoolRef]) -> BoolRef:
    """ALO: at least one var is True → OR(vars)."""
    return Or(bs)

def at_most_one(bs: List[BoolRef]) -> List[BoolRef]:
    """Pairwise AMO: for all i<j, ¬(b_i ∧ b_j) → (¬b_i ∨ ¬b_j)."""
    return [
        Or(Not(bs[i]), Not(bs[j]))
        for i in range(len(bs))
        for j in range(i + 1, len(bs))
    ]

def exactly_one(bs: List[BoolRef]) -> BoolRef:
    """EO: exactly one True = ALO ∧ AMO."""
    return And(at_least_one(bs), *at_most_one(bs))

def at_most_k(bool_vars: List[BoolRef], k: int, name: str) -> List[BoolRef]:
    """
    AMK via sequential counter.
    Creates aux s[i][j] meaning: among first i+1 vars, count ≥ j+1.
    Returns a flat list of clauses; add with solver.add(*clauses).
    """
    n = len(bool_vars)
    constraints: List[BoolRef] = []
    if n == 0:
        return constraints
    if k <= 0:
        # sum ≤ 0 → all false
        constraints += [Not(v) for v in bool_vars]
        return constraints
    if k >= n:
        # sum ≤ n → no constraint needed
        return constraints

    # s[i][j] := (first i+1 vars contain at least j+1 Trues), i=0..n-2, j=0..k-1
    s = [[Bool(f"{name}_{i}_{j}") for j in range(k)] for i in range(n - 1)]

    # base for i=0
    constraints.append(Or(Not(bool_vars[0]), s[0][0]))  # b0 → s00
    for j in range(1, k):
        constraints.append(Not(s[0][j]))                # cannot have ≥2 at i=0

    # transitions for i=1..n-2
    for i in range(1, n - 1):
        constraints.append(Or(Not(bool_vars[i]), s[i][0]))      # bi → si0
        constraints.append(Or(Not(s[i-1][0]), s[i][0]))         # si-1,0 → si0
        constraints.append(Or(Not(bool_vars[i]), Not(s[i-1][k-1])))  # block overflow
        for j in range(1, k):
            # si,j becomes true if (bi ∧ si-1,j-1) or si-1,j
            constraints.append(Or(Not(bool_vars[i]), Not(s[i-1][j-1]), s[i][j]))
            constraints.append(Or(Not(s[i-1][j]), s[i][j]))

    # final guard on last var: bn-1 → ¬s[n-2][k-1]
    constraints.append(Or(Not(bool_vars[n-1]), Not(s[n-2][k-1])))

    return constraints

# ---------- One-hot comparators ----------
def equal_onehot(x: List[BoolRef], y: List[BoolRef]) -> BoolRef:
    """One-hot equality: element-wise equivalence (assume EO elsewhere)."""
    return And(*[xi == yi for xi, yi in zip(x, y)])

def less_onehot_strict(x: List[BoolRef], y: List[BoolRef]) -> BoolRef:
    """
    Strict compare for one-hots: index(x) < index(y).
    Encodes ⋁_i ( x_i ∧ ⋁_{j>i} y_j ).
    """
    n = len(x)
    return Or(*[And(x[i], Or(*y[i+1:])) for i in range(n - 1)])

def lex_less_onehot_seq(X: List[List[BoolRef]], Y: List[List[BoolRef]]) -> BoolRef:
    """
    Strict lex on sequences of one-hots: X <_lex Y.
    Encodes ⋁_k ( prefix_eq(0..k-1) ∧ (X[k] < Y[k]) ).
    """
    terms = []
    for k in range(len(X)):
        prefix_eq = And(*[equal_onehot(X[i], Y[i]) for i in range(k)])
        terms.append(And(prefix_eq, less_onehot_strict(X[k], Y[k])))
    return Or(*terms)

# ---------- Derived one-hots from RR pos + match table ----------
def team_onehot_from_pos(
    table: List[List[int]],
    pos: List[List[List[BoolRef]]],
    w: int,
    p: int,
    n: int,
    P: int,
) -> List[BoolRef]:
    """
    Team identity at slot (w,p) given pos[w][p] (one-hot over k) and a table (Home/Away).
    For each team t, returns OR_k: (pos[w][p][k] ∧ table[w][k]==t).
    Produces a length-n one-hot vector over teams (pure Bool).
    """
    return [
        Or(*[pos[w][p][k] for k in range(P) if table[w][k] == t])
        for t in range(1, n + 1)
    ]
