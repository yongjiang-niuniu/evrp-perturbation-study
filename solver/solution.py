from copy import deepcopy
from hashlib import md5
import numpy as np
from logger import logger

class Solution():
    """
        Represents a solution for the Electric Vehicle Routing Problem (EVRP), 
        managing multiple vehicle tours and providing utilities for solution evaluation and modification.

        **Attributes:**
        - `tours` (list of lists): Stores a list of vehicle tours, where each tour is a list of nodes.
        - `tour_index` (dict): Maps each customer node ID to its corresponding tour index.
        - `tour_length` (float): Represents the total length (cost) of the solution.

        **Methods:**
        - `add_tour(tour)`: Adds a new tour to the solution.
        - `get_num_tours() -> int`: Returns the number of tours in the solution.
        - `set_tour_index() -> int`: Updates `tour_index` to track which tour each customer belongs to.
        - `get_tour_index_by_node(node_id) -> int`: Returns the tour index for a given customer node.
        - `get_presentation() -> str`: Returns an MD5 hash representation of the solution for easy comparison.
        - `get_tours() -> list`: Returns a deep copy of all tours.
        - `get_basic_tours() -> list`: Returns tours containing only customer nodes (excluding depots and charging stations).
        - `get_tour_length() -> float`: Returns the total length of the solution.
        - `set_tour_length(tour_length)`: Sets the total length of the solution.
        - `to_array() -> np.array`: Converts the solution into a NumPy array containing node IDs.
        - `get_vehicle_tours(skip_depot=False, full=True) -> list`: Returns tours formatted based on whether depots should be included.
        - `set_vehicle_tours(tours)`: Updates the solution with new tours and recalculates tour indices.
        - **Comparison Methods (`>=`, `>`, `<=`, `<`)**: Allow solutions to be compared based on tour length.
        - `__repr__() -> str`: Returns a string representation of the solution, displaying tour details.

        **Usage:**
        - This class is used to store and manipulate potential solutions in an EVRP optimization algorithm.
        - It ensures the integrity of the solution by tracking tour indices and constraints.
        - Supports evaluation, modification, and comparison of different solutions.
    """

    def __init__(self, tours=None):
        self.tour_index = {}
        self.tour_length = np.inf
        if tours:
            self.tours = tours
            self.set_tour_index()
        else:
            self.tours = []
        
    def add_tour(self, tour):
        self.tours.append(tour)
        
    def get_num_tours(self):
        return len(self.tours)

    def set_tour_index(self):
        self.tour_index = {}
        for idx, tour in enumerate(self.tours):
            for node in tour:
                if node.is_customer():
                    if node.id not in self.tour_index:
                        self.tour_index[node.id] = idx
                    else:
                        logger.warning('Node {} already in tour {}'.format(node.id, idx))
                        return 0
        return 1
    
    def get_tour_index_by_node(self, node_id):
        return self.tour_index[node_id]
    
    def get_presentation(self):
        list_node = [[x.get_id() for x in tour] for tour in self.tours]
        return md5(str(list_node).encode()).hexdigest()

    def get_tours(self):
        return deepcopy(self.tours)
    
    def get_basic_tours(self):
        tours = []
        for tour in self.tours:
            _tour = [node for node in tour if node.is_customer()]
            tours.append(_tour)
        return tours

    def get_tour_length(self):
        return self.tour_length
    
    def set_tour_length(self, tour_length):
        self.tour_length = tour_length
    
    def to_array(self):
        return np.array([node.id for node in self.tours])
    
    def get_vehicle_tours(self, skip_depot=False, full=True):
        
        if full:
            tours = self.complete_tours
        else:
            tours = self.tours
        """ Vehicle did not start or end depot """
        if len(tours) == 0:
            tours = deepcopy(self.tours)
        if not tours[0].is_depot() or not tours[-1].is_depot():
            return None
        
        vehicle_tours = []
        
        if not skip_depot:
            tour = [tours[0]]
        else:
            tour = []
        
        for idx, node in enumerate(tours):
            if idx == 0 and not skip_depot:
                continue
            if node.is_depot():
                if skip_depot:
                    vehicle_tours.append(tour)
                    continue
                else:
                    tour.append(tours[0])
                    vehicle_tours.append(tour)
                    tour = [tours[0]]
            else:
                tour.append(node)
        return vehicle_tours
    
    def set_vehicle_tours(self, tours):
        self.tours = tours
        self.set_tour_index()
            
    def __ge__(self, other):
        return self.tour_length >= other.tour_length
    
    def __gt__(self, other):
        return self.tour_length > other.tour_length
    
    def __le__(self, other):
        return self.tour_length <= other.tour_length
    
    def __lt__(self, other):
        return self.tour_length < other.tour_length
    
    def __repr__(self) -> str:
        if self.tour_length:
            presentation = "Tour length: {}\n".format(self.tour_length)
        else:
            presentation = ""
        for i, tour in enumerate(self.tours):
            presentation += 'Tour {}: '.format(i) + ' -> '.join([str(node.id) for node in tour]) + '\n'
            
        return presentation