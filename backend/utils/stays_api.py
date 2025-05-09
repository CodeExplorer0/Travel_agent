import os
import time
import html
import folium
import requests
import googlemaps
from math import radians, cos, sin, asin, sqrt
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

# Ensure API keys are present
if not GOOGLE_MAPS_API_KEY or not RAPIDAPI_KEY:
    raise ValueError("Missing API keys. Check your .env file.")

# Initialize Google Maps client
gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)

# Headers for RapidAPI
HEADERS = {
    "x-rapidapi-key": RAPIDAPI_KEY,
    "x-rapidapi-host": "booking-com15.p.rapidapi.com"
}

def get_lat_lng_from_place(place):
    try:
        geocode_result = gmaps.geocode(place)
        if geocode_result:
            lat = geocode_result[0]["geometry"]["location"]["lat"]
            lng = geocode_result[0]["geometry"]["location"]["lng"]
            print(f"📍 Geocode: {place} -> Lat: {lat}, Lng: {lng}")
            return lat, lng
        print("❌ No results found for the place.")
    except Exception as e:
        print(f"❌ Error in geocoding: {str(e)}")
    return None, None

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
    return R * 2 * asin(sqrt(a))

def fetch_hotels_by_coordinates(lat, lng, max_price, check_in, check_out):
    try:
        # Validate dates
        if not check_in or not check_out:
            from datetime import datetime, timedelta
            check_in = datetime.now().strftime("%Y-%m-%d")
            check_out = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            print(f"⚠️ Using default dates: {check_in} to {check_out}")

        print(f"🔍 Searching for hotels near coordinates: {lat}, {lng}")
        print(f"💰 Max price: {max_price}")
        print(f"📅 Check-in: {check_in}, Check-out: {check_out}")

        url = "https://booking-com.p.rapidapi.com/v1/hotels/search-by-coordinates"
        querystring = {
            "units": "metric",
            "room_number": "1",
            "checkout_date": check_out,
            "checkin_date": check_in,
            "adults_number": "2",
            "order_by": "popularity",
            "filter_by_currency": "INR",
            "locale": "en-us",
            "longitude": str(lng),
            "latitude": str(lat),
            "page_number": "0",
            "categories_filter_ids": "class::2,class::4,free_cancellation::1",
            "include_adjacency": "true"
        }

        headers = {
            "X-RapidAPI-Key": os.getenv('RAPIDAPI_KEY'),
            "X-RapidAPI-Host": "booking-com.p.rapidapi.com"
        }

        print("🌐 Making API request to Booking.com...")
        response = requests.get(url, headers=headers, params=querystring)
        print(f"📡 API Response Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ API request failed with status {response.status_code}")
            return []

        data = response.json()
        print(f"📊 Raw API Response: {json.dumps(data, indent=2)}")

        if not data.get('result'):
            print("❌ No hotels found in the response")
            return []

        hotels = []
        for hotel in data['result']:
            try:
                # Skip if essential data is missing
                if not all(key in hotel for key in ['hotel_name', 'min_total_price', 'latitude', 'longitude']):
                    continue

                # Validate coordinates
                hotel_lat = float(hotel['latitude'])
                hotel_lng = float(hotel['longitude'])
                if not (-90 <= hotel_lat <= 90) or not (-180 <= hotel_lng <= 180):
                    continue

                # Calculate distance from center
                distance = haversine(lat, lng, hotel_lat, hotel_lng)
                if distance > 10:  # Skip if more than 10km away
                    continue

                # Check price
                price = float(hotel['min_total_price'])
                if price > max_price * 1.2:  # Allow 20% price buffer
                    continue

                # Get additional details
                hotel_obj = {
                    'name': hotel['hotel_name'],
                    'price': price,
                    'rating': float(hotel.get('review_score', 0)),
                    'reviews': int(hotel.get('review_nr', 0)),
                    'latitude': hotel_lat,
                    'longitude': hotel_lng,
                    'distance': distance,
                    'address': hotel.get('address', ''),
                    'description': hotel.get('description', ''),
                    'accommodation_type': hotel.get('accommodation_type_name', 'Hotel'),
                    'photos': [photo.get('url_max', '') for photo in hotel.get('photos', [])[:3]]
                }

                # Calculate score based on rating, reviews, and price
                hotel_obj['score'] = (
                    (hotel_obj['rating'] * 0.4) +
                    (min(hotel_obj['reviews'], 100) / 100 * 0.2) +
                    ((1 - (price / max_price)) * 0.4)
                )

                hotels.append(hotel_obj)

            except Exception as e:
                print(f"❌ Error processing hotel {hotel.get('hotel_name', 'Unknown')}: {str(e)}")
                continue

        # Sort by score and return top 10
        hotels.sort(key=lambda x: x['score'], reverse=True)
        return hotels[:10]

    except Exception as e:
        print(f"❌ Error in fetch_hotels_by_coordinates: {str(e)}")
        return []

def fetch_hotel_review_scores(hotel_id):
    try:
        url = "https://booking-com15.p.rapidapi.com/api/v1/hotels/getHotelReviewScores"
        params = {"hotel_id": str(hotel_id), "languagecode": "en-us"}
        res = requests.get(url, headers=HEADERS, params=params)
        data = res.json()
        return data.get("data", []) if data.get("status") == "true" else []
    except Exception as e:
        print(f"❌ Review score error: {str(e)}")
        return []

def fetch_hotel_reviews(hotel_id):
    try:
        url = "https://booking-com15.p.rapidapi.com/api/v1/hotels/getHotelReviews"
        params = {
            "hotel_id": str(hotel_id),
            "sort_option_id": "sort_score_desc",
            "page_number": "1",
            "languagecode": "en-us"
        }
        res = requests.get(url, headers=HEADERS, params=params)
        data = res.json()
        if data.get("status") == "true":
            return sorted(data["data"]["result"], key=lambda x: x.get("average_score", 0), reverse=True)[:5]
        return []
    except Exception as e:
        print(f"❌ Error fetching reviews: {str(e)}")
        return []

def enrich_hotel_data_with_reviews(hotel):
    hotel_id = hotel.get("hotel_id")
    if not hotel_id:
        return hotel
    hotel["top_reviews"] = fetch_hotel_reviews(hotel_id)
    hotel["review_scores"] = fetch_hotel_review_scores(hotel_id)
    time.sleep(1)  # Avoid hitting rate limits
    return hotel

def plot_hotels_on_map(hotels, center_lat, center_lng):
    map_obj = folium.Map(location=[center_lat, center_lng], zoom_start=13)

    for hotel in hotels:
        name = hotel.get("hotel_name", "Unnamed Hotel")
        price = hotel.get("composite_price_breakdown", {}).get("gross_amount_hotel_currency", {}).get("value", "N/A")
        lat = hotel.get("latitude")
        lng = hotel.get("longitude")
        dist = hotel.get("distance_km", "?")
        review_snippet = "No reviews available"

        if hotel.get("top_reviews"):
            top = hotel["top_reviews"][0]
            pros = html.escape(top.get("pros", ""))
            score = top.get("average_score", "N/A")
            review_snippet = f"{pros}<br>Score: {score}"

        tooltip = f"""
        <b>{name}</b><br>
        ₹{price}, {dist} km from center<br>
        {review_snippet}
        """

        folium.Marker(
            [lat, lng],
            icon=folium.Icon(color="blue", icon="info-sign"),
            tooltip=folium.Tooltip(tooltip, sticky=True)
        ).add_to(map_obj)

    map_obj.save("hotels_map.html")
    print("🗺️ Map saved as hotels_map.html")

def fetch_and_map_hotels(destination, max_budget_inr, checkin_date, checkout_date):
    lat, lng = get_lat_lng_from_place(destination)
    if lat is None or lng is None:
        return []

    raw_hotels = fetch_hotels_by_coordinates(lat, lng, max_budget_inr, checkin_date, checkout_date)
    hotel_list = raw_hotels.get("data", {}).get("result", [])
    if not hotel_list:
        print("❌ No hotels fetched.")
        return []

    MAX_DISTANCE_KM = 30
    filtered = []
    for h in hotel_list:
        price = h.get("composite_price_breakdown", {}).get("gross_amount_hotel_currency", {}).get("value")
        h_lat = h.get("latitude")
        h_lng = h.get("longitude")
        if not price or not h_lat or not h_lng:
            continue
        dist = haversine(lat, lng, h_lat, h_lng)
        if dist <= MAX_DISTANCE_KM and price <= max_budget_inr:
            h["distance_km"] = round(dist, 2)
            filtered.append(h)

    if not filtered:
        print("❌ No hotels within budget/distance.")
        return []

    enriched = [enrich_hotel_data_with_reviews(h) for h in filtered]

    def get_score(h):
        top = h.get("top_reviews", [])
        return top[0].get("average_score", 0) if top else 0

    top_hotels = sorted(enriched, key=get_score, reverse=True)[:10]
    plot_hotels_on_map(top_hotels, lat, lng)
    return top_hotels
