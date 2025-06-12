# Production optimizations for memory and performance
import gc
import threading
import time
from functools import wraps
from flask import request, jsonify

# Memory cleanup system
def setup_memory_cleanup():
    """Setup automatic memory cleanup every 5 minutes"""
    def cleanup_memory():
        gc.collect()
        threading.Timer(300, cleanup_memory).start()
    cleanup_memory()

# Rate limiting system
request_times = {}
RATE_LIMIT_WINDOW = 30  # seconds
MAX_REQUESTS_PER_WINDOW = 3

def rate_limit(f):
    """Rate limiting decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        ip = request.remote_addr
        now = time.time()
        
        # Clean old entries
        request_times[ip] = [req_time for req_time in request_times.get(ip, []) 
                           if now - req_time < RATE_LIMIT_WINDOW]
        
        # Check rate limit
        if len(request_times.get(ip, [])) >= MAX_REQUESTS_PER_WINDOW:
            return jsonify({
                "error": "Rate limit exceeded",
                "message": f"Maximum {MAX_REQUESTS_PER_WINDOW} requests per {RATE_LIMIT_WINDOW} seconds"
            }), 429
        
        # Add current request
        if ip not in request_times:
            request_times[ip] = []
        request_times[ip].append(now)
        
        return f(*args, **kwargs)
    return decorated_function

# Production configuration
PRODUCTION_CONFIG = {
    "TIMEOUT_SETTINGS": {
        "sitemap_check": 1,
        "pattern_analysis": 2,
        "deep_crawl": 1,
        "robots_txt": 1
    },
    "CRAWLING_LIMITS": {
        "max_urls": 10000,
        "max_deep_crawl": 500,
        "max_subdomains": 10
    },
    "MEMORY_SETTINGS": {
        "cleanup_interval": 300,  # 5 minutes
        "session_lifetime": 1200,  # 20 minutes
        "max_concurrent_sessions": 5
    }
}