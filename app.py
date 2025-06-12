from flask import Flask, render_template, request, jsonify, send_file
from enhanced_crawler import EnhancedCrawler
from sitemap_generator import SitemapGenerator
from production_optimizations import setup_memory_cleanup, rate_limit, PRODUCTION_CONFIG
import threading
import logging
import os
import uuid
import time
from threading import Lock
import atexit
import gc

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize production optimizations
setup_memory_cleanup()

# Production configuration for Render.com free tier
app.config.update(PRODUCTION_CONFIG)

# Thread-safe dictionary to store crawling sessions
crawling_sessions = {}
sessions_lock = Lock()

def cleanup_expired_sessions():
    """Clean up sessions older than 10 minutes that are not actively crawling"""
    current_time = time.time()
    expired_sessions = []
    
    with sessions_lock:
        for session_id, session_data in crawling_sessions.items():
            # Keep sessions active for 20 minutes (1200 seconds) to handle slow sites
            if current_time - session_data.get('last_access', session_data['start_time']) > 1200:
                if session_data.get('completed', False):
                    expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del crawling_sessions[session_id]
            logger.info(f"Cleaned up expired session: {session_id}")

# Start cleanup thread
def start_cleanup_thread():
    def cleanup_loop():
        while True:
            time.sleep(300)  # Run cleanup every 5 minutes to reduce overhead
            cleanup_expired_sessions()
    
    cleanup_thread = threading.Thread(target=cleanup_loop)
    cleanup_thread.daemon = True
    cleanup_thread.start()

start_cleanup_thread()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/crawl', methods=['POST'])
@rate_limit
def crawl():
    try:
        data = request.json
        if not data or 'url' not in data:
            return jsonify({"error": "URL is required"}), 400
            
        url = data['url'].strip()
        if not url:
            return jsonify({"error": "URL cannot be empty"}), 400
        
        # Generate unique session ID for each request
        session_id = str(uuid.uuid4())
        
        # Thread-safe session initialization
        with sessions_lock:
            crawling_sessions[session_id] = {
                'crawler': EnhancedCrawler(url),
                'sitemap_generator': SitemapGenerator(),
                'completed': False,
                'error': None,
                'start_time': time.time(),
                'last_access': time.time(),
                'url': url
            }

        def crawl_and_generate():
            try:
                with sessions_lock:
                    if session_id not in crawling_sessions:
                        logger.error(f"Session {session_id} not found during crawl")
                        return
                    
                    session_data = crawling_sessions[session_id]
                    crawler = session_data['crawler']
                    sitemap_gen = session_data['sitemap_generator']
                
                logger.info(f"Starting crawl for {url} (session: {session_id})")
                crawler.crawl()
                logger.info(f"Crawl completed for {url}. Found {len(crawler.visited)} URLs")
                
                with sessions_lock:
                    if session_id in crawling_sessions:
                        if crawler.visited:
                            success = sitemap_gen.generate(crawler.visited)
                            if success:
                                logger.info("Sitemap generated successfully")
                            else:
                                crawling_sessions[session_id]['error'] = "Failed to generate sitemap"
                        else:
                            # Detailed error information
                            error_details = f"URL: {url}\n"
                            error_details += f"Normalize edilmiş URL: {crawler.start_url}\n"
                            error_details += f"Domain: {crawler.domain}\n"
                            error_details += f"Visited URLs: {len(crawler.visited) if hasattr(crawler, 'visited') else 'N/A'}\n"
                            error_details += f"To visit URLs: {len(crawler.to_visit) if hasattr(crawler, 'to_visit') else 'N/A'}\n"
                            
                            # Test initial URL access
                            try:
                                test_response = crawler.session.get(crawler.start_url, timeout=10)
                                error_details += f"HTTP Status: {test_response.status_code}\n"
                                error_details += f"Content-Type: {test_response.headers.get('content-type', 'Unknown')}\n"
                                error_details += f"Response size: {len(test_response.content)} bytes\n"
                                
                                if test_response.status_code == 200:
                                    error_details += "Sayfa erişilebilir ancak içerikde link bulunamadı"
                                else:
                                    error_details += f"Sayfa erişim hatası: HTTP {test_response.status_code}"
                            except Exception as test_e:
                                error_details += f"URL test hatası: {str(test_e)}"
                            
                            crawling_sessions[session_id]['error'] = "Taranacak URL bulunamadı"
                            crawling_sessions[session_id]['error_details'] = error_details
                            
                        crawling_sessions[session_id]['completed'] = True
                
            except Exception as e:
                logger.error(f"Error during crawl and generate process: {str(e)}")
                with sessions_lock:
                    if session_id in crawling_sessions:
                        crawling_sessions[session_id]['error'] = str(e)
                        crawling_sessions[session_id]['completed'] = True

        thread = threading.Thread(target=crawl_and_generate)
        thread.daemon = True
        thread.start()

        return jsonify({"message": "Crawling started", "url": url, "session_id": session_id})
        
    except Exception as e:
        logger.error(f"Error starting crawl: {str(e)}")
        return jsonify({"error": "Failed to start crawling"}), 500

@app.route('/progress/<session_id>')
def progress(session_id):
    with sessions_lock:
        if session_id not in crawling_sessions:
            return jsonify({
                "message": "Session not found",
                "crawled_urls": 0,
                "total_urls": 0,
                "visited_urls": [],
                "completed": True,
                "percentage": 0,
                "error": "Session expired or not found"
            })
        
        session_data = crawling_sessions[session_id]
        crawler = session_data['crawler']
        
        # Update session timestamp to prevent expiry during active crawling
        session_data['last_access'] = time.time()
        
        if session_data['completed']:
            percentage = 100
        else:
            percentage = (len(crawler.visited) / crawler.total_urls * 100) if crawler.total_urls > 0 else 0
        
        return jsonify({
            "crawled_urls": len(crawler.visited),
            "total_urls": crawler.total_urls,
            "visited_urls": list(crawler.visited),
            "completed": session_data['completed'],
            "percentage": round(percentage, 2),
            "error": session_data['error'],
            "error_details": session_data.get('error_details', ''),
            "url": session_data['url']
        })

@app.route('/download')
def download():
    try:
        if os.path.exists('sitemap.xml'):
            return send_file('sitemap.xml', as_attachment=True, download_name='sitemap.xml')
        else:
            return jsonify({"error": "Sitemap not found. Please generate one first."}), 404
    except Exception as e:
        logger.error(f"Error downloading sitemap: {str(e)}")
        return jsonify({"error": "Failed to download sitemap"}), 500

@app.route('/download-csv/<session_id>')
def download_csv(session_id):
    try:
        with sessions_lock:
            if session_id not in crawling_sessions:
                return jsonify({"error": "Session not found. Please generate a sitemap first."}), 404
                
            session_data = crawling_sessions[session_id]
            crawler = session_data['crawler']
        
        if crawler and crawler.url_data:
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(['URL', 'Sayfa Başlığı'])
            
            for url in sorted(crawler.visited):
                title = crawler.url_data.get(url, 'Başlık bulunamadı')
                writer.writerow([url, title])
            
            csv_data = output.getvalue()
            output.close()
            
            # Create a BytesIO object for the response
            csv_bytes = io.BytesIO()
            csv_bytes.write(csv_data.encode('utf-8'))
            csv_bytes.seek(0)
            
            return send_file(
                csv_bytes,
                mimetype='text/csv',
                as_attachment=True,
                download_name='sitemap_urls.csv'
            )
        else:
            return jsonify({"error": "CSV data not found. Please generate a sitemap first."}), 404
    except Exception as e:
        logger.error(f"Error downloading CSV: {str(e)}")
        return jsonify({"error": "Failed to download CSV"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
