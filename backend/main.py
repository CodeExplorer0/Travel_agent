import json
import requests
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
import re
import concurrent.futures
import google.generativeai as genai
import googlemaps

from utils.weather_api import get_clothing_suggestion, geocode_place, get_5_day_forecast, get_weather_condition
from utils.places_recommendation import get_recommendations, plot_combined_map
from utils.stays_api import fetch_hotels_by_coordinates
from utils.maps_api import get_lat_lng_from_place
# from data.reddit_scraper import scrape_relevant_data  # Commented out scraping
from vector_store import store_itinerary
from iternary_generator import group_days_by_city, allocate_budget, validate_total_spend, generate_itinerary_text

# Load .env variables
load_dotenv()

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_CHAT_API_KEY")
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"

# List available models
for m in genai.list_models():
    print(f"Model: {m.name}")

def parse_user_input(prompt):
    # First try to parse as direct JSON input
    try:
        return json.loads(prompt)
    except json.JSONDecodeError:
        # If not JSON, treat as natural language and process with Gemini
        from prompts.system_prompt import system_prompt
        from prompts.weather_rules import weather_rules
        
        # Prepare the prompt
        full_prompt = f"{system_prompt}\n{weather_rules}\nRespond ONLY with a valid JSON object. Do not include any text or explanation before or after the JSON. Output JSON with: destination, days, budget, interests, travel_style, start_date, end_date, number_of_people, reason_of_visit\n\nUser request: {prompt}"
        
        # Prepare the request payload
        payload = {
            "contents": [{
                "parts": [{"text": full_prompt}]
            }]
        }
        
        try:
            # Make the API request
            response = requests.post(GEMINI_API_URL, json=payload)
            result = response.json()
            
            if 'candidates' in result and len(result['candidates']) > 0:
                llm_output = result['candidates'][0]['content']['parts'][0]['text']
            else:
                print("No valid response from Gemini API")
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
    
    # Ensure we have valid dates
    if "start_date" not in user_input or user_input["start_date"] == "To be determined":
        # Default to next week if no date provided
        default_start = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        value = input(f"Enter start date (YYYY-MM-DD) [default: {default_start}]: ")
        user_input["start_date"] = value if value else default_start
    
    # Calculate end date based on days
    if "days" in user_input:
        try:
            days = int(user_input["days"])
            start = datetime.strptime(user_input["start_date"], "%Y-%m-%d")
            user_input["end_date"] = (start + timedelta(days=days-1)).strftime("%Y-%m-%d")
        except Exception:
            user_input["end_date"] = user_input["start_date"]
    
    # Ask for other missing fields
    for field, question in questions.items():
        if field not in user_input or not user_input[field]:
            value = input(question)
            if field in ["budget", "days", "number_of_people"]:
                try:
                    value = int(value)
                except Exception:
                    pass
            user_input[field] = value
            
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
        "morning": {"name": selected[0]['name'] if len(selected) > 0 else "Leisurely Breakfast", "location": selected[0].get('vicinity', city) if len(selected) > 0 else city},
        "afternoon": {"name": selected[1]['name'] if len(selected) > 1 else "Local Market Visit", "location": selected[1].get('vicinity', city) if len(selected) > 1 else city},
        "evening": {"name": selected[2]['name'] if len(selected) > 2 else "Sunset Cruise", "location": selected[2].get('vicinity', city) if len(selected) > 2 else city}
    }

def extract_coordinates_from_itinerary(itinerary_json):
    coordinates_data = {
        'accommodations': [],
        'restaurants': [],
        'attractions': []
    }
    for day, plan in itinerary_json.get('itinerary', {}).items():
        # Extract accommodation coordinates
        if 'accommodation' in plan:
            acc = plan['accommodation']
            if 'name' in acc:
                lat, lng = get_lat_lng_from_place(acc['name'])
                if lat and lng:
                    coordinates_data['accommodations'].append({
                        'name': acc['name'],
                        'latitude': lat,
                        'longitude': lng,
                        'address': acc.get('address', '')
                    })
        # Extract food/restaurant coordinates
        if 'food' in plan:
            for food_item in plan['food']:
                if 'name' in food_item:
                    lat, lng = get_lat_lng_from_place(food_item['name'])
                    if lat and lng:
                        coordinates_data['restaurants'].append({
                            'name': food_item['name'],
                            'latitude': lat,
                            'longitude': lng,
                            'address': food_item.get('address', '')
                        })
        # Extract activity/attraction coordinates
        for activity in plan.get('activities', []):
            if 'name' in activity:
                lat, lng = get_lat_lng_from_place(activity['name'])
                if lat and lng:
                    coordinates_data['attractions'].append({
                        'name': activity['name'],
                        'latitude': lat,
                        'longitude': lng,
                        'address': activity.get('address', '')
                    })
    return coordinates_data

def generate_full_itinerary(user_input):
    try:
        print("\n🚀 Starting itinerary generation...")
        
        # Create a full itinerary object matching the provided structure
        full_itinerary = {
            "tripData": {
                "destination": user_input.get("destination"),
                "startDate": user_input.get("start_date"),
                "endDate": user_input.get("end_date"),
                "duration": user_input.get("days"),
                "currency": {
                    "name": "Indian Rupee (₹)",
                    "conversionRate": 1.0  # Already in INR
                },
                "weather": user_input.get("weather_considerations", ""),
                "language": "Hindi, English",
                "emergencyContact": "112",
                "electricalOutlet": "Type C, 230V",
                "transportation": ["Auto-rickshaw", "Taxi", "Bus", "Metro"],
                "cost": {
                    "transportation": {"inr": 0},
                    "accommodation": {"inr": 0},
                    "food": {"inr": 0},
                    "activities": {"inr": 0},
                    "miscellaneous": {"inr": 0},
                    "total": {"inr": user_input.get("budget", 0)}
                }
            },
            "itineraryDays": []
        }
        
        # Get coordinates for destination
        print("\n🌍 Getting coordinates for destination...")
        lat, lng = get_lat_lng_from_place(user_input["destination"])
        if not lat or not lng:
            raise ValueError(f"Could not get coordinates for {user_input['destination']}")
        print(f"📍 Destination coordinates: {lat}, {lng}")
        
        # Process each day's activities
        itinerary = user_input.get('itinerary', {})
        for day_num, plan in itinerary.items():
            day_data = {
                "day": int(day_num.split('_')[1]) if '_' in day_num else int(day_num),
                "title": f"Day {day_num.split('_')[1] if '_' in day_num else day_num}",
                "transport": {
                    "type": "Auto-rickshaw",
                    "details": "Local transport",
                    "time": "09:00",
                    "cost": "₹200-300"
                },
                "accommodation": {
                    "name": user_input.get('accommodation', {}).get('recommendations', [{}])[0].get('name', 'Hotel to be booked'),
                    "checkIn": "14:00",
                    "checkOut": "11:00",
                    "price": "₹2000-3000/night",
                    "location": "City Center"
                },
                "activities": [],
                "food": [],
                "tips": plan.get('weather_considerations', "Stay hydrated and carry water. Wear comfortable walking shoes.")
            }
            
            # Process activities
            for activity in plan.get('activities', []):
                if "name" in activity:
                    activity_lat, activity_lng = get_lat_lng_from_place(activity["name"])
                    activity_data = {
                        "name": activity["name"],
                        "time": activity.get("duration", "2-3 hours"),
                        "indoor": activity.get("indoor", False),
                        "location": activity.get("location", ""),
                        "coordinates": {
                            "latitude": activity_lat,
                            "longitude": activity_lng
                        } if activity_lat and activity_lng else None,
                        "description": activity.get("description", ""),
                        "estimated_cost": activity.get("estimated_cost", 0)
                    }
                    day_data["activities"].append(activity_data)
            
            # Process food recommendations
            for food in plan.get('food', []):
                if "name" in food:
                    food_lat, food_lng = get_lat_lng_from_place(food["name"])
                    food_data = {
                        "name": food["name"],
                        "cuisine": food.get("cuisine", "Local"),
                        "mealType": "Lunch/Dinner",
                        "price": "₹₹",
                        "location": food.get("location", ""),
                        "coordinates": {
                            "latitude": food_lat,
                            "longitude": food_lng
                        } if food_lat and food_lng else None,
                        "description": food.get("description", ""),
                        "estimated_cost": food.get("estimated_cost", 0)
                    }
                    day_data["food"].append(food_data)
            
            full_itinerary["itineraryDays"].append(day_data)
        
        # Calculate total costs
        total_transport = 0
        total_accommodation = 0
        total_food = 0
        total_activities = 0
        
        for day in full_itinerary["itineraryDays"]:
            # Sum up activity costs
            for activity in day["activities"]:
                if isinstance(activity.get("estimated_cost"), (int, float)):
                    total_activities += activity["estimated_cost"]
            
            # Sum up food costs
            for food in day["food"]:
                if isinstance(food.get("estimated_cost"), (int, float)):
                    total_food += food["estimated_cost"]
        
        # Update cost breakdown
        full_itinerary["tripData"]["cost"].update({
            "transportation": {"inr": 2000},  # Estimated daily transport
            "accommodation": {"inr": 4000},   # 2 nights at ₹2000
            "food": {"inr": total_food},
            "activities": {"inr": total_activities},
            "miscellaneous": {"inr": 5000},   # Buffer
            "total": {"inr": user_input.get("budget", 0)}
        })
        
        # Save the final itinerary
        print("\n💾 Saving final full itinerary...")
        with open('final_full_itinerary.json', 'w', encoding='utf-8') as f:
            json.dump(full_itinerary, f, indent=2, ensure_ascii=False)
            
        # Generate map with coordinates
        print("\n🗺️ Generating map...")
        coordinates_data = {
            'accommodations': [],
            'restaurants': [],
            'attractions': []
        }
        
        for day in full_itinerary["itineraryDays"]:
            # Add accommodation coordinates
            if day["accommodation"].get("coordinates"):
                coordinates_data['accommodations'].append({
                    'name': day["accommodation"]["name"],
                    'latitude': day["accommodation"]["coordinates"]["latitude"],
                    'longitude': day["accommodation"]["coordinates"]["longitude"]
                })
            
            # Add activity coordinates
            for activity in day["activities"]:
                if activity.get("coordinates"):
                    coordinates_data['attractions'].append({
                        'name': activity["name"],
                        'latitude': activity["coordinates"]["latitude"],
                        'longitude': activity["coordinates"]["longitude"]
                    })
            
            # Add food coordinates
            for food in day["food"]:
                if food.get("coordinates"):
                    coordinates_data['restaurants'].append({
                        'name': food["name"],
                        'latitude': food["coordinates"]["latitude"],
                        'longitude': food["coordinates"]["longitude"]
                    })
        
        # Save coordinates data
        with open('coordinates.json', 'w', encoding='utf-8') as f:
            json.dump(coordinates_data, f, indent=2, ensure_ascii=False)
        
        # Generate map
        generate_map(coordinates_data)
        
        # Create chatbot interface
        create_chatbot_interface(user_input)
        
        print("\n✅ Itinerary generation complete!")
        print("✅ Final full itinerary saved to final_full_itinerary.json")
        print("🗺️ Map saved to travel_map.html")
        print("📍 Coordinates saved to coordinates.json")
        print("💬 Chatbot interface saved to chatbot.txt")
        
        # Create human readable itinerary
        create_human_readable_itinerary(user_input)
        print("📝 Human readable itinerary saved to itinerary.txt")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        print(f"Stack trace: {traceback.format_exc()}")
        return False

def create_chatbot_interface(user_input):
    try:
        chatbot_text = f"""🤖 Travel Assistant Chat

👋 Hello! I'm your travel assistant. Let me help you plan your trip to {user_input['destination']}.

📅 Trip Details:
- Duration: {user_input['days']} days
- Dates: {user_input['start_date']} to {user_input['end_date']}
- Budget: ₹{user_input['budget']}
- Travelers: {user_input['number_of_people']} people
- Purpose: {user_input.get('reason_of_visit', 'Leisure')}

🎯 Top Attractions:
{chr(10).join([f"- {p.get('name', '')} (Rating: {p.get('rating', 0)}/5)" for p in user_input.get('itinerary', {}).get('attractions', [])[:5]])}

🏨 Top Accommodation Recommendations:
{chr(10).join([f"- {h.get('name', '')} (Rating: {h.get('rating', 0)}/5, Price: ₹{h.get('price', 0)})" for h in user_input.get('itinerary', {}).get('accommodations', [])[:5]])}

🍽️ Top Restaurant Recommendations:
{chr(10).join([f"- {r.get('name', '')} (Rating: {r.get('rating', 0)}/5)" for r in user_input.get('itinerary', {}).get('restaurants', [])[:5]])}

❓ How can I help you further? You can ask me about:
- Weather conditions
- Transportation options
- Local customs and culture
- Specific attraction details
- Budget adjustments
- Or any other travel-related questions!

Just type your question below:
"""
        with open("chatbot.txt", "w", encoding="utf-8") as f:
            f.write(chatbot_text)
    except Exception as e:
        print(f"❌ Error creating chatbot interface: {str(e)}")

def generate_map(coordinates_data):
    try:
        import folium
        
        # Create a map centered on the first attraction
        center_lat = None
        center_lng = None
        for category in coordinates_data:
            if coordinates_data[category]:
                center_lat = coordinates_data[category][0]['latitude']
                center_lng = coordinates_data[category][0]['longitude']
                break
                
        if not center_lat or not center_lng:
            raise ValueError("No valid coordinates found for map center")
            
        m = folium.Map(location=[center_lat, center_lng], zoom_start=12)
        
        # Add markers for each category
        colors = {
            'accommodations': 'blue',
            'restaurants': 'red',
            'attractions': 'green'
        }
        
        for category, places in coordinates_data.items():
            for place in places:
                if not all(key in place for key in ['latitude', 'longitude', 'name']):
                    continue
                    
                popup_text = f"""
                <b>{place['name']}</b><br>
                Rating: {place.get('rating', 'N/A')}<br>
                {place.get('address', '')}
                """
                
                folium.Marker(
                    location=[place['latitude'], place['longitude']],
                    popup=folium.Popup(popup_text, max_width=300),
                    icon=folium.Icon(color=colors.get(category, 'gray'))
                ).add_to(m)
                
        # Save the map
        m.save('travel_map.html')
        
    except Exception as e:
        print(f"❌ Error generating map: {str(e)}")

def create_human_readable_itinerary(user_input):
    """Create a human-readable itinerary from the LLM output"""
    try:
        # Extract trip details
        destination = user_input.get('destination', 'Unknown Destination')
        days = user_input.get('days', 0)
        start_date = user_input.get('start_date', '')
        end_date = user_input.get('end_date', '')
        budget = user_input.get('budget', 0)
        reason = user_input.get('reason_of_visit', 'Tourism')
        interests = user_input.get('interests', [])
        
        # Create the itinerary text
        itinerary_text = f"""# {destination} Itinerary ({days} Days)
**Trip Dates:** {start_date} to {end_date}
**Budget:** ₹{budget}
**Reason:** {reason}
**Interests:** {', '.join(interests) if interests else 'Not specified'}

"""
        
        # Add daily activities
        itinerary = user_input.get('itinerary', {})
        for day_num, day_data in itinerary.items():
            date = day_data.get('date', '')
            weather = day_data.get('weather', '')
            activities = day_data.get('activities', [])
            
            itinerary_text += f"\n## Day {day_num.split('_')[1]}: {date}\n"
            if weather:
                itinerary_text += f"**Weather:** {weather}\n\n"
            
            itinerary_text += "### Activities:\n"
            for activity in activities:
                name = activity.get('name', '')
                description = activity.get('description', '')
                time = activity.get('time', '')
                indoor = activity.get('indoor', False)
                
                itinerary_text += f"- **{name}**\n"
                if description:
                    itinerary_text += f"  {description}\n"
                if time:
                    itinerary_text += f"  Duration: {time}\n"
                itinerary_text += f"  Indoor/Outdoor: {'Indoor' if indoor else 'Outdoor'}\n\n"
        
        # Add food recommendations
        food_recs = user_input.get('food_recommendations', {})
        if food_recs:
            itinerary_text += "\n## Food Recommendations\n"
            for meal_type, places in food_recs.items():
                if places:
                    itinerary_text += f"\n### {meal_type.title()}:\n"
                    for place in places:
                        itinerary_text += f"- {place}\n"
        
        # Add accommodation recommendations
        acc_recs = user_input.get('accommodation_recommendations', {})
        if acc_recs:
            itinerary_text += "\n## Accommodation Recommendations\n"
            for category, hotels in acc_recs.items():
                if isinstance(hotels, list) and hotels:
                    itinerary_text += f"\n### {category.replace('_', ' ').title()}:\n"
                    for hotel in hotels:
                        itinerary_text += f"- {hotel}\n"
        
        # Add weather suggestions and notes
        weather_suggestion = user_input.get('weather_suggestion', '')
        notes = user_input.get('notes', '')
        
        if weather_suggestion:
            itinerary_text += f"\n## Weather Considerations\n{weather_suggestion}\n"
        if notes:
            itinerary_text += f"\n## Important Notes\n{notes}\n"
        
        # Write to file
        with open('itinerary.txt', 'w', encoding='utf-8') as f:
            f.write(itinerary_text)
            
        return True
        
    except Exception as e:
        print(f"Error creating human readable itinerary: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False

def get_place_photos(place_name):
    """Get photos for a place using Google Places API"""
    try:
        # Initialize Google Places API client
        places_client = googlemaps.Client(key=os.getenv('GOOGLE_MAPS_API_KEY'))
        
        # Search for the place
        places_result = places_client.places(place_name)
        
        if places_result['results']:
            place_id = places_result['results'][0]['place_id']
            
            # Get place details including photo
            place_details = places_client.place(place_id, fields=['photo'])
            
            photos = []
            if 'result' in place_details and 'photos' in place_details['result']:
                for photo in place_details['result']['photos'][:3]:  # Get up to 3 photos
                    photo_reference = photo['photo_reference']
                    photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference={photo_reference}&key={os.getenv('GOOGLE_MAPS_API_KEY')}"
                    photos.append(photo_url)
            
            return photos
    except Exception as e:
        print(f"Error getting photos for {place_name}: {str(e)}")
    
    return []

if __name__ == "__main__":
    # Get user input
    user_prompt = input("Enter your travel request: ")
    
    # Parse the input
    parsed_input = parse_user_input(user_prompt)
    
    if parsed_input:
        # Cross question for any missing fields
        complete_input = cross_question_missing_fields(parsed_input)
        
        try:
            # Generate the itinerary
            success = generate_full_itinerary(complete_input)
            
            if not success:
                print("\n❌ Failed to generate itinerary. Please try again.")
            else:
                # Save the complete itinerary
                with open('itinerary.json', 'w', encoding='utf-8') as f:
                    json.dump(complete_input, f, indent=2, ensure_ascii=False)
                print("\n✨ Successfully generated your travel itinerary!")
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
    else:
        print("\n❌ Failed to parse your request. Please try again with more details.")
