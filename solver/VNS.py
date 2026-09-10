import time
import random
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from copy import deepcopy

from problem import Problem
from solution import Solution
from greedy import GreedySearch
from logger import logger

class VNS:
    """
    Variable Neighborhood Search (VNS) implementation for solving the
    Electric Vehicle Routing Problem (EVRP).
    
    VNS systematically exploits the idea of neighborhood change to escape from local optima
    by using multiple neighborhood structures during the search process.
    """
    
    def __init__(self, max_iterations=1000, max_time=1800, k_max=4, shake_intensity=3):
        """
        Initialize the VNS algorithm with parameters.
        
        Args:
            max_iterations (int): Maximum number of iterations.
            max_time (int): Maximum runtime in seconds.
            k_max (int): Maximum number of different neighborhood structures.
            shake_intensity (int): Controls the intensity of the shaking phase.
        """
        self.max_iterations = max_iterations
        self.max_time = max_time
        self.k_max = k_max
        self.shake_intensity = shake_intensity
        self.greedy_search = GreedySearch()
        self.history = {
            'Iteration': [],
            'Time': [],
            'Current Cost': [],
            'Best Cost': [],
            'Neighborhood': [],
            'Valid Solution': []
        }
    
    def set_problem(self, problem: Problem):
        """
        Set the problem instance for the algorithm.
        """
        self.problem = problem
        self.greedy_search.set_problem(problem)
        
        # Precompute distance and energy consumption matrices for faster access
        self.depot = problem.get_depot()
        self.customers = problem.get_all_customers()
        self.stations = problem.get_all_stations()
        self.battery_capacity = problem.get_battery_capacity()
        self.capacity = problem.get_capacity()
        
        # Cache the nearest station information for faster access
        self.nearest_stations = {}
        all_nodes = [self.depot] + self.customers + self.stations
        
        for node in all_nodes:
            self.nearest_stations[node.get_id()] = sorted(
                self.stations, 
                key=lambda station: node.distance(station)
            )
    
    def solve(self, problem: Problem, verbose=False, plot_path=None) -> Solution:
        """
        Solve the EVRP using Variable Neighborhood Search.
        
        Args:
            problem (Problem): The EVRP problem instance.
            verbose (bool): Whether to print detailed information.
            plot_path (str): Path to save convergence plots.
            
        Returns:
            Solution: The best-found solution.
        """
        self.set_problem(problem)
        start_time = time.time()
        
        if verbose:
            print(f"Starting VNS solver (max iterations: {self.max_iterations}, max time: {self.max_time}s)...")
        
        # Generate initial solution using greedy search
        current_solution = self.greedy_search.solve(problem, verbose=False)
        best_solution = deepcopy(current_solution)
        
        # Ensure the initial solution is valid
        is_valid = self.problem.check_valid_solution(current_solution)
        if not is_valid and verbose:
            print("Initial solution from greedy search is not valid! Attempting repair...")
            current_solution = self.repair_solution(current_solution)
            best_solution = deepcopy(current_solution)
            if not self.problem.check_valid_solution(current_solution):
                print("Could not repair initial solution. Continuing anyway but results may be poor.")
            else:
                print("Initial solution repaired successfully.")
        
        # Recalculate tour length to ensure accuracy
        current_solution.set_tour_length(self.problem.calculate_tour_length(current_solution))
        best_solution.set_tour_length(current_solution.get_tour_length())
        
        iteration = 0
        k = 1  # Current neighborhood
        
        # Record initial solution
        self.history['Iteration'].append(iteration)
        self.history['Time'].append(0)
        self.history['Current Cost'].append(current_solution.get_tour_length())
        self.history['Best Cost'].append(best_solution.get_tour_length())
        self.history['Neighborhood'].append(k)
        self.history['Valid Solution'].append(1 if is_valid else 0)
        
        if verbose:
            print(f"Initial solution cost: {best_solution.get_tour_length():.2f} (valid: {is_valid})")
        
        # Main VNS loop
        while iteration < self.max_iterations and time.time() - start_time < self.max_time:
            iteration += 1
            
            # 1. Shaking - Generate a solution from the kth neighborhood of current_solution
            shaken_solution = self.shaking(deepcopy(current_solution), k)
            
            # Ensure the shaken solution is valid
            if not self.problem.check_valid_solution(shaken_solution):
                shaken_solution = self.repair_solution(shaken_solution)
                if not self.problem.check_valid_solution(shaken_solution):
                    # If repair fails, use current solution instead
                    shaken_solution = deepcopy(current_solution)
            
            # Recalculate tour length
            shaken_valid = self.problem.check_valid_solution(shaken_solution)
            shaken_solution.set_tour_length(self.problem.calculate_tour_length(shaken_solution))
            
            # 2. Local search - Find local optimum starting from shaken_solution
            local_optimum = self.local_search(deepcopy(shaken_solution))
            
            # Ensure the local optimum is valid
            local_valid = self.problem.check_valid_solution(local_optimum)
            if not local_valid:
                local_optimum = self.repair_solution(local_optimum)
                local_valid = self.problem.check_valid_solution(local_optimum)
            
            # Recalculate tour length
            local_optimum.set_tour_length(self.problem.calculate_tour_length(local_optimum))
            
            # 3. Move or not - Accept new solution if better
            if local_valid and local_optimum.get_tour_length() < current_solution.get_tour_length():
                current_solution = deepcopy(local_optimum)
                k = 1  # Reset neighborhood counter
                
                # Update best solution if improved
                if local_optimum.get_tour_length() < best_solution.get_tour_length():
                    best_solution = deepcopy(local_optimum)
                    
                    if verbose:
                        print(f"Iteration {iteration}: New best solution found with cost {best_solution.get_tour_length():.2f}")
            else:
                # Increase neighborhood counter
                k = (k % self.k_max) + 1
            
            # Double-check solution validity before continuing
            current_valid = self.problem.check_valid_solution(current_solution)
            best_valid = self.problem.check_valid_solution(best_solution)
            
            if not current_valid:
                if verbose:
                    print(f"Warning: Current solution became invalid at iteration {iteration}. Repairing...")
                current_solution = self.repair_solution(current_solution)
                current_valid = self.problem.check_valid_solution(current_solution)
                current_solution.set_tour_length(self.problem.calculate_tour_length(current_solution))
            
            if not best_valid:
                if verbose:
                    print(f"Warning: Best solution became invalid at iteration {iteration}. Repairing...")
                best_solution = self.repair_solution(best_solution)
                best_valid = self.problem.check_valid_solution(best_solution)
                best_solution.set_tour_length(self.problem.calculate_tour_length(best_solution))
                
                # If best solution is now worse than current, update
                if best_valid and current_valid and current_solution.get_tour_length() < best_solution.get_tour_length():
                    best_solution = deepcopy(current_solution)
            
            # Record history
            self.history['Iteration'].append(iteration)
            self.history['Time'].append(time.time() - start_time)
            self.history['Current Cost'].append(current_solution.get_tour_length())
            self.history['Best Cost'].append(best_solution.get_tour_length())
            self.history['Neighborhood'].append(k)
            self.history['Valid Solution'].append(1 if current_valid else 0)
            
            # Periodically print status
            if verbose and iteration % 50 == 0:
                print(f"Iteration {iteration}: Current cost = {current_solution.get_tour_length():.2f} (valid: {current_valid}), " 
                      f"Best cost = {best_solution.get_tour_length():.2f} (valid: {best_valid})")
        
        total_time = time.time() - start_time
        
        if verbose:
            print(f"VNS completed: {iteration} iterations in {total_time:.2f} seconds")
            print(f"Best solution cost: {best_solution.get_tour_length():.2f}")
        
        # Final validity check and repair if needed
        if not self.problem.check_valid_solution(best_solution):
            if verbose:
                print("Warning: Best solution is not valid. Attempting repair...")
            best_solution = self.repair_solution(best_solution)
            
            if self.problem.check_valid_solution(best_solution):
                best_solution.set_tour_length(self.problem.calculate_tour_length(best_solution))
                if verbose:
                    print(f"Repaired solution is valid with cost {best_solution.get_tour_length():.2f}")
            else:
                if verbose:
                    print("Could not repair solution. Falling back to greedy solution.")
                best_solution = self.greedy_search.solve(problem, verbose=False)
        
        # Create convergence plot if requested
        if plot_path:
            self.plot_history(plot_path)
        
        return best_solution
    
    def shaking(self, solution: Solution, k: int) -> Solution:
        """
        Shake the current solution by applying k moves of increasing strength.
        
        Args:
            solution (Solution): The current solution.
            k (int): Neighborhood size parameter.
            
        Returns:
            Solution: A new solution after shaking.
        """
        # Apply k moves with intensity proportional to k
        for _ in range(k * self.shake_intensity):
            # Choose a shaking operator proportional to k
            if k == 1:
                # Light shaking - small moves
                operator = random.choice([
                    self.swap_nodes,
                    self.relocate_node
                ])
            elif k == 2:
                # Medium shaking - medium moves
                operator = random.choice([
                    self.two_opt,
                    self.three_opt,
                    self.relocate_customer_between_routes
                ])
            elif k == 3:
                # Strong shaking - more disruptive moves
                operator = random.choice([
                    self.exchange_segments,
                    # self.shuffle_route_segment
                ])
            else:
                # Very strong shaking - major restructuring
                operator = random.choice([
                    self.reroute_multiple_customers,
                    self.redistribute_routes,
                    self.cross_exchange
                ])
            
            # Apply the selected operator
            shaken = operator(solution)
            
            # Check if valid, otherwise revert 
            if not self.problem.check_valid_solution(shaken):
                # Try to fix the solution
                fixed = self.fix_energy_constraints(shaken)
                if self.problem.check_valid_solution(fixed):
                    shaken = fixed
                else:
                    # If still invalid, don't apply this move
                    continue
            
            # Use the valid shaken solution
            solution = shaken
        
        # Ensure energy and capacity constraints are maintained as a final step
        solution = self.fix_energy_constraints(solution)
        
        # Update tour length - always recalculate to ensure accuracy
        solution.set_tour_length(self.problem.calculate_tour_length(solution))
        
        return solution
    
    def local_search(self, solution: Solution) -> Solution:
        """
        Perform local search to improve the solution.
        
        Args:
            solution (Solution): Initial solution for local search.
            
        Returns:
            Solution: Improved solution after local search.
        """
        # Apply Variable Neighborhood Descent (VND)
        improved = True
        
        while improved:
            improved = False
            
            # Try different neighborhood structures in sequence
            neighborhoods = [
                self.swap_nodes,
                self.relocate_node,
                self.two_opt,
                self.optimize_charging_stations
            ]
            
            for neighborhood in neighborhoods:
                # Apply the neighborhood operator until no improvement
                local_improved = True
                
                while local_improved:
                    new_solution = neighborhood(deepcopy(solution))
                    
                    # Ensure solution is valid
                    valid_solution = self.problem.check_valid_solution(new_solution)
                    if not valid_solution:
                        new_solution = self.fix_energy_constraints(new_solution)
                        valid_solution = self.problem.check_valid_solution(new_solution)
                        if not valid_solution:
                            # Skip invalid solutions
                            local_improved = False
                            continue
                    
                    # Calculate costs
                    solution.set_tour_length(self.problem.calculate_tour_length(solution))
                    new_solution.set_tour_length(self.problem.calculate_tour_length(new_solution))
                    
                    if new_solution.get_tour_length() < solution.get_tour_length():
                        solution = new_solution
                        improved = True
                        local_improved = True
                    else:
                        local_improved = False
        
        return solution
    
    def repair_solution(self, solution: Solution) -> Solution:
        """
        Repair an invalid solution by fixing constraints.
        
        Args:
            solution (Solution): The solution to repair.
            
        Returns:
            Solution: A valid repaired solution.
        """
        # First try to fix energy constraints
        repaired = self.fix_energy_constraints(deepcopy(solution))
        
        # Check if the solution is now valid
        if self.problem.check_valid_solution(repaired):
            repaired.set_tour_length(self.problem.calculate_tour_length(repaired))
            return repaired
        
        # If still invalid, try more aggressive repair
        try:
            # Second attempt: optimize each tour individually
            tours = repaired.get_basic_tours()
            
            for i, tour in enumerate(tours):
                if tour:
                    optimized_tour = self.optimize_single_tour(tour)
                    tours[i] = optimized_tour
            
            # Create a new solution from the optimized tours
            repaired = Solution()
            for tour in tours:
                if tour:
                    repaired.add_tour(tour)
            
            # Try to fix constraints again
            repaired = self.fix_energy_constraints(repaired)
            
            if self.problem.check_valid_solution(repaired):
                repaired.set_tour_length(self.problem.calculate_tour_length(repaired))
                return repaired
        except Exception as e:
            logger.error(f"Error in first repair attempt: {e}")
        
        try:
            # Third attempt: Use greedy search
            return self.greedy_search.optimize(solution)
        except Exception as e:
            logger.error(f"Error in greedy repair attempt: {e}")
        
        # Final fallback: create a new solution from scratch
        try:
            return self.greedy_search.solve(self.problem, verbose=False)
        except Exception as e:
            logger.error(f"Error in fallback repair: {e}")
            
            # If all else fails, return the original solution
            return solution
    
    def fix_energy_constraints(self, solution: Solution) -> Solution:
        """
        Fix energy constraints by inserting charging stations.
        
        Args:
            solution (Solution): The solution to fix.
            
        Returns:
            Solution: Solution with energy constraints fixed.
        """
        # Get all tours
        tours = solution.get_tours()
        
        # First fix capacity constraints
        tours = self.fix_capacity_constraints(tours)
        
        for i, tour in enumerate(tours):
            if len(tour) < 2:
                continue
                
            # Check and fix energy constraints for each tour
            tours[i] = self.insert_charging_stations(tour)
        
        # Create a new solution with fixed tours
        fixed_solution = Solution()
        for tour in tours:
            if tour:
                fixed_solution.add_tour(tour)
        
        fixed_solution.set_tour_length(self.problem.calculate_tour_length(fixed_solution))
        return fixed_solution
        
    def fix_capacity_constraints(self, tours):
        """
        Fix capacity constraints by redistributing customers.
        
        Args:
            tours (list): List of tours.
            
        Returns:
            list: Tours with capacity constraints fixed.
        """
        capacity = self.problem.get_capacity()
        
        # Check each tour for capacity violation
        for i, tour in enumerate(tours):
            # Skip empty tours
            if not tour:
                continue
                
            # Calculate total demand
            total_demand = sum(node.get_demand() for node in tour if node.is_customer())
            
            # If capacity is violated, split the tour
            if total_demand > capacity:
                # Extract customers from the tour
                customers = [node for node in tour if node.is_customer()]
                
                # Sort customers by demand (larger first)
                customers.sort(key=lambda x: x.get_demand(), reverse=True)
                
                # Create new tours
                new_tour1 = []
                new_tour2 = []
                demand1 = 0
                demand2 = 0
                
                # Distribute customers to balance load
                for customer in customers:
                    demand = customer.get_demand()
                    
                    if demand1 <= demand2 and demand1 + demand <= capacity:
                        new_tour1.append(customer)
                        demand1 += demand
                    elif demand2 + demand <= capacity:
                        new_tour2.append(customer)
                        demand2 += demand
                    else:
                        # If neither tour can accommodate, prefer the one with less load
                        if demand1 <= demand2:
                            new_tour1.append(customer)
                            demand1 += demand
                        else:
                            new_tour2.append(customer)
                            demand2 += demand
                
                # Replace the original tour with new_tour1
                tours[i] = new_tour1
                
                # Add new_tour2 if it's not empty
                if new_tour2:
                    tours.append(new_tour2)
        
        return tours
    
    def insert_charging_stations(self, tour):
        """
        Insert charging stations into a tour to ensure energy constraints are met.
        
        Args:
            tour (list): List of nodes in the tour.
            
        Returns:
            list: Tour with charging stations inserted.
        """
        if not tour:
            return []
        
        depot = self.problem.get_depot()
        stations = self.problem.get_all_stations()
        battery_capacity = self.problem.get_battery_capacity()
        
        # Start from depot with full battery
        complete_tour = []
        remaining_energy = battery_capacity
        current_node = depot
        
        # Process each customer in the tour
        for next_node in tour:
            energy_needed = self.problem.get_energy_consumption(current_node, next_node)
            
            if energy_needed <= remaining_energy:
                # We can reach the next node directly
                complete_tour.append(next_node)
                remaining_energy -= energy_needed
                current_node = next_node
            else:
                # Need to insert a charging station
                best_station = None
                best_detour = float('inf')
                
                for station in stations:
                    # Check if we can reach this station
                    energy_to_station = self.problem.get_energy_consumption(current_node, station)
                    
                    if energy_to_station <= remaining_energy:
                        energy_from_station = self.problem.get_energy_consumption(station, next_node)
                        
                        # Calculate detour distance
                        direct_dist = current_node.distance(next_node)
                        via_station_dist = current_node.distance(station) + station.distance(next_node)
                        detour = via_station_dist - direct_dist
                        
                        if detour < best_detour:
                            best_detour = detour
                            best_station = station
                
                if best_station:
                    # Insert the best station
                    complete_tour.append(best_station)
                    current_node = best_station
                    remaining_energy = battery_capacity
                    
                    # Now try to reach the customer
                    energy_needed = self.problem.get_energy_consumption(current_node, next_node)
                    if energy_needed <= remaining_energy:
                        complete_tour.append(next_node)
                        remaining_energy -= energy_needed
                        current_node = next_node
                    else:
                        # Still can't reach - try another station
                        found_path = False
                        for station2 in stations:
                            if station2.get_id() == best_station.get_id():
                                continue
                                
                            energy_to_station2 = self.problem.get_energy_consumption(best_station, station2)
                            if energy_to_station2 <= battery_capacity:
                                energy_from_station2 = self.problem.get_energy_consumption(station2, next_node)
                                if energy_from_station2 <= battery_capacity:
                                    # Found a path: current -> best_station -> station2 -> next_node
                                    complete_tour.append(station2)
                                    complete_tour.append(next_node)
                                    remaining_energy = battery_capacity - energy_from_station2
                                    current_node = next_node
                                    found_path = True
                                    break
                                    
                        if not found_path:
                            # Extremely difficult case - skip this customer
                            continue
                else:
                    # No reachable station - try using the depot as a charging point
                    energy_to_depot = self.problem.get_energy_consumption(current_node, depot)
                    if energy_to_depot <= remaining_energy:
                        # We can reach the depot
                        complete_tour.append(depot)
                        current_node = depot
                        remaining_energy = battery_capacity
                        
                        # Now try to reach the customer from depot
                        energy_to_next = self.problem.get_energy_consumption(depot, next_node)
                        if energy_to_next <= battery_capacity:
                            complete_tour.append(next_node)
                            remaining_energy = battery_capacity - energy_to_next
                            current_node = next_node
                        else:
                            # Find a path depot -> station -> next_node
                            found_path = False
                            for station in stations:
                                energy_to_station = self.problem.get_energy_consumption(depot, station)
                                if energy_to_station <= battery_capacity:
                                    energy_from_station = self.problem.get_energy_consumption(station, next_node)
                                    if energy_from_station <= battery_capacity:
                                        complete_tour.append(station)
                                        complete_tour.append(next_node)
                                        remaining_energy = battery_capacity - energy_from_station
                                        current_node = next_node
                                        found_path = True
                                        break
                                        
                            if not found_path:
                                # Skip this customer
                                continue
                    else:
                        # Can't reach depot or any station - skip this customer
                        continue
        
        # Return just the nodes that aren't the depot
        return [node for node in complete_tour if node.get_id() != depot.get_id()]
    
    # ========================
    # Neighborhood operators
    # ========================
    
    def swap_nodes(self, solution: Solution) -> Solution:
        """
        Swap two nodes within a route.
        """
        tours = solution.get_tours()
        
        if not tours:
            return solution
            
        # Select a random tour
        tour_idx = random.randint(0, len(tours) - 1)
        tour = tours[tour_idx]
        
        if len(tour) < 2:
            return solution
        
        # Select two random positions
        pos1, pos2 = random.sample(range(len(tour)), 2)
        
        # Swap nodes
        tour[pos1], tour[pos2] = tour[pos2], tour[pos1]
        
        # Update solution
        solution.set_tour_length(self.problem.calculate_tour_length(solution))
        
        return solution
    
    def relocate_node(self, solution: Solution) -> Solution:
        """
        Move a node from one position to another within a route.
        """
        tours = solution.get_tours()
        
        if not tours:
            return solution
            
        # Select a random tour
        tour_idx = random.randint(0, len(tours) - 1)
        tour = tours[tour_idx]
        
        if len(tour) < 2:
            return solution
        
        # Select source and destination positions
        pos1 = random.randint(0, len(tour) - 1)
        pos2 = random.randint(0, len(tour) - 1)
        
        while pos1 == pos2:
            pos2 = random.randint(0, len(tour) - 1)
        
        # Relocate node
        node = tour.pop(pos1)
        tour.insert(pos2, node)
        
        # Update solution
        solution.set_tour_length(self.problem.calculate_tour_length(solution))
        
        return solution
    
    def two_opt(self, solution: Solution) -> Solution:
        """
        Apply 2-opt move: reverse a segment of a route.
        """
        tours = solution.get_tours()
        
        if not tours:
            return solution
            
        # Select a random tour
        tour_idx = random.randint(0, len(tours) - 1)
        tour = tours[tour_idx]
        
        if len(tour) < 4:
            return solution
        
        # Select two random positions
        i = random.randint(0, len(tour) - 2)
        j = random.randint(i + 1, len(tour) - 1)
        
        # Reverse the segment
        tour[i:j+1] = reversed(tour[i:j+1])
        
        # Update solution
        solution.set_tour_length(self.problem.calculate_tour_length(solution))
        
        return solution
    
    def three_opt(self, solution: Solution) -> Solution:
        """
        Apply 3-opt move: reorganize three segments of a route.
        """
        tours = solution.get_tours()
        
        if not tours:
            return solution
            
        # Select a random tour
        tour_idx = random.randint(0, len(tours) - 1)
        tour = tours[tour_idx]
        
        if len(tour) < 6:
            return solution
        
        # Select three random cut points
        cut_points = sorted(random.sample(range(1, len(tour)), 3))
        i, j, k = cut_points
        
        # Get the segments
        a = tour[:i]
        b = tour[i:j]
        c = tour[j:k]
        d = tour[k:]
        
        # Choose a random 3-opt arrangement
        arrangements = [
            a + b + c + d,  # Original
            a + c + b + d,  # Swap b and c
            a + b[::-1] + c + d,  # Reverse b
            a + b + c[::-1] + d,  # Reverse c
            a + b[::-1] + c[::-1] + d,  # Reverse b and c
            a + c[::-1] + b + d,  # Reverse c and swap
            a + c + b[::-1] + d,  # Reverse b and swap
            a + c[::-1] + b[::-1] + d,  # Reverse both and swap
        ]
        
        # Select a random arrangement
        new_tour = random.choice(arrangements)
        tours[tour_idx] = new_tour
        
        # Update solution
        solution.set_tour_length(self.problem.calculate_tour_length(solution))
        
        return solution
    
    def relocate_customer_between_routes(self, solution: Solution) -> Solution:
        """
        Move a customer from one route to another.
        """
        tours = solution.get_tours()
        
        if len(tours) < 2:
            return solution
        
        # Select two random tours
        tour_idx1, tour_idx2 = random.sample(range(len(tours)), 2)
        tour1, tour2 = tours[tour_idx1], tours[tour_idx2]
        
        # Find customer positions in the first tour
        customer_positions = [i for i, node in enumerate(tour1) if node.is_customer()]
        
        if not customer_positions:
            return solution
        
        # Select a random customer to relocate
        pos = random.choice(customer_positions)
        customer = tour1[pos]
        
        # Check capacity constraint
        tour2_demand = sum(node.get_demand() for node in tour2 if node.is_customer())
        if tour2_demand + customer.get_demand() > self.problem.get_capacity():
            # Would violate capacity - skip this move
            return solution
        
        # Remove from first tour
        tour1.pop(pos)
        
        # Insert into second tour at random position
        insert_pos = random.randint(0, len(tour2))
        tour2.insert(insert_pos, customer)
        
        # Update solution
        solution.set_tour_length(self.problem.calculate_tour_length(solution))
        
        return solution
    
    def exchange_segments(self, solution: Solution) -> Solution:
        """
        Exchange segments between two routes.
        """
        tours = solution.get_tours()
        
        if len(tours) < 2:
            return solution
        
        # Select two random tours
        tour_idx1, tour_idx2 = random.sample(range(len(tours)), 2)
        tour1, tour2 = tours[tour_idx1], tours[tour_idx2]
        
        if len(tour1) < 2 or len(tour2) < 2:
            return solution
        
        # Define maximum segment size to avoid excessive changes
        max_segment_size = min(3, min(len(tour1), len(tour2)) - 1)
        if max_segment_size < 1:
            return solution
            
        # Select random segments in each tour
        start1 = random.randint(0, len(tour1) - max_segment_size)
        length1 = random.randint(1, min(max_segment_size, len(tour1) - start1))
        end1 = start1 + length1 - 1
        
        start2 = random.randint(0, len(tour2) - max_segment_size)
        length2 = random.randint(1, min(max_segment_size, len(tour2) - start2))
        end2 = start2 + length2 - 1
        
        # Extract segments
        segment1 = tour1[start1:end1+1]
        segment2 = tour2[start2:end2+1]
        
        # Check capacity constraints after exchange
        tour1_demand = sum(node.get_demand() for node in tour1 if node.is_customer())
        tour2_demand = sum(node.get_demand() for node in tour2 if node.is_customer())
        
        segment1_demand = sum(node.get_demand() for node in segment1 if node.is_customer())
        segment2_demand = sum(node.get_demand() for node in segment2 if node.is_customer())
        
        new_tour1_demand = tour1_demand - segment1_demand + segment2_demand
        new_tour2_demand = tour2_demand - segment2_demand + segment1_demand
        
        if new_tour1_demand > self.problem.get_capacity() or new_tour2_demand > self.problem.get_capacity():
            # Would violate capacity - skip this move
            return solution
        
        # Replace segments
        new_tour1 = tour1[:start1] + segment2 + tour1[end1+1:]
        new_tour2 = tour2[:start2] + segment1 + tour2[end2+1:]
        
        tours[tour_idx1] = new_tour1
        tours[tour_idx2] = new_tour2
        
        # Update solution
        solution.set_tour_length(self.problem.calculate_tour_length(solution))
        
        return solution
    
    # 在VNS类中添加以下方法

    def optimize_charging_stations(self, solution: Solution) -> Solution:
        """
        优化充电站的放置。
        """
        tours = solution.get_tours()
        
        if not tours:
            return solution
            
        # 选择一个随机路线
        tour_idx = random.randint(0, len(tours) - 1)
        tour = tours[tour_idx]
        
        # 找出充电站的位置
        station_positions = [i for i, node in enumerate(tour) if node.is_charging_station() and not node.is_depot()]
        
        if not station_positions:
            return solution
        
        # 选择一个随机充电站
        pos = random.choice(station_positions)
        
        # 尝试替换为不同的充电站
        stations = self.problem.get_all_stations()
        
        if stations:
            current_station = tour[pos]
            alternatives = [s for s in stations if s.get_id() != current_station.get_id()]
            
            if alternatives:
                # 用随机选择的替代充电站替换
                tour[pos] = random.choice(alternatives)
        
        # 更新解决方案
        solution.set_tour_length(self.problem.calculate_tour_length(solution))
        
        return solution

    def optimize_single_tour(self, tour):
        """
        使用VNS原则优化单个路线。
        用于修复解决方案或处理单个路线。
        
        Args:
            tour (list): 路线中的节点列表。
            
        Returns:
            list: 优化后的路线。
        """
        if not tour or len(tour) < 2:
            return tour
        
        # 为优化创建单路线解决方案
        depot = self.problem.get_depot()
        single_solution = Solution()
        single_solution.add_tour(tour)
        
        # 应用一系列局部搜索操作
        for _ in range(5):  # 应用多次迭代以获得更好的结果
            # 尝试不同的操作
            if len(tour) >= 2:
                # 交换两个节点
                pos1, pos2 = random.sample(range(len(tour)), 2)
                tour[pos1], tour[pos2] = tour[pos2], tour[pos1]
            
            if len(tour) >= 3:
                # 重定位一个节点
                pos1 = random.randint(0, len(tour) - 1)
                pos2 = random.randint(0, len(tour) - 1)
                while pos1 == pos2:
                    pos2 = random.randint(0, len(tour) - 1)
                
                node = tour.pop(pos1)
                tour.insert(pos2, node)
            
            if len(tour) >= 4:
                # 应用2-opt移动
                i = random.randint(0, len(tour) - 2)
                j = random.randint(i + 1, len(tour) - 1)
                
                # 反转片段
                tour[i:j+1] = reversed(tour[i:j+1])
        
        # 确保满足能源约束
        return self.insert_charging_stations(tour)