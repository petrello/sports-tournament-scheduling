from typing import List

from z3 import z3


def exactly_one(bs: List[z3.BoolRef]) -> z3.BoolRef:
    """Exactly one variable is True."""
    return z3.And(z3.Or(bs), z3.AtMost(*bs, 1))

def at_most_k(bs: List[z3.BoolRef], k: int) -> z3.BoolRef:
    """At most k Booleans are True."""
    return z3.AtMost(*bs, k)

def equiv(a: z3.BoolRef, b: z3.BoolRef) -> z3.BoolRef:
    """Bi-implication."""
    return z3.And(z3.Implies(a,b), z3.Implies(b,a))

def less_or_equal_onehot(a: List[z3.BoolRef], b: List[z3.BoolRef]) -> z3.BoolRef:
    # a <= b in index order for one-hot vectors
    # For each i: a_i -> OR_{j>=i} b_j
    return z3.And(*[
        z3.Implies(a_i, z3.Or(*b[i:])) for i, a_i in enumerate(a)
    ])