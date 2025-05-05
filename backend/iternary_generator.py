import random
from backend.utils.weather_api import get_weather
from backend.utils.yelp_api import get_places
from backend.utils.stays_api import get_stays
from backend.utils.maps_api import get_directions
from datetime import datetime

MANDATORY_FIELDS = ["destination", "start_date", "end_date", "interests", "travel_style"]

def validate_user_input(user_input):
    missing_fields = [field for field in MANDATORY_FIELDS if field not in user_input or not user_input[field]]
    return missing_fields

def cross_question(user_input):
    missing = validate_user_input(user_input)
    if missing:
        return {
            "status": "incomplete",
            "message": f"Missing details: {', '.join(missing)}. Please provide them to proceed."
        }
    if "budget" not in user_input:
        return {
            "status": "incomplete",
            "message": "What is your estimated budget for the trip?"
        }
    if "purpose" not in user_input:
        return {
            "status": "incomplete",
            "message": "Could you tell us the main purpose of your trip (leisure, honeymoon, adventure, etc.)?"
        }
    return {"status": "complete"}

def calculate_days(start_date, end_date):
    """Calculate number of days between start_date and end_date."""
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        return (end - start).days
    except Exception as e:
        return {"status": "error", "message": f"Error calculating days: {e}"}

def generate_itinerary(user_input):
    check = cross_question(user_input)
    if check["status"] != "complete":
        return check

    city = user_input["destination"]
    interests = user_input["interests"]
    travel_style = user_input.get("travel_style", "solo")
    start_date = user_input.get("start_date")
    end_date = user_input.get("end_date")

    # Calculate days based on start_date and end_date
    days = calculate_days(start_date, end_date)
    if isinstance(days, dict):  # If there's an error
        return days

    itinerary = []
    for day in range(1, days + 1):
        day_plan = {
            "day": day,
            "weather": get_weather(city),
            "activities": get_places(city, interests),
            "accommodation": get_stays(city, travel_style),
            "directions": get_directions(city)
        }
        itinerary.append(day_plan)

    return {
        "status": "success",
        "itinerary": itinerary
    }
