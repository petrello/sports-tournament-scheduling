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
% pos[p,w] = which circle-method slot occupies row p in week w
array[Periods,Weeks] of var Periods: pos;
% swap[p,w] = if true, flip A↔B for the match placed at (p,w)
array[Periods,Weeks] of var bool:    swap;

%====================================================================
% CONSTRAINTS
%====================================================================

%--- Main constraint: each week uses a permutation of all matches exactly once
constraint
  forall(w in Weeks)( alldifferent([ pos[p,w] | p in Periods ]) );

%--- Main constraint: each team plays in the same period at most twice
constraint
  forall(p in Periods)(
    let {
      array[1..2*weeks] of var Teams: rowVars =
           [ Home[pos[p,w], w] | w in Weeks ] ++
           [ Away[pos[p,w], w] | w in Weeks ],
      array[Teams] of int: cover = [ t | t in Teams ],
      array[Teams] of int: low   = [ 0 | _ in Teams ],
      array[Teams] of int: up    = [ 2 | _ in Teams ]
    } in
      global_cardinality_low_up(rowVars, cover, low, up)
  );

%--- Symmetry breaking: fix week 1 permutation and its orientation
constraint forall(p in Periods)( pos[p,1] = p );
constraint forall(p in Periods)( swap[p,1] = false );

%--- Symmetry breaking: lexicographic order between periods (rows)
constraint
  forall(p in 1..periods-1)(
    lex_less(
      [ Away[pos[p,w],   w] | w in Weeks ] ++ [ Home[pos[p,w],   w] | w in Weeks ],
      [ Away[pos[p+1,w], w] | w in Weeks ] ++ [ Home[pos[p+1,w], w] | w in Weeks ]
    )
  );

%--- Symmetry breaking: lexicographic order between weeks (columns)
constraint
  forall(w in 1..weeks-1)(
    lex_less(
      [ Away[pos[p,   w],   w] | p in Periods ] ++ [ Home[pos[p,   w],   w] | p in Periods ],
      [ Away[pos[p, w+1], w+1] | p in Periods ] ++ [ Home[pos[p, w+1], w+1] | p in Periods ]
    )
  );


%====================================================================
% HOME / AWAY BALANCING (OBJECTIVE)
%====================================================================
array[Teams] of var 0..weeks: homeCount;
constraint
  forall(t in Teams)(
    homeCount[t] =
      sum(p in Periods, w in Weeks)(
          bool2int( (Home[pos[p,w], w] = t) /\ (not swap[p,w]) )   % A at home
        + bool2int( (Away[pos[p,w], w] = t) /\        swap[p,w] )  % B at home
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
      int_search([ pos[p,w]  | p in Periods, w in Weeks],
                 first_fail, indomain_min, complete),
      % …then decide the flips
      int_search([ swap[p,w] | p in Periods, w in Weeks],
                 first_fail, indomain_min, complete)
   ])
   :: restart_luby(100)
 minimize maxImbalance;

%====================================================================
% OUTPUT
%====================================================================
function string: pair(int: p, int: w) =
  if not fix(swap[p,w]) then
      "[" ++ show(Home[pos[p,w], w]) ++ " , " ++ show(Away[pos[p,w], w]) ++ "]"
  else
      "[" ++ show(Away[pos[p,w], w]) ++ " , " ++ show(Home[pos[p,w], w]) ++ "]"
  endif;

output [
  "maxImbalance = ", show(maxImbalance), "\n",
  "[\n" ++
    concat([
      "  [" ++
        concat([ pair(p,w) ++ (if w < weeks then " , " else "" endif)
        | w in Weeks ]) ++ "]" ++
      (if p < periods then " ,\n" else "\n" endif)
    | p in Periods ]) ++ "]\n"
];
