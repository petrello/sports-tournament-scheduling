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
├── instances            # Contains the instances of the STS problem
|   ├── CP
|   ├── SAT
|   ├── SMT
│   └── MIP
├── res                  # Contains the results of the experiments
|   ├── CP               
|   ├── SAT
|   ├── SMT
│   └── MIP
├── source               # Contains the source code for the models implmeneted to solve the STS problem
|   ├── CP 
|   ├── SAT
|   ├── SMT
│   └── MIP
├── .gitignore
├── docker-compose.yaml  # Docker Compose file to manage the container
├── Dockerfile           # Dockerfile to build the container image
├── LICENSE
├── README.md
├── requirements.txt     # Python dependencies for the project
└── check_solution.py    # Checks the correctness of the computed solutions 
```

## Getting Started with Docker

The entire development environment, including all solvers and Python dependencies, is configured in a Docker container for easy and reproducible setup.

### Prerequisites

* [Docker](https://www.docker.com/get-started) installed on your local machine.
* You have cloned this repository. For example:
    ```bash
    git clone https://github.com/petrello/sports-tournament-scheduling.git
    cd sports-tournament-scheduling
    ```

### Build and Run the Container

This project uses Docker Compose to simplify container management.

1.  **Build and Start the Container:**
    Run the following command from the root of the project. It will build the Docker image (if it doesn't exist) and start the container in interactive mode.
    ```bash
    docker-compose up --build -d
    ```
    The `-d` flag runs the container in detached mode. Remove `--build` and `-d` if you want to run it without building.

2.  **Access the Interactive Shell:**
    To get an interactive `bash` shell inside the running container, execute:
    ```bash
    docker-compose exec sports_tournament_scheduling bash
    ```
    You are now inside the container at the `/home/appuser/cdmo` directory, with all solvers and tools ready to use.

### Workflow

Thanks to the volume mounts configured in `docker-compose.yaml`, your local project directory is synchronized with the `/home/appuser/cdmo` directory inside the container.

* **Running Experiments:** Execute your `solve_..._all.py` scripts from the interactive shell.
* **Viewing Results:** Any files saved to the `./res` directory by the scripts inside the container will **automatically appear** in the `./res` folder on your local machine.
* **Editing Code:** You can edit the source code on your local machine using your favorite IDE, and the changes will be immediately reflected inside the container.

### Stopping the Container

When you are finished, you can stop the container from your local machine's terminal by running:
```bash
docker-compose down
```

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details
