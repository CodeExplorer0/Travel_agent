import googlemaps

# Initialize the Google Maps API client
gmaps = googlemaps.Client(key="YOUR_GOOGLE_MAPS_API_KEY")

def get_directions(destination):
    """Get directions for a given destination."""
    directions = gmaps.directions("current location", destination)
    return directions

def get_places_nearby(location, place_type="restaurant"):
    """Get nearby places of a specific type (e.g., restaurants)."""
    places = gmaps.places_nearby(location, type=place_type)
    return places
