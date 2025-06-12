# GitHub'a Proje Yükleme Rehberi

## 📋 Adım Adım GitHub Upload

### 1. GitHub'da Repository Oluştur
1. **github.com** adresine git
2. Sağ üstte **"+"** işaretine tıkla
3. **"New repository"** seç
4. Repository adı: `sitemap-generator`
5. **"Public"** seç (ücretsiz)
6. **"Create repository"** tıkla

### 2. Repository URL'sini Kopyala
- Oluşturulan sayfada **"HTTPS"** sekmesindeki URL'yi kopyala
- Örnek: `https://github.com/kullaniciadin/sitemap-generator.git`

### 3. Replit'te Terminal Aç
- Sol panelde **"Shell"** sekmesine tıkla
- Veya Ctrl+` (backtick) tuş kombinasyonu

### 4. Git Komutlarını Çalıştır

```bash
# Git repository başlat
git init

# Dosyaları ekle
git add .

# İlk commit oluştur
git commit -m "Sitemap Generator - Production Ready"

# Ana branch ayarla
git branch -M main

# GitHub repository'yi bağla (URL'yi kendi URL'inle değiştir)
git remote add origin https://github.com/KULLANICI_ADIN/sitemap-generator.git

# Kodu GitHub'a yükle
git push -u origin main
```

### 5. GitHub Credentials
Eğer kimlik doğrulama isterse:
- **Username**: GitHub kullanıcı adın
- **Password**: GitHub Personal Access Token (şifre değil)

#### Personal Access Token Nasıl Alınır:
1. GitHub'da **Settings** → **Developer settings**
2. **Personal access tokens** → **Tokens (classic)**
3. **"Generate new token"**
4. **"repo"** yetkilerini seç
5. Token'ı kopyala ve sakla

## 🔄 Güncellemeler İçin

Proje üzerinde değişiklik yaptığında:
```bash
git add .
git commit -m "Update: açıklama"
git push origin main
```

## ✅ Başarı Kontrolü
- GitHub repo sayfanda dosyaların görünüyor olması
- `render.yaml`, `app.py`, `enhanced_crawler.py` gibi dosyaların mevcut olması

## 🚨 Sorun Çözme

### "Permission denied" hatası:
```bash
git remote set-url origin https://KULLANICI_ADIN:TOKEN@github.com/KULLANICI_ADIN/sitemap-generator.git
```

### "Repository not found":
- Repository URL'sini kontrol et
- Public olarak oluşturulduğundan emin ol

### "Authentication failed":
- Personal Access Token kullan (şifre değil)
- Token'ın "repo" yetkilerini kontrol et