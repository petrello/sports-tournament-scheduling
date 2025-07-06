# 🏈 Modelling and Solving the Sports Tournament Scheduling (STS) problem

> Project work for the "Combinatorial Decision Making and Optimization" 
> course at Alma Mater Studiorum - University of Bologna.

**Authors**
- Dotti Andrea [[_Github profile_](https://github.com/AndreaD002)][[_Institutional_ _email_](mailto:andrea.dotti4@studio.unibo.it)]
- Petrelli Tommaso [[_Github profile_](https://github.com/petrello)][[_Institutional_ _email_](mailto:tommaso.petrelli2@studio.unibo.it)]

## STS problem description
The aim of this project is to solve the Sports Tournament Scheduling (STS)s
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

## Repository structure

```
.
├── res         
|   ├── CP              # Stores the results of CP optimization technology 
|   ├── SAT             # Stores the results of SAT optimization technology    
|   ├── SMT             # Stores the results of SMT optimization technology
│   └── MIP             # Stores the results of MIP optimization technology
├── source
|   ├── CP              # Contains the source code for CP optimization technology
|   ├── SAT             # Contains the source code for SAT optimization technology
|   ├── SMT             # Contains the source code for SMT optimization technology
│   └── MIP             # Contains the source code for MIP optimization technology
├── .gitignore
├── check_solution.py   # Checks the correctness of the computed solutions 
├── LICENSE
└── README.md
```

## Run Docker container
If you want to use and test the models available in this repository, you can
build and run the Docker container by following the steps below.

You have cloned this repository on your local machine. For example:
 ```bash
 $ git clone https://github.com/petrello/sports-tournament-scheduling.git
 ```

1. Build the Docker container image by running:
    ```bash
    $ docker build -t sports-tournament-scheduling .
    ```

2. Start the Docker container image in interactive mode by running:
    ```bash
    $ docker run -it sports-tournament-scheduling
    ```

### Run inside the container
To download a certain folder locally in your how machine run
```bash
$ docker cp <container_name>:docker_source_path host_dest_path
```

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details
