import xml.etree.ElementTree as ET
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class SitemapGenerator:
    def generate(self, urls):
        """Generate XML sitemap from URLs"""
        try:
            # Create root element with proper namespace
            urlset = ET.Element("urlset")
            urlset.set("xmlns", "http://www.sitemaps.org/schemas/sitemap/0.9")
            
            # Sort URLs for consistent output
            sorted_urls = sorted(list(urls))
            
            for url in sorted_urls:
                url_element = ET.SubElement(urlset, "url")
                
                # Add location
                loc = ET.SubElement(url_element, "loc")
                loc.text = url.strip()
                
                # Add last modified date
                lastmod = ET.SubElement(url_element, "lastmod")
                lastmod.text = datetime.now().strftime("%Y-%m-%d")
                
                # Add change frequency (optional)
                changefreq = ET.SubElement(url_element, "changefreq")
                changefreq.text = "weekly"
                
                # Add priority (optional)
                priority = ET.SubElement(url_element, "priority")
                # Homepage gets higher priority
                if url.rstrip('/').split('/')[-1] == '' or url.rstrip('/').count('/') <= 2:
                    priority.text = "1.0"
                else:
                    priority.text = "0.8"
            
            # Create tree and write to file
            tree = ET.ElementTree(urlset)
            ET.indent(tree, space="  ", level=0)  # Pretty print
            
            with open("sitemap.xml", "wb") as f:
                tree.write(f, encoding="UTF-8", xml_declaration=True)
            
            logger.info(f"Sitemap generated successfully with {len(sorted_urls)} URLs")
            return True
            
        except Exception as e:
            logger.error(f"Error generating sitemap: {str(e)}")
            return False
