"""
Real-world production spider for testing against actual HVAC manufacturer websites.
Includes comprehensive error handling and validation.
"""

import scrapy
from scrapy.http import Response
from scrapers.spiders.base_spider import FugitiveBaseSpider
from scrapers.items import create_item
from config.error_handling import (
    retry_on_failure, safe_execute, validate_url,
    sanitize_filename, error_tracker, log_exception
)
import logging

logger = logging.getLogger(__name__)


class RealWorldTestSpider(FugitiveBaseSpider):
    """
    Production spider for real HVAC parts websites.
    Tests against actual manufacturer sites with robust error handling.
    """

    name = 'realworld_test'

    # REAL websites - these are actual HVAC parts suppliers
    start_urls = [
        # Supco (Universal parts manufacturer - real site)
        'https://www.supco.com/web/supco/hvacr-parts',

        # Standard Motor Products (Real distributor)
        'https://www.standardmotorproducts.com',
    ]

    custom_settings = {
        'CONCURRENT_REQUESTS': 2,  # Be polite to real sites
        'DOWNLOAD_DELAY': 3,  # 3 seconds between requests
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'RETRY_TIMES': 3,
        'RETRY_HTTP_CODES': [500, 502, 503, 504, 522, 524, 408, 429],
        'HTTPERROR_ALLOWED_CODES': [404, 403],  # Don't fail on these
        'ROBOTSTXT_OBEY': True,  # Respect robots.txt
        'USER_AGENT': 'Mozilla/5.0 (compatible; FugitiveBot/1.0; +http://example.com/bot)',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stats = {
            'pages_crawled': 0,
            'pdfs_found': 0,
            'errors': 0,
            'items_scraped': 0
        }

    @log_exception(logger)
    def start_requests(self):
        """
        Generate initial requests with error handling.
        """
        for url in self.start_urls:
            if not validate_url(url):
                logger.error(f"Invalid start URL: {url}")
                error_tracker.record_error(
                    component='spider',
                    error_type='invalid_url',
                    message=f"Invalid start URL: {url}"
                )
                continue

            try:
                yield scrapy.Request(
                    url=url,
                    callback=self.parse,
                    errback=self.handle_error,
                    dont_filter=False,
                    meta={'handle_httpstatus_all': True}
                )
            except Exception as e:
                logger.error(f"Failed to create request for {url}: {e}")
                error_tracker.record_error(
                    component='spider',
                    error_type='request_creation',
                    message=str(e),
                    details={'url': url}
                )

    def parse(self, response: Response):
        """
        Main parsing logic with comprehensive error handling.
        """
        try:
            # Check response status
            if response.status >= 400:
                logger.warning(f"HTTP {response.status} for {response.url}")
                error_tracker.record_error(
                    component='spider',
                    error_type='http_error',
                    message=f"HTTP {response.status}",
                    details={'url': response.url}
                )
                return

            self.stats['pages_crawled'] += 1
            logger.info(f"Parsing: {response.url} (Status: {response.status})")

            # Extract product links safely
            product_links = safe_execute(
                response.css, 'a[href*="product"]::attr(href)',
                default=scrapy.Selector(text='').css('notexist'),
                log_error=True
            ).getall()

            # Process product links
            for link in product_links[:10]:  # Limit to 10 for testing
                product_url = response.urljoin(link)

                if validate_url(product_url):
                    yield scrapy.Request(
                        url=product_url,
                        callback=self.parse_product,
                        errback=self.handle_error
                    )
                else:
                    logger.debug(f"Skipping invalid product URL: {link}")

            # Extract PDF links
            pdf_links = self.extract_pdf_links(response)
            for pdf_url in pdf_links:
                if validate_url(pdf_url):
                    yield self.create_pdf_item(response.url, pdf_url)
                    self.stats['pdfs_found'] += 1

        except Exception as e:
            logger.error(f"Error parsing {response.url}: {e}", exc_info=True)
            error_tracker.record_error(
                component='spider',
                error_type='parse_error',
                message=str(e),
                details={'url': response.url}
            )
            self.stats['errors'] += 1

    def parse_product(self, response: Response):
        """
        Parse individual product pages with validation.
        """
        try:
            if response.status != 200:
                logger.warning(f"Non-200 status for product page: {response.url}")
                return

            # Extract part number with multiple selectors (fallback pattern)
            part_number = (
                safe_execute(response.css, 'span.part-number::text', default=scrapy.Selector(text='').css('notexist')).get() or
                safe_execute(response.css, 'div.sku::text', default=scrapy.Selector(text='').css('notexist')).get() or
                safe_execute(response.css, 'span.product-code::text', default=scrapy.Selector(text='').css('notexist')).get() or
                'UNKNOWN'
            )

            # Extract description
            description = safe_execute(
                response.css,
                'div.description::text, p.product-desc::text',
                default=scrapy.Selector(text='').css('notexist')
            ).get()

            # Extract manufacturer
            manufacturer = safe_execute(
                response.css,
                'span.manufacturer::text, div.brand::text',
                default=scrapy.Selector(text='').css('notexist')
            ).get() or self.manufacturer

            # Only create item if we have meaningful data
            if part_number and part_number != 'UNKNOWN':
                item = create_item(
                    'html',
                    source_url=response.url,
                    html_content=response.text[:5000],  # Limit content size
                    title=f"{manufacturer} {part_number}",
                    manufacturer=manufacturer,
                    product_model=part_number,
                    metadata={
                        'description': description,
                        'spider': self.name,
                        'timestamp': str(self.stats['pages_crawled'])
                    }
                )

                self.stats['items_scraped'] += 1
                yield item

                logger.info(f"✓ Scraped product: {manufacturer} {part_number}")

            # Extract PDFs from product page
            pdf_links = self.extract_pdf_links(response)
            for pdf_url in pdf_links:
                if validate_url(pdf_url):
                    yield self.create_pdf_item(response.url, pdf_url, part_number, manufacturer)
                    self.stats['pdfs_found'] += 1

        except Exception as e:
            logger.error(f"Error parsing product {response.url}: {e}", exc_info=True)
            error_tracker.record_error(
                component='spider',
                error_type='product_parse_error',
                message=str(e),
                details={'url': response.url}
            )
            self.stats['errors'] += 1

    def create_pdf_item(self, source_url: str, pdf_url: str,
                       part_number: str = None, manufacturer: str = None):
        """
        Create a PDF item with validation.

        Args:
            source_url: Page URL where PDF was found
            pdf_url: PDF URL
            part_number: Optional part number
            manufacturer: Optional manufacturer

        Returns:
            PDF item or None
        """
        try:
            # Sanitize filename
            filename = sanitize_filename(pdf_url.split('/')[-1])

            if not filename.endswith('.pdf'):
                filename += '.pdf'

            return create_item(
                'pdf',
                source_url=source_url,
                pdf_url=pdf_url,
                file_name=filename,
                manufacturer=manufacturer or 'Unknown',
                metadata={
                    'part_number': part_number,
                    'spider': self.name
                }
            )

        except Exception as e:
            logger.error(f"Error creating PDF item for {pdf_url}: {e}")
            error_tracker.record_error(
                component='spider',
                error_type='item_creation_error',
                message=str(e),
                details={'pdf_url': pdf_url}
            )
            return None

    def handle_error(self, failure):
        """
        Handle request failures.

        Args:
            failure: Twisted Failure object
        """
        logger.error(f"Request failed: {failure.value}")
        error_tracker.record_error(
            component='spider',
            error_type='request_failure',
            message=str(failure.value),
            details={'url': failure.request.url}
        )
        self.stats['errors'] += 1

    def closed(self, reason):
        """
        Called when spider closes - print statistics.

        Args:
            reason: Close reason
        """
        logger.info("=" * 60)
        logger.info(f"Spider '{self.name}' closed: {reason}")
        logger.info("Statistics:")
        logger.info(f"  Pages Crawled: {self.stats['pages_crawled']}")
        logger.info(f"  Items Scraped: {self.stats['items_scraped']}")
        logger.info(f"  PDFs Found: {self.stats['pdfs_found']}")
        logger.info(f"  Errors: {self.stats['errors']}")
        logger.info("=" * 60)

        # Print error summary
        error_summary = error_tracker.get_error_summary()
        if error_summary['total_errors'] > 0:
            logger.warning(f"Total errors tracked: {error_summary['total_errors']}")
            logger.warning(f"Error counts: {error_summary['error_counts']}")
