import os
import time
import html
import folium
import requests
import googlemaps
from math import radians, cos, sin, asin, sqrt
from dotenv import load_dotenv

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

def fetch_hotels_by_coordinates(lat, lng, max_price, checkin_date, checkout_date):
    try:
        url = "https://booking-com15.p.rapidapi.com/api/v1/hotels/searchHotelsByCoordinates"
        query = {
            "latitude": str(lat),
            "longitude": str(lng),
            "arrival_date": checkin_date,
            "departure_date": checkout_date,
            "currency_code": "INR",
            "max_total_price": str(max_price)
        }
        response = requests.get(url, headers=HEADERS, params=query)
        return response.json() if response.status_code == 200 else {}
    except Exception as e:
        print(f"❌ Error fetching hotels: {str(e)}")
        return {}

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
