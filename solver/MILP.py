import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from copy import deepcopy
import random

from problem import Problem
from solution import Solution
from logger import logger

class MILP:
    """
    Modified Mixed Integer Linear Programming (MILP) implementation for solving the 
    Electric Vehicle Routing Problem (EVRP).
    
    This version does not rely on external solvers like PuLP, CBC, GLPK, etc.
    Instead, it uses a custom heuristic algorithm inspired by MILP principles.
    """
    
    def __init__(self, time_limit=1800, iterations=100000):
        """
        Initialize the solver with parameters.
        
        Args:
            time_limit (int): Maximum time in seconds allowed for solving.
            iterations (int): Maximum number of iterations for the search algorithm.
        """
        self.time_limit = time_limit
        self.max_iterations = iterations
        self.history = {
            'Time': [],
            'Objective Value': [],
            'Gap': [],
            'Lower Bound': []
        }
    
    def set_problem(self, problem: Problem):
        """
        Set the problem instance for the algorithm.
        """
        self.problem = problem
    
    def solve(self, problem: Problem, verbose=False, plot_path=None) -> Solution:
        """
        Solve the EVRP using a custom heuristic algorithm.
        
        Args:
            problem (Problem): The EVRP problem instance.
            verbose (bool): Whether to print detailed information.
            plot_path (str): Path to save convergence plots.
            
        Returns:
            Solution: The best-found solution.
        """
        self.set_problem(problem)
        self.verbose = verbose
        start_time = time.time()
        
        if verbose:
            print("Starting custom MILP solver for EVRP...")
            print(f"Problem size: {len(problem.get_all_customers())} customers, {problem.get_num_stations()} stations, {problem.get_max_num_vehicles()} vehicles")
        
        # Get key problem data
        depot = problem.get_depot()
        customers = problem.get_all_customers()
        stations = problem.get_all_stations()
        
        # Problem constraints
        max_vehicles = problem.get_max_num_vehicles()
        capacity = problem.get_capacity()
        battery_capacity = problem.get_battery_capacity()
        
        # Initialize best solution and parameters
        best_solution = None
        best_cost = float('inf')
        
        # Phase 1: Generate initial solution using a cluster-first, route-second approach
        if verbose:
            print("Phase 1: Generating initial clustered solution...")
            
        # Precompute distance matrix for faster access
        all_nodes = [depot] + customers + stations
        n_nodes = len(all_nodes)
        distances = np.zeros((n_nodes, n_nodes))
        energy_consumption = np.zeros((n_nodes, n_nodes))
        
        for i in range(n_nodes):
            for j in range(n_nodes):
                if i != j:
                    distances[i, j] = problem.get_distance(all_nodes[i], all_nodes[j])
                    energy_consumption[i, j] = problem.get_energy_consumption(all_nodes[i], all_nodes[j])
        
        # Mapping from node ID to index in the distance matrix
        node_to_idx = {node.get_id(): i for i, node in enumerate(all_nodes)}
        idx_to_node = {i: node for i, node in enumerate(all_nodes)}
        
        # 1. Assign customers to vehicles (clustering)
        clusters = self._assign_customers_to_vehicles(customers, max_vehicles, capacity)
        
        # 2. Optimize routes for each vehicle (routing)
        solution = self._optimize_routes(clusters, depot, stations, capacity, battery_capacity)
        
        # Record initial solution
        current_solution = solution
        current_cost = solution.get_tour_length()
        best_solution = deepcopy(solution)
        best_cost = current_cost
        
        # Record information for plotting
        self.history['Time'].append(time.time() - start_time)
        self.history['Objective Value'].append(current_cost)
        self.history['Gap'].append(None)  # Not applicable for our approach
        self.history['Lower Bound'].append(None)  # Not applicable for our approach
        
        if verbose:
            print(f"Initial solution cost: {current_cost:.2f}")
        
        # Phase 2: Local search and improvement
        if verbose:
            print("Phase 2: Improving solution with local search...")
        
        iteration = 0
        no_improvement = 0
        max_no_improvement = 1000  # Parameter to control diversification
        
        while (time.time() - start_time < self.time_limit and 
               iteration < self.max_iterations and 
               no_improvement < max_no_improvement):
            
            iteration += 1
            
            # 1. Apply a local search move
            new_solution = self._apply_local_search_move(deepcopy(current_solution))
            
            # 2. Evaluate the new solution
            new_cost = new_solution.get_tour_length()
            
            # 3. Accept or reject the move
            if new_cost < current_cost:
                current_solution = new_solution
                current_cost = new_cost
                no_improvement = 0
                
                # Update best solution if improved
                if current_cost < best_cost:
                    best_solution = deepcopy(current_solution)
                    best_cost = current_cost
                    
                    if verbose and iteration % 100 == 0:
                        print(f"Iteration {iteration}: New best solution found with cost {best_cost:.2f}")
                    
                    # Record for plotting
                    self.history['Time'].append(time.time() - start_time)
                    self.history['Objective Value'].append(best_cost)
                    self.history['Gap'].append(None)
                    self.history['Lower Bound'].append(None)
            else:
                # Simulated annealing-like acceptance
                temperature = max(0.01, 1.0 - (iteration / self.max_iterations))
                acceptance_probability = np.exp(-(new_cost - current_cost) / (temperature * current_cost))
                
                if random.random() < acceptance_probability:
                    current_solution = new_solution
                    current_cost = new_cost
                
                no_improvement += 1
            
            # Periodically diversify the search
            if no_improvement >= max_no_improvement // 2:
                if verbose:
                    print(f"Diversifying search at iteration {iteration}...")
                
                current_solution = self._diversify_solution(current_solution)
                current_cost = current_solution.get_tour_length()
                no_improvement = 0
            
            # Periodically record for plotting
            if iteration % 1000 == 0:
                self.history['Time'].append(time.time() - start_time)
                self.history['Objective Value'].append(current_cost)
                self.history['Gap'].append(None)
                self.history['Lower Bound'].append(None)
        
        # Final local search on the best solution
        best_solution = self._final_optimization(best_solution)
        best_cost = best_solution.get_tour_length()
        
        # Record final solution
        self.history['Time'].append(time.time() - start_time)
        self.history['Objective Value'].append(best_cost)
        self.history['Gap'].append(None)
        self.history['Lower Bound'].append(None)
        
        total_time = time.time() - start_time
        
        if verbose:
            print(f"MILP completed in {total_time:.2f} seconds, {iteration} iterations")
            print(f"Best solution cost: {best_cost:.2f}")
        
        # Validate solution
        valid = problem.check_valid_solution(best_solution)
        if not valid and verbose:
            print("Warning: Final solution is not valid according to problem constraints.")
            print("Attempting repair...")
            best_solution = self._repair_solution(best_solution)
            valid = problem.check_valid_solution(best_solution)
            best_cost = best_solution.get_tour_length()
            if valid:
                print(f"Repaired solution is valid with cost {best_cost:.2f}")
            else:
                print("Could not repair solution.")
        
        # Create convergence plot if requested
        if plot_path:
            self.plot_history(plot_path)
        
        return best_solution
    
    def _assign_customers_to_vehicles(self, customers, max_vehicles, capacity):
        """
        Assign customers to vehicles using a clustering approach.
        """
        # Sort customers by distance from depot
        depot = self.problem.get_depot()
        sorted_customers = sorted(customers, key=lambda c: depot.distance(c))
        
        # Initialize clusters
        clusters = [[] for _ in range(max_vehicles)]
        cluster_loads = [0.0] * max_vehicles
        
        # Assign each customer to the first vehicle with available capacity
        for customer in sorted_customers:
            demand = customer.get_demand()
            
            # Find the first vehicle with available capacity
            assigned = False
            for i in range(max_vehicles):
                if cluster_loads[i] + demand <= capacity:
                    clusters[i].append(customer)
                    cluster_loads[i] += demand
                    assigned = True
                    break
            
            # If no vehicle has capacity, assign to the vehicle with the least load
            if not assigned:
                min_load_idx = cluster_loads.index(min(cluster_loads))
                clusters[min_load_idx].append(customer)
                cluster_loads[min_load_idx] += demand
        
        return clusters
    
    def _optimize_routes(self, clusters, depot, stations, capacity, battery_capacity):
        """
        Optimize routes for each vehicle.
        """
        solution = Solution()
        
        for cluster in clusters:
            if not cluster:  # Skip empty clusters
                continue
                
            # Start with a simple tour: depot -> customers -> depot
            tour = self._optimize_single_route(cluster, depot)
            
            # Insert charging stations as needed
            tour = self._insert_charging_stations(tour, stations, battery_capacity)
            
            # Add the tour to the solution
            if tour:
                solution.add_tour(tour)
        
        # Calculate tour length
        solution.set_tour_length(self.problem.calculate_tour_length(solution))
        
        return solution
    
    def _optimize_single_route(self, customers, depot):
        """
        Optimize a single route using a nearest neighbor heuristic.
        """
        if not customers:
            return []
            
        # Start from depot
        tour = []
        unvisited = customers.copy()
        current = depot
        
        # Use nearest neighbor heuristic
        while unvisited:
            # Find the nearest unvisited customer
            nearest = min(unvisited, key=lambda c: current.distance(c))
            tour.append(nearest)
            current = nearest
            unvisited.remove(nearest)
        
        return tour
    
    def _insert_charging_stations(self, tour, stations, battery_capacity):
        """
        Insert charging stations into a tour to ensure energy constraints are met.
        """
        if not tour:
            return []
            
        # Start from depot with full battery
        depot = self.problem.get_depot()
        complete_tour = [depot]
        remaining_energy = battery_capacity
        
        for i in range(len(tour)):
            # Check if we can reach the next customer
            energy_needed = self.problem.get_energy_consumption(complete_tour[-1], tour[i])
            
            if energy_needed <= remaining_energy:
                # We can reach the next customer
                complete_tour.append(tour[i])
                remaining_energy -= energy_needed
            else:
                # Need to visit a charging station
                nearest_station = self._find_nearest_charging_station(complete_tour[-1], stations, remaining_energy)
                
                if nearest_station:
                    # Visit charging station
                    complete_tour.append(nearest_station)
                    # Reset energy at charging station
                    remaining_energy = battery_capacity
                    # Try again to reach the customer
                    energy_needed = self.problem.get_energy_consumption(complete_tour[-1], tour[i])
                    
                    if energy_needed <= remaining_energy:
                        complete_tour.append(tour[i])
                        remaining_energy -= energy_needed
                    else:
                        # Can't reach even after charging; this is a problem
                        # Try another station
                        for station in stations:
                            if station != nearest_station:
                                complete_tour.append(station)
                                remaining_energy = battery_capacity
                                energy_needed = self.problem.get_energy_consumption(complete_tour[-1], tour[i])
                                
                                if energy_needed <= remaining_energy:
                                    complete_tour.append(tour[i])
                                    remaining_energy -= energy_needed
                                    break
                else:
                    # No accessible charging station, try to go back to depot
                    depot_energy = self.problem.get_energy_consumption(complete_tour[-1], depot)
                    
                    if depot_energy <= remaining_energy:
                        complete_tour.append(depot)
                        remaining_energy = battery_capacity
                        
                        # Now try to reach the customer from depot
                        energy_needed = self.problem.get_energy_consumption(depot, tour[i])
                        if energy_needed <= remaining_energy:
                            complete_tour.append(tour[i])
                            remaining_energy -= energy_needed
        
        # Return to depot
        depot_energy = self.problem.get_energy_consumption(complete_tour[-1], depot)
        
        if depot_energy <= remaining_energy:
            complete_tour.append(depot)
        else:
            # Need to charge before returning to depot
            nearest_station = self._find_nearest_charging_station(complete_tour[-1], stations, remaining_energy)
            
            if nearest_station:
                complete_tour.append(nearest_station)
                complete_tour.append(depot)
            else:
                # Emergency: try to find any accessible station
                for station in stations:
                    station_energy = self.problem.get_energy_consumption(complete_tour[-1], station)
                    if station_energy <= remaining_energy:
                        complete_tour.append(station)
                        complete_tour.append(depot)
                        break
                else:
                    # No solution found, just add depot (might be infeasible)
                    complete_tour.append(depot)
        
        return complete_tour[1:-1]  # Remove depot from ends (will be added by Solution)
    
    def _find_nearest_charging_station(self, node, stations, remaining_energy):
        """
        Find the nearest charging station that can be reached with the remaining energy.
        """
        accessible_stations = []
        
        for station in stations:
            energy_needed = self.problem.get_energy_consumption(node, station)
            if energy_needed <= remaining_energy:
                accessible_stations.append((station, energy_needed))
        
        if accessible_stations:
            # Sort by energy needed (proxy for distance)
            accessible_stations.sort(key=lambda x: x[1])
            return accessible_stations[0][0]
        
        return None
    
    def _apply_local_search_move(self, solution):
        """
        Apply a local search move to improve the solution.
        """
        # Choose a random local search operator
        operator = random.choice([
            self._swap_nodes,
            self._relocate_node,
            self._two_opt,
            self._exchange_customers_between_routes,
            self._optimize_charging_stations
        ])
        
        # Apply the selected operator
        modified_solution = operator(solution)
        
        # Update tour length
        modified_solution.set_tour_length(self.problem.calculate_tour_length(modified_solution))
        
        return modified_solution
    
    def _swap_nodes(self, solution):
        """
        Swap two nodes within a route.
        """
        tours = solution.get_tours()
        
        if not tours:
            return solution
            
        # Select a random tour
        tour_idx = random.randint(0, len(tours) - 1)
        tour = tours[tour_idx]
        
        if len(tour) < 3:  # Need at least 3 nodes to swap (excluding depot)
            return solution
        
        # Find positions of non-depot, non-charging nodes
        customer_positions = [i for i, node in enumerate(tour) if node.is_customer()]
        
        if len(customer_positions) < 2:
            return solution
        
        # Select two random positions
        pos1, pos2 = random.sample(customer_positions, 2)
        
        # Swap nodes
        tour[pos1], tour[pos2] = tour[pos2], tour[pos1]
        
        return solution
    
    def _relocate_node(self, solution):
        """
        Move a node from one position to another within a route.
        """
        tours = solution.get_tours()
        
        if not tours:
            return solution
            
        # Select a random tour
        tour_idx = random.randint(0, len(tours) - 1)
        tour = tours[tour_idx]
        
        if len(tour) < 3:  # Need at least 3 nodes for relocation
            return solution
        
        # Find positions of non-depot, non-charging nodes
        customer_positions = [i for i, node in enumerate(tour) if node.is_customer()]
        
        if len(customer_positions) < 2:
            return solution
        
        # Select source and destination positions
        src_pos = random.choice(customer_positions)
        dst_pos = random.choice(customer_positions)
        
        while src_pos == dst_pos:
            dst_pos = random.choice(customer_positions)
        
        # Relocate node
        node = tour.pop(src_pos)
        tour.insert(dst_pos if dst_pos < src_pos else dst_pos - 1, node)
        
        return solution
    
    def _two_opt(self, solution):
        """
        Apply 2-opt move: reverse a segment of a route.
        """
        tours = solution.get_tours()
        
        if not tours:
            return solution
            
        # Select a random tour
        tour_idx = random.randint(0, len(tours) - 1)
        tour = tours[tour_idx]
        
        if len(tour) < 4:  # Need at least 4 nodes for 2-opt
            return solution
        
        # Select two random positions for segment endpoints
        i = random.randint(1, len(tour) - 3)
        j = random.randint(i + 1, len(tour) - 2)
        
        # Reverse the segment
        tour[i:j+1] = reversed(tour[i:j+1])
        
        return solution
    
    def _exchange_customers_between_routes(self, solution):
        """
        Exchange customers between two routes.
        """
        tours = solution.get_tours()
        
        if len(tours) < 2:
            return solution
        
        # Select two random tours
        tour_idx1, tour_idx2 = random.sample(range(len(tours)), 2)
        tour1, tour2 = tours[tour_idx1], tours[tour_idx2]
        
        # Find customer positions in each tour
        customer_positions1 = [i for i, node in enumerate(tour1) if node.is_customer()]
        customer_positions2 = [i for i, node in enumerate(tour2) if node.is_customer()]
        
        if not customer_positions1 or not customer_positions2:
            return solution
        
        # Select a random customer from each tour
        pos1 = random.choice(customer_positions1)
        pos2 = random.choice(customer_positions2)
        
        # Exchange customers
        tour1[pos1], tour2[pos2] = tour2[pos2], tour1[pos1]
        
        # Recalculate validity (capacity and energy constraints will be checked by the main algorithm)
        return solution
    
    def _optimize_charging_stations(self, solution):
        """
        Try to optimize the placement of charging stations.
        """
        tours = solution.get_tours()
        
        if not tours:
            return solution
            
        # Select a random tour
        tour_idx = random.randint(0, len(tours) - 1)
        tour = tours[tour_idx]
        
        # Find charging station positions
        station_positions = [i for i, node in enumerate(tour) if node.is_charging_station() and not node.is_depot()]
        
        if not station_positions:
            return solution
        
        # Select a random charging station
        pos = random.choice(station_positions)
        
        # Try to replace with a different station
        stations = self.problem.get_all_stations()
        if len(stations) > 1:
            current_station = tour[pos]
            alternatives = [s for s in stations if s.get_id() != current_station.get_id()]
            
            if alternatives:
                # Replace with a random alternative station
                tour[pos] = random.choice(alternatives)
        
        return solution
    
    def _diversify_solution(self, solution):
        """
        Diversify the solution to escape local optima.
        """
        # Strong diversification: reconstruct part of the solution
        tours = solution.get_tours()
        
        if not tours:
            return solution
        
        # Select a random tour or multiple tours for diversification
        if len(tours) > 1 and random.random() < 0.3:
            # Redistribute customers between tours
            customers = []
            
            # Collect all customers from all tours
            for tour in tours:
                customers.extend([node for node in tour if node.is_customer()])
            
            # Empty the tours but keep the structure
            for i in range(len(tours)):
                tours[i] = []
            
            # Redistribute customers randomly
            random.shuffle(customers)
            
            for customer in customers:
                tours[random.randint(0, len(tours) - 1)].append(customer)
            
            # Reoptimize each tour
            for i in range(len(tours)):
                if tours[i]:
                    tours[i] = self._optimize_single_route(tours[i], self.problem.get_depot())
                    tours[i] = self._insert_charging_stations(tours[i], self.problem.get_all_stations(), self.problem.get_battery_capacity())
        else:
            # Select a random tour for diversification
            tour_idx = random.randint(0, len(tours) - 1)
            
            # Extract customers and reoptimize
            customers = [node for node in tours[tour_idx] if node.is_customer()]
            
            if customers:
                random.shuffle(customers)
                tours[tour_idx] = self._optimize_single_route(customers, self.problem.get_depot())
                tours[tour_idx] = self._insert_charging_stations(tours[tour_idx], self.problem.get_all_stations(), self.problem.get_battery_capacity())
        
        # Recalculate tour length
        solution.set_tour_length(self.problem.calculate_tour_length(solution))
        
        return solution
    
    def _final_optimization(self, solution):
        """
        Apply final optimization to the best solution found.
        """
        best_solution = deepcopy(solution)
        best_cost = solution.get_tour_length()
        
        # Try each local search operator a few times
        operators = [
            self._swap_nodes,
            self._relocate_node,
            self._two_opt,
            self._exchange_customers_between_routes,
            self._optimize_charging_stations
        ]
        
        for _ in range(100):  # Apply 100 iterations of final optimization
            for operator in operators:
                new_solution = operator(deepcopy(best_solution))
                new_cost = self.problem.calculate_tour_length(new_solution)
                
                if new_cost < best_cost and self.problem.check_valid_solution(new_solution):
                    best_solution = new_solution
                    best_cost = new_cost
        
        best_solution.set_tour_length(best_cost)
        return best_solution
    
    def _repair_solution(self, solution):
        """
        Attempt to repair an invalid solution.
        """
        # Try to fix capacity and energy constraints
        tours = solution.get_tours()
        
        for i, tour in enumerate(tours):
            # Check capacity constraint
            total_demand = sum(node.get_demand() for node in tour if node.is_customer())
            
            if total_demand > self.problem.get_capacity():
                # Split into multiple tours
                customers = [node for node in tour if node.is_customer()]
                tours[i] = []
                
                new_tour = []
                current_demand = 0
                
                for customer in customers:
                    if current_demand + customer.get_demand() <= self.problem.get_capacity():
                        new_tour.append(customer)
                        current_demand += customer.get_demand()
                    else:
                        # Start a new tour
                        if new_tour:
                            tours[i].extend(self._insert_charging_stations(new_tour, self.problem.get_all_stations(), self.problem.get_battery_capacity()))
                        
                        # If we've used all tours, create a new one
                        if i == len(tours) - 1:
                            tours.append([])
                            i += 1
                        
                        new_tour = [customer]
                        current_demand = customer.get_demand()
                
                # Add the last tour
                if new_tour:
                    tours[i].extend(self._insert_charging_stations(new_tour, self.problem.get_all_stations(), self.problem.get_battery_capacity()))
            
            # Check energy constraint by re-inserting charging stations
            else:
                customers = [node for node in tour if node.is_customer()]
                tours[i] = self._insert_charging_stations(customers, self.problem.get_all_stations(), self.problem.get_battery_capacity())
        
        # Remove empty tours
        tours = [tour for tour in tours if tour]
        
        # Create a new solution
        repaired = Solution()
        for tour in tours:
            repaired.add_tour(tour)
        
        repaired.set_tour_length(self.problem.calculate_tour_length(repaired))
        return repaired
    
    def plot_history(self, path):
        """
        Plot the convergence history of the algorithm.
        """
        try:
            # Safety check if history is empty
            if not self.history['Time'] or len(self.history['Time']) == 0:
                logger.warning("No history data to plot")
                return
                
            df = pd.DataFrame(self.history)
            
            # Create a figure with subplots
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # Plot objective value over time
            if 'Objective Value' in df and not all(ov is None for ov in df['Objective Value']):
                ax.plot(df['Time'], df['Objective Value'], 'b-', label='Objective Value')
                
            ax.set_xlabel('Time (s)')
            ax.set_ylabel('Objective Value')
            ax.set_title('Custom MILP Convergence')
            ax.legend()
            ax.grid(True)
            
            plt.tight_layout()
            plt.savefig(path)
            plt.close()
        except Exception as e:
            logger.error(f"Error plotting history: {e}")
            # Just skip plotting if there's an error