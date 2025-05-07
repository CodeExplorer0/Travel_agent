import os
import requests
import folium
from math import radians, cos, sin, asin, sqrt
from dotenv import load_dotenv

load_dotenv()
GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')

def get_lat_lng_from_place(place):
    geocode_url = f"https://maps.googleapis.com/maps/api/geocode/json?address={place}&key={GOOGLE_MAPS_API_KEY}"
    geo_response = requests.get(geocode_url).json()
    if geo_response["status"] != "OK":
        return None, None
    location = geo_response["results"][0]["geometry"]["location"]
    return location["lat"], location["lng"]

def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return R * 2 * asin(sqrt(a))

def get_photo_url(photo_reference):
    if not photo_reference:
        return None
    return f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference={photo_reference}&key={GOOGLE_MAPS_API_KEY}"

def get_place_details(place_id):
    details_url = f"https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id,
        "fields": "photo,reviews",
        "key": GOOGLE_MAPS_API_KEY
    }
    response = requests.get(details_url, params=params).json()
    result = response.get("result", {})
    photo_url = None
    reviews = []
    if "photos" in result:
        photo_url = get_photo_url(result["photos"][0]["photo_reference"])
    if "reviews" in result:
        for r in result["reviews"][:2]:
            reviews.append(f"★ {r.get('rating')}: {r.get('text')[:100]}...")
    return photo_url, reviews

def get_recommendations(location, place_type="tourist_attraction"):
    lat, lng = get_lat_lng_from_place(location)
    if lat is None:
        return [], None, None
    nearby_url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "location": f"{lat},{lng}",
        "radius": 5000,
        "type": place_type,
        "key": GOOGLE_MAPS_API_KEY
    }
    data = requests.get(nearby_url, params=params).json()
    places = []
    for place in data.get("results", []):
        place_id = place.get("place_id")
        name = place.get("name")
        rating = place.get("rating", 0)
        types = place.get("types", [])
        geometry = place.get("geometry", {}).get("location", {})
        place_lat = geometry.get("lat")
        place_lng = geometry.get("lng")
        distance = haversine(lat, lng, place_lat, place_lng)
        photo_url, reviews = get_place_details(place_id)
        places.append({
            "name": name,
            "rating": rating,
            "lat": place_lat,
            "lng": place_lng,
            "distance": distance,
            "photo_url": photo_url,
            "reviews": reviews,
            "types": types,
            "score": rating - 0.3 * distance
        })
    return sorted(places, key=lambda x: x["score"], reverse=True)[:15], lat, lng

def plot_combined_map(places, hotels, center_lat, center_lon):
    map_obj = folium.Map(location=[center_lat, center_lon], zoom_start=12)
    # Plot attractions
    for p in places:
        folium.Marker(
            [p["lat"], p["lng"]],
            icon=folium.Icon(color="green", icon="camera"),
            popup=f"{p['name']} (⭐{p['rating']})"
        ).add_to(map_obj)
    # Plot hotels
    for h in hotels:
        folium.Marker(
            [h["latitude"], h["longitude"]],
            icon=folium.Icon(color="blue", icon="bed"),
            popup=f"{h['hotel_name']} (₹{h.get('price', 'N/A')})"
        ).add_to(map_obj)
    map_obj.save("travel_map.html")
