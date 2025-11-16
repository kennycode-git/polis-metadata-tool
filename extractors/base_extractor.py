"""
Base extractor class - template for all platform extractors

PHASE 1 COMPLETE: Enhanced with database alignment features
- ID generation (Post_ID, OP_ID)
- Language detection
- Post type detection
- Dual CSV data formatting
- Tuple return structure
"""
from abc import ABC, abstractmethod
from typing import Dict, Optional, Tuple
from datetime import datetime
import time
import random
import string
from config.settings import RATE_LIMIT_DELAY


class BaseExtractor(ABC):
    """
    Abstract base class for all metadata extractors
    
    All platform-specific extractors should inherit from this class
    and implement the required methods.
    
    Phase 1 Updates:
    - Generates unique Post_ID and OP_ID
    - Detects language from content
    - Detects post type (video/image/text/article)
    - Formats data for dual CSV output (Posts + OPs)
    - Returns tuple: (post_data, op_data)
    """
    
    def __init__(self, url: str):
        """
        Initialize extractor with URL
        
        Args:
            url: The URL to extract metadata from
        """
        self.url = url
        self.metadata = {
            'url': url,
            'extraction_timestamp': datetime.now().isoformat(),
            'platform': self.get_platform_name(),
            'extraction_status': 'pending',
            'error_message': ''
        }
    
    # ==================== ABSTRACT METHODS ====================
    
    @abstractmethod
    def get_platform_name(self) -> str:
        """
        Return the platform identifier
        
        Returns:
            Platform name string (e.g., 'youtube', 'reddit', 'tiktok')
        """
        pass
    
    @abstractmethod
    def validate_url(self) -> bool:
        """
        Validate if URL is correct format for this platform
        
        Returns:
            Boolean indicating if URL is valid
        """
        pass
    
    @abstractmethod
    def extract_metadata(self) -> Dict:
        """
        Extract metadata from the URL
        
        This should return a dictionary with platform-specific fields.
        The base class will handle formatting into Post/OP structure.
        
        Returns:
            Dictionary containing extracted metadata
        """
        pass
    
    # ==================== PHASE 1: ID GENERATION ====================
    
    @staticmethod
    def generate_post_id(seed: str = None) -> str:
        """
        Generate unique Post ID for database tracking
        
        Format: po_<14 random lowercase + digits>
        Example: po_a3b7c9d2e5f8gh
        
        Collision risk: ~1 in 2.8 trillion (safe for CSV exports)
        
        Returns:
            Unique Post_ID string
        """
        if seed:
            # Deterministic ID from seed
            import hashlib
            hash_obj = hashlib.sha256(seed.encode())
            return f"po_{hash_obj.hexdigest()[:14].lower()}"
        else:
            # Random ID
            chars = string.ascii_lowercase + string.digits
            random_str = ''.join(random.choices(chars, k=14))
            return f"po_{random_str}"

    @staticmethod
    def generate_op_id(seed: str = None) -> str:
        """
        Generate unique OP (Original Poster) ID for database tracking
        
        Format: op_<14 random lowercase + digits>
        Example: op_k1m3n5p7q9r2st
        
        Collision risk: ~1 in 2.8 trillion (safe for CSV exports)
        
        Returns:
            Unique OP_ID string
        """
        if seed:
            # Deterministic ID from seed (ensures same author = same ID)
            import hashlib
            hash_obj = hashlib.sha256(seed.encode())
            return f"op_{hash_obj.hexdigest()[:14].lower()}"
        else:
            # Random ID
            chars = string.ascii_lowercase + string.digits
            random_str = ''.join(random.choices(chars, k=14))
            return f"op_{random_str}"
    
    # ==================== PHASE 1: LANGUAGE DETECTION ====================
    
    @staticmethod
    def detect_language(text: str) -> Optional[str]:
        """
        Detect language from text content
        
        Uses simple heuristic for now. Can be upgraded to langdetect library later.
        
        Args:
            text: Text to analyze
            
        Returns:
            Language code or None if detection fails
            - 'en' for English (ASCII characters)
            - 'other' for non-English (non-ASCII characters)
            - None if text is empty or detection fails
        """
        if not text or not isinstance(text, str):
            return None
        
        try:
            # Simple heuristic: check if text is primarily ASCII
            # If mostly ASCII characters, assume English
            # Otherwise, assume non-English
            
            # Take a sample of the text (first 200 chars is enough)
            sample = text[:200]
            
            if not sample.strip():
                return None
            
            # Count ASCII vs non-ASCII characters
            ascii_count = sum(1 for c in sample if ord(c) < 128)
            total_count = len(sample)
            
            # If more than 80% ASCII, consider it English
            if ascii_count / total_count > 0.8:
                return 'en'
            else:
                return 'other'
        
        except Exception as e:
            # If detection fails for any reason, return None
            return None
    
    # ==================== PHASE 1: POST TYPE DETECTION ====================
    
    def detect_post_type(self, metadata: dict) -> str:
        """
        Detect post type from metadata
        
        Logic varies by platform:
        - TikTok, YouTube: always 'video'
        - Reddit: detect from is_video, media_urls
        - News: always 'article'
        - Facebook: detect from content (if working)
        
        Args:
            metadata: Extracted metadata dictionary
            
        Returns:
            Post type string: 'video', 'image', 'text', 'article', 'link', or 'unknown'
        """
        platform = self.get_platform_name()
        
        # Platform-specific logic
        if platform in ['tiktok', 'youtube']:
            return 'video'
        
        if platform == 'news':
            return 'article'
        
        if platform == 'reddit':
            # Check various Reddit indicators
            if metadata.get('is_video'):
                return 'video'
            
            post_hint = metadata.get('post_hint', '')
            if post_hint == 'image':
                return 'image'
            if post_hint == 'link':
                return 'link'
            
            # If has media URLs but no text, likely image
            if metadata.get('media_urls') and not metadata.get('content'):
                return 'image'
            
            # If has selftext, it's a text post
            if metadata.get('content'):
                return 'text'
            
            return 'link'  # Default for Reddit
        
        if platform == 'facebook':
            # Would need more sophisticated detection
            # For now, return unknown
            return 'unknown'
        
        return 'unknown'
    
    # ==================== PHASE 1: CSV DATA FORMATTING ====================
    
    def format_post_csv_data(self, metadata: dict, post_id: str, op_id: str) -> dict:
        """
        Format extracted metadata into Post CSV structure
        
        Args:
            metadata: Raw extracted metadata
            post_id: Generated Post_ID
            op_id: Generated OP_ID
            
        Returns:
            Dictionary with all Post_ fields in correct structure
        """
        # Detect post type and language
        post_type = self.detect_post_type(metadata)
        language = self.detect_language(
            metadata.get('content') or metadata.get('title') or ''
        )
        
        # Calculate engagement rate (already returns tuple)
        engagement_data = self._calculate_engagement_rate_from_dict(metadata)
        engagement_rate = engagement_data[0] if isinstance(engagement_data, tuple) else engagement_data
        
        # Build Post CSV data structure
        post_data = {
            'Post_ID': post_id,
            'Post_caption': metadata.get('content') or metadata.get('title') or '',
            'Post_title': metadata.get('title'),
            'Post_hashtags': metadata.get('hashtags', []),
            'Post_type': post_type,
            'Post_date': metadata.get('publish_date'),
            'Post_extracted_date': datetime.now().isoformat(),
            'Post_platform': self.get_platform_name(),
            'Post_views': metadata.get('views'),
            'Post_likes': metadata.get('likes'),
            'Post_shares': metadata.get('shares'),
            'Post_comments': metadata.get('comments'),
            'Post_saves': metadata.get('saves'),  # Usually None
            'Post_reposts': metadata.get('reposts'),  # Usually None
            'Post_engagement_rate': engagement_rate,
            'Post_url': metadata.get('url') or self.url,
            'Post_language': language,
            'OP_username': metadata.get('author'),
            'OP_ID': op_id
        }
        
        return post_data
    
    def format_op_csv_data(self, metadata: dict, op_id: str) -> dict:
        """
        Format extracted metadata into OP CSV structure
        
        Args:
            metadata: Raw extracted metadata
            op_id: Generated OP_ID
            
        Returns:
            Dictionary with all OP_ fields in correct structure
        """
        op_data = {
            'OP_username': metadata.get('author'),
            'OP_ID': op_id,
            'OP_bio': metadata.get('author_bio') or metadata.get('bio'),
            'OP_followers': metadata.get('author_followers') or metadata.get('followers'),
            'OP_following': metadata.get('author_following') or metadata.get('following'),
            'OP_post': metadata.get('author_post_count') or metadata.get('post_count'),
            'OP_platform': self.get_platform_name()
        }
        
        return op_data
    
    # ==================== MAIN EXTRACTION METHOD ====================
    
    def extract(self) -> Tuple[Dict, Dict]:
        """
        Main extraction method with error handling
        
        PHASE 1 UPDATE: Now returns tuple of (post_data, op_data)
        
        Returns:
            Tuple of (post_data, op_data) dictionaries
            - post_data: All Post_ fields
            - op_data: All OP_ fields
            
            On error, returns (error_dict, empty_dict)
        """
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
            
            # Rate limiting - be polite to servers
            time.sleep(RATE_LIMIT_DELAY)
            
            # Perform platform-specific extraction
            extracted = self.extract_metadata()
            
            # Check if extraction returned an error
            if extracted.get('extraction_status') == 'failed':
                return (extracted, {})
            
            # Generate unique IDs
            post_id = self.generate_post_id()
            op_id = self.generate_op_id()
            
            # Format into Post and OP structures
            post_data = self.format_post_csv_data(extracted, post_id, op_id)
            op_data = self.format_op_csv_data(extracted, op_id)
            
            # Add success status
            post_data['extraction_status'] = 'success'
            
            return (post_data, op_data)
            
        except Exception as e:
            error_data = {
                'extraction_status': 'failed',
                'error_message': str(e),
                'url': self.url,
                'platform': self.get_platform_name()
            }
            return (error_data, {})
    
    # ==================== ENGAGEMENT RATE CALCULATION ====================
    
    def _calculate_engagement_rate_from_dict(self, metadata: dict) -> Tuple[Optional[float], dict]:
        """
        Calculate engagement rate from metadata dictionary
        
        Args:
            metadata: Dictionary with views, likes, comments, shares
            
        Returns:
            (rate, missing)
            rate: float|None  -> None if views is None or 0, or if ALL engagement metrics are None
            missing: dict     -> which inputs were missing (bool per key)
        """
        try:
            # Extract metrics
            views    = metadata.get('views')
            likes    = metadata.get('likes')
            comments = metadata.get('comments')
            shares   = metadata.get('shares')

            # Track missing fields for display
            missing = {
                'views'   : views is None,
                'likes'   : likes is None,
                'comments': comments is None,
                'shares'  : shares is None
            }

            # Can't calculate without view count
            if (views in (None, 0)):
                return None, missing
            
            # If *all* engagement metrics are None → no data
            if all(v is None for v in (likes, comments, shares)):
                return None, missing

            # Convert None to 0 for safe arithmetic
            likes = likes or 0
            comments = comments or 0
            shares = shares or 0

            engagements = likes + comments + shares
            rate = round((engagements / views) * 100, 2)

            return rate, missing

        except Exception as e:
            # Return None and mark everything missing if an unexpected issue occurs
            return None, {
                'views': True, 'likes': True, 'comments': True, 'shares': True
            }
    
    def _calculate_engagement_rate(self) -> Tuple[Optional[float], dict]:
        """
        Calculate engagement rate from self.metadata (for backwards compatibility)
        
        Returns:
            (rate, missing)
            rate: float|None  -> None if views is None or 0, or if ALL engagement metrics are None
            missing: dict     -> which inputs were missing (bool per key)
        """
        return self._calculate_engagement_rate_from_dict(self.metadata)
    
    # ==================== UTILITY METHODS ====================
    
    def _safe_get(self, data: dict, key: str, default=None):
        """
        Safely get value from dictionary
        
        Args:
            data: Dictionary to extract from
            key: Key to look for
            default: Default value if key not found
            
        Returns:
            Value or default
        """
        try:
            return data.get(key, default)
        except:
            return default