# -*- coding: utf-8 -*-

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Station, Vehicle, Cargo, Trip, Route, RouteAssignment, Parameter
from config import Config
from routing import calculate_distance_matrix, RoadNetwork
from optimization import UnlimitedVehicleProblem, LimitedVehicleProblem
from datetime import datetime, timedelta
import json
import folium
from folium import plugins
from scenarios import SCENARIOS

app = Flask(__name__)
app.config.from_object(Config)

# Database
db.init_app(app)

# Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# İlk çalıştırmada veritabanını ve başlangıç verilerini oluştur
def init_database():
    """Veritabanını başlat ve başlangıç verilerini ekle"""
    with app.app_context():
        db.create_all()
        
        # Admin kullanıcısı
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', is_admin=True)
            admin.set_password('admin123')
            db.session.add(admin)
        
        # Test kullanıcısı
        if not User.query.filter_by(username='user1').first():
            user1 = User(username='user1', is_admin=False)
            user1.set_password('user123')
            db.session.add(user1)
        
        # İstasyonları ekle (Kocaeli ilçeleri)
        if Station.query.count() == 0:
            for district, coords in Config.KOCAELI_DISTRICTS.items():
                station = Station(
                    name=district,
                    latitude=coords['lat'],
                    longitude=coords['lon']
                )
                db.session.add(station)
        
        # Araçları ekle
        if Vehicle.query.count() == 0:
            for vehicle_data in Config.INITIAL_VEHICLES:
                vehicle = Vehicle(
                    name=vehicle_data['name'],
                    capacity=vehicle_data['capacity'],
                    rental_cost=vehicle_data['rental_cost']
                )
                db.session.add(vehicle)
        
        # Parametreleri ekle
        if Parameter.query.count() == 0:
            params = [
                {'key': 'COST_PER_KM', 'value': str(Config.COST_PER_KM), 'description': 'Kilometre başına maliyet (birim/km)'},
                {'key': 'RENTAL_COST', 'value': str(Config.RENTAL_VEHICLE_COST), 'description': 'Araç kiralama maliyeti (birim)'},
                {'key': 'RENTAL_CAPACITY', 'value': str(Config.RENTAL_VEHICLE_CAPACITY), 'description': 'Kiralanan araç kapasitesi (kg)'}
            ]
            for param in params:
                p = Parameter(**param)
                db.session.add(p)
        
        db.session.commit()


# Routes - Giriş/Çıkış
@app.route('/')
def index():
    """Ana sayfa"""
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Giriş sayfası"""
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('user_dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            if user.is_admin:
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('user_dashboard'))
        else:
            flash('Kullanıcı adı veya şifre hatalı!', 'danger')
    
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Kayıt sayfası"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not username or not password or not confirm_password:
            flash('Lütfen tüm alanları doldurunuz.', 'danger')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Şifreler eşleşmiyor.', 'danger')
            return render_template('register.html')
        
        if User.query.filter_by(username=username).first():
            flash('Bu kullanıcı adı zaten alınmış.', 'danger')
            return render_template('register.html')
        
        user = User(username=username, is_admin=False)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('Kayıt başarılı! Şimdi giriş yapabilirsiniz.', 'success')
        return redirect(url_for('login'))
        
    return render_template('register.html')


@app.route('/logout')
@login_required
def logout():
    """Çıkış"""
    logout_user()
    return redirect(url_for('index'))


# Kullanıcı Paneli Routes
@app.route('/user/dashboard')
@login_required
def user_dashboard():
    """Kullanıcı ana panel"""
    if current_user.is_admin:
        return redirect(url_for('admin_dashboard'))
    
    # Kullanıcının kargoları
    cargos = Cargo.query.filter_by(user_id=current_user.id).order_by(Cargo.created_at.desc()).all()
    
    return render_template('user/dashboard.html', cargos=cargos)


@app.route('/user/send_cargo', methods=['GET', 'POST'])
@login_required
def send_cargo():
    """Kargo gönderimi"""
    if current_user.is_admin:
        return redirect(url_for('admin_dashboard'))
    
    stations = Station.query.filter_by(is_active=True).all()
    
    if request.method == 'POST':
        station_id = request.form.get('station_id')
        weight = request.form.get('weight')
        delivery_date = request.form.get('delivery_date')
        
        # Validasyon
        if not station_id or not weight or not delivery_date:
            flash('Tüm alanları doldurunuz!', 'danger')
            return render_template('user/send_cargo.html', stations=stations)
        
        try:
            station_id = int(station_id)
            weight = float(weight)
            delivery_date = datetime.strptime(delivery_date, '%Y-%m-%d').date()
        except:
            flash('Geçersiz veri girişi!', 'danger')
            return render_template('user/send_cargo.html', stations=stations)
        
        # İstasyon kontrolü (Strict Validation)
        # Sadece config'de tanımlı istasyonlar kabul edilir
        valid_districts = Config.KOCAELI_DISTRICTS.keys()
        
        station = Station.query.get(station_id)
        if not station or station.name not in valid_districts:
            flash('Geçersiz istasyon seçimi! Lütfen listeden bir ilçe seçiniz.', 'danger')
            return render_template('user/send_cargo.html', stations=stations)
        
        # Kargo oluştur
        cargo = Cargo(
            user_id=current_user.id,
            station_id=station_id,
            weight=weight,
            delivery_date=delivery_date,
            status='pending'
        )
        db.session.add(cargo)
        db.session.commit()
        
        flash('Kargo kaydı başarıyla oluşturuldu!', 'success')
        return redirect(url_for('user_dashboard'))
    
    return render_template('user/send_cargo.html', stations=stations)


@app.route('/user/my_cargo/<int:cargo_id>')
@login_required
def view_cargo(cargo_id):
    """Kargo detayı ve güzergah görüntüleme"""
    if current_user.is_admin:
        return redirect(url_for('admin_dashboard'))
    
    cargo = Cargo.query.get_or_404(cargo_id)
    
    # Yetki kontrolü
    if cargo.user_id != current_user.id:
        flash('Bu kargoya erişim yetkiniz yok!', 'danger')
        return redirect(url_for('user_dashboard'))
    
    # Kargonun rotası var mı?
    assignment = RouteAssignment.query.filter_by(cargo_id=cargo_id).first()
    route_data = None
    
    if assignment:
        route = Route.query.get(assignment.route_id)
        if route:
            route_data = {
                'vehicle': route.vehicle,
                'stations': json.loads(route.route_order) if route.route_order else [],
                'distance': route.total_distance,
                'cost': route.total_cost
            }
            
            # Harita oluştur
            map_html = create_user_route_map(cargo.station, route_data)
            return render_template('user/cargo_detail.html', cargo=cargo, route=route_data, map_html=map_html)
    
    return render_template('user/cargo_detail.html', cargo=cargo, route=None, map_html=None)


# Yönetici Paneli Routes
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    """Yönetici ana panel"""
    if not current_user.is_admin:
        return redirect(url_for('user_dashboard'))
    
    # İstatistikler
    total_stations = Station.query.filter_by(is_active=True).count()
    total_vehicles = Vehicle.query.filter_by(is_active=True).count()
    pending_cargos = Cargo.query.filter_by(status='pending').count()
    total_trips = Trip.query.count()
    
    # Son seferler
    recent_trips = Trip.query.order_by(Trip.created_at.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html', 
                         stats={
                             'stations': total_stations,
                             'vehicles': total_vehicles,
                             'pending_cargos': pending_cargos,
                             'trips': total_trips
                         },
                         recent_trips=recent_trips)


@app.route('/admin/bulk_cargo', methods=['GET', 'POST'])
@login_required
def bulk_cargo():
    """Toplu kargo ekleme - Dokümantasyona göre kargo sayısı ve toplam ağırlık ile"""
    if not current_user.is_admin:
        return redirect(url_for('user_dashboard'))
    
    stations = Station.query.filter_by(is_active=True).all()
    users = User.query.filter_by(is_admin=False).all()
    
    if request.method == 'POST':
        station_id = request.form.get('station_id')
        cargo_count = request.form.get('cargo_count')
        total_weight = request.form.get('total_weight')
        delivery_date = request.form.get('delivery_date')
        user_id = request.form.get('user_id')
        
        # Validasyon
        if not station_id or not cargo_count or not total_weight or not delivery_date or not user_id:
            flash('Tüm alanları doldurunuz!', 'danger')
            return render_template('admin/bulk_cargo.html', stations=stations, users=users)
        
        try:
            station_id = int(station_id)
            cargo_count = int(cargo_count)
            total_weight = float(total_weight)
            delivery_date = datetime.strptime(delivery_date, '%Y-%m-%d').date()
            user_id = int(user_id)
        except:
            flash('Geçersiz veri girişi!', 'danger')
            return render_template('admin/bulk_cargo.html', stations=stations, users=users)
        
        # İstasyon kontrolü
        station = Station.query.get(station_id)
        if not station:
            flash('Geçersiz istasyon!', 'danger')
            return render_template('admin/bulk_cargo.html', stations=stations, users=users)
        
        # Kullanıcı kontrolü
        user = User.query.get(user_id)
        if not user:
            flash('Geçersiz kullanıcı!', 'danger')
            return render_template('admin/bulk_cargo.html', stations=stations, users=users)
        
        # Kargo sayısı ve ağırlık kontrolü
        if cargo_count <= 0:
            flash('Kargo sayısı 0\'dan büyük olmalıdır!', 'danger')
            return render_template('admin/bulk_cargo.html', stations=stations, users=users)
        
        if total_weight <= 0:
            flash('Toplam ağırlık 0\'dan büyük olmalıdır!', 'danger')
            return render_template('admin/bulk_cargo.html', stations=stations, users=users)
        
        # Her kargo için ağırlık hesapla (eşit dağıt)
        weight_per_cargo = total_weight / cargo_count
        
        # Kargoları oluştur
        created_count = 0
        for i in range(cargo_count):
            cargo = Cargo(
                user_id=user_id,
                station_id=station_id,
                weight=weight_per_cargo,
                delivery_date=delivery_date,
                status='pending'
            )
            db.session.add(cargo)
            created_count += 1
        
        db.session.commit()
        
        flash(f'{created_count} adet kargo başarıyla oluşturuldu! (Toplam: {total_weight} kg, İstasyon: {station.name})', 'success')
        return redirect(url_for('bulk_cargo'))
    
    return render_template('admin/bulk_cargo.html', stations=stations, users=users)


@app.route('/admin/stations', methods=['GET', 'POST'])
@login_required
def manage_stations():
    """İstasyon yönetimi"""
    if not current_user.is_admin:
        return redirect(url_for('user_dashboard'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')
        
        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except:
            flash('Geçersiz koordinat değerleri!', 'danger')
            return redirect(url_for('manage_stations'))
        
        # Aynı isimde istasyon var mı?
        if Station.query.filter_by(name=name).first():
            flash('Bu isimde bir istasyon zaten mevcut!', 'danger')
            return redirect(url_for('manage_stations'))
        
        station = Station(name=name, latitude=latitude, longitude=longitude)
        db.session.add(station)
        db.session.commit()
        
        flash(f'{name} istasyonu başarıyla eklendi!', 'success')
        return redirect(url_for('manage_stations'))
    
    stations = Station.query.all()
    
    # İstasyonları haritada göster
    map_html = create_stations_map(stations)
    
    return render_template('admin/stations.html', stations=stations, map_html=map_html)


@app.route('/admin/plan_route', methods=['GET', 'POST'])
@login_required
def plan_route():
    """Rota planlama"""
    if not current_user.is_admin:
        return redirect(url_for('user_dashboard'))
    
    if request.method == 'POST':
        problem_type = request.form.get('problem_type')  # 'unlimited' or 'limited'
        delivery_date = request.form.get('delivery_date')
        optimization_target = request.form.get('optimization_target', 'weight')  # 'weight' or 'count'
        
        if not delivery_date:
            flash('Teslimat tarihini seçiniz!', 'danger')
            return redirect(url_for('plan_route'))
        
        try:
            delivery_date = datetime.strptime(delivery_date, '%Y-%m-%d').date()
        except:
            flash('Geçersiz tarih!', 'danger')
            return redirect(url_for('plan_route'))
        
        # O tarih için bekleyen kargoları al
        cargos = Cargo.query.filter_by(delivery_date=delivery_date, status='pending').all()
        
        if not cargos:
            flash('Seçilen tarih için bekleyen kargo bulunamadı!', 'warning')
            return redirect(url_for('plan_route'))
        
        # Kargoları istasyonlara göre grupla
        cargos_by_station = {}
        stations = Station.query.filter_by(is_active=True).all()
        
        for station in stations:
            station_cargos = [c for c in cargos if c.station_id == station.id]
            if station_cargos:
                cargos_by_station[station.name] = {
                    'weight': sum(c.weight for c in station_cargos),
                    'count': len(station_cargos),
                    'cargo_ids': [c.id for c in station_cargos]
                }
        
        if not cargos_by_station:
            flash('İşlenecek kargo bulunamadı!', 'warning')
            return redirect(url_for('plan_route'))
        
        # Mesafe matrisi oluştur
        stations_dict = {s.name: {'lat': s.latitude, 'lon': s.longitude} for s in stations}
        university = Config.UNIVERSITY_LOCATION
        distance_matrix, road_network = calculate_distance_matrix(stations_dict, university)
        
        # Araçları al
        vehicles = Vehicle.query.filter_by(is_active=True).all()
        vehicles_data = [{'id': v.id, 'capacity': v.capacity, 'rental_cost': v.rental_cost} for v in vehicles]
        
        # Parametreleri al
        cost_per_km = float(Parameter.query.filter_by(key='COST_PER_KM').first().value)
        rental_cost = float(Parameter.query.filter_by(key='RENTAL_COST').first().value)
        rental_capacity = float(Parameter.query.filter_by(key='RENTAL_CAPACITY').first().value)
        
        # Optimizasyon çöz
        if problem_type == 'unlimited':
            solver = UnlimitedVehicleProblem(
                cargos_by_station,
                vehicles_data,
                distance_matrix,
                cost_per_km,
                rental_cost,
                rental_capacity
            )
            routes = solver.solve()
        else:  # limited
            solver = LimitedVehicleProblem(
                cargos_by_station,
                vehicles_data,
                distance_matrix,
                cost_per_km
            )
            routes = solver.solve(optimization_target)
        
        # Sefer kaydet
        trip = Trip(
            trip_date=delivery_date,
            problem_type=problem_type,
            total_cost=sum(r['total_cost'] for r in routes),
            total_distance=sum(r['total_distance'] for r in routes),
            vehicle_count=len(routes),
            cargo_count=sum(r['cargo_count'] for r in routes),
            total_weight=sum(r['total_weight'] for r in routes)
        )
        
        # Kabul edilen ve reddedilen kargolar
        accepted_cargo_ids = set()
        for route in routes:
            accepted_cargo_ids.update(route['cargo_ids'])
        
        trip.accepted_cargo_count = len(accepted_cargo_ids)
        trip.rejected_cargo_count = len(cargos) - len(accepted_cargo_ids)
        
        db.session.add(trip)
        db.session.flush()
        
        # Rotaları kaydet
        for route_data in routes:
            # Araç bilgisini al veya kirala
            vehicle = None
            if 'id' in route_data['vehicle']:
                vehicle = Vehicle.query.get(route_data['vehicle']['id'])
            else:
                # Yeni araç kirala
                vehicle_count = Vehicle.query.filter_by(is_rented=True).count()
                vehicle = Vehicle(
                    name=f'Kiralık Araç {vehicle_count + 1}',
                    capacity=rental_capacity,
                    rental_cost=rental_cost,
                    is_rented=True
                )
                db.session.add(vehicle)
                db.session.flush()
            
            route = Route(
                trip_id=trip.id,
                vehicle_id=vehicle.id,
                route_order=json.dumps(route_data['stations']),
                total_distance=route_data['total_distance'],
                total_cost=route_data['total_cost'],
                total_weight=route_data['total_weight'],
                cargo_count=route_data['cargo_count']
            )
            db.session.add(route)
            db.session.flush()
            
            # Kargo atamalarını yap
            for cargo_id in route_data['cargo_ids']:
                assignment = RouteAssignment(route_id=route.id, cargo_id=cargo_id)
                db.session.add(assignment)
                
                # Kargo durumunu güncelle
                cargo = Cargo.query.get(cargo_id)
                cargo.status = 'assigned'
        
        # Reddedilen kargoları işaretle
        for cargo in cargos:
            if cargo.id not in accepted_cargo_ids:
                cargo.status = 'rejected'
        
        db.session.commit()
        
        flash(f'Rota planlaması başarıyla tamamlandı! {len(routes)} araç için rota oluşturuldu.', 'success')
        return redirect(url_for('view_trip', trip_id=trip.id))
    
    # GET request
    # Yarının tarihi varsayılan
    tomorrow = datetime.now().date() + timedelta(days=1)
    
    return render_template('admin/plan_route.html', default_date=tomorrow.strftime('%Y-%m-%d'))


@app.route('/admin/trip/<int:trip_id>')
@login_required
def view_trip(trip_id):
    """Sefer detayları"""
    if not current_user.is_admin:
        return redirect(url_for('user_dashboard'))
    
    trip = Trip.query.get_or_404(trip_id)
    routes = Route.query.filter_by(trip_id=trip_id).all()
    
    # Harita oluştur
    map_html = create_trip_map(trip, routes)
    
    # Her rota için detaylar
    routes_details = []
    for route in routes:
        cargo_ids = [a.cargo_id for a in route.assignments]
        cargos = Cargo.query.filter(Cargo.id.in_(cargo_ids)).all()
        users = list(set([c.user for c in cargos]))
        
        routes_details.append({
            'route': route,
            'cargos': cargos,
            'users': users,
            'stations': json.loads(route.route_order) if route.route_order else []
        })
    
    return render_template('admin/trip_detail.html', trip=trip, routes=routes_details, map_html=map_html)


@app.route('/admin/trips')
@login_required
def list_trips():
    """Tüm seferler"""
    if not current_user.is_admin:
        return redirect(url_for('user_dashboard'))
    
    trips = Trip.query.order_by(Trip.created_at.desc()).all()
    return render_template('admin/trips.html', trips=trips)


@app.route('/admin/load_scenario/<int:scenario_id>')
@login_required
def load_scenario(scenario_id):
    """Senaryo verilerini yükle"""
    if not current_user.is_admin:
        return redirect(url_for('user_dashboard'))
    
    if scenario_id not in SCENARIOS:
        flash('Geçersiz senaryo ID!', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    # Bekleyen kargoları temizle
    try:
        deleted = Cargo.query.filter_by(status='pending').delete()
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f'Hata: {str(e)}', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    scenario = SCENARIOS[scenario_id]
    data = scenario['data']
    
    # Yarının tarihi (varsayılan teslimat)
    delivery_date = datetime.now().date() + timedelta(days=1)
    
    # Atanacak kullanıcı (user1 veya ilk normal kullanıcı)
    user = User.query.filter_by(username='user1').first()
    if not user:
        user = User.query.filter_by(is_admin=False).first()
    
    if not user:
        flash('Sistemde kayıtlı kullanıcı bulunamadı! Lütfen önce bir kullanıcı oluşturun.', 'warning')
        return redirect(url_for('admin_dashboard'))
    
    created_count = 0
    total_weight_added = 0
    
    for station_name, info in data.items():
        count = info['count']
        weight = info['weight']
        
        if count > 0 and weight > 0:
            station = Station.query.filter_by(name=station_name).first()
            if station:
                weight_per_cargo = weight / count
                
                for _ in range(count):
                    cargo = Cargo(
                        user_id=user.id,
                        station_id=station.id,
                        weight=weight_per_cargo,
                        delivery_date=delivery_date,
                        status='pending'
                    )
                    db.session.add(cargo)
                    created_count += 1
                
                total_weight_added += weight
    
    db.session.commit()
    
    flash(f'Senaryo {scenario_id} yüklendi: {scenario["description"]}. Toplam {created_count} kargo, {total_weight_added} kg.', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/parameters', methods=['GET', 'POST'])
@login_required
def manage_parameters():
    """Parametre yönetimi"""
    if not current_user.is_admin:
        return redirect(url_for('user_dashboard'))
    
    if request.method == 'POST':
        for param in Parameter.query.all():
            new_value = request.form.get(f'param_{param.id}')
            if new_value:
                param.value = new_value
        
        db.session.commit()
        flash('Parametreler güncellendi!', 'success')
        return redirect(url_for('manage_parameters'))
    
    parameters = Parameter.query.all()
    return render_template('admin/parameters.html', parameters=parameters)


# Harita Yardımcı Fonksiyonları
def create_stations_map(stations):
    """İstasyonları haritada göster"""
    # Kocaeli merkezi
    m = folium.Map(location=[40.7654, 29.9400], zoom_start=10)
    
    # Üniversiteyi ekle
    folium.Marker(
        [Config.UNIVERSITY_LOCATION['lat'], Config.UNIVERSITY_LOCATION['lon']],
        popup='Kocaeli Üniversitesi',
        icon=folium.Icon(color='red', icon='university', prefix='fa')
    ).add_to(m)
    
    # İstasyonları ekle
    for station in stations:
        folium.Marker(
            [station.latitude, station.longitude],
            popup=station.name,
            icon=folium.Icon(color='blue', icon='warehouse', prefix='fa')
        ).add_to(m)
    
    return m._repr_html_()


def create_user_route_map(station, route_data):
    """Kullanıcı için tek rota haritası"""
    m = folium.Map(location=[40.7654, 29.9400], zoom_start=10)
    
    # Üniversite
    folium.Marker(
        [Config.UNIVERSITY_LOCATION['lat'], Config.UNIVERSITY_LOCATION['lon']],
        popup='Kocaeli Üniversitesi',
        icon=folium.Icon(color='red', icon='university', prefix='fa')
    ).add_to(m)
    
    # Kullanıcının istasyonu
    folium.Marker(
        [station.latitude, station.longitude],
        popup=station.name,
        icon=folium.Icon(color='green', icon='box', prefix='fa')
    ).add_to(m)
    
    # Rota varsa çiz
    if route_data and route_data['stations']:
        stations_dict = {s.name: {'lat': s.latitude, 'lon': s.longitude} for s in Station.query.all()}
        university = Config.UNIVERSITY_LOCATION
        
        road_network = RoadNetwork(stations_dict, university)
        
        # Rota çiz
        current = 'university'
        for station_name in route_data['stations']:
            path, _ = road_network.get_shortest_path(current, station_name)
            coords = road_network.get_route_coordinates(path)
            
            folium.PolyLine(
                coords,
                color='blue',
                weight=3,
                opacity=0.7
            ).add_to(m)
            
            current = station_name
        
        # Dönüş
        path, _ = road_network.get_shortest_path(current, 'university')
        coords = road_network.get_route_coordinates(path)
        folium.PolyLine(coords, color='blue', weight=3, opacity=0.7).add_to(m)
    
    return m._repr_html_()


def create_trip_map(trip, routes):
    """Sefer için tüm rotaları gösteren harita"""
    m = folium.Map(location=[40.7654, 29.9400], zoom_start=10)
    
    # Üniversite
    folium.Marker(
        [Config.UNIVERSITY_LOCATION['lat'], Config.UNIVERSITY_LOCATION['lon']],
        popup='Kocaeli Üniversitesi',
        icon=folium.Icon(color='red', icon='university', prefix='fa')
    ).add_to(m)
    
    # İstasyonlar
    stations = {s.name: s for s in Station.query.all()}
    stations_dict = {s.name: {'lat': s.latitude, 'lon': s.longitude} for s in Station.query.all()}
    university = Config.UNIVERSITY_LOCATION
    
    road_network = RoadNetwork(stations_dict, university)
    
    # Her rota için farklı renk
    colors = ['blue', 'green', 'purple', 'orange', 'darkred', 'darkblue', 'darkgreen', 'cadetblue']
    
    for idx, route in enumerate(routes):
        color = colors[idx % len(colors)]
        station_order = json.loads(route.route_order) if route.route_order else []
        
        # İstasyonları işaretle
        for station_name in station_order:
            if station_name in stations:
                station = stations[station_name]
                folium.CircleMarker(
                    [station.latitude, station.longitude],
                    radius=8,
                    popup=f'{station_name}<br>Araç: {route.vehicle.name}',
                    color=color,
                    fill=True,
                    fillColor=color
                ).add_to(m)
        
        # Rotayı çiz
        current = 'university'
        for station_name in station_order:
            path, _ = road_network.get_shortest_path(current, station_name)
            coords = road_network.get_route_coordinates(path)
            
            folium.PolyLine(
                coords,
                color=color,
                weight=4,
                opacity=0.7,
                popup=f'{route.vehicle.name}'
            ).add_to(m)
            
            current = station_name
        
        # Dönüş
        path, _ = road_network.get_shortest_path(current, 'university')
        coords = road_network.get_route_coordinates(path)
        folium.PolyLine(coords, color=color, weight=4, opacity=0.7).add_to(m)
    
    return m._repr_html_()


@app.route('/admin/reports')
@login_required
def scenario_reports():
    """Senaryo Karşılaştırma Raporu"""
    if not current_user.is_admin:
        return redirect(url_for('user_dashboard'))
    
    # Rapor verilerini hazırla (Dökümantasyondaki ve hesaplanan veriler)
    # Gerçek zamanlı hesaplama yerine, senaryo tanımlarından beklenenleri gösteriyoruz
    # Çünkü "olası senaryolar için özet tablo" isteniyor.
    
    reports = []
    
    # Mesafe hesaplaması için (Yaklaşık bir rota simülasyonu)
    # Not: Gerçek optimizasyon sonucu anlık değişebilir, burada teorik senaryo verilerini kıyaslıyoruz
    
    for sc_id, sc_data in SCENARIOS.items():
        data = sc_data['data']
        total_cargo = sum(d['count'] for d in data.values())
        total_weight = sum(d['weight'] for d in data.values())
        
        # Basit bir maliyet tahmini (Heuristic)
        # Sınırsız araç: Kapasite (2250) yetmiyorsa kiralama
        vehicle_capacity = sum(v['capacity'] for v in Config.INITIAL_VEHICLES)
        rental_needed = 0
        rental_cost = 0
        
        excess_weight = max(0, total_weight - vehicle_capacity)
        if excess_weight > 0:
            count = math.ceil(excess_weight / Config.RENTAL_VEHICLE_CAPACITY)
            rental_cost = count * Config.RENTAL_VEHICLE_COST
            rental_needed = count
            
        reports.append({
            'name': f'Senaryo {sc_id}',
            'desc': sc_data['description'],
            'total_cargo': total_cargo,
            'total_weight': total_weight,
            'vehicles_owned': 3,
            'vehicles_rented': rental_needed,
            'rental_cost': rental_cost
        })
        
    return render_template('admin/reports.html', reports=reports)


if __name__ == '__main__':
    init_database()
    app.run(debug=True, host='0.0.0.0', port=5000)

