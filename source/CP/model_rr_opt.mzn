include "globals.mzn";

/*====================================================================
  0)  INSTANCE PARAMETER  (unchanged)
====================================================================*/
int: n;
constraint n mod 2 = 0 /\ n >= 2;

/*====================================================================
  1)  DOMAINS & PRE-COMPUTED DATA  (unchanged)
====================================================================*/
int: W = n - 1;          % weeks
int: P = n div 2;        % periods per week

set of int: Teams   = 1..n;
set of int: Weeks   = 1..W;
set of int: Periods = 1..P;

/* circle-method pairs – ordered (larger,smaller) to break mirroring */
array[Weeks, Periods] of int: A =
  array2d(Weeks, Periods,
    [ if p = 1 then n else ((w-1)+(p-1)) mod (n-1) + 1 endif
      | w in Weeks, p in Periods ]);

array[Weeks, Periods] of int: B =
  array2d(Weeks, Periods,
    [ if p = 1 then w else ((n-1)-(p-1)+(w-1)) mod (n-1) + 1 endif
      | w in Weeks, p in Periods ]);


/*====================================================================
  2)  DECISION VARIABLES
====================================================================*/
array[Weeks,Periods] of var Periods: pos;           % which slot
array[Weeks,Periods] of var bool:    swap;   %%% ← NEW  flip A↔B

/*====================================================================
  3)  CONSTRAINTS
====================================================================*/
% 3.a) weekly permutation
constraint
  forall(w in Weeks)( alldifferent([ pos[w,p] | p in Periods ]) );

% 3.b) ≤ 2 appearances per team in each row
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

% 3.c) symmetry breaking
constraint forall(p in Periods)( pos[1,p] = p );     % fix week-1 permutation
constraint forall(p in Periods)( swap[1,p] = false );%%% ← NEW  keep its orientation

/*====================================================================
  4)  HOME / AWAY BALANCING
====================================================================*/
array[Teams] of var 0..W: homeCount;                 %%% ← NEW
constraint
  forall(t in Teams)(
    homeCount[t] =
      sum(w in Weeks, p in Periods)(
          bool2int( (A[w,pos[w,p]] = t) /\ (not swap[w,p]) )   % A home
        + bool2int( (B[w,pos[w,p]] = t) /\        swap[w,p] )  % B home
      )
  );

var 0..W: maxImbalance;                              %%% ← NEW
constraint
  maxImbalance = max([ abs(2*homeCount[t] - W) | t in Teams ]);

%====================================================================
% 5)  SEARCH + OPTIMISE
%====================================================================
solve
:: seq_search([
      % first place the matches…
      int_search([ pos[w,p]  | w in Weeks, p in Periods ],
                 first_fail, indomain_random, complete),
      % …then decide the flips
      int_search([ swap[w,p] | w in Weeks, p in Periods ],
                 first_fail, indomain_random, complete)
   ])
 minimize maxImbalance;

/*====================================================================
  6)  OUTPUT
====================================================================*/
function string: pair(int: w, int: p) =
  if not fix(swap[w,p]) then
      "[" ++ show(A[w,pos[w,p]]) ++ " , " ++ show(B[w,pos[w,p]]) ++ "]"
  else
      "[" ++ show(B[w,pos[w,p]]) ++ " , " ++ show(A[w,pos[w,p]]) ++ "]"
  endif;

output [
  "maxImbalance = ", show(maxImbalance), "\n",
  "[\n" ++
    concat([
      "  [" ++
        concat([ pair(w,p) ++ (if w < W then " , " else "" endif)
        | w in Weeks ]) ++ "]" ++
      (if p < P then " ,\n" else "\n" endif)
    | p in Periods ]) ++ "]\n"
];
