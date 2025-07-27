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


def at_most_k(bool_vars: List[bool], k: int, name: str) -> List:
    """
    Generates CNF clauses for an 'At-Most-K' constraint using the
    correct and efficient sequential counter method provided by the user.

    This encoding is fully compatible with DIMACS conversion.

    Args:
        bool_vars: A list of Z3 boolean variables.
        k: The maximum number of variables that can be true.
        name: A prefix for the names of the auxiliary variables.

    Returns:
        A list of Z3 clauses that can be added to a solver.
    """
    n = len(bool_vars)
    constraints = []

    # s[i][j] is an auxiliary variable meaning "at least j+1 of the first i+1
    # variables (bool_vars[0]...bool_vars[i]) are True".
    # The matrix size is (n-1) x k because the state is only needed up to the
    # second-to-last variable to constrain the final one.
    s = [[Bool(f"{name}_{i}_{j}") for j in range(k)] for i in range(n - 1)]

    # --- Base Case for the first variable (i=0) ---
    # If bool_vars[0] is true, then s[0][0] (count >= 1) must be true.
    # Clause: Not(bool_vars[0]) Or s[0][0]
    constraints.append(Or(Not(bool_vars[0]), s[0][0]))

    # The count for the first variable can't be 2 or more.
    # Clause: Not(s[0][j]) for j from 1 to k-1
    for j in range(1, k):
        constraints.append(Not(s[0][j]))

    # --- Recursive step for variables i = 1 to n-2 ---
    for i in range(1, n - 1):
        # The count is >= 1 if the previous count was >= 1 OR the current var is true.
        # (Not(bool_vars[i]) Or s[i][0]) AND (Not(s[i-1][0]) Or s[i][0])
        constraints.append(Or(Not(bool_vars[i]), s[i][0]))
        constraints.append(Or(Not(s[i-1][0]), s[i][0]))

        # If the count of the first `i` variables is already `k`, then `bool_vars[i]` must be false.
        # Clause: Not(bool_vars[i]) Or Not(s[i-1][k-1])
        constraints.append(Or(Not(bool_vars[i]), Not(s[i-1][k-1])))

        # The count is >= j+1 if (the previous count was >= j+1) OR (the current var is true AND the previous count was >= j)
        for j in range(1, k):
            constraints.append(Or(Not(bool_vars[i]), Not(s[i-1][j-1]), s[i][j]))
            constraints.append(Or(Not(s[i-1][j]), s[i][j]))

    # --- Final constraint for the last variable (n-1) ---
    # If the count of the first `n-1` variables is already `k`, then the last variable `bool_vars[n-1]` must be false.
    constraints.append(Or(Not(bool_vars[n-1]), Not(s[n-2][k-1])))

    # For adding to a Z3 solver, a list of individual clauses is standard and often more flexible.
    return constraints

def equiv(a: z3.BoolRef, b: z3.BoolRef) -> z3.BoolRef:
    """Bi-implication."""
    return z3.And(z3.Implies(a,b), z3.Implies(b,a))

def less_or_equal_onehot(a: List[z3.BoolRef], b: List[z3.BoolRef]) -> z3.BoolRef:
    # a <= b in index order for one-hot vectors
    # For each i: a_i -> OR_{j>=i} b_j
    return z3.And(*[
        z3.Implies(a_i, z3.Or(*b[i:])) for i, a_i in enumerate(a)
    ])