import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY')

def get_weather(destination):
    """Get weather forecast for a given destination."""
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={destination}&appid={OPENWEATHER_API_KEY}"
        response = requests.get(url)
        
        if response.status_code == 200:
            weather_data = response.json()
            if 'weather' in weather_data and len(weather_data['weather']) > 0:
                # Example of extracting relevant weather data
                weather_description = weather_data['weather'][0]['description']
                return weather_description
            else:
                return {"error": "No weather information found."}
        else:
            return {"error": f"Failed to fetch weather. Status code: {response.status_code}"}
    
    except Exception as e:
        return {"error": f"Error fetching weather data: {e}"}
