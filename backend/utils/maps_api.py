import os
import googlemaps
from dotenv import load_dotenv

load_dotenv()
gmaps = googlemaps.Client(key=os.getenv("GOOGLE_MAPS_API_KEY"))

def get_lat_lng_from_place(place):
    geocode_result = gmaps.geocode(place)
    if geocode_result:
        return geocode_result[0]["geometry"]["location"]["lat"], geocode_result[0]["geometry"]["location"]["lng"]
    return None, None

def get_directions(origin, destination, mode="driving"):
    return gmaps.directions(origin, destination, mode=mode)
