include "globals.mzn";

%====================================================================
% INSTANCE PARAMETER
%====================================================================
int: n;                                    % even number of teams (set in .dzn)
constraint n mod 2 = 0 /\ n >= 2;          % basic sanity check

%====================================================================
%  VARIABLES & DOMAINS
%====================================================================
int: weeks   = n - 1;                      % number of weeks
int: periods = n div 2;                    % rows (periods) per week

set of int: Teams   = 1..n;
set of int: Weeks   = 1..weeks;
set of int: Periods = 1..periods;

%====================================================================
% PRECOMPUTED DATA
%====================================================================
/* Circle method pairs (raw), then canonicalize each match so that
   Home = max(team1, team2), Away = min(team1, team2).       */

array[Periods, Weeks] of int: Home_raw =
  array2d(Periods, Weeks,
    [ if p = 1 then n
      else ((w-1) + (p-1)) mod (n-1) + 1
      endif
    | p in Periods, w in Weeks ]);

array[Periods, Weeks] of int: Away_raw =
  array2d(Periods, Weeks,
    [ if p = 1 then w
      else ((n-1) - (p-1) + (w-1)) mod (n-1) + 1
      endif
    | p in Periods, w in Weeks ]);

array[Periods, Weeks] of int: Home =          % home team
  array2d(Periods, Weeks,
    [ max(Home_raw[p,w], Away_raw[p,w]) | p in Periods, w in Weeks ]);

array[Periods, Weeks] of int: Away =          % away team
  array2d(Periods, Weeks,
    [ min(Home_raw[p,w], Away_raw[p,w]) | p in Periods, w in Weeks ]);

%====================================================================
% DECISION VARIABLES
%====================================================================
% pos[p,w] = which match occupies row p in week w
array[Periods, Weeks] of var Periods: pos;

%====================================================================
% CONSTRAINTS
%====================================================================

%--- Main constraint: each week uses a match exactly once
constraint
  forall(w in Weeks)(
    alldifferent([ pos[p,w] | p in Periods ])
  );

%--- Main constraint: each team plays in the same period at most twice
constraint
  forall(p in Periods)(
    let {
      array[1..2*weeks] of var Teams: rowVars =
           [ Home[pos[p,w], w] | w in Weeks ] ++
           [ Away[pos[p,w], w] | w in Weeks ],
      array[Teams] of int: cover = [ t | t in Teams ],
      array[Teams] of int: low   = [ 0 | _ in Teams ],
      array[Teams] of int: up   = [ 2 | _ in Teams ]
    } in
      global_cardinality_low_up(rowVars, cover, low, up)
  );

%====================================================================
% SEARCH STRATEGY
%====================================================================
solve :: int_search([ pos[p,w] | p in Periods, w in Weeks ],
                    first_fail, indomain_min, complete)
       satisfy;

%====================================================================
% OUTPUT
%====================================================================
function string: pair(int: p, int: w) =
  "[" ++ show(Home[pos[p,w], w]) ++ " , " ++ show(Away[pos[p,w], w]) ++ "]";

output [
  "[\n" ++
  concat([
    "  [" ++
      concat([ pair(p,w) ++ (if w < weeks then " , " else "" endif)
      | w in Weeks ]) ++ "]" ++
    (if p < periods then " ,\n" else "\n" endif)
  | p in Periods ]) ++ "]"
];
