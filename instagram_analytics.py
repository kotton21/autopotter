#!/usr/bin/env python3
"""
Enhanced Instagram API Manager for Phase 2: Enhanced Data Collection.
This module expands the existing Instagram API to generate comprehensive account analytics JSON.
"""

import requests
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from logger import get_logger
from config import get_config

class InstagramAnalyticsManager:
    """
    Enhanced Instagram API manager that generates comprehensive account analytics.
    Integrates with the new Phase 1 logging and configuration systems.
    """
    
    def __init__(self, config_path: str = "autopost_config.enhanced.json"):
        self.config = get_config(config_path)
        self.logger = get_logger('instagram_analytics')
        self.instagram_config = self.config.get_instagram_config()
        
        # Validate required configuration
        if not self.instagram_config.get('access_token'):
            raise ValueError("Instagram access token not configured")
        if not self.instagram_config.get('user_id'):
            raise ValueError("Instagram user ID not configured")
        
        self.base_url = "https://graph.facebook.com/v22.0"
        self.access_token = self.instagram_config['access_token']
        self.user_id = self.instagram_config['user_id']
        
        self.logger.info("Instagram Analytics Manager initialized")
    
    def get_account_info(self) -> Dict[str, Any]:
        """
        Retrieve comprehensive account information including followers, following, and basic stats.
        
        Returns:
            Dictionary containing account analytics
        """
        self.logger.info("Retrieving account information")
        
        try:
            # Get basic account info with minimal fields first
            url = f"{self.base_url}/{self.user_id}"
            params = {
                "fields": "id,name",
                "access_token": self.access_token
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            account_data = response.json()
            
            self.logger.debug(f"Account data retrieved: {account_data}")
            
            # Try to get additional fields if available
            additional_fields = {}
            try:
                extended_params = {
                    "fields": "username,account_type,media_count,followers_count,follows_count,biography,website,profile_picture_url",
                    "access_token": self.access_token
                }
                extended_response = requests.get(url, params=extended_params)
                if extended_response.status_code == 200:
                    extended_data = extended_response.json()
                    additional_fields = extended_data
                    self.logger.debug(f"Extended account data retrieved: {extended_data}")
            except Exception as e:
                self.logger.warning(f"Could not retrieve extended account info: {e}")
            
            return {
                'account_id': account_data.get('id'),
                'username': account_data.get('username') or account_data.get('name', 'Unknown'),
                'account_type': additional_fields.get('account_type', 'unknown'),
                'media_count': additional_fields.get('media_count', 0),
                'followers_count': additional_fields.get('followers_count', 0),
                'following_count': additional_fields.get('follows_count', 0),
                'biography': additional_fields.get('biography', ''),
                'website': additional_fields.get('website', ''),
                'profile_picture_url': additional_fields.get('profile_picture_url', ''),
                'retrieved_at': datetime.now().isoformat(),
                'api_limitations': {
                    'basic_fields_only': len(additional_fields) == 0,
                    'available_fields': list(account_data.keys())
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve account info: {e}")
            raise
    
    def get_recent_media(self, limit: int = 25) -> List[Dict[str, Any]]:
        """
        Retrieve recent media posts with basic engagement metrics.
        
        Args:
            limit: Maximum number of media items to retrieve
            
        Returns:
            List of media items with engagement data
        """
        self.logger.info(f"Retrieving recent media (limit: {limit})")
        
        try:
            # Try with minimal fields first
            url = f"{self.base_url}/{self.user_id}/media"
            params = {
                "fields": "id,media_type",
                "access_token": self.access_token,
                "limit": limit
            }
            
            response = requests.get(url, params=params)
            if response.status_code != 200:
                # Try with even more basic fields
                params["fields"] = "id"
                response = requests.get(url, params=params)
                if response.status_code != 200:
                    self.logger.warning("Instagram API does not support media access for this user/app combination")
                    return []
            
            media_data = response.json()
            
            media_items = []
            for item in media_data.get('data', []):
                media_item = {
                    'id': item.get('id'),
                    'media_type': item.get('media_type', 'unknown'),
                    'media_url': None,
                    'thumbnail_url': None,
                    'permalink': None,
                    'timestamp': None,
                    'caption': '',
                    'like_count': 0,
                    'comments_count': 0,
                    'insights': {},
                    'api_limitations': {
                        'limited_fields': True,
                        'available_fields': list(item.keys())
                    }
                }
                
                # Try to get additional fields if available
                try:
                    extended_params = {
                        "fields": "media_url,thumbnail_url,permalink,timestamp,caption,like_count,comments_count",
                        "access_token": self.access_token
                    }
                    extended_response = requests.get(f"{self.base_url}/{item['id']}", params=extended_params)
                    if extended_response.status_code == 200:
                        extended_data = extended_response.json()
                        media_item.update({
                            'media_url': extended_data.get('media_url'),
                            'thumbnail_url': extended_data.get('thumbnail_url'),
                            'permalink': extended_data.get('permalink'),
                            'timestamp': extended_data.get('timestamp'),
                            'caption': extended_data.get('caption', {}).get('text', '') if isinstance(extended_data.get('caption'), dict) else extended_data.get('caption', ''),
                            'like_count': extended_data.get('like_count', 0),
                            'comments_count': extended_data.get('comments_count', 0)
                        })
                        media_item['api_limitations']['limited_fields'] = False
                except Exception as e:
                    self.logger.debug(f"Could not retrieve extended media info for {item['id']}: {e}")
                
                media_items.append(media_item)
            
            self.logger.debug(f"Retrieved {len(media_items)} media items")
            return media_items
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve recent media: {e}")
            return []
    
    def get_video_insights(self, media_id: str) -> Dict[str, Any]:
        """
        Retrieve detailed insights for a specific video.
        
        Args:
            media_id: Instagram media ID
            
        Returns:
            Dictionary containing video insights
        """
        self.logger.info(f"Retrieving video insights for media ID: {media_id}")
        
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
            
            self.logger.debug(f"Video insights retrieved: {insights}")
            return insights
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve video insights: {e}")
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
        self.logger.info(f"Retrieving recent comments for media ID: {media_id}")
        
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
            
            self.logger.debug(f"Retrieved {len(comments)} comments")
            return comments
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve comments: {e}")
            return []
    
    def get_recent_activity(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Retrieve recent account activity including follows, unfollows, and mentions.
        
        Args:
            limit: Maximum number of activity items to retrieve
            
        Returns:
            List of recent activity items
        """
        self.logger.info(f"Retrieving recent activity (limit: {limit})")
        
        try:
            # Note: Instagram Graph API has limited access to real-time activity
            # This method provides what's available through the API
            url = f"{self.base_url}/{self.user_id}/media"
            params = {
                "fields": "id,media_type,timestamp,like_count,comments_count,insights.metric(impressions,reach,engagement)",
                "access_token": self.access_token,
                "limit": limit
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            media_data = response.json()
            
            activity_items = []
            for item in media_data.get('data', []):
                # Calculate engagement rate
                impressions = 0
                reach = 0
                if 'insights' in item and 'data' in item['insights']:
                    for insight in item['insights']['data']:
                        if insight['name'] == 'impressions':
                            impressions = insight['values'][0]['value']
                        elif insight['name'] == 'reach':
                            reach = insight['values'][0]['value']
                
                engagement_rate = 0
                if impressions > 0:
                    engagement_rate = ((item.get('like_count', 0) + item.get('comments_count', 0)) / impressions) * 100
                
                activity_item = {
                    'media_id': item.get('id'),
                    'media_type': item.get('media_type'),
                    'timestamp': item.get('timestamp'),
                    'engagement_metrics': {
                        'likes': item.get('like_count', 0),
                        'comments': item.get('comments_count', 0),
                        'impressions': impressions,
                        'reach': reach,
                        'engagement_rate': round(engagement_rate, 2)
                    }
                }
                
                activity_items.append(activity_item)
            
            self.logger.debug(f"Retrieved {len(activity_items)} activity items")
            return activity_items
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve recent activity: {e}")
            raise
    
    def get_hashtag_performance(self, hashtags: List[str] = None) -> Dict[str, Any]:
        """
        Analyze performance of posts with specific hashtags.
        
        Args:
            hashtags: List of hashtags to analyze (without #)
            
        Returns:
            Dictionary containing hashtag performance data
        """
        self.logger.info(f"Analyzing hashtag performance for: {hashtags}")
        
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
            
            self.logger.debug(f"Hashtag performance analysis completed")
            return hashtag_stats
            
        except Exception as e:
            self.logger.error(f"Failed to analyze hashtag performance: {e}")
            return {}
    
    def export_to_json(self, output_path: str = None) -> Dict[str, Any]:
        """
        Generate comprehensive Instagram analytics JSON document.
        
        Args:
            output_path: Optional path to save JSON file
            
        Returns:
            Dictionary containing all analytics data
        """
        self.logger.info("Generating comprehensive Instagram analytics JSON")
        
        try:
            # Collect all analytics data
            analytics_data = {
                'export_info': {
                    'exported_at': datetime.now().isoformat(),
                    'export_version': '2.0',
                    'source': 'instagram_analytics_manager'
                },
                'account_info': self.get_account_info(),
                'recent_media': self.get_recent_media(limit=25),
                'recent_activity': self.get_recent_activity(limit=20),
                'hashtag_performance': self.get_hashtag_performance(),
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
                self.logger.info(f"Analytics data saved to: {output_path}")
            
            self.logger.info("Instagram analytics JSON generation completed")
            return analytics_data
            
        except Exception as e:
            self.logger.error(f"Failed to export analytics to JSON: {e}")
            raise
    
    def get_latest_video_performance(self) -> Dict[str, Any]:
        """
        Get performance metrics for the most recent video post.
        
        Returns:
            Dictionary containing latest video performance data
        """
        self.logger.info("Retrieving latest video performance metrics")
        
        try:
            # Get recent media and find the latest video
            recent_media = self.get_recent_media(limit=10)
            video_posts = [media for media in recent_media if media.get('media_type') == 'VIDEO']
            
            if not video_posts:
                self.logger.warning("No video posts found in recent media")
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
            
            self.logger.info(f"Latest video performance retrieved: {latest_video['id']}")
            return video_performance
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve latest video performance: {e}")
            return {}

def main():
    """Test the Instagram Analytics Manager."""
    try:
        # Initialize the manager
        analytics_manager = InstagramAnalyticsManager()
        
        # Generate comprehensive analytics
        analytics_data = analytics_manager.export_to_json("instagram_analytics.json")
        
        print("✅ Instagram analytics generated successfully!")
        print(f"📊 Account: {analytics_data['account_info']['username']}")
        print(f"👥 Followers: {analytics_data['account_info']['followers_count']}")
        print(f"📱 Media count: {analytics_data['account_info']['media_count']}")
        print(f"📈 Recent posts analyzed: {analytics_data['summary_metrics']['media_count_analyzed']}")
        
    except Exception as e:
        print(f"❌ Failed to generate Instagram analytics: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
