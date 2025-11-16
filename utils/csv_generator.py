"""
CSV generation utilities
"""
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple
import json


def metadata_to_csv_row(metadata: Dict) -> Dict:
    """
    Convert metadata dictionary to CSV-friendly row
    Handles both new format (Post_/OP_ prefixed) and legacy format
    
    Args:
        metadata: Dictionary containing extracted metadata
        
    Returns:
        Dictionary formatted for CSV output
    """
    # Helper to get field with Post_ prefix or fallback to legacy
    def get_field(field_name):
        return metadata.get(f'Post_{field_name}') or metadata.get(field_name, '')
    
    row = {
        'timestamp': metadata.get('extraction_timestamp', datetime.now().isoformat()),
        'url': get_field('url'),
        'platform': get_field('platform'),
        'title': get_field('title'),
        'author': metadata.get('OP_username') or metadata.get('author', ''),
        'author_id': metadata.get('OP_id') or metadata.get('author_id', ''),
        'content': get_field('caption') or get_field('content'),
        'publish_date': get_field('date') or get_field('publish_date'),
        'likes': get_field('likes') or 0,
        'shares': get_field('shares') or 0,
        'comments': get_field('comments') or 0,
        'views': get_field('views') or 0,
        'hashtags': _format_list(get_field('hashtags') or []),
        'media_urls': _format_list(get_field('media_urls') or []),
        'engagement_rate': get_field('engagement_rate') or 0,
        'extraction_status': metadata.get('extraction_status', 'unknown'),
        'error_message': metadata.get('error_message', '')
    }
    
    return row


def separate_post_op_data(metadata: Dict) -> Tuple[Dict, Dict]:
    """
    Separate metadata into POST data and OP (Original Poster) data
    
    Args:
        metadata: Dictionary containing all extracted metadata
        
    Returns:
        Tuple of (post_data, op_data) dictionaries
    """
    post_data = {}
    op_data = {}
    
    for key, value in metadata.items():
        if key.startswith('Post_'):
            post_data[key] = value
        elif key.startswith('OP_'):
            op_data[key] = value
        elif key == '_op_data':
            # Handle stored OP data (from TikTok extractor)
            op_data.update(value)
        elif key in ['extraction_status', 'error_message', 'extraction_timestamp']:
            # Metadata fields - add to both
            post_data[key] = value
            op_data[key] = value
        else:
            # Legacy fields without prefix - add to post_data for backward compatibility
            post_data[key] = value
    
    return post_data, op_data


def post_data_to_csv_row(post_data: Dict) -> Dict:
    """
    Convert POST data dictionary to CSV-friendly row
    
    Args:
        post_data: Dictionary containing post metadata with Post_ prefix
        
    Returns:
        Dictionary formatted for CSV output
    """
    row = {}
    
    # Add all Post_ fields, removing the prefix for CSV column names
    for key, value in post_data.items():
        if key.startswith('Post_'):
            # Remove 'Post_' prefix for cleaner CSV headers
            clean_key = key[5:]  # Remove 'Post_' (5 characters)
            
            # Format lists as comma-separated strings
            if isinstance(value, list):
                row[clean_key] = _format_list(value)
            else:
                row[clean_key] = value
        elif key in ['extraction_status', 'error_message', 'extraction_timestamp', 'url']:
            # Keep these fields as-is
            row[key] = value
    
    # Ensure timestamp exists
    if 'extraction_timestamp' not in row:
        row['extraction_timestamp'] = datetime.now().isoformat()
    
    return row


def op_data_to_csv_row(op_data: Dict) -> Dict:
    """
    Convert OP (Original Poster) data dictionary to CSV-friendly row
    
    Args:
        op_data: Dictionary containing OP metadata with OP_ prefix
        
    Returns:
        Dictionary formatted for CSV output
    """
    row = {}
    
    # Add all OP_ fields, removing the prefix for CSV column names
    for key, value in op_data.items():
        if key.startswith('OP_'):
            # Remove 'OP_' prefix for cleaner CSV headers
            clean_key = key[3:]  # Remove 'OP_' (3 characters)
            
            # Format lists as comma-separated strings
            if isinstance(value, list):
                row[clean_key] = _format_list(value)
            else:
                row[clean_key] = value
        elif key in ['extraction_status', 'error_message', 'extraction_timestamp']:
            # Keep these fields as-is
            row[key] = value
    
    # Ensure timestamp exists
    if 'extraction_timestamp' not in row:
        row['extraction_timestamp'] = datetime.now().isoformat()
    
    return row


def _format_list(items: List) -> str:
    """
    Format list items for CSV (comma-separated string)
    
    Args:
        items: List of items
        
    Returns:
        Comma-separated string
    """
    if not items:
        return ''
    return ', '.join(str(item) for item in items)


def generate_csv(metadata_list: List[Dict]) -> pd.DataFrame:
    """
    Generate CSV DataFrame from list of metadata dictionaries
    Auto-detects if data is POST, OP, or legacy format
    
    Args:
        metadata_list: List of metadata dictionaries
        
    Returns:
        Pandas DataFrame ready for CSV export
    """
    if not metadata_list:
        return pd.DataFrame()
    
    # Check first item to determine format
    first_item = metadata_list[0]
    has_post_prefix = any(key.startswith('Post_') for key in first_item.keys())
    has_op_prefix = any(key.startswith('OP_') for key in first_item.keys())
    
    if has_post_prefix:
        rows = [post_data_to_csv_row(metadata) for metadata in metadata_list]
    elif has_op_prefix:
        rows = [op_data_to_csv_row(metadata) for metadata in metadata_list]
    else:
        # Legacy format
        rows = [metadata_to_csv_row(metadata) for metadata in metadata_list]
    
    df = pd.DataFrame(rows)
    
    return df


def generate_dual_csv(metadata_list: List[Dict]) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Generate separate POST and OP CSV DataFrames from metadata list
    
    Args:
        metadata_list: List of metadata dictionaries containing both POST and OP data
        
    Returns:
        Tuple of (post_df, op_df) DataFrames
    """
    post_rows = []
    op_rows = []
    
    for metadata in metadata_list:
        post_data, op_data = separate_post_op_data(metadata)
        
        if post_data:
            post_rows.append(post_data_to_csv_row(post_data))
        
        if op_data:
            op_rows.append(op_data_to_csv_row(op_data))
    
    post_df = pd.DataFrame(post_rows) if post_rows else pd.DataFrame()
    op_df = pd.DataFrame(op_rows) if op_rows else pd.DataFrame()
    
    return post_df, op_df


def save_csv(df: pd.DataFrame, filename: str = None) -> str:
    """
    Save DataFrame to CSV file
    
    Args:
        df: Pandas DataFrame
        filename: Optional filename (auto-generated if None)
        
    Returns:
        Filename of saved CSV
    """
    if filename is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'polis_metadata_{timestamp}.csv'
    
    df.to_csv(filename, index=False, encoding='utf-8')
    return filename


def csv_to_download_string(df: pd.DataFrame) -> str:
    """
    Convert DataFrame to CSV string for download
    
    Args:
        df: Pandas DataFrame
        
    Returns:
        CSV as string
    """
    return df.to_csv(index=False, encoding='utf-8')