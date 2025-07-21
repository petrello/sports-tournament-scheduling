include "globals.mzn";

int: n;                    % even
int: total_matches = n*(n-1) div 2;
int: weeks   = n - 1;
int: periods = n div 2;

set of int: Teams   = 1..n;
set of int: Weeks   = 1..weeks;
set of int: Periods = 1..periods;

array[Periods,Weeks] of var Teams: Home;
array[Periods,Weeks] of var Teams: Away;

% 1) each match is an unordered pair: Home<p,w> < Away<p,w>
constraint
  forall(p in Periods, w in Weeks)(
    Home[p,w] < Away[p,w]
  );


% 2) every possible unordered pair occurs exactly once:
%    linearize (i,j) to an integer (i-1)*n + j, then all-different
constraint
  alldifferent([
    Home[p,w] * n + Away[p,w]
  | p in Periods, w in Weeks]);

% 3) each team plays exactly once per week
/*constraint
  forall(t in Teams, w in Weeks)(
    sum(p in Periods)(
      bool2int(Home[p,w] = t \/ Away[p,w] = t)
    ) = 1
  );

% 4) each team plays in the same period at most twice
constraint
  forall(t in Teams, p in Periods)(
    sum(w in Weeks)(
      bool2int(Home[p,w] = t \/ Away[p,w] = t)
    ) <= 2
  );*/
constraint
  forall(w in Weeks)(
    all_different(
      [ Home[p,w] | p in Periods ]
    ++[ Away[p,w] | p in Periods ]
    )
  );


% 4) each team plays in the same period at most twice:
constraint
  forall(p in Periods)(
    global_cardinality_low_up(
      % collect all “slots” in period p:
      [ Home[p,w] | w in Weeks ]
    ++[ Away[p,w] | w in Weeks ],
      % the values to count
      [ t | t in Teams ],
      % lower = 0
      [ 0 | t in Teams ],
      % upper = 2
      [ 2 | t in Teams ]
    )
  );

% 5) symmetry‐break week 1 to (1,2),(3,4),…,(n−1,n)
constraint
  forall(p in Periods)(
    Home[p,1] = 2*p-1 /\ Away[p,1] = 2*p
  );

% 6) lexicographic order on the first row of Home to break further symmetry:
constraint
  increasing(
    [ Home[1,w] | w in Weeks ]
  );

% Search Strategy
%-----------------------------------------------------------------------------%
solve 
  :: int_search([Home[p,w] | p in Periods, w in Weeks], dom_w_deg, indomain_random)
  :: restart_luby(100)
satisfy;

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
