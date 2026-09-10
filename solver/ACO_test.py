# import numpy as np
# import random
# import matplotlib.pyplot as plt
# import pandas as pd
# from problem import Problem
# from solution import Solution
# from greedy import GreedySearch

# class AntColonyOptimization:
#     def __init__(self, num_ants: int, generations: int, alpha: float, beta: float, rho: float, q: float, perturb_rate: float):
#         self.num_ants = num_ants
#         self.generations = generations
#         self.alpha = alpha  # 信息素重要性因子
#         self.beta = beta  # 启发式因子
#         self.rho = rho  # 信息素挥发因子
#         self.q = q  # 信息素强度
#         self.perturb_rate = perturb_rate
#         self.problem = None
#         self.pheromones = None
#         self.best_solution = None
#         self.best_fitness = float('inf')
#         self.gs = GreedySearch()  # GreedySearch 作为启发式初始化
#         self.history = {
#             'Best Fitness': [],
#             'Mean Fitness': []
#         }

#     def set_problem(self, problem: Problem):
#         self.problem = problem
#         self.gs.set_problem(problem)
#         self.pheromones = np.full((problem.get_problem_size(), problem.get_problem_size()), 1.0)

#     def solve(self, problem: Problem, verbose=False, plot_path=None) -> Solution:
#         self.set_problem(problem)

#         for gen in range(self.generations):
#             solutions = self.initialize_ants()
#             # **Apply local search to refine solutions before evaluation**
#             solutions = [self.local_search(sol) for sol in solutions]

#             valid_solutions = [s for s in solutions if self.problem.check_valid_solution(s)]

#             if not valid_solutions:
#                 print(f"Warning: No valid solutions in generation {gen}.")
#                 continue

#             best_sol = min(valid_solutions, key=lambda s: s.get_tour_length())
#             mean_fitness = np.mean([s.get_tour_length() for s in valid_solutions])

#             if best_sol.get_tour_length() < self.best_fitness:
#                 self.best_solution = best_sol
#                 self.best_fitness = best_sol.get_tour_length()

#             self.history['Best Fitness'].append(self.best_fitness)
#             self.history['Mean Fitness'].append(mean_fitness)

#             if verbose:
#                 print(f"Generation {gen}: Best Fit {self.best_fitness:.3f}, Mean Fit {mean_fitness:.3f}")

#             self.update_pheromones(valid_solutions)
            
#             if gen % 10 == 0:
#                 self.perturb_pheromones()

#         if plot_path:
#             self.plot_history(plot_path)
#             problem.plot(self.best_solution, plot_path.replace('.png', '_solution.png'))

#         return self.best_solution

    
#     def initialize_ants(self):
#         """Initialize ants using GreedySearch and refine with local search"""
#         ants = [self.gs.init_solution() for _ in range(self.num_ants)]
#         assert all(ants), "Error: GreedySearch `init_solution()` returned None!"
        
#         optimized_ants = [self.gs.optimize(ant) for ant in ants]
        
#         # **Apply local search to refine solutions**
#         refined_ants = [self.local_search(ant) for ant in optimized_ants]
        
#         return refined_ants



#     def update_pheromones(self, ants):
#         ants = sorted(ants, key=lambda x: x.get_tour_length())
#         tau_max = 1.0 / (0.01 * ants[0].get_tour_length())  
#         tau_min = tau_max / 10

#         for i, ant in enumerate(ants):
#             tour_length = ant.get_tour_length()
#             if tour_length == 0:
#                 continue  # 防止除以零
#             for tour in ant.get_tours():
#                 for j in range(len(tour) - 1):
#                     a, b = tour[j].get_id(), tour[j + 1].get_id()
#                     self.pheromones[a][b] += (1 / tour_length) * (1.5 - i / len(ants))
#                     self.pheromones[b][a] = self.pheromones[a][b]


#         rho = max(0.3, 0.85 - (len(self.history['Best Fitness']) / self.generations) * 0.55)
#         self.pheromones *= (1 - rho)
#         self.pheromones = np.clip(self.pheromones, tau_min, tau_max)

#     def perturb_pheromones(self):
#         mean_pheromone = np.mean(self.pheromones)
#         if mean_pheromone == 0:
#             mean_pheromone = 1e-6  # 避免信息素完全消失
#         self.pheromones = self.pheromones * (1 - self.perturb_rate) + (self.perturb_rate * mean_pheromone)


#     def local_search(self, solution: Solution) -> Solution:
#         if random.random() < 0.5:
#             return self.hmm_aco(solution)
#         else:
#             return self.hsm_aco(solution)

#     def hmm_aco(self, solution: Solution) -> Solution:
#         """蚁群优化的局部搜索：基于信息素和启发式规则进行客户交换"""
#         solution.set_tour_index()
#         tours = solution.get_basic_tours()

#         # **如果只有一个路径，不进行交换**
#         if len(tours) == 1:
#             return solution
        
#         # **随机选取一个非空路径**
#         rd_tour_idx = random.choice([i for i in range(len(tours)) if len(tours[i]) > 0])
#         rd_customer_idx = random.choice(range(len(tours[rd_tour_idx])))
#         rd_customer = tours[rd_tour_idx][rd_customer_idx]

#         tour_idx = solution.tour_index[rd_customer.get_id()]
        
#         # **找到与 rd_customer 信息素最强的候选客户**
#         candidate_list = []
#         for customer_id in self.problem.get_all_customers():
#             if solution.tour_index[customer_id.get_id()] != tour_idx:
#                 candidate_list.append(customer_id)
#                 if len(candidate_list) > 5:  # 限制候选集大小
#                     break
        
#         # **使用信息素 + 启发式距离计算交换概率**
#         probs = []
#         for i, candidate in enumerate(candidate_list):
#             pheromone = self.pheromones[rd_customer.get_id()][candidate.get_id()]
#             distance = self.problem.get_distance(rd_customer, candidate)
#             heuristic = 1.0 / (distance + 1e-6)  # 避免除零
#             probs.append((pheromone ** self.alpha) * (heuristic ** self.beta))
        
#         # **归一化概率**
#         total_prob = sum(probs)
#         if total_prob == 0:
#             return solution  # 没有合适的交换，返回原解
    
#         probs = [p / total_prob for p in probs]
        
#         # **基于概率选择交换的客户**
#         selected_customer = np.random.choice(candidate_list, p=probs)
#         selected_customer_tour_idx = solution.tour_index[selected_customer.get_id()]

#         # **找到 selected_customer 在其路径中的索引**
#         selected_customer_idx = -1
#         for idx, node in enumerate(tours[selected_customer_tour_idx]):
#             if node.get_id() == selected_customer.get_id():
#                 selected_customer_idx = idx
#                 break
        
#         # **交换两个客户**
#         tours[tour_idx][rd_customer_idx], tours[selected_customer_tour_idx][selected_customer_idx] = \
#             tours[selected_customer_tour_idx][selected_customer_idx], tours[tour_idx][rd_customer_idx]
        
#         # **返回新解**
#         return Solution(tours)



#     def hsm_aco(self, solution: Solution) -> Solution:
#         """蚁群优化的局部搜索：基于信息素和启发式规则的客户交换"""
#         solution.set_tour_index()
#         tours = solution.get_basic_tours()

#         # **如果只有一个路径，不进行交换**
#         if len(tours) == 1:
#             return solution
        
#         # **随机选取两个不同的非空路径**
#         tour_a, tour_b = random.sample([i for i in range(len(tours)) if len(tours[i]) > 0], 2)

#         # **随机选择路径中的客户**
#         customer_a = random.choice(tours[tour_a])
#         customer_b = random.choice(tours[tour_b])

#         # **获取客户的索引**
#         customer_a_idx = next(idx for idx, node in enumerate(tours[tour_a]) if node.get_id() == customer_a.get_id())
#         customer_b_idx = next(idx for idx, node in enumerate(tours[tour_b]) if node.get_id() == customer_b.get_id())

#         # **计算基于信息素和距离的交换概率**
#         pheromone_a = self.pheromones[customer_a.get_id()][customer_b.get_id()]
#         pheromone_b = self.pheromones[customer_b.get_id()][customer_a.get_id()]
        
#         distance_a = self.problem.get_distance(customer_a, customer_b)
#         heuristic_a = 1.0 / (distance_a + 1e-6)  # 避免除零

#         exchange_prob = (pheromone_a ** self.alpha) * (heuristic_a ** self.beta)

#         # **按照交换概率决定是否交换**
#         if random.random() < exchange_prob:
#             # **交换两个客户**
#             tours[tour_a][customer_a_idx], tours[tour_b][customer_b_idx] = \
#                 tours[tour_b][customer_b_idx], tours[tour_a][customer_a_idx]

#         return Solution(tours)


#     def plot_history(self, path):
#         df = pd.DataFrame(self.history)
#         df.plot()
#         plt.xlabel('Generation')
#         plt.ylabel('Fitness')
#         plt.title('ACO Convergence ({})'.format(self.problem.get_name()))
#         plt.legend()
#         plt.grid()
#         plt.savefig(path)
#         plt.close()


import random
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from copy import deepcopy
from time import time
from typing import List, Dict, Tuple

from node import Node
from problem import Problem
from solution import Solution
from greedy import GreedySearch
from logger import logger
from SA import SimulatedAnnealing

class AntColonyOptimization:
    """
    Enhanced Ant Colony Optimization implementation for the Electric Vehicle Routing Problem (EVRP).
    
    This algorithm incorporates several enhancements:
    1. Comprehensive solution validation at critical points
    2. Energy-aware construction mechanism for the EVRP domain
    3. Multiple colony approach with adaptive parameters
    4. Specialized repair mechanisms for invalid solutions
    5. Integration with local search and simulated annealing
    """
    
    def __init__(self, num_ants=30, generations=200, alpha=1.0, beta=2.0, 
                 rho=0.1, q=100, perturb_rate=0.05):
        """
        Initialize the Ant Colony Optimization algorithm.
        
        Args:
            num_ants (int): Number of ants in the colony.
            generations (int): Maximum number of generations.
            alpha (float): Importance of pheromone trails (>= 0).
            beta (float): Importance of heuristic information (>= 1).
            rho (float): Pheromone evaporation rate (0 < rho < 1).
            q (float): Pheromone deposit factor.
            perturb_rate (float): Rate of pheromone perturbation (0 < perturb_rate < 1).
        """
        self.num_ants = num_ants
        self.generations = generations
        self.alpha = alpha  # Pheromone importance
        self.beta = beta    # Heuristic importance
        self.rho = rho      # Evaporation rate
        self.q = q          # Pheromone deposit factor
        self.perturb_rate = perturb_rate
        
        # Enhanced parameters
        self.elite_ants = 3  # Number of elite ants to preserve
        self.k_t = 10        # Counter threshold for pheromone perturbation
        self.k_b = 5         # Counter threshold for SA optimization
        self.max_stagnation = 20  # Max generations without improvement before diversification
        
        # Initialize helper algorithms
        self.greedy_search = GreedySearch()
        self.sa_optimizer = SimulatedAnnealing(initial_temp=1000, cooling_rate=0.9, min_temp=1e-3, max_iter=30)
        
        # Tracking history
        self.history = {
            'Generation': [],
            'Best Fitness': [],
            'Mean Fitness': [],
            'Alpha': [],
            'Beta': [],
            'Valid Solutions': []
        }
        
        # Track repair statistics
        self.repair_attempts = 0
        self.repair_successes = 0
        
    def set_problem(self, problem: Problem):
        """
        Set the problem instance for the algorithm.
        
        Args:
            problem (Problem): The EVRP problem instance.
        """
        self.problem = problem
        self.greedy_search.set_problem(problem)
        self.sa_optimizer.set_problem(problem)
        
        # Initialize ant solutions
        self.ant_solutions = [Solution() for _ in range(self.num_ants)]
        
        # Initialize pheromone matrix
        problem_size = problem.get_problem_size()
        self.pheromones = np.ones((problem_size, problem_size)) * 0.5
        self.delta_pheromones = np.zeros((problem_size, problem_size))
        
        # Initialize best solution
        self.best_solution = None
        self.best_tour_length = float('inf')
        
        # Initialize counters for perturbation and SA
        self.t_cnt = 0  # Counter for perturbation
        self.b_cnt = 0  # Counter for SA
        self.stagnation_cnt = 0  # Counter for stagnation
        
    def solve(self, problem: Problem, verbose=False, plot_path=None) -> Solution:
        """
        Solve the EVRP using enhanced Ant Colony Optimization with validity guarantees.
        
        Args:
            problem (Problem): The EVRP problem instance.
            verbose (bool): Whether to print progress information.
            plot_path (str): Path to save convergence plot.
            
        Returns:
            Solution: The best solution found.
        """
        self.set_problem(problem)
        
        # Start with a good initial solution from greedy search
        initial_solution = self.greedy_search.solve(problem, verbose=False)
        valid_initial = problem.check_valid_solution(initial_solution)
        
        if valid_initial:
            self.best_solution = deepcopy(initial_solution)
            self.best_tour_length = initial_solution.get_tour_length()
            if verbose:
                print(f"Starting with valid greedy solution: {self.best_tour_length:.2f}")
        else:
            if verbose:
                print("Initial greedy solution is invalid, starting from scratch")
        
        # Main ACO loop
        for generation in range(self.generations):
            # Adapt parameters based on search progress
            self.adapt_parameters(generation)
            
            # Construct solutions for all ants
            valid_solutions = []
            valid_count = 0
            
            for i in range(self.num_ants):
                # Construct solution for this ant
                solution = self.construct_solution()
                valid = problem.check_valid_solution(solution)
                
                # Track and potentially repair invalid solutions
                if not valid:
                    solution = self.repair_solution(solution)
                    valid = problem.check_valid_solution(solution)
                
                self.ant_solutions[i] = solution
                
                if valid:
                    valid_count += 1
                    valid_solutions.append(solution)
                    
                    # Update best solution if better
                    if solution.get_tour_length() < self.best_tour_length:
                        self.best_solution = deepcopy(solution)
                        self.best_tour_length = solution.get_tour_length()
                        self.t_cnt = 0
                        self.b_cnt = 0
                        self.stagnation_cnt = 0
                        if verbose:
                            print(f"New best at generation {generation}: {self.best_tour_length:.2f}")
                    else:
                        self.b_cnt += 1
                        self.t_cnt += 1
            
            # Check for stagnation
            if len(valid_solutions) > 0:
                if min(s.get_tour_length() for s in valid_solutions) >= self.best_tour_length:
                    self.stagnation_cnt += 1
                else:
                    self.stagnation_cnt = 0
            else:
                self.stagnation_cnt += 1
            
            # Apply SA periodically or when stagnated
            if (self.b_cnt >= self.k_b or self.stagnation_cnt >= self.max_stagnation) and self.best_solution is not None:
                # Use the best solution as starting point
                improved_solution = deepcopy(self.best_solution)
                self.sa_optimizer.set_problem(problem)
                improved_solution = self.sa_optimizer.solve(problem, verbose=False)
                
                if problem.check_valid_solution(improved_solution) and improved_solution.get_tour_length() < self.best_tour_length:
                    self.best_solution = deepcopy(improved_solution)
                    self.best_tour_length = improved_solution.get_tour_length()
                    self.stagnation_cnt = 0
                    if verbose:
                        print(f"SA improved solution at generation {generation}: {self.best_tour_length:.2f}")
                
                self.b_cnt = 0
            
            # Update pheromones based on the solutions
            self.update_pheromones(valid_solutions)
            
            # Apply pheromone perturbation periodically to avoid stagnation
            if self.t_cnt >= self.k_t:
                self.perturb_pheromones()
                self.t_cnt = 0
                if verbose:
                    print(f"Perturbing pheromones at generation {generation}")
            
            # Apply strong diversification when stagnation is severe
            if self.stagnation_cnt >= self.max_stagnation * 2:
                self.strong_diversification()
                self.stagnation_cnt = 0
                if verbose:
                    print(f"Strong diversification at generation {generation}")
            
            # Track history
            mean_fitness = np.mean([s.get_tour_length() for s in valid_solutions]) if valid_solutions else float('inf')
            valid_ratio = valid_count / self.num_ants if self.num_ants > 0 else 0
            
            self.history['Generation'].append(generation)
            self.history['Best Fitness'].append(self.best_tour_length)
            self.history['Mean Fitness'].append(mean_fitness)
            self.history['Alpha'].append(self.alpha)
            self.history['Beta'].append(self.beta)
            self.history['Valid Solutions'].append(valid_ratio)
            
            if verbose and generation % 10 == 0:
                print(f"Generation {generation}: Best = {self.best_tour_length:.2f}, Mean = {mean_fitness:.2f}, "
                      f"Valid = {valid_count}/{self.num_ants}, Alpha = {self.alpha:.2f}, Beta = {self.beta:.2f}")
        
        # Final optimization of best solution
        if self.best_solution is not None:
            # Apply final intensive local search
            self.best_solution = self.iterated_local_search(self.best_solution)
            
            # Verify solution validity
            if not problem.check_valid_solution(self.best_solution):
                self.best_solution = self.repair_solution(self.best_solution)
                
                # If still invalid, fall back to greedy solution
                if not problem.check_valid_solution(self.best_solution):
                    self.best_solution = self.greedy_search.solve(problem, verbose=False)
        else:
            # If no valid solution was found, return a greedy solution
            self.best_solution = self.greedy_search.solve(problem, verbose=False)
        
        # Create convergence plot if requested
        if plot_path:
            self.plot_history(plot_path)
        
        return self.best_solution
    
    def adapt_parameters(self, generation: int):
        """
        Adapt algorithm parameters based on search progress.
        
        Args:
            generation (int): Current generation number.
        """
        # Calculate progress ratio
        progress = generation / self.generations
        
        # Adjust alpha (pheromone importance)
        if progress < 0.3:
            # Start with lower alpha to allow more exploration
            self.alpha = max(0.5, 1.0 - 0.5 * progress/0.3)
        elif progress < 0.7:
            # Gradually increase alpha to intensify exploitation
            self.alpha = 1.0 + 2.0 * (progress - 0.3) / 0.4
        else:
            # Keep high alpha for strong exploitation in final phase
            self.alpha = 3.0
        
        # Adjust beta (heuristic importance)
        if progress < 0.5:
            # Start with high beta for greedy behavior
            self.beta = 3.0
        else:
            # Gradually decrease beta to allow pheromone to dominate
            self.beta = max(1.0, 3.0 - 2.0 * (progress - 0.5) / 0.5)
        
        # Adjust evaporation rate (rho)
        self.rho = 0.1 + 0.3 * progress  # From 0.1 to 0.4
    
    def strong_diversification(self):
        """
        Apply strong diversification to escape local optima.
        """
        # Reset pheromone trails completely
        problem_size = self.problem.get_problem_size()
        self.pheromones = np.ones((problem_size, problem_size)) * 0.5
        
        # Add controlled randomness
        for i in range(problem_size):
            for j in range(i+1, problem_size):
                random_value = 0.5 + (random.random() - 0.5) * 0.2  # ±10% variation
                self.pheromones[i][j] = random_value
                self.pheromones[j][i] = random_value  # Symmetric problem
        
        # Reset counters
        self.t_cnt = 0
        self.b_cnt = 0
    
    def construct_solution(self) -> Solution:
        """
        Construct a solution using pheromone information and heuristic guidance.
        
        Returns:
            Solution: A constructed solution.
        """
        # Start with an empty solution with the depot as the first node
        solution = Solution()
        depot = self.problem.get_depot()
        
        # Track visited customers and current state
        visited = {node.get_id(): False for node in self.problem.get_all_customers()}
        remaining_customers = self.problem.get_num_customers()
        
        # Initialize tours with depot
        current_tour = [depot]
        tours = []
        
        # Track capacity and energy for the current tour
        capacity = self.problem.get_capacity()
        energy = self.problem.get_battery_capacity()
        current_node = depot
        
        # Continue constructing until all customers are visited
        while remaining_customers > 0:
            # Find next node
            next_node = self.select_next_node(current_node, visited, capacity, energy)
            
            # If no suitable next node is found, return to depot and start new tour
            if next_node is None:
                # Need to return to depot
                energy_needed = self.problem.get_energy_consumption(current_node, depot)
                
                # If not enough energy to return to depot, find charging station
                if energy_needed > energy:
                    charging_station = self.find_nearest_charging_station(current_node, energy)
                    
                    if charging_station:
                        current_tour.append(charging_station)
                        energy = self.problem.get_battery_capacity()
                        current_node = charging_station
                
                # Return to depot and start new tour
                current_tour.append(depot)
                tours.append(current_tour)
                
                # Start new tour
                current_tour = [depot]
                current_node = depot
                capacity = self.problem.get_capacity()
                energy = self.problem.get_battery_capacity()
                continue
            
            # Add the node to the current tour
            current_tour.append(next_node)
            
            # Update state
            if next_node.is_customer():
                visited[next_node.get_id()] = True
                remaining_customers -= 1
                capacity -= next_node.get_demand()
            
            # Update energy
            energy -= self.problem.get_energy_consumption(current_node, next_node)
            
            # If we arrive at a charging station, recharge
            if next_node.is_charging_station():
                energy = self.problem.get_battery_capacity()
            
            current_node = next_node
        
        # Complete the last tour by returning to depot if needed
        if current_node.get_id() != depot.get_id():
            # Check if need to add charging station
            energy_needed = self.problem.get_energy_consumption(current_node, depot)
            
            if energy_needed > energy:
                charging_station = self.find_nearest_charging_station(current_node, energy)
                if charging_station:
                    current_tour.append(charging_station)
            
            current_tour.append(depot)
        
        # Add the last tour if not empty
        if len(current_tour) > 1:  # At least depot + one node
            tours.append(current_tour)
        
        # Create solution from tours
        solution = Solution()
        for tour in tours:
            solution.add_tour(tour)
        
        # Apply local search to optimize
        solution = self.apply_local_search(solution)
        
        return solution
    
    def select_next_node(self, current_node, visited, capacity, energy):
        """
        Select the next node to visit based on pheromone and heuristic information.
        
        Args:
            current_node (Node): Current node.
            visited (Dict[int, bool]): Dictionary tracking visited customers.
            capacity (float): Remaining vehicle capacity.
            energy (float): Remaining vehicle energy.
            
        Returns:
            Node: Selected next node or None if no suitable node is found.
        """
        # Get all candidate nodes (unvisited customers and charging stations)
        candidates = []
        
        # Add unvisited customers with sufficient capacity
        for node in self.problem.get_all_customers():
            if not visited[node.get_id()] and node.get_demand() <= capacity:
                energy_needed = self.problem.get_energy_consumption(current_node, node)
                if energy_needed <= energy:
                    candidates.append(node)
        
        # If energy is getting low or no customers available, consider charging stations
        if energy < self.problem.get_battery_capacity() * 0.4 or not candidates:
            for node in self.problem.get_all_stations():
                energy_needed = self.problem.get_energy_consumption(current_node, node)
                if energy_needed <= energy:
                    candidates.append(node)
        
        # If still no candidates, consider returning to depot
        if not candidates:
            depot = self.problem.get_depot()
            energy_needed = self.problem.get_energy_consumption(current_node, depot)
            
            if energy_needed <= energy:
                return depot
            else:
                # No feasible move - try finding nearest charging station
                charging_station = self.find_nearest_charging_station(current_node, energy)
                if charging_station:
                    return charging_station
                return None
        
        # Calculate selection probabilities
        selection_probs = []
        
        for node in candidates:
            i = current_node.get_id()
            j = node.get_id()
            
            # Heuristic factors
            if node.is_customer():
                # For customers, consider distance and demand
                distance = self.problem.get_distance(current_node, node)
                eta = 1.0 / max(0.1, distance)  # Avoid division by zero
                
                # Capacity factor (prefer customers with smaller demand)
                capacity_factor = 1.0 - 0.5 * (node.get_demand() / self.problem.get_capacity())
                eta *= (1.0 + capacity_factor)
            elif node.is_charging_station():
                # For charging stations, consider distance and energy level
                distance = self.problem.get_distance(current_node, node)
                eta = 1.0 / max(0.1, distance)
                
                # Energy factor (prefer stations when energy is low)
                energy_factor = 1.0 - (energy / self.problem.get_battery_capacity())
                eta *= (1.0 + 2.0 * energy_factor)  # Stronger weight when energy is low
            else:
                # For depot, use simple distance
                distance = self.problem.get_distance(current_node, node)
                eta = 1.0 / max(0.1, distance)
            
            # Pheromone factor
            tau = self.pheromones[i][j]
            
            # Combined probability
            prob = (tau ** self.alpha) * (eta ** self.beta)
            selection_probs.append(prob)
        
        # Normalize probabilities
        total_prob = sum(selection_probs)
        if total_prob > 0:
            normalized_probs = [p / total_prob for p in selection_probs]
        else:
            normalized_probs = [1.0 / len(candidates) for _ in candidates]
        
        # Select using roulette wheel
        r = random.random()
        cum_prob = 0
        for i, prob in enumerate(normalized_probs):
            cum_prob += prob
            if r <= cum_prob:
                return candidates[i]
        
        # Fallback: select randomly
        return random.choice(candidates)
    
    def find_nearest_charging_station(self, node, energy):
        """
        Find the nearest charging station that can be reached with the remaining energy.
        
        Args:
            node (Node): Current node.
            energy (float): Remaining energy.
            
        Returns:
            Node: Nearest charging station or None if none can be reached.
        """
        min_distance = float('inf')
        nearest_station = None
        
        for station in self.problem.get_all_stations():
            energy_needed = self.problem.get_energy_consumption(node, station)
            if energy_needed <= energy:
                distance = self.problem.get_distance(node, station)
                if distance < min_distance:
                    min_distance = distance
                    nearest_station = station
        
        # Also consider depot as a charging station
        depot = self.problem.get_depot()
        energy_needed = self.problem.get_energy_consumption(node, depot)
        if energy_needed <= energy:
            distance = self.problem.get_distance(node, depot)
            if distance < min_distance:
                return depot
        
        return nearest_station
    
    def apply_local_search(self, solution: Solution) -> Solution:
        """
        Apply local search to improve the solution.
        
        Args:
            solution (Solution): Initial solution.
            
        Returns:
            Solution: Improved solution.
        """
        # First optimize the basic structure with the greedy search
        solution = self.greedy_search.optimize(solution)
        
        # Check if the solution is valid
        if not self.problem.check_valid_solution(solution):
            return solution  # Don't apply further optimization if invalid
        
        # Apply 2-opt to each tour
        tours = solution.get_tours()
        for i, tour in enumerate(tours):
            # Only apply 2-opt to tours with at least 4 nodes
            if len(tour) >= 4:
                tours[i] = self.two_opt_local_search(tour)
        
        solution.set_vehicle_tours(tours)
        
        # Final optimization with the greedy search
        solution = self.greedy_search.optimize(solution)
        
        return solution
    
    def two_opt_local_search(self, tour):
        """
        Apply 2-opt local search to improve a tour.
        
        Args:
            tour (List[Node]): Initial tour.
            
        Returns:
            List[Node]: Improved tour.
        """
        improved = True
        
        while improved:
            improved = False
            
            # Only consider the inner part of the tour (excluding first and last node)
            for i in range(1, len(tour) - 2):
                for j in range(i + 1, len(tour) - 1):
                    # Skip adjacent edges
                    if j - i == 1:
                        continue
                    
                    # Calculate current cost
                    d1 = self.problem.get_distance(tour[i-1], tour[i])
                    d2 = self.problem.get_distance(tour[j], tour[j+1])
                    
                    # Calculate new cost after swap
                    d3 = self.problem.get_distance(tour[i-1], tour[j])
                    d4 = self.problem.get_distance(tour[i], tour[j+1])
                    
                    # If new route is shorter, swap
                    if d1 + d2 > d3 + d4:
                        # Reverse the segment from i to j
                        tour[i:j+1] = reversed(tour[i:j+1])
                        improved = True
                        break
                
                if improved:
                    break
        
        return tour
    
    def repair_solution(self, solution: Solution) -> Solution:
        """
        Attempt to repair an invalid solution.
        
        Args:
            solution (Solution): Invalid solution.
            
        Returns:
            Solution: Repaired solution or original if repair failed.
        """
        self.repair_attempts += 1
        
        # Make a copy to avoid modifying the original
        repaired = deepcopy(solution)
        
        # First try: Use greedy search to optimize
        repaired = self.greedy_search.optimize(repaired)
        
        if self.problem.check_valid_solution(repaired):
            self.repair_successes += 1
            return repaired
        
        # Second try: Break long tours and re-optimize
        tours = repaired.get_tours()
        
        # Identify tours with energy violations
        modified_tours = []
        
        for tour in tours:
            if len(tour) <= 3:  # Skip very short tours
                modified_tours.append(tour)
                continue
            
            # Check for energy violations
            has_violation = False
            energy = self.problem.get_battery_capacity()
            
            for i in range(len(tour) - 1):
                energy -= self.problem.get_energy_consumption(tour[i], tour[i+1])
                if energy < 0:
                    has_violation = True
                    break
                
                if tour[i+1].is_charging_station():
                    energy = self.problem.get_battery_capacity()
            
            if has_violation:
                # Split this tour at a midpoint
                mid = len(tour) // 2
                
                # Ensure both parts have a depot
                depot = self.problem.get_depot()
                
                if tour[0].get_id() == depot.get_id():
                    tour1 = tour[:mid]
                    if tour[-1].get_id() != depot.get_id():
                        tour1.append(depot)
                else:
                    tour1 = [depot] + tour[:mid]
                
                if tour[-1].get_id() == depot.get_id():
                    tour2 = tour[mid:]
                    if tour[0].get_id() != depot.get_id():
                        tour2.insert(0, depot)
                else:
                    tour2 = tour[mid:] + [depot]
                    if tour[0].get_id() != depot.get_id():
                        tour2.insert(0, depot)
                
                modified_tours.append(tour1)
                modified_tours.append(tour2)
            else:
                modified_tours.append(tour)
        
        # Create a new solution with the modified tours
        solution_with_split_tours = Solution()
        for tour in modified_tours:
            if len(tour) > 1:  # Only add non-empty tours
                solution_with_split_tours.add_tour(tour)
        
        # Optimize again
        solution_with_split_tours = self.greedy_search.optimize(solution_with_split_tours)
        
        if self.problem.check_valid_solution(solution_with_split_tours):
            self.repair_successes += 1
            return solution_with_split_tours
        
        # Third try: Completely rebuild using greedy search
        rebuilt = self.greedy_search.solve(self.problem)
        
        if self.problem.check_valid_solution(rebuilt):
            self.repair_successes += 1
            return rebuilt
        
        # If all repair attempts failed, return the original
        return solution
    
    def iterated_local_search(self, solution: Solution, num_iterations=5) -> Solution:
        """
        Apply iterated local search to further improve the solution.
        
        Args:
            solution (Solution): Initial solution.
            num_iterations (int): Number of iterations to perform.
            
        Returns:
            Solution: Improved solution.
        """
        best_solution = deepcopy(solution)
        best_fitness = solution.get_tour_length()
        
        for _ in range(num_iterations):
            # Apply perturbation
            perturbed = deepcopy(best_solution)
            self.perturb_solution(perturbed)
            
            # Apply local search
            improved = self.apply_local_search(perturbed)
            
            # Check if better
            if (self.problem.check_valid_solution(improved) and 
                improved.get_tour_length() < best_fitness):
                best_solution = deepcopy(improved)
                best_fitness = improved.get_tour_length()
        
        return best_solution
    
    def perturb_solution(self, solution: Solution):
        """
        Apply perturbation to escape local optima.
        
        Args:
            solution (Solution): Solution to perturb.
        """
        # Get tours
        tours = solution.get_basic_tours()
        
        if not tours:
            return
        
        # Apply a random perturbation strategy
        strategy = random.randint(1, 3)
        
        if strategy == 1 and len(tours) > 1:
            # Strategy 1: Exchange customers between two tours
            tour1_idx = random.randint(0, len(tours) - 1)
            tour2_idx = random.randint(0, len(tours) - 1)
            
            while tour2_idx == tour1_idx and len(tours) > 1:
                tour2_idx = random.randint(0, len(tours) - 1)
            
            if len(tours[tour1_idx]) > 0 and len(tours[tour2_idx]) > 0:
                # Select random customers from each tour
                cust1_idx = random.randint(0, len(tours[tour1_idx]) - 1)
                cust2_idx = random.randint(0, len(tours[tour2_idx]) - 1)
                
                # Swap
                tours[tour1_idx][cust1_idx], tours[tour2_idx][cust2_idx] = tours[tour2_idx][cust2_idx], tours[tour1_idx][cust1_idx]
        
        elif strategy == 2:
            # Strategy 2: Reverse a segment in a random tour
            if tours:
                tour_idx = random.randint(0, len(tours) - 1)
                
                if len(tours[tour_idx]) >= 3:
                    i = random.randint(0, len(tours[tour_idx]) - 3)
                    j = random.randint(i + 1, len(tours[tour_idx]) - 1)
                    
                    # Reverse segment
                    tours[tour_idx][i:j+1] = reversed(tours[tour_idx][i:j+1])
        
        else:
            # Strategy 3: Relocate a random customer
            if tours:
                tour_idx = random.randint(0, len(tours) - 1)
                
                if len(tours[tour_idx]) > 0:
                    cust_idx = random.randint(0, len(tours[tour_idx]) - 1)
                    customer = tours[tour_idx].pop(cust_idx)
                    
                    # Insert at a random position in a random tour
                    dest_tour_idx = random.randint(0, len(tours) - 1)
                    if len(tours[dest_tour_idx]) > 0:
                        insert_pos = random.randint(0, len(tours[dest_tour_idx]))
                        tours[dest_tour_idx].insert(insert_pos, customer)
                    else:
                        tours[dest_tour_idx].append(customer)
        
        # Update solution
        solution.set_vehicle_tours(tours)
    
    def update_pheromones(self, valid_solutions):
        """
        Update pheromone levels based on valid solutions.
        
        Args:
            valid_solutions (List[Solution]): Valid solutions found in the current generation.
        """
        # Sort solutions by tour length (ascending)
        valid_solutions.sort(key=lambda s: s.get_tour_length())
        
        # Evaporate existing pheromones
        self.pheromones = (1 - self.rho) * self.pheromones
        
        # Add pheromone for elite solutions
        for idx, solution in enumerate(valid_solutions[:min(self.elite_ants, len(valid_solutions))]):
            tours = solution.get_tours()
            tour_length = solution.get_tour_length()
            rank_factor = self.elite_ants - idx  # Higher rank (lower index) gets more pheromone
            
            for tour in tours:
                for i in range(len(tour) - 1):
                    from_id = tour[i].get_id()
                    to_id = tour[i + 1].get_id()
                    
                    # Add pheromone proportional to solution quality and rank
                    delta = rank_factor * self.q / tour_length
                    self.pheromones[from_id][to_id] += delta
                    self.pheromones[to_id][from_id] += delta  # Symmetric problem
        
        # Add extra pheromone for the best solution found so far
        if self.best_solution:
            tours = self.best_solution.get_tours()
            
            for tour in tours:
                for i in range(len(tour) - 1):
                    from_id = tour[i].get_id()
                    to_id = tour[i + 1].get_id()
                    
                    # Add extra pheromone to the best solution
                    delta = 2 * self.elite_ants * self.q / self.best_tour_length
                    self.pheromones[from_id][to_id] += delta
                    self.pheromones[to_id][from_id] += delta  # Symmetric problem
    
    def perturb_pheromones(self):
        """
        Perturb pheromone levels to avoid stagnation.
        """
        # Calculate mean pheromone level
        mean_pheromone = np.mean(self.pheromones)
        
        # Perturb pheromones towards the mean (diversification)
        self.pheromones = self.pheromones * (1 - self.perturb_rate) + mean_pheromone * self.perturb_rate
    
    def weighted_random_choice(self, items, weights):
        """
        Implementation of weighted random choice for Python versions before 3.6
        
        Args:
            items (List): Items to choose from.
            weights (List[float]): Weights for each item.
        
        Returns:
            Any: Selected item.
        """
        total = sum(weights)
        r = random.random() * total
        cumulative_weight = 0
        for item, weight in zip(items, weights):
            cumulative_weight += weight
            if r <= cumulative_weight:
                return item
        return items[-1]  # Fallback
    
    def plot_history(self, path):
        """
        Plot the convergence history of the algorithm.
        
        Args:
            path (str): Path to save the plot.
        """
        # Create a new dictionary with only the entries that have been updated
        filtered_history = {
            key: values for key, values in self.history.items() 
            if len(values) > 0
        }
        
        # Find the minimum length to ensure all arrays are the same length
        min_length = min(len(values) for values in filtered_history.values())
        
        # Truncate all arrays to the minimum length
        plot_data = {
            key: values[:min_length] for key, values in filtered_history.items()
        }
        
        df = pd.DataFrame(plot_data)
        
        # Create a figure with multiple subplots
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 15))
        
        # Plot fitness values
        ax1.plot(df['Generation'], df['Best Fitness'], label='Best Fitness', linewidth=2)
        if 'Mean Fitness' in df:
            ax1.plot(df['Generation'], df['Mean Fitness'], label='Mean Fitness', alpha=0.7)
        ax1.set_xlabel('Generation')
        ax1.set_ylabel('Fitness (Tour Length)')
        ax1.set_title('ACO Convergence')
        ax1.legend()
        ax1.grid(True)
        
        # Plot parameters
        ax2.plot(df['Generation'], df['Alpha'], label='Alpha', color='red')
        ax2.plot(df['Generation'], df['Beta'], label='Beta', color='green')
        ax2.set_xlabel('Generation')
        ax2.set_ylabel('Parameter Value')
        ax2.set_title('Parameter Adaptation')
        ax2.legend()
        ax2.grid(True)
        
        # Plot valid solution ratio
        if 'Valid Solutions' in df:
            ax3.plot(df['Generation'], df['Valid Solutions'], label='Valid Solutions Ratio', color='blue')
            ax3.set_xlabel('Generation')
            ax3.set_ylabel('Ratio')
            ax3.set_title('Valid Solutions Ratio')
            ax3.set_ylim(0, 1.1)
            ax3.grid(True)
        
        plt.tight_layout()
        plt.savefig(path)
        plt.close()