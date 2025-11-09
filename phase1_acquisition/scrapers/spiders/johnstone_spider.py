"""
JohnstoneSupplySpider - Scraper for Johnstone Supply distributor portal.
Demonstrates portal authentication and session management for high-value data.
"""

import os
import scrapy
from scrapers.spiders.base_spider import FugitiveBaseSpider
from scrapers.items import create_item


class JohnstoneSupplySpider(FugitiveBaseSpider):
    """
    Spider for scraping Johnstone Supply distributor portal.
    Accesses authenticated cross-reference data and pricing information.
    """

    name = 'johnstone_supply'
    allowed_domains = ['johnstonesupply.com']

    # Portal URLs (adjust to actual URLs)
    login_url = 'https://www.johnstonesupply.com/account/login'
    portal_url = 'https://www.johnstonesupply.com/portal'

    custom_settings = {
        'CONCURRENT_REQUESTS': 2,  # Be conservative with authenticated requests
        'DOWNLOAD_DELAY': 4,
        'COOKIES_ENABLED': True,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Load technician credentials from environment
        self.username = os.getenv('JOHNSTONE_USERNAME')
        self.password = os.getenv('JOHNSTONE_PASSWORD')

        if not self.username or not self.password:
            self.logger.error('Johnstone Supply credentials not configured')

    def start_requests(self):
        """
        Start by navigating to the login page.
        """
        if not self.username or not self.password:
            self.logger.error('Cannot proceed without valid credentials')
            return

        yield scrapy.Request(
            url=self.login_url,
            callback=self.parse_login_form,
            meta={'dont_cache': True}
        )

    def parse_login_form(self, response):
        """
        Parse login form and extract any hidden fields or CSRF tokens.
        """
        self.logger.info('Analyzing login form')

        # Look for anti-forgery tokens
        csrf_token = response.css('input[name="__RequestVerificationToken"]::attr(value)').get()
        if not csrf_token:
            # Try alternative names
            csrf_token = response.css('input[name="csrf_token"]::attr(value)').get()
            if not csrf_token:
                csrf_token = response.css('input[name="_token"]::attr(value)').get()

        # Extract form action URL (in case it's different from login_url)
        form_action = response.css('form#login-form::attr(action)').get()
        if form_action:
            login_post_url = response.urljoin(form_action)
        else:
            login_post_url = self.login_url

        # Build form data
        form_data = {
            'username': self.username,
            'email': self.username,  # Some sites use 'email' instead
            'password': self.password,
        }

        # Add CSRF token if found
        if csrf_token:
            form_data['__RequestVerificationToken'] = csrf_token
            self.logger.info('CSRF token found and included')

        # Extract any other hidden fields
        for hidden in response.css('form#login-form input[type="hidden"]'):
            name = hidden.attrib.get('name')
            value = hidden.attrib.get('value', '')
            if name and name not in form_data:
                form_data[name] = value

        # Submit login form
        yield scrapy.FormRequest(
            url=login_post_url,
            formdata=form_data,
            callback=self.verify_login,
            dont_filter=True
        )

    def verify_login(self, response):
        """
        Verify that login was successful and start scraping portal data.
        """
        # Check for indicators of successful login
        success_indicators = [
            'dashboard',
            'welcome',
            'logout',
            'my account',
            'signed in',
        ]

        failure_indicators = [
            'invalid credentials',
            'login failed',
            'incorrect password',
            'try again',
        ]

        response_text_lower = response.text.lower()

        # Check for failure first
        if any(indicator in response_text_lower for indicator in failure_indicators):
            self.logger.error('Login FAILED - check credentials and form fields')
            return

        # Check for success
        if any(indicator in response_text_lower for indicator in success_indicators):
            self.logger.info('✓ Login SUCCESSFUL - accessing portal data')

            # Start scraping authenticated portal content
            yield from self.scrape_portal_content()
        else:
            self.logger.warning('Login status unclear - check manually')

    def scrape_portal_content(self):
        """
        Scrape high-value content from the authenticated portal.
        """
        # Cross-reference database
        yield scrapy.Request(
            url=f'{self.portal_url}/cross-reference',
            callback=self.parse_cross_reference_page,
            dont_filter=True
        )

        # Product catalog with specifications
        yield scrapy.Request(
            url=f'{self.portal_url}/products',
            callback=self.parse_product_catalog,
            dont_filter=True
        )

    def parse_cross_reference_page(self, response):
        """
        Parse cross-reference data - this is extremely valuable!
        """
        self.logger.info(f'Parsing cross-reference data: {response.url}')

        # Extract cross-reference tables (adjust selectors)
        tables = response.css('table.cross-reference-table')

        for table in tables:
            # Extract table as HTML
            table_html = table.get()

            # Also extract as structured data
            rows = []
            for row in table.css('tr'):
                cells = row.css('td::text').getall()
                if cells:
                    rows.append(cells)

            yield create_item(
                'html',
                source_url=response.url,
                html_content=table_html,
                title='Johnstone Supply Cross Reference Table',
                manufacturer='Various',
                metadata={
                    'content_type': 'cross_reference_table',
                    'row_count': len(rows),
                    'authenticated': True,
                    'distributor': 'Johnstone Supply',
                    'spider': self.name
                }
            )

    def parse_product_catalog(self, response):
        """
        Parse product catalog pages.
        """
        self.logger.info(f'Parsing product catalog: {response.url}')

        # Extract product cards
        products = response.css('div.product-card')

        for product in products:
            part_number = product.css('span.part-number::text').get()
            manufacturer = product.css('span.manufacturer::text').get()

            # PDF spec sheet links
            pdf_link = product.css('a.spec-sheet-link::attr(href)').get()
            if pdf_link:
                yield create_item(
                    'pdf',
                    source_url=response.url,
                    pdf_url=response.urljoin(pdf_link),
                    file_name=pdf_link.split('/')[-1],
                    manufacturer=manufacturer or 'Unknown',
                    metadata={
                        'part_number': part_number,
                        'authenticated': True,
                        'distributor': 'Johnstone Supply',
                        'spider': self.name
                    }
                )

            # Product detail link
            detail_link = product.css('a.details-link::attr(href)').get()
            if detail_link:
                yield response.follow(
                    detail_link,
                    callback=self.parse_product_detail
                )

        # Pagination
        next_button = response.css('a.next-page::attr(href)').get()
        if next_button:
            yield response.follow(next_button, callback=self.parse_product_catalog)

    def parse_product_detail(self, response):
        """
        Parse individual product detail pages.
        """
        part_number = response.css('h1.product-title span.part::text').get()
        manufacturer = response.css('span.manufacturer-name::text').get()

        # Specifications section
        specs = response.css('div.specifications').get()
        if specs:
            yield create_item(
                'html',
                source_url=response.url,
                html_content=specs,
                title=f'{part_number} Specifications',
                manufacturer=manufacturer or 'Unknown',
                product_model=part_number,
                metadata={
                    'content_type': 'specifications',
                    'authenticated': True,
                    'distributor': 'Johnstone Supply',
                    'spider': self.name
                }
            )
