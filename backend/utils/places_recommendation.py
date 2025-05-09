import os
import requests
import folium
from math import radians, cos, sin, asin, sqrt, atan2
from dotenv import load_dotenv
import json

load_dotenv()
GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')

# Mapping of Google Places types to our categories
PLACE_TYPE_MAPPING = {
    'tourist_attraction': 'Attraction',
    'point_of_interest': 'Attraction',
    'museum': 'Museum',
    'art_gallery': 'Museum',
    'church': 'Religious',
    'temple': 'Religious',
    'mosque': 'Religious',
    'park': 'Park',
    'natural_feature': 'Nature',
    'landmark': 'Landmark',
    'amusement_park': 'Entertainment',
    'zoo': 'Entertainment',
    'aquarium': 'Entertainment',
    'restaurant': 'Restaurant',
    'cafe': 'Restaurant',
    'bar': 'Restaurant',
    'lodging': 'Accommodation',
    'hotel': 'Accommodation',
    'guest_house': 'Accommodation'
}

def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Earth's radius in kilometers

    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    distance = R * c

    return distance


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
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
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


def get_recommendations(location, place_type=None):
    try:
        # Get coordinates for the location
        lat, lng = get_lat_lng_from_place(location)
        if not lat or not lng:
            print(f"❌ Could not get coordinates for {location}")
            return []

        # Define place types to search for
        place_types = ['tourist_attraction', 'point_of_interest', 'museum', 'art_gallery', 'church', 'temple', 'mosque', 'park']
        if place_type:
            place_types = [place_type]

        all_places = []
        for type_ in place_types:
            # Define search parameters
            params = {
                'location': f'{lat},{lng}',
                'radius': '5000',  # 5km radius
                'type': type_,
                'key': os.getenv('GOOGLE_MAPS_API_KEY'),
                'rankby': 'prominence'
            }

            # Make API request
            url = 'https://maps.googleapis.com/maps/api/place/nearbysearch/json'
            response = requests.get(url, params=params)
            data = response.json()

            if data['status'] != 'OK':
                print(f"❌ Places API error for {type_}: {data['status']}")
                continue

            for place in data.get('results', []):
                # Skip places without essential data
                if not all(key in place for key in ['name', 'geometry', 'place_id']):
                    continue

                # Get place details
                place_id = place['place_id']
                details_url = f'https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&fields=name,formatted_address,geometry,rating,reviews,photos,types&key={os.getenv("GOOGLE_MAPS_API_KEY")}'
                details_response = requests.get(details_url)
                details_data = details_response.json()

                if details_data['status'] != 'OK':
                    continue

                details = details_data['result']
                
                # Skip if coordinates are too far
                place_lat = details['geometry']['location']['lat']
                place_lng = details['geometry']['location']['lng']
                distance = haversine(lat, lng, place_lat, place_lng)
                if distance > 5:  # Skip if more than 5km away
                    continue

                # Get category based on place type
                category = 'Other'
                for type_ in details.get('types', []):
                    if type_ in PLACE_TYPE_MAPPING:
                        category = PLACE_TYPE_MAPPING[type_]
                        break

                # Create place object
                place_obj = {
                    'name': details['name'],
                    'address': details.get('formatted_address', ''),
                    'latitude': place_lat,
                    'longitude': place_lng,
                    'rating': details.get('rating', 0),
                    'reviews': len(details.get('reviews', [])),
                    'category': category,
                    'city': location.split(',')[0].strip(),
                    'photos': [photo.get('photo_reference', '') for photo in details.get('photos', [])[:3]]
                }

                # Calculate score based on rating and reviews
                place_obj['score'] = (place_obj['rating'] * 0.7) + (min(place_obj['reviews'], 100) / 100 * 0.3)
                
                # Skip if we already have this place
                if not any(p['name'] == place_obj['name'] for p in all_places):
                    all_places.append(place_obj)

        # Sort by score and return top 15
        all_places.sort(key=lambda x: x['score'], reverse=True)
        return all_places[:15]

    except Exception as e:
        print(f"❌ Error in get_recommendations: {str(e)}")
        return []


def get_top_places_for_city(city, n=3):
    """Return top-n recommended places for a city."""
    places, _, _ = get_recommendations(city)
    return places[:n]


def plot_combined_map(locations, center_coords, destination):
    """
    Plot a map with all locations (attractions, hotels, restaurants)
    
    Args:
        locations: List of dictionaries containing location data
        center_coords: [lat, lon] for the map center
        destination: Name of the destination for the map title
    """
    map_obj = folium.Map(location=center_coords, zoom_start=12)

    # Add markers based on type
    for loc in locations:
        if loc.get("type") == "attraction":
            folium.Marker(
                [loc["lat"], loc["lng"]],
                icon=folium.Icon(color="green", icon="info-sign"),
                popup=f"{loc['name']} (⭐{loc.get('rating', 'N/A')})"
            ).add_to(map_obj)
        elif loc.get("type") == "accommodation":
            folium.Marker(
                [loc["lat"], loc["lng"]],
                icon=folium.Icon(color="blue", icon="home"),
                popup=f"{loc['name']} (Hotel)"
            ).add_to(map_obj)
        elif loc.get("type") == "restaurant":
            folium.Marker(
                [loc["lat"], loc["lng"]],
                icon=folium.Icon(color="red", icon="cutlery"),
                popup=f"{loc['name']} (⭐{loc.get('rating', 'N/A')})"
            ).add_to(map_obj)

    # Add title
    title_html = f'''
        <h3 align="center" style="font-size:16px">
            <b>Travel Map: {destination}</b>
        </h3>
    '''
    map_obj.get_root().html.add_child(folium.Element(title_html))

    map_obj.save("travel_map.html")
