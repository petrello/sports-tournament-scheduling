# 🏈 Modelling and Solving the Sports Tournament Scheduling (STS) problem

> Project work for the "Combinatorial Decision Making and Optimization" 
> course at Alma Mater Studiorum - University of Bologna.

**Authors**
- Dotti Andrea
- Petrelli Tommaso

## STS problem description
The aim of this project is to solve the Sports Tournament Scheduling (STS)
problem, defined as follows.  A tournament involving $n$ teams is scheduled
over $n − 1$ weeks, with each week divided into $\frac{n}{2}$ periods 
(assuming that $n$ is even), and each period consists of two slots. 
In each period of every week, a game is played between two teams, with 
the team assigned to the first slot playing at home, while the
team in the second slot playing away.

The goal is to decide the home and away teams of all the games in a way that:
- every team plays with every other team only once;
- every team plays once a week;
- every team plays at most twice in the same period over the tournament.

An example schedule with $n=6$ teams is shown in the table below, resulting
in a schedule of 15 games over 5 weeks.

|          | Week 1    | Week 2    | Week 3    | Week 4    | Week 5    |
| -------- | :-------: | :-------: | :-------: | :-------: | :-------: |
| Period 1 | 2 vs 4    | 5 vs 1    | 3 vs 6    | 3 vs 4    | 6 vs 3    | 
| Period 2 | 5 vs 6    | 2 vs 3    | 4 vs 5    | 5 vs 1    | 1 vs 4    |
| Period 3 | 1 vs 3    | 4 vs 6    | 5 vs 1    | 6 vs 2    | 3 vs 5    |


### STS as optimization problem
In addition to the decision problem stated above, an optimization 
version can be implemented. In this case, the goal is to balance the number
of home and away games of each team, to ensure fairness in the tournament. 
For instance, the table above shows a balanced schedule for $n=6$.

## Project work
The purpose of this project work is to model and solve the STS problem
using
(i) **Constraint Programming (CP)**, 
(ii) **propositional SATisfiability (SAT)**
(iii) **Satisfiability Modulo Theories (SMT)**, and 
(iv) **Mixed-Integer Linear Programming (MIP)**.

For this project work, we want to build models as well as
conducting an experimental study using different search strategies
to assess the performance of the solvers. The experimental study
will consider progressively larger values of $n$ for which 
a solution can be obtained within the time limit, i.e. $5$ minutes.