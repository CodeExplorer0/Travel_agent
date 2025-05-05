from utils.maps_api import get_directions
from utils.weather_api import get_weather
from utils.yelp_api import get_recommendations
from utils.stays_api import get_stay_recommendations

def generate_itinerary(user_preferences):
    """
    Generate an itinerary based on user preferences like destination, activities,
    food choices, and weather considerations.
    """
    destination = user_preferences['destination']
    activities = user_preferences['activities']
    budget = user_preferences['budget']
    
    # Example itinerary structure:
    itinerary = {
        "destination": destination,
        "activities": activities,
        "restaurants": get_recommendations(destination),
        "weather_suggestion": get_weather(destination),
        "stay_recommendations": get_stay_recommendations(destination, budget),
        "distance": get_directions(destination),
    }
    
    return itinerary
