from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, JSON, ForeignKey, Date
from database import Base
import datetime

class Trip(Base):
    __tablename__ = "trips"

    id = Column(Integer, primary_key=True, index=True)
    driver_name = Column(String)
    resort = Column(String)
    
    # Text address from the user
    start_location_text = Column(String)
    
    # Geocoded coordinates for mapping/matching
    start_lat = Column(Float, nullable=True)
    start_lng = Column(Float, nullable=True)
    
    # Real-time location tracking (for "Ride Now" mode)
    current_lat = Column(Float, nullable=True)
    current_lng = Column(Float, nullable=True)
    last_location_update = Column(DateTime, nullable=True)
    
    departure_time = Column(String)
    available_seats = Column(Integer, default=3)
    is_realtime = Column(Boolean, default=False)
    
    # For scheduled rides
    trip_date = Column(Date, nullable=True)  # Date of the trip (tomorrow, etc.)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.datetime.utcnow)

class RideRequest(Base):
    __tablename__ = "ride_requests"
    id = Column(Integer, primary_key=True, index=True)
    passenger_name = Column(String)
    resort = Column(String)
    pickup_lat = Column(Float)
    pickup_lng = Column(Float)
    pickup_address = Column(String)
    departure_time = Column(String)  # Added: matches schema and used in create_ride_request
    status = Column(String, default="pending") # pending, matched
    
    # Real-time location tracking (for "Ride Now" mode)
    current_lat = Column(Float, nullable=True)
    current_lng = Column(Float, nullable=True)
    last_location_update = Column(DateTime, nullable=True)
    
    # For scheduled rides
    request_date = Column(Date, nullable=True)  # Date of the ride request (tomorrow, etc.)
    
    # Matching relationships
    matched_trip_id = Column(Integer, ForeignKey('trips.id'), nullable=True)
    suggested_hub_id = Column(String, nullable=True)  # Store suggested hub ID
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.datetime.utcnow)