import os
import googlemaps
from dotenv import load_dotenv

# Load API keys from .env file
load_dotenv()

# Initialize Google Maps client
gmaps = googlemaps.Client(key=os.getenv("GOOGLE_MAPS_API_KEY"))

def get_lat_lng_from_place(place):
    """Get latitude and longitude of a place using Google Maps Geocoding API."""
    geocode_result = gmaps.geocode(place)
    if geocode_result:
        location = geocode_result[0]["geometry"]["location"]
        return location["lat"], location["lng"]
    return None, None

def get_directions(origin, destination, mode="driving"):
    """Get directions between origin and destination using specified travel mode."""
    return gmaps.directions(origin, destination, mode=mode)
