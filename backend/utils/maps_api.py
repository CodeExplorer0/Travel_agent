import googlemaps
import os
from dotenv import load_dotenv
import folium

# Load environment variables
load_dotenv()
GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')

# Initialize the Google Maps API client
gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)

def get_lat_lng_from_place(place):
    """Get the latitude and longitude of a place."""
    geocode_result = gmaps.geocode(place)
    if geocode_result:
        lat = geocode_result[0]['geometry']['location']['lat']
        lng = geocode_result[0]['geometry']['location']['lng']
        return lat, lng
    else:
        return None, None

def get_directions(origin, destination):
    """Get directions from origin to destination."""
    try:
        directions = gmaps.directions(origin, destination)
        return directions
    except Exception as e:
        return {"error": f"Error fetching directions: {e}"}

def get_places_nearby(location, place_type="restaurant", radius=1000):
    """Get nearby places of a specific type (e.g., restaurants)."""
    try:
        places = gmaps.places_nearby(location=location, radius=radius, type=place_type)
        return places
    except Exception as e:
        return {"error": f"Error fetching places: {e}"}

def get_google_maps_url_for_directions(origin, destination):
    """Generate a Google Maps URL for directions."""
    origin_lat_lng = get_lat_lng_from_place(origin)
    destination_lat_lng = get_lat_lng_from_place(destination)
    
    if origin_lat_lng and destination_lat_lng:
        origin_str = f"{origin_lat_lng[0]},{origin_lat_lng[1]}"
        destination_str = f"{destination_lat_lng[0]},{destination_lat_lng[1]}"
        url = f"https://www.google.com/maps/dir/?api=1&origin={origin_str}&destination={destination_str}&travelmode=driving"
        return url
    else:
        return {"error": "Invalid locations."}

def plot_route_on_map(origin, destination):
    """Plot the route between origin and destination on a map using Folium."""
    origin_lat_lng = get_lat_lng_from_place(origin)
    destination_lat_lng = get_lat_lng_from_place(destination)
    
    if origin_lat_lng and destination_lat_lng:
        # Create a Folium map centered around the origin
        route_map = folium.Map(location=[origin_lat_lng[0], origin_lat_lng[1]], zoom_start=12)
        
        # Add origin and destination markers
        folium.Marker(location=[origin_lat_lng[0], origin_lat_lng[1]], popup=f"Origin: {origin}").add_to(route_map)
        folium.Marker(location=[destination_lat_lng[0], destination_lat_lng[1]], popup=f"Destination: {destination}").add_to(route_map)
        
        # Draw a line between the origin and destination
        folium.PolyLine(
            locations=[origin_lat_lng, destination_lat_lng],
            color="blue",
            weight=5,
            opacity=0.7
        ).add_to(route_map)

        return route_map
    else:
        return {"error": "Invalid locations."}

def plot_nearby_places_on_map(location, place_type="restaurant"):
    """Plot nearby places on a map using Folium."""
    lat, lng = get_lat_lng_from_place(location)
    
    if lat is None or lng is None:
        return {"error": "Invalid location."}
    
    # Get places nearby
    places_nearby = get_places_nearby((lat, lng), place_type)
    
    if isinstance(places_nearby, dict) and "error" in places_nearby:
        return places_nearby
    
    # Create a Folium map centered around the location
    map_obj = folium.Map(location=[lat, lng], zoom_start=14)
    
    # Add markers for each nearby place
    for place in places_nearby["results"]:
        place_name = place["name"]
        place_lat = place["geometry"]["location"]["lat"]
        place_lng = place["geometry"]["location"]["lng"]
        folium.Marker([place_lat, place_lng], popup=place_name).add_to(map_obj)
    
    return map_obj
