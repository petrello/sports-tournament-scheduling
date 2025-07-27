from typing import List

from z3 import z3, Bool, Or, Not, And


def at_least_one(bs: List[z3.BoolRef]) -> z3.BoolRef:
    """At least one variable is True."""
    return z3.Or(bs)

def at_most_one(bs: List[z3.BoolRef]) -> List[z3.BoolRef]:
    return [
        z3.Or(z3.Not(bs[i]), z3.Not(bs[j]))
        for i in range(len(bs))
        for j in range(i+1, len(bs))
    ]

def exactly_one(bs: list[z3.BoolRef]) -> z3.BoolRef:
    return z3.And([at_least_one(bs), *at_most_one(bs)])


def at_most_k(bool_vars, k):
    constraints = []
    n = len(bool_vars)
    s = [[Bool(f"s_{i}_{j}") for j in range(k)] for i in range(n - 1)]
    constraints.append(Or(Not(bool_vars[0]), s[0][0]))
    constraints += [Not(s[0][j]) for j in range(1, k)]

    for i in range(1, n - 1):
        constraints.append(Or(Not(bool_vars[i]), s[i][0]))
        constraints.append(Or(Not(s[i - 1][0]), s[i][0]))
        constraints.append(Or(Not(bool_vars[i]), Not(s[i - 1][k - 1])))
        for j in range(1, k):
            constraints.append(Or(Not(bool_vars[i]), Not(s[i - 1][j - 1]), s[i][j]))
            constraints.append(Or(Not(s[i - 1][j]), s[i][j]))

    constraints.append(Or(Not(bool_vars[n - 1]), Not(s[n - 2][k - 1])))

    return And(constraints)

def equiv(a: z3.BoolRef, b: z3.BoolRef) -> z3.BoolRef:
    """Bi-implication."""
    return z3.And(z3.Implies(a,b), z3.Implies(b,a))

def less_or_equal_onehot(a: List[z3.BoolRef], b: List[z3.BoolRef]) -> z3.BoolRef:
    # a <= b in index order for one-hot vectors
    # For each i: a_i -> OR_{j>=i} b_j
    return z3.And(*[
        z3.Implies(a_i, z3.Or(*b[i:])) for i, a_i in enumerate(a)
    ])