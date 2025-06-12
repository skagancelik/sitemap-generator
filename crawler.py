import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlunparse
from urllib import robotparser
import time
import logging
import xml.etree.ElementTree as ET
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

class Crawler:
    def __init__(self, start_url):
        self.start_url = self._normalize_url(start_url)
        self.domain = urlparse(self.start_url).netloc
        self.urls = set()
        self.visited = set()
        self.crawled_urls = 0
        self.total_urls = 0
        self.url_data = {}  # Store URL and title pairs
        self.max_depth = 6
        self.max_urls = 15000
        self.session = self._create_session()
        self.save_interval = 100  # Save progress every 100 URLs
        self.backup_file = f"crawler_backup_{self.domain}.json"
        
        # Initialize robots.txt parser (don't read during init)
        self.robot_parser = None
        self.robots_url = urljoin(self.start_url, '/robots.txt')
    
    def _normalize_url(self, url):
        """Normalize URL by ensuring it has a protocol"""
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        return url.rstrip('/')
    
    def _create_session(self):
        """Create a session with retry strategy"""
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; SitemapGenerator/1.0)'
        })
        return session

    def crawl(self):
        """Main crawling method"""
        self.urls.add(self.start_url)
        self.total_urls = 1

        # Check for existing sitemaps
        sitemap_urls = [
            urljoin(self.start_url, '/sitemap.xml'),
            urljoin(self.start_url, '/sitemap_index.xml'),
            urljoin(self.start_url, '/sitemaps.xml'),
            urljoin(self.start_url, '/sitemap/'),
            urljoin(self.start_url, '/sitemaps/'),
        ]
        
        for sitemap_url in sitemap_urls:
            self.parse_sitemap(sitemap_url)

        # Add sitemap URLs directly to visited and process them
        if len(self.urls) > 1:  # More than just start_url
            logger.info(f"Found {len(self.urls)} URLs from sitemaps")
            # Add sitemap URLs directly to visited (they're already validated)
            for url in self.urls:
                if len(self.visited) < self.max_urls:
                    self.visited.add(url)
                    self.crawled_urls += 1
                    # Extract title for sitemap URLs
                    try:
                        response = self.session.get(url, timeout=10)
                        if response.status_code == 200:
                            title = self._extract_title(response.text)
                            self.url_data[url] = title
                    except:
                        self.url_data[url] = "Başlık alınamadı"
            
            # Continue with manual crawling even if we have sitemap URLs
            logger.info(f"Sitemap phase completed. Starting deep crawling from {len(self.visited)} URLs")
        
        # Use ALL sitemap URLs as starting points for aggressive crawling
        if len(self.visited) > 1:
            # Use all sitemap URLs for comprehensive crawling
            current_level_urls = self.visited.copy()
            logger.info(f"Starting aggressive deep crawl from ALL {len(current_level_urls)} sitemap URLs")
        else:
            current_level_urls = {self.start_url}
        
        depth = 0
        
        while current_level_urls and depth < self.max_depth and len(self.visited) < self.max_urls:
            next_level_urls = set()
            
            for url in current_level_urls:
                if url not in self.visited and self._can_crawl(url):
                    try:
                        logger.info(f"Crawling: {url} (depth: {depth})")
                        response = self.session.get(url, timeout=15, allow_redirects=True)
                        
                        if response.status_code == 200:
                            self.visited.add(url)
                            self.crawled_urls += 1
                            
                            # Extract page title
                            title = self._extract_title(response.text)
                            self.url_data[url] = title
                            
                            # Save backup periodically
                            if self.crawled_urls % self.save_interval == 0:
                                self._save_backup()
                            
                            # Parse links only if we haven't reached max depth
                            if depth < self.max_depth - 1:
                                new_urls = self.parse_links(response.text, url)
                                next_level_urls.update(new_urls)
                                
                        elif response.status_code in [301, 302, 303, 307, 308]:
                            redirect_url = response.headers.get('Location')
                            if redirect_url:
                                full_redirect_url = urljoin(url, redirect_url)
                                if self._is_valid_url(urlparse(full_redirect_url)):
                                    next_level_urls.add(full_redirect_url)
                                    
                        time.sleep(0.3)  # Faster but still respectful delay
                        
                    except requests.RequestException as e:
                        logger.error(f"Error crawling {url}: {str(e)}")
                    except Exception as e:
                        logger.error(f"Unexpected error crawling {url}: {str(e)}")
                        
                    # Update total URLs count
                    self.total_urls = len(self.visited) + len(next_level_urls)
                    
            current_level_urls = next_level_urls
            depth += 1
            
        logger.info(f"Crawling completed. Found {len(self.visited)} URLs at depth {depth}")
        # Save final backup
        self._save_backup()
    
    def _save_backup(self):
        """Save current crawling progress to backup file"""
        try:
            import json
            backup_data = {
                'visited': list(self.visited),
                'url_data': self.url_data,
                'crawled_urls': self.crawled_urls,
                'total_urls': self.total_urls,
                'domain': self.domain,
                'start_url': self.start_url
            }
            with open(self.backup_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2)
            logger.debug(f"Backup saved with {self.crawled_urls} URLs")
        except Exception as e:
            logger.error(f"Error saving backup: {str(e)}")
    
    def _load_backup(self):
        """Load previous crawling progress from backup file"""
        try:
            import json
            import os
            if os.path.exists(self.backup_file):
                with open(self.backup_file, 'r', encoding='utf-8') as f:
                    backup_data = json.load(f)
                
                self.visited = set(backup_data.get('visited', []))
                self.url_data = backup_data.get('url_data', {})
                self.crawled_urls = backup_data.get('crawled_urls', 0)
                self.total_urls = backup_data.get('total_urls', 0)
                logger.info(f"Loaded backup with {self.crawled_urls} URLs")
                return True
        except Exception as e:
            logger.error(f"Error loading backup: {str(e)}")
        return False
    
    def _extract_title(self, html):
        """Extract page title from HTML"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            title_tag = soup.find('title')
            if title_tag:
                title_text = title_tag.get_text().strip()
                if title_text:
                    return title_text
            
            # Try to find h1 as fallback
            h1_tag = soup.find('h1')
            if h1_tag:
                h1_text = h1_tag.get_text().strip()
                if h1_text:
                    return h1_text
                    
            return "Başlık bulunamadı"
        except Exception as e:
            logger.debug(f"Error extracting title: {str(e)}")
            return "Başlık bulunamadı"
    
    def _can_crawl(self, url):
        """Check if URL can be crawled based on robots.txt"""
        if self.robot_parser is None:
            try:
                self.robot_parser = robotparser.RobotFileParser()
                self.robot_parser.set_url(self.robots_url)
                self.robot_parser.read()
            except Exception as e:
                logger.debug(f"Could not read robots.txt: {e}")
                return True
        
        try:
            return self.robot_parser.can_fetch("*", url)
        except:
            return True  # If robots.txt check fails, allow crawling

    def parse_links(self, html, base_url):
        """Parse HTML content and extract valid links"""
        new_urls = set()
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find all links from various sources
            link_selectors = [
                'a[href]',  # Standard links
                'link[rel="canonical"]',  # Canonical links
                'area[href]',  # Image map areas
                'form[action]',  # Form actions
                'iframe[src]',  # Iframe sources
                'meta[property="og:url"]',  # Open Graph URLs
                'link[rel="alternate"]',  # Alternate links
                'link[rel="next"]',  # Pagination next
                'link[rel="prev"]',  # Pagination previous
            ]
            
            for selector in link_selectors:
                elements = soup.select(selector)
                for element in elements:
                    # Get href, action, src, or content attribute
                    href = (element.get('href') or 
                           element.get('action') or 
                           element.get('src') or 
                           element.get('content', ''))
                    
                    if not isinstance(href, str) or not href:
                        continue
                    
                    href = href.strip()
                    if not href or href.startswith('#') or href.startswith('mailto:') or href.startswith('tel:') or href.startswith('javascript:'):
                        continue
                        
                    url = urljoin(base_url, href)
                    parsed_url = urlparse(url)
                    
                    if self._is_valid_url(parsed_url):
                        new_urls.add(url)
                        logger.debug(f"Found valid URL: {url}")
                    else:
                        logger.debug(f"Skipped invalid URL: {url}")
            
            # Enhanced JavaScript and data attribute extraction
            scripts = soup.find_all('script')
            for script in scripts:
                script_text = script.get_text()
                if script_text:
                    import re
                    # Multiple patterns for different URL formats
                    patterns = [
                        r'https?://[^\s"\'\)]+' + re.escape(self.domain) + r'[^\s"\'\)]*',
                        r'["\'](/[^"\']*)["\']',  # Relative URLs
                        r'href["\s]*:["\s]*["\']([^"\']*)["\']',  # JSON href
                        r'url["\s]*:["\s]*["\']([^"\']*)["\']',   # JSON url
                        r'link["\s]*:["\s]*["\']([^"\']*)["\']'   # JSON link
                    ]
                    
                    for pattern in patterns:
                        js_urls = re.findall(pattern, script_text)
                        for js_url in js_urls:
                            try:
                                if js_url.startswith('/'):
                                    js_url = urljoin(base_url, js_url)
                                parsed_url = urlparse(js_url)
                                if self._is_valid_url(parsed_url):
                                    new_urls.add(js_url)
                                    logger.debug(f"Found JS URL: {js_url}")
                            except:
                                continue
            
            # Extract from data attributes
            for element in soup.find_all():
                if hasattr(element, 'attrs') and element.attrs:
                    for attr, value in element.attrs.items():
                        if attr.startswith('data-') and isinstance(value, str):
                            if value.startswith('/') or self.domain in value:
                                try:
                                    if value.startswith('/'):
                                        value = urljoin(base_url, value)
                                    parsed_url = urlparse(value)
                                    if self._is_valid_url(parsed_url):
                                        new_urls.add(value)
                                        logger.debug(f"Found data attribute URL: {value}")
                                except:
                                    continue
                    
        except Exception as e:
            logger.error(f"Error parsing links from {base_url}: {str(e)}")
            
        return new_urls

    def _is_valid_url(self, parsed_url):
        """Check if URL is valid for crawling"""
        # Must be same domain
        if parsed_url.netloc != self.domain:
            return False
            
        # Must be HTTP/HTTPS
        if parsed_url.scheme not in ('http', 'https'):
            return False
            
        # Skip certain file types only (reduced restrictions)
        path = parsed_url.path.lower()
        skip_extensions = {'.pdf', '.jpg', '.jpeg', '.png', '.gif', '.css', '.js', '.ico', '.svg', '.woff', '.woff2', '.ttf', '.eot', '.zip', '.mp4', '.avi', '.mov'}
        
        if any(path.endswith(ext) for ext in skip_extensions):
            return False
            
        # Skip duplicate URLs (already visited)
        if parsed_url.geturl() in self.visited:
            return False
            
        # Allow ALL query parameters (remove restrictions for more URLs)
        # This will capture pagination, category filters, search results, etc.
        return True

    def parse_sitemap(self, sitemap_url):
        """Parse existing sitemap.xml if available"""
        try:
            response = self.session.get(sitemap_url, timeout=10)
            if response.status_code == 200:
                logger.info(f"Found existing sitemap at {sitemap_url}")
                root = ET.fromstring(response.content)
                
                # Handle regular sitemap
                for url_elem in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc'):
                    if url_elem.text:
                        url = url_elem.text.strip()
                        parsed_url = urlparse(url)
                        if self._is_valid_url(parsed_url):
                            self.urls.add(url)
                            
                # Handle sitemap index
                for sitemap_elem in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}sitemap'):
                    loc_elem = sitemap_elem.find('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                    if loc_elem is not None and loc_elem.text:
                        # Recursively parse sub-sitemaps
                        self.parse_sitemap(loc_elem.text.strip())
                        
            else:
                logger.debug(f"No sitemap found at {sitemap_url}")
                
        except requests.RequestException as e:
            logger.debug(f"Error fetching sitemap {sitemap_url}: {str(e)}")
        except ET.ParseError as e:
            logger.error(f"Error parsing sitemap {sitemap_url}: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error parsing sitemap {sitemap_url}: {str(e)}")
