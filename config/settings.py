"""
Configuration settings for Polis Analysis Metadata Tool
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Keys
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY', '')
REDDIT_CLIENT_ID = os.getenv('REDDIT_CLIENT_ID', '')
REDDIT_CLIENT_SECRET = os.getenv('REDDIT_CLIENT_SECRET', '')
REDDIT_USER_AGENT = os.getenv('REDDIT_USER_AGENT', 'PolisAnalysis-MetadataBot/1.0')

# Rate Limiting
RATE_LIMIT_DELAY = int(os.getenv('RATE_LIMIT_DELAY', 2))
MAX_RETRIES = int(os.getenv('MAX_RETRIES', 3))

# CSV Output Configuration
CSV_COLUMNS = [
    'timestamp',
    'url',
    'platform',
    'title',
    'author',
    'author_id',
    'content',
    'publish_date',
    'likes',
    'shares',
    'comments',
    'views',
    'hashtags',
    'media_urls',
    'engagement_rate',
    'extraction_status',
    'error_message'
]

# Known news/blog domains for generic scraper
KNOWN_NEWS_DOMAINS = [
    'bbc.com', 'bbc.co.uk',
    'cnn.com',
    'theguardian.com',
    'reuters.com',
    'apnews.com',
    'nytimes.com',
    'washingtonpost.com',
    'aljazeera.com',
    'economist.com',
    'medium.com',
    'substack.com',
    'blogger.com',
    'wordpress.com',
    'wix.com'
]

# Platform configuration
PLATFORM_CONFIG = {
    'youtube': {
        'name': 'YouTube',
        'enabled': True,
        'requires_api': True,
        'api_cost': 'Free (10,000 quota/day)'
    },
    'reddit': {
        'name': 'Reddit',
        'enabled': True,
        'requires_api': True,
        'api_cost': 'Free (60 req/min)'
    },
    'news': {
        'name': 'News/Blog Sites',
        'enabled': True,
        'requires_api': False,
        'api_cost': 'Free (scraping)'
    }
}
