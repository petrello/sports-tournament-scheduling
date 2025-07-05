include "globals.mzn";

%--------------------------------------------------------------------
% INSTANCE PARAMETER
%--------------------------------------------------------------------
int: n;                                 % #teams (even, read from .dzn)
constraint n mod 2 = 0 /\ n >= 2;       % sanity check – MUST be even ≥ 2
%--------------------------------------------------------------------
% HELPER VARIABLES
%--------------------------------------------------------------------
int: W = n - 1;                         % #weeks = columns
int: P = n div 2;                       % #periods (=rows) per week

set of int: Weeks   = 1..W;             % column indices
set of int: Periods = 1..P;             % row indices
set of int: Teams = 1..n;               % teams' ids

%--------------------------------------------------------------------
% CIRCLE-METHOD – place team n fixed, arrange the other n-1 teams in a circle.
%                 For each week rotate the circle one step and pair facing teams 
%--------------------------------------------------------------------
array[Weeks, Periods] of int: a_raw =
  array2d(Weeks, Periods,
    [ if p = 1 then n
      else ((w-1) + (p-1)) mod (n-1) + 1 endif
    | w in Weeks, p in Periods ]);

array[Weeks, Periods] of int: b_raw =
  array2d(Weeks, Periods,
    [ if p = 1 then w
      else ((n-1) - (p-1) + (w-1)) mod (n-1) + 1 endif
    | w in Weeks, p in Periods ]);

/* The max min ordering within each match has been removed since it increases the imbalance*/

/* Row to swap with row 1 (except week 1) to have a decreasing order in the first row.
   This is an empiric heuristic to reduce the cases where one team appears more than two
   times in the first row. */
array[Weeks] of int: swap_row =
    [ 1 ] ++                                      % week 1: nothing to swap
    [ let {
        int: tgt = n - (w-1);                     % decresing team id as target
        set of int: cand = { r | r in 2..P
                            where a_raw[w,r] = tgt \/ b_raw[w,r] = tgt }
      } in min(cand)                              % select the first occurrence 
    | w in 2..W ];

/* Final tables (after the swap) */
array[Weeks,Periods] of int: A =
  array2d(Weeks,Periods,
    [ if w>1 /\ p=1               then a_raw[w, swap_row[w]] %swap first element with the new one
      elseif w>1 /\ p=swap_row[w] then a_raw[w, 1]           %swap new element with the first one
      else a_raw[w,p] endif
    | w in Weeks, p in Periods ]);

array[Weeks,Periods] of int: B =
  array2d(Weeks,Periods,
    [ if w>1 /\ p=1               then b_raw[w, swap_row[w]] %swap first element with the new one
      elseif w>1 /\ p=swap_row[w] then b_raw[w, 1]           %swap new element with the first one
      else b_raw[w,p] endif
    | w in Weeks, p in Periods ]);

%--------------------------------------------------------------------
%  Check if the raw table ALREADY satisfies ≤ 2 appearences per team per row
%--------------------------------------------------------------------
bool: already_ok =
    max([ sum(w in Weeks)(
            bool2int(A[w,p] = t \/ B[w,p] = t)
          )
        | p in Periods, t in Teams ]) <= 2;

%--------------------------------------------------------------------
%  DECISION VARIABLES
%     pos[w,p] = which match index (1..P) is placed in row p of week w.
%     It keeps the pairs and permute them along their weeks, if needed.
%
%     swap[w,p] keeps track of the possible swaps inside each pair to
%     balance home and away matches for each team.
%--------------------------------------------------------------------
array[Weeks, Periods] of var Periods: pos;
array[Weeks, Periods] of var bool: swap;

%--------------------------------------------------------------------
%  CONSTRAINTS
%--------------------------------------------------------------------
/* Core constraint 1: each week is a permutation of matches
   – enforces that every match appears exactly once per week */
constraint
  forall(w in Weeks)(
    alldifferent([ pos[w,p] | p in Periods ])
  );

/* Core constraint 2: row capacity ≤ 2
   – Gather the 2*W team (A and B) numbers that land in a given row p
   – global_cardinality_low_up makes sure each team appears ≤ 2 times */
array[Teams] of int: cover = [ t | t in Teams ];  % labels
array[Teams] of int: low   = [ 0 | _ in Teams ];  % min occurrences
array[Teams] of int: up    = [ 2 | _ in Teams ];  % max occurrences (rule)

constraint
  forall(p in Periods)(
    let {
      array[1..2*W] of var Teams: rowVars =
           [ A[w, pos[w,p]] | w in Weeks ] ++
           [ B[w, pos[w,p]] | w in Weeks ]
    } in
      global_cardinality_low_up(rowVars, cover, low, up)
  );

/* Implied constraints (modelled by construction)
   - Each team plays exactly once per week (property of circle method)
   - All matches are unique => no duplicate games anywhere
*/
%--------------------------------------------------------------------
%  OBJECTIVE FUNCTION
%--------------------------------------------------------------------
array[Teams] of var 0..W: homeCount;

constraint
  forall(t in Teams)(
    homeCount[t] =
      sum(w in Weeks, p in Periods)( % sum the occurrences of team t in A (home) and B (if swapped)
        bool2int( (A[w, pos[w,p]] = t) /\ (not swap[w,p]) ) +
        bool2int( (B[w, pos[w,p]] = t) /\ swap[w,p] )
      )
  );

var 0..W: maxImbalance;   % the max difference (home-away) among the teams
constraint maxImbalance = max([ abs(homeCount[t] - (W - homeCount[t])) | t in Teams ]);


%--------------------------------------------------------------------
%  SEARCH STRATEGY  (basic symmetry breaking via variable order)
%--------------------------------------------------------------------
ann: search_ann =
    if already_ok then       % Search strategy starting from the already correct initial solution
        int_search(
            [ pos[w,p] | p in Periods, w in Weeks ],
            input_order, indomain_min, complete)
    else                     % Search strategy with first-fail to find correct periods permutations
        int_search(
            [ pos[w,p] | p in Periods, w in Weeks ],
            first_fail, indomain_min, complete)
    endif;

solve :: search_ann minimize maxImbalance;

%--------------------------------------------------------------------
%  OUTPUT – show final table
%--------------------------------------------------------------------
function string: pair(int: w, int: p) =
  "[" ++
    (if not fix(swap[w,p]) then
        show(A[w, pos[w,p]]) ++ ", " ++ show(B[w, pos[w,p]])
     else
        show(B[w, pos[w,p]]) ++ ", " ++ show(A[w, pos[w,p]])
     endif) ++ "]";

output [
  "maxImbalance = ", show(maxImbalance), ";\n",
  "[\n" ++
    concat([
      "  [" ++
        concat([ pair(w,p) ++ (if w < W then ", " else "" endif)
        | w in Weeks ]) ++ "]" ++
      (if p < P then ",\n" else "\n" endif)
    | p in Periods ]) ++ "]\n"
];
