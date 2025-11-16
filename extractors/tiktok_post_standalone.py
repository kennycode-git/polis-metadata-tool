#!/usr/bin/env python3
"""
TikTok Post Scraper
Extracts video post metadata only (RAW format)
"""

import sys
import json
import re
from datetime import datetime

try:
    import requests
except ImportError:
    print(json.dumps({"error": "requests not installed"}))
    sys.exit(1)

def log(*args):
    print(*args, file=sys.stderr)

def scrape_tiktok(url):
    """Scrape TikTok video metadata - returns RAW format"""
    
    # Resolve mobile URLs to desktop version
    if 'm.tiktok.com' in url:
        url = url.replace('m.tiktok.com', 'www.tiktok.com')
        log(f"[POST] Converted mobile URL to desktop: {url}")

    # Check if it's a short URL (vm.tiktok.com or vt.tiktok.com)
    if 'vm.tiktok.com' in url or 'vt.tiktok.com' in url:
        try:
            log("[POST] Resolving short URL...")
            response = requests.head(url, allow_redirects=True, timeout=10)
            resolved_url = response.url
            log(f"[POST] Resolved to: {resolved_url}")
            url = resolved_url
        except Exception as e:
            log(f"[POST] Failed to resolve short URL: {e}")
            try:
                response = requests.get(url, allow_redirects=True, timeout=10)
                url = response.url
                log(f"[POST] Resolved with GET: {url}")
            except:
                return {"error": f"Could not resolve short URL: {url}"}
    
    # Validate URL and extract video ID
    standard_pattern = r'tiktok\.com/@[\w.-]+/video/(\d+)'
    match = re.search(standard_pattern, url)
    
    if not match:
        return {"error": f"Invalid TikTok URL after resolution: {url}"}
    
    video_id = match.group(1)
    log(f"[POST] Video ID: {video_id}")
    
    # Strategy: Try fetching with good headers
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
    }
    
    try:
        # Create session
        session = requests.Session()
        session.headers.update(headers)
        
        # Fetch page
        response = session.get(url, timeout=15, allow_redirects=True)
        response.raise_for_status()
        html = response.text
        log(f"[POST] HTML length: {len(html)}")
        
        # Check if we got full HTML
        if len(html) < 100000:
            # Try alternative: visit homepage first
            log("[POST] Short HTML, warming up with homepage...")
            session.get("https://www.tiktok.com", timeout=10)
            import time
            time.sleep(2)
            
            headers['Referer'] = 'https://www.tiktok.com/'
            headers['Sec-Fetch-Site'] = 'same-origin'
            session.headers.update(headers)
            
            response = session.get(url, timeout=15, allow_redirects=True)
            html = response.text
            log(f"[POST] Retry HTML length: {len(html)}")
        
        # Parse HTML
        metadata = parse_html(html, url)
        log(f"[POST] Extraction method: {metadata.get('extraction_method')}")
        log(f"[POST] Views: {metadata.get('views')}, Likes: {metadata.get('likes')}")
        
        # If no engagement metrics, try oembed as fallback
        if not any([metadata.get('views'), metadata.get('likes')]):
            log("[POST] No metrics, trying oembed fallback...")
            oembed_data = get_oembed(url)
            # Merge oembed data
            for key in ['title', 'author', 'author_id']:
                if not metadata.get(key) and oembed_data.get(key):
                    metadata[key] = oembed_data[key]
        
        return metadata
        
    except Exception as e:
        log(f"[POST] Exception: {e}")
        # Fallback to oembed
        return get_oembed(url)


def parse_html(html, url):
    """Parse HTML to extract metadata - returns RAW format"""
    metadata = {
        'url': url,
        'title': None,
        'author': None,
        'author_id': None,
        'content': None,
        'publish_date': 'N/A',
        'views': None,
        'likes': None,
        'comments': None,
        'shares': None,
        'saves': None,
        'hashtags': [],
        'media_urls': [],
        'extraction_method': None
    }
    
    # Try UNIVERSAL_DATA
    universal_pattern = r'<script[^>]*id=["\']__UNIVERSAL_DATA_FOR_REHYDRATION__["\'][^>]*>(.*?)</script>'
    match = re.search(universal_pattern, html, re.DOTALL)
    
    if match:
        try:
            data = json.loads(match.group(1))
            
            if '__DEFAULT_SCOPE__' in data:
                default_scope = data['__DEFAULT_SCOPE__']
                
                if 'webapp.video-detail' in default_scope:
                    video_detail = default_scope['webapp.video-detail']
                    if 'itemInfo' in video_detail and 'itemStruct' in video_detail['itemInfo']:
                        video_data = video_detail['itemInfo']['itemStruct']
                        
                        desc = video_data.get('desc', '')
                        author_data = video_data.get('author', {})
                        stats = video_data.get('stats', {})

                        metadata.update({
                            'title': desc or 'No title found',
                            'author': author_data.get('nickname', 'Unknown'),
                            'author_id': author_data.get('uniqueId', None),
                            'content': desc,
                            'publish_date': format_timestamp(video_data.get('createTime')),
                            'views': safe_int(stats.get('playCount')),
                            'likes': safe_int(stats.get('diggCount', 0 )),
                            'comments': safe_int(stats.get('commentCount', 0)),
                            'shares': safe_int(stats.get('shareCount', 0)),
                            'saves': safe_int(stats.get('collectCount', 0)), 
                            'hashtags': extract_hashtags(desc),
                            'extraction_method': 'UNIVERSAL_DATA'
                        })
                        
                        if video_data.get('video', {}).get('cover'):
                            metadata['media_urls'].append(video_data['video']['cover'])

                        return metadata
        except:
            pass
    
    # Try SIGI_STATE
    sigi_patterns = [
        r'<script[^>]*>window\[\'SIGI_STATE\'\]\s*=\s*(\{.+?\});?</script>',
        r'SIGI_STATE\s*=\s*(\{.+?\});',
    ]
    
    for pattern in sigi_patterns:
        match = re.search(pattern, html, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                
                if 'ItemModule' in data:
                    for item_id, item_data in data['ItemModule'].items():
                        if isinstance(item_data, dict) and 'stats' in item_data:
                            stats = item_data.get('stats', {})
                            author_data = item_data.get('author', {})
                            desc = item_data.get('desc', '')
                            
                            metadata.update({
                                'title': desc or 'No title found',
                                'author': author_data.get('nickname', 'Unknown'),
                                'author_id': author_data.get('uniqueId', None),
                                'content': desc,
                                'publish_date': format_timestamp(item_data.get('createTime')),
                                'views': safe_int(stats.get('playCount')),
                                'likes': safe_int(stats.get('diggCount', 0 )),
                                'comments': safe_int(stats.get('commentCount', 0)),
                                'shares': safe_int(stats.get('shareCount', 0)),
                                'saves': safe_int(stats.get('collectCount', 0)),
                                'hashtags': extract_hashtags(desc),
                                'extraction_method': 'SIGI_STATE'
                            })
                            
                            return metadata
            except:
                continue
 
    # Try JSON-LD
    jsonld_pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
    jsonld_matches = re.findall(jsonld_pattern, html, re.DOTALL)
    
    for jsonld_text in jsonld_matches:
        try:
            jsonld_data = json.loads(jsonld_text)
            if jsonld_data.get('@type') == 'VideoObject':
                author_name = 'Unknown'
                author_id = None
                
                if isinstance(jsonld_data.get('author'), dict):
                    author_name = jsonld_data['author'].get('name', 'Unknown')
                    author_id = jsonld_data['author'].get('alternateName', None)
                
                interaction_stats = jsonld_data.get('interactionStatistic', [])
                views = None
                if isinstance(interaction_stats, list) and interaction_stats:
                    views = safe_int(interaction_stats[0].get('userInteractionCount'))
                
                metadata.update({
                    'title': jsonld_data.get('description', 'No title found'),
                    'author': author_name,
                    'author_id': author_id,
                    'content': jsonld_data.get('description', ''),
                    'publish_date': jsonld_data.get('uploadDate', 'N/A'),
                    'views': views,
                    'comments': safe_int(jsonld_data.get('commentCount')),
                    'hashtags': extract_hashtags(jsonld_data.get('description', '')),
                    'extraction_method': 'JSON-LD'
                })
                
                if jsonld_data.get('thumbnailUrl'):
                    metadata['media_urls'].append(jsonld_data['thumbnailUrl'])
                
                return metadata
        except:
            continue
    
    return metadata


def get_oembed(url):
    """Fallback: Get data from oembed API - returns RAW format"""
    try:
        oembed_url = f"https://www.tiktok.com/oembed?url={url}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(oembed_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        author_id = None
        if data.get('author_url'):
            parts = data['author_url'].split('@')
            if len(parts) > 1:
                author_id = parts[-1].rstrip('/')
        
        return {
            'url': url,
            'title': data.get('title', 'No title found'),
            'author': data.get('author_name', 'Unknown'),
            'author_id': author_id,
            'content': data.get('title', ''),
            'publish_date': 'N/A',
            'views': None,
            'likes': None,
            'comments': None,
            'shares': None,
            'hashtags': extract_hashtags(data.get('title', '')),
            'media_urls': [data.get('thumbnail_url', '')] if data.get('thumbnail_url') else [],
            'extraction_method': 'oembed'
        }
    except Exception as e:
        return {
            'url': url,
            'error': f"All extraction methods failed: {str(e)}"
        }


def extract_hashtags(text):
    """Extract hashtags from text"""
    if not text:
        return []
    hashtags = re.findall(r'#(\w+)', text)
    return [f"#{tag}" for tag in hashtags[:10]]


def safe_int(value):
    """Safely convert to int"""
    if value is None:
        return None
    if value == 0:  # Explicitly handle 0
        return 0
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def format_timestamp(timestamp):
    """Convert Unix timestamp to ISO format"""
    if not timestamp:
        return 'N/A'
    try:
        return datetime.fromtimestamp(int(timestamp)).isoformat()
    except:
        return 'N/A'


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No URL provided"}))
        sys.exit(1)
    
    url = sys.argv[1]
    result = scrape_tiktok(url)
    
    # Output JSON to stdout
    print(json.dumps(result, indent=2))