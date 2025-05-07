import os
import requests
import googlemaps
import folium
from math import radians, cos, sin, asin, sqrt
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

# Initialize Google Maps API
gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)

# Booking API headers
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
        else:
            print("❌ No results found for the place.")
            return None, None
    except Exception as e:
        print(f"❌ Error in geocoding: {str(e)}")
        return None, None

def haversine(lat1, lon1, lat2, lon2):
    """Calculate distance in km between two lat/lng points."""
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return R * c

def fetch_hotels_by_coordinates(lat, lng, max_price, checkin_date, checkout_date):
    try:
        url = "https://booking-com15.p.rapidapi.com/api/v1/hotels/searchHotelsByCoordinates"
        querystring = {
            "latitude": str(lat),
            "longitude": str(lng),
            "arrival_date": checkin_date,
            "departure_date": checkout_date,
            "currency_code": "INR",
            "max_total_price": str(max_price)
        }
        response = requests.get(url, headers=HEADERS, params=querystring)
        if response.status_code == 200:
            return response.json()
        else:
            print("❌ Failed to fetch hotels:", response.text)
            return {}
    except Exception as e:
        print(f"❌ Error fetching hotels: {str(e)}")
        return {}

def fetch_hotel_review_scores(hotel_id):
    try:
        url = "https://booking-com15.p.rapidapi.com/api/v1/hotels/getHotelReviewScores"
        querystring = {
            "hotel_id": str(hotel_id),
            "languagecode": "en-us"
        }
        response = requests.get(url, headers=HEADERS, params=querystring)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "true" and data.get("data"):
                return data["data"]
        return []
    except Exception as e:
        print(f"❌ Error fetching review scores: {str(e)}")
        return []

def fetch_hotel_reviews(hotel_id, sort_option="sort_score_desc"):
    try:
        url = "https://booking-com15.p.rapidapi.com/api/v1/hotels/getHotelReviews"
        querystring = {
            "hotel_id": str(hotel_id),
            "sort_option_id": sort_option,
            "page_number": "1",
            "languagecode": "en-us"
        }
        response = requests.get(url, headers=HEADERS, params=querystring)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "true" and data.get("data"):
                reviews = data["data"]["result"]
                return sorted(reviews, key=lambda x: x.get("average_score", 0), reverse=True)[:10]
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
    return hotel

def plot_hotels_on_map(enriched_hotels, center_lat, center_lng):
    hotel_ids = []
    map_obj = folium.Map(location=[center_lat, center_lng], zoom_start=14)

    for hotel in enriched_hotels:
        hotel_name = hotel.get("hotel_name")
        price = hotel.get("composite_price_breakdown", {}).get("gross_amount_hotel_currency", {}).get("value")
        hotel_lat = hotel.get("latitude")
        hotel_lng = hotel.get("longitude")
        hotel_id = hotel.get("hotel_id")
        main_photo_url = hotel.get("main_photo_url")
        distance = hotel.get("distance_km", None)

        if hotel_name and hotel_lat and hotel_lng:
            import html
            top_reviews = hotel.get("top_reviews", [])
            review_snippet = "<em>No reviews available</em>"
            if top_reviews:
                top_review = top_reviews[0]
                pros = html.escape(top_review.get("pros", ""))
                score = top_review.get("average_score", "N/A")
                review_snippet = f"<em>{pros}</em><br><strong>Score:</strong> {score}"

            tooltip_content = f"""
            <strong>{hotel_name}</strong><br>
            <img src="{main_photo_url}" width="150" height="100" style="border-radius: 5px;"><br>
            Price: ₹{price}<br>
            Distance: {distance} km<br>
            {review_snippet}
            """

            folium.Marker(
                location=[hotel_lat, hotel_lng],
                tooltip=folium.Tooltip(tooltip_content),
                icon=folium.Icon(color="blue", icon="info-sign")
            ).add_to(map_obj)

            hotel_ids.append(hotel_id)

    map_obj.save("hotels_map.html")
    print("🗺️ Map saved as hotels_map.html")
    return hotel_ids

def fetch_and_map_hotels(destination, max_budget_inr, checkin_date, checkout_date):
    lat, lng = get_lat_lng_from_place(destination)
    if lat is None or lng is None:
        return []

    raw_hotels_data = fetch_hotels_by_coordinates(lat, lng, max_price=max_budget_inr, checkin_date=checkin_date, checkout_date=checkout_date)
    hotels = raw_hotels_data.get("data", {}).get("result", [])
    if not hotels:
        print("❌ No hotels fetched.")
        return []

    # Filter by distance and budget
    MAX_DISTANCE_KM = 30
    filtered_hotels = []
    for hotel in hotels:
        price = hotel.get("composite_price_breakdown", {}).get("gross_amount_hotel_currency", {}).get("value")
        h_lat = hotel.get("latitude")
        h_lng = hotel.get("longitude")
        if price is not None and h_lat and h_lng:
            dist = haversine(lat, lng, h_lat, h_lng)
            if dist <= MAX_DISTANCE_KM and price <= max_budget_inr:
                hotel["distance_km"] = round(dist, 2)
                filtered_hotels.append(hotel)

    if not filtered_hotels:
        print("❌ No hotels matched the distance and budget criteria.")
        return []

    # Enrich and select top 10 based on review score
    enriched_hotels = [enrich_hotel_data_with_reviews(h) for h in filtered_hotels]

    def get_score(hotel):
        top = hotel.get("top_reviews", [])
        if top:
            return top[0].get("average_score", 0)
        return 0

    top_10_hotels = sorted(enriched_hotels, key=get_score, reverse=True)[:10]
    return plot_hotels_on_map(top_10_hotels, lat, lng)
