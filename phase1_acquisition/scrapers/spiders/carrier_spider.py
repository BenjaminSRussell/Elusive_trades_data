"""
CarrierSpider - Scraper for Carrier HVAC product data.
Demonstrates authenticated scraping for distributor portals.
"""

import os
import scrapy
from scrapers.spiders.base_spider import FugitiveBaseSpider
from scrapers.items import create_item


class CarrierSpider(FugitiveBaseSpider):
    """
    Spider for scraping Carrier HVAC parts with authentication.
    Demonstrates login flow with CSRF token handling.
    """

    name = 'carrier'
    allowed_domains = ['carrier.com', 'carrierenterpriseparts.com']

    # Login URL (adjust to actual Carrier portal)
    login_url = 'https://www.carrierenterpriseparts.com/login'

    custom_settings = {
        'CONCURRENT_REQUESTS': 4,
        'DOWNLOAD_DELAY': 3,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Load credentials from environment
        self.username = os.getenv('CARRIER_USERNAME')
        self.password = os.getenv('CARRIER_PASSWORD')

        if not self.username or not self.password:
            self.logger.warning('Carrier credentials not found in environment')

    def start_requests(self):
        """
        Start by requesting the login page to capture CSRF tokens.
        """
        if not self.username or not self.password:
            self.logger.error('Cannot proceed without credentials')
            return

        yield scrapy.Request(
            url=self.login_url,
            callback=self.parse_login_page
        )

    def parse_login_page(self, response):
        """
        Parse the login page to extract CSRF tokens and other hidden fields.
        """
        self.logger.info('Parsing login page')

        # Extract CSRF token (adjust selector based on actual site)
        csrf_token = response.css('input[name="csrf_token"]::attr(value)').get()

        # Extract any other hidden fields
        hidden_inputs = {}
        for hidden in response.css('input[type="hidden"]'):
            name = hidden.attrib.get('name')
            value = hidden.attrib.get('value', '')
            if name:
                hidden_inputs[name] = value

        # Prepare login form data
        form_data = {
            'username': self.username,
            'password': self.password,
            **hidden_inputs  # Include all hidden fields
        }

        if csrf_token:
            form_data['csrf_token'] = csrf_token

        # Submit login form
        yield scrapy.FormRequest(
            url=self.login_url,
            formdata=form_data,
            callback=self.after_login,
            dont_filter=True
        )

    def after_login(self, response):
        """
        Verify login was successful and start scraping protected content.
        """
        # Check for login success (adjust based on actual site)
        if 'logout' in response.text.lower() or 'my account' in response.text.lower():
            self.logger.info('Login successful!')

            # Start scraping authenticated content
            yield from self.scrape_authenticated_content()
        else:
            self.logger.error('Login failed - check credentials')

    def scrape_authenticated_content(self):
        """
        Scrape content that requires authentication.
        """
        # Example: Cross-reference database URLs
        protected_urls = [
            'https://www.carrierenterpriseparts.com/cross-reference',
            'https://www.carrierenterpriseparts.com/products/motors',
            'https://www.carrierenterpriseparts.com/products/capacitors',
        ]

        for url in protected_urls:
            yield scrapy.Request(
                url=url,
                callback=self.parse_product_page,
                dont_filter=True
            )

    def parse_product_page(self, response):
        """
        Parse authenticated product pages.
        """
        self.logger.info(f'Parsing authenticated page: {response.url}')

        # Extract product information (adjust selectors)
        products = response.css('div.product-item')

        for product in products:
            part_number = product.css('span.part-number::text').get()
            description = product.css('p.description::text').get()
            pdf_link = product.css('a.spec-sheet::attr(href)').get()

            # If PDF link exists
            if pdf_link:
                pdf_url = response.urljoin(pdf_link)
                yield create_item(
                    'pdf',
                    source_url=response.url,
                    pdf_url=pdf_url,
                    file_name=pdf_url.split('/')[-1],
                    manufacturer='Carrier',
                    metadata={
                        'part_number': part_number,
                        'description': description,
                        'authenticated': True,
                        'spider': self.name
                    }
                )

            # Extract cross-reference data
            cross_refs = product.css('div.cross-reference')
            if cross_refs:
                cross_ref_html = cross_refs.get()
                yield create_item(
                    'html',
                    source_url=response.url,
                    html_content=cross_ref_html,
                    title=f'Carrier {part_number} Cross Reference',
                    manufacturer='Carrier',
                    product_model=part_number,
                    metadata={
                        'content_type': 'cross_reference',
                        'authenticated': True,
                        'spider': self.name
                    }
                )

        # Follow pagination
        next_page = response.css('a.pagination-next::attr(href)').get()
        if next_page:
            yield response.follow(next_page, callback=self.parse_product_page)
