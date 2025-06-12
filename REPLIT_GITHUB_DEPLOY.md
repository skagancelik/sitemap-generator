# Replit GitHub Integration ile Deployment

## 🎯 GitHub Hesabı Replit'e Bağlı - Kolay Yol

### 1. Replit'ten Direkt GitHub'a Push

Sol panelde **"Version control"** (git ikonu) sekmesine tıkla:

1. **"Initialize Git"** (eğer görünürse)
2. Dosyaları seç veya "Stage all changes"
3. Commit message yaz: `"Production ready: Sitemap Generator"`
4. **"Commit & push"** tıkla
5. "Create new repository" seç
6. Repository adı: `sitemap-generator`
7. **Public** seç
8. **"Create & push"** tıkla

### 2. Alternatif: Existing Repository'ye Push

Eğer zaten repository oluşturmuşsan:
1. Version control sekmesinde
2. **"Connect to Git"** tıkla
3. GitHub repository URL'sini gir
4. Dosyaları stage et
5. Commit message yaz
6. **"Commit & push"** tıkla

## 🚀 Render.com Deployment

### Hızlı Setup
1. **render.com** → GitHub ile giriş yap
2. **"New +"** → **"Web Service"**
3. Repository seç: **sitemap-generator**
4. **"Connect"** tıkla
5. Ayarlar otomatik algılanır:
   - Build: `pip install poetry && poetry config virtualenvs.create false && poetry install --only main`
   - Start: `gunicorn --bind 0.0.0.0:$PORT --workers 1 --timeout 300 app:app`
6. **"Create Web Service"** tıkla

### Deployment Süreci
- Build: 3-5 dakika
- Deploy: 1-2 dakika
- Live URL: `https://sitemap-generator-xyz.onrender.com`

## ✅ Otomatik Güncelleme

Replit'te değişiklik yaptığında:
1. Version control → Stage changes
2. Commit message yaz
3. Push tıkla
4. Render otomatik yeniden deploy eder

## 🎯 Avantajlar

- Tek tıkla GitHub push
- Otomatik repository oluşturma
- Terminal komut gerektirmiyor
- Sürekli sync halinde
- Deploy pipeline otomatik

Bu yöntem çok daha pratik ve hızlı!