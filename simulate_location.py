#!/usr/bin/env python3
"""
Script to simulate location updates for testing.
Updates driver/passenger locations to simulate movement along a route.
"""
import sys
import os
import time
import math
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_db
from models import Trip, RideRequest
from sqlalchemy.orm import Session

def interpolate_location(start_lat, start_lng, end_lat, end_lng, progress):
    """Interpolate between two points. progress: 0.0 to 1.0"""
    lat = start_lat + (end_lat - start_lat) * progress
    lng = start_lng + (end_lng - start_lng) * progress
    return lat, lng

def simulate_driver_route(trip_id: int, steps: int = 10, delay: float = 2.0):
    """
    Simulate a driver moving from start to resort.
    Updates location every 'delay' seconds for 'steps' steps.
    """
    db: Session = next(get_db())
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        print(f"❌ Trip {trip_id} not found")
        return
    
    # Get resort coordinates
    RESORTS = {
        "Alta": (40.5883, -111.6358),
        "Snowbird": (40.5830, -111.6563),
        "Brighton": (40.5981, -111.5831),
        "Solitude": (40.6199, -111.5919),
        "Park City Mountain": (40.6514, -111.5080),
        "Canyons Village": (40.6853, -111.5562),
        "Deer Valley": (40.6367, -111.4792),
    }
    
    resort_coords = RESORTS.get(trip.resort)
    if not resort_coords:
        print(f"❌ Resort {trip.resort} not found")
        return
    
    start_lat = trip.start_lat or trip.current_lat
    start_lng = trip.start_lng or trip.current_lng
    
    if not start_lat or not start_lng:
        print(f"❌ Trip {trip_id} has no start location")
        return
    
    print(f"🚗 Simulating driver {trip_id} ({trip.driver_name})")
    print(f"   Route: ({start_lat:.4f}, {start_lng:.4f}) → {trip.resort} ({resort_coords[0]:.4f}, {resort_coords[1]:.4f})")
    print(f"   {steps} steps, {delay}s delay per step\n")
    
    for i in range(steps + 1):
        progress = i / steps
        lat, lng = interpolate_location(start_lat, start_lng, resort_coords[0], resort_coords[1], progress)
        
        trip.current_lat = lat
        trip.current_lng = lng
        trip.last_location_update = datetime.utcnow()
        db.commit()
        
        print(f"   Step {i}/{steps}: ({lat:.4f}, {lng:.4f}) - {progress*100:.0f}% to {trip.resort}")
        
        if i < steps:
            time.sleep(delay)
    
    print(f"\n✅ Driver {trip_id} reached {trip.resort}\n")
    db.close()

def simulate_passenger_movement(request_id: int, steps: int = 5, delay: float = 2.0):
    """
    Simulate a passenger moving (e.g., for scheduled en-route).
    Ride Now: passengers are at pickup; we do not track their location.
    Use this only for scheduled en-route testing.
    Moves in a small circle around their pickup location.
    """
    db: Session = next(get_db())
    request = db.query(RideRequest).filter(RideRequest.id == request_id).first()
    if not request:
        print(f"❌ Request {request_id} not found")
        return
    if (request.departure_time or "").strip().lower() == "now":
        print("⚠️  Ride Now: passengers are at pickup; we do not track their location.")
        print("   Use --request-id only for scheduled en-route (e.g. request IDs 3 or 4).")
        db.close()
        return

    center_lat = request.pickup_lat
    center_lng = request.pickup_lng
    
    print(f"🚶 Simulating passenger {request_id} ({request.passenger_name})")
    print(f"   Moving around ({center_lat:.4f}, {center_lng:.4f})")
    print(f"   {steps} steps, {delay}s delay per step\n")
    
    # Small circle movement (about 100m radius)
    radius = 0.001  # ~100m in degrees
    
    for i in range(steps):
        angle = (i / steps) * 2 * math.pi
        lat = center_lat + radius * math.cos(angle)
        lng = center_lng + radius * math.sin(angle)
        
        request.current_lat = lat
        request.current_lng = lng
        request.last_location_update = datetime.utcnow()
        db.commit()
        
        print(f"   Step {i+1}/{steps}: ({lat:.4f}, {lng:.4f})")
        time.sleep(delay)
    
    print(f"\n✅ Passenger {request_id} movement complete\n")
    db.close()

def simulate_scheduled_en_route(trip_id: int, hub_lat: float, hub_lng: float, steps: int = 10, delay: float = 2.0):
    """Simulate driver moving to meeting hub for scheduled ride"""
    db: Session = next(get_db())
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        print(f"❌ Trip {trip_id} not found")
        return
    
    start_lat = trip.start_lat or trip.current_lat or 40.7244
    start_lng = trip.start_lng or trip.current_lng or -111.8881
    
    print(f"🚗 Simulating scheduled driver {trip_id} en route to meeting point")
    print(f"   Route: ({start_lat:.4f}, {start_lng:.4f}) → Hub ({hub_lat:.4f}, {hub_lng:.4f})")
    print(f"   {steps} steps, {delay}s delay per step\n")
    
    for i in range(steps + 1):
        progress = i / steps
        lat, lng = interpolate_location(start_lat, start_lng, hub_lat, hub_lng, progress)
        
        trip.current_lat = lat
        trip.current_lng = lng
        trip.last_location_update = datetime.utcnow()
        db.commit()
        
        print(f"   Step {i}/{steps}: ({lat:.4f}, {lng:.4f}) - {progress*100:.0f}% to hub")
        if i < steps:
            time.sleep(delay)
    
    print(f"\n✅ Driver {trip_id} reached meeting point\n")
    db.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Simulate location updates for testing")
    parser.add_argument("--trip-id", type=int, help="Trip ID to simulate (driver)")
    parser.add_argument("--request-id", type=int, help="Request ID to simulate (passenger)")
    parser.add_argument("--hub-lat", type=float, help="Hub latitude (for scheduled en-route)")
    parser.add_argument("--hub-lng", type=float, help="Hub longitude (for scheduled en-route)")
    parser.add_argument("--steps", type=int, default=10, help="Number of steps (default: 10)")
    parser.add_argument("--delay", type=float, default=2.0, help="Delay between steps in seconds (default: 2.0)")
    
    args = parser.parse_args()
    
    if args.trip_id and args.hub_lat and args.hub_lng:
        simulate_scheduled_en_route(args.trip_id, args.hub_lat, args.hub_lng, args.steps, args.delay)
    elif args.trip_id:
        simulate_driver_route(args.trip_id, args.steps, args.delay)
    elif args.request_id:
        simulate_passenger_movement(args.request_id, args.steps, args.delay)
    else:
        print("Usage:")
        print("  # Simulate driver route (Ride Now)")
        print("  python simulate_location.py --trip-id 1 --steps 10 --delay 2.0")
        print("\n  # Simulate passenger movement (scheduled en-route only; not Ride Now)")
        print("  python simulate_location.py --request-id 3 --steps 5 --delay 2.0")
        print("\n  # Simulate scheduled driver en route to hub")
        print("  python simulate_location.py --trip-id 3 --hub-lat 40.5897 --hub-lng -111.8856 --steps 10 --delay 2.0")
