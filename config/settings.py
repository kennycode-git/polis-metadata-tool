"""
Configuration settings for Polis Analysis Metadata Tool
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file (for local development)
load_dotenv()

# Try to import Streamlit for cloud deployment
try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False

# Helper function to get config value from multiple sources
def get_config(key, default=''):
    """Get config from Streamlit secrets, then env vars, then default"""
    # Priority 1: Streamlit secrets (for cloud deployment)
    if STREAMLIT_AVAILABLE:
        try:
            if key in st.secrets:
                return st.secrets[key]
        except:
            pass
    
    # Priority 2: Environment variables (for local .env)
    return os.getenv(key, default)

# API Keys
YOUTUBE_API_KEY = get_config('YOUTUBE_API_KEY', '')
REDDIT_CLIENT_ID = get_config('REDDIT_CLIENT_ID', '')
REDDIT_CLIENT_SECRET = get_config('REDDIT_CLIENT_SECRET', '')
REDDIT_USER_AGENT = get_config('REDDIT_USER_AGENT', 'PolisAnalysis-MetadataBot/1.0')

# Rate Limiting
RATE_LIMIT_DELAY = int(get_config('RATE_LIMIT_DELAY', '1'))
MAX_RETRIES = int(get_config('MAX_RETRIES', '4'))

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
