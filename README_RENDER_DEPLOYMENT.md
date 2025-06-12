# Render.com Deployment Rehberi

## 🚀 Render.com ile Ücretsiz Deployment

### Öncesi Hazırlık
Proje render.com için optimize edildi:
- ✅ Production optimizasyonları eklendi
- ✅ Rate limiting sistemi kuruldu
- ✅ Memory management optimize edildi
- ✅ Gunicorn production server hazır

### Adım 1: GitHub'a Yükleme
```bash
git init
git add .
git commit -m "Initial commit - Sitemap Generator"
git branch -M main
git remote add origin [YOUR_GITHUB_REPO_URL]
git push -u origin main
```

### Adım 2: Render.com Setup
1. **render.com** adresine git
2. "Sign Up" ile hesap oluştur (GitHub ile giriş önerilen)
3. "New +" → "Web Service" seç
4. GitHub repo'yu bağla
5. Repository seç: sitemap-generator
6. Ayarları kontrol et:
   - **Build Command**: `pip install poetry && poetry config virtualenvs.create false && poetry install --only main`
   - **Start Command**: `gunicorn --bind 0.0.0.0:$PORT --workers 1 --timeout 300 app:app`
   - **Plan**: Free
7. "Create Web Service" tıkla

### Adım 3: Environment Variables (Opsiyonel)
Render dashboard'da Environment sekmesinden ekle:
- `FLASK_ENV`: production
- `PYTHONUNBUFFERED`: 1

### Adım 4: Deploy ve Test
- Deployment otomatik başlar (5-10 dakika)
- Live URL alırsın (örn: https://sitemap-generator-xyz.onrender.com)
- URL'yi test et

## 🔧 Render.com Ücretsiz Plan Özellikler

### ✅ Avantajlar
- Tamamen ücretsiz
- Otomatik HTTPS
- Custom domain desteği
- GitHub integration
- Otomatik deployments

### ⚠️ Limitler
- 750 saat/ay (günde ~25 saat)
- 15 dakika inaktivite sonrası sleep
- 512MB RAM
- Shared CPU
- İlk istek sonrası 30 saniye startup süresi

## 📊 Production Optimizasyonları

### Memory Management
- Otomatik garbage collection (5 dakika)
- Session cleanup (20 dakika)
- Optimized crawling limits

### Rate Limiting
- 30 saniyede max 3 istek per IP
- Otomatik rate limit koruması
- Friendly error messages

### Performance
- Gunicorn production server
- Single worker (free tier için optimal)
- 300 saniye timeout
- Memory-efficient crawling

## 🚨 Önemli Notlar

### Free Tier için İpuçları
1. **Sleep mode**: 15 dakika inaktivite sonrası site uyur
2. **Cold start**: İlk istek 30 saniye sürebilir
3. **Memory limit**: Çok büyük siteleri taramaktan kaçın
4. **Monthly limit**: 750 saat/ay = günde ~25 saat

### Monitoring
- Render dashboard'dan logları izle
- Performance metrics takip et
- Error alerts setup yap

## 🔄 Otomatik Deployment

Her GitHub push'ta otomatik deploy:
```bash
git add .
git commit -m "Update features"
git push origin main
```

## 🎯 Test Senaryoları

Deployment sonrası test et:
1. Ana sayfa yükleniyor mu?
2. Site crawling çalışıyor mu?
3. Sitemap download çalışıyor mu?
4. CSV export çalışıyor mu?

## 💡 Production Tips

### Kullanıcı Deneyimi
- Sleep mode için loading indicator ekle
- Cold start için warning göster
- Rate limit mesajlarını user-friendly yap

### Cost Optimization
- Gereksiz crawling işlemlerini önle
- Cache mekanizması ekle
- Efficient URL patterns kullan

## 📞 Destek

Render.com dokümantasyon:
- [Python Deployment Guide](https://render.com/docs/deploy-flask)
- [Environment Variables](https://render.com/docs/environment-variables)
- [Free Tier Limits](https://render.com/docs/free#free-web-services)