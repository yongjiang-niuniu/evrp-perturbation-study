# import numpy as np
# import pandas as pd
# import matplotlib.pyplot as plt
# from copy import deepcopy
# from random import choice, random, shuffle
# from problem import Problem
# from solution import Solution
# from greedy import GreedySearch

# class SimulatedAnnealing():
#     def __init__(self, initial_temp: float, cooling_rate: float, min_temp: float, max_iter: int):
#         """
#         初始化 SA 相关参数
#         """
#         self.initial_temp = initial_temp
#         self.cooling_rate = cooling_rate
#         self.min_temp = min_temp
#         self.max_iter = max_iter
#         self.gs = GreedySearch()
#         self.history = {'Mean Fitness': [], 'Best Fitness': []}  
#         self.perturbation_success = {"greedy_1": 1, "greedy_2": 1, "swap": 1, "reverse": 1, "split_merge": 1}

#     def set_problem(self, problem: Problem):
#         """
#         设置问题，并生成初始解（多次随机初始化，选最优）
#         """
#         self.problem = problem
#         self.gs.set_problem(problem)

#         # 生成多个初始解，选最优的
#         solutions = [self.gs.optimize(self.gs.init_solution()) for _ in range(5)]
#         self.current_solution = min(solutions, key=lambda s: s.get_tour_length())

#         self.best_solution = deepcopy(self.current_solution)
#         self.best_fitness = self.current_solution.get_tour_length()

#     def solve(self, problem: Problem, verbose=False, plot_path=None) -> Solution:
#         """
#         执行模拟退火算法
#         """
#         self.set_problem(problem)
#         T = self.initial_temp  
#         iteration = 0
#         no_improve_count = 0  

#         while T > self.min_temp and iteration < self.max_iter:
#             new_solution, perturb_type = self.generate_neighbor(self.current_solution)
#             new_fitness = new_solution.get_tour_length()
#             current_fitness = self.current_solution.get_tour_length()
#             delta = new_fitness - current_fitness

#             # 自适应接受率
#             accept_prob = np.exp(-delta / T) if delta > 0 else 1.0
#             if delta < 0 or random() < accept_prob:
#                 self.current_solution = new_solution
#                 if new_fitness < self.best_fitness:
#                     self.best_solution = deepcopy(new_solution)
#                     self.best_fitness = new_fitness
#                     self.perturbation_success[perturb_type] += 1  
#                     no_improve_count = 0  
#                 else:
#                     no_improve_count += 1
#             else:
#                 no_improve_count += 1  

#             # 记录收敛历史
#             valid_solutions = [self.current_solution, self.best_solution]
#             mean_fitness = np.mean([s.get_tour_length() for s in valid_solutions])
#             self.history['Mean Fitness'].append(mean_fitness)
#             self.history['Best Fitness'].append(self.best_fitness)

#             if verbose:
#                 print(f"Iteration {iteration}: Mean Fit {mean_fitness:.3f}, Best Fit {self.best_fitness:.3f}, Temp {T:.5f}, Accept Prob {accept_prob:.4f}")

#             # **优化退火策略**：前期缓慢降温，后期快速降温
#             if iteration < self.max_iter * 0.3:
#                 T *= 0.98  
#             elif no_improve_count > 10:  
#                 T *= 0.92  
#             else:
#                 T *= 0.95  

#             iteration += 1

#         if plot_path is not None:
#             self.plot_history(plot_path)
#             problem.plot(self.best_solution, plot_path.replace('.png', '_solution.png'))

#         return self.best_solution

#     def generate_neighbor(self, solution: Solution):
#         """
#         **自适应扰动策略**
#         """
#         total_success = sum(self.perturbation_success.values())

#         # 确保不会除以 0
#         if total_success == 0:
#             probabilities = {key: 1 / len(self.perturbation_success) for key in self.perturbation_success}
#         else:
#             probabilities = {key: val / total_success for key, val in self.perturbation_success.items()}

#         # 设定 3-opt 概率
#         three_opt_prob = 0.1
#         existing_probs = list(probabilities.values())

#         # 归一化，确保概率和为 1
#         scale_factor = (1 - three_opt_prob) / sum(existing_probs)
#         probabilities = {key: val * scale_factor for key, val in probabilities.items()}

#         # 计算最终概率
#         final_probs = list(probabilities.values()) + [three_opt_prob]

#         # 选择扰动类型
#         perturb_type = np.random.choice(
#             list(probabilities.keys()) + ["three_opt"],
#             p=final_probs
#         )

#         if perturb_type == "greedy_1":
#             return self.greedy_1(solution), "greedy_1"
#         elif perturb_type == "greedy_2":
#             return self.greedy_2(solution), "greedy_2"
#         elif perturb_type == "swap":
#             return self.swap(solution), "swap"
#         elif perturb_type == "reverse":
#             return self.reverse(solution), "reverse"
#         elif perturb_type == "split_merge":
#             return self.split_merge(solution), "split_merge"
#         else:
#             return self.three_opt(solution), "three_opt"



#     def split_merge(self, solution: Solution) -> Solution:
#         """
#         **大尺度扰动：拆分 & 重新合并路径**
#         """
#         tours = solution.get_basic_tours()
#         shuffle(tours)  
#         new_tours = [tour[:len(tour)//2] for tour in tours] + [tour[len(tour)//2:] for tour in tours]
#         return Solution(new_tours)

#     def swap(self, solution: Solution) -> Solution:
#         """
#         **局部扰动：同一路线内随机交换两个客户**
#         """
#         tours = solution.get_basic_tours()
#         rd_tour_idx = choice(range(len(tours)))
#         if len(tours[rd_tour_idx]) < 2:
#             return solution
#         i, j = np.random.choice(len(tours[rd_tour_idx]), 2, replace=False)
#         tours[rd_tour_idx][i], tours[rd_tour_idx][j] = tours[rd_tour_idx][j], tours[rd_tour_idx][i]
#         return Solution(tours)

#     def reverse(self, solution: Solution) -> Solution:
#         """
#         **局部扰动：反转某一段路径**
#         """
#         tours = solution.get_basic_tours()
#         rd_tour_idx = choice(range(len(tours)))
#         if len(tours[rd_tour_idx]) < 2:
#             return solution
#         i, j = sorted(np.random.choice(len(tours[rd_tour_idx]), 2, replace=False))
#         tours[rd_tour_idx][i:j] = reversed(tours[rd_tour_idx][i:j])
#         return Solution(tours)

#     def greedy_1(self, solution: Solution) -> Solution:
#         """
#         **基于最近邻的轻微扰动**
#         """
#         return self.gs.optimize(solution)

#     def greedy_2(self, solution: Solution) -> Solution:
#         """
#         **深度贪心优化**
#         """
#         return self.gs.optimize(self.gs.optimize(solution))
    
#     def three_opt(self, solution: Solution) -> Solution:
#         """
#         **3-opt 局部优化**
#         - 在路径上随机选 3 个断点
#         - 重新连接三条子路径，选择最优的排列
#         """
#         tours = solution.get_basic_tours()
#         rd_tour_idx = choice(range(len(tours)))

#         if len(tours[rd_tour_idx]) < 4:
#             return solution  # 如果路径太短，不进行 3-opt

#         tour = tours[rd_tour_idx]
#         n = len(tour)

#         # 随机选择 3 个不同的断点
#         a, b, c = sorted(np.random.choice(n, 3, replace=False))

#         # 计算所有可能的 3-opt 变换
#         options = [
#             tour[:a] + tour[a:b] + tour[b:c] + tour[c:],  # 原路径
#             tour[:a] + tour[a:b][::-1] + tour[b:c] + tour[c:],  # 逆转第 1 段
#             tour[:a] + tour[a:b] + tour[b:c][::-1] + tour[c:],  # 逆转第 2 段
#             tour[:a] + tour[a:b][::-1] + tour[b:c][::-1] + tour[c:],  # 逆转第 1 和第 2 段
#             tour[:a] + tour[b:c] + tour[a:b] + tour[c:],  # 交换第 1、2 段
#             tour[:a] + tour[b:c][::-1] + tour[a:b] + tour[c:],  # 交换第 1、2 段，逆转第 2 段
#         ]

#         # 选取最优路径
#         best_tour = min(options, key=lambda t: self.problem.calculate_tour_length(Solution([t])))
#         tours[rd_tour_idx] = best_tour
#         return Solution(tours)


#     def plot_history(self, path):
#         df = pd.DataFrame(self.history)
#         df.plot()
#         plt.xlabel('Iteration')
#         plt.ylabel('Fitness')
#         plt.title('Simulated Annealing Convergence ({})'.format(self.problem.get_name()))
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

from problem import Problem
from solution import Solution
from greedy import GreedySearch
from logger import logger

class SimulatedAnnealing:
    """
    Simulated Annealing implementation for the Electric Vehicle Routing Problem (EVRP).
    
    This algorithm starts with an initial solution and iteratively applies local modifications.
    It always accepts improvements and occasionally accepts worse solutions based on a
    temperature parameter, which decreases over time (simulating the annealing process).
    
    Attributes:
        initial_temp (float): Starting temperature of the annealing process.
        cooling_rate (float): Rate at which temperature decreases.
        min_temp (float): Minimum temperature at which the algorithm stops.
        max_iter (int): Maximum number of iterations.
    """
    
    def __init__(self, initial_temp=5000, cooling_rate=0.9999, min_temp=1e-5, max_iter=500):
        """
        Initialize the Simulated Annealing algorithm.
        
        Args:
            initial_temp (float): Starting temperature of the annealing process.
            cooling_rate (float): Rate at which temperature decreases (0 < cooling_rate < 1).
            min_temp (float): Minimum temperature at which the algorithm stops.
            max_iter (int): Maximum number of iterations.
        """
        self.initial_temp = initial_temp
        self.cooling_rate = cooling_rate
        self.min_temp = min_temp
        self.max_iter = max_iter
        self.greedy_search = GreedySearch()
        self.history = {
            'Temperature': [],
            'Current Fitness': [],
            'Best Fitness': [],
            'Accept Probability': []
        }
        
    def set_problem(self, problem: Problem):
        """
        Set the problem instance for the algorithm.
        
        Args:
            problem (Problem): The EVRP problem instance.
        """
        self.problem = problem
        self.greedy_search.set_problem(problem)
    
    def solve(self, problem: Problem, verbose=False, plot_path=None) -> Solution:
        """
        Solve the EVRP using Simulated Annealing.
        
        Args:
            problem (Problem): The EVRP problem instance.
            verbose (bool): Whether to print progress information.
            plot_path (str): Path to save convergence plot.
            
        Returns:
            Solution: The best solution found.
        """
        self.set_problem(problem)
        
        # Initialize with a greedy solution
        current_solution = self.greedy_search.init_solution()
        current_solution = self.greedy_search.optimize(current_solution)
        
        # Track the best solution found
        best_solution = deepcopy(current_solution)
        
        # Initialize temperature
        t_current = self.initial_temp
        
        # Calculate the square root of n for the cooling schedule
        sqrt_n = math.log10(problem.get_problem_size())
        
        # Main simulated annealing loop
        iteration = 0
        while t_current > self.min_temp and iteration < self.max_iter:
            iteration += 1
            
            # Calculate the adaptive parameters
            alpha = 3.0  # Alpha parameter for cooling schedule
            beta = 0.1   # Beta parameter for greedy steps
            t_greedy = problem.get_problem_size() * beta
            t_cool = (alpha * sqrt_n - 1.0) / (alpha * sqrt_n)
            
            # Track if an improvement is found in this iteration
            improve = False
            G = 0  # Counter for greedy steps
            
            # Attempt to find improvements
            while G < t_greedy:
                G += 1
                
                # Generate neighboring solution with the greedy operators
                new_solution = deepcopy(current_solution)
                
                # Apply a random greedy operator
                if random.random() <= 0.5:
                    self.greedy_1(new_solution)
                else:
                    self.greedy_2(new_solution)
                
                # Optimize the new solution
                new_solution = self.greedy_search.optimize(new_solution)
                
                # Calculate improvement
                improve = new_solution.get_tour_length() < current_solution.get_tour_length()
                
                # Accept the new solution if it's better
                if improve:
                    current_solution = new_solution
                    
                    # Update best solution if needed
                    if new_solution.get_tour_length() < best_solution.get_tour_length():
                        best_solution = deepcopy(new_solution)
                    break
                
                # Calculate acceptance probability for worse solutions
                if problem.check_valid_solution(new_solution):
                    # Normalized cost difference
                    upper = abs(new_solution.get_tour_length() - current_solution.get_tour_length()) / \
                           abs(new_solution.get_tour_length() - best_solution.get_tour_length() + 1e-5)
                    
                    # Metropolis acceptance criterion
                    accept_prob = math.exp(-upper / t_current)
                    
                    # Decide whether to accept the worse solution
                    if random.random() < accept_prob:
                        current_solution = new_solution
                        break
            
            # Track history for plotting
            self.history['Temperature'].append(t_current)
            self.history['Current Fitness'].append(current_solution.get_tour_length())
            self.history['Best Fitness'].append(best_solution.get_tour_length())
            
            if verbose and iteration % 10 == 0:
                print(f"Iteration {iteration}: Temp = {t_current:.4f}, Current = {current_solution.get_tour_length():.2f}, Best = {best_solution.get_tour_length():.2f}")
            
            # Cool down the temperature
            t_current *= t_cool
            t_current = max(t_current, self.min_temp)
        
        # Create convergence plot if requested
        if plot_path:
            self.plot_history(plot_path)
        
        return best_solution
    
    def greedy_1(self, solution: Solution):
        """
        First greedy operator: Exchange customers between different tours.
        
        Similar to the greedy_1 method in the C++ implementation.
        
        Args:
            solution (Solution): The solution to modify.
        """
        # Set tour index for the solution
        solution.set_tour_index()
        
        # Get all basic tours (customers only)
        tours = solution.get_basic_tours()
        
        # Skip if there's only one tour
        if len(tours) <= 1:
            return
        
        # Pick a random tour
        tour_idx = random.randint(0, len(tours) - 1)
        if len(tours[tour_idx]) == 0:
            return
        
        # Pick a random customer from the tour
        customer_idx = random.randint(0, len(tours[tour_idx]) - 1)
        customer = tours[tour_idx][customer_idx]
        
        # Find a customer from a different tour (nearest neighbor with probability)
        for near_customer_id in self.greedy_search.nearest_dist_customer_matrix[customer.get_id()]:
            if random.random() < 0.1:  # Skip with some probability to introduce randomness
                continue
                
            # Check if the customer is in a different tour
            if near_customer_id in solution.tour_index and solution.tour_index[near_customer_id] != solution.tour_index[customer.get_id()]:
                near_customer_tour_idx = solution.tour_index[near_customer_id]
                
                # Find the position of the near customer in its tour
                near_customer_idx = -1
                for i, node in enumerate(tours[near_customer_tour_idx]):
                    if node.get_id() == near_customer_id:
                        near_customer_idx = i
                        break
                
                if near_customer_idx != -1:
                    # Get the node object for the near customer
                    near_customer = tours[near_customer_tour_idx][near_customer_idx]
                    
                    # Swap the customers between tours
                    tours[tour_idx][customer_idx] = near_customer
                    tours[near_customer_tour_idx][near_customer_idx] = customer
                    
                    # Update the solution with modified tours
                    solution.set_vehicle_tours(tours)
                    return
    
    def greedy_2(self, solution: Solution):
        """
        Second greedy operator: Move a customer from one tour to another.
        
        Similar to the greedy_2 method in the C++ implementation.
        
        Args:
            solution (Solution): The solution to modify.
        """
        # Set tour index for the solution
        solution.set_tour_index()
        
        # Get all basic tours (customers only)
        tours = solution.get_basic_tours()
        
        # Skip if there's only one tour
        if len(tours) <= 1:
            return
        
        # Pick a random tour and customer
        tour_idx = random.randint(0, len(tours) - 1)
        if len(tours[tour_idx]) == 0:
            return
            
        customer_idx = random.randint(0, len(tours[tour_idx]) - 1)
        customer = tours[tour_idx][customer_idx]
        
        # Calculate current tour capacity
        customer_tour_idx = solution.tour_index[customer.get_id()]
        cost = sum(node.get_demand() for node in tours[customer_tour_idx])
        
        # Find a suitable customer from a different tour to move
        for near_customer_id in self.greedy_search.nearest_dist_customer_matrix[customer.get_id()]:
            # Check if the customer is in a different tour
            if near_customer_id in solution.tour_index and solution.tour_index[near_customer_id] != solution.tour_index[customer.get_id()]:
                near_customer_tour_idx = solution.tour_index[near_customer_id]
                
                # Skip if the target tour would have only one customer left
                if len(tours[near_customer_tour_idx]) <= 1:
                    continue
                
                # Get the near customer node
                near_customer = None
                near_customer_idx = -1
                for i, node in enumerate(tours[near_customer_tour_idx]):
                    if node.get_id() == near_customer_id:
                        near_customer = node
                        near_customer_idx = i
                        break
                
                if near_customer is None:
                    continue
                
                # Check if adding this customer would violate capacity constraint
                if cost + near_customer.get_demand() <= self.problem.get_capacity():
                    # Move the customer from its tour to the target tour
                    tours[tour_idx].append(near_customer)
                    tours[near_customer_tour_idx].pop(near_customer_idx)
                    
                    # Update the solution with modified tours
                    solution.set_vehicle_tours(tours)
                    return
    
    def plot_history(self, path):
        """
        Plot the convergence history of the algorithm.
        
        Args:
            path (str): Path to save the plot.
        """
        df = pd.DataFrame(self.history)
        
        # Create a figure with two subplots
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 12))
        
        # Plot fitness values
        ax1.plot(df['Current Fitness'], label='Current Fitness')
        ax1.plot(df['Best Fitness'], label='Best Fitness')
        ax1.set_xlabel('Iteration')
        ax1.set_ylabel('Fitness (Tour Length)')
        ax1.set_title('Fitness Evolution')
        ax1.legend()
        ax1.grid(True)
        
        # Plot temperature
        ax2.plot(df['Temperature'], label='Temperature', color='red')
        ax2.set_xlabel('Iteration')
        ax2.set_ylabel('Temperature')
        ax2.set_title('Temperature Cooling Schedule')
        ax2.set_yscale('log')  # Use logarithmic scale for better visualization
        ax2.grid(True)
        
        plt.tight_layout()
        plt.savefig(path)
        plt.close()