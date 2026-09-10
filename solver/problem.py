from collections import OrderedDict
from copy import deepcopy
import os
from random import shuffle
import numpy as np
from matplotlib import pyplot as plt

from node import Node
from solution import Solution

from logger import get_problem_name, logger

class Problem():
    
    def __init__(self, problem_path=None):
        self.problem_path = problem_path
        self.problem_name = get_problem_name(problem_path)
        if not os.path.isfile(problem_path):
            raise ValueError(f"Problem file not found: {problem_path}. Please input a valid problem name.")

        self.max_num_vehicles = None
        self.energy_capacity = None
        self.capacity = None
        self.num_stations = None
        self.num_dimensions = None
        self.optimal_value = None
        self.energy_consumption = None
        self.nodes = []
        self.node_dict = dict()
        self.customers = []
        self.customer_ids = []
        self.stations = []
        self.station_ids = []
        self.demands = []
        self.depot = None
        self.depot_id = None

        self.problem = self.__read_problem(problem_path)
        
    def get_name(self):
        return self.problem_name
            
    def get_problem_size(self):
        return len(self.nodes)
    
    def get_depot(self):
        return self.depot
    
    def get_num_customers(self):
        return self.num_customers
    
    def get_num_stations(self):
        return self.num_stations
    
    def get_num_dimensions(self):
        return self.num_dimensions
    
    def get_max_num_vehicles(self):
        return self.max_num_vehicles
    
    def get_customer_demand(self, node):
        return node.get_demand()
    
    def get_energy_consumption(self, from_node, to_node):
        return self.energy_consumption * from_node.distance(to_node)
    
    def get_depot_id(self):
        return self.depot_id
    
    def get_customer_ids(self):
        return deepcopy(self.customer_ids)
    
    def get_station_ids(self):
        return deepcopy(self.station_ids)
    
    def get_all_stations(self):
        return deepcopy(self.stations)
    
    def get_battery_capacity(self):
        return self.energy_capacity
    
    def get_capacity(self):
        return self.capacity
    
    def get_all_customers(self):
        return self.customers
    
    def get_node_from_id(self, id):
        return self.node_dict[id]
    
    def get_distance(self, from_node, to_node):
        return from_node.distance(to_node)
        
    def __read_problem(self, problem_file_path):
        with open(problem_file_path, 'r') as f:
            lines = f.readlines()
            
            """ Read metadata """
            logger.info(f"Read problem file: {problem_file_path}")
            logger.info("{}".format(lines[0]))
            logger.info("{}".format(lines[1]))
            logger.info("{}".format(lines[2]))
            logger.info("{}".format(lines[3]))
            self.max_num_vehicles = int(lines[4].split()[-1])
            self.num_dimensions = int(lines[5].split()[-1])
            self.num_stations = int(lines[6].split()[-1])
            self.num_customers = self.num_dimensions - self.num_stations
            self.capacity = float(lines[7].split()[-1])
            self.energy_capacity = float(lines[8].split()[-1])
            self.energy_consumption = float(lines[9].split()[-1])
            logger.info("{}".format(lines[10]))
            edge_weight_type = lines[10].split()[-1]
            
            """ Read NODES """
            if edge_weight_type == 'EUC_2D':
                start_line = 12
                end_line = 12 + self.num_dimensions
                for i in range(start_line, end_line):
                    id, x, y = lines[i].split()
                    id = int(id) - 1
                    self.nodes.append(Node(int(id), float(x), float(y)))
                    self.node_dict[id] = self.nodes[-1]
                    
                start_line = end_line + 1
                end_line = start_line + self.num_customers
                for i in range(start_line, end_line):
                    _id, demand = lines[i].split()[-2:]
                    _id = int(_id) - 1
                    demand = float(demand)
                    self.demands.append(demand)
                    self.nodes[_id].set_type('C')
                    self.nodes[_id].set_demand(demand)
                    self.customer_ids.append(_id)
                    self.customers.append(self.nodes[_id])
                    
                start_line = end_line + 1
                end_line = start_line + self.num_stations
                for i in range(start_line, end_line):
                    _id = lines[i].split()[-1]
                    _id = int(_id) - 1
                    self.nodes[_id].set_type('S')
                    self.station_ids.append(_id)
                    self.stations.append(self.nodes[_id])
                    
                self.depot_id = int(lines[end_line + 1].split()[-1]) - 1
                self.nodes[self.depot_id].set_type('D')
                self.depot = self.nodes[self.depot_id]
                # remove depot from customers
                self.customer_ids.remove(self.depot_id)
                for i in range(len(self.customers)):
                    if self.customers[i].is_depot():
                        self.customers.pop(i)
                        break

                self.num_customers -= 1 # skip depot from customers
            else:
                raise ValueError(f"Invalid benchmark, edge weight type: {edge_weight_type} not supported.")
    
    def check_valid_solution(self, solution, verbose=False):
        """
        Validates whether the given solution meets all constraints of the Electric Vehicle Routing Problem (EVRP).

        **Checks Performed:**
        1. **Unique Customer Visits:** Ensures that each customer is visited only once.
        2. **Vehicle Limit:** Ensures the solution does not exceed the maximum number of available vehicles.
        3. **Capacity Constraint:** Ensures that no vehicle exceeds its maximum load capacity.
        4. **Energy Constraint:** Ensures that no vehicle runs out of energy before reaching a charging station or depot.

        **Parameters:**
        - `solution` (Solution): The proposed vehicle routing solution.
        - `verbose` (bool, optional): If `True`, logs warnings when constraints are violated.

        **Returns:**
        - `True` if the solution is valid.
        - `False` if any constraint is violated.
        """

        # Step 1: Ensure each customer is visited only once
        is_valid = solution.set_tour_index()
        if not is_valid:
            if verbose:
                logger.warning("The vehicle has visited a customer more than once.")
            return False

        # Step 2: Retrieve all tours in the solution
        tours = solution.get_tours()

        # Step 3: Check if the solution exceeds the available number of vehicles
        if len(tours) > self.max_num_vehicles:
            if verbose:
                logger.warning("This solution is using more vehicles than allowed.")
            return False

        # Step 4: Track visited customers to ensure no duplicate visits
        visited = {}

        # Step 5: Iterate over each tour to check constraints
        for tour in tours:
            # Initialize vehicle's energy and capacity
            energy_temp = self.get_battery_capacity()
            capacity_temp = self.get_capacity()

            # Iterate through each consecutive node in the tour
            for i in range(len(tour) - 1):
                first_node = tour[i]
                second_node = tour[i + 1]

                # Step 6: Ensure each customer is visited only once
                if first_node.is_customer():
                    if first_node.get_id() in visited:
                        if verbose:
                            logger.warning("The vehicle has visited a customer more than once.")
                        return False
                    visited[first_node.get_id()] = 1

                # Step 7: Reduce the remaining vehicle capacity by the demand of the next customer
                capacity_temp -= self.get_customer_demand(second_node)

                # Step 8: Reduce the remaining energy based on the distance between nodes
                energy_temp -= self.get_energy_consumption(first_node, second_node)

                # Step 9: Ensure the vehicle does not exceed its capacity
                if capacity_temp < 0.0:
                    if verbose:
                        logger.warning("The vehicle exceeds capacity when visiting {}.".format(second_node.get_id()))
                    return False

                # Step 10: Ensure the vehicle does not run out of energy
                if energy_temp < 0.0:
                    if verbose:
                        logger.warning("The vehicle exceeds energy when visiting {}.".format(second_node.get_id()))
                    return False

                # Step 11: If the vehicle reaches a depot, reset its capacity and energy
                if second_node.is_depot():
                    capacity_temp = self.get_capacity()
                    energy_temp = self.get_battery_capacity()

                # Step 12: If the vehicle reaches a charging station, reset its energy
                if second_node.is_charging_station():
                    energy_temp = self.get_battery_capacity()

        # Step 13: If all checks pass, the solution is valid
        return True

    
    def get_tour_length(self, tour):
        tour_length = 0
        for i in range(len(tour) - 1):
            tour_length += tour[i].distance(tour[i + 1])
        return tour_length
    
    def calculate_tour_length(self, solution: Solution):
        tour_length = 0
        for tour in solution.get_tours():
            tour = [self.get_depot()] + tour + [self.get_depot()]
            for i in range(len(tour) - 1):
                tour_length += tour[i].distance(tour[i + 1])
        
        if self.check_valid_solution(solution):
            return tour_length
        else:
            return tour_length * 2
    
    def plot(self, solution=None, path=None):

        _, ax = plt.subplots()

        for node in self.nodes:
            if node.is_customer():
                ax.scatter(node.x, node.y, c='green', marker='o',
                        s=30, alpha=0.5, label="Customer Node")
            elif node.is_depot():
                ax.scatter(node.x, node.y, c='red', marker='s',
                        s=30, alpha=0.5, label="Depot Node")
            elif node.is_charging_station():
                ax.scatter(node.x, node.y, c='blue', marker='^',
                        s=30, alpha=0.5, label="Charging Station Node")
            else:
                raise ValueError("Invalid node type")

        # Set title and labels
        ax.set_title(f"Problem {self.problem_name}")

        handles, labels = plt.gca().get_legend_handles_labels()
        by_label = OrderedDict(zip(labels, handles))
        plt.legend(by_label.values(), by_label.keys(),
                loc='upper right',
                prop={'size': 6})

        if solution is not None:
            tours = solution.get_tours()
            for tour in tours:
                if len(tour) == 0:
                    continue
                plt.plot([self.get_depot().x, tour[0].x],
                        [self.get_depot().y, tour[0].y],
                        c='black', linewidth=0.5, linestyle='--')
                
                for i in range(len(tour) - 1):
                    first_node = tour[i]
                    second_node = tour[i + 1]
                    plt.plot([first_node.x, second_node.x],
                            [first_node.y, second_node.y],
                            c='black', linewidth=0.5, linestyle='--')
                    
                plt.plot([tour[-1].x, self.get_depot().x],
                        [tour[-1].y, self.get_depot().y],
                        c='black', linewidth=0.5, linestyle='--')
        if path is None:
            plt.show()
        else:
            plt.savefig(path)
            plt.close()

        
    
    