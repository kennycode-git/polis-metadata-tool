"""Extractors package for Polis Analysis Metadata Tool"""

from .base_extractor import BaseExtractor
from .tiktok_extractor import TikTokExtractor
from .youtube_extractor import YouTubeExtractor
from .reddit_extractor import RedditExtractor
from .news_extractor import NewsExtractor
from .facebook_extractor import FacebookExtractor

__all__ = [
    'BaseExtractor',
    'TikTokExtractor',
    'YouTubeExtractor',
    'RedditExtractor',
    'NewsExtractor',
    'FacebookExtractor'
]
