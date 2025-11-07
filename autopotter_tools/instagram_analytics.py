#!/usr/bin/env python3
"""
Enhanced Instagram API Manager for Phase 2: Enhanced Data Collection.
This module expands the existing Instagram API to generate comprehensive account analytics JSON.
"""

import requests
import json
import sys, os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Add the parent directory to Python path to import config
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from simplelogger import Logger
except ImportError:
    from autopotter_tools.simplelogger import Logger
    
from config import get_config

class InstagramAnalyticsManager:
    """
    Enhanced Instagram API manager that generates comprehensive account analytics.
    Integrates with the new Phase 1 logging and configuration systems.

    Notes: 
     - Summary metrics are computed localy and likely unnecessary complexity.
     - Control parameters like post limits to grab should be in the config. 
     - account_insights could be more thorougly explored
     - media_insights should be more thorougly explored: https://developers.facebook.com/docs/instagram-platform/reference/instagram-media/insights
    """
    
    def __init__(self, config_path: str = "autopost_config.enhanced.json"):
        self.config = get_config(config_path)
        # self.instagram_config = self.config.get_instagram_config()
        
        self.base_url = "https://graph.facebook.com/v22.0"
        self.access_token = self.config.get('instagram_access_token', None)
        self.user_id = self.config.get('instagram_user_id', None)

        # Validate required configuration
        if not self.access_token:
            raise ValueError("Instagram access token not configured")
        if not self.user_id:
            raise ValueError("Instagram user ID not configured")
        
        
        # Configuration parameters for data retrieval limits
        self.max_media_items = self.config.get('max_media_items', 9)
        self.max_comments_per_media = self.config.get('max_comments_per_media', 9)
        self.max_replies_per_comment = self.config.get('max_replies_per_comment', 9)
        
        # Find Instagram Business Account through Facebook pages
        self.instagram_account_id = self.user_id
        self.page_access_token = self.access_token
        # self._find_instagram_account()

        if self.instagram_account_id is None or self.page_access_token is None:
            self.check_token_permissions()
            raise ValueError("During __INIT__, No Instagram Business Account found")
        
        Logger.info(f"Instagram Analytics Manager initialized with limits: media={self.max_media_items}, comments={self.max_comments_per_media}, replies={self.max_replies_per_comment}")
    
    def get_current_config(self) -> Dict[str, Any]:
        """
        Get the current configuration parameters for data retrieval limits.
        
        Returns:
            Dictionary containing current configuration values
        """
        return {
            'max_media_items': self.max_media_items,
            'max_comments_per_media': self.max_comments_per_media,
            'max_replies_per_comment': self.max_replies_per_comment
        }
    
    def _find_instagram_account(self):
        """Find the Instagram Business Account through Facebook pages."""
        try:
            # Get user's Facebook pages
            url = f"{self.base_url}/{self.user_id}/accounts"
            params = {"access_token": self.access_token}
            
            response = requests.get(url, params=params)
            if response.status_code == 200:
                accounts_data = response.json()
                
                for page in accounts_data.get('data', []):
                    page_id = page.get('id')
                    page_token = page.get('access_token')
                    
                    if page_id and page_token:
                        # Check if this page has an Instagram account
                        ig_url = f"{self.base_url}/{page_id}"
                        ig_params = {
                            "fields": "instagram_business_account",
                            "access_token": page_token
                        }
                        
                        ig_response = requests.get(ig_url, params=ig_params)
                        if ig_response.status_code == 200:
                            ig_data = ig_response.json()
                            if ig_data.get('instagram_business_account'):
                                self.instagram_account_id = ig_data['instagram_business_account']['id']
                                self.page_access_token = page_token
                                Logger.info(f"Found Instagram Business Account: {self.instagram_account_id}")
                                return
            
            if not self.instagram_account_id:
                Logger.warning("No Instagram Business Account found")
                
        except Exception as e:
            Logger.error(f"Failed to find Instagram account: {e}")
    
    def check_token_permissions(self) -> Dict[str, Any]:
        """
        Check the permissions and scopes available on the current access token.
        Provides verbose logging of all available permissions, expiration dates, and metadata.
        
        Returns:
            Dictionary containing comprehensive token permission information
        """
        Logger.info("🔍 Checking token permissions and scopes...")
        
        try:
            url = "https://graph.facebook.com/debug_token"
            params = {
                "input_token": self.access_token,
                "access_token": self.access_token
            }
            
            response = requests.get(url, params=params)
            if response.status_code != 200:
                Logger.error(f"❌ Failed to check token permissions: {response.status_code} - {response.text}")
                return {
                    'error': f'API error: {response.status_code}',
                    'available_scopes': [],
                    'missing_scopes': []
                }
            
            token_data = response.json()
            if 'data' not in token_data:
                Logger.error("❌ No token data in response")
                return {
                    'error': 'No token data in response',
                    'available_scopes': [],
                    'missing_scopes': []
                }
            
            data = token_data['data']
            available_scopes = data.get('scopes', [])
            
            # Define required scopes for Instagram operations
            required_scopes = [
                'instagram_basic',
                'instagram_content_publish', 
                'instagram_manage_comments',
                'instagram_manage_insights',
                'pages_read_engagement',
                'pages_manage_metadata'
            ]
            
            # Find missing scopes
            missing_scopes = [scope for scope in required_scopes if scope not in available_scopes]
            
            # Check if we have Instagram Business Account access
            has_instagram_access = 'instagram_basic' in available_scopes
            
            # Extract and format expiration information
            expires_at = data.get('expires_at')
            data_access_expires_at = data.get('data_access_expires_at')
            
            # Format expiration dates for human readability
            expires_date = None
            data_access_expires_date = None
            if expires_at:
                expires_date = datetime.fromtimestamp(expires_at).strftime('%Y-%m-%d %H:%M:%S UTC')
            if data_access_expires_at:
                data_access_expires_date = datetime.fromtimestamp(data_access_expires_at).strftime('%Y-%m-%d %H:%M:%S UTC')
            
            # Calculate time until expiration
            current_time = datetime.now()
            expires_in_days = None
            data_access_expires_in_days = None
            
            if expires_at:
                expires_datetime = datetime.fromtimestamp(expires_at)
                expires_in_days = (expires_datetime - current_time).days
            if data_access_expires_at:
                data_access_expires_datetime = datetime.fromtimestamp(data_access_expires_at)
                data_access_expires_in_days = (data_access_expires_datetime - current_time).days
            
            permission_info = {
                'app_id': data.get('app_id'),
                'user_id': data.get('user_id'),
                'available_scopes': available_scopes,
                'missing_scopes': missing_scopes,
                'has_instagram_access': has_instagram_access,
                'expires_at': expires_at,
                'expires_date': expires_date,
                'expires_in_days': expires_in_days,
                'data_access_expires_at': data_access_expires_at,
                'data_access_expires_date': data_access_expires_date,
                'data_access_expires_in_days': data_access_expires_in_days,
                'is_valid': len(missing_scopes) == 0,
                'scope_count': len(available_scopes),
                'missing_count': len(missing_scopes),
                'token_type': data.get('type'),
                'application': data.get('application'),
                'granular_scopes': data.get('granular_scopes', []),
                'is_valid_token': data.get('is_valid', False),
                'issued_at': data.get('issued_at'),
                'issued_date': datetime.fromtimestamp(data.get('issued_at', 0)).strftime('%Y-%m-%d %H:%M:%S UTC') if data.get('issued_at') else None
            }
            
            # Verbose logging of all permissions and metadata
            Logger.info("🔑 Token Permission Analysis Complete")
            Logger.info(f"📱 App ID: {data.get('app_id', 'Unknown')}")
            Logger.info(f"👤 User ID: {data.get('user_id', 'Unknown')}")
            Logger.info(f"📋 Token Type: {data.get('type', 'Unknown')}")
            Logger.info(f"🏢 Application: {data.get('application', 'Unknown')}")
            
            # Log scope information
            Logger.info(f"✅ Available Scopes ({len(available_scopes)}): {', '.join(available_scopes)}")
            if missing_scopes:
                Logger.warning(f"❌ Missing Required Scopes ({len(missing_scopes)}): {', '.join(missing_scopes)}")
            else:
                Logger.info("🎉 All required scopes are available!")
            
            # Log Instagram access status
            if has_instagram_access:
                Logger.info("📸 Instagram access: ✅ Available")
            else:
                Logger.warning("📸 Instagram access: ❌ Not available (missing instagram_basic scope)")
            
            # Log expiration information
            if expires_at:
                Logger.info(f"⏰ Token expires: {expires_date}")
                if expires_in_days is not None:
                    if expires_in_days > 30:
                        Logger.info(f"⏰ Token expires in: {expires_in_days} days")
                    elif expires_in_days > 7:
                        Logger.warning(f"⚠️ Token expires in: {expires_in_days} days")
                    elif expires_in_days > 0:
                        Logger.error(f"🚨 Token expires in: {expires_in_days} days!")
                    else:
                        Logger.error(f"🚨 Token expired {abs(expires_in_days)} days ago!")
            else:
                Logger.info("⏰ Token expiration: Never (long-lived token)")
            
            if data_access_expires_at:
                Logger.info(f"🔒 Data access expires: {data_access_expires_date}")
                if data_access_expires_in_days is not None:
                    if data_access_expires_in_days > 30:
                        Logger.info(f"🔒 Data access expires in: {data_access_expires_in_days} days")
                    elif data_access_expires_in_days > 7:
                        Logger.warning(f"⚠️ Data access expires in: {data_access_expires_in_days} days")
                    elif data_access_expires_in_days > 0:
                        Logger.error(f"🚨 Data access expires in: {data_access_expires_in_days} days!")
                    else:
                        Logger.error(f"🚨 Data access expired {abs(data_access_expires_in_days)} days ago!")
            
            # Log granular scopes if available
            if data.get('granular_scopes'):
                granular_scopes = data.get('granular_scopes', [])
                if isinstance(granular_scopes, list) and granular_scopes:
                    # Handle granular scopes which can be complex objects
                    scope_strings = []
                    for scope in granular_scopes:
                        if isinstance(scope, str):
                            scope_strings.append(scope)
                        elif isinstance(scope, dict):
                            # Extract scope name from dict if available
                            scope_name = scope.get('scope', str(scope))
                            scope_strings.append(str(scope_name))
                        else:
                            scope_strings.append(str(scope))
                    Logger.info(f"🔍 Granular Scopes: {', '.join(scope_strings)}")
                else:
                    Logger.info(f"🔍 Granular Scopes: {granular_scopes}")
            
            # Log token validity
            if data.get('is_valid', False):
                Logger.info("✅ Token is valid")
            else:
                Logger.error("❌ Token is invalid!")
            
            # Log issuance date
            if data.get('issued_at'):
                issued_date = datetime.fromtimestamp(data.get('issued_at')).strftime('%Y-%m-%d %H:%M:%S UTC')
                Logger.info(f"📅 Token issued: {issued_date}")
            
            # Summary
            Logger.info(f"📊 Summary: {len(available_scopes)} scopes available, {len(missing_scopes)} missing, Instagram access: {'✅' if has_instagram_access else '❌'}")
            
            return permission_info
            
        except Exception as e:
            Logger.error(f"❌ Failed to check token permissions: {e}")
            return {
                'error': str(e),
                'available_scopes': [],
                'missing_scopes': []
            }
    
    def test_available_fields(self) -> Dict[str, Any]:
        """
        Test different field combinations to see what's available from Instagram API.
        
        Returns:
            Dictionary containing test results for different field combinations
        """
        if not self.instagram_account_id:
            return {}
        
        field_combinations = [
            # "id,username",
            # "id,username,name",
            # "id,username,biography",
            # "id,username,website",
            # "id,username,profile_picture_url",
            # "id,username,followers_count",
            # "id,username,follows_count",
            # "id,username,media_count",
            "id,username,name,biography,website,profile_picture_url,followers_count,follows_count,media_count"
        ]
        
        results = {}
        
        for fields in field_combinations:
            try:
                url = f"{self.base_url}/{self.instagram_account_id}"
                params = {
                    "fields": fields,
                    "access_token": self.page_access_token
                }
                
                response = requests.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    results[fields] = {
                        'status': 'success',
                        'fields_returned': list(data.keys()),
                        'data': data
                    }
                else:
                    results[fields] = {
                        'status': 'error',
                        'status_code': response.status_code,
                        'error': response.text
                    }
                    
            except Exception as e:
                results[fields] = {
                    'status': 'exception',
                    'error': str(e)
                }
        
        return results
    
    def test_insights_configurations(self) -> Dict[str, Any]:
        """
        Test specific insights API configurations for all supported metrics and periods.
        
        Returns:
            Dictionary containing test results for different configurations
        """
        if not self.instagram_account_id:
            return {}
        
        # Define the specific metrics to test
        metrics_to_test = [
            "reach",
            "follower_count", 
            "website_clicks",
            "profile_views",
            "online_followers",
            "accounts_engaged",
            "total_interactions",
            "likes",
            "comments"
        ]
        
        # Define periods to test
        periods_to_test = ["day", "week", "days_28"]
        
        results = {}
        
        for metric in metrics_to_test:
            for period in periods_to_test:
                # Special handling for profile_views
                if metric == "profile_views":
                    config = {
                        "metric": metric,
                        "period": period,
                        "metric_type": "total_value"
                    }
                else:
                    config = {
                        "metric": metric,
                        "period": period
                    }
                
                try:
                    url = f"{self.base_url}/{self.instagram_account_id}/insights"
                    params = {
                        "access_token": self.page_access_token,
                        **config
                    }
                    
                    response = requests.get(url, params=params)
                    results[f"{metric}_{period}"] = {
                        'status_code': response.status_code,
                        'success': response.status_code == 200,
                        'response': response.text[:200] if response.status_code != 200 else 'Success',
                        'config': config
                    }
                    
                except Exception as e:
                    results[f"{metric}_{period}"] = {
                        'status_code': 'Exception',
                        'success': False,
                        'response': str(e),
                        'config': config
                    }
        
        return results
    
    def get_account_insights(self) -> Dict[str, Any]:
        """
        Get Instagram account insights including follower count and other metrics.
        
        Returns:
            Dictionary containing account insights
        """
        if not self.instagram_account_id:
            return {}
        
        try:
            # Aggregate insights across multiple valid configurations and periods
            url = f"{self.base_url}/{self.instagram_account_id}/insights"
            aggregated: Dict[str, Dict[str, Any]] = {}
            
            # Define per-metric rules to maximize success based on test results
            metrics_info = [
                {"name": "follower_count", "periods": ["day"], "extra": {}},
                {"name": "reach", "periods": ["day", "week", "days_28"], "extra": {}},
                {"name": "profile_views", "periods": ["day"], "extra": {"metric_type": "total_value"}},
                {"name": "website_clicks", "periods": ["day", "week", "days_28"], "extra": {"metric_type": "total_value"}},
                {"name": "online_followers", "periods": ["day"], "extra": {}},
                {"name": "accounts_engaged", "periods": ["day", "week", "days_28"], "extra": {"metric_type": "total_value"}},
                {"name": "total_interactions", "periods": ["day", "week", "days_28"], "extra": {"metric_type": "total_value"}},
                {"name": "likes", "periods": ["day", "week", "days_28"], "extra": {"metric_type": "total_value"}},
                {"name": "comments", "periods": ["day", "week", "days_28"], "extra": {"metric_type": "total_value"}}
            ]
            
            for metric in metrics_info:
                metric_name = metric["name"]
                for period in metric["periods"]:
                    params = {
                        "metric": metric_name,
                        "period": period,
                        "access_token": self.page_access_token,
                        **metric.get("extra", {})
                    }
                    response = requests.get(url, params=params)
                    if response.status_code != 200:
                        Logger.debug(f"Insights request failed metric={metric_name} period={period}: {response.status_code} - {response.text}")
                        continue
                    insights_data = response.json()
                    Logger.debug(f"Insights response for {metric_name} {period}: {insights_data}")
                    for insight in insights_data.get('data', []):
                        name = insight.get('name')
                        if name not in aggregated:
                            aggregated[name] = {}
                        # Prefer total_value, otherwise take the last value in 'values'
                        value_to_store = None
                        total_value = insight.get('total_value')
                        if isinstance(total_value, dict) and 'value' in total_value:
                            value_to_store = total_value['value']
                        else:
                            values = insight.get('values') or []
                            if len(values) > 0 and 'value' in values[-1]:
                                value_to_store = values[-1]['value']
                        if value_to_store is not None:
                            aggregated[name][period] = value_to_store
                            Logger.debug(f"Stored {name}[{period}] = {value_to_store}")
                        else:
                            Logger.debug(f"No value found for {name} {period}, insight: {insight}")
            
            Logger.info(f"Successfully aggregated {len(aggregated)} metrics: {list(aggregated.keys())}")
            for metric, periods in aggregated.items():
                Logger.info(f"  {metric}: {periods}")
            return aggregated
                
        except Exception as e:
            Logger.warning(f"Could not retrieve account insights: {e}")
            return {}
    
    def get_account_info(self) -> Dict[str, Any]:
        """
        Retrieve comprehensive Instagram account information.
        
        Returns:
            Dictionary containing Instagram account analytics
        """
        Logger.info("Retrieving Instagram account information")
        
        if not self.instagram_account_id:
            Logger.warning("No Instagram Business Account found")
            return {
                'account_id': self.user_id,
                'username': 'Unknown',
                'media_count': 0,
                'followers_count': 0,
                'following_count': 0,
                'biography': '',
                'website': '',
                'profile_picture_url': '',
                'retrieved_at': datetime.now().isoformat()
            }
        
        try:
            # Get Instagram Business Account info with comprehensive fields
            url = f"{self.base_url}/{self.instagram_account_id}"
            params = {
                "fields": "id,username,name,biography,website,profile_picture_url,followers_count,follows_count,media_count",
                "access_token": self.page_access_token
            }
            
            response = requests.get(url, params=params)
            if response.status_code != 200:
                Logger.error(f"Failed to retrieve Instagram account info: {response.status_code} - {response.text}")
                # Fallback to basic info
                return {
                    'account_id': self.instagram_account_id,
                    'username': 'Instagram Account',
                    'media_count': 0,
                    'followers_count': 0,
                    'following_count': 0,
                    'biography': '',
                    'website': '',
                    'profile_picture_url': '',
                    'retrieved_at': datetime.now().isoformat(),
                    
                }
            
            account_data = response.json()
            Logger.debug(f"Instagram account data retrieved: {account_data}")
            
            # Get account insights for additional metrics
            account_insights = self.get_account_insights()
            followers_count = account_data.get('followers_count', 0) or account_insights.get('follower_count', 0)
            
            return {
                'account_id': account_data.get('id'),
                'username': account_data.get('username', 'Unknown'),
                'name': account_data.get('name', ''),
                'media_count': account_data.get('media_count', 0),
                'followers_count': followers_count,
                'following_count': account_data.get('follows_count', 0),
                'biography': account_data.get('biography', ''),
                'website': account_data.get('website', ''),
                'profile_picture_url': account_data.get('profile_picture_url', ''),
                'retrieved_at': datetime.now().isoformat(),
                'account_insights': account_insights
            }
            
        except Exception as e:
            Logger.error(f"Failed to retrieve Instagram account info: {e}")
            raise
    
    def get_comprehensive_account_info(self) -> Dict[str, Any]:
        """
        Get comprehensive account information including token permissions and Instagram data.
        
        Returns:
            Dictionary containing complete account analytics with permissions
        """
        Logger.info("Retrieving comprehensive Instagram account information")
        
        # Get basic account info
        account_info = self.get_account_info()
        
        # Check token permissions
        permissions = self.check_token_permissions()
        
        # Get recent media count
        recent_media = self.get_recent_media(limit=1)
        media_count = len(recent_media) if recent_media else 0
        
        # Combine all information
        comprehensive_info = {
            **account_info,
            'token_permissions': permissions,
            'recent_media_count': media_count,
            'instagram_account_found': self.instagram_account_id is not None,
            'instagram_account_id': self.instagram_account_id,
            'analysis_timestamp': datetime.now().isoformat()
        }
        
        # Add permission-based insights
        if permissions.get('is_valid'):
            comprehensive_info['permission_status'] = 'full_access'
            comprehensive_info['can_publish'] = 'instagram_content_publish' in permissions.get('available_scopes', [])
            comprehensive_info['can_manage_comments'] = 'instagram_manage_comments' in permissions.get('available_scopes', [])
            comprehensive_info['can_view_insights'] = 'instagram_manage_insights' in permissions.get('available_scopes', [])
        else:
            comprehensive_info['permission_status'] = 'limited_access'
            comprehensive_info['missing_permissions'] = permissions.get('missing_scopes', [])
        
        return comprehensive_info
    
    def get_recent_media(self, limit: int = None) -> List[Dict[str, Any]]:
        """
        Retrieve recent media posts from Instagram Business Account.
        
        Args:
            limit: Maximum number of media items to retrieve (defaults to config value)
            
        Returns:
            List of media items with engagement data
        """
        # Use config limit if none specified
        if limit is None:
            limit = self.max_media_items
            
        Logger.info(f"Retrieving recent Instagram media (limit: {limit})")
        
        if not self.instagram_account_id:
            Logger.warning("No Instagram Business Account found")
            return []
        
        try:
            # Get media from Instagram Business Account
            url = f"{self.base_url}/{self.instagram_account_id}/media"
            params = {
                "fields": "id,media_type,media_url,thumbnail_url,permalink,timestamp,caption,like_count,comments_count",
                "access_token": self.page_access_token,
                "limit": limit
            }
            
            response = requests.get(url, params=params)
            if response.status_code != 200:
                Logger.error(f"Failed to retrieve Instagram media: {response.status_code} - {response.text}")
                return []
            
            media_data = response.json()
            media_items = []
            
            for item in media_data.get('data', []):
                media_item = {
                    'id': item.get('id'),
                    'media_type': item.get('media_type', 'unknown'),
                    'media_url': item.get('media_url'),
                    'thumbnail_url': item.get('thumbnail_url'),
                    'permalink': item.get('permalink'),
                    'timestamp': item.get('timestamp'),
                    'caption': item.get('caption', ''),
                    'like_count': item.get('like_count', 0),
                    'comments_count': item.get('comments_count', 0),
                    'insights': {}
                }
                
                # Handle caption format (sometimes it's a dict with 'text' field)
                if isinstance(media_item['caption'], dict):
                    media_item['caption'] = media_item['caption'].get('text', '')
                
                # Fetch comments for this media item
                comments = self.get_media_comments(item.get('id'))
                media_item['comments'] = comments
                
                # Fetch insights for this media item
                insights = self.get_media_insights(item.get('id'), item.get('media_type'))
                media_item['insights'] = insights
                
                media_items.append(media_item)
            
            Logger.info(f"Retrieved {len(media_items)} Instagram media items")
            return media_items
            
        except Exception as e:
            Logger.error(f"Failed to retrieve Instagram media: {e}")
            return []
    
    def get_media_comments(self, media_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve comments for a specific media item including nested replies.
        
        Args:
            media_id: Instagram media ID
            
        Returns:
            List of comments with user information, text, timestamp, and replies
        """
        if not media_id:
            return []
        
        try:
            url = f"{self.base_url}/{media_id}/comments"
            params = {
                "fields": "id,text,timestamp,username,from,like_count",
                "access_token": self.page_access_token,
                "limit": self.max_comments_per_media
            }
            
            response = requests.get(url, params=params)
            if response.status_code != 200:
                Logger.debug(f"Failed to retrieve comments for media {media_id}: {response.status_code} - {response.text}")
                return []
            
            comments_data = response.json()
            comments = []
            
            for comment in comments_data.get('data', []):
                comment_item = {
                    'id': comment.get('id'),
                    'text': comment.get('text', ''),
                    'timestamp': comment.get('timestamp'),
                    'username': comment.get('username'),
                    'from': comment.get('from', {}),
                    'like_count': comment.get('like_count', 0)
                }
                
                # Keep only the 'from' object - no need to duplicate user information
                
                # Fetch replies for this comment
                replies = self.get_comment_replies(comment.get('id'))
                comment_item['replies'] = replies
                
                comments.append(comment_item)
            
            return comments
            
        except Exception as e:
            Logger.debug(f"Failed to retrieve comments for media {media_id}: {e}")
            return []
    
    def get_comment_replies(self, comment_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve replies for a specific comment.
        
        Args:
            comment_id: Instagram comment ID
            
        Returns:
            List of reply comments with user information, text, and timestamp
        """
        if not comment_id:
            return []
        
        try:
            url = f"{self.base_url}/{comment_id}/replies"
            params = {
                "fields": "id,text,timestamp,username,from,like_count",
                "access_token": self.page_access_token,
                "limit": self.max_replies_per_comment
            }
            
            response = requests.get(url, params=params)
            if response.status_code != 200:
                Logger.debug(f"Failed to retrieve replies for comment {comment_id}: {response.status_code} - {response.text}")
                return []
            
            replies_data = response.json()
            replies = []
            
            for reply in replies_data.get('data', []):
                reply_item = {
                    'id': reply.get('id'),
                    'text': reply.get('text', ''),
                    'timestamp': reply.get('timestamp'),
                    'username': reply.get('username'),
                    'from': reply.get('from', {}),
                    'like_count': reply.get('like_count', 0)
                }
                
                # Keep only the 'from' object - no need to duplicate user information
                
                replies.append(reply_item)
            
            return replies
            
        except Exception as e:
            Logger.debug(f"Failed to retrieve replies for comment {comment_id}: {e}")
            return []
    
    def get_media_insights(self, media_id: str, media_type: str) -> Dict[str, Any]:
        """
        Retrieve insights for a specific media item.
        
        Args:
            media_id: Instagram media ID
            media_type: Type of media (IMAGE, VIDEO, CAROUSEL_ALBUM)
            
        Returns:
            Dictionary containing media insights
        """
        if not media_id:
            return {}
        
        try:
            url = f"{self.base_url}/{media_id}/insights"
            
            # Different metrics available based on media type and Instagram API documentation
            if media_type == "VIDEO":
                # For video content (REELS), use available metrics
                metrics = "reach,likes,comments,saved,shares,total_interactions,views"
            elif media_type == "IMAGE":
                # For image content (FEED posts), use available metrics
                metrics = "reach,likes,comments,saved,shares,total_interactions,profile_visits,profile_activity"
            elif media_type == "CAROUSEL_ALBUM":
                # For carousel content (FEED posts), use available metrics
                metrics = "reach,likes,comments,saved,shares,total_interactions,profile_visits,profile_activity"
            else:
                # Default to basic metrics for unknown types
                metrics = "reach,likes,comments,saved,shares"
            
            params = {
                "metric": metrics,
                "access_token": self.page_access_token
                # Note: period is automatically set to "lifetime" by Instagram API
            }
            
            response = requests.get(url, params=params)
            if response.status_code != 200:
                Logger.debug(f"Failed to retrieve insights for media {media_id}: {response.status_code} - {response.text}")
                return {}
            
            insights_data = response.json()
            insights = {}
            
            for insight in insights_data.get('data', []):
                metric_name = insight.get('name')
                if insight.get('values') and len(insight['values']) > 0:
                    insights[metric_name] = insight['values'][0].get('value', 0)
            
            return insights
            
        except Exception as e:
            Logger.debug(f"Failed to retrieve insights for media {media_id}: {e}")
            return {}
    
    def get_video_insights(self, media_id: str) -> Dict[str, Any]:
        """
        Retrieve detailed insights for a specific video.
        
        Args:
            media_id: Instagram media ID
            
        Returns:
            Dictionary containing video insights
        """
        Logger.info(f"Retrieving video insights for media ID: {media_id}")
        
        try:
            url = f"{self.base_url}/{media_id}/insights"
            params = {
                "metric": "impressions,reach,engagement,plays,saved,shares,comments,likes",
                "access_token": self.access_token
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            insights_data = response.json()
            
            insights = {}
            for insight in insights_data.get('data', []):
                insights[insight['name']] = insight['values'][0]['value']
            
            Logger.debug(f"Video insights retrieved: {insights}")
            return insights
            
        except Exception as e:
            Logger.error(f"Failed to retrieve video insights: {e}")
            return {}
    
    def get_recent_comments(self, media_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve recent comments for a specific media item.
        
        Args:
            media_id: Instagram media ID
            limit: Maximum number of comments to retrieve
            
        Returns:
            List of comments with user and engagement data
        """
        Logger.info(f"Retrieving recent comments for media ID: {media_id}")
        
        try:
            url = f"{self.base_url}/{media_id}/comments"
            params = {
                "fields": "id,text,timestamp,username,like_count",
                "access_token": self.access_token,
                "limit": limit
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            comments_data = response.json()
            
            comments = []
            for comment in comments_data.get('data', []):
                comments.append({
                    'id': comment.get('id'),
                    'text': comment.get('text', ''),
                    'timestamp': comment.get('timestamp'),
                    'username': comment.get('username', ''),
                    'like_count': comment.get('like_count', 0)
                })
            
            Logger.debug(f"Retrieved {len(comments)} comments")
            return comments
            
        except Exception as e:
            Logger.error(f"Failed to retrieve comments: {e}")
            return []
    
    
    def get_recent_activity(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Retrieve recent account activity from Instagram Business Account.
        
        Args:
            limit: Maximum number of activity items to retrieve
            
        Returns:
            List of recent activity items
        """
        Logger.info(f"Retrieving recent Instagram activity (limit: {limit})")
        
        if not self.instagram_account_id:
            Logger.warning("No Instagram Business Account found")
            return []
        
        try:
            # Get recent media from Instagram Business Account
            url = f"{self.base_url}/{self.instagram_account_id}/media"
            params = {
                "fields": "id,media_type,timestamp,like_count,comments_count",
                "access_token": self.page_access_token,
                "limit": limit
            }
            
            response = requests.get(url, params=params)
            if response.status_code != 200:
                Logger.error(f"Failed to retrieve Instagram activity: {response.status_code} - {response.text}")
                return []
            
            media_data = response.json()
            activity_items = []
            
            for item in media_data.get('data', []):
                activity_item = {
                    'media_id': item.get('id'),
                    'media_type': item.get('media_type'),
                    'timestamp': item.get('timestamp'),
                    'engagement_metrics': {
                        'likes': item.get('like_count', 0),
                        'comments': item.get('comments_count', 0),
                        'total_engagement': item.get('like_count', 0) + item.get('comments_count', 0)
                    }
                }
                
                activity_items.append(activity_item)
            
            Logger.info(f"Retrieved {len(activity_items)} Instagram activity items")
            return activity_items
            
        except Exception as e:
            Logger.error(f"Failed to retrieve Instagram activity: {e}")
            return []
    
    def get_hashtag_performance(self, hashtags: List[str] = None) -> Dict[str, Any]:
        """
        Analyze performance of posts with specific hashtags.
        
        Args:
            hashtags: List of hashtags to analyze (without #)
            
        Returns:
            Dictionary containing hashtag performance data
        """
        Logger.info(f"Analyzing hashtag performance for: {hashtags}")
        
        if not hashtags:
            hashtags = ['3dprinting', 'pottery', 'ceramics', 'art', 'design']
        
        try:
            # Get recent media to analyze hashtag usage
            recent_media = self.get_recent_media(limit=50)
            
            hashtag_stats = {}
            for hashtag in hashtags:
                hashtag_stats[hashtag] = {
                    'usage_count': 0,
                    'total_likes': 0,
                    'total_comments': 0,
                    'total_impressions': 0,
                    'avg_engagement_rate': 0
                }
            
            # Analyze hashtag usage in recent posts
            for media in recent_media:
                caption = media.get('caption', '').lower()
                
                for hashtag in hashtags:
                    if f"#{hashtag}" in caption or f"#{hashtag.lower()}" in caption:
                        hashtag_stats[hashtag]['usage_count'] += 1
                        hashtag_stats[hashtag]['total_likes'] += media.get('like_count', 0)
                        hashtag_stats[hashtag]['total_comments'] += media.get('comments_count', 0)
                        
                        # Add insights if available
                        if 'insights' in media and 'impressions' in media['insights']:
                            hashtag_stats[hashtag]['total_impressions'] += media['insights']['impressions']
            
            # Calculate averages
            for hashtag in hashtags:
                if hashtag_stats[hashtag]['usage_count'] > 0:
                    avg_likes = hashtag_stats[hashtag]['total_likes'] / hashtag_stats[hashtag]['usage_count']
                    avg_comments = hashtag_stats[hashtag]['total_comments'] / hashtag_stats[hashtag]['usage_count']
                    
                    hashtag_stats[hashtag]['avg_likes'] = round(avg_likes, 1)
                    hashtag_stats[hashtag]['avg_comments'] = round(avg_comments, 1)
                    
                    if hashtag_stats[hashtag]['total_impressions'] > 0:
                        engagement_rate = ((hashtag_stats[hashtag]['total_likes'] + hashtag_stats[hashtag]['total_comments']) / 
                                         hashtag_stats[hashtag]['total_impressions']) * 100
                        hashtag_stats[hashtag]['avg_engagement_rate'] = round(engagement_rate, 2)
            
            Logger.debug(f"Hashtag performance analysis completed")
            return hashtag_stats
            
        except Exception as e:
            Logger.error(f"Failed to analyze hashtag performance: {e}")
            return {}
    
    def export_to_json(self, output_path: str = None) -> Dict[str, Any]:
        """
        Generate comprehensive Instagram analytics JSON document.
        
        Args:
            output_path: Optional path to save JSON file
            
        Returns:
            Dictionary containing all analytics data
        """
        Logger.info("Generating comprehensive Instagram analytics JSON")
        
        try:
            # Collect all analytics data
            analytics_data = {
                'export_info': {
                    'exported_at': datetime.now().isoformat(),
                    'export_version': '2.0',
                    'source': 'instagram_analytics_manager',
                    'configuration': self.get_current_config()
                },
                'account_info': self.get_account_info(),
                'recent_media': self.get_recent_media(),
                # 'recent_activity': self.get_recent_activity(limit=20),
                # 'hashtag_performance': self.get_hashtag_performance(),
                'summary_metrics': {}
            }
            
            # Calculate summary metrics
            total_likes = sum(media.get('like_count', 0) for media in analytics_data['recent_media'])
            total_comments = sum(media.get('comments_count', 0) for media in analytics_data['recent_media'])
            total_impressions = 0
            
            for media in analytics_data['recent_media']:
                if 'insights' in media and 'impressions' in media['insights']:
                    total_impressions += media['insights']['impressions']
            
            analytics_data['summary_metrics'] = {
                'total_recent_likes': total_likes,
                'total_recent_comments': total_comments,
                'total_recent_impressions': total_impressions,
                'avg_engagement_rate': round(((total_likes + total_comments) / max(total_impressions, 1)) * 100, 2) if total_impressions > 0 else 0,
                'media_count_analyzed': len(analytics_data['recent_media'])
            }
            
            # Save to file if output path provided
            if output_path:
                with open(output_path, 'w') as f:
                    json.dump(analytics_data, f, indent=2)
                Logger.info(f"Analytics data saved to: {output_path}")
            
            Logger.info("Instagram analytics JSON generation completed")
            return analytics_data
            
        except Exception as e:
            Logger.error(f"Failed to export analytics to JSON: {e}")
            raise
    
    def get_latest_video_performance(self) -> Dict[str, Any]:
        """
        Get performance metrics for the most recent video post.
        
        Returns:
            Dictionary containing latest video performance data
        """
        Logger.info("Retrieving latest video performance metrics")
        
        try:
            # Get recent media and find the latest video
            recent_media = self.get_recent_media(limit=10)
            video_posts = [media for media in recent_media if media.get('media_type') == 'VIDEO']
            
            if not video_posts:
                Logger.warning("No video posts found in recent media")
                return {}
            
            latest_video = video_posts[0]  # Already sorted by timestamp
            
            # Get detailed insights for the video
            video_insights = self.get_video_insights(latest_video['id'])
            recent_comments = self.get_recent_comments(latest_video['id'], limit=20)
            
            video_performance = {
                'video_id': latest_video['id'],
                'permalink': latest_video['permalink'],
                'caption': latest_video['caption'],
                'timestamp': latest_video['timestamp'],
                'engagement_metrics': {
                    'likes': latest_video.get('like_count', 0),
                    'comments': latest_video.get('comments_count', 0),
                    'impressions': video_insights.get('impressions', 0),
                    'reach': video_insights.get('reach', 0),
                    'plays': video_insights.get('plays', 0),
                    'saved': video_insights.get('saved', 0),
                    'shares': video_insights.get('shares', 0)
                },
                'recent_comments': recent_comments,
                'performance_summary': {
                    'engagement_rate': 0,
                    'play_rate': 0,
                    'comment_quality': 'low' if latest_video.get('comments_count', 0) < 5 else 'medium' if latest_video.get('comments_count', 0) < 15 else 'high'
                }
            }
            
            # Calculate engagement rate
            if video_insights.get('impressions', 0) > 0:
                engagement_rate = ((latest_video.get('like_count', 0) + latest_video.get('comments_count', 0)) / 
                                 video_insights['impressions']) * 100
                video_performance['performance_summary']['engagement_rate'] = round(engagement_rate, 2)
            
            # Calculate play rate
            if video_insights.get('impressions', 0) > 0:
                play_rate = (video_insights.get('plays', 0) / video_insights['impressions']) * 100
                video_performance['performance_summary']['play_rate'] = round(play_rate, 2)
            
            Logger.info(f"Latest video performance retrieved: {latest_video['id']}")
            return video_performance
            
        except Exception as e:
            Logger.error(f"Failed to retrieve latest video performance: {e}")
            return {}

def main():
    """CLI entrypoint for Instagram Analytics Manager."""
    try:
        import argparse
        
        parser = argparse.ArgumentParser(description="Instagram Analytics Manager")
        parser.add_argument("--fulltest", 
                            action='store_true',
                            help="Run full diagnostics (account info, permissions, field/insights tests) before exporting")
        parser.add_argument("-o", "--output", 
                            type=str,
                            default="instagram_analytics_result.json", 
                            help="Output JSON file path")
        args = parser.parse_args()
        
        print("🚀 Instagram Analytics Manager")
        print("=" * 50)
        
        # Initialize the manager
        analytics_manager = InstagramAnalyticsManager()
        print("✅ Manager initialized successfully")
        
        # Display current configuration
        config = analytics_manager.get_current_config()
        print(f"\n⚙️  Current Configuration:")
        print(f"  Max Media Items: {config['max_media_items']}")
        print(f"  Max Comments per Media: {config['max_comments_per_media']}")
        print(f"  Max Replies per Comment: {config['max_replies_per_comment']}")
        
        if args.fulltest:
            # Get account info with permissions
            print("\n🔍 Retrieving account information and permissions...")
            account_info = analytics_manager.get_comprehensive_account_info()
            
            # Display complete account information
            print(f"\n📊 Account Information:")
            print(f"  Username: {account_info.get('username', 'Unknown')}")
            print(f"  Account ID: {account_info.get('account_id', 'Unknown')}")
            print(f"  Instagram Connected: {account_info.get('instagram_account_found', False)}")
            print(f"  Instagram Account ID: {account_info.get('instagram_account_id', 'None')}")
            print(f"  Recent Media Count: {account_info.get('recent_media_count', 0)}")
            print(f"  Retrieved At: {account_info.get('retrieved_at', 'Unknown')}")
            print(f"  Analysis Timestamp: {account_info.get('analysis_timestamp', 'Unknown')}")
            
            # Display complete permission information
            permissions = account_info.get('token_permissions', {})
            if permissions:
                print(f"\n🔐 Token Permissions:")
                print(f"  App ID: {permissions.get('app_id', 'Unknown')}")
                print(f"  User ID: {permissions.get('user_id', 'Unknown')}")
                print(f"  Available Scopes: {permissions.get('scope_count', 0)}")
                print(f"  Missing Scopes: {permissions.get('missing_count', 0)}")
                print(f"  Has Instagram Access: {permissions.get('has_instagram_access', False)}")
                print(f"  Is Valid: {permissions.get('is_valid', False)}")
                print(f"  Expires At: {permissions.get('expires_at', 'Unknown')}")
                print(f"  Data Access Expires At: {permissions.get('data_access_expires_at', 'Unknown')}")
                
                # Show all available scopes
                available_scopes = permissions.get('available_scopes', [])
                if available_scopes:
                    print(f"  Available Scopes List:")
                    for scope in available_scopes:
                        print(f"    • {scope}")
                
                # Show missing scopes if any
                missing_scopes = permissions.get('missing_scopes', [])
                if missing_scopes:
                    print(f"  Missing Scopes:")
                    for scope in missing_scopes:
                        print(f"    • {scope}")
            
            # Display capability information
            print(f"\n🎯 Capabilities:")
            print(f"  Permission Status: {account_info.get('permission_status', 'unknown')}")
            print(f"  Can Publish: {account_info.get('can_publish', False)}")
            print(f"  Can Manage Comments: {account_info.get('can_manage_comments', False)}")
            print(f"  Can View Insights: {account_info.get('can_view_insights', False)}")
            
            # Test available fields
            print(f"\n🔬 Testing available Instagram API fields...")
            field_test_results = analytics_manager.test_available_fields()
            
            print(f"📋 Field Test Results:")
            for fields, result in field_test_results.items():
                if result.get('status') == 'success':
                    print(f"  ✅ {fields}: {len(result.get('fields_returned', []))} fields returned")
                    for field in result.get('fields_returned', []):
                        print(f"    • {field}")
                else:
                    print(f"  ❌ {fields}: {result.get('status')} - {result.get('error', 'Unknown error')}")
            
            # Test insights configurations
            print(f"\n🔍 Testing Instagram insights configurations...")
            insights_test_results = analytics_manager.test_insights_configurations()
            
            print(f"📊 Insights Test Results:")
            for config, result in insights_test_results.items():
                if result.get('success'):
                    print(f"  ✅ {config}: Success")
                else:
                    print(f"  ❌ {config}: {result.get('status_code')} - {result.get('response', 'Unknown error')}")
        
        # Export to JSON (always run)
        output_file = args.output
        print(f"\n💾 Exporting analytics to JSON: {output_file}...")
        analytics_manager.export_to_json(output_file)
        print(f"✅ Instagram Analytics Manager exported results to: {output_file}")
        
        if args.fulltest:
            print("\n🎉 Full test completed successfully!")
        else:
            print("\n✅ Export completed. Run with --fulltest for diagnostics.")
        
    except Exception as e:
        print(f"❌ Execution failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
