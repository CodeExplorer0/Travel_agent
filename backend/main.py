import json
import requests
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
import re
import concurrent.futures

from utils.weather_api import get_clothing_suggestion, geocode_place, get_5_day_forecast, get_weather_condition
from utils.places_recommendation import get_recommendations, plot_combined_map
from utils.stays_api import fetch_hotels_by_coordinates
from data.reddit_scraper import scrape_relevant_data
from vector_store import store_itinerary
from iternary_generator import group_days_by_city, allocate_budget, validate_total_spend, generate_itinerary_text

# Load .env variables
load_dotenv()

OPENAI_API_URL = "https://open-ai21.p.rapidapi.com/conversationllama"
HEADERS = {
    "x-rapidapi-key": os.getenv("OPENAI_API_KEY"),
    "x-rapidapi-host": "open-ai21.p.rapidapi.com",
    "Content-Type": "application/json"
}

def parse_user_input(prompt):
    from prompts.system_prompt import system_prompt
    from prompts.weather_rules import weather_rules
    payload = {
        "messages": [
            {
                "role": "system",
                "content": f"{system_prompt}\n{weather_rules}\nRespond ONLY with a valid JSON object. Do not include any text or explanation before or after the JSON. Output JSON with: destination, days, budget, interests, travel_style, start_date, end_date, number_of_people, reason_of_visit"
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "web_access": True
    }
    try:
        response = requests.post(OPENAI_API_URL, json=payload, headers=HEADERS)
        result = response.json()
        if 'result' in result:
            llm_output = result['result']
        elif 'choices' in result and 'message' in result['choices'][0]:
            llm_output = result['choices'][0]['message']['content']
        elif 'message' in result:
            llm_output = result['message']
        else:
            print("No valid key found in LLM response.")
            return None
        print(f"LLM Output: {llm_output}")  # Print the LLM output here
        try:
            return json.loads(llm_output)
        except Exception:
            match = re.search(r'\{.*\}', llm_output, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except Exception as e2:
                    print(f"Regex JSON parse error: {e2}")
            print("Failed to extract valid JSON from LLM output.")
            return None
    except Exception as e:
        print(f"API Error: {str(e)}")
        return None

def cross_question_missing_fields(user_input):
    questions = {
        "budget": "What is your total trip budget (in INR)? ",
        "days": "How many days will your trip last? ",
        "start_date": "What is your trip start date? (YYYY-MM-DD) ",
        "number_of_people": "How many people are travelling? ",
        "reason_of_visit": "What is the reason for your visit (e.g., leisure, business, honeymoon, family, etc.)? "
    }
    for field, question in questions.items():
        if field not in user_input or not user_input[field]:
            value = input(question)
            if field in ["budget", "days", "number_of_people"]:
                try:
                    value = int(value)
                except Exception:
                    pass
            user_input[field] = value
    if "end_date" not in user_input or not user_input["end_date"]:
        try:
            days = int(user_input.get("days", 1))
            start = datetime.strptime(user_input["start_date"], "%Y-%m-%d")
            user_input["end_date"] = (start + timedelta(days=days)).strftime("%Y-%m-%d")
        except Exception:
            user_input["end_date"] = ""
    return user_input

def generate_daily_activities(city, date, places, weather_condition, interests):
    """Generate daily activities based on weather and interests"""
    filtered_places = []
    for place in places:
        if place['city'] == city:
            # Weather-based filtering
            if "rain" in weather_condition.lower() and place.get('category') == 'outdoor':
                continue
            if "sun" in weather_condition.lower() and place.get('category') == 'indoor':
                continue
            filtered_places.append(place)
    # Select 3-4 main activities
    selected = sorted(filtered_places, key=lambda x: x['score'], reverse=True)[:4]
    return {
        "morning": selected[0]['name'] if len(selected) > 0 else "Leisurely Breakfast",
        "afternoon": selected[1]['name'] if len(selected) > 1 else "Local Market Visit",
        "evening": selected[2]['name'] if len(selected) > 2 else "Sunset Cruise"
    }

def generate_full_itinerary(prompt):
    try:
        user_input = parse_user_input(prompt)
        if not user_input:
            return {"error": "Failed to parse input"}

        user_input = cross_question_missing_fields(user_input)

        # Step 2: Extract keywords and scrape relevant Reddit posts in parallel with other tasks
        keywords = [user_input["destination"]] + user_input.get("interests", [])
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_scrape = executor.submit(scrape_relevant_data, keywords)
            future_weather = executor.submit(geocode_place, user_input["destination"])
            weather_data = future_weather.result()  # Blocking call to get weather data
            future_scrape.result()  # Wait for Reddit scraping to complete

        # Weather data processing
        lat, lon = weather_data
        weather_forecast = get_5_day_forecast(lat, lon)

        # Step 3: Get all recommended places for the destination (moved up)
        all_places = []
        places, lat, lon = get_recommendations(user_input["destination"])
        all_places.extend(places)

        # Step 4: Daily plan
        itinerary_days = []
        start_date = user_input["start_date"]
        days = int(user_input["days"])
        for i in range(days):
            day_date = (datetime.strptime(start_date, "%Y-%m-%d") + timedelta(days=i)).strftime("%Y-%m-%d")
            itinerary_days.append({"day": i+1, "date": day_date, "city": user_input["destination"]})

        # Step 4a: Generate detailed daily plans
        budget_alloc = allocate_budget(user_input["budget"], days)
        per_day_food = budget_alloc["food_per_day"]
        per_day_sights = budget_alloc["sights_per_day"]

        detailed_days = []
        for day in itinerary_days:
            date_str = day['date']
            weather_condition = get_weather_condition(weather_forecast, date_str)
            # Get activities
            daily_activities = generate_daily_activities(
                user_input["destination"],
                date_str,
                all_places,
                weather_condition,
                user_input.get("interests", [])
            )
            # Get food recommendations
            food_options = get_recommendations(user_input["destination"], "restaurant")[0][:3]
            detailed_days.append({
                **day,
                "weather": weather_condition.capitalize(),
                "activities": daily_activities,
                "food_recommendations": [{
                    "name": f.get('name'),
                    "type": " | ".join(f.get('types', [])),
                    "rating": f.get('rating')
                } for f in food_options],
                "clothing_suggestion": get_clothing_suggestion(weather_condition),
                "estimated_costs": {
                    "activities": per_day_sights,
                    "food": per_day_food,
                    "accommodation": budget_alloc["hotel_per_day"]
                }
            })

        # Step 5: Group by city
        city_segments = group_days_by_city(itinerary_days)

        # Step 6: Budget allocation (already done above)

        per_night_budget = budget_alloc["hotel_per_day"]

        # Step 7: Hotels
        hotels = []
        for segment in city_segments:
            city = segment["city"]
            checkin = segment["checkin"]
            checkout = segment["checkout"]
            lat, lng = geocode_place(city)
            nights = (datetime.strptime(checkout, "%Y-%m-%d") - datetime.strptime(checkin, "%Y-%m-%d")).days
            max_price = int(per_night_budget * nights)
            hotels_data = fetch_hotels_by_coordinates(lat, lng, max_price, checkin, checkout)
            hotel_list = hotels_data.get("data", {}).get("result", [])
            if hotel_list:
                best = sorted(hotel_list, key=lambda h: h.get("composite_price_breakdown", {}).get("gross_amount_hotel_currency", {}).get("value", 1e9))[0]
                hotels.append({
                    "city": city,
                    "checkin": checkin,
                    "checkout": checkout,
                    "hotel": best
                })

        # Step 8: Places map
        all_hotels_for_map = []
        for seg in city_segments:
            places, lat, lon = get_recommendations(seg["city"])
            all_places.extend(places)
            for h in hotels:
                if h["city"] == seg["city"]:
                    hotel_info = h["hotel"]
                    hotel_info["latitude"] = hotel_info.get("latitude") or lat
                    hotel_info["longitude"] = hotel_info.get("longitude") or lon
                    all_hotels_for_map.append(hotel_info)
            plot_combined_map(all_places, all_hotels_for_map, lat, lon)

        # Step 9: Cost estimates
        food_sum = per_day_food * days
        sights_sum = per_day_sights * days
        hotel_sum = sum(h["hotel"].get("composite_price_breakdown", {}).get("gross_amount_hotel_currency", {}).get("value", 0) for h in hotels)

        # Step 10: Validate budget
        if not validate_total_spend(user_input["budget"], hotel_sum, food_sum, sights_sum):
            return {"error": "Itinerary exceeds your specified budget. Please increase budget or reduce trip length."}

        # Step 11: Build itinerary
        itinerary = {
            "destination": user_input["destination"],
            "duration_days": days,
            "total_budget": user_input["budget"],
            "interests": user_input.get("interests", []),
            "number_of_people": user_input.get("number_of_people", 1),
            "reason_of_visit": user_input.get("reason_of_visit", ""),
            "start_date": user_input.get("start_date"),
            "end_date": user_input.get("end_date"),
            "city_segments": city_segments,
            "hotels": hotels,
            "food_total": food_sum,
            "sights_total": sights_sum,
            "hotel_total": hotel_sum,
            "total_spent": hotel_sum + food_sum + sights_sum,
            "daily_plan": itinerary_days,
            "detailed_daily_plan": detailed_days,
            "weather_forecast": [{
                "date": (datetime.strptime(user_input["start_date"], "%Y-%m-%d") + timedelta(days=i)).strftime("%Y-%m-%d"),
                "condition": get_weather_condition(weather_forecast, (datetime.strptime(user_input["start_date"], "%Y-%m-%d") + timedelta(days=i)).strftime("%Y-%m-%d"))
            } for i in range(days)]
        }

        # Step 12: Store itinerary
        store_itinerary(itinerary)
        return itinerary

    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    prompt = input("Enter your travel request: ")
    result = generate_full_itinerary(prompt)
    with open("itinerary.json", "w") as f:
        json.dump(result, f, indent=2)
    print("✅ Itinerary saved to itinerary.json")
    print("🗺️ Map saved to travel_map.html")
    # ---- TEXT OUTPUT ----
    # If the itinerary was generated successfully, print a readable version
    if "error" not in result:
        text_itinerary = generate_itinerary_text(result)
        with open("itinerary.txt", "w", encoding="utf-8") as tf:
            tf.write(text_itinerary)
        print("\n📄 Human-readable itinerary saved to itinerary.txt\n")
        print(text_itinerary)  # Optionally print to console
    else:
        print("Error:", result["error"])
