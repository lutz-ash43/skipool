from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime

# --- SHARED BASES ---
class TripBase(BaseModel):
    driver_name: str
    resort: str
    departure_time: str
    # CHANGED: Made Optional so 'Ride Now' doesn't fail
    start_location_text: Optional[str] = None 
    available_seats: int = 3
    is_realtime: bool = False
    # ADDED: To capture GPS from the phone
    current_lat: Optional[float] = None
    current_lng: Optional[float] = None
    # For scheduled rides
    trip_date: Optional[date] = None

class RideRequestBase(BaseModel):
    passenger_name: str
    resort: str
    # ADDED: To match the frontend sending time
    departure_time: Optional[str] = "Now"
    # For scheduled rides
    request_date: Optional[date] = None 

# --- TRIP SCHEMAS (Driver) ---
class TripCreate(TripBase):
    pass

class Trip(TripBase):
    id: int
    start_lat: Optional[float]
    start_lng: Optional[float]
    current_lat: Optional[float]
    current_lng: Optional[float]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class LocationUpdate(BaseModel):
    current_lat: float
    current_lng: float

# --- RIDE REQUEST SCHEMAS (Passenger) ---
class RideRequestCreate(RideRequestBase):
    # CHANGED: Made Optional so it doesn't crash if using a text address instead
    lat: Optional[float] = None
    lng: Optional[float] = None
    # ADDED: To capture manual address input
    pickup_text: Optional[str] = None

class RideRequest(RideRequestBase):
    id: int
    pickup_lat: float
    pickup_lng: float
    status: str
    matched_trip_id: Optional[int] = None
    suggested_hub_id: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class RideRequestUpdate(BaseModel):
    matched_trip_id: Optional[int] = None
    suggested_hub_id: Optional[str] = None
    status: Optional[str] = None

class ScheduledMatch(BaseModel):
    trip_id: int
    request_id: int
    driver_name: str
    passenger_name: str
    resort: str
    suggested_hub: dict
    driver_departure_time: str
    passenger_departure_time: str
    hub_distance_driver: float  # km
    hub_distance_passenger: float  # km