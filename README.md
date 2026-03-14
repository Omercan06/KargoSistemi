# 🚚 Akıllı Kargo Takip ve Rota Optimizasyon Sistemi

Bu proje, müşterilerin kargo gönderimi yapabildiği ve yöneticilerin bu kargoları en düşük maliyet/mesafe ile dağıtmak için akıllı rota optimizasyonları yapabildiği web tabanlı bir lojistik yönetim sistemidir. Flask framework'ü ile geliştirilmiş olup, Folium kütüphanesi ile interaktif harita destekli rota çizimleri sunar. 

Sistem, teslimat süreçlerini **Sınırlı Araç** ve **Sınırsız Araç (Kiralama)** algoritmalarıyla optimize ederek lojistik maliyetlerini minimuma indirmeyi hedefler.

## 🚀 Temel Özellikler

Sistem **Yönetici (Admin)** ve **Müşteri (User)** olmak üzere iki temel role ayrılmıştır.

### 👨‍💻 Yönetici (Admin) Paneli
* **Akıllı Rota Planlama (VRP Optimizasyonu):** Belirli bir tarihteki bekleyen kargolar için en uygun rotaları hesaplama. İki farklı problem tipini çözer:
  * *Sınırsız Araç Problemi:* Eldeki araçların kapasitesi yetmediğinde sistem otomatik olarak yeni araç kiralama maliyetlerini hesaplayarak rotayı böler.
  * *Sınırlı Araç Problemi:* Sadece mevcut araçlar kullanılarak, ağırlık veya kargo sayısına göre (Optimizasyon Hedefi) en verimli teslimatları seçer, kalanları reddeder/erteler.
* **İnteraktif Haritalama:** Kocaeli Üniversitesi merkez alınarak belirlenen ilçe istasyonlarını ve hesaplanan teslimat rotalarını Folium üzerinden renkli çizgilerle görselleştirme.
* **İstasyon ve Parametre Yönetimi:** Yeni istasyonlar (ilçeler/koordinatlar) ekleyebilme; km başına maliyet, araç kiralama bedeli ve kapasitesi gibi dinamik parametreleri sistem üzerinden güncelleyebilme.
* **Toplu Kargo ve Senaryo Yükleme:** Sistemi test etmek için tek tuşla hazır senaryolar yükleme veya belirtilen istasyona eşit ağırlıklarda toplu kargo girişi yapabilme.

### 📦 Müşteri (Kullanıcı) Paneli
* **Kargo Gönderimi:** Listelenen aktif istasyonlardan birini seçerek kargo ağırlığını ve istenilen teslimat tarihini belirleyip gönderi talebi oluşturma.
* **Durum Takibi:** Gönderilen kargoların "Bekliyor", "Atandı", "Reddedildi" gibi durumlarını anlık izleyebilme.
* **Kişisel Rota Görüntüleme:** Kargosu bir araca atandığında, o kargonun üniversiteden çıkıp kendi istasyonuna kadar izleyeceği rotayı harita üzerinde görebilme.

## 🛠️ Kullanılan Teknolojiler

* **Backend:** Python 3.x, Flask
* **Veritabanı ve ORM:** Flask-SQLAlchemy
* **Kimlik Doğrulama:** Flask-Login, Werkzeug Security (Şifre Hashleme)
* **Haritalama:** Folium
* **Optimizasyon ve Matematiksel İşlemler:** NumPy, NetworkX (Graf ve düğüm hesaplamaları), Geopy

## 🗄️ Veritabanı Modelleri
Proje sağlam bir ilişkisel veritabanı şemasına sahiptir:
* `User`: Yönetici ve müşteri bilgileri.
* `Station`: İstasyon koordinatları ve aktiflik durumları.
* `Vehicle`: Araç kapasiteleri ve kiralık olma durumları.
* `Cargo`: Müşteri bazlı gönderiler, ağırlıklar ve statüler.
* `Trip` & `Route`: Gerçekleştirilen seferler ve bu seferlere bağlı araçların taşıdığı yükler, maliyetler, kat edilen mesafe kayıtları.
* `RouteAssignment`: Hangi kargonun hangi rotada/araçta olduğunun eşleştirmesi.
* `Parameter`: Sistemdeki dinamik hesaplama çarpanları (Km maliyeti vb.).

## 💻 Kurulum ve Çalıştırma

Sistemi yerel bilgisayarınızda çalıştırmak için aşağıdaki adımları izleyin:

**1. Repoyu Klonlayın:**
```bash
git clone <repo_url>
cd <repo_klasor_adi>
