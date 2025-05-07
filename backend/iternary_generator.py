from datetime import datetime, timedelta

def group_days_by_city(itinerary_days):
    grouped = []
    if not itinerary_days:
        return grouped
    current_city = itinerary_days[0]["city"]
    start_date = itinerary_days[0]["date"]
    prev_date = start_date
    for i, day in enumerate(itinerary_days[1:], 1):
        if day["city"] != current_city:
            grouped.append({
                "city": current_city,
                "checkin": start_date,
                "checkout": prev_date
            })
            current_city = day["city"]
            start_date = day["date"]
        prev_date = day["date"]
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
