include "globals.mzn";

%====================================================================
% 0)  INSTANCE PARAMETER
%====================================================================
int: n;                        % even number of teams (set in .dzn)
constraint n mod 2 = 0 /\ n >= 2;

%====================================================================
% 1)  CIRCLE-METHOD FIXTURE  (constants)
%====================================================================
int: W = n - 1;                % weeks  (columns)
int: P = n div 2;              % periods/rows per week

set of int: Weeks   = 1..W;
set of int: Matches = 1..P;    % match indices 1..P
set of int: Periods = 1..P;    % rows 1..P

array[Weeks, Matches] of int: a_raw =
  array2d(Weeks, Matches,
    [ if m = 1 then n
      else ((w-1) + (m-1)) mod (n-1) + 1
      endif
    | w in Weeks, m in Matches ]);

array[Weeks, Matches] of int: b_raw =
  array2d(Weeks, Matches,
    [ if m = 1 then w
      else ((n-1) - (m-1) + (w-1)) mod (n-1) + 1
      endif
    | w in Weeks, m in Matches ]);

array[Weeks, Matches] of int: A_h =
  array2d(Weeks, Matches,
    [ max(a_raw[w,m], b_raw[w,m]) | w in Weeks, m in Matches ]);

array[Weeks, Matches] of int: B_h =
  array2d(Weeks, Matches,
    [ min(a_raw[w,m], b_raw[w,m]) | w in Weeks, m in Matches ]);


array[Weeks] of int: swap_row =
    [ 1 ] ++
    [ let {
        int: tgt = n - (w-1);
        set of int: cand = { r | r in 2..P where A_h[w,r] = tgt \/ B_h[w,r] = tgt }
      } in min(cand)
    | w in 2..W ];

array[Weeks,Matches] of int: A =
  array2d(Weeks,Matches,
    [ if w>1 /\ m=1              then A_h[w, swap_row[w]]
      elseif w>1 /\ m=swap_row[w] then A_h[w, 1]
      else A_h[w,m] endif
    | w in Weeks, m in Matches ]);

array[Weeks,Matches] of int: B =
  array2d(Weeks,Matches,
    [ if w>1 /\ m=1              then B_h[w, swap_row[w]]
      elseif w>1 /\ m=swap_row[w] then B_h[w, 1]
      else B_h[w,m] endif
    | w in Weeks, m in Matches ]);
%====================================================================
% 2)  “IS THE ORIGINAL TABLE ALREADY OK?”  (constant Boolean)
%====================================================================
set of int: Teams = 1..n;

/* In the initial layout each week puts match m in row m, i.e. pos0[w,p]=p. */
/* true  ⇔  every team appears ≤ 2 times in every period (row) */
bool: already_ok =
    max( [   %  maximum over all ⟨row p, team t⟩
             sum(w in Weeks)(
                 bool2int(A[w,p] = t \/ B[w,p] = t)
             )
         | p in Periods, t in Teams ] )   <= 2;


%====================================================================
% 3)  DECISION VARIABLES  (only needed if already_ok = false)
%     pos[w,p] = which match index sits in row p of week w
%====================================================================
array[Weeks, Periods] of var Matches: pos;

/* If the original layout is good, freeze every variable to its
   default position → the solver stops immediately.                 */
constraint forall(w in Weeks, p in Periods)(
             already_ok ->           % guard
             (pos[w,p] = p)          % fixed to default
          );

/* Each week must use every match exactly once (row permutation). */
constraint
  forall(w in Weeks)(
    alldifferent([ pos[w,p] | p in Periods ])
  );

/* Period-cardinality rule ≤ 2  (checked or enforced with variables). */
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

%--------------------------------------------------------------------
%  OPTIONAL symmetry breaking when search is needed
%--------------------------------------------------------------------
/*constraint forall(p in Periods)( pos[1,p] = p );           % fix week-1
constraint forall(w in 2..W-1)( lex_lesseq([ pos[w,1] ],
                                             [ pos[w+1,1] ]) );*/

%====================================================================
% 4)  SEARCH STRATEGY
%====================================================================
solve :: int_search([ pos[w,p] | p in Periods, w in Weeks ],
                    first_fail, indomain_random, complete)
       satisfy;

%====================================================================
% 5)  OUTPUT
%====================================================================
function string: pair_orig(int: w, int: p) =
  "[" ++ show(A[w,p]) ++ " , " ++ show(B[w,p]) ++ "]";

function string: pair_final(int: w, int: p) =
  "[" ++ show(A[w, pos[w,p]]) ++ " , " ++ show(B[w, pos[w,p]]) ++ "]";

output [
  "=== ORIGINAL CIRCLE-METHOD TABLE ===\n",
  "[\n" ++
    concat([
      "  [" ++
        concat([ pair_orig(w,p) ++ (if w < W then " , " else "" endif)
        | w in Weeks ]) ++ "]" ++
      (if p < P then " ,\n" else "\n" endif)
    | p in Periods ]) ++
  "]\n\n",

  "=== FINAL TABLE (" ++
    (if already_ok then "unchanged – it was already valid"
                   else "permuted to fix row counts" endif) ++
  ") ===\n",
  "[\n" ++
    concat([
      "  [" ++
        concat([ pair_final(w,p) ++ (if w < W then " , " else "" endif)
        | w in Weeks ]) ++ "]" ++
      (if p < P then " ,\n" else "\n" endif)
    | p in Periods ]) ++
  "]\n"
];
