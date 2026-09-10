import argparse
import os

import numpy as np

from problem import Problem
from greedy import GreedySearch
from GA import GSGA
from logger import get_problem_name, logger
import random
from ACO import AntColonyOptimization  # 引入 ACO
from PSO import ParticleSwarmOptimization  # 引入 PSO
from MILP import MILP
from BNB import BranchAndBound
from VNS import VNS
def argparser():
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--problem-path', type=str, default='./benchmark/E-n22-k4.evrp')
    parser.add_argument('-a', '--algorithm', type=str, default='GreedySearch')
    parser.add_argument('-o', '--result-path', type=str, default='./results/GreedySearch/')
    parser.add_argument('-n', '--nruns', type=int, default=10)
    parser.add_argument('--seed', type=int, default=12)
    args = parser.parse_args()
    return args

def set_random_seed(seed):
    np.random.seed(seed)
    random.seed(seed)
    

if __name__ == "__main__":
    args = argparser()
    set_random_seed(args.seed)
    problem_name = get_problem_name(args.problem_path)
    problem = Problem(args.problem_path)
    
    if args.algorithm == 'GreedySearch':
        algorithm = GreedySearch()
        
        kwargs = {
            'problem': problem,
            'verbose': True
        }
    elif args.algorithm == 'GSGA':
        algorithm = GSGA(population_size=100, generations=200, 
                          crossover_prob=0.85, mutation_prob=0.75, elite_rate=0.2)
        
        kwargs = {
            'problem': problem,
            'verbose': True,
            'plot_path': os.path.join(args.result_path, problem_name, 'fitness_history.png')
        }
    elif args.algorithm == 'SA':
        from SA import SimulatedAnnealing
        algorithm = SimulatedAnnealing(initial_temp=10000, cooling_rate=0.99, min_temp=1e-6, max_iter=2000)

        kwargs = {
            'problem': problem,
            'verbose': True,
            'plot_path': os.path.join(args.result_path, problem_name, 'fitness_history_SA.png')
        }
    elif args.algorithm == 'ACO':
        algorithm = AntColonyOptimization(
            num_ants=30, 
            generations=200, 
            alpha=1.0, 
            beta=2.0, 
            rho=0.1, 
            q=100, 
            perturb_rate=0.05
        )

        kwargs = {
            'problem': problem,
            'verbose': True,
            'plot_path': os.path.join(args.result_path, problem_name, 'aco_fitness.png')  # 自动保存收敛曲线
        }
    elif args.algorithm == 'PSO':
        algorithm = ParticleSwarmOptimization(
            num_particles=40,
            iterations=300,
            w=0.9,             # Initial inertia weight
            c1=2.0,            # Personal best influence
            c2=2.0,            # Global best influence
            w_min=0.4,         # Minimum inertia weight
            intensive_search=True,
            local_search_freq=5
        )
        
        kwargs = {
            'problem': problem,
            'verbose': True,
            'plot_path': os.path.join(args.result_path, problem_name, 'pso_fitness.png')
        }
    elif args.algorithm == 'MILP':
        algorithm = MILP(time_limit=1800, iterations=100000)
        
        kwargs = {
            'problem': problem,
            'verbose': True,
            'plot_path': os.path.join(args.result_path, problem_name, 'milp_convergence.png')
        }
    elif args.algorithm == 'BNB':
        algorithm = BranchAndBound(time_limit=1800, max_nodes=100000)
        
        kwargs = {
            'problem': problem,
            'verbose': True,
            'plot_path': os.path.join(args.result_path, problem_name, 'bnb_convergence.png')
    }
    elif args.algorithm == 'VNS':
        algorithm = VNS(max_iterations=2000, max_time=1800, k_max=4, shake_intensity=3)
        
        kwargs = {
            'problem': problem,
            'verbose': True,
            'plot_path': os.path.join(args.result_path, problem_name, 'vns_convergence.png')
    }
    else:
        raise ValueError(f'Invalid algorithm {args.algorithm}')
    results = []
    
    
    
    
    
    
    
    
    for i in range(args.nruns):
        result_path = os.path.join(args.result_path, problem_name)
        result_file = os.path.join(result_path, f"run_{i}.txt")
        figure_file = os.path.join(result_path, f"run_{i}.png")
        
        if not os.path.exists(result_path):
            os.makedirs(result_path)
        solution = algorithm.solve(**kwargs)
        
        if problem.check_valid_solution(solution, verbose=True):
            tour_length = solution.get_tour_length()
            with open(result_file, 'w') as f:
                f.write(f"{tour_length}\n")
                
            results.append(tour_length)
            problem.plot(solution, figure_file)
            print(solution)
        else:
            logger.error('Invalid solution')
            results.append(np.inf)
            
            with open(result_file, 'w') as f:
                f.write(f"{np.inf}\n")
            
            