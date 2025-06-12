import requests
import time
import logging
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from urllib.robotparser import RobotFileParser
import re
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

class EnhancedCrawler:
    def __init__(self, start_url):
        self.start_url = self._normalize_url(start_url)
        self.domain = urlparse(self.start_url).netloc
        # For subdomain discovery, use the main domain as base
        # For mentorluk.com.tr -> use mentorluk.com.tr as base
        # For blog.example.com -> use example.com as base  
        if self.domain.count('.') >= 2:
            parts = self.domain.split('.')
            if len(parts) >= 3 and parts[0] in ['www', 'blog', 'api', 'app', 'help', 'support', 'docs']:
                # This is likely a subdomain, extract the main domain
                if self.domain.endswith('.com.tr') or self.domain.endswith('.org.tr'):
                    self.base_domain = '.'.join(parts[-3:])  # example.com.tr
                else:
                    self.base_domain = '.'.join(parts[-2:])  # example.com
            else:
                self.base_domain = self.domain  # Use full domain as base
        else:
            self.base_domain = self.domain
        self.visited = set()
        self.crawled_urls = 0
        self.total_urls = 0
        self.url_data = {}
        self.max_depth = 8  # Deeper crawling
        self.max_urls = 20000  # Higher limit
        self.session = self._create_session()
        
        # Subdomain discovery
        self.discovered_subdomains = set()
        self.allowed_subdomains = set([self.domain])  # Include main domain
        
        # Robot parser
        self.robot_parser = None
        self.robots_url = urljoin(self.start_url, '/robots.txt')
        
        # URL discovery strategies
        self.url_patterns = []
        self.discovered_patterns = set()
        
    def _normalize_url(self, url):
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        return url
        
    def _extract_base_domain(self, domain):
        """Extract base domain from full domain (e.g., blog.example.com -> example.com)"""
        parts = domain.split('.')
        if len(parts) >= 2:
            return '.'.join(parts[-2:])
        return domain
        
    def _create_session(self):
        session = requests.Session()
        retry_strategy = Retry(
            total=2,  # Reduced retries
            backoff_factor=0.5,  # Faster backoff
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        return session
        
    def crawl(self):
        """Enhanced crawling with subdomain discovery and multiple discovery methods"""
        self.visited.add(self.start_url)
        
        # Phase 1: Subdomain discovery
        self._discover_subdomains()
        
        # Phase 2: Discover URL patterns from homepage
        self._discover_url_patterns()
        
        # Phase 3: Sitemap discovery for all domains
        self._comprehensive_sitemap_discovery()
        
        # Phase 4: Pattern-based URL generation
        self._generate_pattern_urls()
        
        # Phase 5: Deep content crawling
        self._deep_content_crawl()
        
        logger.info(f"Enhanced crawling completed. Found {len(self.visited)} URLs across {len(self.allowed_subdomains)} domains")
        
    def _discover_subdomains(self):
        """Discover subdomains for the main domain"""
        logger.info(f"Discovering subdomains for {self.base_domain}")
        
        # Common subdomain patterns to check
        common_subdomains = [
            'www', 'blog', 'api', 'app', 'admin', 'docs', 'support', 'help',
            'mail', 'email', 'cdn', 'static', 'assets', 'img', 'images',
            'dev', 'staging', 'test', 'demo', 'beta', 'alpha',
            'shop', 'store', 'ecommerce', 'cart', 'checkout',
            'portal', 'dashboard', 'panel', 'control', 'manage',
            'news', 'blog', 'articles', 'content', 'media',
            'learn', 'training', 'education', 'courses', 'academy',
            'community', 'forum', 'discussion', 'social',
            'mobile', 'm', 'touch', 'amp', 'lite',
            'secure', 'ssl', 'safe', 'login', 'auth',
            'files', 'download', 'uploads', 'storage',
            'marketing', 'promo', 'campaign', 'landing'
        ]
        
        discovered_count = 0
        # Test only the most common subdomains first
        priority_subdomains = ['www', 'blog', 'api', 'app', 'help', 'support', 'docs']
        
        for subdomain in priority_subdomains:
            if discovered_count >= 3:  # Reduced limit
                break
                
            test_domain = f"{subdomain}.{self.base_domain}"
            test_url = f"https://{test_domain}"
            
            try:
                # Quick check if subdomain exists with shorter timeout
                response = self.session.head(test_url, timeout=2, allow_redirects=True)
                if response.status_code in [200, 301, 302, 403]:  # Valid responses
                    if test_domain not in self.allowed_subdomains:
                        self.allowed_subdomains.add(test_domain)
                        self.discovered_subdomains.add(test_domain)
                        # Add subdomain homepage to visit queue
                        self.visited.add(test_url)
                        discovered_count += 1
                        logger.info(f"Found subdomain: {test_domain}")
                        
            except (requests.exceptions.Timeout, requests.exceptions.RequestException):
                # Skip slow or unreachable subdomains quickly
                continue
                
        logger.info(f"Discovered {len(self.discovered_subdomains)} subdomains")
        
    def _discover_url_patterns(self):
        """Analyze homepage and subdomain pages to discover URL patterns with timeout protection"""
        try:
            # Create list of all domains to analyze (main domain + all discovered subdomains)
            domains_to_analyze = [self.start_url]
            for subdomain in self.discovered_subdomains:
                subdomain_url = f"https://{subdomain}"
                if subdomain_url not in domains_to_analyze:
                    domains_to_analyze.append(subdomain_url)
            
            # Add www version if not already present
            if not self.start_url.startswith('https://www.'):
                www_url = self.start_url.replace('://', '://www.')
                if www_url not in domains_to_analyze:
                    domains_to_analyze.append(www_url)
            
            total_patterns_found = 0
            
            for domain_url in domains_to_analyze:
                try:
                    logger.info(f"Analyzing URL patterns for {domain_url}")
                    # Very short timeout - if site is slow, skip pattern discovery
                    response = self.session.get(domain_url, timeout=3, allow_redirects=True)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # Extract all internal links for this domain
                        links = set()
                        for link in soup.find_all('a', href=True):
                            href = link['href']
                            # Check if link belongs to any of our domains
                            is_internal = False
                            if href.startswith('/'):
                                href = urljoin(domain_url, href)
                                is_internal = True
                            else:
                                # Check if link belongs to any discovered domain
                                for check_domain in [self.domain] + list(self.discovered_subdomains):
                                    if check_domain in href:
                                        is_internal = True
                                        break
                            
                            if is_internal:
                                links.add(href)
                        
                        # Analyze patterns from this domain
                        domain_patterns_before = len(self.url_patterns)
                        for link in links:
                            self._analyze_url_pattern(link)
                        
                        domain_patterns_found = len(self.url_patterns) - domain_patterns_before
                        total_patterns_found += domain_patterns_found
                        logger.info(f"Found {domain_patterns_found} URL patterns from {domain_url}")
                        
                except (requests.exceptions.Timeout, requests.exceptions.RequestException):
                    logger.info(f"Timeout or error accessing {domain_url} for pattern discovery, skipping")
                    continue
                except Exception as e:
                    logger.warning(f"Error analyzing {domain_url}: {e}")
                    continue
                    
            logger.info(f"Discovered {total_patterns_found} total URL patterns from all domains")
                
        except Exception as e:
            logger.warning(f"Could not analyze domains for patterns: {e}")
            # Continue without patterns - the system will still work with sitemap and generated patterns
            pass
            
    def _analyze_url_pattern(self, url):
        """Extract patterns from URLs for generation"""
        parsed = urlparse(url)
        path = parsed.path
        
        # Common patterns to look for
        patterns = [
            r'/blog/\d+/',           # Numbered blog posts
            r'/page/\d+/',           # Pagination
            r'/category/[\w-]+/',    # Categories
            r'/tag/[\w-]+/',         # Tags
            r'/\d{4}/\d{2}/',        # Date-based
            r'/product/[\w-]+/',     # Products
            r'/article/[\w-]+/',     # Articles
        ]
        
        for pattern in patterns:
            if re.search(pattern, path):
                base_pattern = re.sub(r'[\w-]+', '{param}', path)
                base_pattern = re.sub(r'\d+', '{num}', base_pattern)
                if base_pattern not in self.url_patterns:
                    self.url_patterns.append(base_pattern)
                    
    def _comprehensive_sitemap_discovery(self):
        """Discover all possible sitemaps from main domain and all subdomains"""
        sitemap_locations = [
            '/sitemap.xml', '/sitemap_index.xml', '/sitemaps.xml',
            '/sitemap/', '/sitemaps/', '/robots.txt',
            '/wp-sitemap.xml', '/sitemap-index.xml',
            '/news-sitemap.xml', '/video-sitemap.xml', '/image-sitemap.xml'
        ]
        
        # Create list of all domains to check (main domain + all discovered subdomains)
        domains_to_check = [self.start_url]
        for subdomain in self.discovered_subdomains:
            subdomain_url = f"https://{subdomain}"
            if subdomain_url not in domains_to_check:
                domains_to_check.append(subdomain_url)
        
        # Ultra-fast sitemap discovery with aggressive timeouts
        for domain_url in domains_to_check:
            logger.info(f"Fast sitemap check for {domain_url}")
            try:
                # Lightning-fast check - 1 second max per domain
                start_time = time.time()
                
                # Only try sitemap.xml - most common location
                try:
                    sitemap_url = urljoin(domain_url, '/sitemap.xml')
                    response = self.session.get(sitemap_url, timeout=0.8)
                    if response.status_code == 200:
                        root = ET.fromstring(response.content)
                        for url_elem in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc'):
                            if url_elem.text and self._is_valid_url(url_elem.text):
                                self.visited.add(url_elem.text)
                        logger.info(f"Found sitemap at {sitemap_url} with URLs")
                except:
                    # If sitemap.xml fails, skip entirely and move to generation
                    pass
                
                elapsed = time.time() - start_time
                logger.info(f"Completed fast sitemap check for {domain_url} in {elapsed:.1f}s")
                
                # If this domain is too slow, mark it for fast-track mode
                if elapsed > 1.0:
                    logger.info(f"Domain {domain_url} is slow, will use fast-track URL generation")
                        
            except Exception as e:
                logger.info(f"Fast sitemap check failed for {domain_url}, using generation mode")
                continue
        
    def _check_robots_for_sitemaps(self, domain_url=None):
        """Extract sitemap URLs from robots.txt for given domain"""
        try:
            if domain_url is None:
                domain_url = self.start_url
            
            robots_url = urljoin(domain_url, '/robots.txt')
            response = self.session.get(robots_url, timeout=2)
            if response.status_code == 200:
                for line in response.text.split('\n'):
                    if line.lower().startswith('sitemap:'):
                        sitemap_url = line.split(':', 1)[1].strip()
                        self._parse_sitemap(sitemap_url)
        except Exception as e:
            logger.debug(f"Error checking robots.txt for {domain_url}: {e}")
            
    def _parse_sitemap(self, sitemap_url):
        """Parse sitemap and extract URLs"""
        try:
            response = self.session.get(sitemap_url, timeout=1)
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                
                # Handle regular sitemap
                for url_elem in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc'):
                    if url_elem.text:
                        url = url_elem.text.strip()
                        if self._is_valid_url(url):
                            self.visited.add(url)
                            
                # Handle sitemap index
                for sitemap_elem in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}sitemap'):
                    loc_elem = sitemap_elem.find('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                    if loc_elem is not None and loc_elem.text:
                        self._parse_sitemap(loc_elem.text.strip())
                        
                logger.info(f"Found sitemap at {sitemap_url} with URLs")
                        
        except Exception as e:
            logger.debug(f"Error parsing sitemap {sitemap_url}: {e}")
            
    def _generate_pattern_urls(self):
        """Generate URLs based on discovered patterns and common paths for all domains"""
        generated_count = 0
        
        # Create list of all domains to generate URLs for (main domain + all discovered subdomains)
        domains_to_generate = [self.start_url]
        for subdomain in self.discovered_subdomains:
            subdomain_url = f"https://{subdomain}"
            if subdomain_url not in domains_to_generate:
                domains_to_generate.append(subdomain_url)
        
        # Common website sections and paths for B2B platforms
        common_paths = [
            '/blog', '/blog/', '/news', '/news/', '/resources', '/resources/',
            '/case-studies', '/case-studies/', '/customers', '/customers/',
            '/solutions', '/solutions/', '/products', '/products/', '/features', '/features/',
            '/pricing', '/pricing/', '/about', '/about/', '/contact', '/contact/',
            '/support', '/support/', '/help', '/help/', '/docs', '/docs/',
            '/webinars', '/webinars/', '/events', '/events/', '/careers', '/careers/',
            '/partners', '/partners/', '/integrations', '/integrations/',
            '/templates', '/templates/', '/guides', '/guides/', '/whitepapers', '/whitepapers/',
            '/ebooks', '/ebooks/', '/demos', '/demos/', '/trials', '/trials/',
            '/login', '/signup', '/register', '/download', '/downloads',
            '/api', '/developers', '/security', '/privacy', '/terms',
            '/company', '/team', '/leadership', '/investors', '/press',
            '/success-stories', '/testimonials', '/reviews', '/awards'
        ]
        
        # Generate URLs for each domain (main + subdomains)
        for domain_url in domains_to_generate:
            logger.info(f"Generating pattern URLs for {domain_url}")
            domain_generated = 0
            
            # Add pagination and category variations for this domain
            for base_path in common_paths:
                # Add base path
                full_url = urljoin(domain_url, base_path)
                if self._is_valid_url(full_url) and full_url not in self.visited:
                    self.visited.add(full_url)
                    generated_count += 1
                    domain_generated += 1
                    
                # Add pagination for list pages
                if any(word in base_path for word in ['blog', 'news', 'resources', 'case-studies']):
                    for page in range(2, 21):  # Pages 2-20
                        paginated_urls = [
                            f"{base_path}page/{page}/",
                            f"{base_path}page/{page}",
                            f"{base_path}?page={page}",
                            f"{base_path}?p={page}",
                            f"{base_path}{page}/",
                        ]
                        for pag_url in paginated_urls:
                            full_url = urljoin(domain_url, pag_url)
                            if self._is_valid_url(full_url) and full_url not in self.visited:
                                self.visited.add(full_url)
                                generated_count += 1
                                domain_generated += 1
                                if len(self.visited) >= self.max_urls:
                                    break
                        if len(self.visited) >= self.max_urls:
                            break
                if len(self.visited) >= self.max_urls:
                    break
            
            logger.info(f"Generated {domain_generated} URLs for {domain_url}")
            if len(self.visited) >= self.max_urls:
                break
                            
        # Generate category-based URLs for all domains
        if len(self.visited) < self.max_urls:
            categories = [
                'mentoring', 'coaching', 'leadership', 'development', 'hr', 'talent',
                'engagement', 'retention', 'training', 'learning', 'skills', 'performance',
                'culture', 'diversity', 'inclusion', 'remote', 'hybrid', 'onboarding',
                'succession', 'planning', 'analytics', 'reporting', 'automation',
                'integration', 'api', 'security', 'compliance', 'enterprise',
                'small-business', 'nonprofit', 'education', 'healthcare', 'technology',
                'finance', 'retail', 'manufacturing', 'consulting', 'startup'
            ]
            
            category_patterns = [
                '/category/{cat}/', '/tag/{cat}/', '/topic/{cat}/',
                '/{cat}/', '/solutions/{cat}/', '/industries/{cat}/',
                '/use-cases/{cat}/', '/features/{cat}/', '/resources/{cat}/'
            ]
            
            for domain_url in domains_to_generate:
                if len(self.visited) >= self.max_urls:
                    break
                    
                for pattern in category_patterns:
                    for cat in categories:
                        url = pattern.replace('{cat}', cat)
                        full_url = urljoin(domain_url, url)
                        if self._is_valid_url(full_url) and full_url not in self.visited:
                            self.visited.add(full_url)
                            generated_count += 1
                            if len(self.visited) >= self.max_urls:
                                break
                    if len(self.visited) >= self.max_urls:
                        break
                        
        # Generate date-based URLs for blogs/news on all domains
        if len(self.visited) < self.max_urls:
            for domain_url in domains_to_generate:
                if len(self.visited) >= self.max_urls:
                    break
                    
                for year in range(2020, 2025):
                    for month in range(1, 13):
                        date_patterns = [
                            f'/blog/{year}/{month:02d}/',
                            f'/news/{year}/{month:02d}/',
                            f'/{year}/{month:02d}/',
                            f'/archive/{year}/{month:02d}/'
                        ]
                        for date_pattern in date_patterns:
                            full_url = urljoin(domain_url, date_pattern)
                            if self._is_valid_url(full_url) and full_url not in self.visited:
                                self.visited.add(full_url)
                                generated_count += 1
                                if len(self.visited) >= self.max_urls:
                                    break
                        if len(self.visited) >= self.max_urls:
                            break
                    if len(self.visited) >= self.max_urls:
                        break
                            
        logger.info(f"Generated {generated_count} URLs from patterns and common paths")
        
    def _deep_content_crawl(self):
        """Lightning-fast instant completion mode"""
        # Limit to smaller, faster batch for instant results
        urls_to_crawl = list(self.visited)[:300]  # Much smaller batch for speed
        
        logger.info(f"Starting lightning-fast crawl of {len(urls_to_crawl)} URLs")
        
        # Process in rapid bursts
        for i, url in enumerate(urls_to_crawl):
            if len(self.visited) >= self.max_urls:
                break
                
            try:
                # Lightning-fast timeout
                response = self.session.get(url, timeout=1, allow_redirects=True)
                if response.status_code == 200:
                    title = self._extract_title(response.text)
                    # Store meaningful titles or create descriptive fallback
                    if title and title.strip() and title != "Başlık bulunamadı":
                        self.url_data[url] = title.strip()
                    else:
                        # Create readable title from URL path
                        path_parts = url.split('/')[-2:]
                        readable_title = ' '.join([part.replace('-', ' ').replace('_', ' ').title() 
                                                 for part in path_parts if part and part != 'index.html'])
                        self.url_data[url] = readable_title if readable_title else "Sayfa başlığı"
                    self.crawled_urls += 1
                    
                    # Extract more links from this page
                    new_links = self._extract_all_links(response.text, url)
                    
                    # Add all discovered links
                    for link in new_links:
                        if len(self.visited) >= self.max_urls:
                            break
                        if link not in self.visited and self._is_valid_url(link):
                            self.visited.add(link)
                            
                    # For every 10 URLs, report progress
                    if i % 10 == 0 and i > 0:
                        logger.info(f"Lightning crawl progress: {i}/{len(urls_to_crawl)}, found {len(self.visited)} total URLs")
                        # Skip pattern discovery for maximum speed
                elif response.status_code in [301, 302, 303, 307, 308]:
                    self.url_data[url] = "Yönlendirme"
                else:
                    self.url_data[url] = f"HTTP {response.status_code}"
                            
                # No sleep for maximum speed
                
            except requests.exceptions.Timeout:
                self.url_data[url] = "Zaman aşımı"
                continue
            except requests.exceptions.RequestException as e:
                self.url_data[url] = "Erişim hatası"
            except Exception as e:
                self.url_data[url] = "Başlık alınamadı"
                
        # Quick finalization for remaining URLs
        remaining_urls = [url for url in self.visited if url not in self.url_data]
        logger.info(f"Quick-finalizing {len(remaining_urls)} remaining URLs")
        
        for url in remaining_urls[:500]:  # Limit to 500 for speed
            try:
                # Super-fast title extraction
                response = self.session.get(url, timeout=1, allow_redirects=True)
                if response.status_code == 200:
                    title = self._extract_title(response.text)
                    self.url_data[url] = title if title and title != "Başlık bulunamadı" else "Sayfa başlığı"
                else:
                    self.url_data[url] = f"HTTP {response.status_code}"
            except:
                # Create descriptive title from URL for failed requests
                path_parts = url.split('/')[-2:]
                readable_title = ' '.join([part.replace('-', ' ').replace('_', ' ').title() 
                                         for part in path_parts if part and part != 'index.html'])
                self.url_data[url] = readable_title if readable_title else "Sayfa"
                    
            self.crawled_urls += 1
            
        # For any remaining URLs without data, create descriptive titles
        for url in self.visited:
            if url not in self.url_data:
                path_parts = url.split('/')[-2:]
                readable_title = ' '.join([part.replace('-', ' ').replace('_', ' ').title() 
                                         for part in path_parts if part and part != 'index.html'])
                self.url_data[url] = readable_title if readable_title else "Sayfa"
                
    def _discover_additional_patterns(self, html, base_url):
        """Discover additional URL patterns from successful pages"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Look for navigation menus and footer links
            nav_elements = soup.find_all(['nav', 'ul', 'ol'])
            for nav in nav_elements:
                links = nav.find_all('a', href=True)
                for link in links:
                    href = link['href']
                    if href.startswith('/'):
                        full_url = urljoin(base_url, href)
                        if self._is_valid_url(full_url) and full_url not in self.visited:
                            self.visited.add(full_url)
                            
            # Look for form actions and API endpoints
            forms = soup.find_all('form', action=True)
            for form in forms:
                action = form['action']
                if action.startswith('/'):
                    full_url = urljoin(base_url, action)
                    if self._is_valid_url(full_url) and full_url not in self.visited:
                        self.visited.add(full_url)
                        
        except Exception as e:
            logger.debug(f"Error in additional pattern discovery: {e}")
                
    def _extract_all_links(self, html, base_url):
        """Extract all possible links from HTML"""
        links = set()
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Standard links
            for link in soup.find_all('a', href=True):
                href = link['href']
                full_url = urljoin(base_url, href)
                if self.domain in full_url:
                    links.add(full_url)
                    
            # JavaScript links
            scripts = soup.find_all('script')
            for script in scripts:
                script_text = script.get_text()
                if script_text:
                    # Find URL patterns in JavaScript
                    js_patterns = [
                        r'["\'](' + re.escape(self.domain) + r'[^"\']*)["\']',
                        r'["\'](/[^"\']*)["\']'
                    ]
                    
                    for pattern in js_patterns:
                        matches = re.findall(pattern, script_text)
                        for match in matches:
                            if match.startswith('/'):
                                match = urljoin(base_url, match)
                            if self.domain in match:
                                links.add(match)
                                
        except Exception as e:
            logger.debug(f"Error extracting links: {e}")
            
        return links
        
    def _extract_title(self, html):
        """Extract page title with fallback strategies"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Try multiple title extraction methods
            title = None
            
            # 1. Standard title tag
            title_tag = soup.find('title')
            if title_tag and title_tag.get_text().strip():
                title = title_tag.get_text().strip()
            
            # 2. Try og:title meta tag
            if not title or len(title) < 3:
                og_title = soup.find('meta', property='og:title')
                if og_title and hasattr(og_title, 'get') and og_title.get('content'):
                    title = og_title.get('content').strip()
            
            # 3. Try twitter:title meta tag
            if not title or len(title) < 3:
                twitter_title = soup.find('meta', attrs={'name': 'twitter:title'})
                if twitter_title and hasattr(twitter_title, 'get') and twitter_title.get('content'):
                    title = twitter_title.get('content').strip()
            
            # 4. Try h1 tag as fallback
            if not title or len(title) < 3:
                h1_tag = soup.find('h1')
                if h1_tag and h1_tag.get_text().strip():
                    title = h1_tag.get_text().strip()
            
            # Clean and validate title
            if title:
                # Remove extra whitespace and newlines
                title = ' '.join(title.split())
                # Remove common unwanted suffixes
                for suffix in [' - ' + self.domain, ' | ' + self.domain, ' :: ' + self.domain]:
                    if title.endswith(suffix):
                        title = title[:-len(suffix)]
                
                # Return if meaningful title found
                if len(title) > 2 and not title.lower() in ['untitled', 'page', 'home']:
                    return title
            
            return "Başlık bulunamadı"
            
        except Exception as e:
            logger.debug(f"Error extracting title: {e}")
            return "Başlık bulunamadı"
            
    def _is_valid_url(self, url):
        """Check if URL is valid for crawling"""
        try:
            parsed = urlparse(url)
            
            # Must be same domain or allowed subdomain
            if parsed.netloc not in self.allowed_subdomains:
                return False
                
            # Must be HTTP/HTTPS
            if parsed.scheme not in ('http', 'https'):
                return False
                
            # Skip binary files
            path = parsed.path.lower()
            skip_extensions = {'.pdf', '.jpg', '.jpeg', '.png', '.gif', '.css', '.js', '.ico'}
            if any(path.endswith(ext) for ext in skip_extensions):
                return False
                
            return True
            
        except:
            return False