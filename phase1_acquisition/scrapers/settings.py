"""
Scrapy settings for the Fugitive Data Pipeline.
Configured for Splash integration and anti-bot evasion.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Scrapy project settings
BOT_NAME = 'fugitive_scrapers'
SPIDER_MODULES = ['scrapers.spiders']
NEWSPIDER_MODULE = 'scrapers.spiders'

# Crawl responsibly - Obey robots.txt rules (set to False only if legally authorized)
ROBOTSTXT_OBEY = True

# Configure maximum concurrent requests
CONCURRENT_REQUESTS = 16
CONCURRENT_REQUESTS_PER_DOMAIN = 4

# Download delay to avoid overwhelming servers (in seconds)
DOWNLOAD_DELAY = 1
RANDOMIZE_DOWNLOAD_DELAY = True

# Disable cookies unless needed for authentication
COOKIES_ENABLED = True

# Disable Telemetry in production
TELNETCONSOLE_ENABLED = False

# User Agent rotation for anti-bot evasion
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

# Enable or disable spider middlewares
SPIDER_MIDDLEWARES = {
    'scrapers.middlewares.FugitiveSpiderMiddleware': 543,
}

# Enable or disable downloader middlewares
DOWNLOADER_MIDDLEWARES = {
    # Splash integration middlewares
    'scrapy_splash.SplashCookiesMiddleware': 723,
    'scrapy_splash.SplashMiddleware': 725,
    'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': 810,
    # User agent rotation
    'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
    'scrapy_user_agents.middlewares.RandomUserAgentMiddleware': 400,
}

# Splash Configuration
SPLASH_URL = os.getenv('SPLASH_URL', 'http://localhost:8050')
DUPEFILTER_CLASS = 'scrapy_splash.SplashAwareDupeFilter'
HTTPCACHE_STORAGE = 'scrapy_splash.SplashAwareFSCacheStorage'

# Enable and configure the Kafka pipeline
ITEM_PIPELINES = {
    'scrapers.pipelines.DeduplicationPipeline': 100,
    'scrapers.pipelines.KafkaProducerPipeline': 300,
}

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9093')
KAFKA_TOPIC_PDF_URLS = os.getenv('KAFKA_TOPIC_PDF_URLS', 'pdf_urls')
KAFKA_TOPIC_HTML_CONTENT = os.getenv('KAFKA_TOPIC_HTML_CONTENT', 'html_content')
KAFKA_TOPIC_FORUM_TEXT = os.getenv('KAFKA_TOPIC_FORUM_TEXT', 'forum_text')

# AutoThrottle extension (adaptive download delay)
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1
AUTOTHROTTLE_MAX_DELAY = 10
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
AUTOTHROTTLE_DEBUG = False

# Enable HTTP caching for development (disable in production)
HTTPCACHE_ENABLED = True
HTTPCACHE_EXPIRATION_SECS = 86400  # 24 hours
HTTPCACHE_DIR = 'httpcache'
HTTPCACHE_IGNORE_HTTP_CODES = [500, 502, 503, 504, 522, 524, 408, 429]

# Retry settings
RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 522, 524, 408, 429]

# Logging
LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s [%(name)s] %(levelname)s: %(message)s'

# Request fingerprinter implementation
REQUEST_FINGERPRINTER_IMPLEMENTATION = '2.7'

# Set settings whose default value is deprecated to a future-proof value
TWISTED_REACTOR = 'twisted.internet.asyncioreactor.AsyncioSelectorReactor'
FEED_EXPORT_ENCODING = 'utf-8'
