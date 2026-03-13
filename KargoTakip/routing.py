# -*- coding: utf-8 -*-

import math
import networkx as nx
from geopy.distance import geodesic

class RoadNetwork:

    
    def __init__(self, stations, university):
        self.stations = stations
        self.university = university
        self.graph = nx.Graph()
        self._build_road_network()
    
    def _build_road_network(self):

        # Tüm lokasyonları ekle
        locations = {}
        locations['university'] = self.university
        for station_name, coords in self.stations.items():
            locations[station_name] = coords
        
        # Düğümleri ekle
        for name, coords in locations.items():
            self.graph.add_node(name, lat=coords['lat'], lon=coords['lon'])
            

        
        def get_geo(name1, name2):
            key = tuple(sorted((name1, name2)))
            u, v = key # u is alphabetically first
            
            # Helper to access node coords
            u_coords = (locations[u]['lat'], locations[u]['lon'])
            v_coords = (locations[v]['lat'], locations[v]['lon'])


            raw_geometries = {
                # ---------------------------------------------------------
                # KUZEY HATTI (D100)
                # ---------------------------------------------------------
                
                # Çayırova (u) - Darıca (v) | C < D | Direction: West -> East
                ('Çayırova', 'Darıca'): [
                    (40.8065, 29.3735), (40.7950, 29.3850), (40.7830, 29.3950)
                ],
                
                # Darıca (u) - Gebze (v) | D < G | Direction: West -> East
                ('Darıca', 'Gebze'): [
                    (40.7750, 29.4050), (40.7850, 29.4200), (40.7950, 29.4300)
                ],


                ('Dilovası', 'Gebze'): [
                    (40.7860, 29.5300), (40.7900, 29.5100), (40.7950, 29.4800), (40.8000, 29.4500)
                ],

                # Dilovası (u) - Körfez (v) | D < K | Direction: West -> East (Dilovası -> Körfez)
                ('Dilovası', 'Körfez'): [
                    (40.7800, 29.5700), (40.7750, 29.6000), (40.7720, 29.6500), 
                    (40.7700, 29.7000), (40.7650, 29.7400), (40.7600, 29.7700)
                ],


                ('Derince', 'Körfez'): [
                     (40.7560, 29.8100), (40.7580, 29.7900)
                ],

                # Derince (u) - İzmit (v) | D < I | Direction: West -> East (Derince -> İzmit)
                ('Derince', 'İzmit'): [
                    (40.7530, 29.8600), (40.7550, 29.8900), 
                    (40.7580, 29.9100), (40.7600, 29.9250)
                ],


                ('Gölcük', 'Karamürsel'): [
                     (40.7200, 29.8200), (40.7180, 29.7900), 
                     (40.7160, 29.7500), (40.7120, 29.7100), 
                     (40.7050, 29.6600), (40.6950, 29.6200)
                ],


                ('Başiskele', 'Gölcük'): [
                    (40.7150, 29.9300), (40.7180, 29.9000), (40.7200, 29.8600)
                ],

                # Başiskele (u) - İzmit (v) | B < I | Direction: South -> North (Başiskele -> İzmit)
                ('Başiskele', 'İzmit'): [
                    (40.7250, 29.9500), (40.7350, 29.9700), # Kullar
                    (40.7500, 29.9800), # Sanayi
                    (40.7580, 29.9500)  # D100 bağlantı
                ],



                # İzmit (u) - Kartepe (v) | I < K | Direction: West -> East
                ('İzmit', 'Kartepe'): [
                    (40.7620, 29.9600), (40.7600, 30.0000), (40.7550, 30.0300)
                ],

                # Kartepe (u) - University (v) | K < U (assuming 'u' from 'university')?
                # 'university' string starts with 'u'. 'Kartepe' with 'K'.
                # K < U ? Yes.
                # Direction: Kartepe -> Univ. (East -> West/North).
                ('Kartepe', 'university'): [
                   (40.7600, 30.0000), (40.7700, 29.9800), (40.8000, 29.9600)
                ],

                # İzmit (u) - Kandıra (v) | I < K | Direction: South -> North
                ('İzmit', 'Kandıra'): [
                    (40.7700, 29.9600), (40.8000, 29.9800), 
                    (40.8500, 30.0200), (40.9500, 30.0800), 
                    (41.0200, 30.1200), (41.0500, 30.1400)
                ],
                

                ('İzmit', 'university'): [
                    (40.7700, 29.9400), (40.7850, 29.9450), 
                    (40.7950, 29.9500), (40.8100, 29.9400)
                ]
            }
            
            # Auto-repair keys if sorted order is different (e.g. locale issues)
            # This ensures we find the entry even if my manual sort guess was wrong
            points = raw_geometries.get(key)
            if not points:
                # Try reversed key
                rev_key = (key[1], key[0])
                points = raw_geometries.get(rev_key)
                if points:
                    # If we found it via reverse key, it means the dictionary definition
                    # was opposite to 'sorted' result.
                    # We defined it as U->V. If key is V->U, we must reverse points.
                    points = list(reversed(points))

            if not points:
                return []
                
            # Full path: [StartNode] + [Waypoints] + [EndNode]
            return [u_coords] + points + [v_coords]

        
        # Kesin Topoloji (Strict Topology)
        # Sadece komşu ilçeleri bağla. Asla atlama yapma.
        valid_connections = [
            # Kuzey Şeridi (Sıralı)
            ('Çayırova', 'Darıca'),
            ('Darıca', 'Gebze'),
            ('Gebze', 'Dilovası'),
            ('Dilovası', 'Körfez'),
            ('Körfez', 'Derince'),
            ('Derince', 'İzmit'),
            
            # Güney Şeridi (Sıralı)
            ('Karamürsel', 'Gölcük'),
            ('Gölcük', 'Başiskele'),
            ('Başiskele', 'İzmit'), # Köprü yok, İzmit üzerinden geçiş zorunlu
            
            # Merkez Dağılım
            ('İzmit', 'Kartepe'),
            ('İzmit', 'Kandıra'),
            ('İzmit', 'university'),
            ('Kartepe', 'university') # Alternatif
        ]
        
        for name1, name2 in valid_connections:
            # Sadece mevcut istasyonları bağla (Senaryolarda eksik olabilir)
            if name1 in locations and name2 in locations:
                distance = self._calculate_road_distance(locations[name1], locations[name2])
                geometry = get_geo(name1, name2)
                self.graph.add_edge(name1, name2, weight=distance, geometry=geometry)
            

                
    def _calculate_road_distance(self, loc1, loc2, is_main_road=True):

        crow_distance = geodesic(
            (loc1['lat'], loc1['lon']),
            (loc2['lat'], loc2['lon'])
        ).km
        
        if is_main_road:
            # Ana yollarda yol faktörü 1.2-1.4 arası (daha düz yollar)
            road_factor = 1.2 + (crow_distance / 100)
        else:
            # Tali yollarda yol faktörü 1.4-1.8 arası (daha dolambaçlı)
            road_factor = 1.5 + (crow_distance / 50)
        
        return crow_distance * road_factor
    
    def get_shortest_path(self, start, end):

        try:
            path = nx.shortest_path(self.graph, start, end, weight='weight')
            distance = nx.shortest_path_length(self.graph, start, end, weight='weight')
            return path, distance
        except nx.NetworkXNoPath:
            # Yol bulunamazsa direkt mesafe (en kötü senaryo)
            loc1 = self.graph.nodes[start]
            loc2 = self.graph.nodes[end]
            distance = geodesic((loc1['lat'], loc1['lon']), (loc2['lat'], loc2['lon'])).km * 2
            return [start, end], distance
    
    def get_route_coordinates(self, path):

        coordinates = []
        if not path:
            return coordinates
            
        for i in range(len(path) - 1):
            u = path[i]
            v = path[i+1]
            
            # Başlangıç noktası
            u_data = self.graph.nodes[u]
            coordinates.append((u_data['lat'], u_data['lon']))
            
            # Ara noktalar (Geometri)
            # Edge verisini her iki yönde de kontrol et
            edge_data = self.graph.get_edge_data(u, v)
            
            if edge_data and 'geometry' in edge_data:
                points = edge_data['geometry']

                
                is_alphabetical_direction = (u < v)
                
                if is_alphabetical_direction:
                    # Yönümüz, geometry storage yönüyle aynı.
                    coordinates.extend(points)
                else:
                    # Yönümüz ters, geometry'yi tersten almalıyız.
                    coordinates.extend(reversed(points))
                    
        # Son nokta
        last_node = self.graph.nodes[path[-1]]
        coordinates.append((last_node['lat'], last_node['lon']))
            
        return coordinates
    
    def calculate_total_route_distance(self, station_order):

        total_distance = 0
        current = 'university'
        
        for station in station_order:
            _, distance = self.get_shortest_path(current, station)
            total_distance += distance
            current = station
        
        # Üniversiteye dönüş
        _, distance = self.get_shortest_path(current, 'university')
        total_distance += distance
        
        return total_distance


def calculate_distance_matrix(stations, university):

    road_network = RoadNetwork(stations, university)
    locations = ['university'] + list(stations.keys())
    
    distance_matrix = {}
    for loc1 in locations:
        distance_matrix[loc1] = {}
        for loc2 in locations:
            if loc1 == loc2:
                distance_matrix[loc1][loc2] = 0
            else:
                _, distance = road_network.get_shortest_path(loc1, loc2)
                distance_matrix[loc1][loc2] = distance
    
    return distance_matrix, road_network

