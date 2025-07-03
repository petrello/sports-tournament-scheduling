include "globals.mzn";

%------------------------------------------------------------
% 0)  INSTANCE PARAMETER
%------------------------------------------------------------
int: n;                          % even number of teams 
constraint n mod 2 = 0 /\ n >= 2;

%------------------------------------------------------------
% 1)  DOMAINS  (derived constants + helper tables)
%------------------------------------------------------------
int: W = n - 1;                  % weeks
int: P = n div 2;                % periods / rows

set of int: Teams   = 1..n;
set of int: Weeks   = 1..W;
set of int: Matches = 1..P;
set of int: Periods = 1..P;

/* Round-robin pairing created once with the classic
   circle-method formula.  A[w,m] plays at home vs B[w,m]. */
array[Weeks, Matches] of int: A =
  array2d(Weeks, Matches,
    [ if m = 1 then n                        % pivot team
      else ((w-1)+(m-1)) mod (n-1) + 1
      endif
    | w in Weeks, m in Matches ]);

array[Weeks, Matches] of int: B =
  array2d(Weeks, Matches,
    [ if m = 1 then w                        % pivot’s opponent
      else ((n-1)-(m-1)+(w-1)) mod (n-1) + 1
      endif
    | w in Weeks, m in Matches ]);

%------------------------------------------------------------
% 2)  DECISION VARIABLES
%------------------------------------------------------------
array[Weeks, Periods] of var Matches: pos;   % which match sits in row p of week w

%------------------------------------------------------------
% 3)  CONSTRAINTS
%------------------------------------------------------------
% 3.a)  Base constraints
constraint
  forall(w in Weeks)(
    alldifferent([ pos[w,p] | p in Periods ])   % each match used once per week
  );

% 3.b)  Base constraints  (max two appearances of a team in any row)
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

% 3.c)  Symmetry-breaking constraints
constraint forall(p in Periods)( pos[1,p] = p );           % fix week-1 permutation

constraint
  forall(w in 2..W-1)(                                    % light lex on first column
    lex_lesseq([ pos[w,1] ], [ pos[w+1,1] ])
  );

%------------------------------------------------------------
% 4)  SEARCH
%------------------------------------------------------------
solve :: int_search([ pos[w,p] | p in Periods, w in Weeks ],
                    first_fail, indomain_min, complete)
       satisfy;

%------------------------------------------------------------
% 5)  OUTPUT
%------------------------------------------------------------
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
