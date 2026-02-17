#!/usr/bin/env python3
"""
SkiPool Ride Simulation Setup Script

Sets up the iOS Simulator for realistic ride testing by:
1. Wiping the database
2. Seeding test data (passengers for Ride Now, driver+passenger for Scheduled)
3. Setting Simulator GPS location via xcrun simctl
4. Simulating driver movement by pushing location updates via API

Usage:
    # Ride Now simulation
    python sim_ride.py --mode now --resort solitude

    # Scheduled ride simulation (driver perspective)
    python sim_ride.py --mode scheduled --resort solitude
    
    # Scheduled ride simulation (passenger perspective)
    python sim_ride.py --mode scheduled --resort solitude --perspective passenger
    
    # Custom update interval
    python sim_ride.py --mode now --resort solitude --interval 5
"""

import requests
import argparse
import sys
import subprocess
import os
import time
import xml.etree.ElementTree as ET
from datetime import date
from typing import Dict, Optional, Tuple, List

# Colors for terminal output
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
CYAN = '\033[0;36m'
NC = '\033[0m'  # No Color

# Resort configurations
# Using simpler addresses that Nominatim can reliably geocode
RESORTS = {
    "solitude": {
        "name": "Solitude",
        "driver_origin": "Sugar House, Salt Lake City",
        "driver_coords": (40.7178, -111.8689),  # Matches actual geocoded location
        "passenger_pickup": "Big Cottonwood Canyon Park and Ride, Utah",
        "passenger_coords": (40.6194, -111.7870),  # On the route to Solitude
        "gpx_file": "gpx/route_to_solitude.gpx",
        "hub_gpx": "gpx/route_to_hub_bcc_pr.gpx"
    },
    "park_city": {
        "name": "Park City Mountain",
        "driver_origin": "Park City",
        "driver_coords": (40.6460, -111.4980),
        "passenger_pickup": "Park City",
        "passenger_coords": (40.6460, -111.4980),
        "gpx_file": "gpx/route_to_park_city.gpx",
        "hub_gpx": None  # No hub route for Park City yet
    }
}


def print_header(msg: str):
    print(f"\n{BLUE}{'='*60}{NC}")
    print(f"{BLUE}{msg}{NC}")
    print(f"{BLUE}{'='*60}{NC}")


def print_success(msg: str):
    print(f"{GREEN}✓ {msg}{NC}")


def print_fail(msg: str):
    print(f"{RED}✗ {msg}{NC}")


def print_info(msg: str):
    print(f"{CYAN}→ {msg}{NC}")


def print_warning(msg: str):
    print(f"{YELLOW}⚠ {msg}{NC}")


def parse_gpx_waypoints(gpx_file: str) -> List[Dict]:
    """Parse lat/lon pairs from a GPX track file
    
    Returns list of waypoints with lat, lng, and name.
    """
    try:
        tree = ET.parse(gpx_file)
        root = tree.getroot()
        ns = {"gpx": "http://www.topografix.com/GPX/1/1"}
        waypoints = []
        
        for trkpt in root.findall(".//gpx:trkpt", ns):
            lat = float(trkpt.get("lat"))
            lon = float(trkpt.get("lon"))
            name_el = trkpt.find("gpx:name", ns)
            name = name_el.text if name_el is not None else ""
            waypoints.append({"lat": lat, "lng": lon, "name": name})
        
        return waypoints
    except Exception as e:
        print_fail(f"Failed to parse GPX file {gpx_file}: {e}")
        return []


def wipe_database(base_url: str) -> bool:
    """Delete all trips and ride requests"""
    print_info("Wiping database...")
    
    try:
        # First delete all ride requests
        resp = requests.get(f"{base_url}/ride-requests/active")
        if resp.status_code == 200:
            ride_requests = resp.json()
            for ride_request in ride_requests:
                requests.delete(f"{base_url}/ride-requests/{ride_request['id']}")
        
        # Then delete all trips
        resp = requests.get(f"{base_url}/trips/active")
        if resp.status_code == 200:
            trips = resp.json()
            for trip in trips:
                requests.delete(f"{base_url}/trips/{trip['id']}")
        
        print_success(f"Database wiped")
        return True
    except Exception as e:
        print_fail(f"Failed to wipe database: {e}")
        return False


def wait_for_driver_trip(base_url: str, expected_name: str, resort: str, timeout: int = 120) -> Optional[Dict]:
    """Poll API until a driver trip with the expected name is detected
    
    Args:
        base_url: API base URL
        expected_name: Driver name to look for
        resort: Resort name to match
        timeout: Maximum seconds to wait
        
    Returns:
        Trip dict if found, None if timeout
    """
    print_info(f"Waiting for driver trip (name: '{expected_name}', resort: {resort})...")
    print_info(f"Timeout: {timeout} seconds")
    print_info("Checking every 2 seconds...\n")
    
    start = time.time()
    dots = 0
    while time.time() - start < timeout:
        try:
            resp = requests.get(f"{base_url}/trips/active")
            if resp.status_code == 200:
                trips = resp.json()
                # region agent log
                import json
                with open('/Users/ashley/skipool/.cursor/debug.log', 'a') as f:
                    f.write(json.dumps({"id":f"log_{int(time.time()*1000)}","timestamp":int(time.time()*1000),"location":"sim_ride.py:162","message":"Polling trips","data":{"expected_name":expected_name,"expected_resort":resort,"found_trips":[{"driver_name":t.get('driver_name'),"resort":t.get('resort'),"id":t.get('id'),"is_realtime":t.get('is_realtime')} for t in trips]},"runId":"post-fix","hypothesisId":"H1-H2-H3-H4-H10"}) + '\n')
                # endregion
                for trip in trips:
                    if trip.get('driver_name') == expected_name and trip.get('resort') == resort:
                        print_success(f"Driver detected! Trip ID: {trip['id']}")
                        return trip
        except Exception as e:
            print_warning(f"Error polling for driver: {e}")
        
        # Print progress dots
        dots = (dots + 1) % 4
        print(f"\rWaiting{'.' * dots}   ", end='', flush=True)
        time.sleep(2)
    
    print()  # New line after dots
    print_fail(f"Timeout: No driver trip detected after {timeout}s")
    return None


def wait_for_match_accepted(base_url: str, trip_id: int, expected_passenger_id: int, timeout: int = 120) -> bool:
    """Poll API until driver accepts a passenger match in the UI.
    
    Uses /ride-requests/{id}/matched-driver which returns {"matched": true/false}
    regardless of ride request status. The /ride-requests/active endpoint only
    returns "pending" requests, so once matched the request disappears from that list.
    
    Args:
        base_url: API base URL
        trip_id: Trip ID to monitor
        expected_passenger_id: The passenger ID we expect to be matched
        timeout: Maximum seconds to wait
        
    Returns:
        True if match accepted, False if timeout
    """
    print_info(f"Waiting for match to be accepted in UI (Trip ID: {trip_id})...")
    print_info(f"Expected Passenger ID: {expected_passenger_id}")
    print_info(f"Timeout: {timeout} seconds")
    print_info("Checking every 2 seconds...\n")
    
    start = time.time()
    dots = 0
    while time.time() - start < timeout:
        try:
            # Use matched-driver endpoint which works regardless of status
            resp = requests.get(f"{base_url}/ride-requests/{expected_passenger_id}/matched-driver")
            if resp.status_code == 200:
                data = resp.json()
                is_matched = data.get('matched', False)
                # region agent log
                import json
                with open('/Users/ashley/skipool/.cursor/debug.log', 'a') as f:
                    f.write(json.dumps({"id":f"log_{int(time.time()*1000)}","timestamp":int(time.time()*1000),"location":"sim_ride.py:209","message":"Polling for match","data":{"expected_trip_id":trip_id,"expected_passenger_id":expected_passenger_id,"matched":is_matched,"response":data},"runId":"post-fix-v2","hypothesisId":"H11"}) + '\n')
                # endregion
                if is_matched:
                    print_success(f"Match accepted! Passenger {expected_passenger_id} matched to trip {trip_id}")
                    return True
        except Exception as e:
            print_warning(f"Error polling for match: {e}")
        
        # Print progress dots
        dots = (dots + 1) % 4
        print(f"\rWaiting{'.' * dots}   ", end='', flush=True)
        time.sleep(2)
    
    print()  # New line after dots
    print_fail(f"Timeout: Match not accepted after {timeout}s")
    return False


def wait_for_en_route(base_url: str, trip_id: int, timeout: int = 120) -> bool:
    """Poll API until driver starts en-route (driver_en_route_at is set)
    
    Args:
        base_url: API base URL
        trip_id: Trip ID to monitor
        timeout: Maximum seconds to wait
        
    Returns:
        True if en-route detected, False if timeout
    """
    print_info(f"Waiting for driver to start en-route (Trip ID: {trip_id})...")
    print_info(f"Timeout: {timeout} seconds")
    print_info("Checking every 2 seconds...\n")
    
    start = time.time()
    dots = 0
    while time.time() - start < timeout:
        try:
            resp = requests.get(f"{base_url}/trips/{trip_id}")
            if resp.status_code == 200:
                trip = resp.json()
                if trip.get('driver_en_route_at') is not None:
                    print_success("Driver started en-route!")
                    return True
        except Exception as e:
            print_warning(f"Error polling for en-route status: {e}")
        
        # Print progress dots
        dots = (dots + 1) % 4
        print(f"\rWaiting{'.' * dots}   ", end='', flush=True)
        time.sleep(2)
    
    print()  # New line after dots
    print_fail(f"Timeout: Driver did not start en-route after {timeout}s")
    return False


def set_simulator_location(lat: float, lng: float) -> bool:
    """Set iOS Simulator location using xcrun simctl"""
    try:
        cmd = ["xcrun", "simctl", "location", "booted", "set", f"{lat},{lng}"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print_success(f"Simulator location set to ({lat}, {lng})")
            return True
        else:
            print_warning(f"Failed to set Simulator location: {result.stderr}")
            print_info("Make sure iOS Simulator is running and booted")
            return False
    except Exception as e:
        print_warning(f"Could not set Simulator location: {e}")
        print_info("You can manually set location in Simulator: Features > Location > Custom Location")
        return False


def simulate_driver_route(base_url: str, trip_id: int, gpx_file: str, passenger_coords: Tuple[float, float], interval: int = 10):
    """Push driver location updates from GPX waypoints via API
    
    Args:
        base_url: API base URL
        trip_id: Driver's trip ID
        gpx_file: Path to GPX file with route waypoints
        passenger_coords: (lat, lng) tuple of passenger pickup location
        interval: Seconds between waypoint updates (default 10)
    """
    print_header("Simulating Driver Route")
    
    waypoints = parse_gpx_waypoints(gpx_file)
    if not waypoints:
        print_fail("No waypoints found in GPX file")
        return False
    
    print_info(f"Starting route simulation with {len(waypoints)} waypoints")
    print_info(f"Update interval: {interval} seconds")
    print_info("Watch the Expo app to see the driver moving on the map!\n")
    
    passenger_lat, passenger_lng = passenger_coords
    
    for i, wp in enumerate(waypoints, 1):
        # region agent log
        import json, time
        with open('/Users/ashley/skipool/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"id":f"log_{int(time.time()*1000)}","timestamp":int(time.time()*1000),"location":"sim_ride.py:258","message":"Waypoint iteration","data":{"waypoint_num":i,"total":len(waypoints),"lat":wp["lat"],"lng":wp["lng"],"name":wp.get("name")},"runId":"post-fix","hypothesisId":"H6-H7"}) + '\n')
        # endregion
        # Update location via API
        try:
            resp = requests.put(
                f"{base_url}/trips/{trip_id}/location",
                json={"current_lat": wp["lat"], "current_lng": wp["lng"]}
            )
            if resp.status_code == 200:
                # Calculate distance to passenger
                from math import radians, sin, cos, sqrt, atan2
                R = 6371  # Earth radius in km
                dlat = radians(passenger_lat - wp["lat"])
                dlon = radians(passenger_lng - wp["lng"])
                a = sin(dlat/2)**2 + cos(radians(wp["lat"])) * cos(radians(passenger_lat)) * sin(dlon/2)**2
                distance_km = 2 * R * atan2(sqrt(a), sqrt(1-a))
                
                waypoint_name = wp["name"] or f"Waypoint {i}"
                print_success(f"[{i}/{len(waypoints)}] {waypoint_name} - {distance_km:.2f}km to passenger")
                
                # region agent log
                with open('/Users/ashley/skipool/.cursor/debug.log', 'a') as f:
                    f.write(json.dumps({"id":f"log_{int(time.time()*1000)}","timestamp":int(time.time()*1000),"location":"sim_ride.py:278","message":"Setting simulator location","data":{"lat":wp["lat"],"lng":wp["lng"],"waypoint":i},"runId":"post-fix","hypothesisId":"H5-H6"}) + '\n')
                # endregion
                # Update Simulator location so map centers correctly
                set_simulator_location(wp["lat"], wp["lng"])
                
                # Check if close to passenger (within 500m = 0.5 km)
                # This threshold matches the API's near_pickup flag in GET /trips/{id}/matched-passenger
                if distance_km < 0.5:
                    print_header("Driver Approaching Passenger!")
                    print_success("Driver is within 500m of passenger pickup")
                    print_info("The app should show 'Confirm pickup' prompt (near_pickup: true); it stays active until you confirm, then complete the trip.")
                    break
            else:
                print_warning(f"Failed to update location: {resp.status_code}")
        except Exception as e:
            print_warning(f"Error updating location: {e}")
        
        # Wait before next waypoint (except on last one)
        if i < len(waypoints):
            time.sleep(interval)
    
    print_success("\nRoute simulation complete!")
    return True


def start_gpx_route(gpx_file: str) -> bool:
    """Provide instructions for GPX route playback on iOS Simulator
    
    Note: xcrun simctl does not support GPX files directly.
    They must be loaded through Xcode's Debug menu.
    """
    if not os.path.exists(gpx_file):
        print_warning(f"GPX file not found: {gpx_file}")
        return False
    
    abs_path = os.path.abspath(gpx_file)
    print_info(f"GPX file ready: {abs_path}")
    print_info("To start the route:")
    print_info(f"  1. Open Xcode with your project")
    print_info(f"  2. Run app on iOS Simulator")
    print_info(f"  3. Xcode menu: Debug > Simulate Location > Add GPX File...")
    print_info(f"  4. Select: {abs_path}")
    print_info(f"  5. Or add to project and select from Debug menu")
    return True


def sim_ride_now(base_url: str, resort_key: str, driver_name: str = "Sim Driver", interval: int = 10):
    """Simulate Ride Now flow - creates passenger, waits for user to post driver trip, then simulates route"""
    # region agent log
    import json, time
    with open('/Users/ashley/skipool/.cursor/debug.log', 'a') as f:
        f.write(json.dumps({"id":f"log_{int(time.time()*1000)}","timestamp":int(time.time()*1000),"location":"sim_ride.py:320","message":"sim_ride_now called","data":{"driver_name":driver_name,"resort_key":resort_key,"interval":interval},"runId":"post-fix","hypothesisId":"H1"}) + '\n')
    # endregion
    print_header(f"Ride Now Simulation: {RESORTS[resort_key]['name']}")
    
    resort = RESORTS[resort_key]
    
    # Wipe DB
    if not wipe_database(base_url):
        sys.exit(1)
    
    # Create passenger
    print_info("Creating passenger ride request...")
    passenger_data = {
        "passenger_name": "Sim Passenger",
        "resort": resort["name"],
        "departure_time": "Now",
        "pickup_text": resort["passenger_pickup"],
        "lat": resort["passenger_coords"][0],
        "lng": resort["passenger_coords"][1],
        "seats_needed": 1
    }
    
    try:
        resp = requests.post(f"{base_url}/ride-requests/", json=passenger_data)
        if resp.status_code != 200:
            print_fail(f"Failed to create passenger: {resp.status_code} - {resp.text}")
            sys.exit(1)
        
        passenger = resp.json()
        passenger_id = passenger['id']
        passenger_lat = passenger.get('pickup_lat')
        passenger_lng = passenger.get('pickup_lng')
        print_success(f"Passenger created (ID: {passenger_id})")
        print_info(f"  Name: {passenger_data['passenger_name']}")
        print_info(f"  Pickup: {resort['passenger_pickup']}")
        print_info(f"  Resort: {resort['name']}")
        print_info(f"  Coords: ({passenger_lat:.4f}, {passenger_lng:.4f})")
    except Exception as e:
        print_fail(f"Error creating passenger: {e}")
        sys.exit(1)
    
    # Print instructions for user
    print_header("Passenger Ready - Waiting for Driver")
    print(f"{GREEN}Next Steps:{NC}")
    print(f"{GREEN}1. Open the Expo app on iOS Simulator{NC}")
    print(f"{GREEN}2. Select 'Ride Now' and 'Driver'{NC}")
    print(f"{GREEN}3. Post a trip with name: '{driver_name}'{NC}")
    print(f"{GREEN}4. Destination: {resort['name']}{NC}")
    print(f"{GREEN}5. The script will detect your trip and wait for you to match{NC}\n")
    
    # Wait for driver trip to be posted
    driver = wait_for_driver_trip(base_url, driver_name, resort["name"], timeout=120)
    if not driver:
        print_fail("No driver trip detected - exiting")
        sys.exit(1)
    
    trip_id = driver['id']
    
    # WORKAROUND: Mobile app may not set is_realtime=true for Ride Now trips
    # This causes match acceptance to fail. Force it to true.
    if not driver.get('is_realtime'):
        print_warning("Trip is_realtime=false, fixing...")
        try:
            resp = requests.patch(f"{base_url}/trips/{trip_id}", json={"is_realtime": True})
            if resp.status_code == 200:
                print_success("Fixed is_realtime flag")
            else:
                print_warning(f"Could not fix is_realtime: {resp.status_code}")
        except Exception as e:
            print_warning(f"Error fixing is_realtime: {e}")
    
    # Wait for user to manually match in UI
    print_header("Driver Detected - Waiting for Manual Match")
    print(f"{GREEN}Next Steps:{NC}")
    print(f"{GREEN}1. You should see the passenger icon on the map in the Expo app{NC}")
    print(f"{GREEN}2. Tap the passenger to view details{NC}")
    print(f"{GREEN}3. Accept the match in the UI{NC}")
    print(f"{GREEN}4. The script will detect the match and start the route simulation{NC}\n")
    
    if not wait_for_match_accepted(base_url, trip_id, passenger_id, timeout=120):
        print_fail("Match not accepted - exiting")
        sys.exit(1)
    
    # Print route simulation notice
    print_header("Starting Automated Route Simulation")
    print(f"{GREEN}Watch the Expo app:{NC}")
    print(f"{GREEN}• Driver marker will move along the route automatically{NC}")
    print(f"{GREEN}• Location updates every {interval} seconds{NC}")
    print(f"{GREEN}• Distance to passenger printed at each waypoint{NC}\n")
    print_info("Press Ctrl+C to stop the simulation\n")
    
    time.sleep(2)  # Give user time to see the app
    
    # region agent log
    import json, time as time_module
    with open('/Users/ashley/skipool/.cursor/debug.log', 'a') as f:
        f.write(json.dumps({"id":f"log_{int(time_module.time()*1000)}","timestamp":int(time_module.time()*1000),"location":"sim_ride.py:423","message":"Before route simulation","data":{"trip_id":trip_id,"driver_start_lat":driver.get('start_lat'),"driver_start_lng":driver.get('start_lng'),"driver_current_lat":driver.get('current_lat'),"driver_current_lng":driver.get('current_lng')},"runId":"post-fix","hypothesisId":"H5-H6"}) + '\n')
    # endregion
    
    # Start route simulation
    simulate_driver_route(base_url, trip_id, resort["gpx_file"], (passenger_lat, passenger_lng), interval)


def sim_scheduled(base_url: str, resort_key: str, perspective: str = "driver", interval: int = 10):
    """Simulate Scheduled ride flow - seeds driver+passenger, confirms match"""
    print_header(f"Scheduled Ride Simulation: {RESORTS[resort_key]['name']} ({perspective.title()} Perspective)")
    
    resort = RESORTS[resort_key]
    today = str(date.today())
    
    # Wipe DB
    if not wipe_database(base_url):
        sys.exit(1)
    
    # Create driver trip
    print_info("Creating driver trip...")
    driver_data = {
        "driver_name": "Sim Driver",
        "resort": resort["name"],
        "departure_time": "7:00 AM",
        "start_location_text": resort["driver_origin"],
        "available_seats": 3,
        "is_realtime": False,
        "trip_date": today
    }
    
    try:
        resp = requests.post(f"{base_url}/trips/", json=driver_data)
        if resp.status_code != 200:
            print_fail(f"Failed to create driver: {resp.status_code} - {resp.text}")
            sys.exit(1)
        
        driver = resp.json()
        trip_id = driver['id']
        print_success(f"Driver created (ID: {trip_id})")
    except Exception as e:
        print_fail(f"Error creating driver: {e}")
        sys.exit(1)
    
    # Create passenger request
    print_info("Creating passenger ride request...")
    passenger_data = {
        "passenger_name": "Sim Passenger",
        "resort": resort["name"],
        "departure_time": "7:15 AM",
        "pickup_text": resort["passenger_pickup"],
        "lat": resort["passenger_coords"][0],
        "lng": resort["passenger_coords"][1],
        "seats_needed": 1,
        "request_date": today
    }
    
    try:
        resp = requests.post(f"{base_url}/ride-requests/", json=passenger_data)
        if resp.status_code != 200:
            print_fail(f"Failed to create passenger: {resp.status_code} - {resp.text}")
            sys.exit(1)
        
        passenger = resp.json()
        request_id = passenger['id']
        print_success(f"Passenger created (ID: {request_id})")
    except Exception as e:
        print_fail(f"Error creating passenger: {e}")
        sys.exit(1)
    
    # Find match
    print_info("Finding scheduled match...")
    try:
        resp = requests.get(f"{base_url}/match-scheduled/", params={
            "resort": resort["name"],
            "target_date": today
        })
        if resp.status_code != 200:
            print_fail(f"Failed to find match: {resp.status_code}")
            sys.exit(1)
        
        matches = resp.json()
        if not matches:
            print_fail("No matches found")
            sys.exit(1)
        
        match = matches[0]
        hub = match['suggested_hub']
        print_success(f"Match found!")
        print_info(f"  Hub: {hub['name']}")
        print_info(f"  Hub coords: ({hub['lat']:.4f}, {hub['lng']:.4f})")
    except Exception as e:
        print_fail(f"Error finding match: {e}")
        sys.exit(1)
    
    # Confirm match
    print_info("Confirming match...")
    try:
        resp = requests.post(f"{base_url}/match-scheduled/confirm", params={
            "trip_id": trip_id,
            "request_id": request_id,
            "hub_id": hub['id']
        })
        if resp.status_code != 200:
            print_fail(f"Failed to confirm match: {resp.status_code}")
            sys.exit(1)
        
        print_success("Match confirmed!")
    except Exception as e:
        print_fail(f"Error confirming match: {e}")
        sys.exit(1)
    
    # Set Simulator location based on perspective
    if perspective == "driver":
        print_info("Setting up iOS Simulator (driver perspective)...")
        set_simulator_location(driver.get('start_lat'), driver.get('start_lng'))
        
        # Print instructions for user
        print_header("Match Confirmed - Waiting for En-Route")
        print(f"{GREEN}Next Steps:{NC}")
        print(f"{GREEN}1. Open the Expo app on iOS Simulator{NC}")
        print(f"{GREEN}2. You should see 'Today's Ride' with hub: {hub['name']}{NC}")
        print(f"{GREEN}3. Tap 'I'm on my way' button{NC}")
        print(f"{GREEN}4. The script will automatically detect this and start the route simulation{NC}\n")
        
        # Wait for driver to start en-route
        if not wait_for_en_route(base_url, trip_id, timeout=120):
            print_fail("Driver did not start en-route - exiting")
            sys.exit(1)
        
        # Start route simulation
        print_header("Starting Automated Route Simulation")
        print(f"{GREEN}Watch the Expo app:{NC}")
        print(f"{GREEN}• Driver marker will move toward the hub automatically{NC}")
        print(f"{GREEN}• Hub: {hub['name']}{NC}")
        print(f"{GREEN}• Location updates every {interval} seconds{NC}\n")
        print_info("Press Ctrl+C to stop the simulation\n")
        
        time.sleep(2)  # Give user time to see the app
        
        # Run route simulation to hub if GPX available
        if resort["hub_gpx"] and os.path.exists(resort["hub_gpx"]):
            hub_coords = (hub['lat'], hub['lng'])
            simulate_driver_route(base_url, trip_id, resort["hub_gpx"], hub_coords, interval)
        else:
            print_warning("No hub GPX route available for this resort")
    else:
        print_info("Setting up iOS Simulator (passenger perspective)...")
        set_simulator_location(passenger.get('pickup_lat'), passenger.get('pickup_lng'))
        
        # For passenger perspective, start background driver simulation
        print_info("Starting background driver simulation...")
        try:
            subprocess.Popen([
                "python3", "simulate_realtime_tracking.py",
                "--trip-id", str(trip_id),
                "--interval", "15.0"
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print_success("Background driver simulation started")
        except:
            print_warning("Could not start background simulation (you'll need to move driver manually)")
        
        print(f"{GREEN}1. Open the Expo app on iOS Simulator as PASSENGER{NC}")
        print(f"{GREEN}2. You should see 'Today's Ride' with hub: {hub['name']}{NC}")
        print(f"{GREEN}3. Watch the driver's location update on the map (automated){NC}")
        print(f"{GREEN}4. Driver will move toward the hub{NC}")
        print(f"{GREEN}5. Confirm pickup when prompted{NC}\n")
        print_warning("To stop background driver simulation: pkill -f simulate_realtime_tracking")


def main():
    parser = argparse.ArgumentParser(description="SkiPool Ride Simulation Setup")
    parser.add_argument("--mode", required=True, choices=["now", "scheduled"],
                       help="Simulation mode: 'now' for Ride Now, 'scheduled' for Scheduled rides")
    parser.add_argument("--resort", default="solitude", choices=["solitude", "park_city"],
                       help="Resort to simulate (default: solitude)")
    parser.add_argument("--base-url", default="http://localhost:8080",
                       help="API base URL (default: http://localhost:8080)")
    parser.add_argument("--perspective", default="driver", choices=["driver", "passenger"],
                       help="Perspective for scheduled mode (default: driver)")
    parser.add_argument("--driver-name", default="Sim Driver",
                       help="Expected driver name to detect (default: 'Sim Driver')")
    parser.add_argument("--interval", type=int, default=10,
                       help="Seconds between location updates (default: 10)")
    
    args = parser.parse_args()
    
    # Check API health
    print_info(f"Checking API at {args.base_url}...")
    try:
        resp = requests.get(f"{args.base_url}/health", timeout=5)
        if resp.status_code != 200:
            print_fail(f"API health check failed: {resp.status_code}")
            print_info("Make sure the API is running: ./dev.sh local")
            sys.exit(1)
        print_success("API is healthy")
    except Exception as e:
        print_fail(f"Cannot reach API: {e}")
        print_info("Make sure the API is running: ./dev.sh local")
        sys.exit(1)
    
    # Run simulation
    if args.mode == "now":
        sim_ride_now(args.base_url, args.resort, args.driver_name, args.interval)
    else:
        sim_scheduled(args.base_url, args.resort, args.perspective, args.interval)


if __name__ == "__main__":
    main()
