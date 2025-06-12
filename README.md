# Sitemap Generator

Professional sitemap generator with ultra-fast subdomain indexing and comprehensive web crawling capabilities.

## Features

- **Lightning-fast crawling** with 0.8s timeouts for optimal performance
- **Comprehensive subdomain discovery** - automatically finds and indexes all subdomains
- **Deep URL pattern analysis** - discovers hidden pages through pattern recognition
- **Multi-source detection** - combines sitemap parsing, robots.txt analysis, and deep crawling
- **Turkish interface** with real-time progress updates
- **CSV export** with URLs and page titles (up to 10,000 URLs)
- **Production-ready** with memory optimization and rate limiting

## Technology Stack

- **Backend**: Flask with advanced crawling algorithms
- **Frontend**: Vanilla JavaScript with real-time updates
- **Crawling**: Multi-threaded with BeautifulSoup and requests
- **Export**: XML sitemap and CSV formats
- **Deployment**: Optimized for Render.com free tier

## Production Deployment

### Render.com (Recommended)
1. Fork this repository to your GitHub account
2. Connect to Render.com with your GitHub account
3. Create new Web Service from this repository
4. Render will automatically detect configuration from `render.yaml`
5. Deploy with one click - no configuration needed

### Features in Production
- **Memory optimization** - automatic cleanup every 5 minutes
- **Rate limiting** - prevents abuse and ensures stability
- **Gunicorn server** - production-grade WSGI server
- **Free tier optimized** - works within 512MB RAM limits

## Usage

1. Enter website URL (e.g., `example.com`)
2. Click "Sitemap Oluştur" to start crawling
3. Monitor real-time progress with Turkish interface
4. Download XML sitemap or CSV export when complete

## Performance

- **Ultra-fast timeouts**: 0.8 seconds per request
- **Subdomain discovery**: Automatically finds all subdomains
- **Pattern recognition**: Discovers hidden URL structures
- **Comprehensive indexing**: Up to 10,000 URLs per crawl

## Free Deployment

This application is optimized for free hosting on Render.com:
- 750 hours/month free tier
- Automatic HTTPS and custom domains
- GitHub integration for automatic deployments
- No credit card required

## License

MIT License - Free for commercial and personal use.
