import os
import requests
from dotenv import load_dotenv

load_dotenv()
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

def geocode_place(place_name):
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": place_name, "key": os.getenv("GOOGLE_MAPS_API_KEY")}
    response = requests.get(url, params=params)
    data = response.json()
    if data["status"] == "OK":
        location = data["results"][0]["geometry"]["location"]
        return location["lat"], location["lng"]
    raise ValueError("Geocoding failed: " + data.get("status", "Unknown error"))

def get_5_day_forecast(lat, lon):
    url = "https://api.openweathermap.org/data/2.5/forecast"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": OPENWEATHER_API_KEY,
        "units": "metric"
    }
    response = requests.get(url, params=params)
    return response.json()
