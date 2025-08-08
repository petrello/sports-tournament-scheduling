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
/* Circle-method pairs (no canonicalization here).
   Orientation (home/away) is decided by the decision var `swap`.       */
array[Weeks, Periods] of int: A =
  array2d(Weeks, Periods,
    [ if p = 1 then n else ((w-1) + (p-1)) mod (n-1) + 1 endif
    | w in Weeks, p in Periods ]);

array[Weeks, Periods] of int: B =
  array2d(Weeks, Periods,
    [ if p = 1 then w else ((n-1) - (p-1) + (w-1)) mod (n-1) + 1 endif
    | w in Weeks, p in Periods ]);

%====================================================================
% DECISION VARIABLES
%====================================================================
% pos[w,p] = which circle-method slot occupies row p in week w
array[Weeks,Periods] of var Periods: pos;
% swap[w,p] = if true, flip A↔B for the match placed at (w,p)
array[Weeks,Periods] of var bool:    swap;

%====================================================================
% CONSTRAINTS
%====================================================================

%--- Main constraint: each week uses a permutation of all matches exactly once
constraint
  forall(w in Weeks)( alldifferent([ pos[w,p] | p in Periods ]) );

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

%--- Symmetry breaking: fix week 1 permutation and its orientation
constraint forall(p in Periods)( pos[1,p] = p );
constraint forall(p in Periods)( swap[1,p] = false );

%--- Symmetry breaking: lexicographic order between weeks (columns)
constraint
  forall(w in 1..weeks-1)(
    lex_less(
      [ B[w,   pos[w,   p]] | p in Periods ] ++ [ A[w,   pos[w,   p]] | p in Periods ],
      [ B[w+1, pos[w+1, p]] | p in Periods ] ++ [ A[w+1, pos[w+1, p]] | p in Periods ]
    )
  );


%====================================================================
% HOME / AWAY BALANCING (OBJECTIVE)
%====================================================================
array[Teams] of var 0..weeks: homeCount;
constraint
  forall(t in Teams)(
    homeCount[t] =
      sum(w in Weeks, p in Periods)(
          bool2int( (A[w, pos[w,p]] = t) /\ (not swap[w,p]) )   % A at home
        + bool2int( (B[w, pos[w,p]] = t) /\        swap[w,p] )  % B at home
      )
  );

var 0..weeks: maxImbalance;
constraint
  maxImbalance = max([ abs(2*homeCount[t] - weeks) | t in Teams ]);

%====================================================================
% SEARCH + OPTIMISE
%====================================================================
solve
:: seq_search([
      % first place the matches (permutations)…
      int_search([ pos[w,p]  | w in Weeks, p in Periods ],
                 first_fail, indomain_min, complete),
      % …then decide the flips
      int_search([ swap[w,p] | w in Weeks, p in Periods ],
                 first_fail, indomain_min, complete)
   ])
 minimize maxImbalance;

%====================================================================
% OUTPUT
%====================================================================
function string: pair(int: w, int: p) =
  if not fix(swap[w,p]) then
      "[" ++ show(A[w, pos[w,p]]) ++ " , " ++ show(B[w, pos[w,p]]) ++ "]"
  else
      "[" ++ show(B[w, pos[w,p]]) ++ " , " ++ show(A[w, pos[w,p]]) ++ "]"
  endif;

output [
  "maxImbalance = ", show(maxImbalance), "\n",
  "[\n" ++
    concat([
      "  [" ++
        concat([ pair(w,p) ++ (if w < weeks then " , " else "" endif)
        | w in Weeks ]) ++ "]" ++
      (if p < periods then " ,\n" else "\n" endif)
    | p in Periods ]) ++ "]\n"
];
