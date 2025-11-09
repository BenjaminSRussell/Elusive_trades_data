"""
GoodmanSpider - Scraper for Goodman Manufacturing product data.
Handles JavaScript-heavy product pages using Splash.
"""

from scrapers.spiders.base_spider import FugitiveBaseSpider
from scrapers.items import create_item


class GoodmanSpider(FugitiveBaseSpider):
    """
    Spider for scraping Goodman HVAC parts and specifications.
    Demonstrates Splash integration for dynamic content.
    """

    name = 'goodman'
    allowed_domains = ['goodmanmfg.com']

    # Start URLs - modify these to actual Goodman product pages
    start_urls = [
        'https://www.goodmanmfg.com/products',
    ]

    custom_settings = {
        'CONCURRENT_REQUESTS': 8,
        'DOWNLOAD_DELAY': 2,
    }

    def start_requests(self):
        """
        Initial requests to start crawling.
        For JavaScript-heavy sites, use Splash from the start.
        """
        for url in self.start_urls:
            # Use Splash for JavaScript rendering
            yield self.create_splash_request(
                url=url,
                callback=self.parse_product_listing,
                lua_script=self._get_product_list_lua_script()
            )

    def _get_product_list_lua_script(self):
        """
        Custom Lua script for handling product listing page interactions.
        This demonstrates advanced Splash usage for clicking tabs, scrolling, etc.
        """
        return """
        function main(splash, args)
            splash:init_cookies(splash.args.cookies)
            assert(splash:go(args.url))
            assert(splash:wait(2))

            -- Example: Click on "Specifications" tab if it exists
            local specs_tab = splash:select('#specifications-tab')
            if specs_tab then
                specs_tab:mouse_click()
                assert(splash:wait(1))
            end

            -- Example: Scroll to trigger lazy-loaded content
            splash:set_viewport_full()
            for i = 1, 5 do
                splash:evaljs('window.scrollTo(0, document.body.scrollHeight)')
                assert(splash:wait(0.5))
            end

            return {
                html = splash:html(),
                cookies = splash:get_cookies(),
            }
        end
        """

    def parse_product_listing(self, response):
        """
        Parse product listing page to find individual product links.
        """
        self.logger.info(f'Parsing product listing: {response.url}')

        # Extract product links (adjust selectors based on actual site structure)
        product_links = response.css('a.product-link::attr(href)').getall()

        for link in product_links:
            product_url = response.urljoin(link)
            yield self.create_splash_request(
                url=product_url,
                callback=self.parse_product_page,
                wait_time=3.0
            )

        # Follow pagination (if exists)
        next_page = response.css('a.next-page::attr(href)').get()
        if next_page:
            yield self.create_splash_request(
                url=response.urljoin(next_page),
                callback=self.parse_product_listing
            )

    def parse_product_page(self, response):
        """
        Parse individual product page to extract specifications and PDF links.
        """
        self.logger.info(f'Parsing product page: {response.url}')

        # Extract product information
        product_model = response.css('h1.product-title::text').get()
        description = response.css('div.product-description::text').getall()
        description_text = ' '.join(description).strip()

        # Extract PDF specification sheets
        for pdf_url in self.extract_pdf_links(response):
            yield create_item(
                'pdf',
                source_url=response.url,
                pdf_url=pdf_url,
                file_name=pdf_url.split('/')[-1],
                manufacturer='Goodman',
                metadata={
                    'product_model': product_model,
                    'spider': self.name
                }
            )

        # Extract HTML content
        specs_section = response.css('div.specifications').get()
        if specs_section:
            yield create_item(
                'html',
                source_url=response.url,
                html_content=specs_section,
                title=product_model,
                manufacturer='Goodman',
                product_model=product_model,
                metadata={
                    'description': description_text,
                    'spider': self.name
                }
            )

        # Look for cross-reference information
        cross_ref_section = response.css('div.cross-reference')
        if cross_ref_section:
            cross_ref_text = ' '.join(cross_ref_section.css('::text').getall())

            yield create_item(
                'html',
                source_url=response.url,
                html_content=cross_ref_text,
                title=f'{product_model} - Cross Reference',
                manufacturer='Goodman',
                product_model=product_model,
                metadata={
                    'content_type': 'cross_reference',
                    'spider': self.name
                }
            )
