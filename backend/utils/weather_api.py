import requests

def get_weather(destination):
    """Get weather forecast for a given destination."""
    api_key = "YOUR_OPENWEATHER_API_KEY"
    url = f"http://api.openweathermap.org/data/2.5/weather?q={destination}&appid={api_key}"
    response = requests.get(url)
    weather_data = response.json()
    
    # Example of extracting relevant weather data
    weather_description = weather_data['weather'][0]['description']
    return weather_description
