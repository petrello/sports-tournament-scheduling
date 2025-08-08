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
   A = max(team1, team2), B = min(team1, team2).      */

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

array[Weeks, Periods] of int: A =          % home team
  array2d(Weeks, Periods,
    [ max(a_raw[w,p], b_raw[w,p]) | w in Weeks, p in Periods ]);

array[Weeks, Periods] of int: B =          % away team
  array2d(Weeks, Periods,
    [ min(a_raw[w,p], b_raw[w,p]) | w in Weeks, p in Periods ]);

%====================================================================
% DECISION VARIABLES
%====================================================================
% pos[w,p] = which match occupies row p in week w
array[Weeks, Periods] of var Periods: pos;

%====================================================================
% CONSTRAINTS
%====================================================================

%--- Main constraint: each week uses a match exactly once
constraint
  forall(w in Weeks)(
    alldifferent([ pos[w,p] | p in Periods ])
  );

%--- Main constraint: each team plays in the same period at most twice
constraint
  forall(p in Periods)(
    let {
      array[1..2*weeks] of var Teams: rowVars =
           [ A[w, pos[w,p]] | w in Weeks ] ++
           [ B[w, pos[w,p]] | w in Weeks ],
      array[Teams] of int: cover = [ t | t in Teams ],
      array[Teams] of int: low   = [ 0 | _ in Teams ],
      array[Teams] of int: up   = [ 2 | _ in Teams ]
    } in
      global_cardinality_low_up(rowVars, cover, low, up)
  );

%--- Symmetry breaking: fix week 1 to the identity permutation
constraint
  forall(p in Periods)( pos[1,p] = p );

%--- Symmetry breaking: lexicographic order between periods (rows)
constraint
  forall(p in 1..periods-1)(
    lex_less(
      [ B[w, pos[w,p]]   | w in Weeks ] ++ [ A[w, pos[w,p]]   | w in Weeks ],
      [ B[w, pos[w,p+1]] | w in Weeks ] ++ [ A[w, pos[w,p+1]] | w in Weeks ]
    )
  );

%--- Symmetry breaking: lexicographic order between weeks (columns)
constraint
  forall(w in 1..weeks-1)(
    lex_less(
      [ B[w,   pos[w,   p]] | p in Periods ] ++ [ A[w,   pos[w,   p]] | p in Periods ],
      [ B[w+1, pos[w+1, p]] | p in Periods ] ++ [ A[w+1, pos[w+1, p]] | p in Periods ]
    )
  );

%====================================================================
% SEARCH STRATEGY
%====================================================================
solve :: int_search([ pos[w,p] | p in Periods, w in Weeks ],
                    first_fail, indomain_min, complete)
       satisfy;

%====================================================================
% OUTPUT
%====================================================================
function string: pair(int: w, int: p) =
  "[" ++ show(A[w, pos[w,p]]) ++ " , " ++ show(B[w, pos[w,p]]) ++ "]";

output [
  "[\n" ++
  concat([
    "  [" ++
      concat([ pair(w,p) ++ (if w < weeks then " , " else "" endif)
      | w in Weeks ]) ++ "]" ++
    (if p < periods then " ,\n" else "\n" endif)
  | p in Periods ]) ++ "]"
];
