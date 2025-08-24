#!/usr/bin/env python3
"""
Instagram Hashtag Search Script - Simplified Version

This script searches for Instagram posts with a specific hashtag and saves the results.
It's designed to be simple, readable, and focused on core functionality.
"""

import requests
import json
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Add the parent directory to Python path to import config
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import ConfigManager


class InstagramHashtagSearcher:
    """Simple Instagram hashtag search using Instagram Graph API."""
    
    def __init__(self, config_path: str = "autopost_config.enhanced.json"):
        """Initialize with configuration."""
        self.config_manager = ConfigManager(config_path)
        self.config = self.config_manager.config  # Always use full config
        self.base_url = "https://graph.facebook.com/v23.0"
        
        # Validate required Instagram credentials
        if not self.config.get('instagram_access_token'):
            raise ValueError("Instagram access token is required")
        if not self.config.get('instagram_user_id'):
            raise ValueError("Instagram user ID is required")
    
    def search_hashtag_id(self, hashtag: str) -> Optional[str]:
        """Search for a hashtag ID using Instagram Graph API."""
        url = f"{self.base_url}/ig_hashtag_search"
        params = {
            "user_id": self.config['instagram_user_id'],
            "q": hashtag,
            "access_token": self.config['instagram_access_token']
        }
        
        try:
            print(f"🔍 Searching for hashtag ID: #{hashtag}")
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            if "data" in data and len(data["data"]) > 0:
                hashtag_id = data["data"][0]["id"]
                print(f"✅ Found hashtag ID: {hashtag_id}")
                return hashtag_id
            else:
                print(f"❌ No hashtag ID found for #{hashtag}")
                return None
                
        except Exception as e:
            print(f"❌ Error searching for hashtag: {e}")
            return None
    
    def get_hashtag_posts(self, hashtag_id: str, limit: int = 10) -> List[Dict]:
        """Retrieve recent posts with a specific hashtag."""
        url = f"{self.base_url}/{hashtag_id}/recent_media"
        params = {
            "user_id": self.config['instagram_user_id'],
            "fields": "id,caption,media_type,media_url,permalink,like_count,comments_count,timestamp",
            "limit": min(limit, 50),
            "access_token": self.config['instagram_access_token']
        }
        
        try:
            print(f"📱 Retrieving posts for hashtag ID: {hashtag_id}")
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            if "data" in data:
                posts = data["data"]
                print(f"✅ Retrieved {len(posts)} posts")
                return posts
            else:
                print(f"❌ No posts found")
                return []
                
        except Exception as e:
            print(f"❌ Error retrieving posts: {e}")
            return []
    
    def get_post_comments(self, post_id: str, limit: int = 10) -> List[Dict]:
        """Retrieve comments for a specific post using Instagram Graph API."""
        url = f"{self.base_url}/{post_id}/comments"
        params = {
            "user_id": self.config['instagram_user_id'],
            "fields": "id,text,timestamp,username",
            "limit": min(limit, 50),
            "access_token": self.config['instagram_access_token']
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            if "data" in data:
                comments = data["data"]
                return comments
            else:
                return []
                
        except Exception as e:
            print(f"⚠️ Warning: Could not retrieve comments for post {post_id}: {e}")
            return []
    
    def get_cached_hashtag_id(self, hashtag: str) -> Optional[str]:
        """Check if hashtag ID exists in config cache."""
        cached_ids = self.config.get('ig_hashtag_ids', {})
        return cached_ids.get(hashtag)
    
    def save_hashtag_id_to_config(self, hashtag: str, hashtag_id: str) -> None:
        """Save hashtag ID to config for future use."""
        try:
            # Get current hashtag IDs or initialize empty dict
            hashtag_ids = self.config_manager.get('ig_hashtag_ids', {})
            
            # Update with new hashtag ID
            hashtag_ids[hashtag] = hashtag_id
            
            # Set the updated hashtag IDs in config
            self.config_manager.set('ig_hashtag_ids', hashtag_ids)
            
            # Save config to file
            self.config_manager.save_config()
            
            print(f"💾 Saved hashtag ID for #{hashtag}: {hashtag_id}")
            
        except Exception as e:
            print(f"⚠️ Warning: Could not save hashtag ID to config: {e}")
    
    def save_results(self, hashtag: str, hashtag_id: str, posts: List[Dict], include_comments: bool = False) -> str:
        """Save search results to a JSON file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"instagram_hashtag_{hashtag}_{timestamp}.json"
        
        results = {
            "search_info": {
                "hashtag": hashtag,
                "hashtag_id": hashtag_id,
                "search_timestamp": datetime.now().isoformat(),
                "total_posts": len(posts),
                "comments_included": include_comments
            },
            "posts": []
        }
        
        # Process posts
        for post in posts:
            post_data = {
                "post_id": post.get("id"),
                "caption": post.get("caption", ""),
                "post_url": post.get("permalink", ""),
                "likes": post.get("like_count", 0),
                "comments": post.get("comments_count", 0),
                "media_type": post.get("media_type", ""),
                "media_url": post.get("media_url", ""),
                "timestamp": post.get("timestamp", "")
            }
            
            # Add comments if requested
            if include_comments:
                comments = self.get_post_comments(post.get("id"), limit=10)
                post_data["comment_details"] = []
                for comment in comments:
                    comment_data = {
                        "comment_id": comment.get("id"),
                        "text": comment.get("text", ""),
                        "timestamp": comment.get("timestamp", ""),
                        "username": comment.get("username", "")
                    }
                    post_data["comment_details"].append(comment_data)
            
            results["posts"].append(post_data)
        
        # Save to file
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Results saved to: {filename}")
        return filename
    
    def display_results(self, results: Dict, hashtag: str):
        """Display search results in a clean format."""
        posts = results.get('posts', [])
        comments_included = results.get('search_info', {}).get('comments_included', False)
        
        print(f"\n📊 Search Results for #{hashtag}")
        print(f"   Total posts: {len(posts)}")
        print(f"   Hashtag ID: {results['search_info']['hashtag_id']}")
        if comments_included:
            print(f"   💬 Comments included: Yes")
        print("-" * 50)
        
        # Display one-line summary for each post
        for post in posts:
            post_id = post.get('post_id', 'N/A')
            likes = post.get('likes', 0)
            comments = post.get('comments', 0)
            permalink = post.get('post_url', 'N/A')
            print(f"📱 {post_id}  ❤️ {likes}  💬 {comments}  �🔗 {permalink}")
        
        # Show top posts by likes
        if posts:
            print(f"\n🏆 Top posts by likes:")
            sorted_posts = sorted(posts, key=lambda x: x.get('likes', 0), reverse=True)
            for i, post in enumerate(sorted_posts[:5], 1):
                caption = post.get('caption', '')[:50] + '...' if len(post.get('caption', '')) > 50 else post.get('caption', '')
                print(f"   {i}. {post.get('likes', 0)} likes - {caption}")
        
        # Show sample comments if included
        if comments_included:
            print(f"\n💬 Sample Comments:")
            for i, post in enumerate(posts[:3], 1):  # Show comments from first 3 posts
                comment_details = post.get('comment_details', [])
                if comment_details:
                    print(f"\n   📱 Post {i} ({post.get('post_id', 'N/A')}):")
                    for j, comment in enumerate(comment_details[:3], 1):  # Show first 3 comments
                        username = comment.get('username', 'Unknown')
                        text = comment.get('text', '')[:60] + '...' if len(comment.get('text', '')) > 60 else comment.get('text', '')
                        print(f"      {j}. @{username}: {text}")
                else:
                    print(f"\n   📱 Post {i} ({post.get('post_id', 'N/A')}): No comments")
    
    def search_hashtag(self, hashtag: str, limit: int = 10, include_comments: bool = False) -> bool:
        """Main method: search for hashtag and retrieve posts."""
        print(f"🚀 Starting Instagram hashtag search for #{hashtag}")
        print(f"📊 Configuration: User ID {self.config['instagram_user_id']}")
        print("-" * 50)
        
        # Check for cached hashtag ID first
        hashtag_id = self.get_cached_hashtag_id(hashtag)
        if hashtag_id:
            print(f"📋 Using cached hashtag ID for #{hashtag}: {hashtag_id}")
        else:
            # Search for hashtag ID if not cached
            hashtag_id = self.search_hashtag_id(hashtag)
            if not hashtag_id:
                print("❌ Cannot proceed without hashtag ID")
                return False
            
            # Save the hashtag ID to config for future use
            self.save_hashtag_id_to_config(hashtag, hashtag_id)
        
        # Retrieve posts
        posts = self.get_hashtag_posts(hashtag_id, limit)
        if not posts:
            print("❌ No posts found")
            return False
        
        # Save and display results
        output_file = self.save_results(hashtag, hashtag_id, posts, include_comments)
        
        # Load the saved results to display them
        with open(output_file, 'r', encoding='utf-8') as f:
            saved_results = json.load(f)
        self.display_results(saved_results, hashtag)
        
        return True


def main():
    """Main function with simple command line interface."""
    import argparse

    print("""Some items to place into the config file:
"ig_hashtag_ids": {
    "pottery": "17842299859068210",
    "ceramics": "17841562915095670",
    "3dprintedpottery": "17864421391033352",
    "testhashtag": "17843690350012293",
    "newtest": "17843817244001674"
}"
""")
    
    parser = argparse.ArgumentParser(description='Instagram Hashtag Search Tool')
    parser.add_argument('--hashtag', '-t', type=str, default='3dprintedpottery',
                       help='Hashtag to search for (default: 3dprintedpottery)')
    parser.add_argument('--limit', '-l', type=int, default=10,
                       help='Maximum number of posts to retrieve (default: 10, max: 50)')
    parser.add_argument('--config', '-c', type=str, default='autopost_config.enhanced.json',
                       help='Configuration file path')
    parser.add_argument('--comments', '-m', action='store_true',
                       help='Include comments for each post (requires additional API calls)')
    parser.add_argument('--single_comment', '-s', type=str, default=None,
                       help='Do comment call for a single post ID')
    
    args = parser.parse_args()
    
    try:
        # Remove # if present in hashtag
        hashtag = args.hashtag.lstrip('#')
        
        print("=== Instagram Hashtag Search Tool ===")
        print(f"🔍 Target hashtag: #{hashtag}")
        print(f"📊 Post limit: {args.limit}")
        print(f"📁 Config file: {args.config}")
        if args.comments:
            print(f"💬 Comments: Enabled")
        print("=" * 50)
        
        # Initialize searcher and perform search
        searcher = InstagramHashtagSearcher(config_path=args.config)

        if args.single_comment:
            single_comment_id = args.single_comment
            comments = searcher.get_post_comments(single_comment_id)
            print(comments)
            return 0

        success = searcher.search_hashtag(hashtag, args.limit, args.comments)
        
        if success:
            print("\n✅ Search completed successfully!")
            return 0
        else:
            print("\n❌ Search failed!")
            return 1
            
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
