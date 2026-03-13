# -*- coding: utf-8 -*-

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """Kullanıcı modeli - hem yönetici hem normal kullanıcı"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # İlişkiler
    cargos = db.relationship('Cargo', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Station(db.Model):
    """İstasyon (İlçe) modeli"""
    __tablename__ = 'stations'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # İlişkiler
    cargos = db.relationship('Cargo', backref='station', lazy=True)


class Vehicle(db.Model):
    """Araç modeli"""
    __tablename__ = 'vehicles'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    capacity = db.Column(db.Float, nullable=False)  # kg
    rental_cost = db.Column(db.Float, default=0)  # 0 ise başlangıç aracı
    is_active = db.Column(db.Boolean, default=True)
    is_rented = db.Column(db.Boolean, default=False)  # Kiralanmış mı?
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Cargo(db.Model):
    """Kargo modeli"""
    __tablename__ = 'cargos'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    station_id = db.Column(db.Integer, db.ForeignKey('stations.id'), nullable=False)
    weight = db.Column(db.Float, nullable=False)  # kg
    status = db.Column(db.String(50), default='pending')  # pending, assigned, delivered, rejected
    delivery_date = db.Column(db.Date, nullable=False)  # Teslimat tarihi
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # İlişkiler
    route_assignments = db.relationship('RouteAssignment', backref='cargo', lazy=True)


class Trip(db.Model):
    """Sefer modeli - Her rota planlaması bir sefer"""
    __tablename__ = 'trips'
    
    id = db.Column(db.Integer, primary_key=True)
    trip_date = db.Column(db.Date, nullable=False)  # Sefer tarihi
    problem_type = db.Column(db.String(50), nullable=False)  # 'unlimited' veya 'limited'
    total_cost = db.Column(db.Float, default=0)
    total_distance = db.Column(db.Float, default=0)  # km
    vehicle_count = db.Column(db.Integer, default=0)
    cargo_count = db.Column(db.Integer, default=0)
    total_weight = db.Column(db.Float, default=0)  # kg
    accepted_cargo_count = db.Column(db.Integer, default=0)  # Belirli araç probleminde
    rejected_cargo_count = db.Column(db.Integer, default=0)  # Belirli araç probleminde
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # İlişkiler
    routes = db.relationship('Route', backref='trip', lazy=True, cascade='all, delete-orphan')


class Route(db.Model):
    """Rota modeli - Her araç için bir rota"""
    __tablename__ = 'routes'
    
    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.Integer, db.ForeignKey('trips.id'), nullable=False)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'), nullable=False)
    route_order = db.Column(db.Text)  # JSON string - istasyon sırası
    total_distance = db.Column(db.Float, default=0)  # km
    total_cost = db.Column(db.Float, default=0)
    total_weight = db.Column(db.Float, default=0)  # kg
    cargo_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # İlişkiler
    vehicle = db.relationship('Vehicle', backref='routes')
    assignments = db.relationship('RouteAssignment', backref='route', lazy=True, cascade='all, delete-orphan')


class RouteAssignment(db.Model):
    """Rota-Kargo eşleştirmesi"""
    __tablename__ = 'route_assignments'
    
    id = db.Column(db.Integer, primary_key=True)
    route_id = db.Column(db.Integer, db.ForeignKey('routes.id'), nullable=False)
    cargo_id = db.Column(db.Integer, db.ForeignKey('cargos.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Parameter(db.Model):
    """Sistem parametreleri - Değiştirilebilir parametreler"""
    __tablename__ = 'parameters'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(500))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

