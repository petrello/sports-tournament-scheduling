include "globals.mzn";

int: n;  % even
int: total_matches = n * (n - 1) div 2;
int: weeks = n - 1;
int: periods = n div 2;

set of int: MatchIndex = 1..total_matches;
set of int: Teams = 1..n;
set of int: Weeks = 1..weeks;
set of int: Periods = 1..periods;

% All unordered match pairs (known in advance)
array[MatchIndex] of int: TeamA = [i | i, j in Teams where i < j];
array[MatchIndex] of int: TeamB = [j | i, j in Teams where i < j];

% The only decision variable: which match goes in each slot
array[Periods, Weeks] of var MatchIndex: MatchAssigned;

% Each match used exactly once
constraint alldifferent([MatchAssigned[p,w] | p in Periods, w in Weeks]);

% No team plays more than once per week
constraint
  forall(t in Teams, w in Weeks) (
    sum(p in Periods)(
      bool2int(TeamA[MatchAssigned[p,w]] == t \/ TeamB[MatchAssigned[p,w]] == t)
    ) = 1
  );

% No team plays in the same period more than twice
constraint
  forall(t in Teams, p in Periods) (
    sum(w in Weeks)(
      bool2int(TeamA[MatchAssigned[p,w]] == t \/ TeamB[MatchAssigned[p,w]] == t)
    ) <= 2
  );

% Optional symmetry: fix first match
constraint MatchAssigned[1,1] = 1;

solve :: int_search(
  [MatchAssigned[p,w] | p in Periods, w in Weeks],
  first_fail, indomain_min, complete
) satisfy;

output [
  "[\n" ++
  concat([
    "  [" ++
    concat([
      "[" ++ show(TeamA[MatchAssigned[p,w]]) ++ " , " ++ show(TeamB[MatchAssigned[p,w]]) ++ "]" ++
      if w < weeks then " , " else "" endif
     | w in Weeks]) ++ "]" ++
    if p < periods then " ,\n" else "\n" endif
  | p in Periods]) ++ "]"
];
