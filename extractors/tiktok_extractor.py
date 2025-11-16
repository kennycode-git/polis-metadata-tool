"""
TikTok Extractor - Subprocess Bridge (Phase 2 Enhanced)
Calls TWO standalone scraper scripts:
1. tiktok_post_standalone.py - extracts post data (RAW)
2. tiktok_op_scraper.py - extracts profile data (RAW)
Combines and formats into dual-output structure: post data + OP data
"""
from typing import Dict, Tuple
import subprocess
import json
import os
import sys
import time
import random
import string
from datetime import datetime

try:
    from .base_extractor import BaseExtractor
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from extractors.base_extractor import BaseExtractor


class TikTokExtractor(BaseExtractor):
    """
    Extract metadata from TikTok videos using two external subprocesses
    
    Phase 2: Returns dual output structure:
    - post: Post data with all metrics
    - op: Original Poster (user profile) data
    
    This bypasses Streamlit's async/threading issues by running
    scrapers in completely separate Python processes
    """

    def extract(self) -> Tuple[Dict, Dict]:
        """Override extract() to handle TikTok's dual-output structure"""
        try:
            # Validate URL first
            if not self.validate_url():
                error_data = {
                    'extraction_status': 'failed',
                    'error_message': 'Invalid URL format for this platform',
                    'url': self.url,
                    'platform': self.get_platform_name()
                }
                return (error_data, {})
            
            # Rate limiting
            from config.settings import RATE_LIMIT_DELAY
            time.sleep(RATE_LIMIT_DELAY)
            
            # Get dual structure from extract_metadata
            # This returns {'post': {...}, 'op': {...}}
            result = self.extract_metadata()
            
            # Check if it's an error from fallback
            if 'error' in result and 'post' not in result:
                error_data = {
                    'extraction_status': 'failed',
                    'error_message': result.get('error', 'Unknown error'),
                    'url': self.url,
                    'platform': self.get_platform_name()
                }
                return (error_data, {})
            
            # Extract post and op from dual structure
            post_data = result.get('post', {})
            op_data = result.get('op', {})
            
            # Add success status if not already present
            if 'extraction_status' not in post_data:
                post_data['extraction_status'] = 'success'
            
            # Return the tuple as expected by BaseExtractor
            return (post_data, op_data)
            
        except Exception as e:
            print(f"  ⚠ TikTok extraction error: {e}")
            import traceback
            traceback.print_exc()
            
            error_data = {
                'extraction_status': 'failed',
                'error_message': str(e),
                'url': self.url,
                'platform': self.get_platform_name()
            }
            return (error_data, {})
        
    def get_platform_name(self) -> str:
        return 'tiktok'
    
    def validate_url(self) -> bool:
        """Validate TikTok URL"""
        import re
        
        try:
            # Pattern for standard TikTok URLs
            standard_pattern = r'tiktok\.com/@[\w.-]+/video/(\d+)'
            match = re.search(standard_pattern, self.url)
            
            if match:
                self.video_id = match.group(1)
                return True
            
            # Pattern for short URLs (vm.tiktok.com)
            short_pattern = r'vm\.tiktok\.com/([A-Za-z0-9]+)'
            match = re.search(short_pattern, self.url)
            
            if match:
                self.video_id = None
                self.short_code = match.group(1)
                return True
            
            # Pattern for vt.tiktok.com short URLs
            vt_pattern = r'vt\.tiktok\.com/([A-Za-z0-9]+)'
            match = re.search(vt_pattern, self.url)
            
            if match:
                self.video_id = None
                self.short_code = match.group(1)
                return True
            
            return False
            
        except Exception as e:
            print(f"DEBUG: URL validation error: {e}")
            return False
    
    def extract_metadata(self) -> Dict:
        """
        Extract metadata by calling TWO external scraper scripts
        
        Returns dual structure:
        {
            'post': {...post data...},
            'op': {...user profile data...}
        }
        """
        
        print(f"\nDEBUG - TikTok Extraction (Phase 2 - Dual Scraper) for: {self.url}")
        print("  Step 1: Extracting POST data (RAW format)...")
        print("  Step 2: Extracting PROFILE data (RAW format)...")
        print("  Step 3: Combining & formatting to Phase 2 structure...\n")
        
        # ==== STEP 1: Extract POST data (RAW) ====
        post_data_raw = self._extract_post_data()
        
        if not post_data_raw or 'error' in post_data_raw:
            print("  ⚠ POST extraction failed, using fallback")
            return self._fallback_minimal()
        
        print(f"  ✓ POST data extracted (RAW)")
        print(f"    - Views: {post_data_raw.get('views')}")
        print(f"    - Likes: {post_data_raw.get('likes')}")
        print(f"    - Author: {post_data_raw.get('author_id')}")
        
        # Wait between operations (mimicking separate runs)
        print("\n  Waiting 3 seconds between operations...")
        time.sleep(3)
        
        # ==== STEP 2: Extract PROFILE data (RAW) ====
        # Get username from post data
        import re
        username = post_data_raw.get('author_id')
        if not username:
            # Fallback: extract from URL
            match = re.search(r'tiktok\.com/@([\w.-]+)/video', self.url)
            if match:
                username = match.group(1)
            else:
                username = 'Unknown'
        
        print(f"\n  Extracting profile for @{username}...")
        profile_data_raw = self._extract_profile_data(username)
        
        if profile_data_raw and not profile_data_raw.get('error'):
            print(f"  ✓ PROFILE data extracted (RAW)")
            print(f"    - Followers: {profile_data_raw.get('followers')}")
            print(f"    - Following: {profile_data_raw.get('following')}")
            print(f"    - Videos: {profile_data_raw.get('video_count')}")
        else:
            print(f"  ⚠ PROFILE extraction failed (will use nulls)")
            profile_data_raw = None
        
        # ==== STEP 3: Format into Phase 2 structure ====
        print("\n  Building Phase 2 output structure...")
        final_output = self._build_phase2_structure(post_data_raw, profile_data_raw, username)
        
        print(f"  ✓ Complete!")
        print(f"    - Post ID: {final_output['post']['Post_ID']}")
        print(f"    - OP ID: {final_output['op']['OP_ID']}")
        print(f"    - Post Views: {final_output['post']['Post_views']}")
        print(f"    - OP Followers: {final_output['op']['OP_followers']}")
        
        return final_output
    
    def _extract_post_data(self):
        """Call tiktok_post_standalone.py to extract post data (RAW format)"""
        try:
            # Find the post scraper script
            script_path = self._find_script('tiktok_post_standalone.py')
            
            if not script_path:
                print("  ⚠ tiktok_post_standalone.py not found")
                return None
            
            print(f"  Found post scraper at: {script_path}")
            
            # Call the script
            result = subprocess.run(
                [sys.executable, script_path, self.url],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Forward stderr logs
            if result.stderr:
                for line in result.stderr.split('\n'):
                    if line.strip():
                        print(f"    [POST] {line}")
            
            if result.returncode != 0:
                print(f"  ⚠ Post scraper failed with code {result.returncode}")
                return None
            
            # Parse JSON output (RAW format)
            data = json.loads(result.stdout)
            
            if 'error' in data:
                print(f"  ⚠ Post scraper error: {data['error']}")
                return None
            
            return data
            
        except subprocess.TimeoutExpired:
            print("  ⚠ Post scraper timeout (30s)")
            return None
        except json.JSONDecodeError as e:
            print(f"  ⚠ Failed to parse post scraper output: {e}")
            return None
        except Exception as e:
            print(f"  ⚠ Post scraper error: {e}")
            return None
    
    def _extract_profile_data(self, username):
        """Call tiktok_op_scraper.py to extract profile data (RAW format)"""
        try:
            # Find the profile scraper script
            script_path = self._find_script('tiktok_op_standalone.py')
            
            if not script_path:
                print("  ⚠ tiktok_op_standalone.py not found")
                return None
            
            print(f"  Found profile scraper at: {script_path}")
            
            # Call the script with username
            result = subprocess.run(
                [sys.executable, script_path, username],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Forward stderr logs
            if result.stderr:
                for line in result.stderr.split('\n'):
                    if line.strip():
                        print(f"    [PROFILE] {line}")
            
            if result.returncode != 0:
                print(f"  ⚠ Profile scraper failed with code {result.returncode}")
                return None
            
            # Parse JSON output (RAW format)
            data = json.loads(result.stdout)
            
            if 'error' in data:
                print(f"  ⚠ Profile scraper error: {data['error']}")
                return None
            
            return data
            
        except subprocess.TimeoutExpired:
            print("  ⚠ Profile scraper timeout (30s)")
            return None
        except json.JSONDecodeError as e:
            print(f"  ⚠ Failed to parse profile scraper output: {e}")
            return None
        except Exception as e:
            print(f"  ⚠ Profile scraper error: {e}")
            return None
    
    def _build_phase2_structure(self, post_raw, profile_raw, username):
        """
        Build the final Phase 2 dual post/op structure from RAW data
        
        Args:
            post_raw: RAW post data {'views': 226, 'likes': 8, ...}
            profile_raw: RAW profile data {'followers': 3328, ...}
            username: Username string
            
        Returns:
            {'post': {...}, 'op': {...}}
        """
        
        # Generate IDs
        post_id = self._generate_post_id()
        op_id = self._generate_op_id()
        
        # Detect language
        language = self._detect_language(
            post_raw.get('content') or post_raw.get('title')
        )
        
        # Calculate engagement rate
        engagement_rate = None
        if post_raw.get('views') and post_raw.get('views') > 0:
            likes = post_raw.get('likes') or 0
            comments = post_raw.get('comments') or 0
            shares = post_raw.get('shares') or 0
            
            if likes or comments or shares:
                engagements = likes + comments + shares
                engagement_rate = round((engagements / post_raw['views']) * 100, 2)
        
        # Build POST data (Phase 2 format with Post_ prefix)
        post_data = {
            'Post_ID': post_id,
            'Post_title': None,  # TikTok doesn't have titles
            'Post_caption': post_raw.get('content') or post_raw.get('title'),
            'Post_hashtags': post_raw.get('hashtags', []),
            'Post_type': 'video',
            'Post_date': post_raw.get('publish_date'),
            'Post_extracted_date': datetime.now().isoformat(),
            'Post_platform': 'tiktok',
            'Post_views': post_raw.get('views'),
            'Post_likes': post_raw.get('likes'),
            'Post_shares': post_raw.get('shares'),
            'Post_comments': post_raw.get('comments'),
            'Post_saves': post_raw.get('saves'), 
            'Post_reposts': None,
            'Post_engagement_rate': engagement_rate,
            'Post_url': self.url,
            'Post_language': language,
            'OP_username': username,
            'OP_ID': op_id
        }
        
        # Build OP data (Phase 2 format with OP_ prefix)
        op_data = {
            'OP_username': username,
            'OP_ID': op_id,
            'OP_bio': profile_raw.get('bio') if profile_raw else None,
            'OP_followers': profile_raw.get('followers') if profile_raw else None,
            'OP_following': profile_raw.get('following') if profile_raw else None,
            'OP_post': profile_raw.get('video_count') if profile_raw else None,
            'OP_platform': 'tiktok'
        }
        
        return {
            'post': post_data,
            'op': op_data
        }
    
    def _find_script(self, script_name):
        """Find a scraper script by name"""
        
        possible_paths = [
            # Same directory as this file
            os.path.join(os.path.dirname(__file__), script_name),
            # Parent directory
            os.path.join(os.path.dirname(os.path.dirname(__file__)), script_name),
            # Current working directory
            script_name,
            # Extractors directory
            os.path.join('extractors', script_name),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return os.path.abspath(path)
        
        return None
    
    def _generate_post_id(self):
        """Generate unique Post ID"""
        chars = string.ascii_lowercase + string.digits
        return f"po_{''.join(random.choices(chars, k=14))}"
    
    def _generate_op_id(self):
        """Generate unique OP ID"""
        chars = string.ascii_lowercase + string.digits
        return f"op_{''.join(random.choices(chars, k=14))}"
    
    def _detect_language(self, text):
        """Detect language from text (simple heuristic)"""
        if not text:
            return None
        
        try:
            sample = text[:200]
            if not sample.strip():
                return None
            
            ascii_count = sum(1 for c in sample if ord(c) < 128)
            total_count = len(sample)
            
            return 'en' if (ascii_count / total_count > 0.8) else 'other'
        except:
            return None
    
    def _fallback_minimal(self):
        """
        Fallback: Return minimal dual structure
        Try to at least get basic data from oembed
        """
        print("  Using minimal fallback...")
        
        import re
        
        # Try oembed for basic info
        basic_data = self._try_oembed()
        
        # Extract username from URL
        username = 'Unknown'
        match = re.search(r'tiktok\.com/@([\w.-]+)/video', self.url)
        if match:
            username = match.group(1)
        elif basic_data.get('author_id'):
            username = basic_data['author_id']
        
        post_id = self._generate_post_id()
        op_id = self._generate_op_id()
        
        return {
            'post': {
                'Post_ID': post_id,
                'Post_title': None,
                'Post_caption': basic_data.get('content') or basic_data.get('title'),
                'Post_hashtags': basic_data.get('hashtags', []),
                'Post_type': 'video',
                'Post_date': basic_data.get('publish_date') or 'N/A',
                'Post_extracted_date': datetime.now().isoformat(),
                'Post_platform': 'tiktok',
                'Post_views': basic_data.get('views'),
                'Post_likes': basic_data.get('likes'),
                'Post_shares': basic_data.get('shares'),
                'Post_comments': basic_data.get('comments'),
                'Post_saves': None,
                'Post_reposts': None,
                'Post_engagement_rate': None,
                'Post_url': self.url,
                'Post_language': None,
                'OP_username': username,
                'OP_ID': op_id
            },
            'op': {
                'OP_username': username,
                'OP_ID': op_id,
                'OP_bio': None,
                'OP_followers': None,
                'OP_following': None,
                'OP_post': None,
                'OP_platform': 'tiktok'
            },
            'fallback': True
        }
    
    def _try_oembed(self):
        """Try oembed API for basic fallback data"""
        try:
            import requests
            import re
            
            oembed_url = f"https://www.tiktok.com/oembed?url={self.url}"
            
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
            
            def extract_hashtags(text):
                if not text:
                    return []
                hashtags = re.findall(r'#(\w+)', text)
                return [f"#{tag}" for tag in hashtags[:10]]
            
            return {
                'title': data.get('title', 'No title found'),
                'author': data.get('author_name', 'Unknown'),
                'author_id': author_id,
                'content': data.get('title', ''),
                'publish_date': 'N/A',
                'views': None,
                'likes': None,
                'comments': None,
                'shares': None,
                'hashtags': extract_hashtags(data.get('title', ''))
            }
            
        except Exception as e:
            print(f"  ⚠ oembed also failed: {e}")
            return {
                'title': 'No title found',
                'author': 'Unknown',
                'author_id': None,
                'content': '',
                'publish_date': 'N/A',
                'hashtags': []
            }