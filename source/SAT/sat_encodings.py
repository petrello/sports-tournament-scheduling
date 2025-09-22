from typing import List
from z3 import And, Or, Not, Bool, BoolRef

def at_least_one(bs: List[BoolRef]) -> BoolRef:
    return Or(bs)

def at_most_one(bs: List[BoolRef]) -> List[BoolRef]:
    """Pairwise encoding."""
    return [
        Or(Not(bs[i]), Not(bs[j]))
        for i in range(len(bs))
        for j in range(i + 1, len(bs))
    ]

def exactly_one(bs: List[BoolRef]) -> BoolRef:
    return And(at_least_one(bs), *at_most_one(bs))

def at_most_k(bool_vars: List[BoolRef], k: int, name: str) -> List[BoolRef]:
    """Sequential encoding."""
    n = len(bool_vars)
    constraints: List[BoolRef] = []
    if n == 0:
        return constraints
    if k <= 0:
        constraints += [Not(v) for v in bool_vars]
        return constraints
    if k >= n:
        return constraints

    s = [[Bool(f"{name}_{i}_{j}") for j in range(k)] for i in range(n - 1)]

    constraints.append(Or(Not(bool_vars[0]), s[0][0]))
    for j in range(1, k):
        constraints.append(Not(s[0][j]))

    for i in range(1, n - 1):
        constraints.append(Or(Not(bool_vars[i]), s[i][0]))
        constraints.append(Or(Not(s[i-1][0]), s[i][0]))
        constraints.append(Or(Not(bool_vars[i]), Not(s[i-1][k-1])))
        for j in range(1, k):
            constraints.append(Or(Not(bool_vars[i]), Not(s[i-1][j-1]), s[i][j]))
            constraints.append(Or(Not(s[i-1][j]), s[i][j]))

    constraints.append(Or(Not(bool_vars[n-1]), Not(s[n-2][k-1])))

    return constraints

# ---------- One-hot comparators ----------
def equal_onehot(x: List[BoolRef], y: List[BoolRef]) -> BoolRef:
    """One-hot equality: element-wise equivalence (assume EO elsewhere)."""
    return And(*[xi == yi for xi, yi in zip(x, y)])

def less_onehot_strict(x: List[BoolRef], y: List[BoolRef]) -> BoolRef:
    """Strict compare for one-hots: index(x) < index(y)."""
    n = len(x)
    return Or(*[And(x[i], Or(*y[i+1:])) for i in range(n - 1)])

def lex_less_onehot_seq(X: List[List[BoolRef]], Y: List[List[BoolRef]]) -> BoolRef:
    """Strict lex on sequences of one-hots: X <_lex Y."""
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
