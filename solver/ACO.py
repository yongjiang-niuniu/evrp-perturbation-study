import random
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from copy import deepcopy
from solution import Solution
from problem import Problem
from node import Node
from greedy import GreedySearch
from time import time
from bisect import bisect_right
import logging

class AntColonyOptimization:
    """
    Optimized Ant Colony Optimization for the Electric Vehicle Routing Problem (EVRP).
    Integrates greedy search, simulated annealing, and advanced pheromone management strategies.
    """
    
    def __init__(self, num_ants=60, generations=500, alpha=0.8, beta=4.0, 
                 rho=0.1, q=100, perturb_rate=0.05, local_search_freq=2,
                 elite_count=5, k_nearest=20, intensive_local_search=True, seed=42):
        """
        Initialize ACO parameters.

        Args:
            num_ants: Number of ants in the colony
            generations: Maximum number of iterations
            alpha: Weight of pheromone influence
            beta: Weight of heuristic influence (distance)
            rho: Pheromone evaporation rate
            q: Constant factor for pheromone deposit
            perturb_rate: Rate to perturb pheromones
            local_search_freq: Frequency of local search application
            elite_count: Number of elite ants
            k_nearest: Number of nearest neighbors to consider for each node
            intensive_local_search: Whether to apply intensive local search
            seed: Random seed
        """
        if seed is not None:
            np.random.seed(seed)
            random.seed(seed)
            
        self.num_ants = num_ants
        self.generations = generations
        self.alpha = alpha
        self.beta = beta
        self.rho = rho
        self.q = q
        self.perturb_rate = perturb_rate
        self.tau_max = 5.0  # Maximum pheromone level
        self.tau_min = 0.01  # Minimum pheromone level
        self.local_search_freq = local_search_freq
        self.elite_count = elite_count
        self.k_nearest = k_nearest
        self.intensive_local_search = intensive_local_search
        
        self.history = {
            'Mean Fitness': [],
            'Best Fitness': [],
            'Time': []
        }
        
        self.gs = GreedySearch()  # Use greedy search for local optimization
        
    def set_problem(self, problem: Problem):
        """Set the EVRP problem instance and initialize necessary structures."""
        self.problem = problem
        self.gs.set_problem(problem)
        self.num_nodes = problem.get_problem_size()
        self.depot = problem.get_depot()
        self.depot_id = problem.get_depot_id()
        self.customers = problem.get_all_customers()
        self.stations = problem.get_all_stations() + [self.depot]
        
        # Calculate distance matrix between nodes
        self.distances = np.zeros((self.num_nodes, self.num_nodes))
        for i in range(self.num_nodes):
            for j in range(self.num_nodes):
                if i != j:
                    node_i = problem.get_node_from_id(i)
                    node_j = problem.get_node_from_id(j)
                    self.distances[i][j] = node_i.distance(node_j)
        
        # Precompute K nearest neighbors for each node
        self.nearest_neighbors = {}
        for i in range(self.num_nodes):
            dist_to_i = [(j, self.distances[i][j]) for j in range(self.num_nodes) if j != i]
            sorted_neighbors = sorted(dist_to_i, key=lambda x: x[1])
            self.nearest_neighbors[i] = [j for j, _ in sorted_neighbors[:self.k_nearest]]
        
        # Initialize pheromone matrix and delta pheromones
        self.pheromones = np.ones((self.num_nodes, self.num_nodes)) * self.tau_max * 0.5
        self.delta_pheromones = np.zeros((self.num_nodes, self.num_nodes))
        
        # Initialize ant solutions
        self.ant_solutions = [Solution() for _ in range(self.num_ants)]
        
        # Create initial best solution using greedy algorithm
        initial_solution = self.gs.solve(problem, verbose=False)
        self.best_solution = deepcopy(initial_solution)
        
        # Compute visibility matrix (heuristic information)
        self.visibility = np.zeros((self.num_nodes, self.num_nodes))
        for i in range(self.num_nodes):
            for j in range(self.num_nodes):
                if i != j and self.distances[i][j] > 0:
                    self.visibility[i][j] = 1.0 / self.distances[i][j]
                else:
                    self.visibility[i][j] = 0.001  # Avoid division by zero
        
        # Additional node information
        self.customer_demands = {}
        self.node_types = {}
        for node in self.customers:
            self.customer_demands[node.get_id()] = node.get_demand()
            self.node_types[node.get_id()] = 'C'
        
        for node in self.stations:
            self.node_types[node.get_id()] = 'S' if node.is_charging_station() else 'D'
        
    def phi(self, from_node_id, to_node_id, visited, capacity_remaining=None, energy_remaining=None):
        """
        Calculate the probability of selecting an edge based on pheromone and heuristic.
        
        Args:
            from_node_id: ID of the starting node
            to_node_id: ID of the target node
            visited: Dictionary of visited nodes
            capacity_remaining: Remaining capacity (for additional heuristics)
            energy_remaining: Remaining energy (for additional heuristics)
            
        Returns:
            float: Probability (unnormalized) of selecting this edge
        """
        # Basic pheromone and distance heuristic
        tau = self.pheromones[from_node_id][to_node_id]
        eta = self.visibility[from_node_id][to_node_id]
        
        # Advanced heuristic: Consider customer demand and remaining capacity
        if capacity_remaining is not None and self.node_types.get(to_node_id) == 'C':
            demand = self.customer_demands.get(to_node_id, 0)
            if demand > 0:
                # Prefer customers with smaller demand when capacity is limited
                demand_factor = 1.0 - (demand / capacity_remaining) ** 0.5
                eta *= (1.0 + demand_factor)
        
        # Advanced heuristic: Consider energy constraints
        if energy_remaining is not None and self.node_types.get(to_node_id) == 'C':
            from_node = self.problem.get_node_from_id(from_node_id)
            to_node = self.problem.get_node_from_id(to_node_id)
            energy_needed = self.problem.get_energy_consumption(from_node, to_node)
            
            # Penalize choices that would consume too much energy
            if energy_needed > 0.8 * energy_remaining:
                eta *= 0.8
        
        # Advanced heuristic: Add node type preferences
        if self.node_types.get(to_node_id) == 'S' and self.node_types.get(from_node_id) == 'C':
            # Be selective about visiting charging stations unless truly needed
            eta *= 0.7
        
        # Calculate combined influence
        return (tau ** self.alpha) * (eta ** self.beta)
    
    def select_next_node(self, current_node_id, available_nodes, visited, energy_remaining=None, capacity_remaining=None):
        """
        Select the next node using probabilistic selection based on pheromones.
        
        Args:
            current_node_id: Current node ID
            available_nodes: List of available node IDs
            visited: Dictionary of visited nodes
            energy_remaining: Remaining energy
            capacity_remaining: Remaining capacity
            
        Returns:
            int: ID of the selected next node
        """
        if not available_nodes:
            return self.depot_id
        
        # Only consider K nearest neighbors for efficiency and quality
        nearest = [n for n in self.nearest_neighbors.get(current_node_id, []) 
                  if n in available_nodes]
        
        # If no neighbors are in the available list, use all available nodes
        candidates = nearest if nearest else available_nodes
        
        # Calculate probabilities for all available nodes
        probabilities = []
        for node_id in candidates:
            prob = self.phi(current_node_id, node_id, visited, capacity_remaining, energy_remaining)
            probabilities.append(prob)
        
        # Normalize probabilities
        sum_prob = sum(probabilities)
        if sum_prob == 0:
            # If all probabilities are zero, choose randomly
            return random.choice(candidates)
        
        probabilities = [p / sum_prob for p in probabilities]
        
        # Apply roulette wheel selection
        cumulative_probs = [sum(probabilities[:i+1]) for i in range(len(probabilities))]
        r = random.random()
        idx = bisect_right(cumulative_probs, r)
        if idx >= len(candidates):
            idx = len(candidates) - 1
        
        return candidates[idx]
    
    def construct_route(self, ant_index):
        """
        Construct a route for an ant using ACO principles.
        
        Args:
            ant_index: Index of the ant in the colony
            
        Returns:
            bool: True if a valid route was constructed, False otherwise
        """
        # Initialize route with depot
        route = [self.depot]
        visited = {self.depot_id: True}
        
        # Get customer nodes
        customer_ids = self.problem.get_customer_ids()
        unvisited_customers = list(customer_ids)
        
        # Shuffle for diversity
        random.shuffle(unvisited_customers)
        
        # Initialize energy and capacity
        energy = self.problem.get_battery_capacity()
        capacity = self.problem.get_capacity()
        
        max_tries = 3  # Maximum number of tries, to avoid infinite loops
        try_count = 0
        
        # Keep constructing route until all customers are visited
        while unvisited_customers and try_count < max_tries:
            current_node = route[-1]
            current_node_id = current_node.get_id()
            
            # Filter available nodes based on capacity constraint
            available_nodes = []
            for node_id in unvisited_customers:
                node = self.problem.get_node_from_id(node_id)
                if capacity >= node.get_demand():
                    available_nodes.append(node_id)
            
            # If no nodes satisfy capacity, return to depot
            if not available_nodes:
                route.append(self.depot)
                energy = self.problem.get_battery_capacity()
                capacity = self.problem.get_capacity()
                continue
            
            # Select next node
            next_node_id = self.select_next_node(current_node_id, available_nodes, visited, 
                                               energy, capacity)
            next_node = self.problem.get_node_from_id(next_node_id)
            
            # Check energy constraint
            energy_needed = self.problem.get_energy_consumption(current_node, next_node)
            
            if energy_needed > energy:
                # Find best charging station
                best_station = self.find_best_charging_station(current_node, next_node, energy)
                
                if best_station is None:
                    # If no reachable station, go back to depot
                    route.append(self.depot)
                    energy = self.problem.get_battery_capacity()
                    capacity = self.problem.get_capacity()
                    continue
                
                # Add charging station to route
                route.append(best_station)
                energy = self.problem.get_battery_capacity()
                # Decrement energy consumed to reach next node from station
                energy -= self.problem.get_energy_consumption(best_station, next_node)
            else:
                # Directly decrement energy
                energy -= energy_needed
            
            # Add selected node to route
            route.append(next_node)
            unvisited_customers.remove(next_node_id)
            visited[next_node_id] = True
            
            # Update capacity
            capacity -= next_node.get_demand()
            
            # Consider returning to depot if capacity is running low
            if capacity < 0.1 * self.problem.get_capacity() and len(unvisited_customers) > 3:
                route.append(self.depot)
                energy = self.problem.get_battery_capacity()
                capacity = self.problem.get_capacity()
        
        # Complete the route by returning to depot
        if route[-1].get_id() != self.depot_id:
            route.append(self.depot)
        
        # If not all customers were visited, increment try count
        if unvisited_customers:
            try_count += 1
            if try_count < max_tries:
                # Retry
                return self.construct_route(ant_index)
            else:
                # Construction failed
                return False
        
        # Convert route to a Solution object
        solution = self.route_to_solution(route)
        
        # Apply local search optimization
        solution = self.optimize_solution(solution)
        
        self.ant_solutions[ant_index] = solution
        
        # Check if solution is valid
        is_valid = self.problem.check_valid_solution(solution)
        if not is_valid and hasattr(logging, 'warning'):
            logging.warning(f"Invalid solution for ant {ant_index}")
        
        return is_valid
    
    def find_best_charging_station(self, current_node, next_node, energy):
        """
        Find the best charging station considering energy constraints and future travel.
        
        Args:
            current_node: Current node
            next_node: Next planned node
            energy: Remaining energy
            
        Returns:
            Node: Best charging station or None if none found
        """
        stations = self.problem.get_station_ids()
        best_station = None
        min_detour = float('inf')
        
        direct_dist = current_node.distance(next_node)
        
        for station_id in stations:
            station = self.problem.get_node_from_id(station_id)
            energy_to_station = self.problem.get_energy_consumption(current_node, station)
            
            # Ensure there's enough energy to reach the station
            if energy_to_station <= energy:
                # Calculate detour cost: (current to station distance + station to next node distance) - direct distance
                detour = current_node.distance(station) + station.distance(next_node) - direct_dist
                
                if detour < min_detour:
                    min_detour = detour
                    best_station = station
        
        # If no station found, consider depot as a charging station
        if best_station is None and self.problem.get_energy_consumption(current_node, self.depot) <= energy:
            best_station = self.depot
        
        return best_station
    
    def route_to_solution(self, route):
        """
        Convert a route to a Solution object by identifying separate tours.
        
        Args:
            route: List of nodes representing the complete route
            
        Returns:
            Solution: Solution object containing separate tours
        """
        solution = Solution()
        
        # Split route into separate tours at depot visits
        current_tour = []
        for i, node in enumerate(route):
            if node.is_depot():
                if i > 0 and current_tour:  # Avoid adding empty tours
                    solution.add_tour(current_tour)
                    current_tour = []
            else:
                current_tour.append(node)
        
        # Add last tour if not empty
        if current_tour:
            solution.add_tour(current_tour)
        
        return solution
    
    def optimize_solution(self, solution):
        """
        Apply local search optimization to improve solution quality.
        
        Args:
            solution: Initial solution
            
        Returns:
            Solution: Optimized solution
        """
        # Apply greedy search optimization
        solution = self.gs.optimize(solution)
        
        # Add advanced local search: two different optimization strategies
        if random.random() < 0.3:  # 30% chance of applying more advanced optimization
            # Exchange customers to optimize individual tours
            solution = self.exchange_optimization(solution)
        elif random.random() < 0.3:  # 30% chance
            # Redistribute customers to balance tours
            solution = self.redistribution_optimization(solution)
        
        # If intensive local search is enabled, always apply 2-opt
        if self.intensive_local_search:
            solution = self.intensive_2opt(solution)
        
        # Recalculate total tour length
        solution.set_tour_length(self.problem.calculate_tour_length(solution))
        return solution
    
    def exchange_optimization(self, solution):
        """
        Optimize individual tours by swapping customers within the same tour.
        
        Args:
            solution: Initial solution
            
        Returns:
            Solution: Optimized solution
        """
        tours = solution.get_tours()
        for i, tour in enumerate(tours):
            # Only consider tours with multiple customers
            if len(tour) < 3:
                continue
                
            # Try all possible 2-opt swaps
            improved = True
            while improved:
                improved = False
                best_delta = 0
                best_swap = None
                
                # Consider all possible customer pairs
                for j in range(len(tour)):
                    for k in range(j+2, len(tour)):
                        if j == 0 and k == len(tour) - 1:
                            continue  # Skip first-last swap
                        
                        # Calculate length change after swap
                        if j > 0:
                            before_j = tour[j-1]
                        else:
                            before_j = self.depot
                            
                        if k < len(tour) - 1:
                            after_k = tour[k+1]
                        else:
                            after_k = self.depot
                        
                        current_cost = (before_j.distance(tour[j]) + 
                                        tour[k].distance(after_k))
                        new_cost = (before_j.distance(tour[k]) + 
                                    tour[j].distance(after_k))
                        delta = current_cost - new_cost
                        
                        if delta > best_delta:
                            best_delta = delta
                            best_swap = (j, k)
                
                # If improvement found, execute the swap
                if best_delta > 0 and best_swap:
                    j, k = best_swap
                    # Reverse the sub-tour between j and k
                    tour[j:k+1] = reversed(tour[j:k+1])
                    improved = True
        
        solution.set_vehicle_tours(tours)
        return solution
    
    def intensive_2opt(self, solution):
        """
        Apply an intensive 2-opt local search to all tours.
        
        Args:
            solution: Initial solution
            
        Returns:
            Solution: Optimized solution
        """
        tours = solution.get_tours()
        for i, tour in enumerate(tours):
            # Skip very short tours
            if len(tour) < 3:
                continue
            
            # Add depot to beginning and end for evaluation
            full_tour = [self.depot] + tour + [self.depot]
            best_tour = full_tour[:]
            best_length = sum(full_tour[j].distance(full_tour[j+1]) for j in range(len(full_tour)-1))
            
            # Multiple iterations of improvement
            for _ in range(3):  # Try 3 iterations
                improved = False
                for j in range(1, len(full_tour)-2):
                    for k in range(j+1, len(full_tour)-1):
                        # Skip if j and k are adjacent
                        if k == j + 1:
                            continue
                            
                        # Create new tour by reversing segment j to k
                        new_tour = full_tour[:]
                        new_tour[j:k+1] = reversed(new_tour[j:k+1])
                        
                        # Calculate new length
                        new_length = sum(new_tour[m].distance(new_tour[m+1]) for m in range(len(new_tour)-1))
                        
                        # Update if improved
                        if new_length < best_length:
                            best_length = new_length
                            best_tour = new_tour[:]
                            improved = True
                
                # Update tour if improved
                if improved:
                    full_tour = best_tour[:]
                else:
                    break
            
            # Update the tour (remove depot)
            tours[i] = best_tour[1:-1]
        
        solution.set_vehicle_tours(tours)
        return solution
    
    def redistribution_optimization(self, solution):
        """
        Optimize load balancing by redistributing customers between tours.
        
        Args:
            solution: Initial solution
            
        Returns:
            Solution: Optimized solution
        """
        solution.set_tour_index()
        tours = solution.get_tours()
        
        # If only one tour, no redistribution possible
        if len(tours) <= 1:
            return solution
        
        # Calculate current load for each tour
        tour_loads = []
        for i, tour in enumerate(tours):
            load = sum(node.get_demand() for node in tour if hasattr(node, 'get_demand'))
            tour_loads.append((i, load))
        
        # Sort tours by load
        tour_loads.sort(key=lambda x: x[1], reverse=True)
        
        # Try to move customers from highest load tour to lowest load tour
        for attempt in range(3):  # Limit attempts
            if len(tour_loads) < 2:
                break
                
            high_idx, high_load = tour_loads[0]
            low_idx, low_load = tour_loads[-1]
            
            # If load difference is small, no need to balance
            if high_load - low_load < 0.1 * self.problem.get_capacity():
                break
            
            # Look for suitable customers in high load tour
            high_tour = tours[high_idx]
            candidates = []
            
            for i, node in enumerate(high_tour):
                if node.is_customer():
                    demand = node.get_demand()
                    # Ensure move won't exceed target tour's capacity
                    if low_load + demand <= self.problem.get_capacity():
                        candidates.append((i, node, demand))
            
            # If no suitable candidates, try next pair of tours
            if not candidates:
                tour_loads.pop(0)  # Remove highest load tour
                continue
            
            # Choose customer with smallest demand to maximize redistribution
            candidates.sort(key=lambda x: x[2])
            _, selected_node, demand = candidates[0]
            
            # Remove customer from high load tour
            high_tour = [n for n in high_tour if n.get_id() != selected_node.get_id()]
            tours[high_idx] = high_tour
            
            # Add customer to low load tour
            tours[low_idx].append(selected_node)
            
            # Update load information
            tour_loads[0] = (high_idx, high_load - demand)
            tour_loads[-1] = (low_idx, low_load + demand)
            
            # Resort loads for next iteration
            tour_loads.sort(key=lambda x: x[1], reverse=True)
        
        solution.set_vehicle_tours(tours)
        return solution
    
    def update_pheromones(self):
        """
        Update pheromone levels based on ant solutions.
        Combines rank-based selection and elitist strategy.
        """
        # Rank ants by solution quality
        valid_ants = [ant for ant in self.ant_solutions if self.problem.check_valid_solution(ant)]
        if not valid_ants:
            return
            
        sorted_ants = sorted(valid_ants, key=lambda x: x.get_tour_length())
        
        # Reset delta pheromones
        self.delta_pheromones = np.zeros((self.num_nodes, self.num_nodes))
        
        # Update delta pheromones based on top ants and elitist strategy
        max_ants = min(len(sorted_ants), self.num_ants // 2)
        for k in range(max_ants):
            solution = sorted_ants[k]
            tour_length = solution.get_tour_length()
            
            if tour_length <= 0 or tour_length == float('inf'):
                continue
                
            # Extract all ordered nodes from all tours
            all_nodes = []
            for tour in solution.get_tours():
                # Add depot as start of tour
                all_nodes.append(self.depot)
                all_nodes.extend(tour)
                # Add depot as end of tour
                all_nodes.append(self.depot)
            
            # Add pheromone to edges based on solution quality
            for i in range(len(all_nodes) - 1):
                from_id = all_nodes[i].get_id()
                to_id = all_nodes[i + 1].get_id()
                
                # Higher ranked ants deposit more pheromone
                rank_factor = (self.num_ants - k) / self.num_ants
                deposit = rank_factor * self.q / tour_length
                
                # Extra reward for elite ants
                if k < self.elite_count:
                    deposit *= 2
                
                self.delta_pheromones[from_id][to_id] += deposit
                self.delta_pheromones[to_id][from_id] += deposit  # Symmetric problem
        
        # Extra update with best solution found so far
        if self.best_solution.get_tour_length() < float('inf'):
            best_tour_length = self.best_solution.get_tour_length()
            
            # Extract all nodes from all tours
            all_nodes = []
            for tour in self.best_solution.get_tours():
                all_nodes.append(self.depot)
                all_nodes.extend(tour)
                all_nodes.append(self.depot)
            
            # Add pheromone to edges in best solution
            for i in range(len(all_nodes) - 1):
                from_id = all_nodes[i].get_id()
                to_id = all_nodes[i + 1].get_id()
                
                # Best solution gets extra pheromone
                deposit = self.elite_count * self.q / best_tour_length
                self.delta_pheromones[from_id][to_id] += deposit
                self.delta_pheromones[to_id][from_id] += deposit
        
        # Update pheromone levels using Max-Min Ant System (MMAS) strategy
        for i in range(self.num_nodes):
            for j in range(self.num_nodes):
                self.pheromones[i][j] = (1 - self.rho) * self.pheromones[i][j] + self.delta_pheromones[i][j]
                
                # Ensure pheromone levels stay within bounds
                self.pheromones[i][j] = min(self.pheromones[i][j], self.tau_max)
                self.pheromones[i][j] = max(self.pheromones[i][j], self.tau_min)
    
    def perturb_pheromones(self):
        """
        Perturb pheromone levels to avoid local optima.
        Uses a layered perturbation strategy.
        """
        # Calculate mean pheromone level
        mean_pheromone = np.mean(self.pheromones)
        
        # Apply perturbation
        for i in range(self.num_nodes):
            for j in range(self.num_nodes):
                # Apply different perturbation based on distance from mean
                diff = abs(self.pheromones[i][j] - mean_pheromone)
                
                if diff > 0.5 * (self.tau_max - self.tau_min):
                    # Stronger perturbation for more extreme values
                    perturb = self.perturb_rate * 1.5
                else:
                    # Lighter perturbation for values closer to mean
                    perturb = self.perturb_rate * 0.5
                
                self.pheromones[i][j] = (1 - perturb) * self.pheromones[i][j] + perturb * mean_pheromone
    
    def verify_solution_quality(self, solution):
        """
        Perform extensive validation of the solution to ensure it meets all constraints.
        
        Args:
            solution: Solution to verify
            
        Returns:
            tuple: (is_valid, message)
        """
        # First check using the problem's validation method
        is_valid = self.problem.check_valid_solution(solution, verbose=True)
        if not is_valid:
            return False, "Failed problem validation check"
        
        # Additional validation checks
        tours = solution.get_tours()
        
        # 1. Ensure all customers are visited exactly once
        customer_visits = {}
        for tour in tours:
            for node in tour:
                if node.is_customer():
                    node_id = node.get_id()
                    customer_visits[node_id] = customer_visits.get(node_id, 0) + 1
        
        for customer_id in self.problem.get_customer_ids():
            if customer_id not in customer_visits:
                return False, f"Customer {customer_id} not visited"
            if customer_visits[customer_id] > 1:
                return False, f"Customer {customer_id} visited multiple times"
        
        # 2. Verify energy constraints for each tour
        for tour_idx, tour in enumerate(tours):
            energy = self.problem.get_battery_capacity()
            prev_node = self.depot
            
            for node in tour:
                energy_needed = self.problem.get_energy_consumption(prev_node, node)
                energy -= energy_needed
                
                if energy < 0:
                    return False, f"Energy constraint violated in tour {tour_idx}"
                
                if node.is_charging_station():
                    energy = self.problem.get_battery_capacity()
                
                prev_node = node
            
            # Check return to depot
            energy_needed = self.problem.get_energy_consumption(prev_node, self.depot)
            energy -= energy_needed
            if energy < 0:
                return False, f"Energy constraint violated returning to depot in tour {tour_idx}"
        
        # 3. Verify capacity constraints for each tour
        for tour_idx, tour in enumerate(tours):
            capacity = self.problem.get_capacity()
            
            for node in tour:
                if node.is_customer():
                    capacity -= node.get_demand()
                    if capacity < 0:
                        return False, f"Capacity constraint violated in tour {tour_idx}"
        
        # 4. Check if tour length matches calculated value
        calculated_length = self.problem.calculate_tour_length(solution)
        stored_length = solution.get_tour_length()
        
        if abs(calculated_length - stored_length) > 1e-6:
            return False, f"Tour length mismatch: stored={stored_length}, calculated={calculated_length}"
        
        return True, "Valid solution"
    
    def solve(self, problem: Problem, verbose=False, plot_path=None):
        """
        Run the ACO algorithm to solve the EVRP problem.
        
        Args:
            problem: The EVRP problem instance
            verbose: Whether to print progress information
            plot_path: Path to save convergence plot
            
        Returns:
            Solution: The best solution found
        """
        start_time = time()
        self.set_problem(problem)
        
        # Counters for perturbation and improvement tracking
        stagnation_counter = 0
        perturbation_counter = 0
        best_solution_gen = 0
        
        # Main ACO loop
        for gen in range(self.generations):
            gen_start_time = time()
            
            # Construct routes for all ants
            valid_count = 0
            for ant in range(self.num_ants):
                valid = self.construct_route(ant)
                if valid:
                    valid_count += 1
            
            # Calculate statistics
            valid_solutions = [ant for ant in self.ant_solutions if self.problem.check_valid_solution(ant)]
            
            if valid_solutions:
                mean_fitness = np.mean([ant.get_tour_length() for ant in valid_solutions])
                min_fitness = min([ant.get_tour_length() for ant in valid_solutions])
                
                # Update best solution if improved
                best_ant = min(valid_solutions, key=lambda x: x.get_tour_length())
                if best_ant.get_tour_length() < self.best_solution.get_tour_length():
                    self.best_solution = deepcopy(best_ant)
                    stagnation_counter = 0
                    best_solution_gen = gen
                else:
                    stagnation_counter += 1
            else:
                mean_fitness = float('inf')
                min_fitness = float('inf')
                stagnation_counter += 1
            
            # Update history for plotting
            self.history['Mean Fitness'].append(mean_fitness)
            self.history['Best Fitness'].append(self.best_solution.get_tour_length())
            self.history['Time'].append(time() - start_time)
            
            # Update pheromones
            self.update_pheromones()
            
            # Apply periodic local search to strengthen best solution
            if gen % self.local_search_freq == 0:
                intensified_solution = self.gs.optimize(self.best_solution)
                intensified_solution.set_tour_length(self.problem.calculate_tour_length(intensified_solution))
                if intensified_solution.get_tour_length() < self.best_solution.get_tour_length():
                    self.best_solution = intensified_solution
                    stagnation_counter = 0
                    best_solution_gen = gen
            
            # Apply perturbation if stagnated
            perturbation_counter += 1
            perturbation_threshold = 15 if gen < self.generations // 2 else 10
            if perturbation_counter >= 10 or stagnation_counter >= perturbation_threshold:
                self.perturb_pheromones()
                perturbation_counter = 0
            
            if verbose:
                gen_time = time() - gen_start_time
                print(f"Generation {gen+1}/{self.generations}, Valid ants: {valid_count}/{self.num_ants}, " 
                      f"Mean fitness: {mean_fitness:.2f}, Best fitness: {self.best_solution.get_tour_length():.4f}, "
                      f"Time: {gen_time:.2f}s")
            
            # Optional early stopping if converged
            if stagnation_counter > 50 and gen > self.generations // 2:  # Only stop in second half
                if verbose:
                    print(f"Early stopping at generation {gen+1} due to stagnation")
                break
        
        # Final optimization push - apply intensive local search to best solution
        final_solution = deepcopy(self.best_solution)
        for _ in range(5):  # Try multiple optimization passes
            optimized = self.intensive_2opt(final_solution)
            optimized = self.gs.optimize(optimized)
            optimized.set_tour_length(self.problem.calculate_tour_length(optimized))
            if optimized.get_tour_length() < final_solution.get_tour_length():
                final_solution = optimized
        
        # Use the better of the two solutions
        if final_solution.get_tour_length() < self.best_solution.get_tour_length():
            self.best_solution = final_solution
        
        # Plot convergence if requested
        if plot_path:
            self.plot_history(plot_path)
        
        # Final validation and output
        total_time = time() - start_time
        is_valid, message = self.verify_solution_quality(self.best_solution)
        
        if verbose:
            print(f"ACO completed, best fitness: {self.best_solution.get_tour_length():.4f}, total time: {total_time:.2f}s")
            print(f"Best solution found at generation {best_solution_gen+1}")
            print(f"Solution validity: {is_valid}, {message}")
            
            # Print optimal value if known
            if hasattr(problem, 'optimal_value') and problem.optimal_value is not None:
                gap = (self.best_solution.get_tour_length() - problem.optimal_value) / problem.optimal_value * 100
                print(f"Optimal value: {problem.optimal_value:.4f}, gap: {gap:.2f}%")
            
            if not is_valid:
                print(f"WARNING: Final solution is invalid! Reason: {message}")
        
        return self.best_solution
    def three_opt_optimization(self, solution):
        """
        应用3-opt优化以提高路径质量。
        
        Args:
            solution: 初始解决方案
            
        Returns:
            Solution: 优化后的解决方案
        """
        tours = solution.get_tours()
        
        for tour_idx, tour in enumerate(tours):
            # 只考虑有足够节点的路径
            if len(tour) < 6:  # 3-opt至少需要6个节点才能有效
                continue
            
            # 在开始和结束处添加depot以进行评估
            full_tour = [self.depot] + tour + [self.depot]
            n = len(full_tour)
            
            improved = True
            max_iterations = 5  # 限制迭代次数以避免陷入循环
            iteration = 0
            
            while improved and iteration < max_iterations:
                improved = False
                iteration += 1
                
                # 尝试所有可能的3个边组合来移除
                for i in range(1, n-4):
                    # 限制搜索空间以提高效率
                    max_j = min(i + 10, n-3)
                    for j in range(i+1, max_j):
                        max_k = min(j + 10, n-2)
                        for k in range(j+1, max_k):
                            # 计算当前长度
                            current_length = (
                                full_tour[i-1].distance(full_tour[i]) +
                                full_tour[j-1].distance(full_tour[j]) +
                                full_tour[k-1].distance(full_tour[k])
                            )
                            
                            # 尝试所有可能的重新连接方式
                            # 选项1: (i−1,j), (k−1,i), (j−1,k)
                            new_length1 = (
                                full_tour[i-1].distance(full_tour[j]) +
                                full_tour[k-1].distance(full_tour[i]) +
                                full_tour[j-1].distance(full_tour[k])
                            )
                            
                            # 选项2: (i−1,j), (k−1,j−1), (i,k)
                            new_length2 = (
                                full_tour[i-1].distance(full_tour[j]) +
                                full_tour[k-1].distance(full_tour[j-1]) +
                                full_tour[i].distance(full_tour[k])
                            )
                            
                            # 选项3: (i−1,k−1), (j,i), (j−1,k)
                            new_length3 = (
                                full_tour[i-1].distance(full_tour[k-1]) +
                                full_tour[j].distance(full_tour[i]) +
                                full_tour[j-1].distance(full_tour[k])
                            )
                            
                            # 选项4: (i−1,k−1), (j,k), (j−1,i)
                            new_length4 = (
                                full_tour[i-1].distance(full_tour[k-1]) +
                                full_tour[j].distance(full_tour[k]) +
                                full_tour[j-1].distance(full_tour[i])
                            )
                            
                            # 找到最好的选项
                            best_length = min(new_length1, new_length2, new_length3, new_length4)
                            
                            # 如果最佳选项优于当前选项，则应用它
                            if best_length < current_length:
                                new_tour = None
                                
                                if best_length == new_length1:
                                    # 选项1: (i−1,j), (k−1,i), (j−1,k)
                                    new_tour = (
                                        full_tour[:i] +
                                        full_tour[j:k] +
                                        full_tour[i:j] +
                                        full_tour[k:]
                                    )
                                elif best_length == new_length2:
                                    # 选项2: (i−1,j), (k−1,j−1), (i,k)
                                    new_tour = (
                                        full_tour[:i] +
                                        full_tour[j:k] +
                                        list(reversed(full_tour[i:j])) +
                                        full_tour[k:]
                                    )
                                elif best_length == new_length3:
                                    # 选项3: (i−1,k−1), (j,i), (j−1,k)
                                    new_tour = (
                                        full_tour[:i] +
                                        list(reversed(full_tour[j:k])) +
                                        full_tour[i:j] +
                                        full_tour[k:]
                                    )
                                elif best_length == new_length4:
                                    # 选项4: (i−1,k−1), (j,k), (j−1,i)
                                    new_tour = (
                                        full_tour[:i] +
                                        list(reversed(full_tour[j:k])) +
                                        list(reversed(full_tour[i:j])) +
                                        full_tour[k:]
                                    )
                                
                                if new_tour:
                                    full_tour = new_tour
                                    improved = True
                                    # 如果找到改进，提前终止内部循环
                                    break
                        if improved:
                            break
                    if improved:
                        break
            
            # 更新路径（删除depot）
            tours[tour_idx] = full_tour[1:-1]
        
        solution.set_vehicle_tours(tours)
        return solution
    
    def plot_history(self, path):
        """
        Plot the convergence history.
        
        Args:
            path: Path to save the plot
        """
        plt.figure(figsize=(12, 6))
        
        # Create twin y-axis plot
        ax1 = plt.gca()
        ax2 = ax1.twinx()
        
        # Plot fitness history
        ax1.plot(self.history['Best Fitness'], 'b-', label='Best Fitness', linewidth=2)
        ax1.plot(self.history['Mean Fitness'], 'g--', label='Mean Fitness', alpha=0.7)
        
        # Plot time
        ax2.plot(self.history['Time'], 'r-.', label='Cumulative Time (s)', alpha=0.5)
        
        # Set labels and legend
        ax1.set_xlabel('Generation')
        ax1.set_ylabel('Fitness (Tour Length)')
        ax2.set_ylabel('Time (seconds)')
        
        # Combine legends
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right')
        
        # Set title and grid
        plt.title(f'ACO Convergence Trend ({self.problem.get_name()})')
        ax1.grid(True)
        
        plt.tight_layout()
        plt.savefig(path)
        plt.close()