#!/usr/bin/env python3
"""
TikTok Profile Scraper
Extracts user profile metadata only
"""

import sys
import json
import re

try:
    import requests
except ImportError:
    print(json.dumps({"error": "requests not installed"}))
    sys.exit(1)

def log(*args):
    print(*args, file=sys.stderr)

def scrape_profile(username):
    """Scrape TikTok profile metadata for given username"""
    
    log(f"[PROFILE] Scraping profile for @{username}")
    
    # Build profile URL
    profile_url = f"https://www.tiktok.com/@{username}"
    
    # Headers
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-GB,en;q=0.9',
        'Connection': 'keep-alive',
        'Referer': 'https://www.tiktok.com/',
    }
    
    try:
        # Create fresh session
        session = requests.Session()
        session.headers.update(headers)
        
        # Fetch profile page
        log(f"[PROFILE] Fetching: {profile_url}")
        response = session.get(profile_url, timeout=15, allow_redirects=True)
        response.raise_for_status()
        html = response.text
        log(f"[PROFILE] HTML length: {len(html)}")
        
        # Parse HTML
        profile_data = parse_profile_html(html, username)
        
        if profile_data:
            log(f"[PROFILE] Success! Followers: {profile_data.get('followers')}, Posts: {profile_data.get('video_count')}")
        else:
            log("[PROFILE] No profile data extracted")
        
        return profile_data
        
    except Exception as e:
        log(f"[PROFILE] Error: {e}")
        return {
            'username': username,
            'error': str(e)
        }


def parse_profile_html(html, username):
    """Parse HTML to extract profile metadata"""
    
    profile_data = {
        'username': username,
        'bio': None,
        'followers': None,
        'following': None,
        'video_count': None,
        'extraction_method': None
    }
    
    # Try SIGI_STATE first (often has profile data)
    sigi_pattern = r'<script[^>]*>window\[\'SIGI_STATE\'\]\s*=\s*(\{.+?\});?</script>'
    match = re.search(sigi_pattern, html, re.DOTALL)
    
    if match:
        try:
            data = json.loads(match.group(1))
            log("[PROFILE] Found SIGI_STATE")
            
            # Look for UserModule
            if 'UserModule' in data and 'users' in data['UserModule']:
                for user_id, user_data in data['UserModule']['users'].items():
                    if isinstance(user_data, dict):
                        stats = user_data.get('stats', {})
                        
                        profile_data.update({
                            'bio': user_data.get('signature', ''),
                            'followers': safe_int(stats.get('followerCount')),
                            'following': safe_int(stats.get('followingCount')),
                            'video_count': safe_int(stats.get('videoCount')),
                            'extraction_method': 'SIGI_STATE'
                        })
                        
                        log(f"[PROFILE] SIGI_STATE success")
                        return profile_data
        except Exception as e:
            log(f"[PROFILE] SIGI_STATE parse error: {e}")
    
    # Try UNIVERSAL_DATA
    universal_pattern = r'<script[^>]*id=["\']__UNIVERSAL_DATA_FOR_REHYDRATION__["\'][^>]*>(.*?)</script>'
    match = re.search(universal_pattern, html, re.DOTALL)
    
    if match:
        try:
            data = json.loads(match.group(1))
            log("[PROFILE] Found UNIVERSAL_DATA")
            
            if '__DEFAULT_SCOPE__' in data:
                default_scope = data['__DEFAULT_SCOPE__']
                
                if 'webapp.user-detail' in default_scope:
                    user_detail = default_scope['webapp.user-detail']
                    if 'userInfo' in user_detail:
                        user_data = user_detail['userInfo'].get('user', {})
                        stats = user_detail['userInfo'].get('stats', {})
                        
                        profile_data.update({
                            'bio': user_data.get('signature', ''),
                            'followers': safe_int(stats.get('followerCount')),
                            'following': safe_int(stats.get('followingCount')),
                            'video_count': safe_int(stats.get('videoCount')),
                            'extraction_method': 'UNIVERSAL_DATA'
                        })
                        
                        log(f"[PROFILE] UNIVERSAL_DATA success")
                        return profile_data
        except Exception as e:
            log(f"[PROFILE] UNIVERSAL_DATA parse error: {e}")
    
    log("[PROFILE] Could not extract profile data")
    return profile_data


def safe_int(value):
    """Safely convert to int"""
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
       print(json.dumps({"error": "No username provided"}))
       sys.exit(1)
    
    username = sys.argv[1].lstrip('@')  # Remove @ if provided
    result = scrape_profile(username)
    
    # Output JSON to stdout
    print(json.dumps(result, indent=2))