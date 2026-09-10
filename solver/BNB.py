import time
import heapq
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from copy import deepcopy
from collections import deque

from problem import Problem
from solution import Solution
from node import Node
from logger import logger

class BNBNode:
    """
    Represents a node in the Branch and Bound search tree.
    
    This is different from the Node class in the EVRP problem,
    which represents a physical location (customer, station, or depot).
    """
    def __init__(self, level=0, path=None, bound=0.0, current_cost=0.0, 
                 remaining_customers=None, load=0.0, energy=0.0, parent=None):
        self.level = level  # Current level in the search tree
        self.path = path or []  # Current path of nodes
        self.bound = bound  # Lower bound on the cost
        self.current_cost = current_cost  # Cost of the current path
        self.remaining_customers = remaining_customers or set()  # Customers not yet visited
        self.load = load  # Current load on the vehicle
        self.energy = energy  # Current energy level
        self.parent = parent  # Parent node in the search tree
    
    def __lt__(self, other):
        """For priority queue comparison based on bound."""
        return self.bound < other.bound

class BranchAndBound:
    """
    Branch and Bound algorithm implementation for solving the
    Electric Vehicle Routing Problem (EVRP).
    
    This algorithm uses a systematic exploration of the solution space
    with pruning based on lower bounds to find the optimal solution.
    """
    
    def __init__(self, time_limit=1800, max_nodes=100000):
        """
        Initialize the Branch and Bound solver with parameters.
        
        Args:
            time_limit (int): Maximum time in seconds allowed for solving.
            max_nodes (int): Maximum number of nodes to explore in the search tree.
        """
        self.time_limit = time_limit
        self.max_nodes = max_nodes
        self.history = {
            'Iteration': [],
            'Time': [],
            'Best Objective': [],
            'Nodes Explored': [],
            'Lower Bound': []
        }
        self.best_solution = None
        self.best_cost = float('inf')
        self.nodes_explored = 0
    
    def set_problem(self, problem: Problem):
        """
        Set the problem instance for the algorithm.
        """
        self.problem = problem
        
        # Pre-compute distance matrix for faster access
        all_nodes = ([self.problem.get_depot()] + 
                     self.problem.get_all_customers() + 
                     self.problem.get_all_stations())
        
        self.node_id_to_index = {node.get_id(): i for i, node in enumerate(all_nodes)}
        self.index_to_node = {i: node for i, node in enumerate(all_nodes)}
        
        n = len(all_nodes)
        self.distances = np.zeros((n, n))
        self.energy_consumption = np.zeros((n, n))
        
        for i in range(n):
            for j in range(n):
                if i != j:
                    self.distances[i, j] = problem.get_distance(all_nodes[i], all_nodes[j])
                    self.energy_consumption[i, j] = problem.get_energy_consumption(all_nodes[i], all_nodes[j])
        
        # Nearest neighbor information for bound calculation
        self.nearest_neighbor = {}
        for i in range(n):
            sorted_indices = np.argsort(self.distances[i])
            self.nearest_neighbor[i] = sorted_indices[1]  # Skip itself (at index 0)
    
    def solve(self, problem: Problem, verbose=False, plot_path=None) -> Solution:
        """
        Solve the EVRP using Branch and Bound.
        
        Args:
            problem (Problem): The EVRP problem instance.
            verbose (bool): Whether to print detailed information.
            plot_path (str): Path to save convergence plots.
            
        Returns:
            Solution: The optimal or best-found solution.
        """
        self.set_problem(problem)
        self.verbose = verbose
        start_time = time.time()
        
        # Initialize best solution
        self.best_solution = None
        self.best_cost = float('inf')
        self.nodes_explored = 0
        
        # Get problem data
        depot = problem.get_depot()
        depot_id = depot.get_id()
        depot_idx = self.node_id_to_index[depot_id]
        
        customers = problem.get_all_customers()
        customer_ids = [c.get_id() for c in customers]
        
        # Maximum vehicles and capacity
        max_vehicles = problem.get_max_num_vehicles()
        capacity = problem.get_capacity()
        battery_capacity = problem.get_battery_capacity()
        
        # Set of all customer indices to visit
        remaining_customers = set(self.node_id_to_index[c_id] for c_id in customer_ids)
        
        # Initialize the first node (at depot)
        initial_path = [depot_idx]
        initial_node = BNBNode(level=0, 
                              path=initial_path,
                              bound=self.calculate_bound(initial_path, remaining_customers),
                              current_cost=0.0,
                              remaining_customers=remaining_customers,
                              load=0.0,
                              energy=battery_capacity)
        
        # Priority queue for branch and bound
        pq = [initial_node]
        
        # Record starting time and initial stats
        iteration = 0
        self.history['Iteration'].append(iteration)
        self.history['Time'].append(0)
        self.history['Best Objective'].append(float('inf'))
        self.history['Nodes Explored'].append(0)
        self.history['Lower Bound'].append(initial_node.bound)
        
        if verbose:
            print(f"Starting Branch and Bound (time limit: {self.time_limit}s, max nodes: {self.max_nodes})...")
            print(f"Problem size: {len(customer_ids)} customers, {max_vehicles} vehicles")
        
        # Main Branch and Bound loop
        while pq and self.nodes_explored < self.max_nodes:
            # Check time limit
            if time.time() - start_time > self.time_limit:
                if verbose:
                    print(f"Time limit reached after {self.nodes_explored} nodes.")
                break
            
            # Get node with smallest bound
            current_node = heapq.heappop(pq)
            self.nodes_explored += 1
            
            # If the bound is greater than the best cost, skip this node
            if current_node.bound >= self.best_cost:
                continue
            
            current_path = current_node.path
            current_level = current_node.level
            current_cost = current_node.current_cost
            remaining = current_node.remaining_customers
            current_load = current_node.load
            current_energy = current_node.energy
            
            # Get the last node in the path
            last_idx = current_path[-1]
            last_node = self.index_to_node[last_idx]
            
            # Check if all customers have been visited
            if not remaining:
                # If at depot, we have a complete solution
                if last_idx == depot_idx:
                    if current_cost < self.best_cost:
                        self.best_cost = current_cost
                        self.best_solution = deepcopy(current_path)
                        
                        if verbose:
                            print(f"New best solution found: {self.best_cost:.2f} at node {self.nodes_explored}")
                            
                        # Record stats
                        iteration += 1
                        self.history['Iteration'].append(iteration)
                        self.history['Time'].append(time.time() - start_time)
                        self.history['Best Objective'].append(self.best_cost)
                        self.history['Nodes Explored'].append(self.nodes_explored)
                        self.history['Lower Bound'].append(current_node.bound)
                
                # If not at depot, add the cost to return to depot
                else:
                    return_cost = self.distances[last_idx][depot_idx]
                    return_energy = self.energy_consumption[last_idx][depot_idx]
                    
                    # Check if we have enough energy to return
                    if current_energy >= return_energy:
                        total_cost = current_cost + return_cost
                        
                        if total_cost < self.best_cost:
                            complete_path = current_path + [depot_idx]
                            self.best_cost = total_cost
                            self.best_solution = deepcopy(complete_path)
                            
                            if verbose:
                                print(f"New best solution found: {self.best_cost:.2f} at node {self.nodes_explored}")
                            
                            # Record stats
                            iteration += 1
                            self.history['Iteration'].append(iteration)
                            self.history['Time'].append(time.time() - start_time)
                            self.history['Best Objective'].append(self.best_cost)
                            self.history['Nodes Explored'].append(self.nodes_explored)
                            self.history['Lower Bound'].append(current_node.bound)
                
                continue
            
            # Branch: explore possible next nodes
            
            # Option 1: Visit a customer
            for next_idx in list(remaining):
                next_node = self.index_to_node[next_idx]
                
                # Skip if the customer is already in the path
                if next_idx in current_path:
                    continue
                
                # Calculate cost and energy to move to this customer
                edge_cost = self.distances[last_idx][next_idx]
                edge_energy = self.energy_consumption[last_idx][next_idx]
                
                # Check energy constraint
                if current_energy >= edge_energy:
                    # Check capacity constraint
                    next_load = current_load + next_node.get_demand()
                    
                    if next_load <= capacity:
                        # Create a new set of remaining customers
                        new_remaining = remaining.copy()
                        new_remaining.remove(next_idx)
                        
                        # Create a new path
                        new_path = current_path + [next_idx]
                        
                        # Calculate new cost, energy, and bound
                        new_cost = current_cost + edge_cost
                        new_energy = current_energy - edge_energy
                        new_bound = new_cost + self.calculate_bound(new_path, new_remaining)
                        
                        # If the bound is less than the best cost, add to queue
                        if new_bound < self.best_cost:
                            new_node = BNBNode(level=current_level+1,
                                              path=new_path,
                                              bound=new_bound,
                                              current_cost=new_cost,
                                              remaining_customers=new_remaining,
                                              load=next_load,
                                              energy=new_energy,
                                              parent=current_node)
                            
                            heapq.heappush(pq, new_node)
            
            # Option 2: Visit a charging station if energy is low
            if current_energy < 0.5 * battery_capacity:  # Energy threshold
                for station_id in problem.get_station_ids():
                    station_idx = self.node_id_to_index[station_id]
                    
                    # Skip if this station is the last node in the path
                    if station_idx == last_idx:
                        continue
                    
                    # Calculate cost and energy to move to this station
                    edge_cost = self.distances[last_idx][station_idx]
                    edge_energy = self.energy_consumption[last_idx][station_idx]
                    
                    # Check if we have enough energy to reach the station
                    if current_energy >= edge_energy:
                        # Create new path
                        new_path = current_path + [station_idx]
                        
                        # Calculate new cost and bound
                        new_cost = current_cost + edge_cost
                        new_bound = new_cost + self.calculate_bound(new_path, remaining)
                        
                        # If the bound is less than the best cost, add to queue
                        if new_bound < self.best_cost:
                            new_node = BNBNode(level=current_level+1,
                                              path=new_path,
                                              bound=new_bound,
                                              current_cost=new_cost,
                                              remaining_customers=remaining,
                                              load=current_load,
                                              energy=battery_capacity,  # Reset energy at station
                                              parent=current_node)
                            
                            heapq.heappush(pq, new_node)
            
            # Option 3: Return to depot to reset
            if last_idx != depot_idx and (current_load > 0.7 * capacity or current_energy < 0.3 * battery_capacity):
                # Calculate cost and energy to return to depot
                edge_cost = self.distances[last_idx][depot_idx]
                edge_energy = self.energy_consumption[last_idx][depot_idx]
                
                # Check if we have enough energy to return
                if current_energy >= edge_energy:
                    # Create new path
                    new_path = current_path + [depot_idx]
                    
                    # Calculate new cost and bound
                    new_cost = current_cost + edge_cost
                    new_bound = new_cost + self.calculate_bound(new_path, remaining)
                    
                    # If the bound is less than the best cost, add to queue
                    if new_bound < self.best_cost:
                        new_node = BNBNode(level=current_level+1,
                                          path=new_path,
                                          bound=new_bound,
                                          current_cost=new_cost,
                                          remaining_customers=remaining,
                                          load=0.0,  # Reset load at depot
                                          energy=battery_capacity,  # Reset energy at depot
                                          parent=current_node)
                        
                        heapq.heappush(pq, new_node)
            
            # Periodically record stats
            if self.nodes_explored % 1000 == 0:
                iteration += 1
                self.history['Iteration'].append(iteration)
                self.history['Time'].append(time.time() - start_time)
                self.history['Best Objective'].append(self.best_cost)
                self.history['Nodes Explored'].append(self.nodes_explored)
                self.history['Lower Bound'].append(min(node.bound for node in pq) if pq else float('inf'))
        
        total_time = time.time() - start_time
        
        if verbose:
            print(f"B&B completed: {self.nodes_explored} nodes explored in {total_time:.2f} seconds")
            print(f"Best cost found: {self.best_cost:.2f}")
        
        # Construct final solution
        solution = self._construct_solution()
        
        # Validate solution
        valid = problem.check_valid_solution(solution)
        if not valid and verbose:
            print("Warning: Solution from Branch and Bound is not valid according to problem constraints.")
            
        # Set tour length
        solution.set_tour_length(self.best_cost if valid else float('inf'))
        
        # Create convergence plot if requested
        if plot_path:
            self.plot_history(plot_path)
        
        return solution
    
    def calculate_bound(self, path, remaining_customers):
        """
        Calculate a lower bound for the current path and remaining customers.
        Uses a minimum spanning tree (MST) based heuristic.
        """
        if not remaining_customers:
            # If all customers are visited, bound is the cost to return to depot
            if path[-1] != self.node_id_to_index[self.problem.get_depot_id()]:
                return self.distances[path[-1]][self.node_id_to_index[self.problem.get_depot_id()]]
            return 0
        
        # Calculate minimum edge costs for each remaining customer
        min_costs = []
        
        # Current location
        current_idx = path[-1]
        
        # For each remaining customer, find its closest neighbor
        for customer_idx in remaining_customers:
            # Distance from current location
            cost1 = self.distances[current_idx][customer_idx]
            
            # Distance to closest other customer or back to depot
            min_cost = float('inf')
            depot_idx = self.node_id_to_index[self.problem.get_depot_id()]
            
            # Check cost to depot
            min_cost = min(min_cost, self.distances[customer_idx][depot_idx])
            
            # Check cost to other remaining customers
            for other_idx in remaining_customers:
                if other_idx != customer_idx:
                    min_cost = min(min_cost, self.distances[customer_idx][other_idx])
            
            min_costs.append(cost1 + min_cost)
        
        # Sum of minimum costs is a lower bound
        return sum(sorted(min_costs)[:1])  # Use the minimum cost customer
    
    def _construct_solution(self):
        """
        Construct a Solution object from the best path found.
        """
        if not self.best_solution:
            return Solution([])  # Empty solution if none found
        
        solution = Solution()
        
        # Split the path at depot occurrences
        depot_idx = self.node_id_to_index[self.problem.get_depot_id()]
        tours = []
        current_tour = []
        
        for idx in self.best_solution:
            if idx == depot_idx and current_tour:  # End of a tour
                tours.append(current_tour)
                current_tour = []
            elif idx != depot_idx:  # Add to current tour
                current_tour.append(self.index_to_node[idx])
        
        # Add the last tour if not empty
        if current_tour:
            tours.append(current_tour)
        
        # Add tours to solution
        for tour in tours:
            solution.add_tour(tour)
        
        return solution
    
    def plot_history(self, path):
        """
        Plot the convergence history of the algorithm.
        """
        df = pd.DataFrame(self.history)
        
        # Create a figure with subplots
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 10))
        
        # Plot objective value and lower bound vs iteration
        ax1.plot(df['Iteration'], df['Best Objective'], 'b-', label='Best Objective')
        ax1.plot(df['Iteration'], df['Lower Bound'], 'r--', label='Lower Bound')
        ax1.set_xlabel('Iteration')
        ax1.set_ylabel('Objective Value')
        ax1.set_title('Branch and Bound Convergence')
        ax1.legend()
        ax1.grid(True)
        
        # Plot nodes explored vs time
        ax2.plot(df['Time'], df['Nodes Explored'], 'g-')
        ax2.set_xlabel('Time (s)')
        ax2.set_ylabel('Nodes Explored')
        ax2.set_title('Search Tree Exploration Progress')
        ax2.grid(True)
        
        plt.tight_layout()
        plt.savefig(path)
        plt.close()