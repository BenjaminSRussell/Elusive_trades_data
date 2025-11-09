"""
Data models for scraped items in the Fugitive Data Pipeline.
"""

import scrapy
from datetime import datetime


class DocumentItem(scrapy.Item):
    """Base item for all scraped documents."""
    source_url = scrapy.Field()
    scraped_at = scrapy.Field()
    document_type = scrapy.Field()  # 'pdf', 'html', 'forum'
    content = scrapy.Field()
    metadata = scrapy.Field()


class PDFItem(DocumentItem):
    """Item for PDF documents (URLs to be downloaded and processed)."""
    pdf_url = scrapy.Field()
    file_name = scrapy.Field()
    manufacturer = scrapy.Field()


class HTMLItem(DocumentItem):
    """Item for HTML content (product pages, spec sheets)."""
    html_content = scrapy.Field()
    title = scrapy.Field()
    manufacturer = scrapy.Field()
    product_model = scrapy.Field()


class ForumPostItem(DocumentItem):
    """Item for forum posts containing tribal knowledge."""
    post_text = scrapy.Field()
    post_title = scrapy.Field()
    author = scrapy.Field()
    post_date = scrapy.Field()
    forum_name = scrapy.Field()


def create_item(item_type: str, **kwargs) -> DocumentItem:
    """
    Factory function to create items with default values.

    Args:
        item_type: Type of item ('pdf', 'html', 'forum')
        **kwargs: Field values

    Returns:
        Populated DocumentItem subclass
    """
    item_classes = {
        'pdf': PDFItem,
        'html': HTMLItem,
        'forum': ForumPostItem
    }

    item_class = item_classes.get(item_type, DocumentItem)
    item = item_class()

    # Set default values
    item['scraped_at'] = datetime.utcnow().isoformat()
    item['document_type'] = item_type

    # Set provided values
    for key, value in kwargs.items():
        if key in item.fields:
            item[key] = value

    return item
