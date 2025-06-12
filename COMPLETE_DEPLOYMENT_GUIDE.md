# Tam Deployment Rehberi: GitHub + Render.com

## 📚 1. GitHub'a Yükleme (Public Repository)

### GitHub Repository URL'sini Al
Public repository oluşturduktan sonra repository sayfasında:
- Yeşil **"Code"** butonuna tıkla
- **HTTPS** sekmesinde URL'yi kopyala
- Örnek: `https://github.com/kullaniciadin/sitemap-generator.git`

### Replit Shell'de Komutları Çalıştır

```bash
# 1. Dosyaları staging area'ya ekle
git add .

# 2. Commit oluştur
git commit -m "Production ready: Sitemap Generator with ultra-fast subdomain indexing"

# 3. GitHub repository'yi bağla (URL'yi kendi URL'inle değiştir)
git remote add origin https://github.com/KULLANICI_ADIN/sitemap-generator.git

# 4. Ana branch'i main olarak ayarla
git branch -M main

# 5. Kodu GitHub'a yükle
git push -u origin main
```

### Kimlik Doğrulama
- **Username**: GitHub kullanıcı adın
- **Password**: Personal Access Token (şifre değil!)

**Token almak için:**
1. GitHub → Profil → Settings
2. Sol menüde "Developer settings"
3. "Personal access tokens" → "Tokens (classic)"
4. "Generate new token" → "repo" yetkilerini seç
5. Token'ı kopyala ve sakla

## 🚀 2. Render.com Deployment

### Render.com Hesap Oluştur
1. **render.com** adresine git
2. "Get Started for Free" tıkla
3. GitHub ile giriş yap (önerilen)

### Web Service Oluştur
1. Dashboard'da **"New +"** → **"Web Service"**
2. **"Build and deploy from a Git repository"** seç
3. GitHub hesabını bağla (izin ver)
4. Repository listesinden **sitemap-generator** seç
5. **"Connect"** tıkla

### Deployment Ayarları
Render otomatik olarak ayarları algılar:

**Kontrol et:**
- **Name**: sitemap-generator
- **Region**: Oregon (US West) - en yakın
- **Branch**: main
- **Build Command**: `pip install poetry && poetry config virtualenvs.create false && poetry install --only main`
- **Start Command**: `gunicorn --bind 0.0.0.0:$PORT --workers 1 --timeout 300 app:app`
- **Plan**: Free

### Deployment Başlat
1. **"Create Web Service"** tıkla
2. Deployment başlar (5-10 dakika)
3. Logları izle: Build → Deploy → Live

### URL'yi Al
- Deployment tamamlandığında live URL alırsın
- Örnek: `https://sitemap-generator-abc123.onrender.com`

## ✅ 3. Test ve Doğrulama

### Deployment Kontrolü
1. URL'yi tarayıcıda aç
2. Ana sayfa yükleniyor mu?
3. Site URL'si gir ve crawl et
4. Sitemap download çalışıyor mu?

### Performans Testi
- Küçük site ile test: `example.com`
- Orta site ile test: `togetherplatform.com`
- Türkçe site ile test: herhangi bir .com.tr

## 🔧 4. Production Ayarları

### Environment Variables (Opsiyonel)
Render dashboard'da:
1. Environment sekmesine git
2. İsterersen şunları ekle:
   - `FLASK_ENV`: production
   - `PYTHONUNBUFFERED`: 1

### Custom Domain (Opsiyonel)
Kendi domain'in varsa:
1. Settings → Custom Domains
2. Domain ekle ve DNS ayarları yap

## 📊 5. Free Tier Özellikleri

### Avantajlar
- Tamamen ücretsiz
- Otomatik HTTPS
- GitHub integration
- Otomatik deployments

### Limitler
- 750 saat/ay (günde ~25 saat)
- 15 dakika inaktivite sonrası sleep
- 512MB RAM limit
- Cold start: 30 saniye

### Sleep Mode Çözümü
- UptimeRobot gibi servisle ping at
- Kullanıcılara "İlk yükleme 30 saniye sürebilir" uyarısı

## 🔄 6. Güncellemeler

### Kod Güncellemesi
```bash
git add .
git commit -m "Feature: yeni özellik açıklaması"
git push origin main
```
Render otomatik olarak yeniden deploy eder.

### Monitoring
- Render dashboard'dan logları izle
- Error notifications setup yap
- Metrics takip et

## 🚨 Sorun Çözme

### GitHub Upload Sorunları
- "Permission denied": Token kullan, şifre değil
- "Repository not found": URL'yi kontrol et
- "Authentication failed": Token permissions kontrol et

### Render Deployment Sorunları
- Build failed: Logları kontrol et
- Service unavailable: Sleep mode, birkaç saniye bekle
- Memory errors: Çok büyük site taramaktan kaçın

## 📞 Destek
- GitHub: docs.github.com
- Render: render.com/docs
- Bu proje: README_RENDER_DEPLOYMENT.md