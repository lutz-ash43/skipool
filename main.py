from fastapi import FastAPI, Query, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
import math
from datetime import datetime, date, timedelta
from geopy.geocoders import Nominatim

# Database & Models
from database import engine, get_db, Base
from models import Trip, RideRequest
import schemas

Base.metadata.create_all(bind=engine)

app = FastAPI()
geolocator = Nominatim(user_agent="skipool_app")

# --- DATA CONFIGURATION ---
RESORTS_DATA = [
    {"name": "Alta", "lat": 40.5883, "lng": -111.6358},
    {"name": "Snowbird", "lat": 40.5830, "lng": -111.6563},
    {"name": "Brighton", "lat": 40.5981, "lng": -111.5831},
    {"name": "Solitude", "lat": 40.6199, "lng": -111.5919},
    {"name": "Park City Mountain", "lat": 40.6514, "lng": -111.5080},
    {"name": "Canyons Village", "lat": 40.6853, "lng": -111.5562},
    {"name": "Deer Valley", "lat": 40.6367, "lng": -111.4792},
    {"name": "Woodward Park City", "lat": 40.7589, "lng": -111.5761}
]

HUBS = {
    "h1": {"name": "Historic Sandy Station", "lat": 40.5897, "lng": -111.8856},
    "h2": {"name": "9400 S. Highland Dr.", "lat": 40.5815, "lng": -111.8085},
    "h3": {"name": "Midvale Fort Union Station", "lat": 40.6192, "lng": -111.8983},
    "h4": {"name": "6200 S. Wasatch Blvd. (Swamp Lot)", "lat": 40.6375, "lng": -111.7997},
    "h5": {"name": "Big Cottonwood Canyon P&R", "lat": 40.6194, "lng": -111.7870},
    "h6": {"name": "Richardson Flat", "lat": 40.6711, "lng": -111.4496},
    "h7": {"name": "Ecker Hill P&R", "lat": 40.7461, "lng": -111.5734},
    "h8": {"name": "Kimball Junction Transit Center", "lat": 40.7241, "lng": -111.5467},
    "h9": {"name": "Park City High School", "lat": 40.6587, "lng": -111.5034},
    "h10": {"name": "Jeremy Ranch P&R", "lat": 40.7589, "lng": -111.5761}
}

RESORT_HUB_MAP = {
    "Alta": ["h1", "h2", "h3", "h4"],
    "Snowbird": ["h1", "h2", "h3", "h4"],
    "Brighton": ["h3", "h4", "h5"],
    "Solitude": ["h3", "h4", "h5"],
    "Park City Mountain": ["h6", "h7", "h8", "h9"],
    "Canyons Village": ["h7", "h10", "h8"],
    "Deer Valley": ["h6", "h9"],
    "Woodward Park City": ["h7"]
}

# --- MATH UTILITIES ---
def haversine(lat1, lon1, lat2, lon2):
    R = 6371 # km
    dlat, dlon = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return 2 * math.asin(math.sqrt(a)) * R

def get_bearing(lat1, lon1, lat2, lon2):
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_lambda = math.radians(lon2 - lon1)
    y = math.sin(delta_lambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda)
    return (math.degrees(math.atan2(y, x)) + 360) % 360

def get_cross_track_distance(d_lat, d_lon, r_lat, r_lon, p_lat, p_lon):
    R = 6371 
    dist_dp = haversine(d_lat, d_lon, p_lat, p_lon)
    bearing_dr = get_bearing(d_lat, d_lon, r_lat, r_lon)
    bearing_dp = get_bearing(d_lat, d_lon, p_lat, p_lon)
    return abs(math.asin(math.sin(dist_dp / R) * math.sin(math.radians(bearing_dp - bearing_dr))) * R)

# --- UTILITY ENDPOINTS ---
@app.get("/resorts/")
def get_resorts():
    return [r["name"] for r in RESORTS_DATA]

@app.get("/hubs-for-resort/")
def get_hubs_for_resort(resort: str):
    allowed_ids = RESORT_HUB_MAP.get(resort, [])
    return {hid: HUBS[hid] for hid in allowed_ids if hid in HUBS}

# --- TRIP ENDPOINTS (DRIVER) ---
@app.post("/trips/", response_model=schemas.Trip)
def create_trip(trip: schemas.TripCreate, db: Session = Depends(get_db)):
    lat, lng = trip.current_lat, trip.current_lng
    if trip.start_location_text:
        loc = geolocator.geocode(f"{trip.start_location_text}, Utah")
        if loc:
            lat, lng = loc.latitude, loc.longitude
    
    # Initialize current location for real-time trips
    current_lat, current_lng = trip.current_lat, trip.current_lng
    if trip.is_realtime and current_lat and current_lng:
        # For real-time trips, current location starts as initial location
        pass
    else:
        current_lat, current_lng = None, None
    
    new_trip = Trip(
        **trip.model_dump(exclude={"current_lat", "current_lng"}),
        start_lat=lat,
        start_lng=lng,
        current_lat=current_lat,
        current_lng=current_lng,
        last_location_update=datetime.utcnow() if trip.is_realtime and current_lat else None
    )
    db.add(new_trip)
    db.commit()
    db.refresh(new_trip)
    return new_trip

@app.delete("/trips/{trip_id}")
def delete_trip(trip_id: int, db: Session = Depends(get_db)):
    db_trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not db_trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    db.delete(db_trip)
    db.commit()
    return {"message": "Trip deleted successfully"}

@app.post("/trips/{trip_id}/book")
def book_trip(trip_id: int, db: Session = Depends(get_db)):
    db_trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not db_trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if db_trip.available_seats > 0:
        db_trip.available_seats -= 1
        db.commit()
        return {"remaining": db_trip.available_seats}
    raise HTTPException(status_code=400, detail="Unable to book - no available seats")

@app.put("/trips/{trip_id}/location", response_model=schemas.Trip)
def update_trip_location(trip_id: int, location: schemas.LocationUpdate, db: Session = Depends(get_db)):
    """Update driver's current location for real-time trips"""
    db_trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not db_trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if not db_trip.is_realtime:
        raise HTTPException(status_code=400, detail="Location updates only allowed for real-time trips")
    
    db_trip.current_lat = location.current_lat
    db_trip.current_lng = location.current_lng
    db_trip.last_location_update = datetime.utcnow()
    db.commit()
    db.refresh(db_trip)
    return db_trip

# --- MATCHING & SEARCH ---
@app.get("/match-nearby-passengers/")
def match_passengers(lat: float, lng: float, resort: str, db: Session = Depends(get_db)):
    """Find passengers near driver's route (for real-time trips)"""
    resort_coords = next((r for r in RESORTS_DATA if r["name"] == resort), None)
    if not resort_coords: return []

    # Only match real-time requests (departure_time == "Now" or is_realtime equivalent)
    requests = db.query(RideRequest).filter(
        RideRequest.resort == resort,
        RideRequest.status == "pending",
        RideRequest.departure_time == "Now"  # Only real-time requests
    ).all()

    matches = []
    for req in requests:
        xtd = get_cross_track_distance(lat, lng, resort_coords["lat"], resort_coords["lng"], req.pickup_lat, req.pickup_lng)
        if xtd < 2.0: # Match if within 2km of the route
            matches.append(req)
    return matches

@app.get("/match-nearby-drivers/")
def match_drivers(lat: float, lng: float, resort: str, db: Session = Depends(get_db)):
    """Find active drivers near passenger (for real-time rides)"""
    resort_coords = next((r for r in RESORTS_DATA if r["name"] == resort), None)
    if not resort_coords: return []

    # Get active real-time trips going to the same resort
    trips = db.query(Trip).filter(
        Trip.resort == resort,
        Trip.is_realtime == True,
        Trip.available_seats > 0,
        Trip.current_lat.isnot(None),  # Must have current location
        Trip.current_lng.isnot(None)
    ).all()

    matches = []
    for trip in trips:
        # Use driver's current location if available, otherwise start location
        driver_lat = trip.current_lat if trip.current_lat else trip.start_lat
        driver_lng = trip.current_lng if trip.current_lng else trip.start_lng
        
        if not driver_lat or not driver_lng:
            continue
            
        # Check if passenger is on driver's route
        xtd = get_cross_track_distance(driver_lat, driver_lng, resort_coords["lat"], resort_coords["lng"], lat, lng)
        if xtd < 2.0:  # Within 2km of route
            matches.append({
                "id": trip.id,
                "driver_name": trip.driver_name,
                "current_lat": driver_lat,
                "current_lng": driver_lng,
                "available_seats": trip.available_seats,
                "departure_time": trip.departure_time
            })
    return matches

@app.get("/trips/active")
def get_active_trips(is_realtime: Optional[bool] = None, db: Session = Depends(get_db)):
    """Get all active trips for map display"""
    query = db.query(Trip).filter(Trip.available_seats > 0)
    
    if is_realtime is not None:
        query = query.filter(Trip.is_realtime == is_realtime)
    
    trips = query.all()
    return [
        {
            "id": trip.id,
            "driver_name": trip.driver_name,
            "resort": trip.resort,
            "start_lat": trip.start_lat,
            "start_lng": trip.start_lng,
            "current_lat": trip.current_lat,
            "current_lng": trip.current_lng,
            "available_seats": trip.available_seats,
            "is_realtime": trip.is_realtime,
            "departure_time": trip.departure_time
        }
        for trip in trips
    ]

@app.get("/ride-requests/active")
def get_active_requests(is_realtime: Optional[bool] = None, db: Session = Depends(get_db)):
    """Get all active ride requests for map display"""
    query = db.query(RideRequest).filter(RideRequest.status == "pending")
    
    if is_realtime is not None:
        if is_realtime:
            query = query.filter(RideRequest.departure_time == "Now")
        else:
            query = query.filter(RideRequest.departure_time != "Now")
    
    requests = query.all()
    return [
        {
            "id": req.id,
            "passenger_name": req.passenger_name,
            "resort": req.resort,
            "pickup_lat": req.pickup_lat,
            "pickup_lng": req.pickup_lng,
            "departure_time": req.departure_time,
            "status": req.status
        }
        for req in requests
    ]

def parse_time(time_str: str) -> Optional[int]:
    """Parse time string like '7:00 AM' to minutes since midnight"""
    try:
        if time_str.lower() == "now":
            return None
        time_str = time_str.strip().upper()
        if "AM" in time_str or "PM" in time_str:
            time_part = time_str.replace("AM", "").replace("PM", "").strip()
            hour, minute = map(int, time_part.split(":"))
            if "PM" in time_str and hour != 12:
                hour += 12
            elif "AM" in time_str and hour == 12:
                hour = 0
            return hour * 60 + minute
    except:
        return None
    return None

def time_difference_minutes(time1_str: str, time2_str: str) -> Optional[int]:
    """Calculate absolute difference in minutes between two time strings"""
    t1 = parse_time(time1_str)
    t2 = parse_time(time2_str)
    if t1 is None or t2 is None:
        return None
    return abs(t1 - t2)

@app.get("/get-optimal-hub/")
def get_optimal_hub(p_lat: float, p_lng: float, trip_id: int, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    resort = next(r for r in RESORTS_DATA if r["name"] == trip.resort)
    
    valid_hubs = []
    for hid, hdata in HUBS.items():
        xtd = get_cross_track_distance(trip.start_lat, trip.start_lng, resort["lat"], resort["lng"], hdata["lat"], hdata["lng"])
        if xtd < 1.5:
            dist = haversine(p_lat, p_lng, hdata["lat"], hdata["lng"])
            valid_hubs.append({"id": hid, "name": hdata["name"], "lat": hdata["lat"], "lng": hdata["lng"], "dist": dist})
    
    return sorted(valid_hubs, key=lambda x: x["dist"])[0] if valid_hubs else None

@app.get("/match-scheduled/", response_model=List[schemas.ScheduledMatch])
def match_scheduled_rides(resort: str, target_date: Optional[date] = None, db: Session = Depends(get_db)):
    """
    Match scheduled trips and ride requests for a specific date.
    Optimizes for timing compatibility and closest hub.
    """
    if target_date is None:
        # Default to tomorrow
        target_date = date.today() + timedelta(days=1)
    
    # Get scheduled trips (not real-time) for the target date
    trips = db.query(Trip).filter(
        Trip.resort == resort,
        Trip.is_realtime == False,
        Trip.trip_date == target_date,
        Trip.available_seats > 0
    ).all()
    
    # Get scheduled ride requests for the target date
    requests = db.query(RideRequest).filter(
        RideRequest.resort == resort,
        RideRequest.status == "pending",
        RideRequest.request_date == target_date,
        RideRequest.departure_time != "Now"
    ).all()
    
    if not trips or not requests:
        return []
    
    resort_coords = next((r for r in RESORTS_DATA if r["name"] == resort), None)
    if not resort_coords:
        return []
    
    matches = []
    
    for trip in trips:
        for req in requests:
            # Skip if already matched
            if req.matched_trip_id:
                continue
            
            # Calculate time compatibility (prefer times within 30 minutes)
            time_diff = time_difference_minutes(trip.departure_time, req.departure_time)
            if time_diff is None or time_diff > 60:  # More than 1 hour difference is not ideal
                continue
            
            # Find optimal hub for this match
            valid_hub_ids = RESORT_HUB_MAP.get(resort, [])
            best_hub = None
            best_score = float('inf')
            
            for hub_id in valid_hub_ids:
                if hub_id not in HUBS:
                    continue
                hub = HUBS[hub_id]
                
                # Check if hub is on driver's route
                driver_xtd = get_cross_track_distance(
                    trip.start_lat, trip.start_lng,
                    resort_coords["lat"], resort_coords["lng"],
                    hub["lat"], hub["lng"]
                )
                if driver_xtd > 1.5:  # Hub too far from driver's route
                    continue
                
                # Calculate distances
                dist_driver = haversine(trip.start_lat, trip.start_lng, hub["lat"], hub["lng"])
                dist_passenger = haversine(req.pickup_lat, req.pickup_lng, hub["lat"], hub["lng"])
                
                # Score: total distance + time difference penalty
                # Lower score is better
                score = dist_driver + dist_passenger + (time_diff * 0.1)  # 0.1 km per minute difference
                
                if score < best_score:
                    best_score = score
                    best_hub = {
                        "id": hub_id,
                        "name": hub["name"],
                        "lat": hub["lat"],
                        "lng": hub["lng"],
                        "driver_distance": dist_driver,
                        "passenger_distance": dist_passenger
                    }
            
            if best_hub:
                matches.append(schemas.ScheduledMatch(
                    trip_id=trip.id,
                    request_id=req.id,
                    driver_name=trip.driver_name,
                    passenger_name=req.passenger_name,
                    resort=resort,
                    suggested_hub={
                        "id": best_hub["id"],
                        "name": best_hub["name"],
                        "lat": best_hub["lat"],
                        "lng": best_hub["lng"]
                    },
                    driver_departure_time=trip.departure_time,
                    passenger_departure_time=req.departure_time,
                    hub_distance_driver=best_hub["driver_distance"],
                    hub_distance_passenger=best_hub["passenger_distance"]
                ))
    
    # Sort by best match (lowest total distance + time penalty)
    matches.sort(key=lambda x: x["hub_distance_driver"] + x["hub_distance_passenger"])
    
    return matches[:10]  # Return top 10 matches

@app.post("/match-scheduled/{match_id}/confirm")
def confirm_scheduled_match(match_id: int, db: Session = Depends(get_db)):
    """Confirm a scheduled match and link the trip and request"""
    # This would be called from the match-scheduled results
    # For now, we'll need to pass trip_id and request_id separately
    # This is a placeholder - you may want to store matches first
    pass

# --- RIDE REQUESTS (PASSENGER) ---
@app.post("/ride-requests/", response_model=schemas.RideRequest)
def create_ride_request(req: schemas.RideRequestCreate, db: Session = Depends(get_db)):
    lat, lng = req.lat, req.lng
    if not lat and req.pickup_text:
        loc = geolocator.geocode(f"{req.pickup_text}, Utah")
        if loc: lat, lng = loc.latitude, loc.longitude

    new_req = RideRequest(
        passenger_name=req.passenger_name,
        resort=req.resort,
        pickup_lat=lat,
        pickup_lng=lng,
        departure_time=req.departure_time,
        request_date=req.request_date,
        status="pending"
    )
    db.add(new_req)
    db.commit()
    db.refresh(new_req)
    return new_req

@app.patch("/ride-requests/{request_id}", response_model=schemas.RideRequest)
def update_ride_request(request_id: int, updates: schemas.RideRequestUpdate, db: Session = Depends(get_db)):
    """Update a ride request (e.g., to confirm a match)"""
    db_request = db.query(RideRequest).filter(RideRequest.id == request_id).first()
    if not db_request:
        raise HTTPException(status_code=404, detail="Ride request not found")
    
    update_data = updates.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if hasattr(db_request, key):
            setattr(db_request, key, value)
    
    db.commit()
    db.refresh(db_request)
    return db_request