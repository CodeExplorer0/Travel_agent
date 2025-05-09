from datetime import datetime, timedelta

def group_days_by_city(itinerary_days):
    grouped = []
    if not itinerary_days:
        return grouped

    current_city = itinerary_days[0]["city"]
    start_date = itinerary_days[0]["date"]
    prev_date = start_date

    for day in itinerary_days[1:]:
        if day["city"] != current_city:
            grouped.append({
                "city": current_city,
                "checkin": start_date,
                "checkout": prev_date
            })
            current_city = day["city"]
            start_date = day["date"]
        prev_date = day["date"]

    # Append the last segment
    grouped.append({
        "city": current_city,
        "checkin": start_date,
        "checkout": (datetime.strptime(prev_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
    })
    return grouped

def allocate_budget(total_budget, days, hotel_pct=0.5, food_pct=0.3, sights_pct=0.2):
    hotel_budget = total_budget * hotel_pct
    food_budget = total_budget * food_pct
    sights_budget = total_budget * sights_pct
    return {
        "hotel_per_day": hotel_budget / days,
        "food_per_day": food_budget / days,
        "sights_per_day": sights_budget / days
    }

def validate_total_spend(total_budget, hotel_sum, food_sum, sights_sum):
    total = hotel_sum + food_sum + sights_sum
    return total <= total_budget

def generate_itinerary_text(itinerary):
    """
    Generate a human-readable itinerary from the detailed_daily_plan.
    """
    text = f"# {itinerary['destination']} Itinerary ({itinerary['days']} Days)\n"
    text += f"**Trip Dates:** {itinerary['start_date']} to {itinerary['end_date']}\n"
    text += f"**Budget:** ₹{itinerary['budget']:,}\n"
    text += f"**Reason:** {itinerary.get('reason_of_visit','')}\n"
    text += f"**Interests:** {', '.join(itinerary.get('interests', []))}\n\n"

    if "detailed_daily_plan" not in itinerary:
        text += "No detailed daily plan available.\n"
        return text

    for day in itinerary["detailed_daily_plan"]:
        text += f"## Day {day['day']}: {day['date']} ({day['weather']})\n"
        text += f"**City:** {day['city']}\n"
        text += f"**Clothing Suggestion:** {day.get('clothing_suggestion', 'Standard casual wear')}\n\n"

        text += "### Activities:\n"
        for time, activity in day.get("activities", {}).items():
            text += f"- **{time.capitalize()}:** {activity}\n"

        if day.get("food_recommendations"):
            text += "\n### Food Recommendations:\n"
            for food in day["food_recommendations"]:
                name = food.get("name", "Unknown")
                typ = food.get("type", "")
                rating = food.get("rating", "")
                text += f"- {name}"
                if typ:
                    text += f" ({typ})"
                if rating:
                    text += f" ⭐{rating}"
                text += "\n"

        if day.get("estimated_costs"):
            total_cost = sum(day["estimated_costs"].values())
            text += f"\n**Estimated Daily Cost:** ₹{int(total_cost):,}\n"

        text += "\n"

    text += f"---\n**Total Estimated Spend:** ₹{int(itinerary.get('total_spent',0)):,}\n"
    text += f"**Hotel Total:** ₹{int(itinerary.get('hotel_total',0)):,} | **Food Total:** ₹{int(itinerary.get('food_total',0)):,} | **Sightseeing Total:** ₹{int(itinerary.get('sights_total',0)):,}\n"
    return text
