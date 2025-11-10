"""
Custom Scrapy middlewares for the Fugitive Data Pipeline.
"""

import logging
from scrapy import signals
from scrapy.http import HtmlResponse

logger = logging.getLogger(__name__)


class FugitiveSpiderMiddleware:
    """
    Spider middleware for handling common patterns across all spiders.
    """

    @classmethod
    def from_crawler(cls, crawler):
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(s.spider_closed, signal=signals.spider_closed)
        return s

    def process_spider_input(self, response, spider):
        """Called for each response before it enters the spider."""
        return None

    def process_spider_output(self, response, result, spider):
        """Called with the results returned from the spider."""
        for item in result:
            yield item

    def process_spider_exception(self, response, exception, spider):
        """Called when a spider or process_spider_input raises an exception."""
        logger.error(f"Spider exception in {spider.name}: {exception}")
        return []

    def spider_opened(self, spider):
        logger.info(f'Spider opened: {spider.name}')

    def spider_closed(self, spider):
        logger.info(f'Spider closed: {spider.name}')


class JavaScriptDetectionMiddleware:
    """
    Detects if a page requires JavaScript rendering and routes to Splash.
    """

    JS_INDICATORS = [
        'This page requires JavaScript',
        'Please enable JavaScript',
        'javascript:void(0)',
        'noscript',
    ]

    def process_response(self, request, response, spider):
        """
        Check if response appears to need JavaScript rendering.
        If so, retry with Splash (if not already using it).
        """
        if not hasattr(request, 'meta') or 'splash' not in request.meta:
            content = response.text.lower()

            # Check for JavaScript requirement indicators
            needs_js = any(indicator.lower() in content for indicator in self.JS_INDICATORS)

            if needs_js:
                logger.warning(f"JavaScript required for {request.url}, retrying with Splash")
                # This would need to be handled at the spider level
                # by implementing a retry with SplashRequest

        return response
