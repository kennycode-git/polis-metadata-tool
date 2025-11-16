"""
Platform detection from URL
"""
from urllib.parse import urlparse
from config.settings import KNOWN_NEWS_DOMAINS


def detect_platform(url: str) -> str:
    """
    Detect the platform/source from a URL
    
    Args:
        url: The URL to analyze
        
    Returns:
        Platform identifier string ('youtube', 'tiktok', 'facebook', 'reddit', 'news', 'unknown')
    """
    try:
        parsed = urlparse(url.lower())
        domain = parsed.netloc
        
        # Remove www. prefix
        if domain.startswith('www.'):
            domain = domain[4:]

        if 'tiktok.com' in domain or 'vm.tiktok.com' in domain:
            return 'tiktok'
        
        # YouTube detection
        if 'youtube.com' in domain or 'youtu.be' in domain:
            return 'youtube'
        
        # Facebook detection
        if 'facebook.com' in domain or 'fb.com' in domain or 'fb.watch' in domain:
            return 'facebook'
        
        # Reddit detection
        if 'reddit.com' in domain:
            return 'reddit'
        
        # News/Blog detection
        for news_domain in KNOWN_NEWS_DOMAINS:
            if news_domain in domain:
                return 'news'
        
        # Check if it looks like a blog/news site (has common patterns)
        if any(pattern in domain for pattern in ['.blog', 'blog.', 'news.', '.news']):
            return 'news'
        
        return 'unknown'
        
    except Exception as e:
        return 'unknown'


def get_platform_display_name(platform: str) -> str:
    """
    Get human-readable platform name
    
    Args:
        platform: Platform identifier
        
    Returns:
        Display name string
    """
    platform_names = {
        'tiktok': 'TikTok',
        'youtube': 'YouTube',
        'facebook': 'Facebook',
        'reddit': 'Reddit',
        'news': 'News/Blog Site',
        'unknown': 'Unknown Source'
    }
    return platform_names.get(platform, 'Unknown')


def is_supported_platform(platform: str) -> bool:
    """
    Check if platform is currently supported
    
    Args:
        platform: Platform identifier
        
    Returns:
        Boolean indicating support status
    """
    supported = ['tiktok', 'youtube', 'facebook', 'reddit', 'news']
    return platform in supported