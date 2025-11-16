"""
YouTube metadata extractor with dual-CSV output structure
Supports multiple URL formats: standard, shorts, embeds, mobile, live streams
"""
import json       # For decoding the API error response content
import time       # For backoff delay (sleep between retries)
import subprocess
import os
import sys
import string
import hashlib
import random
from typing import Dict, Tuple, Optional
from datetime import datetime

# Import validators - try multiple paths for flexibility
try:
    from utils.validators import extract_video_id_youtube
except ImportError:
    try:
        from validators import extract_video_id_youtube
    except ImportError:
        # Fallback inline implementation
        import re
        def extract_video_id_youtube(url: str) -> Optional[str]:
            """Extract YouTube video ID from various URL formats"""
            url = url.strip()
            patterns = [
                r'youtu\.be/([a-zA-Z0-9_-]{11})',
                r'youtube\.com/shorts/([a-zA-Z0-9_-]{11})',
                r'youtube\.com/embed/([a-zA-Z0-9_-]{11})',
                r'youtube\.com/v/([a-zA-Z0-9_-]{11})',
                r'[?&]v=([a-zA-Z0-9_-]{11})',
                r'youtube\.com/live/([a-zA-Z0-9_-]{11})',
                r'attribution_link.*?[?&]v=([a-zA-Z0-9_-]{11})'
            ]
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    return match.group(1)
            return None

from config.settings import YOUTUBE_API_KEY

try:
    from .base_extractor import BaseExtractor
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from extractors.base_extractor import BaseExtractor

try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    YOUTUBE_AVAILABLE = True
except ImportError:
    YOUTUBE_AVAILABLE = False


class YouTubeExtractor(BaseExtractor):
    """
    Extract metadata from YouTube videos using official API
    Returns separate post_data and op_data for dual-CSV structure
    
    Supports URL formats:
    - Standard: https://www.youtube.com/watch?v=VIDEO_ID
    - Shorts: https://www.youtube.com/shorts/VIDEO_ID
    - Short links: https://youtu.be/VIDEO_ID
    - Embeds: https://www.youtube.com/embed/VIDEO_ID
    - Mobile: https://m.youtube.com/watch?v=VIDEO_ID
    - Live streams: https://www.youtube.com/live/VIDEO_ID
    - With timestamps: https://www.youtube.com/watch?v=VIDEO_ID&t=123s
    """
    
    def get_platform_name(self) -> str:
        return 'youtube'
    
    def validate_url(self) -> bool:
        """Validate YouTube URL and extract video ID (supports all YouTube formats)"""
        video_id = extract_video_id_youtube(self.url)
        if video_id:
            self.video_id = video_id
            print(f"✅ Extracted YouTube video ID: {video_id}")
            return True
        print(f"❌ Could not extract video ID from: {self.url}")
        return False
    
    def _get_channel_data(self, channel_id: str) -> Optional[Dict]:
        """
        Fetch channel statistics and info for OP data
        
        Args:
            channel_id: YouTube channel ID
            
        Returns:
            Dictionary with channel snippet and statistics, or None if error
        """
        try:
            youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
            request = youtube.channels().list(
                part='snippet,statistics',
                id=channel_id
            )
            response = request.execute()
            
            if not response.get('items'):
                return None
                
            channel = response['items'][0]
            return {
                'snippet': channel.get('snippet', {}),
                'statistics': channel.get('statistics', {})
            }
            
        except HttpError as e:
            # Log error but don't fail the entire extraction
            print(f"Warning: Could not fetch channel data for {channel_id}: {e}")
            return None
        except Exception as e:
            print(f"Warning: Unexpected error fetching channel data: {e}")
            return None
    
    def extract_metadata(self) -> Dict:
        """
        Extract metadata using YouTube Data API v3
        
        Returns:
            Tuple of (post_data, op_data) dictionaries for dual-CSV output
        """
        
        if not YOUTUBE_AVAILABLE:
            raise Exception("YouTube API client not installed. Run: pip install google-api-python-client")
        
        if not YOUTUBE_API_KEY:
            raise Exception("YouTube API key not configured. Please set YOUTUBE_API_KEY in environment.")
        
        try:
            # Build YouTube API client
            youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
            
            # Request video details
            request = youtube.videos().list(
                part='snippet,statistics,contentDetails',
                id=self.video_id
            )
            response = request.execute()
            
            if not response.get('items'):
                raise Exception("Video not found or is private")
            
            video = response['items'][0]
            snippet = video.get('snippet', {})
            statistics = video.get('statistics', {})
            
            # Generate IDs
            post_id = self._generate_post_id()
            channel_id = snippet.get('channelId')
            # Use channel ID as basis for OP_ID so same channel always gets same ID
            op_id = self._generate_op_id(channel_id) if channel_id else self._generate_op_id()
            
            # Get channel data for OP info
            channel_data = self._get_channel_data(channel_id) if channel_id else None
            channel_snippet = channel_data['snippet'] if channel_data else {}
            channel_stats = channel_data['statistics'] if channel_data else {}
            
            # Extract hashtags from tags and description
            tags = snippet.get('tags', [])
            description = snippet.get('description', '')
            hashtags = self._extract_hashtags(tags, description)
            
            # Calculate engagement metrics
            views = int(statistics.get('viewCount', 0))
            likes = int(statistics.get('likeCount', 0))
            comments = int(statistics.get('commentCount', 0))
            
            # Engagement rate = (likes + comments) / views * 100
            engagement_rate = ((likes + comments) / views * 100) if views > 0 else 0.0
            
            # Build Post Data dictionary
            post_data = {
                'Post_ID': post_id,
                'Post_title': snippet.get('title') or None,
                'Post_caption': snippet.get('description') or None,
                'Post_hashtags': ', '.join(hashtags) if hashtags else None,
                'Post_type': 'video',
                'Post_date': snippet.get('publishedAt') or None,
                'Post_extracted_date': datetime.now().isoformat(),
                'Post_platform': 'youtube',
                'Post_views': views if views > 0 else None,
                'Post_likes': likes if likes > 0 else None,
                'Post_shares': None,  # YouTube API doesn't provide share count
                'Post_comments': comments if comments > 0 else None,
                'Post_saves': None,  # Not available on YouTube
                'Post_reposts': None,  # Not available on YouTube
                'Post_engagement_rate': round(engagement_rate, 2) if engagement_rate > 0 else None,
                'Post_url': f"https://www.youtube.com/watch?v={self.video_id}",
                'Post_language': snippet.get('defaultLanguage') or snippet.get('defaultAudioLanguage') or 'unknown',
                'OP_username': snippet.get('channelTitle') or None,
                'OP_ID': op_id
            }
            
            # Build OP (Original Poster) Data dictionary
            op_data = {
                'OP_username': snippet.get('channelTitle') or None,
                'OP_ID': op_id,
                'OP_bio': channel_snippet.get('description') or None,
                'OP_followers': int(channel_stats.get('subscriberCount', 0)) if channel_stats.get('subscriberCount') else None,
                'OP_following': None,  # YouTube doesn't provide subscription count
                'OP_post': int(channel_stats.get('videoCount', 0)) if channel_stats.get('videoCount') else None,
                'OP_platform': 'youtube'
            }


            # 🔍 DEBUG LOGS
            print("\n[DEBUG][YouTubeExtractor] channel_id:", channel_id)
            print("[DEBUG][YouTubeExtractor] channel_snippet:", channel_snippet)
            print("[DEBUG][YouTubeExtractor] channel_stats:", channel_stats)
            print("[DEBUG][YouTubeExtractor] op_data:", op_data)
            print("[DEBUG][YouTubeExtractor] post_data keys:", list(post_data.keys()))
            return {
                'post': post_data,
                'op': op_data
             }
        
        except HttpError as e:
            try:
                err = json.loads(e.content.decode('utf-8'))
                reason = err['error']['errors'][0].get('reason')
                message = err['error'].get('message')
            except Exception:
                reason = None
                message = str(e)

            # Optional: back off only for rate limit reasons
            if e.resp.status == 403 and reason in {'rateLimitExceeded', 'userRateLimitExceeded'}:
                time.sleep(2)  # simple backoff
                # Could implement retry logic here

            raise Exception(f"YouTube API 403: {reason or 'forbidden'} — {message}")
        
    def extract(self) -> Tuple[Dict, Dict]:

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

            # Call our metadata method (returns {'post': ..., 'op': ...})
            result = self.extract_metadata()

            # If you ever return an error dict from extract_metadata, handle it:
            if 'error' in result and 'post' not in result:
                error_data = {
                    'extraction_status': 'failed',
                    'error_message': result.get('error', 'Unknown error'),
                    'url': self.url,
                    'platform': self.get_platform_name()
                }
                return (error_data, {})

            post_data = result.get('post', {})
            op_data = result.get('op', {})

            # Mark success if not already marked
            if 'extraction_status' not in post_data:
                post_data['extraction_status'] = 'success'

            return (post_data, op_data)

        except Exception as e:
            print(f"  ⚠ YouTube extraction error: {e}")
            import traceback
            traceback.print_exc()

            error_data = {
                'extraction_status': 'failed',
                'error_message': str(e),
                'url': self.url,
                'platform': self.get_platform_name()
            }
            return (error_data, {})


    def _extract_hashtags(self, tags: list, description: str = '') -> list:
        """
        Extract hashtags from video tags and description
        
        Args:
            tags: List of video tags from YouTube API
            description: Video description text
            
        Returns:
            List of hashtags in #format
        """
        hashtags = []
        
        # Convert tags to hashtag format
        if tags:
            for tag in tags:
                # Clean and format tag
                clean_tag = tag.replace(' ', '').strip()
                if clean_tag:
                    hashtags.append(f"#{clean_tag}")
        
        # Extract hashtags from description (words starting with #)
        if description:
            words = description.split()
            for word in words:
                if word.startswith('#') and len(word) > 1:
                    # Clean up punctuation
                    clean_hashtag = word.rstrip('.,!?;:')
                    if clean_hashtag not in hashtags:
                        hashtags.append(clean_hashtag)
        
        return hashtags
    
    def _generate_post_id(self):
        """Generate unique Post ID"""
        chars = string.ascii_lowercase + string.digits
        return f"po_{''.join(random.choices(chars, k=14))}"
    
    def _generate_op_id(self, channel_id: Optional[str] = None) -> str:
        """
        Generate OP ID.
        If channel_id is provided, generate a deterministic ID from it
        so the same channel always gets the same OP_ID.
        """
        if channel_id:
            # Deterministic based on channel_id
            digest = hashlib.md5(channel_id.encode('utf-8')).hexdigest()[:14]
            return f"op_{digest}"
        
        # Fallback: random ID
        chars = string.ascii_lowercase + string.digits
        return f"op_{''.join(random.choices(chars, k=14))}"