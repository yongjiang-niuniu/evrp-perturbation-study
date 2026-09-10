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
    Enhanced Simulated Annealing implementation for the Electric Vehicle Routing Problem (EVRP).
    
    This algorithm uses multiple strategies to find near-optimal solutions for EVRP:
    1. Diversified initial solution generation
    2. Adaptive temperature control 
    3. Multiple neighborhood operators
    4. Problem-specific mutations (energy-aware)
    5. Intensive local search with validation
    """
    
    def __init__(self, initial_temp=10000, cooling_rate=0.99, min_temp=1e-6, max_iter=2000):
        """
        Initialize the Simulated Annealing algorithm with optimized parameters.
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
            'Accept Probability': [],
            'Valid Solution': []
        }
        # Track operator effectiveness for adaptive operator selection
        self.operator_success = {
            'greedy_1': 1,
            'greedy_2': 1,
            'three_opt': 1,
            'reverse': 1,
            'swap': 1,
            'energy_aware': 1,
            'station_insertion': 1
        }
        
    def set_problem(self, problem: Problem):
        """
        Set the problem instance for the algorithm.
        """
        self.problem = problem
        self.greedy_search.set_problem(problem)
    
    def weighted_random_choice(self, items, weights):
        """
        Implementation of weighted random choice for Python versions before 3.6
        """
        total = sum(weights)
        r = random.random() * total
        cumulative_weight = 0
        for item, weight in zip(items, weights):
            cumulative_weight += weight
            if r <= cumulative_weight:
                return item
        return items[-1]  # Fallback
    
    def solve(self, problem: Problem, verbose=False, plot_path=None) -> Solution:
        """
        Solve the EVRP using enhanced Simulated Annealing with validity guarantees.
        """
        self.set_problem(problem)
        
        # Generate a diverse set of initial solutions
        initial_solutions = self.generate_diverse_initial_solutions(10)
        current_solution = min(initial_solutions, key=lambda s: s.get_tour_length())
        
        # Track the best solution found
        best_solution = deepcopy(current_solution)
        best_fitness = current_solution.get_tour_length()
        
        # Initialize temperature and tracking variables
        t_current = self.initial_temp
        iteration = 0
        stagnation_count = 0
        max_stagnation = 100  # Reheat after this many iterations without improvement
        consecutive_invalid = 0  # Track consecutive invalid solutions
        
        # Main simulated annealing loop
        while t_current > self.min_temp and iteration < self.max_iter:
            iteration += 1
            
            # Adaptive cooling rate based on progress
            if iteration < self.max_iter * 0.2:
                t_cool = 0.99  # Very slow cooling at the beginning
            elif stagnation_count > 50:
                t_cool = 0.85  # Faster cooling if badly stagnated
            elif stagnation_count > 20:
                t_cool = 0.95  # Moderate cooling if slightly stagnated
            else:
                t_cool = 0.98  # Slow cooling with good progress
            
            # Generate a neighbor solution using adaptive operator selection
            new_solution, operator = self.generate_neighbor(current_solution)
            
            # Verify solution validity
            valid_solution = self.problem.check_valid_solution(new_solution)
            
            # If we get too many consecutive invalid solutions, try a different approach
            if not valid_solution:
                consecutive_invalid += 1
                if consecutive_invalid > 5:
                    new_solution = self.repair_solution(new_solution)
                    valid_solution = self.problem.check_valid_solution(new_solution)
                    consecutive_invalid = 0 if valid_solution else consecutive_invalid
            else:
                consecutive_invalid = 0
            
            self.history['Valid Solution'].append(1 if valid_solution else 0)
            
            # Calculate improvement
            new_fitness = new_solution.get_tour_length()
            current_fitness = current_solution.get_tour_length()
            delta = new_fitness - current_fitness
            
            # Determine whether to accept the new solution
            accept = False
            accept_prob = 0.0
            
            if delta < 0 and valid_solution:  # Improvement and valid
                accept = True
                self.operator_success[operator] += 1
                stagnation_count = 0
            elif valid_solution:  # Not an improvement but valid
                # Calculate acceptance probability
                accept_prob = math.exp(-delta / t_current)
                if len(self.history['Accept Probability']) < self.max_iter:
                    self.history['Accept Probability'].append(accept_prob)
                if random.random() < accept_prob:
                    accept = True
                stagnation_count += 1
            else:  # Invalid solution - try repairing if it would be a good move
                if delta < 0:  # Would have been an improvement if valid
                    repaired_solution = self.repair_solution(new_solution)
                    if self.problem.check_valid_solution(repaired_solution):
                        new_solution = repaired_solution
                        new_fitness = new_solution.get_tour_length()
                        delta = new_fitness - current_fitness
                        if delta < 0:
                            accept = True
                            stagnation_count = 0
            
            if accept:
                current_solution = new_solution
                current_fitness = new_fitness
                
                # Update best solution if needed
                if current_fitness < best_fitness and valid_solution:
                    best_solution = deepcopy(current_solution)
                    best_fitness = current_fitness
                    stagnation_count = 0
                    if verbose:
                        print(f"New best: {best_fitness:.2f} at iteration {iteration}")
            
            # Apply diversification strategies based on search state
            if stagnation_count >= max_stagnation:
                # Strong diversification
                if stagnation_count >= max_stagnation * 2:
                    if verbose:
                        print(f"Strong diversification at iteration {iteration}")
                    current_solution = self.strong_diversification(best_solution)
                    t_current = self.initial_temp * 0.7  # Strong reheat
                    stagnation_count = 0
                # Regular reheat
                else:
                    if verbose:
                        print(f"Reheating at iteration {iteration}, best fitness: {best_fitness:.2f}")
                    t_current = self.initial_temp * 0.4  # Regular reheat
                    current_solution = deepcopy(best_solution)  # Restart from best solution
                    stagnation_count = 0
            
            # Track history for plotting
            if len(self.history['Temperature']) < self.max_iter:
                self.history['Temperature'].append(t_current)
            if len(self.history['Current Fitness']) < self.max_iter:
                self.history['Current Fitness'].append(current_fitness)
            if len(self.history['Best Fitness']) < self.max_iter:
                self.history['Best Fitness'].append(best_fitness)
            
            if verbose and iteration % 10 == 0:
                print(f"Iteration {iteration}: Temp = {t_current:.4f}, Current = {current_fitness:.2f}, Best = {best_fitness:.2f}, Valid = {valid_solution}")
            
            # Cool down the temperature
            t_current *= t_cool
            t_current = max(t_current, self.min_temp)
        
        # Final intensive local search on the best solution with validity check
        best_solution = self.iterated_local_search(best_solution, num_iterations=10)
        
        # Ensure final solution is valid
        if not self.problem.check_valid_solution(best_solution):
            best_solution = self.repair_solution(best_solution)
            # If still invalid, fall back to the best greedy solution
            if not self.problem.check_valid_solution(best_solution):
                best_solution = self.greedy_search.solve(problem, verbose=False)
        
        # Create convergence plot if requested
        if plot_path:
            self.plot_history(plot_path)
        
        return best_solution
    
    def generate_diverse_initial_solutions(self, count: int) -> list:
        """
        Generate a diverse set of initial solutions using various strategies.
        """
        solutions = []
        
        # Get several greedy solutions
        for _ in range(count // 2):
            solution = self.greedy_search.optimize(self.greedy_search.init_solution())
            if self.problem.check_valid_solution(solution):
                solutions.append(solution)
        
        # Get solutions with random perturbations
        for _ in range(count // 4):
            solution = self.greedy_search.optimize(self.greedy_search.init_solution())
            if self.problem.check_valid_solution(solution):
                self.random_perturbation(solution, strength=3)
                solution = self.greedy_search.optimize(solution)
                if self.problem.check_valid_solution(solution):
                    solutions.append(solution)
        
        # Get solutions with energy-focused optimization
        for _ in range(count // 4):
            solution = self.greedy_search.optimize(self.greedy_search.init_solution())
            if self.problem.check_valid_solution(solution):
                self.energy_aware_mutation(solution)
                solution = self.greedy_search.optimize(solution)
                if self.problem.check_valid_solution(solution):
                    solutions.append(solution)
        
        # If we don't have enough valid solutions, add more greedy ones
        while len(solutions) < 5:
            solution = self.greedy_search.optimize(self.greedy_search.init_solution())
            if self.problem.check_valid_solution(solution):
                solutions.append(solution)
        
        return solutions
    
    def random_perturbation(self, solution: Solution, strength: int = 1):
        """
        Apply random perturbations to a solution with given strength.
        """
        for _ in range(strength):
            op = random.choice(['reverse', 'swap', 'three_opt'])
            if op == 'reverse':
                self.reverse(solution)
            elif op == 'swap':
                self.swap(solution)
            elif op == 'three_opt':
                self.three_opt(solution)
                
        # Ensure the solution remains valid
        solution = self.greedy_search.optimize(solution)
    
    def generate_neighbor(self, solution: Solution):
        """
        Generate a neighboring solution using adaptive operator selection.
        """
        # Calculate operator probabilities based on success rates
        total_success = sum(self.operator_success.values())
        if total_success > 0:
            operator_probs = {k: v/total_success for k, v in self.operator_success.items()}
        else:
            operator_probs = {k: 1/len(self.operator_success) for k in self.operator_success}
        
        # Select operator probabilistically (compatible with older Python versions)
        operators = list(operator_probs.keys())
        probabilities = list(operator_probs.values())
        selected_operator = self.weighted_random_choice(operators, probabilities)
        
        # Apply selected operator
        new_solution = deepcopy(solution)
        
        if selected_operator == 'greedy_1':
            self.greedy_1(new_solution)
        elif selected_operator == 'greedy_2':
            self.greedy_2(new_solution)
        elif selected_operator == 'three_opt':
            self.three_opt(new_solution)
        elif selected_operator == 'reverse':
            self.reverse(new_solution)
        elif selected_operator == 'swap':
            self.swap(new_solution)
        elif selected_operator == 'energy_aware':
            self.energy_aware_mutation(new_solution)
        elif selected_operator == 'station_insertion':
            self.station_insertion(new_solution)
        
        # Apply greedy optimization
        new_solution = self.greedy_search.optimize(new_solution)
        
        return new_solution, selected_operator
    
    def repair_solution(self, solution: Solution) -> Solution:
        """
        Attempt to repair an invalid solution.
        """
        # First try: optimize with greedy search
        repaired = deepcopy(solution)
        repaired = self.greedy_search.optimize(repaired)
        
        if self.problem.check_valid_solution(repaired):
            return repaired
        
        # Second try: optimize with greedy search after breaking up the solution
        repaired = deepcopy(solution)
        tours = repaired.get_basic_tours()
        
        # Break up tours that might be too long
        new_tours = []
        for tour in tours:
            if len(tour) > 6:  # Break long tours
                mid = len(tour) // 2
                new_tours.append(tour[:mid])
                new_tours.append(tour[mid:])
            else:
                new_tours.append(tour)
        
        repaired = Solution(new_tours)
        repaired = self.greedy_search.optimize(repaired)
        
        if self.problem.check_valid_solution(repaired):
            return repaired
        
        # Third try: create a fresh greedy solution
        repaired = self.greedy_search.solve(self.problem, verbose=False)
        
        return repaired
    
    def strong_diversification(self, solution: Solution) -> Solution:
        """
        Apply strong diversification to escape deep local optima.
        """
        # Start with a copy of the current best solution
        diversified = deepcopy(solution)
        
        # Get the basic tours
        tours = diversified.get_basic_tours()
        
        # Strategy 1: Shuffle customers between tours
        if random.random() < 0.5 and len(tours) > 1:
            # Collect all customers
            all_customers = []
            for tour in tours:
                all_customers.extend(tour)
            
            # Shuffle them
            random.shuffle(all_customers)
            
            # Reassign to tours based on capacity
            new_tours = []
            current_tour = []
            capacity = 0
            
            for customer in all_customers:
                if capacity + customer.get_demand() <= self.problem.get_capacity():
                    current_tour.append(customer)
                    capacity += customer.get_demand()
                else:
                    new_tours.append(current_tour)
                    current_tour = [customer]
                    capacity = customer.get_demand()
            
            if current_tour:
                new_tours.append(current_tour)
            
            diversified = Solution(new_tours)
        
        # Strategy 2: Merge some tours and split others
        else:
            if len(tours) > 1:
                # Randomly merge tours
                merge_indices = sorted(random.sample(range(len(tours)), min(2, len(tours))))
                merged_tour = []
                
                for i, tour in enumerate(tours):
                    if i in merge_indices:
                        merged_tour.extend(tour)
                    else:
                        if len(tour) > 4:  # Split longer tours
                            mid = len(tour) // 2
                            tours[i] = tour[:mid]  # Replace with first half
                            tours.append(tour[mid:])  # Add second half
                
                # Add the merged tour if it exists
                if merged_tour:
                    tours.append(merged_tour)
                
                diversified = Solution(tours)
        
        # Apply greedy optimization to make it valid
        diversified = self.greedy_search.optimize(diversified)
        
        # Ensure the solution is valid
        if not self.problem.check_valid_solution(diversified):
            diversified = self.repair_solution(diversified)
        
        return diversified
    
    def greedy_1(self, solution: Solution):
        """
        First greedy operator: Exchange customers between different tours.
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
                    
                    # Verify capacity constraints won't be violated
                    current_capacity1 = sum(node.get_demand() for node in tours[tour_idx])
                    current_capacity2 = sum(node.get_demand() for node in tours[near_customer_tour_idx])
                    
                    new_capacity1 = current_capacity1 - customer.get_demand() + near_customer.get_demand()
                    new_capacity2 = current_capacity2 - near_customer.get_demand() + customer.get_demand()
                    
                    if new_capacity1 <= self.problem.get_capacity() and new_capacity2 <= self.problem.get_capacity():
                        # Swap the customers between tours
                        tours[tour_idx][customer_idx] = near_customer
                        tours[near_customer_tour_idx][near_customer_idx] = customer
                        
                        # Update the solution with modified tours
                        solution.set_vehicle_tours(tours)
                        return
    
    def greedy_2(self, solution: Solution):
        """
        Second greedy operator: Move a customer from one tour to another.
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
    
    def energy_aware_mutation(self, solution: Solution):
        """
        Energy-aware mutation operator that focuses on optimizing energy consumption.
        """
        # Get all tours including the complete routes with charging stations
        tours = solution.get_tours()
        
        # Find segments with high energy consumption
        high_energy_segments = []
        
        for t_idx, tour in enumerate(tours):
            for i in range(len(tour)-1):
                from_node = tour[i]
                to_node = tour[i+1]
                energy = self.problem.get_energy_consumption(from_node, to_node)
                
                # Track segments with high energy consumption
                if energy > self.problem.get_battery_capacity() * 0.4:  # More than 40% of battery
                    high_energy_segments.append((t_idx, i, energy))
        
        # Sort by energy consumption (highest first)
        high_energy_segments.sort(key=lambda x: x[2], reverse=True)
        
        # Try to optimize the highest energy segment
        if high_energy_segments:
            t_idx, pos, _ = high_energy_segments[0]
            
            if pos < len(tours[t_idx])-1:
                from_node = tours[t_idx][pos]
                to_node = tours[t_idx][pos+1]
                
                # Try to find a charging station between these nodes
                for station in self.problem.get_all_stations():
                    # Check if adding this station would reduce total energy
                    energy_direct = self.problem.get_energy_consumption(from_node, to_node)
                    energy_with_station = (self.problem.get_energy_consumption(from_node, station) + 
                                           self.problem.get_energy_consumption(station, to_node))
                    
                    if energy_with_station < energy_direct * 1.3:  # Allow some detour
                        # Insert the charging station
                        tours[t_idx].insert(pos+1, station)
                        solution.set_vehicle_tours(tours)
                        return
        
        # If no high energy segment was found or optimized, try general energy optimization
        # Find a tour that doesn't end with full battery
        for t_idx, tour in enumerate(tours):
            if len(tour) >= 2:
                second_last = tour[-2]
                last = tour[-1]
                
                # If not ending at a charging station or depot
                if not last.is_charging_station():
                    # Find nearest charging station
                    nearest_station = None
                    min_detour = float('inf')
                    
                    for station in self.problem.get_all_stations():
                        detour = (self.problem.get_distance(second_last, station) + 
                                  self.problem.get_distance(station, last) - 
                                  self.problem.get_distance(second_last, last))
                        
                        if detour < min_detour:
                            min_detour = detour
                            nearest_station = station
                    
                    # Insert if the detour is reasonable
                    if nearest_station and min_detour < self.problem.get_distance(second_last, last) * 0.5:
                        tours[t_idx].insert(len(tours[t_idx])-1, nearest_station)
                        solution.set_vehicle_tours(tours)
                        return
    
    def station_insertion(self, solution: Solution):
        """
        Insert charging stations at strategic locations to optimize energy usage.
        """
        # Get all tours
        tours = solution.get_tours()
        
        for t_idx, tour in enumerate(tours):
            # Skip very short tours
            if len(tour) < 3:
                continue
            
            # Calculate current energy consumption for the tour
            energy_remaining = self.problem.get_battery_capacity()
            low_energy_points = []
            
            for i in range(len(tour)-1):
                from_node = tour[i]
                to_node = tour[i+1]
                
                # Reset energy at charging stations or depot
                if from_node.is_charging_station():
                    energy_remaining = self.problem.get_battery_capacity()
                
                # Consume energy
                energy_consumption = self.problem.get_energy_consumption(from_node, to_node)
                energy_remaining -= energy_consumption
                
                # Identify points with low energy
                if energy_remaining < self.problem.get_battery_capacity() * 0.3:  # Below 30%
                    low_energy_points.append((i, energy_remaining))
                
                # If we would run out of energy, this is invalid
                if energy_remaining < 0:
                    break
            
            # If we found low energy points, try to insert a charging station
            if low_energy_points:
                # Sort by lowest energy remaining
                low_energy_points.sort(key=lambda x: x[1])
                
                for pos, _ in low_energy_points:
                    if pos < len(tour)-1:
                        from_node = tour[pos]
                        to_node = tour[pos+1]
                        
                        # Find nearest charging station
                        nearest_station = None
                        min_detour = float('inf')
                        
                        for station in self.problem.get_all_stations():
                            detour = (self.problem.get_distance(from_node, station) + 
                                      self.problem.get_distance(station, to_node) - 
                                      self.problem.get_distance(from_node, to_node))
                            
                            if detour < min_detour:
                                min_detour = detour
                                nearest_station = station
                        
                        # Insert if the detour is reasonable
                        if nearest_station and min_detour < self.problem.get_distance(from_node, to_node) * 0.8:
                            tours[t_idx].insert(pos+1, nearest_station)
                            solution.set_vehicle_tours(tours)
                            return
    
    def three_opt(self, solution: Solution):
        """
        3-opt local search operation with validity checks.
        """
        tours = solution.get_basic_tours()
        
        # Skip if no tours
        if not tours:
            return
            
        # Select a random tour
        tour_idx = random.randint(0, len(tours) - 1)
        tour = tours[tour_idx]
        
        # Skip if tour is too short
        if len(tour) < 4:
            return
        
        # Select three random indices
        n = len(tour)
        indices = sorted([random.randint(0, n-1) for _ in range(3)])
        
        # Ensure we have 3 distinct indices
        if len(set(indices)) < 3:
            i = 0
            j = min(n//3, n-1)
            k = min(2*n//3, n-1)
        else:
            i, j, k = indices
        
        # Get the segments
        a = tour[:i]
        b = tour[i:j]
        c = tour[j:k]
        d = tour[k:]
        
        # Try all combinations of segments and select the best
        options = [
            a + b + c + d,  # Original
            a + b[::-1] + c + d,  # Reverse b
            a + b + c[::-1] + d,  # Reverse c
            a + b[::-1] + c[::-1] + d,  # Reverse b and c
            a + c + b + d,  # Swap b and c
            a + c[::-1] + b + d,  # Swap b and c, reverse c
            a + c + b[::-1] + d,  # Swap b and c, reverse b
            a + c[::-1] + b[::-1] + d,  # Swap b and c, reverse both
        ]
        
        # Evaluate all options
        best_option = None
        best_length = float('inf')
        
        for option in options:
            # Skip empty tours
            if not option:
                continue
                
            # Check capacity constraint
            total_demand = sum(node.get_demand() for node in option)
            if total_demand > self.problem.get_capacity():
                continue
                
            temp_tours = tours.copy()
            temp_tours[tour_idx] = option
            temp_solution = Solution(temp_tours)
            
            # First quick check if the basic tours is better before calling optimize
            basic_length = self.problem.calculate_tour_length(temp_solution)
            
            if basic_length < best_length:
                # Only fully optimize the most promising candidates
                temp_solution = self.greedy_search.optimize(temp_solution)
                length = temp_solution.get_tour_length()
                
                if length < best_length and self.problem.check_valid_solution(temp_solution):
                    best_length = length
                    best_option = option
        
        # Update the tour
        if best_option:
            tours[tour_idx] = best_option
            solution.set_vehicle_tours(tours)

    def reverse(self, solution: Solution):
        """
        Reverse a segment of a random tour with validity check.
        """
        tours = solution.get_basic_tours()
        
        # Skip if no tours
        if not tours:
            return
            
        # Select a random tour
        tour_idx = random.randint(0, len(tours) - 1)
        tour = tours[tour_idx]
        
        # Skip if tour is too short
        if len(tour) < 2:
            return
        
        # Select a random segment
        n = len(tour)
        i = random.randint(0, n-2)
        j = random.randint(i+1, n-1)
        
        # Create the reversed segment
        reversed_tour = tour[:i] + list(reversed(tour[i:j+1])) + tour[j+1:]
        
        # Check capacity constraint (should be the same, but verify for safety)
        total_demand = sum(node.get_demand() for node in reversed_tour)
        if total_demand <= self.problem.get_capacity():
            tours[tour_idx] = reversed_tour
            solution.set_vehicle_tours(tours)

    def swap(self, solution: Solution):
        """
        Swap two random nodes in a random tour with validity check.
        """
        tours = solution.get_basic_tours()
        
        # Skip if no tours
        if not tours:
            return
            
        # Select a random tour
        tour_idx = random.randint(0, len(tours) - 1)
        tour = tours[tour_idx]
        
        # Skip if tour is too short
        if len(tour) < 2:
            return
        
        # Select two random nodes
        n = len(tour)
        i = random.randint(0, n-1)
        j = random.randint(0, n-1)
        while j == i:
            j = random.randint(0, n-1)
        
        # Swap the nodes
        tour[i], tour[j] = tour[j], tour[i]
        
        # Capacity should be the same, but verify for safety
        total_demand = sum(node.get_demand() for node in tour)
        if total_demand <= self.problem.get_capacity():
            tours[tour_idx] = tour
            solution.set_vehicle_tours(tours)
    
    def intensive_local_search(self, solution: Solution) -> Solution:
        """
        Apply intensive local search to the final solution with strong validation.
        """
        improved = True
        current_solution = deepcopy(solution)
        best_solution = deepcopy(solution)
        best_fitness = solution.get_tour_length()
        
        # Apply multiple operators repeatedly until no improvement
        iteration = 0
        max_iterations = 20  # Limit iterations to avoid infinite loops
        
        while improved and iteration < max_iterations:
            iteration += 1
            improved = False
            
            # Try each operator
            for operator in ['three_opt', 'reverse', 'swap', 'greedy_1', 'greedy_2', 'energy_aware', 'station_insertion']:
                new_solution = deepcopy(current_solution)
                
                if operator == 'three_opt':
                    self.three_opt(new_solution)
                elif operator == 'reverse':
                    self.reverse(new_solution)
                elif operator == 'swap':
                    self.swap(new_solution)
                elif operator == 'greedy_1':
                    self.greedy_1(new_solution)
                elif operator == 'greedy_2':
                    self.greedy_2(new_solution)
                elif operator == 'energy_aware':
                    self.energy_aware_mutation(new_solution)
                elif operator == 'station_insertion':
                    self.station_insertion(new_solution)
                
                # Apply greedy optimization
                new_solution = self.greedy_search.optimize(new_solution)
                
                # Only accept valid solutions
                if self.problem.check_valid_solution(new_solution):
                    new_fitness = new_solution.get_tour_length()
                    
                    # Update if improved
                    if new_fitness < best_fitness:
                        best_solution = deepcopy(new_solution)
                        best_fitness = new_fitness
                        improved = True
            
            # Update current solution
            if improved:
                current_solution = deepcopy(best_solution)
        
        return best_solution
    
    def iterated_local_search(self, solution: Solution, num_iterations=10) -> Solution:
        """
        Apply iterated local search with perturbation to escape local optima.
        """
        best_solution = deepcopy(solution)
        best_fitness = solution.get_tour_length()
        
        for i in range(num_iterations):
            # Start from the best solution
            current = deepcopy(best_solution)
            
            # Apply perturbation
            perturbation_strength = 1 + i // 3  # Increase perturbation strength over time
            self.random_perturbation(current, strength=perturbation_strength)
            
            # Optimize
            current = self.greedy_search.optimize(current)
            
            # Apply local search
            current = self.intensive_local_search(current)
            
            # Check if better and valid
            if (current.get_tour_length() < best_fitness and 
                self.problem.check_valid_solution(current)):
                best_solution = deepcopy(current)
                best_fitness = current.get_tour_length()
        
        return best_solution
    
    def find_nearest_station(self, node):
        """
        Find the nearest charging station to a node.
        """
        min_distance = float('inf')
        nearest_station = None
        
        for station in self.problem.get_all_stations():
            distance = self.problem.get_distance(node, station)
            if distance < min_distance:
                min_distance = distance
                nearest_station = station
        
        return nearest_station
    
    def plot_history(self, path):
        """
        Plot the convergence history of the algorithm with more robust handling of arrays.
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
        if 'Current Fitness' in plot_data:
            ax1.plot(df['Current Fitness'], label='Current Fitness', alpha=0.7)
        ax1.plot(df['Best Fitness'], label='Best Fitness', linewidth=2)
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
        
        # Plot solution validity
        if 'Valid Solution' in plot_data:
            # Calculate a moving average for visibility
            window_size = 10
            valid_pct = df['Valid Solution'].rolling(window=window_size, min_periods=1).mean()
            
            ax3.plot(valid_pct, label='Valid Solution %', color='green')
            ax3.set_xlabel('Iteration')
            ax3.set_ylabel('Validity Rate')
            ax3.set_title('Solution Validity Rate (Moving Average)')
            ax3.set_ylim(0, 1.1)
            ax3.grid(True)
        
        plt.tight_layout()
        plt.savefig(path)
        plt.close()