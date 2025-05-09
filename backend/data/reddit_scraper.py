import os
import praw
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Reddit client
reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent="solotravel_scraper"
)

def scrape_relevant_data(keywords, subreddits=None, limit=50):
    """
    Scrape Reddit posts from specified subreddits that contain any of the keywords.

    Args:
        keywords (list of str): Keywords to search for in title or body.
        subreddits (list of str): Subreddits to search (default: travel-related).
        limit (int): Max posts to fetch per subreddit.
    """
    if subreddits is None:
        subreddits = ["solotravel", "travel", "backpacking"]

    keywords = [kw.lower() for kw in keywords if kw]
    posts_data = []

    for sub in subreddits:
        subreddit = reddit.subreddit(sub)
        search_query = " OR ".join(f'"{kw}"' for kw in keywords)

        for post in subreddit.search(search_query, sort="relevance", limit=limit):
            content = f"{post.title} {post.selftext}".lower()
            if any(kw in content for kw in keywords):
                post_data = {
                    "title": post.title,
                    "author": str(post.author),
                    "score": post.score,
                    "url": post.url,
                    "selftext": post.selftext,
                    "subreddit": sub,
                    "comments": [
                        comment.body for comment in post.comments
                        if hasattr(comment, "body") and any(kw in comment.body.lower() for kw in keywords)
                    ]
                }
                posts_data.append(post_data)

    os.makedirs("data", exist_ok=True)
    with open("data/relevant_posts.json", "w", encoding="utf-8") as f:
        json.dump(posts_data, f, indent=2)

    print(f"Scraped and saved {len(posts_data)} relevant posts to data/relevant_posts.json")

if __name__ == "__main__":
    # Example usage: scrape for Kerala beaches and food
    scrape_relevant_data(["Kerala", "beaches", "food"])
