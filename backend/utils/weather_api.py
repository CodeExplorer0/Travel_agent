import os
import requests
from dotenv import load_dotenv
from datetime import datetime, timezone

# Load environment variables
load_dotenv()

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

def get_clothing_suggestion(weather_condition):
    suggestions = {
        "rain": "Waterproof jacket, umbrella, and waterproof shoes",
        "clear": "Light clothing, sunglasses, and sunscreen",
        "cloudy": "Light jacket or sweater",
        "extreme heat": "Light breathable fabrics, hat, and extra water",
        "cold": "Layered clothing, warm jacket, and gloves"
    }
    return suggestions.get(weather_condition.lower(), "Standard casual wear")

def get_weather_condition(forecast_data, target_date):
    """
    Extract the dominant weather condition for a specific date (YYYY-MM-DD).
    Considers all 3-hour intervals and returns the most frequent condition.
    """
    date_conditions = []
    for entry in forecast_data.get('list', []):
        # Convert UNIX timestamp to a timezone-aware UTC datetime
        entry_date = datetime.fromtimestamp(entry['dt'], tz=timezone.utc).strftime('%Y-%m-%d')
        if entry_date == target_date:
            # Use 'main' for broad category (Rain, Clear, Clouds, etc.)
            condition = entry['weather'][0]['main'].lower()
            date_conditions.append(condition)
    if not date_conditions:
        return "clear"
    # Return the most frequent condition
    return max(set(date_conditions), key=date_conditions.count)


def geocode_place(place_name):
    """
    Geocode a place name to (latitude, longitude) using Google Maps Geocoding API.
    """
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": place_name, "key": GOOGLE_MAPS_API_KEY}
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data["status"] == "OK":
            location = data["results"][0]["geometry"]["location"]
            return location["lat"], location["lng"]
        raise ValueError("Geocoding failed: " + data.get("status", "Unknown error"))
    except Exception as e:
        print(f"Error in geocode_place: {e}")
        raise

def get_5_day_forecast(lat, lon):
    """
    Get 5-day weather forecast for given latitude and longitude using OpenWeatherMap API.
    Returns the raw forecast data (list of 3-hour intervals).
    """
    url = "https://api.openweathermap.org/data/2.5/forecast"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": OPENWEATHER_API_KEY,
        "units": "metric"
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get('cod') != '200':
            raise ValueError(f"Weather API Error: {data.get('message', 'Unknown error')}")
        return data
    except Exception as e:
        print(f"Error in get_5_day_forecast: {e}")
        return {}

# Example usage (uncomment to test):
# lat, lon = geocode_place("Kochi, Kerala, India")
# forecast = get_5_day_forecast(lat, lon)
# print(get_weather_condition(forecast, "2025-05-09"))
# print(get_clothing_suggestion("rain"))
