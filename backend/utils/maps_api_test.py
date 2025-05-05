from maps_api import get_directions, get_google_maps_url_for_directions, plot_route_on_map, plot_nearby_places_on_map
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')

def test_get_directions():
    origin = "Kolkata"
    destination = "Bhubaneshwar"
    
    # Get directions
    directions = get_directions(origin, destination)
    
    if isinstance(directions, dict) and "error" in directions:
        print("Error fetching directions:", directions["error"])
    else:
        route = directions[0]['legs'][0]
        print("Route from", route['start_address'], "to", route['end_address'])
        for step in route['steps']:
            print("-", step['html_instructions'].replace('<b>', '').replace('</b>', ''))
        
        # Generate Google Maps URL for the route
        map_url = get_google_maps_url_for_directions(origin, destination)
        print(f"\nYou can view the route here: {map_url}")

def test_plot_route_on_map():
    origin = "Kolkata"
    destination = "Bhubaneshwar"
    
    # Plot route on map
    route_map = plot_route_on_map(origin, destination)
    
    if isinstance(route_map, dict) and "error" in route_map:
        print("Error plotting map:", route_map["error"])
    else:
        # Save map to an HTML file
        route_map.save("route_map.html")
        print("Map has been saved as 'route_map.html'. Open it in a browser to view the route.")

def test_plot_nearby_places_on_map():
    location_name = "Kolkata"
    place_type = "restaurant"  # You can change this to other types like 'hospital', 'park', etc.
    
    # Plot nearby places on map
    nearby_places_map = plot_nearby_places_on_map(location_name, place_type)
    
    if isinstance(nearby_places_map, dict) and "error" in nearby_places_map:
        print("Error plotting places:", nearby_places_map["error"])
    else:
        # Save map to an HTML file
        nearby_places_map.save("nearby_places_map.html")
        print("Map with nearby places has been saved as 'nearby_places_map.html'. Open it in a browser to view the places.")

# Run the tests
if __name__ == "__main__":
    print("Testing Directions API:")
    test_get_directions()
    
    print("\nTesting Route Map Plotting:")
    test_plot_route_on_map()
    
    print("\nTesting Nearby Places Map Plotting:")
    test_plot_nearby_places_on_map()
