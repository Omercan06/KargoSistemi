# -*- coding: utf-8 -*-

import os

class Config:
    # Flask ayarları
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'kargo-takip-secret-key-2024'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///kargo_takip.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Araç parametreleri (Değiştirilebilir)
    INITIAL_VEHICLES = [
        {'name': 'Araç 1', 'capacity': 500, 'rental_cost': 0},
        {'name': 'Araç 2', 'capacity': 750, 'rental_cost': 0},
        {'name': 'Araç 3', 'capacity': 1000, 'rental_cost': 0}
    ]
    
    # Kiralama parametreleri (Değiştirilebilir)
    RENTAL_VEHICLE_CAPACITY = 500  # kg
    RENTAL_VEHICLE_COST = 200  # birim
    
    # Maliyet parametreleri (Değiştirilebilir)
    COST_PER_KM = 1  # birim/km
    
    # Kocaeli İlçeleri - Latitude ve Longitude bilgileri
    KOCAELI_DISTRICTS = {
        'Başiskele': {'lat': 40.7617, 'lon': 29.9184},
        'Çayırova': {'lat': 40.8203, 'lon': 29.3714},
        'Darıca': {'lat': 40.7697, 'lon': 29.3889},
        'Derince': {'lat': 40.7667, 'lon': 29.8333},
        'Dilovası': {'lat': 40.7833, 'lon': 29.5333},
        'Gebze': {'lat': 40.8027, 'lon': 29.4308},
        'Gölcük': {'lat': 40.7164, 'lon': 29.8178},
        'Kandıra': {'lat': 41.0683, 'lon': 30.1544},
        'Karamürsel': {'lat': 40.6906, 'lon': 29.6186},
        'Kartepe': {'lat': 40.7550, 'lon': 30.0344},
        'Körfez': {'lat': 40.7689, 'lon': 29.7500},
        'İzmit': {'lat': 40.7654, 'lon': 29.9400}
    }
    
    # Kocaeli Üniversitesi (Umuttepe Kampüsü)
    UNIVERSITY_LOCATION = {'name': 'Kocaeli Üniversitesi', 'lat': 40.8246, 'lon': 29.9200}

