#!/usr/bin/env python3
"""
SkiPool End-to-End Test Script

Tests the full ride lifecycle (post, match, accept, pickup, complete) for both
Ride Now and Scheduled rides by calling the live API.

Usage:
    python test_flows.py                           # defaults to http://localhost:8080
    python test_flows.py --base-url http://localhost:8080
    python test_flows.py --base-url https://skidb-backend-XXXX.run.app
    python test_flows.py --no-wipe                 # skip DB wipe
    python test_flows.py --skip-geocoding          # use lat/lng instead of addresses (faster)
"""

import requests
import argparse
import random
import sys
import math
from datetime import date, datetime, timedelta
from typing import List, Dict, Tuple, Optional

# Colors for terminal output
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color

# Real SLC-area locations for test data with expected coordinates for validation
# Using simpler addresses that Nominatim can reliably geocode
# Organized so drivers start WEST and passengers are BETWEEN driver and resort (east)
DRIVER_ORIGINS = [
    # For Solitude (Big Cottonwood Canyon) - start from western SLC valley
    {"name": "Sugar House, Salt Lake City", "lat": 40.7178, "lng": -111.8689},  # West, good start
    {"name": "Downtown Salt Lake City", "lat": 40.7608, "lng": -111.8910},     # West, good start
    {"name": "Murray, Utah", "lat": 40.6669, "lng": -111.8879},                # West, good start
    {"name": "Midvale, Utah", "lat": 40.6211, "lng": -111.8989},               # West, good start
]

PASSENGER_PICKUPS = [
    # Locations BETWEEN western SLC and Big Cottonwood Canyon (on the way to Solitude)
    {"name": "Holladay, Utah", "lat": 40.6688, "lng": -111.8245},      # East of SLC, on route
    {"name": "Cottonwood Heights", "lat": 40.6181, "lng": -111.8362},  # Near canyon entrance
    {"name": "Murray, Utah", "lat": 40.6669, "lng": -111.8879},        # Central, on route
    {"name": "Millcreek, Utah", "lat": 40.6869, "lng": -111.8758},     # East side, on route
]

# Track test results
test_results = []
created_trip_ids = []
created_request_ids = []

# Global flag for geocoding mode
use_geocoding = True


class TestResult:
    """Tracks result of a single test step"""
    def __init__(self, scenario: str, step: str, passed: bool, details: str = ""):
        self.scenario = scenario
        self.step = step
        self.passed = passed
        self.details = details
        test_results.append(self)


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in km between two lat/lng points"""
    R = 6371  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return 2 * R * math.asin(math.sqrt(a))


def validate_coords(actual_lat: float, actual_lng: float, expected_lat: float, expected_lng: float, tolerance_km: float = 5.0) -> Tuple[bool, float]:
    """
    Check if geocoded coords are within tolerance of expected location.
    Returns (is_valid, distance_km)
    """
    dist = haversine(actual_lat, actual_lng, expected_lat, expected_lng)
    return (dist <= tolerance_km, dist)


def print_pass(message: str):
    """Print a green success message"""
    print(f"{GREEN}✓ {message}{NC}")


def print_fail(message: str):
    """Print a red failure message"""
    print(f"{RED}✗ {message}{NC}")


def print_info(message: str):
    """Print a blue info message"""
    print(f"{BLUE}→ {message}{NC}")


def print_header(message: str):
    """Print a section header"""
    print(f"\n{BLUE}{'=' * 60}{NC}")
    print(f"{BLUE}{message}{NC}")
    print(f"{BLUE}{'=' * 60}{NC}")


def wipe_database(base_url: str) -> bool:
    """Wipe all trips and ride requests from the database"""
    print_header("Wiping Database")
    
    try:
        # First, get and delete all ride requests
        print_info("Fetching all active ride requests...")
        resp = requests.get(f"{base_url}/ride-requests/active")
        if resp.status_code == 200:
            requests_data = resp.json()
            print_info(f"Found {len(requests_data)} active ride requests")
            
            for ride_request in requests_data:
                request_id = ride_request['id']
                resp = requests.delete(f"{base_url}/ride-requests/{request_id}")
                if resp.status_code not in [200, 404]:
                    print_warning(f"Failed to delete ride request {request_id}: {resp.status_code}")
        else:
            print_warning(f"Could not fetch ride requests: {resp.status_code}")
        
        # Then, get and delete all trips
        print_info("Fetching all active trips...")
        resp = requests.get(f"{base_url}/trips/active")
        if resp.status_code != 200:
            print_fail(f"Failed to fetch trips: {resp.status_code}")
            return False
        
        trips = resp.json()
        print_info(f"Found {len(trips)} active trips")
        
        # Delete all trips
        for trip in trips:
            trip_id = trip['id']
            resp = requests.delete(f"{base_url}/trips/{trip_id}")
            if resp.status_code not in [200, 404]:
                print_warning(f"Failed to delete trip {trip_id}: {resp.status_code}")
        
        print_pass(f"Database wiped: deleted {len(requests_data)} ride requests and {len(trips)} trips")
        return True
        
    except Exception as e:
        print_fail(f"Error wiping database: {e}")
        return False


def cleanup_test_data(base_url: str):
    """Delete all test data created during this run"""
    print_info("Cleaning up test data...")
    for trip_id in created_trip_ids:
        try:
            requests.delete(f"{base_url}/trips/{trip_id}")
        except:
            pass


def test_ride_now_lifecycle(base_url: str) -> bool:
    """Test the complete Ride Now lifecycle"""
    print_header("Test: Ride Now (Real-Time) -- Full Lifecycle")
    scenario = "Ride Now Lifecycle"
    
    try:
        # Pick random locations
        driver_origin = random.choice(DRIVER_ORIGINS)
        passenger_pickup = random.choice(PASSENGER_PICKUPS)
        resort = "Solitude"
        
        print_info(f"Driver origin: {driver_origin['name']}")
        print_info(f"Passenger pickup: {passenger_pickup['name']}")
        print_info(f"Resort: {resort}")
        
        # Step 1: Driver posts trip
        print_info("Step 1: Driver posts Ride Now trip...")
        driver_data = {
            "driver_name": "Test Driver (Ride Now)",
            "resort": resort,
            "departure_time": "Now",
            "start_location_text": driver_origin['name'],
            "available_seats": 3,
            "is_realtime": True
        }
        
        # If not using geocoding, provide lat/lng directly
        if not use_geocoding:
            driver_data["current_lat"] = driver_origin['lat']
            driver_data["current_lng"] = driver_origin['lng']
        
        resp = requests.post(f"{base_url}/trips/", json=driver_data)
        if resp.status_code != 200:
            print_fail(f"Failed to create trip: {resp.status_code} - {resp.text}")
            TestResult(scenario, "POST /trips/ (driver)", False, f"Status: {resp.status_code}")
            return False
        
        trip = resp.json()
        trip_id = trip['id']
        created_trip_ids.append(trip_id)
        print_pass(f"Driver trip created (ID: {trip_id})")
        TestResult(scenario, "POST /trips/ (driver)", True, f"trip_id={trip_id}")
        
        # Step 2: Passenger posts ride request
        print_info("Step 2: Passenger posts ride request...")
        passenger_data = {
            "passenger_name": "Test Passenger (Ride Now)",
            "resort": resort,
            "departure_time": "Now",
            "pickup_text": passenger_pickup['name'],
            "seats_needed": 1
        }
        
        # If not using geocoding, provide lat/lng directly
        if not use_geocoding:
            passenger_data["lat"] = passenger_pickup['lat']
            passenger_data["lng"] = passenger_pickup['lng']
        
        resp = requests.post(f"{base_url}/ride-requests/", json=passenger_data)
        if resp.status_code != 200:
            print_fail(f"Failed to create ride request: {resp.status_code} - {resp.text}")
            TestResult(scenario, "POST /ride-requests/ (passenger)", False, f"Status: {resp.status_code}")
            return False
        
        ride_request = resp.json()
        request_id = ride_request['id']
        created_request_ids.append(request_id)
        
        # Validate geocoded coordinates if using geocoding
        if use_geocoding:
            if ride_request.get('pickup_lat') and ride_request.get('pickup_lng'):
                is_valid, dist = validate_coords(
                    ride_request['pickup_lat'], ride_request['pickup_lng'],
                    passenger_pickup['lat'], passenger_pickup['lng']
                )
                if not is_valid:
                    print_fail(f"Geocoded coordinates off by {dist:.2f}km (expected within 5km)")
                    TestResult(scenario, "POST /ride-requests/ (passenger) - geocoding", False, f"Off by {dist:.2f}km")
                else:
                    print_pass(f"Geocoding accurate (within {dist:.2f}km)")
                    TestResult(scenario, "POST /ride-requests/ (passenger) - geocoding", True, f"Within {dist:.2f}km")
            else:
                print_fail("Missing pickup_lat/pickup_lng in response")
                TestResult(scenario, "POST /ride-requests/ (passenger) - geocoding", False, "Missing coordinates")
        
        print_pass(f"Passenger request created (ID: {request_id})")
        TestResult(scenario, "POST /ride-requests/ (passenger)", True, f"request_id={request_id}")
        
        # Step 3: Driver searches for nearby passengers
        print_info("Step 3: Driver searches for nearby passengers...")
        resp = requests.get(f"{base_url}/match-nearby-passengers/", params={
            "trip_id": trip_id,
            "resort": resort
        })
        if resp.status_code != 200:
            print_fail(f"Failed to search passengers: {resp.status_code}")
            TestResult(scenario, "GET /match-nearby-passengers/", False, f"Status: {resp.status_code}")
            return False
        
        matches = resp.json()
        if not matches or not any(m['id'] == request_id for m in matches):
            print_fail(f"Passenger not in matches. Found {len(matches)} matches")
            TestResult(scenario, "GET /match-nearby-passengers/", False, f"Passenger not found in {len(matches)} matches")
            return False
        
        print_pass(f"Passenger found in matches ({len(matches)} total)")
        TestResult(scenario, "GET /match-nearby-passengers/", True, f"Found {len(matches)} matches")
        
        # Step 4: Passenger searches for nearby drivers
        print_info("Step 4: Passenger searches for nearby drivers...")
        resp = requests.get(f"{base_url}/match-nearby-drivers/", params={
            "request_id": request_id,
            "resort": resort
        })
        if resp.status_code != 200:
            print_fail(f"Failed to search drivers: {resp.status_code}")
            TestResult(scenario, "GET /match-nearby-drivers/", False, f"Status: {resp.status_code}")
            return False
        
        matches = resp.json()
        if not matches or not any(m['id'] == trip_id for m in matches):
            print_fail(f"Driver not in matches. Found {len(matches)} matches")
            TestResult(scenario, "GET /match-nearby-drivers/", False, f"Driver not found in {len(matches)} matches")
            return False
        
        print_pass(f"Driver found in matches ({len(matches)} total)")
        TestResult(scenario, "GET /match-nearby-drivers/", True, f"Found {len(matches)} matches")
        
        # Step 5: Driver accepts passenger
        print_info("Step 5: Driver accepts passenger...")
        resp = requests.post(f"{base_url}/trips/{trip_id}/accept-passenger", params={
            "request_id": request_id
        })
        if resp.status_code != 200:
            print_fail(f"Failed to accept passenger: {resp.status_code} - {resp.text}")
            TestResult(scenario, "POST /trips/{id}/accept-passenger", False, f"Status: {resp.status_code}")
            return False
        
        print_pass("Driver accepted passenger")
        TestResult(scenario, "POST /trips/{id}/accept-passenger", True, "Match accepted")
        
        # Step 6: Passenger gets matched driver info
        print_info("Step 6: Passenger gets matched driver info...")
        resp = requests.get(f"{base_url}/ride-requests/{request_id}/matched-driver")
        if resp.status_code != 200:
            print_fail(f"Failed to get matched driver: {resp.status_code}")
            TestResult(scenario, "GET /ride-requests/{id}/matched-driver", False, f"Status: {resp.status_code}")
            return False
        
        driver_info = resp.json()
        if not driver_info.get('matched'):
            print_fail("Passenger shows no matched driver")
            TestResult(scenario, "GET /ride-requests/{id}/matched-driver", False, "No match")
            return False
        
        print_pass(f"Passenger sees driver: {driver_info.get('driver_name')}")
        TestResult(scenario, "GET /ride-requests/{id}/matched-driver", True, f"Driver: {driver_info.get('driver_name')}")
        
        # Step 7: Driver gets matched passenger info
        print_info("Step 7: Driver gets matched passenger info...")
        resp = requests.get(f"{base_url}/trips/{trip_id}/matched-passenger")
        if resp.status_code != 200:
            print_fail(f"Failed to get matched passenger: {resp.status_code}")
            TestResult(scenario, "GET /trips/{id}/matched-passenger", False, f"Status: {resp.status_code}")
            return False
        
        passenger_info = resp.json()
        if not passenger_info.get('matched'):
            print_fail("Driver shows no matched passenger")
            TestResult(scenario, "GET /trips/{id}/matched-passenger", False, "No match")
            return False
        
        print_pass(f"Driver sees passenger: {passenger_info.get('passenger_name')}")
        TestResult(scenario, "GET /trips/{id}/matched-passenger", True, f"Passenger: {passenger_info.get('passenger_name')}")
        
        # Step 8: Driver confirms pickup
        print_info("Step 8: Driver confirms pickup...")
        resp = requests.post(f"{base_url}/trips/{trip_id}/confirm-pickup")
        if resp.status_code != 200:
            print_fail(f"Failed to confirm pickup (driver): {resp.status_code} - {resp.text}")
            TestResult(scenario, "POST /trips/{id}/confirm-pickup", False, f"Status: {resp.status_code}")
            return False
        
        print_pass("Driver confirmed pickup")
        TestResult(scenario, "POST /trips/{id}/confirm-pickup", True, "Confirmed")
        
        # Step 9: Passenger confirms pickup
        print_info("Step 9: Passenger confirms pickup...")
        resp = requests.post(f"{base_url}/ride-requests/{request_id}/confirm-pickup")
        if resp.status_code != 200:
            print_fail(f"Failed to confirm pickup (passenger): {resp.status_code} - {resp.text}")
            TestResult(scenario, "POST /ride-requests/{id}/confirm-pickup", False, f"Status: {resp.status_code}")
            return False
        
        result = resp.json()
        if not result.get('both_confirmed'):
            print_fail("Both parties should be confirmed but aren't")
            TestResult(scenario, "POST /ride-requests/{id}/confirm-pickup", False, "Both not confirmed")
            return False
        
        print_pass("Passenger confirmed pickup - both confirmed!")
        TestResult(scenario, "POST /ride-requests/{id}/confirm-pickup", True, "Both confirmed")
        
        # Step 10: Driver completes ride
        print_info("Step 10: Driver completes ride...")
        resp = requests.post(f"{base_url}/trips/{trip_id}/complete")
        if resp.status_code != 200:
            print_fail(f"Failed to complete ride: {resp.status_code} - {resp.text}")
            TestResult(scenario, "POST /trips/{id}/complete", False, f"Status: {resp.status_code}")
            return False
        
        result = resp.json()
        if result.get('status') != 'completed':
            print_fail(f"Status should be 'completed' but is '{result.get('status')}'")
            TestResult(scenario, "POST /trips/{id}/complete", False, f"Status: {result.get('status')}")
            return False
        
        print_pass("Ride completed successfully!")
        TestResult(scenario, "POST /trips/{id}/complete", True, "Status: completed")
        
        print_pass("✓ Ride Now lifecycle test PASSED")
        return True
        
    except Exception as e:
        print_fail(f"Exception during Ride Now test: {e}")
        TestResult(scenario, "Exception", False, str(e))
        return False


def test_scheduled_ride_lifecycle(base_url: str) -> bool:
    """Test the complete Scheduled ride lifecycle"""
    print_header("Test: Scheduled Ride -- Full Lifecycle")
    scenario = "Scheduled Ride Lifecycle"
    
    try:
        # Pick random locations
        driver_origin = random.choice(DRIVER_ORIGINS)
        passenger_pickup = random.choice(PASSENGER_PICKUPS)
        resort = "Solitude"
        today = date.today()
        
        # Random morning times within 30 minutes
        driver_time = "7:00 AM"
        passenger_time = "7:15 AM"
        
        print_info(f"Driver origin: {driver_origin['name']}")
        print_info(f"Passenger pickup: {passenger_pickup['name']}")
        print_info(f"Resort: {resort}")
        print_info(f"Date: {today}")
        print_info(f"Driver time: {driver_time}, Passenger time: {passenger_time}")
        
        # Step 1: Driver posts scheduled trip
        print_info("Step 1: Driver posts scheduled trip...")
        driver_data = {
            "driver_name": "Test Driver (Scheduled)",
            "resort": resort,
            "departure_time": driver_time,
            "start_location_text": driver_origin['name'],
            "available_seats": 4,
            "is_realtime": False,
            "trip_date": str(today)
        }
        
        # If not using geocoding, provide lat/lng directly
        if not use_geocoding:
            driver_data["current_lat"] = driver_origin['lat']
            driver_data["current_lng"] = driver_origin['lng']
        
        resp = requests.post(f"{base_url}/trips/", json=driver_data)
        if resp.status_code != 200:
            print_fail(f"Failed to create trip: {resp.status_code} - {resp.text}")
            TestResult(scenario, "POST /trips/ (driver)", False, f"Status: {resp.status_code}")
            return False
        
        trip = resp.json()
        trip_id = trip['id']
        created_trip_ids.append(trip_id)
        
        # Validate geocoded coordinates if using geocoding
        if use_geocoding:
            if trip.get('start_lat') and trip.get('start_lng'):
                is_valid, dist = validate_coords(
                    trip['start_lat'], trip['start_lng'],
                    driver_origin['lat'], driver_origin['lng']
                )
                if not is_valid:
                    print_fail(f"Geocoded coordinates off by {dist:.2f}km (expected within 5km)")
                    TestResult(scenario, "POST /trips/ (driver) - geocoding", False, f"Off by {dist:.2f}km")
                else:
                    print_pass(f"Geocoding accurate (within {dist:.2f}km)")
                    TestResult(scenario, "POST /trips/ (driver) - geocoding", True, f"Within {dist:.2f}km")
            else:
                print_fail("Missing start_lat/start_lng in response")
                TestResult(scenario, "POST /trips/ (driver) - geocoding", False, "Missing coordinates")
        
        print_pass(f"Driver trip created (ID: {trip_id})")
        TestResult(scenario, "POST /trips/ (driver)", True, f"trip_id={trip_id}")
        
        # Step 2: Passenger posts ride request
        print_info("Step 2: Passenger posts scheduled ride request...")
        passenger_data = {
            "passenger_name": "Test Passenger (Scheduled)",
            "resort": resort,
            "departure_time": passenger_time,
            "pickup_text": passenger_pickup['name'],
            "seats_needed": 2,
            "request_date": str(today)
        }
        
        # If not using geocoding, provide lat/lng directly
        if not use_geocoding:
            passenger_data["lat"] = passenger_pickup['lat']
            passenger_data["lng"] = passenger_pickup['lng']
        
        resp = requests.post(f"{base_url}/ride-requests/", json=passenger_data)
        if resp.status_code != 200:
            print_fail(f"Failed to create ride request: {resp.status_code} - {resp.text}")
            TestResult(scenario, "POST /ride-requests/ (passenger)", False, f"Status: {resp.status_code}")
            return False
        
        ride_request = resp.json()
        request_id = ride_request['id']
        created_request_ids.append(request_id)
        
        # Validate geocoded coordinates if using geocoding
        if use_geocoding:
            if ride_request.get('pickup_lat') and ride_request.get('pickup_lng'):
                is_valid, dist = validate_coords(
                    ride_request['pickup_lat'], ride_request['pickup_lng'],
                    passenger_pickup['lat'], passenger_pickup['lng']
                )
                if not is_valid:
                    print_fail(f"Geocoded coordinates off by {dist:.2f}km (expected within 5km)")
                    TestResult(scenario, "POST /ride-requests/ (passenger) - geocoding", False, f"Off by {dist:.2f}km")
                else:
                    print_pass(f"Geocoding accurate (within {dist:.2f}km)")
                    TestResult(scenario, "POST /ride-requests/ (passenger) - geocoding", True, f"Within {dist:.2f}km")
            else:
                print_fail("Missing pickup_lat/pickup_lng in response")
                TestResult(scenario, "POST /ride-requests/ (passenger) - geocoding", False, "Missing coordinates")
        
        print_pass(f"Passenger request created (ID: {request_id})")
        TestResult(scenario, "POST /ride-requests/ (passenger)", True, f"request_id={request_id}")
        
        # Step 3: Get scheduled matches
        print_info("Step 3: Get scheduled matches...")
        resp = requests.get(f"{base_url}/match-scheduled/", params={
            "resort": resort,
            "target_date": str(today)
        })
        if resp.status_code != 200:
            print_fail(f"Failed to get scheduled matches: {resp.status_code}")
            TestResult(scenario, "GET /match-scheduled/", False, f"Status: {resp.status_code}")
            return False
        
        matches = resp.json()
        our_match = next((m for m in matches if m['trip_id'] == trip_id and m['request_id'] == request_id), None)
        if not our_match:
            print_fail(f"No match found for our trip/request. Found {len(matches)} matches")
            TestResult(scenario, "GET /match-scheduled/", False, f"Match not found in {len(matches)} matches")
            return False
        
        suggested_hub_id = our_match['suggested_hub']['id']
        print_pass(f"Match found with hub: {our_match['suggested_hub']['name']}")
        TestResult(scenario, "GET /match-scheduled/", True, f"Hub: {our_match['suggested_hub']['name']}")
        
        # Step 4: Confirm the match
        print_info("Step 4: Confirm scheduled match...")
        resp = requests.post(f"{base_url}/match-scheduled/confirm", params={
            "trip_id": trip_id,
            "request_id": request_id,
            "hub_id": suggested_hub_id
        })
        if resp.status_code != 200:
            print_fail(f"Failed to confirm match: {resp.status_code} - {resp.text}")
            TestResult(scenario, "POST /match-scheduled/confirm", False, f"Status: {resp.status_code}")
            return False
        
        print_pass("Match confirmed")
        TestResult(scenario, "POST /match-scheduled/confirm", True, "Confirmed")
        
        # Step 5: Driver gets scheduled match info
        print_info("Step 5: Driver gets scheduled match info...")
        resp = requests.get(f"{base_url}/trips/{trip_id}/scheduled-match")
        if resp.status_code != 200:
            print_fail(f"Failed to get scheduled match: {resp.status_code}")
            TestResult(scenario, "GET /trips/{id}/scheduled-match", False, f"Status: {resp.status_code}")
            return False
        
        match_info = resp.json()
        if not match_info.get('matched'):
            print_fail("Driver shows no matched passenger")
            TestResult(scenario, "GET /trips/{id}/scheduled-match", False, "No match")
            return False
        
        print_pass(f"Driver sees match with passenger: {match_info.get('passenger_name')}")
        TestResult(scenario, "GET /trips/{id}/scheduled-match", True, f"Passenger: {match_info.get('passenger_name')}")
        
        # Step 6: Passenger gets scheduled match info
        print_info("Step 6: Passenger gets scheduled match info...")
        resp = requests.get(f"{base_url}/ride-requests/{request_id}/scheduled-match")
        if resp.status_code != 200:
            print_fail(f"Failed to get scheduled match: {resp.status_code}")
            TestResult(scenario, "GET /ride-requests/{id}/scheduled-match", False, f"Status: {resp.status_code}")
            return False
        
        match_info = resp.json()
        if not match_info.get('matched'):
            print_fail("Passenger shows no matched driver")
            TestResult(scenario, "GET /ride-requests/{id}/scheduled-match", False, "No match")
            return False
        
        print_pass(f"Passenger sees match with driver: {match_info.get('driver_name')}")
        TestResult(scenario, "GET /ride-requests/{id}/scheduled-match", True, f"Driver: {match_info.get('driver_name')}")
        
        # Step 7: Driver starts en-route
        print_info("Step 7: Driver starts en-route...")
        resp = requests.post(f"{base_url}/trips/{trip_id}/start-en-route")
        if resp.status_code != 200:
            print_fail(f"Failed to start en-route: {resp.status_code} - {resp.text}")
            TestResult(scenario, "POST /trips/{id}/start-en-route", False, f"Status: {resp.status_code}")
            return False
        
        print_pass("Driver started en-route")
        TestResult(scenario, "POST /trips/{id}/start-en-route", True, "Started")
        
        # Step 8: Update driver location
        print_info("Step 8: Update driver location...")
        resp = requests.put(f"{base_url}/trips/{trip_id}/location", json={
            "current_lat": driver_origin['lat'] + 0.01,  # Slightly moved
            "current_lng": driver_origin['lng'] - 0.01
        })
        if resp.status_code != 200:
            print_fail(f"Failed to update location: {resp.status_code} - {resp.text}")
            TestResult(scenario, "PUT /trips/{id}/location", False, f"Status: {resp.status_code}")
            return False
        
        print_pass("Driver location updated")
        TestResult(scenario, "PUT /trips/{id}/location", True, "Updated")
        
        # Step 9: Both confirm pickup
        print_info("Step 9: Both confirm pickup...")
        resp = requests.post(f"{base_url}/trips/{trip_id}/confirm-pickup")
        if resp.status_code != 200:
            print_fail(f"Failed to confirm pickup (driver): {resp.status_code}")
            TestResult(scenario, "POST /trips/{id}/confirm-pickup", False, f"Status: {resp.status_code}")
            return False
        
        resp = requests.post(f"{base_url}/ride-requests/{request_id}/confirm-pickup")
        if resp.status_code != 200:
            print_fail(f"Failed to confirm pickup (passenger): {resp.status_code}")
            TestResult(scenario, "POST /ride-requests/{id}/confirm-pickup", False, f"Status: {resp.status_code}")
            return False
        
        result = resp.json()
        if not result.get('both_confirmed'):
            print_fail("Both parties should be confirmed")
            TestResult(scenario, "Pickup confirmation", False, "Both not confirmed")
            return False
        
        print_pass("Both confirmed pickup!")
        TestResult(scenario, "Pickup confirmation", True, "Both confirmed")
        
        # Step 10: Complete ride
        print_info("Step 10: Complete ride...")
        resp = requests.post(f"{base_url}/trips/{trip_id}/complete")
        if resp.status_code != 200:
            print_fail(f"Failed to complete ride: {resp.status_code}")
            TestResult(scenario, "POST /trips/{id}/complete", False, f"Status: {resp.status_code}")
            return False
        
        result = resp.json()
        if result.get('status') != 'completed':
            print_fail(f"Status should be 'completed' but is '{result.get('status')}'")
            TestResult(scenario, "POST /trips/{id}/complete", False, f"Status: {result.get('status')}")
            return False
        
        print_pass("Ride completed successfully!")
        TestResult(scenario, "POST /trips/{id}/complete", True, "Status: completed")
        
        print_pass("✓ Scheduled ride lifecycle test PASSED")
        return True
        
    except Exception as e:
        print_fail(f"Exception during Scheduled ride test: {e}")
        TestResult(scenario, "Exception", False, str(e))
        return False


def test_edge_cases(base_url: str) -> bool:
    """Test matching edge cases that should NOT produce matches"""
    print_header("Test: Matching Edge Cases")
    scenario = "Edge Cases"
    all_passed = True
    
    try:
        # Edge Case 1: Different resorts should not match
        print_info("Edge Case 1: Different resorts...")
        driver_origin = random.choice(DRIVER_ORIGINS)
        passenger_pickup = random.choice(PASSENGER_PICKUPS)
        
        # Driver to Solitude
        driver_data = {
            "driver_name": "Test Driver (Solitude)",
            "resort": "Solitude",
            "departure_time": "Now",
            "start_location_text": driver_origin['name'] if use_geocoding else None,
            "available_seats": 3,
            "is_realtime": True
        }
        if not use_geocoding:
            driver_data["current_lat"] = driver_origin['lat']
            driver_data["current_lng"] = driver_origin['lng']
        resp = requests.post(f"{base_url}/trips/", json=driver_data)
        if resp.status_code != 200:
            print_fail("Failed to create driver trip")
            TestResult(scenario, "Different resorts - driver post", False, f"Status: {resp.status_code}")
            all_passed = False
        else:
            trip_id = resp.json()['id']
            created_trip_ids.append(trip_id)
            
            # Passenger to Park City
            passenger_data = {
                "passenger_name": "Test Passenger (Park City)",
                "resort": "Park City Mountain",
                "departure_time": "Now",
                "pickup_text": passenger_pickup['name'] if use_geocoding else None,
                "seats_needed": 1
            }
            if not use_geocoding:
                passenger_data["lat"] = passenger_pickup['lat']
                passenger_data["lng"] = passenger_pickup['lng']
            resp = requests.post(f"{base_url}/ride-requests/", json=passenger_data)
            if resp.status_code != 200:
                print_fail("Failed to create passenger request")
                TestResult(scenario, "Different resorts - passenger post", False, f"Status: {resp.status_code}")
                all_passed = False
            else:
                request_id = resp.json()['id']
                created_request_ids.append(request_id)
                
                # Check no match
                resp = requests.get(f"{base_url}/match-nearby-passengers/", params={
                    "trip_id": trip_id,
                    "resort": "Solitude"
                })
                matches = resp.json() if resp.status_code == 200 else []
                
                if any(m['id'] == request_id for m in matches):
                    print_fail("FAIL: Passenger matched across different resorts!")
                    TestResult(scenario, "Different resorts - no match", False, "Matched across resorts")
                    all_passed = False
                else:
                    print_pass("PASS: No match across different resorts")
                    TestResult(scenario, "Different resorts - no match", True, "Correctly no match")
        
        # Edge Case 2: Not enough seats
        print_info("Edge Case 2: Seat overflow (driver has 1 seat, passenger needs 2)...")
        driver_origin = random.choice(DRIVER_ORIGINS)
        passenger_pickup = random.choice(PASSENGER_PICKUPS)
        
        driver_data = {
            "driver_name": "Test Driver (1 seat)",
            "resort": "Solitude",
            "departure_time": "Now",
            "start_location_text": driver_origin['name'] if use_geocoding else None,
            "available_seats": 1,
            "is_realtime": True
        }
        if not use_geocoding:
            driver_data["current_lat"] = driver_origin['lat']
            driver_data["current_lng"] = driver_origin['lng']
        resp = requests.post(f"{base_url}/trips/", json=driver_data)
        if resp.status_code != 200:
            print_fail("Failed to create driver trip")
            TestResult(scenario, "Seat overflow - driver post", False, f"Status: {resp.status_code}")
            all_passed = False
        else:
            trip_id = resp.json()['id']
            created_trip_ids.append(trip_id)
            
            passenger_data = {
                "passenger_name": "Test Passenger (needs 2)",
                "resort": "Solitude",
                "departure_time": "Now",
                "pickup_text": passenger_pickup['name'] if use_geocoding else None,
                "seats_needed": 2
            }
            if not use_geocoding:
                passenger_data["lat"] = passenger_pickup['lat']
                passenger_data["lng"] = passenger_pickup['lng']
            resp = requests.post(f"{base_url}/ride-requests/", json=passenger_data)
            if resp.status_code != 200:
                print_fail("Failed to create passenger request")
                TestResult(scenario, "Seat overflow - passenger post", False, f"Status: {resp.status_code}")
                all_passed = False
            else:
                request_id = resp.json()['id']
                created_request_ids.append(request_id)
                
                # Check no match
                resp = requests.get(f"{base_url}/match-nearby-passengers/", params={
                    "trip_id": trip_id,
                    "resort": "Solitude"
                })
                matches = resp.json() if resp.status_code == 200 else []
                
                if any(m['id'] == request_id for m in matches):
                    print_fail("FAIL: Passenger matched despite insufficient seats!")
                    TestResult(scenario, "Seat overflow - no match", False, "Matched despite insufficient seats")
                    all_passed = False
                else:
                    print_pass("PASS: No match when seats insufficient")
                    TestResult(scenario, "Seat overflow - no match", True, "Correctly no match")
        
        if all_passed:
            print_pass("✓ Edge cases test PASSED")
        else:
            print_fail("✗ Some edge cases FAILED")
        
        return all_passed
        
    except Exception as e:
        print_fail(f"Exception during edge cases test: {e}")
        TestResult(scenario, "Exception", False, str(e))
        return False


def write_markdown_report(base_url: str, wipe_performed: bool):
    """Write test results to a markdown file"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    total = len(test_results)
    passed = sum(1 for r in test_results if r.passed)
    failed = total - passed
    
    report = f"""# SkiPool Test Report

**Date**: {timestamp}  
**Target**: {base_url}  
**DB Reset**: {"Yes" if wipe_performed else "No"}

## Summary

- **Total Tests**: {total}
- **Passed**: {passed} ✓
- **Failed**: {failed} ✗
- **Success Rate**: {(passed/total*100):.1f}%

"""
    
    # Group by scenario
    scenarios = {}
    for result in test_results:
        if result.scenario not in scenarios:
            scenarios[result.scenario] = []
        scenarios[result.scenario].append(result)
    
    for scenario, results in scenarios.items():
        report += f"\n## {scenario}\n\n"
        report += "| Step | Result | Details |\n"
        report += "|------|--------|----------|\n"
        
        for result in results:
            status = "✓ PASS" if result.passed else "✗ FAIL"
            report += f"| {result.step} | {status} | {result.details} |\n"
    
    # Write to file
    with open("test_report.md", "w") as f:
        f.write(report)
    
    print_info(f"Report written to test_report.md")


def main():
    parser = argparse.ArgumentParser(description="SkiPool End-to-End Test Script")
    parser.add_argument("--base-url", default="http://localhost:8080", 
                       help="Base URL of the API (default: http://localhost:8080)")
    parser.add_argument("--no-wipe", action="store_true",
                       help="Skip database wipe before tests")
    parser.add_argument("--skip-geocoding", action="store_true",
                       help="Use lat/lng directly instead of addresses (faster, skips geocoding validation)")
    
    args = parser.parse_args()
    base_url = args.base_url.rstrip('/')
    
    # Set global geocoding mode
    global use_geocoding
    use_geocoding = not args.skip_geocoding
    
    print_header("SkiPool End-to-End Test Suite")
    print_info(f"Target: {base_url}")
    print_info(f"DB Wipe: {'No' if args.no_wipe else 'Yes'}")
    print_info(f"Geocoding: {'Yes (using addresses)' if use_geocoding else 'No (using lat/lng)'}")
    
    # Check API health
    print_info("Checking API health...")
    try:
        resp = requests.get(f"{base_url}/health", timeout=5)
        if resp.status_code != 200:
            print_fail(f"API health check failed: {resp.status_code}")
            sys.exit(1)
        print_pass("API is healthy")
    except Exception as e:
        print_fail(f"Cannot reach API: {e}")
        print_info("Make sure the API is running (./dev.sh local or ./dev.sh cloud)")
        sys.exit(1)
    
    # Wipe database if requested
    wipe_performed = False
    if not args.no_wipe:
        if not wipe_database(base_url):
            print_fail("Failed to wipe database")
            sys.exit(1)
        wipe_performed = True
    
    # Run tests
    results = []
    
    results.append(("Ride Now Lifecycle", test_ride_now_lifecycle(base_url)))
    results.append(("Scheduled Ride Lifecycle", test_scheduled_ride_lifecycle(base_url)))
    results.append(("Edge Cases", test_edge_cases(base_url)))
    
    # Cleanup
    cleanup_test_data(base_url)
    
    # Write report
    write_markdown_report(base_url, wipe_performed)
    
    # Print summary
    print_header("Test Summary")
    total = len(results)
    passed = sum(1 for _, p in results if p)
    failed = total - passed
    
    print_info(f"Total scenarios: {total}")
    print_pass(f"Passed: {passed}")
    if failed > 0:
        print_fail(f"Failed: {failed}")
    
    print_info("\nDetailed results:")
    for name, passed in results:
        if passed:
            print_pass(f"  {name}")
        else:
            print_fail(f"  {name}")
    
    print_info(f"\nFull report written to test_report.md")
    
    # Exit with appropriate code
    if failed > 0:
        print_fail("\n✗ TESTS FAILED")
        sys.exit(1)
    else:
        print_pass("\n✓ ALL TESTS PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
