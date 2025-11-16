"""
URL validation utilities
"""
import validators
import re
from urllib.parse import urlparse, parse_qs
from typing import Optional


def is_valid_url(url: str) -> bool:
    """
    Validate if string is a proper URL
    
    Args:
        url: String to validate
        
    Returns:
        Boolean indicating if URL is valid
    """
    if not url or not isinstance(url, str):
        return False
    
    # Use validators library
    result = validators.url(url)
    return result is True


def normalize_url(url: str) -> str:
    """
    Normalize URL format (add https if missing, etc.)
    
    Args:
        url: URL to normalize
        
    Returns:
        Normalized URL string
    """
    url = url.strip()
    
    # Add protocol if missing
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    return url


def extract_video_id_youtube(url: str) -> Optional[str]:
    """
    Extract YouTube video ID from various URL formats
    
    Supported formats:
    - Standard: https://www.youtube.com/watch?v=VIDEO_ID
    - Short: https://youtu.be/VIDEO_ID
    - Shorts: https://www.youtube.com/shorts/VIDEO_ID
    - Embed: https://www.youtube.com/embed/VIDEO_ID
    - Mobile: https://m.youtube.com/watch?v=VIDEO_ID
    - With timestamp: https://www.youtube.com/watch?v=VIDEO_ID&t=123s
    - With playlist: https://www.youtube.com/watch?v=VIDEO_ID&list=PLAYLIST_ID
    - Live: https://www.youtube.com/live/VIDEO_ID
    
    Args:
        url: YouTube URL
        
    Returns:
        Video ID string or None
    """
    # Remove whitespace
    url = url.strip()
    
    # Pattern 1: youtu.be short links
    # Example: https://youtu.be/dQw4w9WgXcQ
    match = re.search(r'youtu\.be/([a-zA-Z0-9_-]{11})', url)
    if match:
        return match.group(1)
    
    # Pattern 2: youtube.com/shorts/
    # Example: https://www.youtube.com/shorts/dQw4w9WgXcQ
    match = re.search(r'youtube\.com/shorts/([a-zA-Z0-9_-]{11})', url)
    if match:
        return match.group(1)
    
    # Pattern 3: youtube.com/embed/
    # Example: https://www.youtube.com/embed/dQw4w9WgXcQ
    match = re.search(r'youtube\.com/embed/([a-zA-Z0-9_-]{11})', url)
    if match:
        return match.group(1)
    
    # Pattern 4: youtube.com/v/
    # Example: https://www.youtube.com/v/dQw4w9WgXcQ
    match = re.search(r'youtube\.com/v/([a-zA-Z0-9_-]{11})', url)
    if match:
        return match.group(1)
    
    # Pattern 5: Standard watch URL with query parameters
    # Example: https://www.youtube.com/watch?v=dQw4w9WgXcQ
    # Also handles: https://m.youtube.com/watch?v=dQw4w9WgXcQ
    match = re.search(r'[?&]v=([a-zA-Z0-9_-]{11})', url)
    if match:
        return match.group(1)
    
    # Pattern 6: youtube.com/live/ (live streams)
    # Example: https://www.youtube.com/live/dQw4w9WgXcQ
    match = re.search(r'youtube\.com/live/([a-zA-Z0-9_-]{11})', url)
    if match:
        return match.group(1)
    
    # Pattern 7: Attribution links
    # Example: https://www.youtube.com/attribution_link?u=/watch?v=dQw4w9WgXcQ
    match = re.search(r'attribution_link.*?[?&]v=([a-zA-Z0-9_-]{11})', url)
    if match:
        return match.group(1)
    
    return None


def validate_youtube_url(url: str) -> bool:
    """
    Validate if URL is a valid YouTube URL
    
    Args:
        url: URL string to validate
        
    Returns:
        True if valid YouTube URL, False otherwise
    """
    return extract_video_id_youtube(url) is not None


def extract_post_id_reddit(url: str) -> tuple:
    """
    Extract Reddit post/comment ID from URL
    
    Args:
        url: Reddit URL
        
    Returns:
        Tuple of (post_id, comment_id) or (None, None)
    """
    parsed = urlparse(url)
    path_parts = parsed.path.strip('/').split('/')
    
    try:
        # Reddit URL format: /r/subreddit/comments/post_id/title/comment_id
        if 'comments' in path_parts:
            comment_idx = path_parts.index('comments')
            post_id = path_parts[comment_idx + 1] if len(path_parts) > comment_idx + 1 else None
            comment_id = path_parts[comment_idx + 3] if len(path_parts) > comment_idx + 3 else None
            return post_id, comment_id
    except (ValueError, IndexError):
        pass
    
    return None, None


def extract_tiktok_id(url: str) -> Optional[str]:
    """
    Extract TikTok video ID from URL
    
    Args:
        url: TikTok URL string
        
    Returns:
        Video ID if found, None otherwise
    """
    # Pattern for standard TikTok video URLs
    # Example: https://www.tiktok.com/@username/video/1234567890123456789
    match = re.search(r'tiktok\.com/@[\w.-]+/video/(\d+)', url)
    if match:
        return match.group(1)
    
    # Pattern for short TikTok URLs
    # Example: https://vm.tiktok.com/ABC123/
    match = re.search(r'vm\.tiktok\.com/([a-zA-Z0-9]+)', url)
    if match:
        return match.group(1)
    
    return None


def validate_tiktok_url(url: str) -> bool:
    """
    Validate if URL is a valid TikTok URL
    
    Args:
        url: URL string to validate
        
    Returns:
        True if valid TikTok URL, False otherwise
    """
    return 'tiktok.com' in url.lower()


def validate_reddit_url(url: str) -> bool:
    """
    Validate if URL is a valid Reddit URL
    
    Args:
        url: URL string to validate
        
    Returns:
        True if valid Reddit URL, False otherwise
    """
    return 'reddit.com' in url.lower() and '/comments/' in url.lower()


def validate_facebook_url(url: str) -> bool:
    """
    Validate if URL is a valid Facebook URL
    
    Args:
        url: URL string to validate
        
    Returns:
        True if valid Facebook URL, False otherwise
    """
    url_lower = url.lower()
    return ('facebook.com' in url_lower or 'fb.watch' in url_lower or 'fb.com' in url_lower)


def validate_news_url(url: str) -> bool:
    """
    Validate if URL is from a news or blog site
    
    Args:
        url: URL string to validate
        
    Returns:
        True if likely a news/blog URL, False otherwise
    """
    # Common news/blog domains
    news_domains = [
        'medium.com',
        'substack.com',
        'wordpress.com',
        'blogspot.com',
        'news',  # catches any domain with 'news'
        'bbc.com',
        'cnn.com',
        'nytimes.com',
        'theguardian.com',
        'reuters.com',
        'ap.org',
        'washingtonpost.com',
        'bloomberg.com',
        'forbes.com',
        'time.com',
        'npr.org'
    ]
    
    url_lower = url.lower()
    return any(domain in url_lower for domain in news_domains)


def validate_and_parse(url: str) -> dict:
    """
    Validate URL and return parsed information
    
    Args:
        url: URL to validate and parse
        
    Returns:
        Dictionary with validation results and parsed data
    """
    result = {
        'valid': False,
        'normalized_url': None,
        'platform': None,
        'error': None
    }
    
    # Normalize first
    try:
        normalized = normalize_url(url)
    except Exception as e:
        result['error'] = f"Invalid URL format: {str(e)}"
        return result
    
    # Validate
    if not is_valid_url(normalized):
        result['error'] = "Invalid URL format"
        return result
    
    result['valid'] = True
    result['normalized_url'] = normalized
    
    return result


# Test function for validation
if __name__ == "__main__":
    # Test YouTube URL validation
    test_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://www.youtube.com/shorts/dQw4w9WgXcQ",
        "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://www.youtube.com/embed/dQw4w9WgXcQ",
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=10s",
        "https://www.youtube.com/live/dQw4w9WgXcQ",
    ]
    
    print("Testing YouTube URL validation:")
    for url in test_urls:
        video_id = extract_video_id_youtube(url)
        print(f"  {url}")
        print(f"    → Video ID: {video_id}")
        print(f"    → Valid: {validate_youtube_url(url)}")
        print()