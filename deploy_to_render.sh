#!/bin/bash

# Render.com Deployment Script
# Bu script projeyi GitHub'a yükleyip Render.com deployment için hazırlar

echo "🚀 Render.com Deployment Hazırlığı Başlıyor..."

# Git repository kontrolü
if [ ! -d ".git" ]; then
    echo "📁 Git repository başlatılıyor..."
    git init
    git branch -M main
fi

# .gitignore kontrolü
if [ ! -f ".gitignore" ]; then
    echo "📝 .gitignore dosyası oluşturuluyor..."
    cat > .gitignore << EOF
__pycache__/
*.py[cod]
*.so
.env
.vscode/
*.log
crawler_backup_*.json
sitemap.xml
EOF
fi

# Dosyaları stage'e ekle
echo "📦 Dosyalar Git'e ekleniyor..."
git add .

# Commit oluştur
echo "💾 Commit oluşturuluyor..."
git commit -m "Production ready: Sitemap Generator for Render.com deployment

Features:
- Ultra-fast subdomain indexing
- Lightning-fast sitemap discovery
- Rate limiting and memory optimization
- Production-ready configuration
- Supports 10,000+ URLs with CSV export"

echo "✅ Proje GitHub'a yüklenmeye hazır!"
echo ""
echo "Şimdi şu adımları takip et:"
echo "1. GitHub'da yeni repository oluştur"
echo "2. Bu komutu çalıştır: git remote add origin [REPO_URL]"
echo "3. Bu komutu çalıştır: git push -u origin main"
echo "4. render.com'a git ve 'New Web Service' oluştur"
echo "5. GitHub repo'yu bağla ve deploy et"
echo ""
echo "🎯 Render.com ayarları:"
echo "Build Command: pip install poetry && poetry config virtualenvs.create false && poetry install --only main"
echo "Start Command: gunicorn --bind 0.0.0.0:\$PORT --workers 1 --timeout 300 app:app"
echo ""
echo "📚 Detaylı rehber: README_RENDER_DEPLOYMENT.md"