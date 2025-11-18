"""
Polis Analysis - Metadata Extraction Tool
Main Streamlit Application
"""
import streamlit as st
from datetime import datetime
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import (
    validate_and_parse, 
    detect_platform, 
    get_platform_display_name,
    is_supported_platform,
    generate_csv,
    csv_to_download_string
)
from extractors import TikTokExtractor, YouTubeExtractor, RedditExtractor, NewsExtractor, FacebookExtractor
from config import settings

# Page configuration
st.set_page_config(
    page_title="Polis Analysis - Metadata Tool",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for better styling with theme support
def apply_theme():
    # Initialize theme to LIGHT mode by default
    if 'theme' not in st.session_state:
        st.session_state.theme = 'dark'  # ✅ DEFAULT TO LIGHT
        
    if st.session_state.theme == 'dark':
        theme_css = """
        <style>
            /* Dark mode - full page styling */
            .stApp {
                background-color: #0e1117 !important;
                color: #ffffff !important;
            }
            
            /* TOP HEADER BAR - MATCH PAGE BACKGROUND (black) */
            header[data-testid="stHeader"] {
                background-color: #0e1117 !important;
            }
            
            .main-header {
                font-size: 2.5rem;
                font-weight: bold;
                color: #4dabf7;
                margin-bottom: 0.5rem;
            }
            .sub-header {
                font-size: 1.1rem;
                color: #adb5bd;
                margin-bottom: 2rem;
            }
            .additional-section {
                background-color: #0e1117;
                padding: 0.75rem;
                border-radius: 0.5rem;
                border: 1px dashed #333333;
                margin-top: 6rem;
            }
            
            /* Dark mode text colors */
            .stMarkdown, p, span, label {
                color: #e0e0e0 !important;
            }
            h1, h2, h3, h4, h5, h6 {
                color: #ffffff !important;
            }
            
            /* Input fields dark mode */
            .stTextInput input {
                background-color: #262730 !important;
                color: #ffffff !important;
                border-color: #4a5568 !important;
            }
            
            /* Text area dark mode */
            .stTextArea textarea {
                background-color: #262730 !important;
                color: #ffffff !important;
                border-color: #4a5568 !important;
            }
            .stTextArea label {
                color: #e0e0e0 !important;
            }
            
            /* Expander dark mode */
            .streamlit-expanderHeader {
                background-color: #262730 !important;
                color: #ffffff !important;
            }
            .streamlit-expanderContent {
                background-color: #0e1117 !important;
            }
            
            /* CODE BLOCKS IN SIDEBAR - VISIBLE */
            section[data-testid="stSidebar"] code {
                background-color: #262730 !important;
                color: #4ade80 !important;
                padding: 2px 6px;
                border-radius: 3px;
                font-family: monospace;
            }
            
            /* Markdown in sidebar expanders */
            section[data-testid="stSidebar"] .streamlit-expanderContent {
                background-color: #0e1117 !important;
            }
            section[data-testid="stSidebar"] .streamlit-expanderContent p {
                color: #e0e0e0 !important;
            }
            section[data-testid="stSidebar"] .streamlit-expanderContent strong {
                color: #ffffff !important;
            }
            section[data-testid="stSidebar"] .streamlit-expanderContent ul {
                color: #e0e0e0 !important;
            }
            section[data-testid="stSidebar"] .streamlit-expanderContent li {
                color: #e0e0e0 !important;
            }
            
            /* Sidebar styling - dark grey */
            section[data-testid="stSidebar"] {
                background-color: #262730 !important;
            }
            section[data-testid="stSidebar"] * {
                color: #ffffff !important;
            }
            
            /* PRIMARY BUTTON - BLUE WITH WHITE TEXT */
            .stButton button[kind="primary"] {
                background-color: #0068c9 !important;
                color: #ffffff !important;
                border: none !important;
                font-weight: 500 !important;
            }
            .stButton button[kind="primary"]:hover {
                background-color: #0054a3 !important;
            }
            
            /* Dark mode secondary buttons */
            .stButton button:not([kind="primary"]) {
                background-color: #262730 !important;
                color: #ffffff !important;
                border: 1px solid #444444 !important;
            }
            .stButton button:not([kind="primary"]):hover {
                background-color: #404040 !important;
                border-color: #555555 !important;
            }
            .stDownloadButton button {
                background-color: #262730 !important;
                color: #ffffff !important;
                border: 1px solid #444444 !important;
            }
            .stDownloadButton button:hover {
                background-color: #404040 !important;
                border-color: #555555 !important;
            }
        </style>
        """

    else:
        # LIGHT MODE
        theme_css = """
        <style>
            .stApp {
                background-color: #ffffff !important;
                color: #000000 !important;
            }
            
            header[data-testid="stHeader"] {
                background-color: #ffffff !important;
            }
            
            .main-header {
                font-size: 2.5rem;
                font-weight: bold;
                color: #1f77b4 !important;
                margin-bottom: 0.5rem;
            }
            .sub-header {
                font-size: 1.1rem;
                color: #666666 !important;
                margin-bottom: 2rem;
            }
            
            /* Light mode text */
            .stMarkdown, p, span, label {
                color: #000000 !important;
            }
            h1, h2, h3, h4, h5, h6 {
                color: #000000 !important;
            }
            
            /* Regular code blocks - dark text */
            code {
                background-color: #f0f0f0 !important;
                color: #333333 !important;
                padding: 2px 6px;
                border-radius: 3px;
            }
            
            /* CSV preview code - white text on dark background */
            [data-testid="stCodeBlock"] {
                background-color: #1e1e1e !important;
                border: 1px solid #000000 !important;
            }
            [data-testid="stCodeBlock"] code,
            [data-testid="stCodeBlock"] pre,
            [data-testid="stCodeBlock"] * {
                color: #ffffff !important;
                background-color: #1e1e1e !important;
            }
            [data-testid="stCodeBlock"]:hover code,
            [data-testid="stCodeBlock"]:hover pre,
            [data-testid="stCodeBlock"]:hover * {
                color: #ffffff !important;
            }
            
            /* Input fields */
            .stTextInput input {
                background-color: #f7f7f7 !important;
                color: #000000 !important;
                border: none !important;
            }
            .stTextInput input::placeholder {
                color: #999999 !important;
            }
            
            /* Text area */
            .stTextArea textarea {
                background-color: #f7f7f7 !important;
                color: #000000 !important;
                border: none !important;
            }
            
            /* Expander */
            .streamlit-expanderHeader {
                background-color: #ffffff !important;
                color: #000000 !important;
                border: 1px solid #e0e0e0 !important;
                border-radius: 4px !important;
            }
            .streamlit-expanderContent {
                background-color: #ffffff !important;
                border: 1px solid #e0e0e0 !important;
                border-top: none !important;
            }
            
            /* Sidebar */
            section[data-testid="stSidebar"] {
                background-color: #f5f5f5 !important;
            }
            section[data-testid="stSidebar"] * {
                color: #000000 !important;
            }
            
            /* Settings menu */
            [data-baseweb="popover"] > div {
                background-color: #f5f5f5 !important;
            }
            [data-baseweb="popover"] ul {
                background-color: #f5f5f5 !important;
            }
            [data-baseweb="popover"] li {
                background-color: #f5f5f5 !important;
                color: #000000 !important;
            }
            [data-baseweb="popover"] li:hover {
                background-color: #e0e0e0 !important;
            }
            [data-baseweb="popover"] [role="menuitem"] * {
                color: #000000 !important;
            }
            
            /* PRIMARY BUTTON - BLUE WITH WHITE TEXT - ULTIMATE FIX */
            .stButton > button[kind="primary"],
            button[kind="primary"],
            button[data-testid="baseButton-primary"],
            div[data-testid="stButton"] > button[kind="primary"] {
                background-color: #0068c9 !important;
                background: #0068c9 !important;
                color: #ffffff !important;
                border: none !important;
                font-weight: 500 !important;
            }
            
            .stButton > button[kind="primary"]:hover,
            button[kind="primary"]:hover {
                background-color: #0054a3 !important;
                background: #0054a3 !important;
                color: #ffffff !important;
            }
            
            .stButton > button[kind="primary"]:focus,
            .stButton > button[kind="primary"]:active,
            button[kind="primary"]:focus,
            button[kind="primary"]:active {
                background-color: #0068c9 !important;
                background: #0068c9 !important;
                color: #ffffff !important;
                outline: none !important;
                box-shadow: none !important;
            }
            
            /* Force white text on button content */
            button[kind="primary"] *,
            .stButton > button[kind="primary"] * {
                color: #ffffff !important;
            }
            
            /* Secondary buttons */
            .stButton button:not([kind="primary"]) {
                background-color: #ffffff !important;
                color: #000000 !important;
                border: 1px solid #d0d0d0 !important;
            }
            .stDownloadButton button {
                background-color: #ffffff !important;
                color: #000000 !important;
                border: 1px solid #d0d0d0 !important;
            }
            
            /* Disabled buttons */
            .stButton button:disabled {
                opacity: 0.4 !important;
                cursor: not-allowed !important;
                background-color: #e0e0e0 !important;
                color: #999999 !important;
            }
            
            /* Tooltips */
            div[role="tooltip"],
            [data-baseweb="tooltip"] {
                background-color: #ffffff !important;
                color: #000000 !important;
                border: 1px solid #000000 !important;
            }
            div[role="tooltip"] *,
            [data-baseweb="tooltip"] * {
                color: #000000 !important;
            }
        </style>
        """
    st.markdown(theme_css, unsafe_allow_html=True)


def main():
    """Main application logic"""

    # Initialize session state for theme
    if 'theme' not in st.session_state:
        st.session_state.theme = 'light'

    # Initialize session state for storing results
    if 'last_metadata' not in st.session_state:
        st.session_state.last_metadata = None

    # Initialize session state for showing supported platforms modal
    if 'show_platforms' not in st.session_state:
        st.session_state.show_platforms = False

    # Initialize test mode for previewing API config messages (hidden feature)
    if 'test_mode_show_api_config' not in st.session_state:
        st.session_state.test_mode_show_api_config = False

    apply_theme()
    
    # Theme toggle button at the top right
    col1, col2 = st.columns([6, 1])
    with col2:
        theme_icon = "🌙" if st.session_state.theme == 'light' else "☀️"
        theme_label = "Dark Mode" if st.session_state.theme == 'light' else "Light Mode"
        if st.button(f"{theme_icon} {theme_label}", key="theme_toggle"):
            st.session_state.theme = 'dark' if st.session_state.theme == 'light' else 'light'
            st.rerun()
    
    # Header
    st.markdown('<div class="main-header">🌍 Polis Analysis - Metadata Extraction Tool</div>', 
                unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Extract metadata from social media and news articles for disinformation analysis</div>', 
                unsafe_allow_html=True)
    
    # Hidden test mode toggle in sidebar (for previewing API config messages)
    with st.sidebar:

        st.markdown("### 🍪 Facebook Authentication (Optional)")
        st.caption("Provide your Facebook cookies for better extraction results")
        
        with st.expander("📖 How to get Facebook cookies"):
            st.markdown("""
            1. **Login to Facebook** in your browser
            2. **Open Developer Tools** (F12 or Right-click → Inspect)
            3. **Go to Application/Storage tab** → Cookies → facebook.com
            4. **Copy the cookie string** in format: `name1=value1; name2=value2`
            5. **Paste below** (your cookies are never stored permanently)
            
            **Recommended cookies to include:**
            - `c_user`
            - `xs`
            - `datr`
            """)
        
        fb_cookies = st.text_area(
            "Facebook Cookie String (optional)",
            placeholder="c_user=123456789; xs=abcd1234...",
            help="Your cookies are only used for this session and are not stored",
            key="fb_cookies"
        )
        
        if fb_cookies:
            st.success("✅ Facebook cookies provided")
            # Store in session state for use by FacebookExtractor
            st.session_state.fb_cookie_string = fb_cookies
        else:
            st.info("ℹ️ Running without Facebook cookies (public mode)")
            st.session_state.fb_cookie_string = None

        st.markdown("---")
        with st.expander("🔧 Developer Tools", expanded=False):
            if st.checkbox("Preview API Config Messages", value=st.session_state.test_mode_show_api_config):
                st.session_state.test_mode_show_api_config = True
            else:
                st.session_state.test_mode_show_api_config = False
            st.caption("Enable this to preview the API configuration messages that users see when API keys are missing.")
    
    # Check if API keys are configured and show collapsible info if needed
    check_api_configuration()
    
    st.markdown("---")  # Visual separator
    
    # URL Input
    st.markdown("### 📎 Enter URL")
    url_input = st.text_input(
        "Paste the URL of the content you want to analyse:",
        placeholder="https://www.youtube.com/watch?v=...",
        help="Supports: YouTube, TikTok, Facebook, Reddit, and major news/blog sites"
    )
    
    # Extract button
    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        extract_button = st.button("🔍 Extract Metadata", type="primary", use_container_width=True)
    with col2:
        if st.button("ℹ️ Supported Platforms", use_container_width=True):
            st.session_state.show_platforms = not st.session_state.show_platforms
    
    # Show supported platforms if toggled
    if st.session_state.show_platforms:
        show_supported_platforms()
    
    # Process URL when button clicked
    if extract_button and url_input:
        st.session_state.last_metadata = None  # Clear previous results
        process_url(url_input)
    elif extract_button and not url_input:
        st.error("⚠️ Please enter a URL first")
    
    # Display stored results if they exist (persists across reruns)
    if st.session_state.last_metadata:
        display_results(st.session_state.last_metadata)
    
    # Show greyed-out premium features
    show_premium_features()
    
    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: #666; font-size: 0.9rem;'>
        Built for Polis Analysis | For questions about this tool, contact your administrator
        </div>
        """,
        unsafe_allow_html=True
    )


def check_api_configuration():
    """Check if API keys are properly configured"""

    # Try to get API keys from Streamlit secrets (for cloud deployment)
    try:
        if hasattr(st, 'secrets'):
            if 'YOUTUBE_API_KEY' in st.secrets:
                os.environ['YOUTUBE_API_KEY'] = st.secrets['YOUTUBE_API_KEY']
            if 'REDDIT_CLIENT_ID' in st.secrets:
                os.environ['REDDIT_CLIENT_ID'] = st.secrets['REDDIT_CLIENT_ID']
            if 'REDDIT_CLIENT_SECRET' in st.secrets:
                os.environ['REDDIT_CLIENT_SECRET'] = st.secrets['REDDIT_CLIENT_SECRET']
    except FileNotFoundError:
        # Secrets file not found - this is normal for local development
        # User will be notified in sidebar if keys are missing
        pass
    except Exception:
        # Other exceptions - continue without secrets
        pass
    
    # Show warning in sidebar if keys missing (OR if test mode enabled)
    missing_keys = []
    if not settings.YOUTUBE_API_KEY:
        missing_keys.append("YouTube")
    if not settings.REDDIT_CLIENT_ID or not settings.REDDIT_CLIENT_SECRET:
        missing_keys.append("Reddit")
    
    # In test mode, pretend all keys are missing to preview the UI
    if st.session_state.get('test_mode_show_api_config', False):
        missing_keys = ["YouTube", "Reddit"]  # Simulate all missing
    
    if missing_keys and st.session_state.get('test_mode_show_api_config', False):
        # Main area - collapsible info about missing keys
        test_mode_label = " (TEST MODE - Preview)" if st.session_state.get('test_mode_show_api_config', False) else ""
        with st.expander(f"ℹ️ API Configuration Required - Click to expand{test_mode_label}", expanded=False):
            st.warning(f"⚠️ API keys not configured for: {', '.join(missing_keys)}")
            st.markdown("""
            **How to configure API keys:**
            
            🌐 **For Streamlit Cloud deployment:**
            1. Go to your app settings (gear icon)
            2. Click on "Secrets" 
            3. Add your API keys in TOML format:
            ```toml
            YOUTUBE_API_KEY = "your-key-here"
            REDDIT_CLIENT_ID = "your-id-here"
            REDDIT_CLIENT_SECRET = "your-secret-here"
            ```
            
            💻 **For local development:**
            Create a `.streamlit/secrets.toml` file in your project folder with the same format above.
            
            📚 [Learn more about getting API keys](https://github.com/your-repo)
            """)
        
        # Sidebar - short reminder
        with st.sidebar:
            test_badge = " 🔧 TEST" if st.session_state.get('test_mode_show_api_config', False) else ""
            st.info(f"⚠️ Missing API keys{test_badge}: {', '.join(missing_keys)}")


def show_supported_platforms():
    """Display information about supported platforms"""
    #Reddit - Posts and discussions (via official API)  
    #- News & Blogs - Articles from major news sites, Medium, Substack, etc.
    st.info("""
    **Currently Supported Platforms:**
    
    ✅ **TikTok** - Videos (via oembed + web scraping)    
    ✅ **YouTube** - Videos (via official API)    
    ✅ **Facebook** - Public posts from pages, profiles, and groups      
    
    **Coming Soon:**
    - Reddit (under development)
    - News & Blogs (e.g substack/medium - under development)
    - Telegram (public channels)
    - Twitter/X (if budget approved)
    """)


def process_url(url: str):
    """Process the URL and extract metadata"""
    
    with st.spinner("🔍 Analyzing URL..."):
        # Validate URL
        validation = validate_and_parse(url)
        
        if not validation['valid']:
            st.error(f"❌ {validation['error']}")
            return
        
        normalized_url = validation['normalized_url']
        
        # Detect platform
        platform = detect_platform(normalized_url)
        platform_name = get_platform_display_name(platform)
        
        # Display detected platform
        st.markdown(f"**Detected Platform:** {platform_name}")
        
        # Check if platform is supported
        if not is_supported_platform(platform):
            st.error(f"""
            ❌ **Platform Not Supported**
            
            The URL appears to be from **{platform_name}**, which is not currently supported.
            
            Please use URLs from: YouTube, TikTok, Facebook (public posts), Reddit, or major news/blog sites.
            """)
            return
        
        # Show API cost info
        show_api_cost_info(platform)
        
    # Extract metadata
    with st.spinner(f"📊 Extracting metadata from {platform_name}..."):
        metadata = extract_metadata(normalized_url, platform)
        
        if metadata['extraction_status'] == 'success':
            st.session_state.last_metadata = metadata  # Store in session state
        elif metadata['extraction_status'] == 'partial':
            st.warning("⚠️ Partial extraction - some data unavailable")
            st.session_state.last_metadata = metadata  # Store in session state
        else:
            st.error(f"❌ Extraction failed: {metadata.get('error_message', 'Unknown error')}")
            st.session_state.last_metadata = None  # Clear results on failure


def show_api_cost_info(platform: str):
    """Display API cost information"""
    
    if platform == 'tiktok': 
        st.info("ℹ️ Using TikTok oembed + web scraping - No API costs")
    elif platform == 'youtube':
        st.info("ℹ️ Using YouTube API - No cost (free tier: 10,000 quota/day)")
    elif platform == 'facebook':
        st.info("ℹ️ Using web scraping - Public posts only, no API costs")
    elif platform == 'reddit':
        st.info("⚠️ Limited Functionality with Reddit.")
        st.info("ℹ️ Using Reddit API - No cost (free tier: 60 requests/minute)")
    elif platform == 'news':
        st.info("⚠️ News/Blog extraction is currently under development. Please try TikTok, YouTube, or Facebook URLs for now.")
        #st.info("ℹ️ Using web scraping - No API costs")


def extract_metadata(url: str, platform: str) -> dict:
    """Extract metadata using appropriate extractor"""
    
    try:
        if platform == 'tiktok':
            extractor = TikTokExtractor(url)
            result = extractor.extract()
            
            # TikTok returns tuple (post_data, op_data) - extract post_data
            if isinstance(result, tuple):
                post_data, op_data = result
                metadata = post_data
                # Store op_data separately if needed
                metadata['_op_data'] = op_data
            else:
                metadata = result
            
            # Add debug output in expander
            with st.expander("🔍 TikTok Extraction Debug", expanded=True):
                if metadata.get('Post_views') or metadata.get('Post_likes'):
                    st.success(f"✅ Got metrics! Views: {metadata.get('Post_views')}, Likes: {metadata.get('Post_likes')}")
                else:
                    st.warning("⚠️ No engagement metrics found")
                
        elif platform == 'youtube':
            extractor = YouTubeExtractor(url)
            result = extractor.extract()
            
            # YouTube returns (post_data, op_data)
            if isinstance(result, tuple):
                post_data, op_data = result
                metadata = post_data
                metadata['_op_data'] = op_data   # ✅ keep OP data
            else:
                metadata = result
                
        elif platform == 'facebook':
            fb_cookie = st.session_state.get('fb_cookie_string', None)
            # Pass cookies to extractor
            extractor = FacebookExtractor(url, cookie_string=fb_cookie)
            result = extractor.extract()
            if isinstance(result, tuple):
                post_data, op_data = result
                metadata = post_data
                metadata['_op_data'] = op_data  
            else:
                metadata = result
                
        elif platform == 'reddit':
            extractor = RedditExtractor(url)
            result = extractor.extract()
            if isinstance(result, tuple):
                post_data, op_data = result
                metadata = post_data
                metadata['_op_data'] = op_data   
            else:
                metadata = result
                
        elif platform == 'news':
            extractor = NewsExtractor(url)
            result = extractor.extract()
            if isinstance(result, tuple):
                post_data, op_data = result
                metadata = post_data
                metadata['_op_data'] = op_data   
            else:
                metadata = result
        else:
            return {'extraction_status': 'failed', 'error_message': f'Unexpected type: {type(result)}'}
        
        if 'extraction_status' not in metadata:
            metadata['extraction_status'] = 'success'  # Default to success if not set

        return metadata
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            'extraction_status': 'failed',
            'error_message': str(e),
            'url': url,
            'platform': platform
        }


def display_results(metadata: dict):
    """Display extracted metadata"""
    
    if metadata.get('platform') in ('facebook','tiktok','youtube','reddit'):
        st.success("✅ **Metadata Extracted Successfully!**")
    
    # Display preview in expandable sections
    st.markdown("### 📊 Preview")
    
    col1, col2 = st.columns(2)

    # Handle both old format and new Post_ prefixed format
    def get_field(field_name):
        """Get field from either format (Post_field or field)"""
        return metadata.get(f'Post_{field_name}') or metadata.get(field_name)

    with col1:
        st.markdown("**Basic Information**")
        st.write(f"**Title:** {fmt_text(get_field('title'))}")
        st.write(f"**Caption:** {fmt_text(get_field('caption'))}")
        st.write(f"**Author:** {fmt_text(metadata.get('OP_username') or metadata.get('author'))}")
        st.write(f"**Published:** {fmt_text(get_field('date'))}")
        st.write(f"**Platform:** {fmt_platform(get_field('platform'))}")

    with col2:
        st.markdown("**Engagement Metrics**")
        st.write(f"**Views:** {fmt_int(get_field('views'))}")
        st.write(f"**Likes:** {fmt_int(get_field('likes'))}")
        st.write(f"**Comments:** {fmt_int(get_field('comments'))}")
        st.write(f"**Saves:** {fmt_int(get_field('saves'))}")
        st.write(f"**Shares:** {fmt_int(get_field('shares'))}")

        engagement_rate = get_field('engagement_rate')
        if engagement_rate is not None:
            if isinstance(engagement_rate, tuple):
                rate = engagement_rate[0]
            else:
                rate = engagement_rate
                
            if rate is not None:
                st.write(f"**Engagement Rate:** {rate:.2f}%")
        else:
            st.warning("⚠️ Engagement rate unavailable — insufficient data.")

        if metadata.get('Post_platform') == 'facebook' and metadata.get('Post_type') == 'reel':
            st.warning("""⚠️ **Double check engagement metrics for Facebook Reels**  
                    (HTML pre-loads multiple reels' data at once.)"""
                    )
    
    # Show content preview
    content = get_field('caption') or get_field('content')
    if content:
        with st.expander("📄 Content Preview"):
            st.text(content[:500] + "..." if len(content) > 500 else content)
    
    # Show hashtags if available
    # FIX for app.py - Replace the hashtag display section

    # Show hashtags if available
    hashtags = get_field('hashtags')
    if hashtags:
        with st.expander("🏷️ Hashtags/Tags"):
            # DEFENSIVE FIX: Handle both string and list formats
            if isinstance(hashtags, str):
                # If it's a string, split it properly
                if ',' in hashtags:
                    # Already comma-separated: "#tag1, #tag2"
                    tags_list = [tag.strip() for tag in hashtags.split(',')]
                elif ' ' in hashtags:
                    # Space-separated: "#tag1 #tag2"  
                    tags_list = [tag.strip() for tag in hashtags.split() if tag.startswith('#')]
                else:
                    # Single hashtag or other format
                    tags_list = [hashtags]
                st.write(", ".join(tags_list))
            elif isinstance(hashtags, list):
                # It's already a list - good!
                st.write(", ".join(hashtags))
            else:
                # Unknown format
                st.write(str(hashtags))
        
    # Generate CSV data for both POST and OP
    st.markdown("### 💾 Download/Copy Data")
    
    # Separate POST and OP data
    post_data = {}
    op_data = {}
    
    for key, value in metadata.items():
        if key.startswith('Post_'):
            post_data[key] = value
        elif key.startswith('OP_'):
            op_data[key] = value
        elif key == '_op_data':
            # Handle stored OP data from TikTok extractor
            continue
        else:
            # Legacy fields without prefix - add to post_data
            post_data[key] = value
    
    # Check if we have OP data stored separately (TikTok case)
    if '_op_data' in metadata:
        op_data.update(metadata['_op_data'])
    
    # Clean up engagement_rate if it's a tuple
    if 'Post_engagement_rate' in post_data and isinstance(post_data['Post_engagement_rate'], tuple):
        post_data['Post_engagement_rate'] = post_data['Post_engagement_rate'][0]
    if 'engagement_rate' in post_data and isinstance(post_data['engagement_rate'], tuple):
        post_data['engagement_rate'] = post_data['engagement_rate'][0]
    
    # Generate CSV strings
    post_csv_string = None
    op_csv_string = None
    df_post = None
    df_op = None
    
    if post_data:
        df_post = generate_csv([post_data])
        post_csv_string = csv_to_download_string(df_post)
    
    if op_data:
        df_op = generate_csv([op_data])
        op_csv_string = csv_to_download_string(df_op)
    
    # Create timestamp for filenames
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Copy Data Section (above downloads)
    st.markdown("#### 📋 Copy Data")
    col1, col2 = st.columns(2)
    
    with col1:
        if post_csv_string:
            if st.button("📄 Copy Post Data CSV", use_container_width=True, key="copy_post"):
                st.code(post_csv_string, language=None)
                st.success("✅ Post data displayed above - select and copy (Ctrl+C / Cmd+C)")
        else:
            st.button("📄 Copy Post Data CSV", use_container_width=True, disabled=True, 
                     help="Post data not available")
    
    with col2:
        if op_csv_string:
            if st.button("👤 Copy OP Data CSV", use_container_width=True, key="copy_op"):
                st.code(op_csv_string, language=None)
                st.success("✅ OP data displayed above - select and copy (Ctrl+C / Cmd+C)")
        else:
            st.button("👤 Copy OP Data CSV", use_container_width=True, disabled=True,
                     help="OP data not available")
    
    # Warning if missing data
    if not post_csv_string or not op_csv_string:
        missing = []
        if not post_csv_string:
            missing.append("Post data")
        if not op_csv_string:
            missing.append("OP data")
        st.warning(f"⚠️ {' and '.join(missing)} unavailable for this extraction")
    
    st.markdown("---")
    
    # Download Section
    st.markdown("#### ⬇️ Download Files")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if post_csv_string:
            st.download_button(
                label="💾 Download Post Data CSV",
                data=post_csv_string,
                file_name=f"polis_POST_metadata_{timestamp}.csv",
                mime="text/csv",
                use_container_width=True,
                key="download_post"
            )
        else:
            st.button("💾 Download Post Data CSV", disabled=True, use_container_width=True)
    
    with col2:
        if op_csv_string:
            st.download_button(
                label="💾 Download OP Data CSV",
                data=op_csv_string,
                file_name=f"polis_OP_metadata_{timestamp}.csv",
                mime="text/csv",
                use_container_width=True,
                key="download_op"
            )
        else:
            st.button("💾 Download OP Data CSV", disabled=True, use_container_width=True)
    
    # Show full tables
    with st.expander("📋 View Full Data Tables"):
        if df_post is not None and not df_post.empty:
            st.markdown("**Post Data**")
            st.dataframe(df_post, use_container_width=True)
            st.markdown("---")
        
        if df_op is not None and not df_op.empty:
            st.markdown("**Original Poster (OP) Data**")
            st.dataframe(df_op, use_container_width=True)
        
        if (df_post is None or df_post.empty) and (df_op is None or df_op.empty):
            st.warning("No data available to display")

# --- helpers ---
def fmt_text(v, na="N/A"):
    """Return text or N/A if missing/empty."""
    return v if (isinstance(v, str) and v.strip()) else (na if v in (None, "", []) else v)

def fmt_int(v, na="N/A"):
    """Format ints with thousands sep; N/A if missing."""
    # Check explicitly for None, not just falsy (to handle 0)
    if v is None:
        return na
    if isinstance(v, (int, float)):
        return f"{int(v):,}"
    return na

def fmt_percent(v, na="N/A"):
    """Format percentage to 2dp; N/A if missing."""
    return f"{float(v):.2f}%" if isinstance(v, (int, float)) else na

def fmt_platform(v, na="N/A"):
    return v.title() if isinstance(v, str) and v.strip() else na

def show_premium_features():
    """Display greyed-out additional features as teasers"""
    
    st.markdown('<div class="additional-section">', unsafe_allow_html=True)
    st.markdown("### 🔒 Additional Features")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.button(
            "🤖 Bot Detection Score",
            disabled=True,
            use_container_width=True,
            help="Analyze account authenticity and detect potential bot activity (Enterprise Feature)"
        )
        st.caption("Identify suspicious accounts spreading disinformation")
    
    with col2:
        st.button(
            "📁 Auto-Database Sync",
            disabled=True,
            use_container_width=True,
            help="Automatically sync extracted data to your database (Enterprise Feature)"
        )
        st.caption("Seamless integration with your data infrastructure")
    
    with col3:
        st.button(
            "🔍 Boolean Tag Search",
            disabled=True,
            use_container_width=True,
            help="Advanced filtering with AND/OR/NOT logic (Enterprise Feature)"
        )
        st.caption("Filter posts by complex hashtag combinations")
    
    st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
