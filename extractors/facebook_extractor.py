"""
Facebook Post Extractor - FIXED VERSION

Fixes applied:
1. URL properly passed to BaseExtractor via super().__init__(url)
2. Targeted metric extraction using video/post ID to avoid cross-contamination
3. Timer added to track extraction duration
4. Improved share_count extraction to find correct post's metrics
"""

import requests
import re
import time
import random
import os
import sys
from dotenv import load_dotenv
from typing import Dict, Tuple, Optional, List
from datetime import datetime
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import hashlib
import json
from html import unescape as html_unescape 
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode


try:
    from .base_extractor import BaseExtractor
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from extractors.base_extractor import BaseExtractor

load_dotenv()

USER_AGENTS = [
    # Desktop only – avoids "Open app" interstitials
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Version/17.0 Safari/605.1.15"
    ),
]

class FacebookExtractor(BaseExtractor):
    """
    Extract metadata from *public* Facebook posts with anti-detection measures.
    """

    def __init__(self, url: str, cookie_string: Optional[str] = None):
        # CRITICAL FIX: Call parent __init__ FIRST to set self.url in BaseExtractor
        super().__init__(url)
        
        # Now set our own attributes
        self.url = url.strip()
        self.cookie_string = cookie_string or os.getenv("FB_COOKIE_STRING")
        self.session = None
        self.start_time = None  # For timing
        self._init_session()

    # --------------------------------------------------------------------- #
    # Session / HTTP helpers
    # --------------------------------------------------------------------- #

    def _init_session(self):
        """Initialize a requests session with human-like headers."""

        print("\n" + "=" * 80)
        print("FACEBOOK EXTRACTOR - INITIALIZATION")
        print("=" * 80)

        self.session = requests.Session()

        ua = random.choice(USER_AGENTS)

        self.session.headers.update(
            {
                "User-Agent": ua,
                "Accept": (
                    "text/html,application/xhtml+xml,application/xml;"
                    "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
                ),
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Cache-Control": "max-age=0",
            }
        )

        # Attach cookies from a raw "name=value; name2=value2" string if provided
        if self.cookie_string:
            print("  🍪 Using provided Facebook cookie string")
            for pair in self.cookie_string.split(";"):
                pair = pair.strip()
                if not pair or "=" not in pair:
                    continue
                name, value = pair.split("=", 1)
                self.session.cookies.set(name.strip(), value.strip(), domain=".facebook.com")
        else:
            print("  ⚠️ No Facebook cookies provided – you may hit cookie walls / missing metrics.")

        print(f"  ℹ️  Using User-Agent: {ua}")

    def get_platform_name(self) -> str:
        return 'facebook'

    def _human_delay(self, low: float, high: float, label: str = ""):
        """Sleep for a random interval to mimic human reading time."""
        delay = random.uniform(low, high)
        if label:
            print(f"  ⏳ Waiting {delay:.1f}s ({label})...")
        time.sleep(delay)

    def _is_cookie_wall(self, html: str) -> bool:
        markers = [
            "Allow the use of cookies from Facebook on this browser",
            "These cookies are required to use Meta Products",
        ]
        html_lower = html.lower()
        return any(m.lower() in html_lower for m in markers)

    def _parse_compact_number(self, s: str) -> Optional[int]:
        """Parse strings like '1.4K', '2.3M', '987', '12,345' into integers."""
        if not s:
            return None

        s = s.strip().upper().replace(",", "")
        m = re.match(r"^([\d\.]+)\s*([KMB])?$", s)
        if not m:
            if s.isdigit():
                return int(s)
            return None

        num_str, suffix = m.groups()
        try:
            base = float(num_str)
        except ValueError:
            return None

        if not suffix:
            return int(base)

        if suffix == "K":
            return int(base * 1_000)
        if suffix == "M":
            return int(base * 1_000_000)
        if suffix == "B":
            return int(base * 1_000_000_000)
        return None

    def _get(self, url: str, referer: Optional[str] = None, label: str = "") -> Optional[requests.Response]:
        """Wrapper around session.get with referer + delay. Never raises; returns None on hard failure."""

        if referer:
            self.session.headers.update({"Referer": referer})

        try:
            print(f"  → GET {label or url}")
            resp = self.session.get(url, timeout=20, allow_redirects=True)
            print(f"    ✓ Status: {resp.status_code} | Size: {len(resp.content)} bytes")

            if resp.status_code == 200:
                self._human_delay(0.2, 0.5, "simulating reading")
                return resp

            if resp.status_code == 404:
                print("    ⚠️  404 Not Found – post may be deleted or private.")
            elif resp.status_code == 403:
                print("    ⚠️  403 Forbidden – access restricted in public mode.")
            else:
                print(f"    ⚠️  HTTP {resp.status_code} error")

        except requests.exceptions.RequestException as e:
            print(f"    ⚠️  Request error: {e}")

        return None

    # --------------------------------------------------------------------- #
    # Public interface
    # --------------------------------------------------------------------- #

    def validate_url(self) -> bool:
        """Validate that URL looks like a Facebook post."""
        try:
            parsed = urlparse(self.url.lower())

            if "facebook.com" not in parsed.netloc and "fb.com" not in parsed.netloc:
                return False

            post_patterns = [
                "/posts/",
                "/photo.php",
                "/videos/",
                "/reel/",
                "/reels/",         
                "/permalink.php",
                "/permalink/",
                "/story.php",
                "/share/v/",  # NEW: Share link format
                "/share/r/",  # NEW: Might also exist for reels
                r"/\d+/",
            ]
            for pattern in post_patterns:
                if re.search(pattern, parsed.path):
                    return True

            return False
        except Exception:
            return False

    def extract_metadata(self) -> Dict:
        """Required by BaseExtractor but not used - we override extract() directly"""
        pass

    def extract(self) -> Tuple[Dict, Dict]:
        """
        Extract post data using multiple HTML variants and strategies.
        Returns: (post_data, op_data)
        """
        
        # START TIMER
        self.start_time = time.time()

        print("\n" + "=" * 80)
        print("FACEBOOK EXTRACTOR - STARTING")
        print("=" * 80)
        print(f"📍 URL: {self.url}")

        if not self.validate_url():
            raise Exception("Invalid Facebook URL. Must be a Facebook post/photo/video/reel URL.")

        normalized_url = self._normalize_url(self.url)
        print(f"🎯 Normalized URL: {normalized_url}")

        # Extract the video/post ID from URL for targeted metric extraction
        target_id = self._extract_target_id_from_url(normalized_url)
        print(f"🎯 Target Post/Video ID: {target_id}")
        
        if target_id:
            # Debug: show what type of extraction will be used
            if target_id.startswith('pfbid') or (not target_id.isdigit() and len(target_id) <= 15):
                print(f"    → Will use FALLBACK extraction (ID type: {'pfbid' if target_id.startswith('pfbid') else 'short alphanumeric'})")
            else:
                print(f"    → Will use TARGETED extraction (ID is numeric, len={len(target_id)})")
        else:
            print(f"    → No ID extracted, will use FALLBACK")

        # 0) Visit homepage to "warm up" the session
        print("\n" + "-" * 80)
        print("[STEP 1] VISITING FACEBOOK HOMEPAGE")
        print("-" * 80)

        _ = self._get("https://www.facebook.com/", label="homepage")
        self._human_delay(0.5, 1.0, "after homepage")

        # 1) Fetch different variants of the post
        print("\n" + "-" * 80)
        print("[STEP 2] FETCHING POST VARIANTS")
        print("-" * 80)

        variants: List[Tuple[str, requests.Response]] = []

        # Desktop
        resp_desktop = self._get(normalized_url, referer="https://www.facebook.com/", label="desktop")
        if resp_desktop:
            if self._is_cookie_wall(resp_desktop.text):
                raise Exception("Facebook cookie wall detected. Provide a valid FB_COOKIE_STRING.")
            variants.append(("desktop", resp_desktop))

        # Mobile (m.)
        mobile_url = normalized_url.replace("www.facebook.com", "m.facebook.com")
        if mobile_url != normalized_url:
            resp_mobile = self._get(mobile_url, referer=normalized_url, label="mobile")
            if resp_mobile:
                variants.append(("mobile", resp_mobile))

        # Basic (mbasic.)
        basic_url = normalized_url.replace("www.facebook.com", "mbasic.facebook.com")
        if basic_url != normalized_url:
            resp_basic = self._get(basic_url, referer=normalized_url, label="mbasic")
            if resp_basic:
                variants.append(("mbasic", resp_basic))

        if not variants:
            raise Exception("Failed to fetch any HTML variants for this URL.")

        # 2) Parse and aggregate data across variants
        print("\n" + "-" * 80)
        print("[STEP 3] PARSING & EXTRACTING DATA ACROSS VARIANTS")
        print("-" * 80)

        author: Optional[str] = None
        content: Optional[str] = None
        post_date: Optional[str] = None
        likes: Optional[int] = None
        comments: Optional[int] = None
        shares: Optional[int] = None
        post_type: Optional[str] = None
        views: Optional[int] = None
        post_title: Optional[str] = None
        first_html: Optional[str] = None

        for label, resp in variants:
            print(f"\n  🔍 Processing variant: {label}")

            # DEBUG: save raw HTML
            """
            try:
                with open(f"debug_{label}.html", "w", encoding="utf-8", errors="ignore") as f:
                    f.write(resp.text)
                print(f"    📝 Saved HTML snapshot to debug_{label}.html")
            except Exception as e:
                print(f"    ⚠️ Failed to save debug HTML for {label}: {e}")
            """
            soup = BeautifulSoup(resp.content, "html.parser")
            html_text = resp.text

            if first_html is None:
                first_html = html_text

            # Author
            if not author or author == "Unknown User":
                a = self._safe_call(self._extract_author, soup, html_text, default=None)
                if a:
                    author = a
                    print(f"    👤 Author ({label}): {author}")

            # Content
            if not content:
                c = self._safe_call(self._extract_content, soup, html_text, default=None)
                if c:
                    content = c
                    print(f"    📝 Caption found in {label} (len={len(content)})")

            # Date
            if not post_date:
                d = self._safe_call(self._extract_date, soup, html_text, default=None)
                if d:
                    post_date = d
                    print(f"    📅 Date ({label}): {post_date}")

            # TARGETED ENGAGEMENT EXTRACTION
            # Pass target_id to ensure we get metrics for the correct post
            if likes is None:
                l = self._safe_call(self._extract_likes_targeted, html_text, target_id, default=None)
                if l is not None:
                    likes = l
                    print(f"    👍 Likes ({label}): {likes}")

            if comments is None:
                cmt = self._safe_call(self._extract_comments_targeted, html_text, target_id, default=None)
                if cmt is not None:
                    comments = cmt
                    print(f"    💬 Comments ({label}): {comments}")

            if shares is None:
                sh = self._safe_call(self._extract_shares_targeted, html_text, target_id, default=None)
                if sh is not None:
                    shares = sh
                    print(f"    🔄 Shares ({label}): {shares}")

            # Post type
            if not post_type:
                pt = self._safe_call(self._determine_post_type, normalized_url, soup, default=None)
                if pt:
                    post_type = pt
                    print(f"    📌 Type ({label}): {post_type}")

            # If we've got decent data, stop early
            if content and (likes is not None or comments is not None or shares is not None):
                print("  ✅ Sufficient data collected – stopping further variant processing.")
                break

        # Try OG-title fallback for metrics-style video pages
        if first_html:
            og_metrics = self._parse_og_title_metrics(first_html)
            if og_metrics:
                og_views, og_reactions, og_title, og_owner = og_metrics

                if og_views is not None:
                    if views is None or og_views > views:
                        views = og_views

                if og_reactions is not None:
                    if likes is None or og_reactions > likes:
                        likes = og_reactions

                if post_title is None and og_title:
                    post_title = og_title

                if (not author or author == "Unknown User") and og_owner:
                    author = og_owner

        # Fallbacks
        if not author:
            author = "Unknown User"
        if not post_type:
            post_type = "post"

        content_len = len(content) if content else 0

        # Generate IDs
        post_id = self._generate_post_id(normalized_url)
        op_id = self._generate_op_id(author)

        # Calculate engagement rate using BaseExtractor's method
        engagement_metadata = {
            'views': views,
            'likes': likes,
            'comments': comments,
            'shares': shares
        }
        engagement_rate, missing = self._calculate_engagement_rate_from_dict(engagement_metadata)
        
        # Output dicts
        post_data = {
            "Post_ID": post_id,
            "Post_title": post_title,
            "Post_caption": content[:5000] if content else None,
            "Post_hashtags": self._extract_hashtags(content),
            "Post_type": post_type,
            "Post_date": post_date,
            "Post_extracted_date": datetime.now().isoformat(),
            "Post_platform": "facebook",
            "Post_views": views,
            "Post_likes": likes,
            "Post_shares": shares,
            "Post_comments": comments,
            "Post_saves": None,
            "Post_reposts": None,
            "Post_engagement_rate": engagement_rate,
            "Post_url": normalized_url,
            "Post_language": "unknown",
            "OP_username": author,
            "OP_ID": op_id,
        }

        op_data = {
            "OP_username": author,
            "OP_ID": op_id,
            "OP_bio": None,
            "OP_followers": None,
            "OP_following": None,
            "OP_post": None,
            "OP_platform": "facebook",
        }

        # STOP TIMER
        elapsed_time = time.time() - self.start_time

        print("\n" + "=" * 80)
        print("EXTRACTION COMPLETE - SUMMARY")
        print("=" * 80)
        print(f"  ⏱️  Extraction Time: {elapsed_time:.2f} seconds")
        print(f"  📝 Post_ID: {post_data.get('Post_ID')}")
        print(f"  👤 Author: {author}")
        print(f"  📏 Content: {content_len} chars")
        print(f"  📅 Date: {post_date}")
        print(f"  👍 Likes: {likes}")
        print(f"  💬 Comments: {comments}")
        print(f"  🔄 Shares: {shares}")
        print("=" * 80 + "\n")

        return post_data, op_data

    # --------------------------------------------------------------------- #
    # NEW: Targeted metric extraction methods
    # --------------------------------------------------------------------- #

    def _extract_target_id_from_url(self, url: str) -> Optional[str]:
        """
        Extract the video/post ID from the URL.
        
        Examples:
        - /reel/1754948918532947 → "1754948918532947"
        - /videos/1234567890 → "1234567890"
        - /posts/9876543210 → "9876543210"
        - /posts/pfbid028XrH... → "pfbid028XrH..."
        - /share/v/1aHwNcSFZK/ → "1aHwNcSFZK"
        """
        id_patterns = [
            r"/share/v/([a-zA-Z0-9]+)",  # NEW: /share/v/1aHwNcSFZK/
            r"/share/r/([a-zA-Z0-9]+)",  # NEW: Possible reel variant
            r"/reel/(\d+)",
            r"/reels/(\d+)",
            r"/posts/(\d+)",
            r"/posts/(pfbid[a-zA-Z0-9]+)",
            r"/videos/(\d+)",
            r"fbid=(\d+)",
            r"story_fbid=(pfbid[a-zA-Z0-9]+)",
            r"story_fbid=(\d+)",
            r"/(\d+)/?$",
        ]
        
        for pattern in id_patterns:
            m = re.search(pattern, url)
            if m:
                return m.group(1)
        
        return None

    def _extract_likes_targeted(self, html: str, target_id: Optional[str]) -> Optional[int]:
        """
        Extract like count, prioritizing data blocks that match target_id.
        """
        if not target_id:
            return self._extract_likes_old(html)
        
        # For pfbid-style IDs and share URLs (non-numeric short IDs), use fallback
        # Numeric IDs should ALWAYS try targeted extraction first
        if target_id.startswith('pfbid') or (not target_id.isdigit() and len(target_id) <= 15):
            print(f"    ℹ️  Using fallback for special URL format (ID: {target_id[:20]}...)")
            return self._extract_likes_old(html)
        
        # Strategy 1: Search for the target ID anywhere in HTML, then look for likes nearby
        # This works better for reels which might have the ID in different formats
        
        # Find all occurrences of our target ID
        target_positions = []
        for m in re.finditer(rf'"{target_id}"', html):
            target_positions.append(m.start())
        
        if target_positions:
            print(f"    🔍 Found {len(target_positions)} occurrences of ID {target_id} in HTML")
            
            # Strategy: Find feedback blocks that are associated with our video ID
            # Facebook structure: "video":{"id":"724437857360771"...} ... "feedback":{...metrics...}
            
            # For each ID occurrence, look for the nearest "feedback" block
            for pos in target_positions:
                # Search forward from ID position for feedback block (up to 10000 chars)
                search_start = pos
                search_end = min(len(html), pos + 10000)
                forward_context = html[search_start:search_end]
                
                # Look for feedback block
                feedback_match = re.search(
                    r'"feedback"\s*:\s*\{[^}]*"(?:likers|unified_reactors)"\s*:\s*\{[^}]*"count"\s*:\s*(\d+)',
                    forward_context,
                    re.DOTALL
                )
                
                if feedback_match:
                    count = int(feedback_match.group(1))
                    print(f"    🎯 Found likes in feedback block after ID at pos {pos}: {count}")
                    return count
                
                # Also try searching backward (in case feedback comes before ID reference)
                search_start = max(0, pos - 10000)
                search_end = pos
                backward_context = html[search_start:search_end]
                
                feedback_match = re.search(
                    r'"feedback"\s*:\s*\{[^}]*"(?:likers|unified_reactors)"\s*:\s*\{[^}]*"count"\s*:\s*(\d+)',
                    backward_context,
                    re.DOTALL
                )
                
                if feedback_match:
                    count = int(feedback_match.group(1))
                    print(f"    🎯 Found likes in feedback block before ID at pos {pos}: {count}")
                    return count
        
        # If targeted search failed, fall back to broader search
        print(f"    ⚠️  Could not find likes in targeted block for ID {target_id}, using fallback")
        return self._extract_likes_old(html)

    def _extract_comments_targeted(self, html: str, target_id: Optional[str]) -> Optional[int]:
        """Extract comment count, prioritizing data for target_id."""
        if not target_id:
            return self._extract_comments_old(html)
        
        # For pfbid-style IDs and share URLs, use fallback since they don't appear in GraphQL the same way
        if target_id.startswith('pfbid') or (not target_id.isdigit() and len(target_id) <= 15):
            print(f"    ℹ️  Using fallback for special URL format (ID: {target_id[:20]}...)")
            return self._extract_comments_old(html)
        
        # Find all occurrences of our target ID
        target_positions = []
        for m in re.finditer(rf'"{target_id}"', html):
            target_positions.append(m.start())
        
        if target_positions:
            # For each occurrence, look for feedback block with comments
            for pos in target_positions:
                # Search forward for feedback block (up to 10000 chars)
                search_end = min(len(html), pos + 10000)
                forward_context = html[pos:search_end]
                
                # Look for comment count in feedback block
                patterns = [
                    r'"feedback"\s*:\s*\{[^}]{0,3000}?"total_comment_count"\s*:\s*(\d+)',
                    r'"comment_rendering_instance"\s*:\s*\{\s*"comments"\s*:\s*\{\s*"total_count"\s*:\s*(\d+)',
                ]
                
                for pattern in patterns:
                    m = re.search(pattern, forward_context, re.DOTALL)
                    if m:
                        count = int(m.group(1))
                        print(f"    🎯 Found comments in feedback block after ID at pos {pos}: {count}")
                        return count
                
                # Also try backward search
                search_start = max(0, pos - 10000)
                backward_context = html[search_start:pos]
                
                for pattern in patterns:
                    m = re.search(pattern, backward_context, re.DOTALL)
                    if m:
                        count = int(m.group(1))
                        print(f"    🎯 Found comments in feedback block before ID at pos {pos}: {count}")
                        return count
        
        print(f"    ⚠️  Could not find comments in targeted block for ID {target_id}, using fallback")
        return self._extract_comments_old(html)

    def _extract_shares_targeted(self, html: str, target_id: Optional[str]) -> Optional[int]:
        """
        Extract share count, prioritizing data for target_id.
        """
        if not target_id:
            return self._extract_shares_old(html)
        
        # For pfbid-style IDs and share URLs, use fallback
        if target_id.startswith('pfbid') or (not target_id.isdigit() and len(target_id) <= 15):
            print(f"    ℹ️  Using fallback for special URL format (ID: {target_id[:20]}...)")
            return self._extract_shares_old(html)
        
        # Find all occurrences of our target ID
        target_positions = []
        for m in re.finditer(rf'"{target_id}"', html):
            target_positions.append(m.start())
        
        if target_positions:
            # For each occurrence, look for feedback block with shares
            for pos in target_positions:
                # Search forward for feedback block (up to 10000 chars)
                search_end = min(len(html), pos + 10000)
                forward_context = html[pos:search_end]
                
                # Look for share count in feedback block
                patterns = [
                    r'"feedback"\s*:\s*\{[^}]{0,3000}?"share_count_reduced"\s*:\s*"([^"]+)"',
                    r'"share_count"\s*:\s*\{\s*"count"\s*:\s*(\d+)',
                    r'"i18n_share_count"\s*:\s*"([^"]+)"',
                ]
                
                for pattern in patterns:
                    m = re.search(pattern, forward_context, re.DOTALL)
                    if m:
                        value = m.group(1)
                        if value.isdigit():
                            count = int(value)
                            print(f"    🎯 Found shares in feedback block after ID at pos {pos}: {count}")
                            return count
                        else:
                            parsed = self._parse_compact_number(value)
                            if parsed is not None:
                                print(f"    🎯 Found shares in feedback block after ID at pos {pos}: {parsed}")
                                return parsed
                
                # Also try backward search
                search_start = max(0, pos - 10000)
                backward_context = html[search_start:pos]
                
                for pattern in patterns:
                    m = re.search(pattern, backward_context, re.DOTALL)
                    if m:
                        value = m.group(1)
                        if value.isdigit():
                            count = int(value)
                            print(f"    🎯 Found shares in feedback block before ID at pos {pos}: {count}")
                            return count
                        else:
                            parsed = self._parse_compact_number(value)
                            if parsed is not None:
                                print(f"    🎯 Found shares in feedback block before ID at pos {pos}: {parsed}")
                                return parsed
        
        print(f"    ⚠️  Could not find shares in targeted block for ID {target_id}, using fallback")
        return self._extract_shares_old(html)

    # --------------------------------------------------------------------- #
    # OLD extraction methods (fallbacks)
    # --------------------------------------------------------------------- #

    def _extract_likes_old(self, html: str) -> Optional[int]:
        """Old like extraction method - used as fallback."""
        soup = BeautifulSoup(html, "html.parser")
        
        # GraphQL blocks
        m = re.search(r'"likers"\s*:\s*\{"count"\s*:\s*(\d+)\}', html)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                pass

        m = re.search(r'"unified_reactors"\s*:\s*\{"count"\s*:\s*(\d+)\}', html)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                pass

        # i18n_reaction_count
        m = re.search(r'"i18n_reaction_count"\s*:\s*"([^"]+)"', html)
        if m:
            parsed = self._parse_compact_number(m.group(1))
            if parsed is not None:
                return parsed

        # raw reaction_count
        m = re.search(r'"reaction_count"\s*:\s*(\d+)', html)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                pass

        # og:description
        og_desc = soup.find("meta", property="og:description")
        if og_desc and og_desc.get("content"):
            text = og_desc["content"]
            m = re.search(r"(\d[\d,\.]*\s*[KMB]?)\s+(?:like|likes|reaction|reactions)", text, re.I)
            if m:
                parsed = self._parse_compact_number(m.group(1))
                if parsed is not None:
                    return parsed

        return None

    def _extract_comments_old(self, html: str) -> Optional[int]:
        """Old comment extraction - used as fallback. Handles multiple formats."""
        soup = BeautifulSoup(html, "html.parser")
        
        # Priority 1: comments_count_summary_renderer (nested structure)
        # Pattern: "comment_rendering_instance":{"comments":{"total_count":32}}
        m = re.search(r'"comment_rendering_instance"\s*:\s*\{\s*"comments"\s*:\s*\{\s*"total_count"\s*:\s*(\d+)', html)
        if m:
            try:
                count = int(m.group(1))
                print(f"    ✅ Found comments via comment_rendering_instance: {count}")
                return count
            except Exception:
                pass
        
        # Priority 2: total_comment_count (most reliable for other formats)
        m = re.search(r'"total_comment_count"\s*:\s*(\d+)', html)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                pass
        
        # Priority 3: comment_count object
        m = re.search(r'"comment_count"\s*:\s*\{\s*"total_count"\s*:\s*(\d+)', html)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                pass
        
        # Priority 4: Simple comment_count number
        m = re.search(r'"comment_count"\s*:\s*(\d+)', html)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                pass

        # Priority 5: og:description
        og_desc = soup.find("meta", property="og:description")
        if og_desc and og_desc.get("content"):
            text = og_desc["content"]
            m = re.search(r"(\d[\d,]*)\s+comment[s]?\b", text, re.I)
            if m:
                try:
                    return int(m.group(1).replace(",", ""))
                except Exception:
                    pass

        return None

    def _extract_shares_old(self, html: str) -> Optional[int]:
        """Old share extraction - used as fallback. Handles multiple formats."""
        
        # Priority 1: share_count_reduced (compact string like "5", "1K")
        m = re.search(r'"share_count_reduced"\s*:\s*"([^"]+)"', html)
        if m:
            parsed = self._parse_compact_number(m.group(1))
            if parsed is not None:
                print(f"    ⚠️  Using share_count_reduced: {parsed}")
                return parsed
        
        # Priority 2: share_count object with count field
        m = re.search(r'"share_count"\s*:\s*\{\s*"count"\s*:\s*(\d+)', html)
        if m:
            try:
                count = int(m.group(1))
                print(f"    ⚠️  Using share_count object: {count}")
                return count
            except ValueError:
                pass
        
        # Priority 3: i18n_share_count string
        m = re.search(r'"i18n_share_count"\s*:\s*"([^"]+)"', html)
        if m:
            parsed = self._parse_compact_number(m.group(1))
            if parsed is not None:
                print(f"    ⚠️  Using i18n_share_count: {parsed}")
                return parsed

        # Priority 4: og:description
        soup = BeautifulSoup(html, "html.parser")
        og_desc = soup.find("meta", property="og:description")
        if og_desc and og_desc.get("content"):
            text = og_desc["content"]
            m = re.search(r"(\d[\d,\.]*\s*[KMB]?)\s+share[s]?\b", text, re.I)
            if m:
                parsed = self._parse_compact_number(m.group(1))
                if parsed is not None:
                    return parsed

        return None

    # --------------------------------------------------------------------- #
    # Extractor helpers (unchanged)
    # --------------------------------------------------------------------- #

    def _safe_call(self, func, *args, default=None):
        """Ensure a single extractor failure doesn't kill the run."""
        try:
            value = func(*args)
            return value if value is not None else default
        except Exception as e:
            print(f"    ⚠️  Extractor {func.__name__} failed: {e}")
            return default

    def _normalize_url(self, url: str) -> str:
        """Normalize Facebook URL to standard www.facebook.com form."""
        parsed = urlparse(url)

        netloc = parsed.netloc.replace("m.facebook.com", "www.facebook.com") \
                            .replace("mbasic.facebook.com", "www.facebook.com")
        parsed = parsed._replace(scheme="https", netloc=netloc)

        path = parsed.path or ""

        if path == "/permalink.php":
            qs = parse_qs(parsed.query)
            keep_keys = ("story_fbid", "id")
            kept = {k: v[0] for k, v in qs.items() if k in keep_keys and v}
            query = urlencode(kept) if kept else parsed.query
            parsed = parsed._replace(query=query, fragment="")
            return urlunparse(parsed)

        if path == "/photo.php" or path == "/story.php":
            parsed = parsed._replace(fragment="")
            return urlunparse(parsed)

        parsed = parsed._replace(query="", fragment="")
        return urlunparse(parsed)

    def _extract_owner_from_graphql(self, html: str) -> Optional[str]:
        """Look for GraphQL video_owner block."""
        m = re.search(
            r'"video_owner"\s*:\s*\{"__typename":"(?:User|Page)","id":"[^"]+","name":"([^"]+)"\}',
            html
        )
        if m:
            return html_unescape(m.group(1))
        return None

    def _parse_og_title_metrics(
        self, html: str
    ) -> Optional[Tuple[Optional[int], Optional[int], Optional[str], Optional[str]]]:
        """Parse metrics-style og:title."""
        m = re.search(
            r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"',
            html,
            re.I,
        )
        if not m:
            return None

        raw = html_unescape(m.group(1))
        lower = raw.lower()

        if "views" not in lower and "reactions" not in lower and "comments" not in lower:
            return None

        parts = [p.strip() for p in raw.split("|") if p.strip()]
        metrics_part = parts[0] if parts else ""
        views = reactions = None
        title = owner = None

        mv = re.search(r'([\d.,]+[KMB]?)\s+views', metrics_part, re.I)
        if mv:
            views = self._parse_compact_number(mv.group(1))

        mr = re.search(r'([\d.,]+[KMB]?)\s+reactions', metrics_part, re.I)
        if mr:
            reactions = self._parse_compact_number(mr.group(1))

        if len(parts) >= 2:
            title = parts[1]

        if len(parts) >= 3:
            owner = parts[-1]

        return views, reactions, title, owner

    def _extract_author(self, soup: BeautifulSoup, html: str) -> Optional[str]:
        """Extract post author/username."""
        owner = self._extract_owner_from_graphql(html)
        if owner:
            return owner

        og_metrics = self._parse_og_title_metrics(html)
        if og_metrics:
            _, _, _, og_owner = og_metrics
            if og_owner:
                return og_owner

        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            title = og_title["content"]
            lower = title.lower()
            if "views" not in lower and "reactions" not in lower and "comments" not in lower:
                for sep in [" - ", " | ", " posted ", " shared "]:
                    if sep in title:
                        author = title.split(sep)[0].strip()
                        if 0 < len(author) < 100:
                            return author
                if 0 < len(title) < 100:
                    return title

        scripts = soup.find_all("script", type="application/ld+json")
        for script in scripts:
            try:
                if not script.string:
                    continue
                data = json.loads(script.string)
                if isinstance(data, dict):
                    author = data.get("author", {})
                    if isinstance(author, dict):
                        name = author.get("name")
                        if name:
                            return name
            except Exception:
                continue

        url_match = re.search(r"facebook\.com/([^/]+)/", self.url)
        if url_match:
            username = url_match.group(1)
            if username not in ["photo.php", "posts", "videos", "watch", "story.php"]:
                return username

        return None

    def _extract_content(self, soup: BeautifulSoup, html: str) -> Optional[str]:
        """Extract post caption/content."""
        og_desc = soup.find("meta", property="og:description")
        if og_desc and og_desc.get("content"):
            content = og_desc["content"].strip()
            if len(content) > 10:
                return content

        twitter_desc = soup.find("meta", attrs={"name": "twitter:description"})
        if twitter_desc and twitter_desc.get("content"):
            content = twitter_desc["content"].strip()
            if len(content) > 10:
                return content

        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            content = meta_desc["content"].strip()
            if len(content) > 10:
                return content

        return None

    def _extract_date(self, soup: BeautifulSoup, html: str) -> Optional[str]:
        """Extract publish date."""
        # Priority 1: article:published_time
        pub_time = soup.find("meta", property="article:published_time")
        if pub_time and pub_time.get("content"):
            return pub_time["content"]

        # Priority 2: og:updated_time
        updated_time = soup.find("meta", property="og:updated_time")
        if updated_time and updated_time.get("content"):
            return updated_time["content"]

        # Priority 3: JSON-LD structured data
        scripts = soup.find_all("script", type="application/ld+json")
        for script in scripts:
            try:
                if not script.string:
                    continue
                data = json.loads(script.string)
                if isinstance(data, dict):
                    date = data.get("datePublished") or data.get("dateCreated")
                    if date:
                        return date
            except Exception:
                continue

        # Priority 4: GraphQL timestamp fields
        date_patterns = [
            r'"publish_time"\s*:\s*(\d+)',
            r'"created_time"\s*:\s*(\d+)',
            r'"creation_time"\s*:\s*(\d+)',
            r'"timestamp"\s*:\s*(\d+)',
        ]
        for pattern in date_patterns:
            m = re.search(pattern, html)
            if m:
                try:
                    ts = int(m.group(1))
                    # Facebook timestamps are in seconds (Unix epoch)
                    return datetime.fromtimestamp(ts).isoformat()
                except Exception:
                    continue

        return None

    def _extract_hashtags(self, content: Optional[str]) -> Optional[str]:
        if not content:
            return None
        tags = re.findall(r"#\w+", content)
        return ", ".join(tags) if tags else None

    def _determine_post_type(self, url: str, soup: BeautifulSoup) -> str:
        url_lower = url.lower()
        if "/reel/" in url_lower or "/reels/" in url_lower:
            return "reel"
        if "/video" in url_lower or "/watch/" in url_lower:
            return "video"
        if "/photo" in url_lower:
            return "photo"
        if "/events/" in url_lower:
            return "event"

        og_type = soup.find("meta", property="og:type")
        if og_type and og_type.get("content"):
            t = og_type["content"].lower()
            if "video" in t:
                return "video"
            if "photo" in t or "image" in t:
                return "photo"

        return "post"

    def _generate_post_id(self, url: str) -> str:
        id_patterns = [
            r"/posts/(\d+)",
            r"/videos/(\d+)",
            r"fbid=(\d+)",
            r"story_fbid=(\d+)",
            r"/(\d+)/?$",
        ]
        for pattern in id_patterns:
            m = re.search(pattern, url)
            if m:
                return f"fb_{m.group(1)}"
        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        return f"fb_{url_hash}"

    def _generate_op_id(self, username: str) -> str:
        username_clean = re.sub(r"[^a-zA-Z0-9]", "", (username or "").lower())
        username_hash = hashlib.md5(username_clean.encode()).hexdigest()[:12]
        return f"fb_user_{username_hash}"

    def close(self):
        if self.session:
            self.session.close()


def main():
    print("\n" + "=" * 80)
    print("FACEBOOK POST EXTRACTOR - FIXED VERSION")
    print("=" * 80)
    print("\nFIXES APPLIED:")
    print("  ✅ URL properly passed to BaseExtractor")
    print("  ✅ Targeted metric extraction using video/post ID")
    print("  ✅ Timer added for performance tracking")
    print("  ✅ Fixed share count extraction (no more cross-contamination)")
    print("\n")

    # REQUIRE URL - no fallback to example
    if len(sys.argv) < 2:
        print("❌ ERROR: No URL provided!")
        print(f"\n💡 USAGE: python {sys.argv[0]} <facebook_url>")
        print("\nEXAMPLES:")
        print(f"  python {sys.argv[0]} https://www.facebook.com/reel/1754948918532947")
        print(f"  python {sys.argv[0]} https://www.facebook.com/username/posts/123456789")
        print(f"  python {sys.argv[0]} https://www.facebook.com/watch/?v=987654321")
        sys.exit(1)
    
    url = sys.argv[1]
    print(f"📌 Using URL: {url}\n")

    try:
        extractor = FacebookExtractor(url)
        post_data, op_data = extractor.extract()

        print("\n" + "=" * 80)
        print("RESULTS")
        print("=" * 80)

        print("\n📝 POST DATA:")
        print(json.dumps(post_data, indent=2, default=str))

        print("\n👤 OP DATA:")
        print(json.dumps(op_data, indent=2, default=str))

        with open("facebook_post_data.json", "w", encoding="utf-8") as f:
            json.dump(post_data, f, indent=2, default=str)

        with open("facebook_op_data.json", "w", encoding="utf-8") as f:
            json.dump(op_data, f, indent=2, default=str)

        print("\n✅ Data saved to:")
        print("  - facebook_post_data.json")
        print("  - facebook_op_data.json")

        extractor.close()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        print("\nFull traceback:")
        print(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()