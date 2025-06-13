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
        
        # Phase 3: Comprehensive sitemap discovery (prioritized for blog content)
        self._comprehensive_sitemap_discovery()
        
        # Phase 4: Blog and content-specific discovery
        self._discover_blog_content()
        
        # Phase 5: Pattern-based URL generation
        self._generate_pattern_urls()
        
        # Phase 6: Deep content crawling with recursive link following
        self._deep_content_crawl()
        
        logger.info(f"Enhanced crawling completed. Found {len(self.visited)} URLs across {len(self.allowed_subdomains)} domains")
        
    def _discover_subdomains(self):
        """Discover subdomains dynamically from DNS records and page content"""
        logger.info(f"Discovering subdomains for {self.base_domain}")
        
        # Phase 1: Analyze homepage for subdomain references
        discovered_subdomains_from_content = self._extract_subdomains_from_content()
        
        # Phase 2: Test common patterns + discovered patterns
        all_patterns = set()
        
        # Basic common patterns (minimal set)
        basic_patterns = ['www', 'blog', 'api', 'app', 'help', 'support']
        all_patterns.update(basic_patterns)
        
        # Add patterns discovered from content
        all_patterns.update(discovered_subdomains_from_content)
        
        # Phase 3: Test discovered patterns
        discovered_count = 0
        for subdomain in all_patterns:
            if discovered_count >= 10:  # Increased limit for better coverage
                break
                
            test_domain = f"{subdomain}.{self.base_domain}"
            test_url = f"https://{test_domain}"
            
            try:
                response = self.session.head(test_url, timeout=2, allow_redirects=True)
                if response.status_code in [200, 301, 302, 403]:
                    if test_domain not in self.allowed_subdomains:
                        self.allowed_subdomains.add(test_domain)
                        self.discovered_subdomains.add(test_domain)
                        self.visited.add(test_url)
                        discovered_count += 1
                        logger.info(f"Found subdomain: {test_domain}")
                        
            except (requests.exceptions.Timeout, requests.exceptions.RequestException):
                continue
                
        logger.info(f"Discovered {len(self.discovered_subdomains)} subdomains")
    
    def _extract_subdomains_from_content(self):
        """Extract potential subdomains from website content"""
        discovered_patterns = set()
        
        try:
            # Analyze main domain homepage
            response = self.session.get(self.start_url, timeout=3)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract from all links
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    if isinstance(href, str) and self.base_domain in href:
                        parsed = urlparse(href)
                        if parsed.netloc and parsed.netloc != self.domain:
                            # Extract subdomain part
                            if parsed.netloc.endswith(self.base_domain):
                                subdomain = parsed.netloc.replace('.' + self.base_domain, '')
                                if subdomain and '.' not in subdomain:  # Simple subdomain
                                    discovered_patterns.add(subdomain)
                
                # Extract from JavaScript and data attributes
                scripts = soup.find_all('script')
                for script in scripts:
                    script_text = script.get_text()
                    if script_text:
                        import re
                        # Find subdomain patterns in JS
                        pattern = rf'([a-zA-Z0-9\-]+)\.{re.escape(self.base_domain)}'
                        matches = re.findall(pattern, script_text)
                        for match in matches:
                            if len(match) > 1 and len(match) < 20:  # Reasonable subdomain length
                                discovered_patterns.add(match)
                
                logger.info(f"Discovered {len(discovered_patterns)} subdomain patterns from content")
                                
        except Exception as e:
            logger.info(f"Could not analyze content for subdomains: {e}")
            
        return discovered_patterns
        
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
    
    def _discover_blog_content(self):
        """Aggressively discover blog posts and articles"""
        logger.info("Starting aggressive blog content discovery")
        
        blog_discovered = 0
        
        # Blog-specific paths to check on all domains
        blog_paths = [
            '/blog/', '/blog', '/articles/', '/articles', '/news/', '/news',
            '/posts/', '/posts', '/content/', '/content', '/insights/', '/insights',
            '/resources/', '/resources', '/stories/', '/stories', '/updates/', '/updates',
            '/press/', '/press', '/media/', '/media', '/events/', '/events',
            '/announcements/', '/announcements', '/tutorials/', '/tutorials',
            '/guides/', '/guides', '/tips/', '/tips', '/learn/', '/learn'
        ]
        
        for domain_url in [f"https://{domain}" for domain in self.allowed_subdomains]:
            if blog_discovered >= 1000:  # Limit blog discovery
                break
                
            for blog_path in blog_paths:
                if blog_discovered >= 1000:
                    break
                    
                blog_url = urljoin(domain_url, blog_path)
                if blog_url in self.visited:
                    continue
                    
                try:
                    response = self.session.get(blog_url, timeout=3, allow_redirects=True)
                    if response.status_code == 200:
                        self.visited.add(blog_url)
                        blog_discovered += 1
                        
                        # Extract blog post links from this page
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # Look for blog post patterns
                        blog_selectors = [
                            'a[href*="/blog/"]', 'a[href*="/article/"]', 'a[href*="/post/"]',
                            'a[href*="/news/"]', 'a[href*="/story/"]', 'a[href*="/insight/"]',
                            '.blog-post a', '.article a', '.post a', '.news-item a',
                            '.content-item a', '.story a', '.resource a'
                        ]
                        
                        for selector in blog_selectors:
                            links = soup.select(selector)
                            for link in links[:50]:  # Limit per selector
                                href = link.get('href')
                                if href:
                                    full_url = urljoin(blog_url, href)
                                    if (self._is_valid_url(full_url) and 
                                        full_url not in self.visited and 
                                        len(self.visited) < self.max_urls):
                                        self.visited.add(full_url)
                                        blog_discovered += 1
                        
                        # Check for pagination on blog pages
                        pagination_selectors = [
                            'a[href*="page"]', 'a[href*="Page"]', '.pagination a',
                            '.pager a', '.next a', '.prev a', 'a[rel="next"]'
                        ]
                        
                        for selector in pagination_selectors:
                            pages = soup.select(selector)
                            for page_link in pages[:10]:  # Limit pagination
                                href = page_link.get('href')
                                if href:
                                    page_url = urljoin(blog_url, href)
                                    if (self._is_valid_url(page_url) and 
                                        page_url not in self.visited and 
                                        len(self.visited) < self.max_urls):
                                        self.visited.add(page_url)
                                        blog_discovered += 1
                        
                except (requests.exceptions.Timeout, requests.exceptions.RequestException):
                    continue
                except Exception as e:
                    continue
        
        logger.info(f"Blog discovery completed. Found {blog_discovered} blog-related URLs")
    
    def _comprehensive_link_extraction(self, html, base_url):
        """Extract ALL internal links from a page for comprehensive crawling"""
        links = set()
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract all anchor tags with href
            for link_tag in soup.find_all('a', href=True):
                href = link_tag['href']
                if href:
                    # Convert relative URLs to absolute
                    if href.startswith('/'):
                        full_url = urljoin(base_url, href)
                    elif href.startswith('http'):
                        full_url = href
                    elif not href.startswith(('mailto:', 'tel:', '#', 'javascript:')):
                        full_url = urljoin(base_url, href)
                    else:
                        continue
                    
                    # Only include URLs from same domain or allowed subdomains
                    parsed_url = urlparse(full_url)
                    if parsed_url.netloc in self.allowed_subdomains:
                        # Clean URL (remove fragments, normalize)
                        clean_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
                        if parsed_url.query:
                            clean_url += f"?{parsed_url.query}"
                        links.add(clean_url)
            
            # Extract links from JavaScript onclick events and data attributes
            for element in soup.find_all(attrs={'onclick': True}):
                onclick = element.get('onclick', '')
                if 'location' in onclick or 'href' in onclick:
                    # Extract URLs from JavaScript
                    import re
                    url_matches = re.findall(r'["\']([^"\']*)["\']', onclick)
                    for match in url_matches:
                        if match.startswith('/') or self.domain in match:
                            try:
                                full_url = urljoin(base_url, match)
                                parsed_url = urlparse(full_url)
                                if parsed_url.netloc in self.allowed_subdomains:
                                    links.add(full_url)
                            except:
                                continue
            
            # Extract from data-href and similar attributes
            for element in soup.find_all(attrs={'data-href': True}):
                data_href = element.get('data-href')
                if data_href:
                    try:
                        full_url = urljoin(base_url, data_href)
                        parsed_url = urlparse(full_url)
                        if parsed_url.netloc in self.allowed_subdomains:
                            links.add(full_url)
                    except:
                        continue
            
            # Extract from form actions
            for form in soup.find_all('form', action=True):
                action = form['action']
                if action and not action.startswith(('mailto:', '#')):
                    try:
                        full_url = urljoin(base_url, action)
                        parsed_url = urlparse(full_url)
                        if parsed_url.netloc in self.allowed_subdomains:
                            links.add(full_url)
                    except:
                        continue
                        
        except Exception as e:
            logger.warning(f"Error extracting links from {base_url}: {e}")
        
        return list(links)
            
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
                
                # Try multiple sitemap locations for comprehensive blog content discovery
                sitemap_paths = ['/sitemap.xml', '/sitemap_index.xml', '/wp-sitemap.xml', '/post-sitemap.xml']
                
                for sitemap_path in sitemap_paths:
                    try:
                        sitemap_url = urljoin(domain_url, sitemap_path)
                        response = self.session.get(sitemap_url, timeout=1.5)
                        if response.status_code == 200:
                            try:
                                root = ET.fromstring(response.content)
                                sitemap_urls = 0
                                
                                # Extract all URLs from sitemap
                                for url_elem in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc'):
                                    if url_elem.text and self._is_valid_url(url_elem.text):
                                        self.visited.add(url_elem.text)
                                        sitemap_urls += 1
                                
                                # Handle sitemap index files
                                for sitemap_elem in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}sitemap'):
                                    loc_elem = sitemap_elem.find('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                                    if loc_elem is not None and loc_elem.text:
                                        try:
                                            sub_response = self.session.get(loc_elem.text, timeout=1.2)
                                            if sub_response.status_code == 200:
                                                sub_root = ET.fromstring(sub_response.content)
                                                for sub_url in sub_root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc'):
                                                    if sub_url.text and self._is_valid_url(sub_url.text):
                                                        self.visited.add(sub_url.text)
                                                        sitemap_urls += 1
                                        except:
                                            continue
                                
                                if sitemap_urls > 0:
                                    logger.info(f"Extracted {sitemap_urls} URLs from {sitemap_url}")
                                    
                            except ET.ParseError:
                                # Try text-based parsing for non-XML sitemaps
                                for line in response.text.split('\n'):
                                    line = line.strip()
                                    if line.startswith('http') and self._is_valid_url(line):
                                        self.visited.add(line)
                                        
                    except:
                        continue
                
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
        
        # Phase 1: Discover paths dynamically from homepage and sitemaps
        discovered_paths = self._extract_paths_from_content()
        
        # Phase 2: Combine with minimal common paths
        basic_paths = [
            '/blog', '/news', '/resources', '/about', '/contact', '/support', 
            '/help', '/docs', '/pricing', '/products', '/solutions'
        ]
        
        # Merge discovered and basic paths
        all_paths = set(basic_paths + list(discovered_paths))
        
        logger.info(f"Using {len(all_paths)} discovered paths for generation")
        
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
                            
        logger.info(f"Generated {generated_count} URLs from patterns and discovered paths")
    
    def _extract_paths_from_content(self):
        """Extract all unique paths from homepage and initial crawl"""
        discovered_paths = set()
        
        # Analyze all discovered domains
        domains_to_analyze = [self.start_url]
        for subdomain in self.discovered_subdomains:
            domains_to_analyze.append(f"https://{subdomain}")
        
        for domain_url in domains_to_analyze:
            try:
                response = self.session.get(domain_url, timeout=3)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Extract all internal links and their paths
                    for link in soup.find_all('a', href=True):
                        href = link['href']
                        if href.startswith('/') and len(href) > 1:
                            # Clean path - remove query params and fragments
                            clean_path = href.split('?')[0].split('#')[0]
                            if len(clean_path) > 1 and len(clean_path) < 100:
                                # Extract directory paths
                                parts = clean_path.strip('/').split('/')
                                if parts and parts[0]:
                                    base_path = '/' + parts[0]
                                    discovered_paths.add(base_path)
                                    discovered_paths.add(base_path + '/')
                    
                    # Extract from navigation menus specifically
                    nav_elements = soup.find_all(['nav', 'header', 'footer'])
                    for nav in nav_elements:
                        nav_links = nav.find_all('a', href=True)
                        for link in nav_links:
                            href = link['href']
                            if href.startswith('/') and len(href) > 1:
                                clean_path = href.split('?')[0].split('#')[0]
                                if len(clean_path) > 1:
                                    parts = clean_path.strip('/').split('/')
                                    if parts and parts[0]:
                                        base_path = '/' + parts[0]
                                        discovered_paths.add(base_path)
                                        discovered_paths.add(base_path + '/')
                                        
            except Exception as e:
                logger.debug(f"Error analyzing {domain_url} for paths: {e}")
                continue
        
        # Filter out very common/generic paths that might be noise
        filtered_paths = set()
        for path in discovered_paths:
            path_clean = path.strip('/')
            # Skip very short or potentially problematic paths
            if (len(path_clean) >= 2 and 
                not path_clean.isdigit() and 
                path_clean not in ['js', 'css', 'img', 'images', 'assets', 'static']):
                filtered_paths.add(path)
        
        logger.info(f"Discovered {len(filtered_paths)} unique paths from content analysis")
        return list(filtered_paths)
        
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
                    # Don't increment here - we'll use len(self.visited) for progress
                    
                    # Extract ALL internal links from this page
                    new_links = self._comprehensive_link_extraction(response.text, url)
                    
                    # Add all discovered links with more aggressive crawling
                    for link in new_links:
                        if len(self.visited) >= self.max_urls:
                            break
                        if link not in self.visited and self._is_valid_url(link):
                            self.visited.add(link)
                            
                            # Immediately crawl high-priority links (blog posts, articles)
                            if any(pattern in link.lower() for pattern in ['/blog/', '/article/', '/post/', '/news/', '/story/']):
                                try:
                                    quick_response = self.session.get(link, timeout=1.5, allow_redirects=True)
                                    if quick_response.status_code == 200:
                                        # Extract more links from this blog/article page
                                        deeper_links = self._comprehensive_link_extraction(quick_response.text, link)
                                        for deep_link in deeper_links[:20]:  # Limit to prevent explosion
                                            if (deep_link not in self.visited and 
                                                self._is_valid_url(deep_link) and 
                                                len(self.visited) < self.max_urls):
                                                self.visited.add(deep_link)
                                except:
                                    continue
                            
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