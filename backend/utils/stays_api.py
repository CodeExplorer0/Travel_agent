import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
BOOKING_API_KEY = os.getenv('BOOKING_API_KEY')

def get_stay_recommendations(destination, budget):
    """Get stay recommendations from Booking/Airbnb based on budget."""
    try:
        url = f"https://api.booking.com/v1/hotels?location={destination}&budget={budget}"
        headers = {"Authorization": f"Bearer {BOOKING_API_KEY}"}
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            stays = response.json()
            # Example of extracting stay options within budget
            budget_stays = [stay for stay in stays['results'] if stay['price'] <= budget]
            return budget_stays
        else:
            return {"error": f"Failed to fetch stays. Status code: {response.status_code}"}
    
    except Exception as e:
        return {"error": f"Error fetching stay recommendations: {e}"}
