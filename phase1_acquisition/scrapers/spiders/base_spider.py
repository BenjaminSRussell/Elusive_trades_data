"""
Base spider class with common functionality for all Fugitive spiders.
"""

import scrapy
import hashlib
from typing import Optional
from scrapy_splash import SplashRequest


class FugitiveBaseSpider(scrapy.Spider):
    """
    Base spider class with shared utilities for all manufacturer spiders.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.manufacturer = self.__class__.__name__.replace('Spider', '')

    def create_splash_request(self, url: str, callback, lua_script: Optional[str] = None,
                             wait_time: float = 2.0, **kwargs):
        """
        Create a SplashRequest for JavaScript-heavy pages.

        Args:
            url: URL to scrape
            callback: Callback function to process response
            lua_script: Custom Lua script (if None, uses default wait script)
            wait_time: Time to wait for page to load (seconds)
            **kwargs: Additional arguments for SplashRequest

        Returns:
            SplashRequest object
        """
        if lua_script is None:
            # Default Lua script: wait for page load and return HTML
            lua_script = f"""
            function main(splash, args)
                splash:init_cookies(splash.args.cookies)
                assert(splash:go(args.url))
                assert(splash:wait({wait_time}))
                return {{
                    html = splash:html(),
                    cookies = splash:get_cookies(),
                }}
            end
            """

        return SplashRequest(
            url=url,
            callback=callback,
            endpoint='execute',
            args={'lua_source': lua_script, 'wait': wait_time},
            **kwargs
        )

    def extract_pdf_links(self, response, selector: str = 'a[href$=".pdf"]'):
        """
        Extract PDF links from a response.

        Args:
            response: Scrapy response object
            selector: CSS selector for PDF links

        Yields:
            Absolute PDF URLs
        """
        for link in response.css(selector):
            pdf_url = response.urljoin(link.attrib.get('href', ''))
            if pdf_url.lower().endswith('.pdf'):
                yield pdf_url

    def compute_hash(self, content: str) -> str:
        """
        Compute SHA256 hash of content.

        Args:
            content: String to hash

        Returns:
            Hexadecimal hash string
        """
        return hashlib.sha256(content.encode()).hexdigest()

    def parse_specification_text(self, text: str) -> dict:
        """
        Extract structured specifications from free-form text.
        This is a placeholder - implement domain-specific logic.

        Args:
            text: Specification text

        Returns:
            Dictionary of extracted specifications
        """
        specs = {}

        # Example patterns (implement more robust extraction)
        import re

        # HP pattern: "1/2 HP", "1 HP"
        hp_match = re.search(r'(\d+(?:/\d+)?)\s*HP', text, re.IGNORECASE)
        if hp_match:
            specs['horsepower'] = hp_match.group(1)

        # Voltage pattern: "208-230V", "115V"
        voltage_match = re.search(r'(\d+(?:-\d+)?)\s*V(?:olts?)?', text, re.IGNORECASE)
        if voltage_match:
            specs['voltage'] = voltage_match.group(1)

        # Capacitor pattern: "40+5 MFD", "45 MFD"
        capacitor_match = re.search(r'(\d+(?:\+\d+)?)\s*(?:MFD|uF|µF)', text, re.IGNORECASE)
        if capacitor_match:
            specs['capacitor'] = capacitor_match.group(1)

        return specs
