import requests

def get_recommendations(location, category="restaurants"):
    """Get food/activity recommendations from Yelp API."""
    api_key = "YOUR_YELP_API_KEY"
    url = f"https://api.yelp.com/v3/businesses/search?location={location}&categories={category}"
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.get(url, headers=headers)
    recommendations = response.json()
    
    # Example of extracting top restaurant recommendations
    businesses = recommendations['businesses']
    top_restaurants = [{"name": business['name'], "rating": business['rating']} for business in businesses]
    return top_restaurants
