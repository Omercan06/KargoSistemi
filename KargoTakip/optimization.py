# -*- coding: utf-8 -*-

import random
import math
import copy
from itertools import combinations

class UnlimitedVehicleProblem:

    def __init__(self, cargos_by_station, vehicles, distance_matrix, cost_per_km, rental_cost, rental_capacity):
        self.cargos_by_station = cargos_by_station  # {station: {'weight': x, 'count': y, 'cargo_ids': [...]}}
        self.vehicles = vehicles  # [{capacity, rental_cost}, ...]
        self.distance_matrix = distance_matrix
        self.cost_per_km = cost_per_km
        self.rental_cost = rental_cost
        self.rental_capacity = rental_capacity
    
    def solve(self):

        stations_with_cargo = [s for s, data in self.cargos_by_station.items() if data['weight'] > 0]
        
        if not stations_with_cargo:
            return []
        
        # Toplam ağırlığı hesapla
        total_cargo_weight = sum(self.cargos_by_station[s]['weight'] for s in stations_with_cargo)
        
        # Başlangıç araçlarını hazırla
        available_vehicles = sorted(self.vehicles, key=lambda v: v['capacity'], reverse=True)
        
        # Mevcut kapasite yeterli mi? Değilse sanal kiralık araçlar ekle
        current_capacity = sum(v['capacity'] for v in available_vehicles)
        
        rental_vehicles_needed = 0
        while current_capacity < total_cargo_weight:
            # Yeni kiralık araç ekle
            rental_vehicle = {
                'capacity': self.rental_capacity,
                'rental_cost': self.rental_cost,
                'is_rented': True,
                'name': f'Kiralık Araç {rental_vehicles_needed + 1}'
            }
            available_vehicles.append(rental_vehicle)
            current_capacity += self.rental_capacity
            rental_vehicles_needed += 1
            
        # Cluster-First, Route-Second yaklaşımı
        routes = []
        
        # İstasyonları grupla - Genişletilmiş araç listesini kullan
        # Not: _create_clusters her araç için uygun bir küme oluşturacak
        clusters = self._create_clusters(stations_with_cargo, available_vehicles)
        
        # Kümeleri araçlara ata ve rota oluştur
        for i, cluster in enumerate(clusters):
            if i < len(available_vehicles):
                vehicle = available_vehicles[i]
                route = self._optimize_route_for_cluster(cluster, vehicle)
                routes.append(route)
        
        # Maliyet hesapla ve optimize et
        routes = self._optimize_routes(routes)
        
        return routes
    
    def _create_clusters(self, stations, vehicles):

        clusters = []
        remaining_stations = set(stations)
        
        for vehicle in vehicles:
            if not remaining_stations:
                break
            
            cluster = []
            current_weight = 0
            
            # En uzak istasyondan başla (Clarke-Wright Savings)
            if remaining_stations:
                # Üniversiteye en uzak istasyonu bul
                farthest = max(remaining_stations, 
                             key=lambda s: self.distance_matrix['university'][s])
                cluster.append(farthest)
                current_weight += self.cargos_by_station[farthest]['weight']
                remaining_stations.remove(farthest)
            
            # En yakın komşuları ekle
            while remaining_stations and current_weight < vehicle['capacity']:
                if not cluster:
                    break
                
                # Son eklenen istasyona en yakın istasyonu bul
                last_station = cluster[-1]
                nearest = min(remaining_stations, 
                            key=lambda s: self.distance_matrix[last_station][s])
                
                if current_weight + self.cargos_by_station[nearest]['weight'] <= vehicle['capacity']:
                    cluster.append(nearest)
                    current_weight += self.cargos_by_station[nearest]['weight']
                    remaining_stations.remove(nearest)
                else:
                    break
            
            if cluster:
                clusters.append(cluster)
        
        # Kalan istasyonlar varsa onları da grupla
        if remaining_stations:
            cluster = list(remaining_stations)
            clusters.append(cluster)
        
        return clusters
    
    def _optimize_route_for_cluster(self, cluster, vehicle):

        if len(cluster) <= 1:
            order = cluster
        elif len(cluster) == 2:
            order = cluster
        else:
            # 2-opt algoritması ile optimize et
            order = self._two_opt(cluster)
        
        # Mesafe ve maliyet hesapla
        total_distance = 0
        current = 'university'
        for station in order:
            total_distance += self.distance_matrix[current][station]
            current = station
        total_distance += self.distance_matrix[current]['university']
        
        total_weight = sum(self.cargos_by_station[s]['weight'] for s in order)
        cargo_count = sum(self.cargos_by_station[s]['count'] for s in order)
        cargo_ids = []
        for s in order:
            cargo_ids.extend(self.cargos_by_station[s]['cargo_ids'])
        
        route_cost = total_distance * self.cost_per_km
        if vehicle.get('is_rented', False):
            route_cost += vehicle['rental_cost']
        
        return {
            'vehicle': vehicle,
            'stations': order,
            'total_distance': total_distance,
            'total_cost': route_cost,
            'total_weight': total_weight,
            'cargo_count': cargo_count,
            'cargo_ids': cargo_ids
        }
    
    def _two_opt(self, stations):

        route = stations.copy()
        improved = True
        
        while improved:
            improved = False
            for i in range(1, len(route) - 1):
                for j in range(i + 1, len(route)):
                    # Mevcut mesafe
                    current_dist = (
                        self.distance_matrix[route[i-1]][route[i]] +
                        self.distance_matrix[route[j]][route[(j+1) % len(route)]]
                    )
                    
                    # Ters çevrilmiş mesafe
                    new_dist = (
                        self.distance_matrix[route[i-1]][route[j]] +
                        self.distance_matrix[route[i]][route[(j+1) % len(route)]]
                    )
                    
                    if new_dist < current_dist:
                        route[i:j+1] = reversed(route[i:j+1])
                        improved = True
        
        return route
    
    def _optimize_routes(self, routes):

        # Maliyete göre sırala
        routes.sort(key=lambda r: r['total_cost'])
        return routes


class LimitedVehicleProblem:

    
    def __init__(self, cargos_by_station, vehicles, distance_matrix, cost_per_km):
        self.cargos_by_station = cargos_by_station
        self.vehicles = vehicles
        self.distance_matrix = distance_matrix
        self.cost_per_km = cost_per_km
        self.population_size = 50
        self.generations = 100
        self.mutation_rate = 0.2
        self.elite_size = 5
    
    def solve(self, optimization_target='weight'):

        stations_with_cargo = [s for s, data in self.cargos_by_station.items() if data['weight'] > 0]
        
        if not stations_with_cargo:
            return []
        
        # Başlangıç popülasyonunu oluştur
        population = self._create_initial_population(stations_with_cargo)
        
        best_solution = None
        best_fitness = float('-inf')
        
        for generation in range(self.generations):
            # Fitness hesapla
            fitness_scores = [(sol, self._calculate_fitness(sol, optimization_target)) 
                            for sol in population]
            fitness_scores.sort(key=lambda x: x[1], reverse=True)
            
            # En iyi çözümü güncelle
            if fitness_scores[0][1] > best_fitness:
                best_fitness = fitness_scores[0][1]
                best_solution = fitness_scores[0][0]
            
            # Yeni nesil oluştur
            new_population = []
            
            # Elit bireyleri koru
            for i in range(self.elite_size):
                new_population.append(fitness_scores[i][0])
            
            # Crossover ve mutasyon
            while len(new_population) < self.population_size:
                parent1 = self._tournament_selection(fitness_scores)
                parent2 = self._tournament_selection(fitness_scores)
                child = self._crossover(parent1, parent2)
                
                if random.random() < self.mutation_rate:
                    child = self._mutate(child, stations_with_cargo)
                
                new_population.append(child)
            
            population = new_population
        
        # En iyi çözümü rotaya çevir
        routes = self._solution_to_routes(best_solution)
        return routes
    
    def _create_initial_population(self, stations):

        population = []
        
        for _ in range(self.population_size):
            # Her araç için rastgele istasyon ataması
            solution = [[] for _ in range(len(self.vehicles))]
            
            available_stations = stations.copy()
            random.shuffle(available_stations)
            
            for station in available_stations:
                # Kapasitesi uygun bir araca ata
                weight = self.cargos_by_station[station]['weight']
                
                # Rastgele araç seç ve kapasite kontrolü yap
                possible_vehicles = []
                for i, vehicle in enumerate(self.vehicles):
                    current_weight = sum(self.cargos_by_station[s]['weight'] for s in solution[i])
                    if current_weight + weight <= vehicle['capacity']:
                        possible_vehicles.append(i)
                
                if possible_vehicles:
                    vehicle_idx = random.choice(possible_vehicles)
                    solution[vehicle_idx].append(station)
            
            population.append(solution)
        
        return population
    
    def _calculate_fitness(self, solution, optimization_target):

        total_cost = 0
        total_weight = 0
        total_count = 0
        
        for vehicle_idx, stations in enumerate(solution):
            if not stations:
                continue
            
            # Rota mesafesini hesapla
            distance = self._calculate_route_distance(stations)
            cost = distance * self.cost_per_km
            total_cost += cost
            
            # Kargo bilgileri
            for station in stations:
                total_weight += self.cargos_by_station[station]['weight']
                total_count += self.cargos_by_station[station]['count']
        
        # Fitness: yüksek kargo, düşük maliyet
        if optimization_target == 'weight':
            cargo_score = total_weight
        else:  # 'count'
            cargo_score = total_count
        
        # Normalizasyon
        cost_penalty = total_cost / 100
        fitness = cargo_score - cost_penalty
        
        return fitness
    
    def _calculate_route_distance(self, stations):

        if not stations:
            return 0
        
        # 2-opt ile optimize et
        optimized = self._two_opt_limited(stations)
        
        total_distance = self.distance_matrix['university'][optimized[0]]
        for i in range(len(optimized) - 1):
            total_distance += self.distance_matrix[optimized[i]][optimized[i+1]]
        total_distance += self.distance_matrix[optimized[-1]]['university']
        
        return total_distance
    
    def _two_opt_limited(self, stations):

        if len(stations) <= 2:
            return stations
        
        route = stations.copy()
        improved = True
        iterations = 0
        max_iterations = 50
        
        while improved and iterations < max_iterations:
            improved = False
            iterations += 1
            
            for i in range(len(route) - 1):
                for j in range(i + 2, len(route)):
                    # Swap kontrolü
                    current_dist = (
                        self.distance_matrix[route[i]][route[i+1]] +
                        self.distance_matrix[route[j-1]][route[j]]
                    )
                    new_dist = (
                        self.distance_matrix[route[i]][route[j]] +
                        self.distance_matrix[route[i+1]][route[j-1]]
                    )
                    
                    if new_dist < current_dist:
                        route[i+1:j] = reversed(route[i+1:j])
                        improved = True
        
        return route
    
    def _tournament_selection(self, fitness_scores, tournament_size=3):

        tournament = random.sample(fitness_scores, min(tournament_size, len(fitness_scores)))
        tournament.sort(key=lambda x: x[1], reverse=True)
        return tournament[0][0]
    
    def _crossover(self, parent1, parent2):

        child = [[] for _ in range(len(self.vehicles))]
        
        # Her istasyon için hangi ebeveynden alınacağına karar ver
        all_stations = set()
        for vehicle_stations in parent1:
            all_stations.update(vehicle_stations)
        
        for station in all_stations:
            # Hangi ebeveynde hangi araçta?
            parent1_vehicle = None
            parent2_vehicle = None
            
            for i, stations in enumerate(parent1):
                if station in stations:
                    parent1_vehicle = i
                    break
            
            for i, stations in enumerate(parent2):
                if station in stations:
                    parent2_vehicle = i
                    break
            
            # Rastgele bir ebeveynden araç seç
            if random.random() < 0.5 and parent1_vehicle is not None:
                target_vehicle = parent1_vehicle
            elif parent2_vehicle is not None:
                target_vehicle = parent2_vehicle
            else:
                target_vehicle = parent1_vehicle if parent1_vehicle is not None else 0
            
            # Kapasite kontrolü
            weight = self.cargos_by_station[station]['weight']
            current_weight = sum(self.cargos_by_station[s]['weight'] for s in child[target_vehicle])
            
            if current_weight + weight <= self.vehicles[target_vehicle]['capacity']:
                child[target_vehicle].append(station)
            else:
                # Başka bir araca ata
                for i, vehicle in enumerate(self.vehicles):
                    current_weight = sum(self.cargos_by_station[s]['weight'] for s in child[i])
                    if current_weight + weight <= vehicle['capacity']:
                        child[i].append(station)
                        break
        
        return child
    
    def _mutate(self, solution, all_stations):

        solution = copy.deepcopy(solution)
        
        mutation_type = random.choice(['swap', 'add', 'remove'])
        
        if mutation_type == 'swap':
            # İki araç arasında istasyon değiştir
            non_empty = [i for i, s in enumerate(solution) if s]
            if len(non_empty) >= 2:
                v1, v2 = random.sample(non_empty, 2)
                if solution[v1] and solution[v2]:
                    station1 = random.choice(solution[v1])
                    station2 = random.choice(solution[v2])
                    
                    # Kapasite kontrolü
                    weight1 = self.cargos_by_station[station1]['weight']
                    weight2 = self.cargos_by_station[station2]['weight']
                    
                    current_weight_v1 = sum(self.cargos_by_station[s]['weight'] for s in solution[v1])
                    current_weight_v2 = sum(self.cargos_by_station[s]['weight'] for s in solution[v2])
                    
                    if (current_weight_v1 - weight1 + weight2 <= self.vehicles[v1]['capacity'] and
                        current_weight_v2 - weight2 + weight1 <= self.vehicles[v2]['capacity']):
                        solution[v1].remove(station1)
                        solution[v2].remove(station2)
                        solution[v1].append(station2)
                        solution[v2].append(station1)
        
        elif mutation_type == 'add':
            # Yeni istasyon ekle
            current_stations = set()
            for stations in solution:
                current_stations.update(stations)
            
            available = set(all_stations) - current_stations
            if available:
                new_station = random.choice(list(available))
                weight = self.cargos_by_station[new_station]['weight']
                
                possible_vehicles = []
                for i, vehicle in enumerate(self.vehicles):
                    current_weight = sum(self.cargos_by_station[s]['weight'] for s in solution[i])
                    if current_weight + weight <= vehicle['capacity']:
                        possible_vehicles.append(i)
                
                if possible_vehicles:
                    vehicle_idx = random.choice(possible_vehicles)
                    solution[vehicle_idx].append(new_station)
        
        elif mutation_type == 'remove':
            # Rastgele istasyon çıkar
            non_empty = [i for i, s in enumerate(solution) if s]
            if non_empty:
                vehicle_idx = random.choice(non_empty)
                if solution[vehicle_idx]:
                    station = random.choice(solution[vehicle_idx])
                    solution[vehicle_idx].remove(station)
        
        return solution
    
    def _solution_to_routes(self, solution):

        routes = []
        
        for vehicle_idx, stations in enumerate(solution):
            if not stations:
                continue
            
            vehicle = self.vehicles[vehicle_idx]
            optimized_order = self._two_opt_limited(stations)
            
            total_distance = self._calculate_route_distance(optimized_order)
            total_cost = total_distance * self.cost_per_km
            total_weight = sum(self.cargos_by_station[s]['weight'] for s in optimized_order)
            cargo_count = sum(self.cargos_by_station[s]['count'] for s in optimized_order)
            cargo_ids = []
            for s in optimized_order:
                cargo_ids.extend(self.cargos_by_station[s]['cargo_ids'])
            
            routes.append({
                'vehicle': vehicle,
                'stations': optimized_order,
                'total_distance': total_distance,
                'total_cost': total_cost,
                'total_weight': total_weight,
                'cargo_count': cargo_count,
                'cargo_ids': cargo_ids
            })
        
        return routes

