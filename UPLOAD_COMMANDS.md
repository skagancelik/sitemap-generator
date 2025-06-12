# GitHub Upload Komutları - Manuel Yöntem

## Durum
Replit'te git lock sorunu nedeniyle Version Control sekmesi çalışmıyor.

## Çözüm: Manual Upload

### 1. Replit üzerinden dosyaları indir
1. Sol panelde Files sekmesinde
2. Tüm dosyaları seç (Ctrl+A)
3. Sağ tık → Download
4. ZIP dosyası indir

### 2. GitHub'da manuel upload
1. GitHub'da repository sayfasına git
2. "Add file" → "Upload files"
3. ZIP'i extract et ve dosyaları sürükle
4. Commit message: "Production ready: Sitemap Generator"
5. "Commit changes" tıkla

### 3. Alternatif: GitHub Desktop
1. GitHub Desktop indir
2. Repository clone et
3. Replit dosyalarını kopyala
4. Commit & push

## Render.com Deployment
GitHub'a upload sonrası:
1. render.com → GitHub ile giriş
2. New Web Service → Repository seç
3. Auto-deploy ayarları: OK
4. Create service

## Test
- Build: 5-10 dakika
- Live URL alacaksın
- Sitemap generator çalışacak