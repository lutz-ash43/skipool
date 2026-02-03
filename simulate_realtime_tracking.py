#!/usr/bin/env python3
"""
Continuous location tracking simulation.
Updates location every few seconds to simulate real-time tracking.
Useful for testing while using the app in simulator.
"""
import sys
import os
import time
import math
import signal
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_db
from models import Trip, RideRequest
from sqlalchemy.orm import Session

running = True

def signal_handler(sig, frame):
    global running
    print("\n\n⏹️  Stopping simulation...")
    running = False

signal.signal(signal.SIGINT, signal_handler)

def interpolate_location(start_lat, start_lng, end_lat, end_lng, progress):
    """Interpolate between two points. progress: 0.0 to 1.0"""
    lat = start_lat + (end_lat - start_lat) * progress
    lng = start_lng + (end_lng - start_lng) * progress
    return lat, lng

def continuous_tracking(trip_id: int = None, request_id: int = None, interval: float = 15.0):
    """
    Continuously update location to simulate real-time tracking.
    Updates every 'interval' seconds.
    """
    db: Session = next(get_db())
    
    RESORTS = {
        "Alta": (40.5883, -111.6358),
        "Snowbird": (40.5830, -111.6563),
        "Brighton": (40.5981, -111.5831),
        "Solitude": (40.6199, -111.5919),
        "Park City Mountain": (40.6514, -111.5080),
        "Canyons Village": (40.6853, -111.5562),
        "Deer Valley": (40.6367, -111.4792),
    }
    
    if trip_id:
        trip = db.query(Trip).filter(Trip.id == trip_id).first()
        if not trip:
            print(f"❌ Trip {trip_id} not found")
            return
        
        start_lat = trip.start_lat or trip.current_lat or 40.7244
        start_lng = trip.start_lng or trip.current_lng or -111.8881
        resort_coords = RESORTS.get(trip.resort)
        
        if not resort_coords:
            print(f"❌ Resort {trip.resort} not found")
            return
        
        print(f"🚗 Continuous tracking: Driver {trip_id} ({trip.driver_name})")
        print(f"   Route: ({start_lat:.4f}, {start_lng:.4f}) → {trip.resort}")
        print(f"   Update interval: {interval}s")
        print(f"   Press Ctrl+C to stop\n")
        
        progress = 0.0
        step_size = 0.02  # Move 2% per update
        
        while running:
            if progress >= 1.0:
                progress = 0.0  # Reset or stop
                print("   ✅ Reached destination, resetting...")
            
            lat, lng = interpolate_location(start_lat, start_lng, resort_coords[0], resort_coords[1], progress)
            
            trip.current_lat = lat
            trip.current_lng = lng
            trip.last_location_update = datetime.utcnow()
            db.commit()
            
            print(f"   📍 ({lat:.4f}, {lng:.4f}) - {progress*100:.0f}% to {trip.resort}")
            
            progress += step_size
            time.sleep(interval)
    
    elif request_id:
        request = db.query(RideRequest).filter(RideRequest.id == request_id).first()
        if not request:
            print(f"❌ Request {request_id} not found")
            return
        if (request.departure_time or "").strip().lower() == "now":
            print("⚠️  Ride Now: passengers are at pickup; we do not track their location.")
            print("   Use this script only for scheduled en-route testing.")
            return
        
        center_lat = request.pickup_lat
        center_lng = request.pickup_lng
        radius = 0.001  # ~100m
        
        print(f"🚶 Continuous tracking: Passenger {request_id} ({request.passenger_name}) [scheduled en-route]")
        print(f"   Moving around: ({center_lat:.4f}, {center_lng:.4f})")
        print(f"   Update interval: {interval}s")
        print(f"   Press Ctrl+C to stop\n")
        
        angle = 0.0
        
        while running:
            lat = center_lat + radius * math.cos(angle)
            lng = center_lng + radius * math.sin(angle)
            
            request.current_lat = lat
            request.current_lng = lng
            request.last_location_update = datetime.utcnow()
            db.commit()
            
            print(f"   📍 ({lat:.4f}, {lng:.4f})")
            
            angle += 0.1
            time.sleep(interval)
    
    else:
        print("❌ Must provide --trip-id or --request-id")
        return
    
    db.close()
    print("\n✅ Tracking stopped")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Continuous location tracking simulation")
    parser.add_argument("--trip-id", type=int, help="Trip ID to track (driver)")
    parser.add_argument("--request-id", type=int, help="Request ID to track (passenger)")
    parser.add_argument("--interval", type=float, default=15.0, help="Update interval in seconds (default: 15.0)")
    
    args = parser.parse_args()
    
    if not args.trip_id and not args.request_id:
        print("Usage:")
        print("  # Continuous driver tracking (Ride Now or scheduled en-route)")
        print("  python simulate_realtime_tracking.py --trip-id 1 --interval 15.0")
        print("\n  # Continuous passenger tracking (scheduled en-route only; not Ride Now)")
        print("  python simulate_realtime_tracking.py --request-id 3 --interval 15.0")
    else:
        continuous_tracking(args.trip_id, args.request_id, args.interval)
