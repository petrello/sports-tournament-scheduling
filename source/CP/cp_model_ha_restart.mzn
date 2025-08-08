include "globals.mzn";

%====================================================================
% INSTANCE PARAMETER
%====================================================================
int: n;                                    % even number of teams (set in .dzn)
constraint n mod 2 = 0 /\ n >= 2;          % basic sanity check

%====================================================================
%  VARIABLES & DOMAINS
%====================================================================
int: total_matches = n*(n-1) div 2;
int: weeks   = n - 1;
int: periods = n div 2;

set of int: Teams   = 1..n;
set of int: Weeks   = 1..weeks;
set of int: Periods = 1..periods;

%====================================================================
% DECISION VARIABLES
%====================================================================
array[Periods,Weeks] of var Teams: Home;
array[Periods,Weeks] of var Teams: Away;

%====================================================================
% CONSTRAINTS
%====================================================================

%--- Main constraint: encode each unordered match pair 
%    in canonical form (Home < Away). 
%    It acts also as symmetry breaking constraint.
constraint
  forall(p in Periods, w in Weeks)(
    Home[p,w] < Away[p,w]
  );

%--- Main constraint: every unordered pair occurs exactly once
%    linearize (i,j) to integer (i-1)*n + j, then all-different
constraint
  alldifferent([
    Home[p,w] * n + Away[p,w]
  | p in Periods, w in Weeks]);

%--- Main constraint: each team plays exactly once per week
constraint
  forall(w in Weeks)(
    all_different(
      [ Home[p,w] | p in Periods ]
    ++[ Away[p,w] | p in Periods ]
    )
  );

%--- Main constraint: each team plays in the same period at most twice
constraint
  forall(p in Periods)(
    global_cardinality_low_up(
      [ Home[p,w] | w in Weeks ]
    ++[ Away[p,w] | w in Weeks ],
      [ t | t in Teams ],
      [ 0 | t in Teams ],
      [ 2 | t in Teams ]
    )
  );

%--- Symmetry breaking: fix week 1 to (1,2), (3,4), …, (n−1,n)
constraint
  forall(p in Periods)(
    Home[p,1] = 2*p-1 /\ Away[p,1] = 2*p
  );

%--- Symmetry breaking: lexicographic order on first row of Home by week
constraint
  lex_lesseq(
    [ Home[1, w]   | w in 1..weeks-1 ],
    [ Home[1, w+1] | w in 1..weeks-1 ]
  );

%--- Symmetry breaking: lexicographic order between periods
constraint 
  forall(p in 1..periods-1)(
    lex_less(
      [ Home[p,w] | w in Weeks ] ++ [ Away[p,w] | w in Weeks ],
      [ Home[p+1, w] | w in Weeks ] ++ [ Away[p+1, w] | w in Weeks ]
    )
  );

%--- Symmetry breaking: lexicographic order between weeks
constraint
  forall(w in 1..weeks-1)(
    lex_less(
      [ Home[p,w] | p in Periods ] ++ [ Away[p,w] | p in Periods ],
      [ Home[p,w+1] | p in Periods ] ++ [ Away[p,w+1] | p in Periods ]
    )
  );

%====================================================================
% SEARCH STRATEGY
%====================================================================
solve 
  :: int_search([Home[p,w] | p in Periods, w in Weeks], first_fail, indomain_random)
  :: restart_luby(100)
satisfy;

%====================================================================
% OUTPUT
%====================================================================
output [
  "[\n" ++
  concat([
    "  [" ++
      concat([
        "[" ++ show(Home[p,w]) ++ " , " ++ show(Away[p,w]) ++ "]"
        ++ if w<weeks then " , " else "" endif
      | w in Weeks]) ++ "]"
    ++ if p<periods then " ,\n" else "\n" endif
  | p in Periods]) ++
  "]\n"
];
