
from copy import deepcopy
from random import shuffle
import time
from loguru import logger
import numpy as np
from problem import Problem
from solution import Solution


class GreedySearch():

    def set_problem(self, problem: Problem):
        self.problem = problem
        self.nearest_dist_customer_matrix = {}
        self.calc_nearest_dist_customer_matrix()
    
    def init_solution(self) -> Solution:
        solution = self.create_clustering_solution()
        solution = self.balancing_capacity(solution)
        return solution
   
    # core optimize process 
    def optimize(self, solution: Solution) -> Solution:
        solution = self.local_search(solution)
        solution = self.insert_depots(solution)
        solution = self.insert_charging_stations(solution)
        solution = self.greedy_optimize_stations(solution)
        solution.set_tour_length(self.problem.calculate_tour_length(solution))
        return solution

    def solve(self, problem, verbose=False) -> Solution:
        self.set_problem(problem)
        self.verbose = verbose
        solution = self.init_solution()
        solution = self.optimize(solution)
        return solution
    
    def calc_nearest_dist_customer_matrix(self):
        """
        Precompute the nearest neighbor relationships:
        1. Between customers (used for clustering and route balancing).
        2. Between each node (customers, charging stations, depot) and the nearest charging stations.
        
        This speeds up route optimization by allowing quick lookups instead of recalculating distances repeatedly.
        """

        # Retrieve all customers from the problem instance
        all_customers = self.problem.get_all_customers()
        
        # Dictionary to store the nearest customers for each customer
        self.nearest_dist_customer_matrix = {}

        # Compute nearest neighbors for each customer
        for i in range(len(all_customers)):
            distances = []  # List to store distances from the current customer to all other customers
            for j in range(len(all_customers)):
                distances.append(all_customers[i].distance(all_customers[j]))  # Compute Euclidean distance
            
            # Sort indices based on shortest distance (closest customers first)
            argsort_dist = np.argsort(distances)

            # Store sorted nearest customer IDs, excluding itself
            self.nearest_dist_customer_matrix[all_customers[i].get_id()] = \
                [all_customers[j].get_id() for j in argsort_dist if i != j]

        # Retrieve all charging stations from the problem instance
        all_charging_stations = self.problem.get_all_stations()
        
        # Dictionary to store the nearest charging stations for each node (customer, station, depot)
        self.nearest_dist_charging_matrix = {}

        # Create a list of all nodes including:
        # - Customers
        # - Charging stations
        # - Depot (used as a charging station)
        all_nodes = all_customers + all_charging_stations + [self.problem.get_depot()]

        # Compute nearest charging station for each node
        for i in range(len(all_nodes)):
            distances = []  # List to store distances from the current node to all charging stations
            for j in range(len(all_charging_stations)):
                distances.append(all_nodes[i].distance(all_charging_stations[j]))  # Compute distance
            
            # Sort by nearest charging stations
            argsort_dist = np.argsort(distances)

            # Store sorted nearest charging station IDs
            self.nearest_dist_charging_matrix[all_nodes[i].get_id()] = \
                [all_charging_stations[j].get_id() for j in argsort_dist]

            
                
    def create_clustering_solution(self) -> Solution:
        """
        Creates an initial solution by clustering customers into tours based on vehicle capacity.
        Uses a greedy approach to assign customers to vehicles while ensuring capacity constraints.
        """

        # Initialize an empty solution
        solution = Solution()

        # Get a list of all customer IDs
        node_list = self.problem.get_customer_ids()

        # Maximum capacity of a vehicle
        capacity_max = self.problem.get_capacity()

        # Shuffle the list of customers to introduce randomness in clustering
        shuffle(node_list)

        # Array to track visited customers
        skipping_nodes = np.zeros(self.problem.get_num_dimensions())

        # Index for iterating through customers
        idx = 0

        # Count of vehicle tours created
        n_tours = 0

        # Assign customers to vehicle tours
        while idx < len(node_list):
            # Skip already assigned customers
            if skipping_nodes[node_list[idx]] == 1:
                idx += 1
                continue

            # Select the current node as the center of a new tour
            center_node = node_list[idx]

            # Increment the number of tours
            n_tours += 1

            # If maximum number of vehicles is reached, assign remaining customers to the last tour
            if n_tours == self.problem.get_max_num_vehicles():
                remaining_nodes = [self.problem.get_node_from_id(node_id) for node_id in node_list if skipping_nodes[node_id] == 0]
                solution.add_tour(remaining_nodes)
                break

            # Mark the selected center node as visited
            skipping_nodes[center_node] = 1

            # Initialize a new tour with the center node
            tour = [center_node]

            # Track the current load of the vehicle
            capacity = self.problem.get_node_from_id(center_node).get_demand()

            # Assign the nearest customers to the same tour while maintaining capacity constraints
            for candidate_node_id in self.nearest_dist_customer_matrix[center_node]:
                if skipping_nodes[candidate_node_id] == 0:
                    demand = self.problem.get_node_from_id(candidate_node_id).get_demand()

                    # Stop adding customers if the vehicle reaches its capacity limit
                    if capacity + demand > capacity_max:
                        break

                    # Add the customer to the tour
                    tour.append(candidate_node_id)

                    # Mark the customer as visited
                    skipping_nodes[candidate_node_id] = 1

                    # Update the vehicle's current load
                    capacity += demand

            # Convert customer IDs to node objects and add the tour to the solution
            solution.add_tour([self.problem.get_node_from_id(tour[i]) for i in range(len(tour))])

        # If there are fewer tours than the available number of vehicles, add empty tours
        while n_tours < self.problem.get_max_num_vehicles():
            n_tours += 1
            solution.add_tour([])

        # Set the tour index for tracking customer assignments
        solution.set_tour_index()

        # Return the initialized solution
        return solution

    
    def balancing_capacity(self, solution: Solution) -> Solution:
        """
        Balances the load across vehicle tours by moving customers from overloaded tours to underutilized ones.
        Ensures that the last tour is not significantly underloaded while maintaining capacity constraints.
        """

        # Get all vehicle tours
        tours = solution.get_tours()

        # Identify the last tour (potentially underloaded)
        last_tour_idx = len(solution.get_tours()) - 1
        last_tour = tours[last_tour_idx]

        # Dictionary to track customers already in the last tour
        is_customer_in_last_tour = {}

        # Calculate the total demand of customers in the last tour
        sum_demand = 0
        for node in last_tour:
            is_customer_in_last_tour[node.get_id()] = True
            sum_demand += node.get_demand()

        # If the last tour already meets or exceeds the vehicle's capacity, no balancing is needed
        if sum_demand >= self.problem.get_capacity():
            return solution

        # Randomly select a customer from the last tour to attempt reallocation
        rd_idx = np.random.randint(0, len(last_tour))
        moving_node_id = last_tour[rd_idx].get_id()

        # Iterate through the nearest customers to the selected customer
        for candidate_node_id in self.nearest_dist_customer_matrix[moving_node_id]:
            # Skip if the candidate is already in the last tour
            if candidate_node_id in is_customer_in_last_tour:
                continue

            # Get the demand of the candidate customer
            demand = self.problem.get_node_from_id(candidate_node_id).get_demand()

            # Identify the tour currently containing this customer
            candidate_tour_index = solution.get_tour_index_by_node(candidate_node_id)

            # Calculate the total demand of the current tour containing the candidate
            curr_tour_demand = sum([node.get_demand() for node in tours[candidate_tour_index]])

            # Compute the demand balance before and after moving the candidate customer
            new_delta = abs((sum_demand + demand) - (curr_tour_demand - demand))
            delta = abs(sum_demand - curr_tour_demand)

            # If moving the customer improves the balance and does not exceed the capacity, perform the move
            if new_delta < delta and sum_demand + demand <= self.problem.get_capacity():
                # Update the total demand of the last tour
                sum_demand += demand

                # Mark the candidate customer as part of the last tour
                is_customer_in_last_tour[candidate_node_id] = True

                # Add the customer to the last tour
                last_tour.append(self.problem.get_node_from_id(candidate_node_id))

                # Remove the customer from their original tour
                tours[candidate_tour_index] = [node for node in tours[candidate_tour_index] if node.get_id() != candidate_node_id]
                break

        # Update the solution with the modified tours
        solution.set_vehicle_tours(tours)

        return solution

    
    def local_search(self, solution: Solution) -> Solution:
        tours = solution.get_basic_tours()
        for i, tour in enumerate(tours):
            tours[i] = self.local_search_2opt(tour)
        solution.set_vehicle_tours(tours)
        return solution
    
    def local_search_2opt(self, tour):
        """
        Perform a local search using the 2-opt algorithm on the given tour.

        Args:
            tour (List[Node]): The initial tour to be optimized.

        Returns:
            List[Node]: The optimized tour after applying the 2-opt algorithm.

        Description:
            The 2-opt algorithm is a heuristic optimization algorithm for finding the shortest path in a graph.
            It repeatedly searches for a pair of edges that, if reversed, would result in a shorter path.
            This process is repeated until no further improvements can be made.

            The tour is initially extended by adding the depot node at the beginning and the end.
            Then, the algorithm iterates over all possible pairs of edges within the tour.
            For each pair, a new tour is created by reversing the order of the edges.
        """
        n = len(tour)
        tour = [self.problem.get_depot()] + tour + [self.problem.get_depot()]
        while True:
            improvement = False
            for i in range(1, n - 2):
                for j in range(i + 1, n):
                    if j - i == 1:
                        continue
                    new_tour = deepcopy(tour)
                    new_tour[i:j] = reversed(new_tour[i:j])
                    new_distance = sum([new_tour[k].distance(new_tour[k + 1]) for k in range(n - 1)])
                    if new_distance < sum([tour[k].distance(tour[k + 1]) for k in range(n - 1)]):
                        tour = new_tour
                        improvement = True
            if not improvement:
                break
        return tour[1:-1]

    
    def insert_depots(self, solution: Solution) -> Solution:
        vehicle_tours = solution.get_basic_tours()
        for i, tour in enumerate(vehicle_tours):
            vehicle_tours[i] = self.insert_depot_for_single_tour(tour)
        solution.set_vehicle_tours(vehicle_tours)
        return solution
    
    def insert_depot_for_single_tour(self, tour):
        """
        Inserts depots into a tour based on the tour's capacity and demand of nodes.
        The function ensures that the capacity constraint is satisfied for each vehicle.
        If the demand of a node is greater than the vehicle's capacity, the function inserts a depot,
        the vehicle back to the depot to get a new batch of goods and then continues the tour.
        """
        _tour = [self.problem.get_depot()]
        cappacity = self.problem.get_capacity()
        for node in tour:
            if node.is_customer():
                if node.get_demand() > cappacity:
                    _tour.append(self.problem.get_depot())
                    _tour.append(node)
                    cappacity = self.problem.get_capacity() - node.get_demand()
                else:
                    _tour.append(node)
                    cappacity -= node.get_demand()
            if node.is_depot():
                _tour.append(node)
                cappacity = self.problem.get_capacity()
                
        if not _tour[-1].is_depot():
            _tour.append(self.problem.get_depot())

        """
        Greedy optimization for depot position:
        
        Optimize the depot position if the vehicle needs to return to
        the depot during transportation due to exceeding capacity.
        depot -> c1 -> c2 -> depot -> c3 -> depot
        => 
        depot -> c1 -> depot -> c2 -> c3 -> depot
        if distance(c1, depot) + distance(depot, c2) + distance(c2, c3) < distance(c1, c2) + distance(c2, depot) + distance(depot, c3)
        and demand(c2) + demand(c3) <= max_capacity 
        then swap c2 and depot
        """
        
        curr_capacity = 0
        
        for i in reversed(range(len(_tour))):
            if i < 2 or i == len(_tour) - 1:
                continue
            
            node = _tour[i]
            if node.is_customer():
                curr_capacity += node.get_demand()
                
            if node.is_depot():
                c1 = _tour[i - 2]
                c2 = _tour[i - 1]
                depot = _tour[i]
                c3 = _tour[i + 1]
                
                d1 = self.problem.get_distance(c1, c2)
                d2 = self.problem.get_distance(c2, depot)
                d3 = self.problem.get_distance(depot, c3)
                
                new_d1 = self.problem.get_distance(c1, depot)
                new_d2 = self.problem.get_distance(depot, c2)
                new_d3 = self.problem.get_distance(c2, c3)
                
                demand_condition = c2.get_demand() + c3.get_demand() <= self.problem.get_capacity()
                distance_condition = d1 + d2 + d3 > new_d1 + new_d2 + new_d3
                
                if demand_condition and distance_condition:
                    _tour[i] = c2
                    _tour[i - 1] = depot
                    curr_capacity += c2.get_demand()
                else:
                    curr_capacity = 0
                
        return _tour
    
    def insert_charging_stations(self, solution: Solution) -> Solution:
        vehicle_tours = solution.get_tours()
        for i, tour in enumerate(vehicle_tours):
            vehicle_tours[i] = self.insert_charging_station_for_single_tour(tour)
        solution.set_vehicle_tours(vehicle_tours)
        return solution
    
    def insert_charging_station_for_single_tour(self, tour):
        remaining_energy = dict()
        min_required_energy = dict()
        complete_tour = []
        skip_node = dict()
        
        depotID = self.problem.get_depot_id()
        remaining_energy[depotID] = self.problem.get_battery_capacity()
        """
        At the current customer node, calculate the minimum energy required for an 
        electric vehicle to reach the nearest charging station.
        """
        for node in tour:
            nearest_station = self.nearest_station(node, node, self.problem.get_battery_capacity())
            min_required_energy[node.get_id()] = self.problem.get_energy_consumption(node, nearest_station)
        
        if len(tour) < 2:
            return tour
        
        i = 0
        from_node = tour[0]
        to_node = tour[1]
        
        while i < len(tour) - 1:
            
            """go ahead util energy is not enough for visiting the next node""" 
            energy_consumption = self.problem.get_energy_consumption(from_node, to_node)
            if energy_consumption <= remaining_energy[from_node.get_id()]:
                if to_node.is_charging_station():
                    remaining_energy[to_node.get_id()] = self.problem.get_battery_capacity()
                else:
                    remaining_energy_node = remaining_energy[from_node.get_id()] - energy_consumption
                    if to_node.get_id() in remaining_energy and remaining_energy_node > remaining_energy[to_node.get_id()]:
                        skip_node[to_node.id] = False
                    remaining_energy[to_node.get_id()] = remaining_energy_node
                complete_tour.append(from_node)
                i += 1
                from_node = tour[i]
                if i < len(tour) - 1:
                    to_node = tour[i + 1]
                continue
            
            find_charging_station = True
            """
            If there is enough energy, find the nearest station.
            If there is not enough energy to reach the nearest station, go back to 
            the previous node and find the next nearest station from there.
            """
            while find_charging_station:
                while i > 0 and min_required_energy[from_node.get_id()] > remaining_energy[from_node.get_id()]:
                    i -= 1
                    from_node = tour[i]
                    complete_tour.pop()
                if i == 0:
                    return tour[1:-1]
                if from_node.get_id() in skip_node:
                    return tour[1:-1]
                skip_node[from_node.get_id()] = True
                to_node = tour[i + 1]
                best_station = self.nearest_station(from_node, to_node, remaining_energy[from_node.get_id()])
                if best_station == -1:
                    return tour[1:-1]
                
                complete_tour.append(from_node)
                from_node = best_station
                to_node = tour[i + 1]
                remaining_energy[from_node.get_id()] = self.problem.get_battery_capacity()
                min_required_energy[from_node.get_id()] = 0
                find_charging_station = False                    
        if not complete_tour[-1].is_depot():
            complete_tour.append(self.problem.get_depot())     
        
        return complete_tour
    
    def greedy_optimize_stations(self, solution: Solution) -> Solution:
        vehicle_tours = solution.get_tours()
        for i, tour in enumerate(vehicle_tours):
            vehicle_tours[i] = self.greedy_optimize_station_for_single_tour(tour)
        solution.set_vehicle_tours(vehicle_tours)
        return solution
    
    def greedy_optimize_station_for_single_tour(self, tour):
        """
        Optimizes the charging station placement in a single tour using a greedy approach.
        
        The goal is to replace inefficient charging stations with better alternatives to reduce the total travel distance.

        **Algorithm Overview:**
        1. **Compute Required Energy:**
        - Calculate the minimum energy required to reach each node in the reverse tour.
        - If any node exceeds battery capacity, return the original tour as it is infeasible.

        2. **Traverse the Tour from the Depot (depot_R):**
        - Start from the depot and track remaining battery capacity.
        - For each node:
            - If it is not a charging station, continue tracking energy consumption.
            - If it is a charging station, attempt to replace it with a better one.

        3. **Replace Charging Stations if a Better One Exists:**
        - Identify the segment that is consuming excessive distance due to a suboptimal charging station.
        - Find an alternative charging station (`S'`) that results in lower travel cost.
        - Replace the original charging station (`S`) if the improvement is significant.

        **Input:**
        - `tour`: A list of nodes representing a vehicle’s route, including customers, charging stations, and depot.

        **Output:**
        - Returns an optimized tour with improved charging station placements.
        """

        # Dictionary to store the required energy to reach each node when traveling in reverse
        required_energy = dict()

        # Get depot ID and initialize required energy for it as zero
        depotID = tour[0].get_id()
        required_energy[depotID] = 0

        # Start constructing an optimal tour with the depot as the first node
        optimal_tour = [self.problem.get_depot()]

        # Compute the required energy for each node in the reverse tour
        for i in range(1, len(tour)):
            if tour[i].is_charging_station() or tour[i].is_depot():
                required_energy[tour[i].get_id()] = 0  # Charging stations reset energy requirement
            else:
                previous_required_energy = required_energy[tour[i - 1].get_id()]
                required_energy[tour[i].get_id()] = previous_required_energy + self.problem.get_energy_consumption(tour[i - 1], tour[i])
                
                # If energy requirement exceeds battery capacity, return the original tour as it is infeasible
                if required_energy[tour[i].get_id()] > self.problem.get_battery_capacity():
                    return tour

        # **Step 2: Travel the Tour from depot_R (Reverse order)**
        tour = list(reversed(tour))
        energy = self.problem.get_battery_capacity()
        i = 1  # Start from the first customer

        while i < len(tour) - 1:
            # If the current node is not a charging station, consume energy and continue
            if not tour[i].is_charging_station():
                energy -= self.problem.get_energy_consumption(optimal_tour[-1], tour[i])
                optimal_tour.append(tour[i])
                i += 1
                continue

            # If it is the depot, reset the battery capacity and continue
            if tour[i].is_depot():
                energy = self.problem.get_battery_capacity()
                optimal_tour.append(tour[i])
                i += 1
                continue

            # **Step 3: Replace Charging Stations if a Better One Exists**
            if i == len(tour) - 1:
                optimal_tour.append(tour[i])
                break

            # Calculate `delta_L1`: the cost of the current charging station segment
            _from_node = optimal_tour[-1]
            num_stations_in_row = 0
            original_distance = 0

            # Count the number of continuous charging stations
            while i + num_stations_in_row < len(tour) - 1 and tour[i + num_stations_in_row].is_charging_station():
                original_distance += _from_node.distance(tour[i + num_stations_in_row])
                _from_node = tour[i + num_stations_in_row]
                num_stations_in_row += 1

            # Find the next customer node after a sequence of charging stations
            next_customer_idx = i + num_stations_in_row
            original_distance += _from_node.distance(tour[next_customer_idx])
            
            # Compute cost reduction `delta_L1`
            delta_L1 = original_distance - tour[i].distance(tour[next_customer_idx])
            _from_node = optimal_tour[-1]
            considered_nodes = []
            tmp_energy = energy

            # Identify alternative stations or direct paths that might reduce cost
            for node in tour[next_customer_idx:]:
                considered_nodes.append(node)
                if node.is_charging_station():
                    break
                tmp_energy -= self.problem.get_energy_consumption(_from_node, node)
                if tmp_energy <= 0:
                    break
                _from_node = node

            from_node = optimal_tour[-1]
            best_station = tour[i]
            best_station_index = 0  # Index to insert the best station after the best found customer

            # Iterate through considered nodes and check if an alternative charging station is better
            for j, node in enumerate(considered_nodes):
                to_node = node
                required_energy_node = required_energy[to_node.get_id()]
                
                # Find the best alternative charging station
                station = self.nearest_station_back(from_node, to_node, energy, required_energy_node)
                
                if station != -1:
                    # Compute cost reduction `delta_L2` if replacing with this station
                    delta_L2 = self.problem.get_distance(from_node, station) + self.problem.get_distance(station, to_node) \
                        - self.problem.get_distance(from_node, to_node)

                    # Replace the current station if `delta_L2` is better than `delta_L1`
                    if delta_L2 < delta_L1:
                        delta_L1 = delta_L2
                        best_station = station
                        best_station_index = j

                # Consume energy and move forward in the tour
                energy -= self.problem.get_energy_consumption(from_node, to_node)
                from_node = to_node

            # Insert the best station found in the optimized tour
            optimal_tour.extend(considered_nodes[:best_station_index])
            optimal_tour.append(best_station)
            i = i + num_stations_in_row + best_station_index
            energy = self.problem.get_battery_capacity() - self.problem.get_energy_consumption(best_station, tour[i])

        # Ensure the final tour ends at the depot
        if not optimal_tour[-1].is_depot():
            optimal_tour.append(self.problem.get_depot())

        # Return the optimized tour with better charging station placement
        return list(reversed(optimal_tour))

    
    def nearest_station(self, from_node, to_node, energy):
        best_station = -1

        for s in self.nearest_dist_charging_matrix[to_node.get_id()]:
            s_node = self.problem.get_node_from_id(s)
            if self.problem.get_energy_consumption(from_node, s_node) <= energy:
                return s_node

        return best_station
    
    def nearest_station_back(self, from_node, to_node, energy, required_energy):
        min_length = float("inf")
        best_station = -1
        for s in self.nearest_dist_charging_matrix[from_node.get_id()] + [self.problem.get_depot_id()]:
            s_node = self.problem.get_node_from_id(s)
            if self.problem.get_energy_consumption(from_node, s_node) <= energy and \
                self.problem.get_energy_consumption(s_node, to_node) + required_energy < \
                    self.problem.get_battery_capacity():
                length1 = s_node.distance(from_node)
                length2 = s_node.distance(to_node)
                if min_length > length1 + length2:
                    min_length = length1 + length2
                    best_station = s_node
                
                if length1 > min_length:
                    break

        return best_station
