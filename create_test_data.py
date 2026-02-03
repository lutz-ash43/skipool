#!/usr/bin/env python3
"""
Script to create test data for SkiPool app testing.
Creates drivers and passengers for both Ride Now and Scheduled rides.
"""
import sys
import os
from datetime import date, timedelta, datetime

# Add parent directory to path to import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_db, engine
from models import Trip, RideRequest
from sqlalchemy.orm import Session

def create_test_data():
    """Create test trips and ride requests for testing"""
    db: Session = next(get_db())
    
    try:
        # Clear existing test data (optional - comment out if you want to keep existing)
        # db.query(Trip).filter(Trip.driver_name.like("Test Driver%")).delete()
        # db.query(RideRequest).filter(RideRequest.passenger_name.like("Test Passenger%")).delete()
        # db.commit()
        
        tomorrow = date.today() + timedelta(days=1)
        
        # === RIDE NOW TEST DATA ===
        print("Creating Ride Now test data...")
        
        # Ride Now Driver 1 - Going to Alta, 3 seats, currently at Sugar House
        ride_now_driver1 = Trip(
            driver_name="Test Driver - Solitude",
            resort="Solitude",
            departure_time="Now",
            start_location_text="The Engen Hus Bed & Breakfast",
            start_lat=40.6409,
            start_lng=-111.8175,
            current_lat=40.6409,  # Starting location
            current_lng=-111.8175,
            last_location_update=datetime.utcnow(),
            available_seats=3,
            is_realtime=True
        )
        db.add(ride_now_driver1)
        
        # Ride Now Passenger 1 - Needs 1 seat, at pickup (we don't track location)
        ride_now_passenger1 = RideRequest(
            passenger_name="Test Passenger - Solitude",
            resort="Solitude",
            departure_time="Now",
            pickup_lat=40.6199927,
            pickup_lng=-111.7883008,  
            current_lat=None,
            current_lng=None,
            last_location_update=None,
            pickup_address="Big Cottonwood Canyon Park & Ride",
            seats_needed=1,
            status="pending"
        )
        db.add(ride_now_passenger1)
        
        # Ride Now Driver 2 - Going to Park City, 2 seats, at downtown SLC
        ride_now_driver2 = Trip(
            driver_name="Test Driver - Park City",
            resort="Park City Mountain",
            departure_time="Now",
            start_location_text="Quarry Condos, Park City, UT",
            start_lat=40.75,
            start_lng=-111.57,
            current_lat=40.75,
            current_lng=-111.57,
            last_location_update=datetime.utcnow(),
            available_seats=2,
            is_realtime=True
        )
        db.add(ride_now_driver2)
        
        # Ride Now Passenger 2 - Needs 2 seats, at pickup (we don't track location)
        ride_now_passenger2 = RideRequest(
            passenger_name="Test Passenger - Park City",
            resort="Park City Mountain",
            departure_time="Now",
            pickup_lat=40.755,
            pickup_lng=-111.572,  # Midvale area
            current_lat=None,
            current_lng=None,
            last_location_update=None,
            pickup_address="Jeremy Ranch P&R, Park City, UT",
            seats_needed=2,
            status="pending"
        )
        db.add(ride_now_passenger2)
        
        # === SCHEDULED RIDE TEST DATA ===
        print("Creating Scheduled ride test data...")
        
        # Scheduled Driver 1 - Going to Alta tomorrow, 7:00 AM, 4 seats
        scheduled_driver1 = Trip(
            driver_name="Test Driver - Scheduled Solitude",
            resort="Solitude",
            departure_time="7:00 AM",
            start_location_text="The Engen Hus Bed & Breakfast",
            start_lat=40.6409,
            start_lng=-111.8175,
            available_seats=4,
            is_realtime=False,
            trip_date=tomorrow
        )
        db.add(scheduled_driver1)
        
        # Scheduled Passenger 1 - Needs 2 seats, 7:30 AM
        scheduled_passenger1 = RideRequest(
            passenger_name="Test Passenger - Scheduled Solitude",
            resort="Solitude",
            departure_time="7:30 AM",
            pickup_lat=40.624,
            pickup_lng=-111.801,  # hogwallow pub
            pickup_address="The Hogwallow Pub",
            seats_needed=2,
            status="pending",
            request_date=tomorrow
        )
        db.add(scheduled_passenger1)
        
        # Scheduled Driver 2 - Going to Snowbird, 6:30 AM, 2 seats
        scheduled_driver2 = Trip(
            driver_name="Test Driver - Scheduled Park City",
            resort="Park City Mountain",
            departure_time="6:30 AM",
            start_location_text="Quarry Condos, Park City, UT",
            start_lat=40.75,
            start_lng=-111.57,
            available_seats=2,
            is_realtime=False,
            trip_date=tomorrow
        )
        db.add(scheduled_driver2)
        
        # Scheduled Passenger 2 - Needs 1 seat, 6:45 AM
        scheduled_passenger2 = RideRequest(
            passenger_name="Test Passenger - Scheduled Park City",
            resort="Park City Mountain",
            departure_time="6:45 AM",
            pickup_lat=40.7592,
            pickup_lng=-111.5735,  # Midvale
            pickup_address="Jeremy Ranch Golf & Country Club", #need another location near jeremy ranch
            seats_needed=1,
            status="pending",
            request_date=tomorrow
        )
        db.add(scheduled_passenger2)
        
        db.commit()
        
        print("\n✅ Test data created successfully!")
        print("\nRide Now:")
        print(f"  Driver 1 (Alta): ID {ride_now_driver1.id}, {ride_now_driver1.available_seats} seats")
        print(f"  Passenger 1 (Alta): ID {ride_now_passenger1.id}, needs {ride_now_passenger1.seats_needed} seat")
        print(f"  Driver 2 (Park City): ID {ride_now_driver2.id}, {ride_now_driver2.available_seats} seats")
        print(f"  Passenger 2 (Park City): ID {ride_now_passenger2.id}, needs {ride_now_passenger2.seats_needed} seats")
        print("\nScheduled (tomorrow):")
        print(f"  Driver 1 (Alta, 7:00 AM): ID {scheduled_driver1.id}, {scheduled_driver1.available_seats} seats")
        print(f"  Passenger 1 (Alta, 7:30 AM): ID {scheduled_passenger1.id}, needs {scheduled_passenger1.seats_needed} seats")
        print(f"  Driver 2 (Snowbird, 6:30 AM): ID {scheduled_driver2.id}, {scheduled_driver2.available_seats} seats")
        print(f"  Passenger 2 (Snowbird, 6:45 AM): ID {scheduled_passenger2.id}, needs {scheduled_passenger2.seats_needed} seat")
        print("\n💡 Ride Now: simulate driver only (--trip-id). Passengers at pickup; no location sim.")
        print("   Scheduled en-route: use --request-id 3 or 4 for passenger, --trip-id 3 or 4 for driver.")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error creating test data: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    create_test_data()
