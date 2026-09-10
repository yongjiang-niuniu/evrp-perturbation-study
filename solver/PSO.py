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

class Particle:
    """
    Represents a particle in the PSO algorithm for EVRP.
    
    Each particle contains:
    - Current solution (position)
    - Personal best solution
    - Velocity (represented as a list of operations)
    """
    def __init__(self, solution=None):
        self.current_solution = solution if solution else Solution()
        self.pbest_solution = deepcopy(solution) if solution else Solution()
        self.velocity = []  # List of operations to apply
        self.iteration_since_improvement = 0
        
    def update_pbest(self):
        """Update the personal best if current solution is better"""
        if self.current_solution.get_tour_length() < self.pbest_solution.get_tour_length():
            self.pbest_solution = deepcopy(self.current_solution)
            self.iteration_since_improvement = 0
            return True
        else:
            self.iteration_since_improvement += 1
            return False


class ParticleSwarmOptimization:
    """
    PSO implementation for the Electric Vehicle Routing Problem (EVRP).
    
    This implementation adapts PSO for the discrete nature of EVRP by:
    - Representing positions as EVRP solutions (tours)
    - Using discrete movement operators (swap, insert, invert)
    - Adapting velocity and position updates for the discrete space
    """
    
    def __init__(self, num_particles=50, iterations=400, w=0.9, c1=2.0, c2=2.0,
                 w_min=0.4, intensive_search=True, local_search_freq=3, seed=None):
        """
        Initialize PSO parameters.
        
        Args:
            num_particles: Number of particles in the swarm
            iterations: Maximum number of iterations
            w: Inertia weight
            c1: Cognitive coefficient (personal best influence)
            c2: Social coefficient (global best influence)
            w_min: Minimum inertia weight (for decreasing inertia)
            intensive_search: Whether to apply intensive local search
            local_search_freq: Frequency of local search application
            seed: Random seed
        """
        if seed is not None:
            np.random.seed(seed)
            random.seed(seed)
            
        self.num_particles = num_particles
        self.max_iterations = iterations
        self.w_initial = w  # Initial inertia weight
        self.w = w  # Current inertia weight
        self.w_min = w_min  # Minimum inertia weight
        self.c1 = c1  # Cognitive coefficient
        self.c2 = c2  # Social coefficient
        self.intensive_search = intensive_search
        self.local_search_freq = local_search_freq
        
        self.particles = []
        self.gbest_solution = None
        self.gs = GreedySearch()  # For local optimization
        
        self.history = {
            'Mean Fitness': [],
            'Best Fitness': [],
            'Time': []
        }
        
        # Operation probabilities - initially balanced
        self.op_probs = {
            'swap': 0.4,
            'insert': 0.3,
            'invert': 0.3
        }
        
    def set_problem(self, problem: Problem):
        """Set the EVRP problem instance"""
        self.problem = problem
        self.gs.set_problem(problem)
        self.depot = problem.get_depot()
        self.depot_id = problem.get_depot_id()
        
        # Calculate customer distances to use for nearest neighbor info
        self.customer_distances = {}
        self.customer_nearest = {}
        customers = problem.get_all_customers()
        
        for i, cust1 in enumerate(customers):
            cust_id = cust1.get_id()
            self.customer_distances[cust_id] = {}
            
            # Calculate distances to all other customers
            for cust2 in customers:
                self.customer_distances[cust_id][cust2.get_id()] = cust1.distance(cust2)
            
            # Sort customers by distance
            sorted_customers = sorted([(cust2.get_id(), cust1.distance(cust2)) 
                                     for cust2 in customers if cust2.get_id() != cust_id],
                                     key=lambda x: x[1])
            
            # Store nearest neighbors
            self.customer_nearest[cust_id] = [c[0] for c in sorted_customers[:10]]  # Top 10 nearest
        
        # Initialize particles
        self.initialize_particles()
        
    def initialize_particles(self):
        """Initialize particles with diverse solutions"""
        self.particles = []
        
        # Create initial solutions with different methods
        for i in range(self.num_particles):
            # Mix of initialization methods
            if i < self.num_particles * 0.4:  # Increased proportion of greedy solutions
                # Use greedy initialization for 40% of particles
                solution = self.gs.solve(self.problem, verbose=False)
            else:
                # Use randomized greedy initialization with varying randomness
                solution = self.create_diverse_solution(i)
            
            # Create a particle with this solution
            particle = Particle(solution)
            self.particles.append(particle)
            
            # Update global best if needed
            if self.gbest_solution is None or solution.get_tour_length() < self.gbest_solution.get_tour_length():
                self.gbest_solution = deepcopy(solution)
                
    def create_diverse_solution(self, seed_index):
        """Create a diverse solution for particle initialization"""
        # Create a basic solution
        solution = self.gs.init_solution()
        
        # Apply randomization based on seed index
        random.seed(seed_index * 100 + 42)
        
        # Apply various perturbations based on seed
        perturbation_level = (seed_index % 5) + 1
        for _ in range(perturbation_level):
            solution = self.apply_random_operation(solution)
        
        # Optimize the solution but apply different levels of optimization
        # based on seed to maintain diversity
        if seed_index % 3 == 0:
            # Fully optimize
            solution = self.gs.optimize(solution)
        elif seed_index % 3 == 1:
            # Apply light optimization (custom lighter version)
            solution = self.light_optimize(solution)
        else:
            # Keep as is for diversity
            solution = self.repair_solution(solution)
            solution.set_tour_length(self.problem.calculate_tour_length(solution))
            
        return solution
    
    def light_optimize(self, solution):
        """Apply lighter optimization to maintain solution diversity"""
        # Basic repair
        solution = self.repair_solution(solution)
        
        # Apply only route optimization without charging station insertion
        # This is a lighter version of the gs.optimize
        tours = solution.get_tours()
        
        # Apply 2-opt to each tour
        for tour_idx, tour in enumerate(tours):
            if len(tour) >= 3:
                # Simple 2-opt implementation
                improved = True
                while improved:
                    improved = False
                    tour_with_depot = [self.depot] + tour + [self.depot]
                    best_length = sum(tour_with_depot[j].distance(tour_with_depot[j+1]) 
                                    for j in range(len(tour_with_depot)-1))
                    
                    # Try a sample of possible 2-opt moves to save time
                    num_tries = min(10, len(tour) * (len(tour)-1) // 2)
                    for _ in range(num_tries):
                        a = random.randint(1, len(tour_with_depot)-3)
                        b = random.randint(a+1, len(tour_with_depot)-2)
                        
                        # Create new tour by reversing segment a to b
                        new_tour = tour_with_depot.copy()
                        new_tour[a:b+1] = reversed(new_tour[a:b+1])
                        
                        # Calculate new length
                        new_length = sum(new_tour[k].distance(new_tour[k+1]) 
                                    for k in range(len(new_tour)-1))
                        
                        if new_length < best_length:
                            tour_with_depot = new_tour
                            best_length = new_length
                            improved = True
                    
                    tour = tour_with_depot[1:-1]  # Remove depot
                
                tours[tour_idx] = tour  # Use tour_idx instead of i
        
        solution.set_vehicle_tours(tours)
        solution.set_tour_length(self.problem.calculate_tour_length(solution))
        return solution
    
    def apply_random_operation(self, solution):
        """
        Apply a random operation to the solution for diversification.
        
        Args:
            solution: The solution to modify
            
        Returns:
            Solution: The modified solution
        """
        tours = solution.get_tours()
        
        # If no tours, can't apply operations
        if not tours or all(len(tour) == 0 for tour in tours):
            return solution
        
        # Choose a random operation type based on probabilities
        op_type = random.choices(list(self.op_probs.keys()), 
                               weights=list(self.op_probs.values()))[0]
        
        if op_type == 'swap':
            # Swap two nodes within a tour
            valid_tours = [i for i, tour in enumerate(tours) if len(tour) >= 2]
            if not valid_tours:
                return solution
                
            tour_idx = random.choice(valid_tours)
            i = random.randint(0, len(tours[tour_idx])-1)
            j = random.randint(0, len(tours[tour_idx])-1)
            while i == j:
                j = random.randint(0, len(tours[tour_idx])-1)
                
            tours[tour_idx][i], tours[tour_idx][j] = tours[tour_idx][j], tours[tour_idx][i]
        
        elif op_type == 'insert':
            # Move a node from one tour to another
            if len(tours) < 2:
                return solution
                
            # Find tours with nodes to move
            non_empty_tours = [i for i, tour in enumerate(tours) if len(tour) > 0]
            if not non_empty_tours:
                return solution
                
            from_tour = random.choice(non_empty_tours)
            node_idx = random.randint(0, len(tours[from_tour])-1)
            
            # Select target tour, different from source
            to_tour_candidates = [i for i in range(len(tours)) if i != from_tour]
            if not to_tour_candidates:
                # If no other tour, create a new one
                to_tour = len(tours)
                tours.append([])
            else:
                to_tour = random.choice(to_tour_candidates)
            
            # Determine best insert position based on distance
            node = tours[from_tour][node_idx]
            if len(tours[to_tour]) == 0:
                insert_pos = 0
            else:
                # Try to insert at position that minimizes distance
                best_pos = 0
                best_delta = float('inf')
                
                for pos in range(len(tours[to_tour]) + 1):
                    if pos == 0:
                        prev_node = self.depot
                    else:
                        prev_node = tours[to_tour][pos-1]
                        
                    if pos == len(tours[to_tour]):
                        next_node = self.depot
                    else:
                        next_node = tours[to_tour][pos]
                    
                    # Calculate distance change
                    old_dist = prev_node.distance(next_node)
                    new_dist = prev_node.distance(node) + node.distance(next_node)
                    delta = new_dist - old_dist
                    
                    if delta < best_delta:
                        best_delta = delta
                        best_pos = pos
                
                insert_pos = best_pos
            
            # Move the node
            node = tours[from_tour].pop(node_idx)
            tours[to_tour].insert(insert_pos, node)
            
            # Remove empty tours
            tours = [tour for tour in tours if len(tour) > 0]
        
        elif op_type == 'invert':
            # Invert a subsequence within a tour
            valid_tours = [i for i, tour in enumerate(tours) if len(tour) >= 2]
            if not valid_tours:
                return solution
                
            tour_idx = random.choice(valid_tours)
            i = random.randint(0, len(tours[tour_idx])-2)
            j = random.randint(i+1, len(tours[tour_idx])-1)
            
            # Invert the subsequence
            tours[tour_idx][i:j+1] = reversed(tours[tour_idx][i:j+1])
        
        solution.set_vehicle_tours(tours)
        return solution
    
    def update_velocities_and_positions(self):
        """Update velocities and positions of all particles"""
        for particle in self.particles:
            # Calculate number of operations based on iteration progress
            # Fixed formula to avoid division by zero
            num_ops = max(1, int(3 + 2 * (self.w - self.w_min) / (self.w_initial - self.w_min)))
            
            # Generate new velocity (list of operations)
            new_velocity = []
            
            # Inertia component: keep some previous operations
            if particle.velocity and random.random() < self.w:
                # Keep more operations if particle is improving
                if particle.iteration_since_improvement < 5:
                    keep_fraction = min(0.8, self.w)
                else:
                    keep_fraction = max(0.2, self.w / 2)  # Reduce if stagnating
                
                num_keep = max(1, min(len(particle.velocity), int(len(particle.velocity) * keep_fraction)))
                inertia_ops = random.sample(particle.velocity, num_keep)
                new_velocity.extend(inertia_ops)
            
            # Cognitive component: operations to move toward personal best
            if random.random() < self.c1:
                pbest_ops = self.generate_movement_operations(
                    particle.current_solution, particle.pbest_solution, num_ops)
                new_velocity.extend(pbest_ops)
            
            # Social component: operations to move toward global best
            if random.random() < self.c2:
                gbest_ops = self.generate_movement_operations(
                    particle.current_solution, self.gbest_solution, num_ops)
                new_velocity.extend(gbest_ops)
            
            # Exploration component: add some random operations
            if particle.iteration_since_improvement > 10:
                # Add more random operations if particle is stuck
                for _ in range(random.randint(1, 3)):
                    if random.random() < 0.3:
                        op_type = random.choice(list(self.op_probs.keys()))
                        # Create a random operation based on the type
                        if op_type == 'swap':
                            tours = particle.current_solution.get_tours()
                            if tours:
                                tour_idx = random.randint(0, len(tours)-1)
                                if len(tours[tour_idx]) >= 2:
                                    i = random.randint(0, len(tours[tour_idx])-1)
                                    j = random.randint(0, len(tours[tour_idx])-1)
                                    if i != j:
                                        new_velocity.append((op_type, tour_idx, i, j))
                        elif op_type == 'invert':
                            tours = particle.current_solution.get_tours()
                            if tours:
                                tour_idx = random.randint(0, len(tours)-1)
                                if len(tours[tour_idx]) >= 2:
                                    i = random.randint(0, len(tours[tour_idx])-2)
                                    j = random.randint(i+1, len(tours[tour_idx])-1)
                                    new_velocity.append((op_type, tour_idx, i, j))
            
            # Set the new velocity
            particle.velocity = new_velocity
            
            # Apply velocity to update position (current solution)
            particle.current_solution = self.apply_velocity(
                particle.current_solution, particle.velocity)
            
            # Ensure solution is valid and optimized
            optimization_level = random.random()
            if optimization_level < 0.3:
                # Light optimization (30% of the time)
                particle.current_solution = self.repair_solution(particle.current_solution)
                particle.current_solution.set_tour_length(self.problem.calculate_tour_length(particle.current_solution))
            elif optimization_level < 0.7:
                # Medium optimization (40% of the time)
                particle.current_solution = self.light_optimize(particle.current_solution)
            else:
                # Full optimization (30% of the time)
                particle.current_solution = self.optimize_solution(particle.current_solution)
            
            # Update personal best
            particle.update_pbest()
    
    def generate_movement_operations(self, from_solution, to_solution, num_ops):
        """
        Generate operations to move one solution toward another.
        Uses tour differences to create transformative operations.
        """
        operations = []
        
        # Get tour information
        from_tours = from_solution.get_tours()
        to_tours = to_solution.get_tours()
        
        if not from_tours or not to_tours:
            return operations
        
        # Analyze structural differences between solutions
        from_customers = {}
        to_customers = {}
        
        # Map customers to tours
        for i, tour in enumerate(from_tours):
            for node in tour:
                if node.is_customer():
                    from_customers[node.get_id()] = i
        
        for i, tour in enumerate(to_tours):
            for node in tour:
                if node.is_customer():
                    to_customers[node.get_id()] = i
        
        # Find customers that are in different tours
        different_tour_customers = []
        for cust_id, from_tour_idx in from_customers.items():
            if cust_id in to_customers and to_customers[cust_id] != from_tour_idx:
                different_tour_customers.append((cust_id, from_tour_idx, to_customers[cust_id]))
        
        # Prioritize moving customers that are in different tours
        for cust_id, from_tour_idx, to_tour_idx in different_tour_customers[:min(num_ops, len(different_tour_customers))]:
            # Find position of customer in from_tour
            cust_pos = -1
            for pos, node in enumerate(from_tours[from_tour_idx]):
                if node.is_customer() and node.get_id() == cust_id:
                    cust_pos = pos
                    break
            
            if cust_pos != -1 and to_tour_idx < len(from_tours):
                # Add insert operation to move customer to correct tour
                operations.append(('insert', from_tour_idx, cust_pos, to_tour_idx, 0))
        
        # Consider different structural changes
        if len(from_tours) != len(to_tours):
            # If different number of tours, add split/merge operations
            if len(from_tours) < len(to_tours):
                for _ in range(min(num_ops // 2, len(to_tours) - len(from_tours))):
                    tour_to_split = -1
                    for i, tour in enumerate(from_tours):
                        if len(tour) >= 4:  # Need at least 4 nodes to make splitting worthwhile
                            tour_to_split = i
                            break
                    
                    if tour_to_split != -1:
                        operations.append(('split', tour_to_split))
            else:
                for _ in range(min(num_ops // 2, len(from_tours) - len(to_tours))):
                    if len(from_tours) >= 2:
                        # Find two tours to merge
                        # Prefer merging small tours
                        tour_sizes = [(i, len(tour)) for i, tour in enumerate(from_tours)]
                        tour_sizes.sort(key=lambda x: x[1])
                        
                        if len(tour_sizes) >= 2:
                            operations.append(('merge', tour_sizes[0][0]))
        
        # Generate node-based difference operations
        remaining_ops = num_ops - len(operations)
        if remaining_ops > 0:
            # Use a mix of operations
            for _ in range(remaining_ops):
                op_type = random.choices(list(self.op_probs.keys()), 
                                      weights=list(self.op_probs.values()))[0]
                
                # Generate parameters based on operation type
                if op_type == 'swap' and from_tours:
                    valid_tours = [i for i, tour in enumerate(from_tours) if len(tour) >= 2]
                    if valid_tours:
                        tour_idx = random.choice(valid_tours)
                        i = random.randint(0, len(from_tours[tour_idx])-1)
                        j = random.randint(0, len(from_tours[tour_idx])-1)
                        while i == j:
                            j = random.randint(0, len(from_tours[tour_idx])-1)
                        operations.append((op_type, tour_idx, i, j))
                
                elif op_type == 'insert' and len(from_tours) >= 2:
                    # Move a node from one position to another
                    non_empty_tours = [i for i, tour in enumerate(from_tours) if len(tour) > 0]
                    if non_empty_tours:
                        from_tour = random.choice(non_empty_tours)
                        to_tour = random.randint(0, len(from_tours)-1)
                        while to_tour == from_tour and len(non_empty_tours) > 1:
                            to_tour = random.choice(non_empty_tours)
                        
                        node_idx = random.randint(0, len(from_tours[from_tour])-1)
                        insert_pos = random.randint(0, max(1, len(from_tours[to_tour])))
                        operations.append((op_type, from_tour, node_idx, to_tour, insert_pos))
                
                elif op_type == 'invert' and from_tours:
                    valid_tours = [i for i, tour in enumerate(from_tours) if len(tour) >= 2]
                    if valid_tours:
                        tour_idx = random.choice(valid_tours)
                        i = random.randint(0, len(from_tours[tour_idx])-2)
                        j = random.randint(i+1, len(from_tours[tour_idx])-1)
                        operations.append((op_type, tour_idx, i, j))
        
        return operations
    
    def apply_velocity(self, solution, velocity):
        """Apply velocity operations to a solution to create a new one"""
        new_solution = deepcopy(solution)
        tours = new_solution.get_tours()
        
        # Shuffle operations to reduce dependence on order
        random.shuffle(velocity)
        
        for operation in velocity:
            op_type = operation[0]
            
            if op_type == 'swap' and len(operation) == 4:
                # Swap two nodes within a tour
                tour_idx, i, j = operation[1], operation[2], operation[3]
                if (tour_idx < len(tours) and tours[tour_idx] and 
                    i < len(tours[tour_idx]) and j < len(tours[tour_idx])):
                    tours[tour_idx][i], tours[tour_idx][j] = tours[tour_idx][j], tours[tour_idx][i]
            
            elif op_type == 'insert' and len(operation) == 5:
                # Move a node from one tour to another
                from_tour, node_idx, to_tour, insert_pos = operation[1:]
                if (from_tour < len(tours) and tours[from_tour] and
                    node_idx < len(tours[from_tour])):
                    
                    # Ensure target tour exists
                    while to_tour >= len(tours):
                        tours.append([])
                    
                    # Move the node
                    node = tours[from_tour][node_idx]
                    tours[from_tour].pop(node_idx)
                    
                    # Insert at appropriate position
                    insert_pos = min(insert_pos, len(tours[to_tour]))
                    tours[to_tour].insert(insert_pos, node)
                    
                    # Clean up empty tours
                    if not tours[from_tour]:
                        tours.pop(from_tour)
                        # Adjust tour indices in subsequent operations
                        for i in range(len(velocity)):
                            if i > velocity.index(operation):
                                if velocity[i][0] == 'insert':
                                    if velocity[i][1] > from_tour:
                                        velocity[i] = (velocity[i][0], velocity[i][1]-1, 
                                                     velocity[i][2], velocity[i][3], velocity[i][4])
                                    if velocity[i][3] > from_tour:
                                        velocity[i] = (velocity[i][0], velocity[i][1], 
                                                     velocity[i][2], velocity[i][3]-1, velocity[i][4])
            
            elif op_type == 'invert' and len(operation) == 4:
                # Invert a subsequence
                tour_idx, i, j = operation[1], operation[2], operation[3]
                if (tour_idx < len(tours) and tours[tour_idx] and
                    i < len(tours[tour_idx]) and j < len(tours[tour_idx])):
                    tours[tour_idx][i:j+1] = reversed(tours[tour_idx][i:j+1])
            
            elif op_type == 'split' and len(operation) == 2:
                # Split a tour into two
                tour_idx = operation[1]
                if tour_idx < len(tours) and len(tours[tour_idx]) >= 4:
                    # Find a good split point based on customer clustering
                    # Group customers that are close to each other
                    nodes_with_coords = [(node, node.get_x(), node.get_y()) for node in tours[tour_idx] if node.is_customer()]
                    
                    if len(nodes_with_coords) >= 2:
                        # Use k-means with k=2 for simple clustering
                        # Initialize centroids
                        centroids = [
                            (nodes_with_coords[0][1], nodes_with_coords[0][2]),
                            (nodes_with_coords[-1][1], nodes_with_coords[-1][2])
                        ]
                        
                        # Simple k-means implementation
                        for _ in range(3):  # 3 iterations should be enough
                            # Assign nodes to clusters
                            clusters = [[], []]
                            for node, x, y in nodes_with_coords:
                                # Calculate distance to centroids
                                dist_0 = np.sqrt((x - centroids[0][0])**2 + (y - centroids[0][1])**2)
                                dist_1 = np.sqrt((x - centroids[1][0])**2 + (y - centroids[1][1])**2)
                                
                                # Assign to closest cluster
                                if dist_0 < dist_1:
                                    clusters[0].append((node, x, y))
                                else:
                                    clusters[1].append((node, x, y))
                            
                            # Update centroids
                            for i in range(2):
                                if clusters[i]:
                                    centroids[i] = (
                                        sum(n[1] for n in clusters[i]) / len(clusters[i]),
                                        sum(n[2] for n in clusters[i]) / len(clusters[i])
                                    )
                        
                        # Get nodes in each cluster
                        cluster_nodes = [[n[0] for n in cluster] for cluster in clusters if cluster]
                        
                        if len(cluster_nodes) > 1 and all(cluster_nodes):
                            # Create a new tour with nodes from second cluster
                            new_tour = []
                            remaining_tour = []
                            
                            for node in tours[tour_idx]:
                                if node in cluster_nodes[1]:
                                    new_tour.append(node)
                                else:
                                    remaining_tour.append(node)
                            
                            tours[tour_idx] = remaining_tour
                            tours.append(new_tour)
            
            elif op_type == 'merge' and len(operation) == 2:
                # Merge two consecutive tours
                tour_idx = operation[1]
                if tour_idx < len(tours) - 1:
                    tours[tour_idx].extend(tours[tour_idx+1])
                    tours.pop(tour_idx+1)
        
        # Remove any empty tours
        tours = [tour for tour in tours if tour]
        
        new_solution.set_vehicle_tours(tours)
        return new_solution
    
    def optimize_solution(self, solution):
        """Apply local search optimization to improve solution quality"""
        # Basic validation and repair
        solution = self.repair_solution(solution)
        
        # Apply greedy search optimization
        solution = self.gs.optimize(solution)
        
        # Add specialized optimization procedures
        if self.intensive_search and random.random() < 0.3:
            solution = self.apply_2opt_search(solution)
        
        # Recalculate tour length
        solution.set_tour_length(self.problem.calculate_tour_length(solution))
        return solution
    
    def repair_solution(self, solution):
        """Repair invalid solutions"""
        tours = solution.get_tours()
        
        # Check for empty tours
        tours = [tour for tour in tours if len(tour) > 0]
        
        # Ensure all customers are visited exactly once
        customer_visits = {}
        for tour in tours:
            for node in tour:
                if node.is_customer():
                    node_id = node.get_id()
                    customer_visits[node_id] = customer_visits.get(node_id, 0) + 1
        
        # Collect unvisited customers
        unvisited = [customer_id for customer_id in self.problem.get_customer_ids() 
                  if customer_id not in customer_visits]
        
        # Add unvisited customers
        for customer_id in unvisited:
            customer = self.problem.get_node_from_id(customer_id)
            # Find best tour to add to based on nearest neighbor
            best_tour_idx = 0
            best_insertion_score = float('inf')
            best_pos = 0
            
            for i, tour in enumerate(tours):
                if tour:
                    # Try different insertion positions
                    for pos in range(len(tour) + 1):
                        if pos == 0:
                            prev_node = self.depot
                        else:
                            prev_node = tour[pos-1]
                            
                        if pos == len(tour):
                            next_node = self.depot
                        else:
                            next_node = tour[pos]
                        
                        # Calculate insertion cost
                        old_dist = prev_node.distance(next_node)
                        new_dist = prev_node.distance(customer) + customer.distance(next_node)
                        insertion_score = new_dist - old_dist
                        
                        # Check tour capacity after insertion
                        new_capacity = sum(node.get_demand() for node in tour if node.is_customer())
                        new_capacity += customer.get_demand()
                        
                        # Penalize if near capacity limit
                        if new_capacity > self.problem.get_capacity() * 0.9:
                            insertion_score *= 1.5
                        
                        if insertion_score < best_insertion_score and new_capacity <= self.problem.get_capacity():
                            best_insertion_score = insertion_score
                            best_tour_idx = i
                            best_pos = pos
            
            # Add to best tour
            if tours:
                if best_insertion_score < float('inf'):
                    # Insert at best position
                    tours[best_tour_idx].insert(best_pos, customer)
                else:
                    # Create a new tour if no good insertion found
                    tours.append([customer])
            else:
                tours.append([customer])
        
        # Remove duplicate visits
        for tour_idx, tour in enumerate(tours):
            unique_nodes = []
            seen = set()
            
            for node in tour:
                if node.is_customer():
                    node_id = node.get_id()
                    if node_id not in seen:
                        unique_nodes.append(node)
                        seen.add(node_id)
                else:
                    unique_nodes.append(node)
            
            tours[tour_idx] = unique_nodes
        
        # Balance tours if needed
        if len(tours) > 1:
            tours = self.balance_tours(tours)
        
        solution.set_vehicle_tours(tours)
        return solution
    
    def balance_tours(self, tours):
        """Balance load between tours"""
        # Calculate load of each tour
        tour_loads = [(i, sum(node.get_demand() for node in tour if node.is_customer())) 
                     for i, tour in enumerate(tours)]
        
        # Sort by load
        tour_loads.sort(key=lambda x: x[1])
        
        # Check if balancing is needed
        if len(tour_loads) >= 2:
            min_load = tour_loads[0][1]
            max_load = tour_loads[-1][1]
            
            # Only balance if significant difference
            if max_load > min_load * 1.5 and max_load > self.problem.get_capacity() * 0.7:
                # Get tours with highest and lowest load
                low_idx, low_load = tour_loads[0]
                high_idx, high_load = tour_loads[-1]
                
                # Try to move nodes from high load tour to low load tour
                moved = False
                for node_idx, node in enumerate(tours[high_idx]):
                    if node.is_customer():
                        demand = node.get_demand()
                        
                        # Check if move is feasible
                        if low_load + demand <= self.problem.get_capacity():
                            # Find best position in low tour
                            best_pos = 0
                            best_cost = float('inf')
                            
                            for pos in range(len(tours[low_idx]) + 1):
                                if pos == 0:
                                    prev_node = self.depot
                                else:
                                    prev_node = tours[low_idx][pos-1]
                                    
                                if pos == len(tours[low_idx]):
                                    next_node = self.depot
                                else:
                                    next_node = tours[low_idx][pos]
                                
                                # Calculate insertion cost
                                cost = prev_node.distance(node) + node.distance(next_node) - prev_node.distance(next_node)
                                
                                if cost < best_cost:
                                    best_cost = cost
                                    best_pos = pos
                            
                            # Move node
                            node = tours[high_idx].pop(node_idx)
                            tours[low_idx].insert(best_pos, node)
                            
                            # Update loads
                            low_load += demand
                            high_load -= demand
                            moved = True
                            break
                
                # If no movement possible, try another pair
                if not moved and len(tour_loads) >= 3:
                    low_idx, low_load = tour_loads[1]
                    high_idx, high_load = tour_loads[-1]
                    
                    for node_idx, node in enumerate(tours[high_idx]):
                        if node.is_customer():
                            demand = node.get_demand()
                            
                            # Check if move is feasible
                            if low_load + demand <= self.problem.get_capacity():
                                # Find best position in low tour
                                best_pos = 0
                                best_cost = float('inf')
                                
                                for pos in range(len(tours[low_idx]) + 1):
                                    if pos == 0:
                                        prev_node = self.depot
                                    else:
                                        prev_node = tours[low_idx][pos-1]
                                        
                                    if pos == len(tours[low_idx]):
                                        next_node = self.depot
                                    else:
                                        next_node = tours[low_idx][pos]
                                    
                                    # Calculate insertion cost
                                    cost = prev_node.distance(node) + node.distance(next_node) - prev_node.distance(next_node)
                                    
                                    if cost < best_cost:
                                        best_cost = cost
                                        best_pos = pos
                                
                                # Move node
                                node = tours[high_idx].pop(node_idx)
                                tours[low_idx].insert(best_pos, node)
                                break
        
        # Remove any empty tours after balancing
        tours = [tour for tour in tours if tour]
        return tours
    
    def apply_2opt_search(self, solution):
        """Apply 2-opt local search to improve tours"""
        tours = solution.get_tours()
        
        for i, tour in enumerate(tours):
            if len(tour) < 3:
                continue
            
            # Add depot for complete tour evaluation
            full_tour = [self.depot] + tour + [self.depot]
            improved = True
            
            while improved:
                improved = False
                best_distance = sum(full_tour[j].distance(full_tour[j+1]) 
                                 for j in range(len(full_tour)-1))
                
                # Try all possible 2-opt swaps
                for j in range(1, len(full_tour)-2):
                    for k in range(j+1, len(full_tour)-1):
                        # Create new tour by reversing segment j to k
                        new_tour = full_tour[:]
                        new_tour[j:k+1] = reversed(new_tour[j:k+1])
                        
                        # Calculate new distance
                        new_distance = sum(new_tour[m].distance(new_tour[m+1]) 
                                        for m in range(len(new_tour)-1))
                        
                        if new_distance < best_distance:
                            full_tour = new_tour
                            best_distance = new_distance
                            improved = True
                            break
                    
                    if improved:
                        break
            
            # Remove depot from optimized tour
            tours[i] = full_tour[1:-1]
        
        solution.set_vehicle_tours(tours)
        return solution
    
    def verify_solution_quality(self, solution):
        """Verify that a solution meets all constraints"""
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
        
        # 4. Verify tour length
        calculated_length = self.problem.calculate_tour_length(solution)
        if solution.get_tour_length() != calculated_length:
            solution.set_tour_length(calculated_length)
        
        return True, "Valid solution"
    
    def solve(self, problem: Problem, verbose=False, plot_path=None):
        """
        Run the PSO algorithm to solve the EVRP problem.
        
        Args:
            problem: The EVRP problem instance
            verbose: Whether to print progress information
            plot_path: Path to save convergence plot
            
        Returns:
            Solution: The best solution found
        """
        start_time = time()
        self.set_problem(problem)
        stagnation_counter = 0
        last_improvement = 0
        
        # Record initial best fitness
        initial_best = self.gbest_solution.get_tour_length()
        
        # Main PSO loop
        for iteration in range(self.max_iterations):
            iter_start_time = time()
            
            # Update inertia weight (decreasing strategy)
            self.w = max(self.w_min, self.w_initial - (self.w_initial - self.w_min) * iteration / self.max_iterations)
            
            # Adjust operation probabilities based on progress
            if iteration > self.max_iterations // 2 and stagnation_counter > 10:
                # If stuck in second half, increase invert probability for diversity
                self.op_probs = {'swap': 0.3, 'insert': 0.2, 'invert': 0.5}
            elif iteration > self.max_iterations // 4:
                # Mid-search, balanced probabilities
                self.op_probs = {'swap': 0.4, 'insert': 0.3, 'invert': 0.3}
            else:
                # Early search, favor insert for exploration
                self.op_probs = {'swap': 0.3, 'insert': 0.4, 'invert': 0.3}
            
            # Update velocities and positions
            self.update_velocities_and_positions()
            
            # Apply periodic intensive search to global best
            if iteration % self.local_search_freq == 0 or stagnation_counter > 15:
                intensified_solution = deepcopy(self.gbest_solution)
                for _ in range(3):  # Multiple optimization passes
                    intensified_solution = self.apply_2opt_search(intensified_solution)
                    intensified_solution = self.gs.optimize(intensified_solution)
                
                intensified_solution.set_tour_length(
                    self.problem.calculate_tour_length(intensified_solution))
                
                if intensified_solution.get_tour_length() < self.gbest_solution.get_tour_length():
                    self.gbest_solution = intensified_solution
                    stagnation_counter = 0
                    last_improvement = iteration
            
            # Update global best
            for particle in self.particles:
                if (particle.current_solution.get_tour_length() < self.gbest_solution.get_tour_length() and
                    self.problem.check_valid_solution(particle.current_solution)):
                    self.gbest_solution = deepcopy(particle.current_solution)
                    stagnation_counter = 0
                    last_improvement = iteration
                    
                    # Extra optimization on improvement
                    if random.random() < 0.5:
                        self.gbest_solution = self.apply_2opt_search(self.gbest_solution)
                        self.gbest_solution.set_tour_length(self.problem.calculate_tour_length(self.gbest_solution))
            
            # Calculate statistics
            valid_solutions = [p.current_solution for p in self.particles 
                            if self.problem.check_valid_solution(p.current_solution)]
            
            if valid_solutions:
                mean_fitness = np.mean([sol.get_tour_length() for sol in valid_solutions])
            else:
                mean_fitness = float('inf')
            
            # Update history for plotting
            self.history['Mean Fitness'].append(mean_fitness)
            self.history['Best Fitness'].append(self.gbest_solution.get_tour_length())
            self.history['Time'].append(time() - start_time)
            
            if verbose:
                iter_time = time() - iter_start_time
                improvement = (initial_best - self.gbest_solution.get_tour_length()) / initial_best * 100
                print(f"Iteration {iteration+1}/{self.max_iterations}, "
                      f"Valid solutions: {len(valid_solutions)}/{self.num_particles}, "
                      f"Mean fitness: {mean_fitness:.2f}, "
                      f"Best fitness: {self.gbest_solution.get_tour_length():.4f}, "
                      f"Improvement: {improvement:.2f}%, "
                      f"Time: {iter_time:.2f}s")
            
            # Increment stagnation counter if no improvement
            if iteration != last_improvement:
                stagnation_counter += 1
            
            # Apply perturbation to particles if stuck
            if stagnation_counter > 20 and stagnation_counter % 5 == 0:
                if verbose:
                    print(f"Applying perturbation at iteration {iteration+1}")
                
                # Perturb a portion of the particles
                num_to_perturb = max(5, self.num_particles // 4)
                particles_to_perturb = random.sample(self.particles, num_to_perturb)
                
                for particle in particles_to_perturb:
                    # Randomly decide perturbation type
                    perturb_type = random.choice(['reset', 'heavy_mutation', 'crossover'])
                    
                    if perturb_type == 'reset':
                        # Reset to a new random solution
                        particle.current_solution = self.create_diverse_solution(random.randint(0, 1000))
                    elif perturb_type == 'heavy_mutation':
                        # Apply multiple random operations
                        solution = deepcopy(particle.current_solution)
                        for _ in range(5):
                            solution = self.apply_random_operation(solution)
                        particle.current_solution = self.optimize_solution(solution)
                    elif perturb_type == 'crossover':
                        # Crossover with global best
                        solution = deepcopy(particle.current_solution)
                        ops = self.generate_movement_operations(solution, self.gbest_solution, 10)
                        solution = self.apply_velocity(solution, ops)
                        particle.current_solution = self.optimize_solution(solution)
            
            # Check for early convergence
            if iteration > self.max_iterations // 2:
                last_improvements = self.history['Best Fitness'][-10:]
                if len(last_improvements) >= 10 and all(abs(last_improvements[0] - x) < 0.001 for x in last_improvements):
                    if verbose:
                        print(f"Early stopping at iteration {iteration+1} due to convergence")
                    break
        
        # Final optimization push - apply intensive search to best solution
        final_solution = deepcopy(self.gbest_solution)
        if verbose:
            print("Applying final optimization...")
            
        # Multiple optimization passes with different techniques
        for i in range(5):
            if i % 2 == 0:
                # Apply 2-opt search
                final_solution = self.apply_2opt_search(final_solution)
            else:
                # Apply greedy optimization
                final_solution = self.gs.optimize(final_solution)
                
            final_solution.set_tour_length(self.problem.calculate_tour_length(final_solution))
            
            if verbose:
                print(f"  Pass {i+1}: {final_solution.get_tour_length():.4f}")
        
        # Use the better of the two solutions
        if final_solution.get_tour_length() < self.gbest_solution.get_tour_length():
            self.gbest_solution = final_solution
            if verbose:
                print(f"Final optimization improved solution to: {self.gbest_solution.get_tour_length():.4f}")
        
        # Plot convergence if requested
        if plot_path:
            self.plot_history(plot_path)
        
        # Final validation and output
        total_time = time() - start_time
        is_valid, message = self.verify_solution_quality(self.gbest_solution)
        
        if verbose:
            print(f"PSO completed, best fitness: {self.gbest_solution.get_tour_length():.4f}, total time: {total_time:.2f}s")
            print(f"Solution validity: {is_valid}, {message}")
            
            # Print optimal value if known
            if hasattr(problem, 'optimal_value') and problem.optimal_value is not None:
                gap = (self.gbest_solution.get_tour_length() - problem.optimal_value) / problem.optimal_value * 100
                print(f"Optimal value: {problem.optimal_value:.4f}, gap: {gap:.2f}%")
            
            if not is_valid:
                print(f"WARNING: Final solution is invalid! Reason: {message}")
        
        return self.gbest_solution
    
    def plot_history(self, path):
        """Plot the convergence history"""
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
        ax1.set_xlabel('Iteration')
        ax1.set_ylabel('Fitness (Tour Length)')
        ax2.set_ylabel('Time (seconds)')
        
        # Combine legends
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right')
        
        # Set title and grid
        plt.title(f'PSO Convergence Trend ({self.problem.get_name()})')
        ax1.grid(True)
        
        plt.tight_layout()
        plt.savefig(path)
        plt.close()
        
    def multi_start_solve(self, problem: Problem, num_starts=5, verbose=False, plot_path=None):
        """
        Run PSO multiple times with different seeds to find the best solution.
        
        Args:
            problem: The EVRP problem instance
            num_starts: Number of independent runs
            verbose: Whether to print progress information
            plot_path: Path to save convergence plot
            
        Returns:
            Solution: The best solution found across all runs
        """
        best_solution = None
        best_fitness = float('inf')
        
        for i in range(num_starts):
            if verbose:
                print(f"\n{'='*50}")
                print(f"Starting PSO run {i+1}/{num_starts}")
                print(f"{'='*50}")
                
            # Use different seed for each run
            seed = i * 100 + 42
            
            # Reinitialize PSO with new seed
            pso = ParticleSwarmOptimization(
                num_particles=50,
                iterations=400,
                w=0.9,
                c1=2.0,
                c2=2.0,
                w_min=0.4,
                intensive_search=True,
                local_search_freq=3,
                seed=seed
            )
            
            # Run PSO
            run_path = plot_path.replace('.png', f'_run{i+1}.png') if plot_path else None
            solution = pso.solve(problem, verbose=verbose, plot_path=run_path)
            
            # Check if this is the best solution so far
            if solution.get_tour_length() < best_fitness:
                best_fitness = solution.get_tour_length()
                best_solution = deepcopy(solution)
                
            if verbose:
                print(f"\nRun {i+1} complete. Best fitness: {best_fitness:.4f}")
                
                # Print gap to optimal if known
                if hasattr(problem, 'optimal_value') and problem.optimal_value is not None:
                    gap = (best_fitness - problem.optimal_value) / problem.optimal_value * 100
                    print(f"Gap to optimal: {gap:.2f}%")
        
        return best_solution