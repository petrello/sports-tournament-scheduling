include "globals.mzn";

%====================================================================
% 0)  INSTANCE PARAMETER
%====================================================================
int: n;                                    % even number of teams (set in .dzn)
constraint n mod 2 = 0 /\ n >= 2;          % basic sanity check

%====================================================================
% 1)  DOMAINS & PRE-COMPUTED DATA
%====================================================================
int: W = n - 1;                            % weeks
int: P = n div 2;                          % periods (rows) per week

set of int: Teams   = 1..n;
set of int: Weeks   = 1..W;
set of int: Periods = 1..P;

/* Circle-method pairs… first build them raw, then reorder so that
   the “home” team (A) is always the *larger* number → breaks the
   mirror symmetry of swapping home/away.                                   */
array[Weeks, Periods] of int: a_raw =
  array2d(Weeks, Periods,
    [ if p = 1 then n
      else ((w-1) + (p-1)) mod (n-1) + 1
      endif
    | w in Weeks, p in Periods ]);

array[Weeks, Periods] of int: b_raw =
  array2d(Weeks, Periods,
    [ if p = 1 then w
      else ((n-1) - (p-1) + (w-1)) mod (n-1) + 1
      endif
    | w in Weeks, p in Periods ]);

array[Weeks, Periods] of int: A =      % home team (larger value)
  array2d(Weeks, Periods,
    [ max(a_raw[w,p], b_raw[w,p]) | w in Weeks, p in Periods ]);

array[Weeks, Periods] of int: B =      % away team (smaller value)
  array2d(Weeks, Periods,
    [ min(a_raw[w,p], b_raw[w,p]) | w in Weeks, p in Periods ]);

%====================================================================
% 2)  DECISION VARIABLES
%====================================================================
array[Weeks, Periods] of var Periods: pos;   % which match sits in row p of week w

%====================================================================
% 3)  CONSTRAINTS
%====================================================================
%--- 3.a)  Base rule: each week uses every match exactly once
constraint
  forall(w in Weeks)(
    alldifferent([ pos[w,p] | p in Periods ])
  );

%--- 3.b)  Implied rule: a team may occupy the same row ≤ 2 times
array[Teams] of int: cover = [ t | t in Teams ];
array[Teams] of int: low   = [ 0 | _ in Teams ];
array[Teams] of int: up    = [ 2 | _ in Teams ];

constraint
  forall(p in Periods)(
    let {
      array[1..2*W] of var Teams: rowVars =
           [ A[w, pos[w,p]] | w in Weeks ] ++
           [ B[w, pos[w,p]] | w in Weeks ]
    } in
      global_cardinality_low_up(rowVars, cover, low, up)
  );

%--- 3.c)  Symmetry breaking
constraint forall(p in Periods)( pos[1,p] = p );           % fix week-1 permutation

%====================================================================
% 4)  SEARCH STRATEGY
%====================================================================
solve :: int_search([ pos[w,p] | p in Periods, w in Weeks ],
                    first_fail, indomain_min, complete)
       satisfy;

%====================================================================
% 5)  OUTPUT
%====================================================================
function string: pair(int: w, int: p) =
  "[" ++ show(A[w, pos[w,p]]) ++ " , " ++ show(B[w, pos[w,p]]) ++ "]";

output [
  "[\n" ++
  concat([
    "  [" ++
      concat([ pair(w,p) ++ (if w < W then " , " else "" endif)
      | w in Weeks ]) ++ "]" ++
    (if p < P then " ,\n" else "\n" endif)
  | p in Periods ]) ++ "]"
];
