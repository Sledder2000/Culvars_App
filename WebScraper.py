from tabnanny import check
from math import radians, sin, cos, sqrt, atan2
from bs4 import BeautifulSoup
import requests
import os
import json
from opencage.geocoder import OpenCageGeocode
from geopy.geocoders import Nominatim



# Initialize the OpenCageGeocode instance with your API key
geocoder = Nominatim(user_agent="culvers_geocoder")
def scrapeLocations():
    url = "https://www.culvers.com/stories/signature-stories/culvers-locations-by-state"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    locations = []
    processed_cities = {(loc['city'], loc['state']) for loc in locations}

    for state_section in soup.find_all('div', class_='PageStoriesDetail_contentCopy__BRPDW'):
        for state_name_tag in state_section.find_all('h2'):
            state_name = state_name_tag.text.strip()
            
            # Find all locations under the state
            location_list = state_name_tag.find_next('ul')  # Get the <ul> following the <h2>
            if location_list:
                for location in location_list.find_all('li'):  # Iterate through <li> tags in the <ul>
                    location_text = location.text.strip()
                    city_name = location_text[location_text.find("of")+3:location_text.find(",")]  # Extract city name assuming it's before the first comma
                    location_name = location_text[location_text.find("-")-3:]  # Extract location name assuming it's after the first comma
                   
                    if (city_name, state_name) in processed_cities:
                        continue

                    query = f"{city_name}, {state_name}"
                    try:
                        location = geocoder.geocode(query)
                        if location:
                            latitude = location.latitude
                            longitude = location.longitude
                        else:
                            latitude = 0.0
                            longitude = 0.0
                        
                        locations.append({
                            'state': state_name,
                            'city': city_name,
                            'name': location_name,
                            'latitude': latitude,
                            'longitude': longitude
                        })
                        print(f"Added location: {location_name} in {city_name}, {state_name} at ({latitude}, {longitude})")
                    except Exception as e:
                        print(f"Error geocoding {query}: {e}")
                        continue

    with open('locations.json', 'w') as file:
        json.dump(locations, file, indent=4)
    print("Locations saved to locations.json")

    return locations


def findAddress(loc):
    city = loc['city'].lower().replace(' ', '-')
    name = loc['name']
    name = name[0:3] + name[5:]
    name = name.lower().replace(' ', '-')

    url = f"https://www.culvers.com/restaurants/{city}"
    try:
        response = requests.head(url)
        if response.status_code == 200:  # URL is valid and reachable
            return url
    except requests.RequestException as e:
        print(f"Error checking URL: {url}, {e}")

    for i in range(len(name)):
        url = f"https://www.culvers.com/restaurants/{city}-{name[:len(name)-i]}"
        try:
            response = requests.head(url)
            if response.status_code == 200:  # URL is valid and reachable
                return url
        except requests.RequestException as e:
            print(f"Error checking URL: {url}, {e}")
            continue

    return None

def scrapeFlavors(url):
    url = url + "?tab=current"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    flavors = []
    # Locate all containers for flavors
    flavor_containers = soup.find_all('div', class_='RestaurantCalendarPanel_containerItem__ZEQoq')

    for container in flavor_containers:
        # Extract the day
        day_tag = container.find('h3', class_='RestaurantCalendarPanel_containerItemHeading__7lty1')
        day = day_tag.text.strip() if day_tag else "Unknown Day"

        # Extract the flavor name
        flavor_name_tag = container.find('a', class_='RestaurantCalendarPanel_containerItemContentFlavorLink__Kvd0e')
        flavor_name = flavor_name_tag.text.strip() if flavor_name_tag else "Unknown Flavor"

        
        flavors.append({
            'day': day,
            'name': flavor_name
        })

    return flavors


def haversine(lat1, lon1, lat2, lon2):
    """
    Calculate the distance between two points on the Earth using the Haversine formula.
    """
    R = 6371  # Radius of the Earth in kilometers

    # Convert latitude and longitude from degrees to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    # Calculate differences
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    # Apply Haversine formula
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    distance = R * c

    return distance


def findNearbyLocations(locations, user_lat, user_lon, max_distance):
    """
    Find all locations within a certain distance from the user's coordinates.
    """
    nearby_locations = []
    for loc in locations:
        distance = haversine(user_lat, user_lon, loc['latitude'], loc['longitude'])
        if distance <= max_distance:
            nearby_locations.append({
                'state': loc['state'],
                'city': loc['city'],
                'name': loc['name'],
                'distance': distance
            })

    return nearby_locations
def loadLocations():
    """
    Load locations from a file if it exists.
    """
    if os.path.exists('locations.json'):
        with open('locations.json', 'r') as file:
            locations = json.load(file)
        print("Loaded locations from locations.json")
        return locations
    else:
        print("No saved locations found. Please add locations first.")
        return []

def main():
    # Load locations from file or scrape them
    locations = loadLocations()

    # Ask the user for input
    user_state = input("Enter the state to search for a Culver's location: ").strip().lower()
    user_city = input("Enter the city to search for a Culver's location: ").strip().lower()
    max_distance = float(input("Enter the maximum distance (in kilometers): ").strip())

    for loc in locations:
        if loc['state'].lower() == user_state and loc['city'].lower() == user_city:
            user_lat = loc['latitude']
            user_lon = loc['longitude']
            break
    # Search for the location
    matching_locations = findNearbyLocations(locations, user_lat, user_lon, max_distance)
    if matching_locations:
        for matching_location in matching_locations:
            print(f"Found Culver's in {matching_location['city']}, {matching_location['state']} ({matching_location['distance']:.2f} km away).")
            address = findAddress(matching_location)
            if address:
                print(f"Address: {address}")
                flavors = scrapeFlavors(address)
                print("Flavors of the Day:")
                for flavor in flavors:
                    print(f"{flavor['day']}: {flavor['name']}")
            else:
                print("Could not find a valid address for the location.")
    else:
        print("No Culver's locations found within the specified distance.")
        
if __name__ == "__main__":
    main()
