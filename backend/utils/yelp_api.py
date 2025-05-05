import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
YELP_API_KEY = os.getenv('YELP_API_KEY')

def get_recommendations(location, category="restaurants"):
    """Get food/activity recommendations from Yelp API."""
    try:
        url = f"https://api.yelp.com/v3/businesses/search?location={location}&categories={category}"
        headers = {"Authorization": f"Bearer {YELP_API_KEY}"}
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            recommendations = response.json()
            if 'businesses' in recommendations:
                # Example of extracting top recommendations
                businesses = recommendations['businesses']
                top_recommendations = [{"name": business['name'], "rating": business['rating']} for business in businesses]
                return top_recommendations
            else:
                return {"error": "No businesses found."}
        else:
            return {"error": f"Failed to fetch recommendations. Status code: {response.status_code}"}
    
    except Exception as e:
        return {"error": f"Error fetching recommendations: {e}"}
