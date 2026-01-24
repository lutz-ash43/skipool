from fastapi import FastAPI, Query, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text, inspect
from typing import List, Optional, Tuple
import math
from datetime import datetime, date, timedelta
from geopy.geocoders import Nominatim

# Database & Models
from database import engine, get_db, Base
from models import Trip, RideRequest
import schemas

Base.metadata.create_all(bind=engine)

app = FastAPI()
geolocator = Nominatim(user_agent="skipool_app", timeout=10)  # 10 second timeout


def _geocode_address(raw: str) -> Tuple[Optional[float], Optional[float]]:
    """Try to geocode an address. Tries several query formats. Returns (lat, lng) or (None, None)."""
    s = (raw or "").strip()
    if not s:
        return None, None
    queries = [
        f"{s}, Utah",
        s,
        f"{s}, Utah, USA",
    ]
    for q in queries:
        try:
            loc = geolocator.geocode(q, timeout=10)
            if loc and loc.latitude is not None and loc.longitude is not None:
                return float(loc.latitude), float(loc.longitude)
        except Exception:
            continue
    return None, None


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

@app.get("/health/db")
def check_database_health(db: Session = Depends(get_db)):
    """Test database connection and return status"""
    try:
        # Test 1: Simple query to check connection
        result = db.execute(text("SELECT 1 as test"))
        test_value = result.scalar()
        
        # Test 2: Check if tables exist
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        # Test 3: Try a simple query on trips table (if exists)
        trips_count = None
        requests_count = None
        if 'trips' in tables:
            trips_count = db.query(Trip).count()
        if 'ride_requests' in tables:
            requests_count = db.query(RideRequest).count()
        
        return {
            "status": "healthy",
            "database_connected": True,
            "test_query": test_value == 1,
            "tables_found": tables,
            "trips_count": trips_count,
            "ride_requests_count": requests_count,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database_connected": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "timestamp": datetime.utcnow().isoformat()
        }

# --- TRIP ENDPOINTS (DRIVER) ---
@app.post("/trips/", response_model=schemas.Trip)
def create_trip(trip: schemas.TripCreate, db: Session = Depends(get_db)):
    is_scheduled = not trip.is_realtime
    lat, lng = trip.current_lat, trip.current_lng
    
    # Geocode if text address provided (overrides current_lat/lng when manual)
    if (trip.start_location_text or "").strip():
        glat, glng = _geocode_address(trip.start_location_text)
        if glat is not None and glng is not None:
            lat, lng = glat, glng
    
    # For scheduled rides: location is REQUIRED for optimal hub matching
    # For Ride Now: location is preferred but can use current location later
    if not lat or not lng:
        if is_scheduled:
            msg = "Starting location is required. Use the 📍 button for GPS, or enter an address like 'Sugar House, Salt Lake City' or 'Park City, UT'."
            if (trip.start_location_text or "").strip():
                msg = "We couldn't find that address. Try adding city/state (e.g. 'Sugar House, Salt Lake City') or use the 📍 button for GPS."
            raise HTTPException(status_code=400, detail=msg)
        # For Ride Now, we can proceed without start location (will use current location)
        lat, lng = None, None
    
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
def match_passengers(trip_id: int, resort: str, db: Session = Depends(get_db)):
    """Find passengers near driver's current route (for real-time trips)
    
    Uses driver's current location from the trip to find passengers along their route.
    """
    # Get the driver's trip and current location
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if not trip.is_realtime:
        raise HTTPException(status_code=400, detail="This endpoint is only for real-time trips")
    
    # Use driver's current location (updated as they drive), fallback to start location
    driver_lat = trip.current_lat if trip.current_lat else trip.start_lat
    driver_lng = trip.current_lng if trip.current_lng else trip.start_lng
    
    if not driver_lat or not driver_lng:
        return []  # No location available
    
    resort_coords = next((r for r in RESORTS_DATA if r["name"] == resort), None)
    if not resort_coords: 
        return []

    # Only match real-time requests (departure_time == "Now")
    requests = db.query(RideRequest).filter(
        RideRequest.resort == resort,
        RideRequest.status == "pending",
        RideRequest.departure_time == "Now"  # Only real-time requests
    ).all()

    matches = []
    for req in requests:
        # Use passenger's current location if available (they're moving), otherwise pickup location
        passenger_lat = req.current_lat if req.current_lat else req.pickup_lat
        passenger_lng = req.current_lng if req.current_lng else req.pickup_lng
        
        if not passenger_lat or not passenger_lng:
            continue
            
        # Check if passenger is on driver's route using driver's CURRENT location
        xtd = get_cross_track_distance(
            driver_lat, driver_lng, 
            resort_coords["lat"], resort_coords["lng"], 
            passenger_lat, passenger_lng
        )
        if xtd < 2.0:  # Match if within 2km of the route
            matches.append(req)
    return matches

@app.get("/match-nearby-drivers/")
def match_drivers(request_id: int, resort: str, db: Session = Depends(get_db)):
    """Find active drivers near passenger's current location (for real-time rides)
    
    Uses passenger's current location from the request to find drivers who will pass them.
    """
    # Get the passenger's request and current location
    request = db.query(RideRequest).filter(RideRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Ride request not found")
    if request.departure_time != "Now":
        raise HTTPException(status_code=400, detail="This endpoint is only for real-time ride requests")
    
    # Use passenger's current location (updated as they move), fallback to pickup location
    passenger_lat = request.current_lat if request.current_lat else request.pickup_lat
    passenger_lng = request.current_lng if request.current_lng else request.pickup_lng
    
    if not passenger_lat or not passenger_lng:
        return []  # No location available
    
    resort_coords = next((r for r in RESORTS_DATA if r["name"] == resort), None)
    if not resort_coords: 
        return []

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
        # Use driver's current location (updated as they drive)
        driver_lat = trip.current_lat
        driver_lng = trip.current_lng
        
        if not driver_lat or not driver_lng:
            continue
            
        # Check if passenger's CURRENT location is on driver's route
        xtd = get_cross_track_distance(
            driver_lat, driver_lng, 
            resort_coords["lat"], resort_coords["lng"], 
            passenger_lat, passenger_lng
        )
        if xtd < 2.0:  # Within 2km of route
            matches.append({
                "id": trip.id,
                "driver_name": trip.driver_name,
                "current_lat": driver_lat,
                "current_lng": driver_lng,
                "start_lat": trip.start_lat,  # For fallback
                "start_lng": trip.start_lng,  # For fallback
                "available_seats": trip.available_seats,
                "departure_time": trip.departure_time,
                "resort": trip.resort
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
            "current_lat": req.current_lat,
            "current_lng": req.current_lng,
            "departure_time": req.departure_time,
            "status": req.status
        }
        for req in requests
    ]

def parse_time(time_str: str) -> Optional[int]:
    """Parse time string like '7:00 AM' or '7:00AM' to minutes since midnight"""
    if not time_str or not isinstance(time_str, str):
        return None
    try:
        s = time_str.strip().upper()
        if s == "NOW":
            return None
        if "AM" not in s and "PM" not in s:
            return None
        time_part = s.replace("AM", "").replace("PM", "").strip()
        parts = time_part.split(":")
        if len(parts) < 2:
            return None
        hour = int(parts[0].strip())
        minute = int(parts[1].strip())
        if "PM" in s and hour != 12:
            hour += 12
        elif "AM" in s and hour == 12:
            hour = 0
        return hour * 60 + minute
    except (ValueError, AttributeError):
        return None

def time_difference_minutes(time1_str: str, time2_str: str) -> Optional[int]:
    """Calculate absolute difference in minutes between two time strings"""
    t1 = parse_time(time1_str)
    t2 = parse_time(time2_str)
    if t1 is None or t2 is None:
        return None
    return abs(t1 - t2)

def _normalize_date(d) -> Optional[date]:
    """Normalize DB value to date for comparison. Handles date, datetime, 'YYYY-MM-DD' string."""
    if d is None:
        return None
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, date):
        return d
    if isinstance(d, str) and len(d) >= 10:
        try:
            return datetime.strptime(d[:10], "%Y-%m-%d").date()
        except ValueError:
            pass
    if hasattr(d, "date") and callable(getattr(d, "date", None)):
        out = d.date()
        return out if isinstance(out, date) else None
    return None

def _date_eq(d, target: date) -> bool:
    n = _normalize_date(d)
    return n is not None and n == target

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
        Trip.available_seats > 0
    ).all()
    trips = [t for t in trips if _date_eq(t.trip_date, target_date)]
    
    # Get scheduled ride requests for the target date
    requests = db.query(RideRequest).filter(
        RideRequest.resort == resort,
        RideRequest.status == "pending",
        RideRequest.departure_time != "Now"
    ).all()
    requests = [r for r in requests if _date_eq(r.request_date, target_date)]
    
    if not trips or not requests:
        return []
    
    resort_coords = next((r for r in RESORTS_DATA if r["name"] == resort), None)
    if not resort_coords:
        return []
    
    matches = []
    
    for trip in trips:
        for req in requests:
            if req.matched_trip_id:
                continue
            
            time_diff = time_difference_minutes(trip.departure_time, req.departure_time)
            if time_diff is None or time_diff > 60:
                continue
            
            # Need coords for hub search or fallback; skip if missing
            if trip.start_lat is None or trip.start_lng is None or req.pickup_lat is None or req.pickup_lng is None:
                continue
            
            valid_hub_ids = RESORT_HUB_MAP.get(resort, [])
            best_hub = None
            best_score = float('inf')
            HUB_ROUTE_KM = 5.0

            for hub_id in valid_hub_ids:
                if hub_id not in HUBS:
                    continue
                hub = HUBS[hub_id]
                driver_xtd = get_cross_track_distance(
                    trip.start_lat, trip.start_lng,
                    resort_coords["lat"], resort_coords["lng"],
                    hub["lat"], hub["lng"]
                )
                if driver_xtd > HUB_ROUTE_KM:
                    continue
                dist_driver = haversine(trip.start_lat, trip.start_lng, hub["lat"], hub["lng"])
                dist_passenger = haversine(req.pickup_lat, req.pickup_lng, hub["lat"], hub["lng"])
                score = dist_driver + dist_passenger + (time_diff * 0.1)
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

            # Fallback: use "Meet at driver's start" when we have coords (use "is not None" so 0.0 is valid)
            if not best_hub and trip.start_lat is not None and trip.start_lng is not None and req.pickup_lat is not None and req.pickup_lng is not None:
                dist_driver = 0.0
                dist_passenger = haversine(req.pickup_lat, req.pickup_lng, trip.start_lat, trip.start_lng)
                best_hub = {
                    "id": "driver_start",
                    "name": "Meet at driver's start",
                    "lat": trip.start_lat,
                    "lng": trip.start_lng,
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
    matches.sort(key=lambda x: x.hub_distance_driver + x.hub_distance_passenger)
    
    return matches[:10]  # Return top 10 matches

@app.get("/match-scheduled/debug")
def match_scheduled_debug(resort: str, target_date: Optional[date] = None, db: Session = Depends(get_db)):
    """Debug why match-scheduled returns no matches. Use same resort & target_date as match-scheduled."""
    if target_date is None:
        target_date = date.today() + timedelta(days=1)
    
    trips = db.query(Trip).filter(
        Trip.resort == resort,
        Trip.is_realtime == False,
        Trip.available_seats > 0
    ).all()
    trips = [t for t in trips if _date_eq(t.trip_date, target_date)]
    
    requests = db.query(RideRequest).filter(
        RideRequest.resort == resort,
        RideRequest.status == "pending",
        RideRequest.departure_time != "Now"
    ).all()
    requests = [r for r in requests if _date_eq(r.request_date, target_date)]
    
    def _t(t):
        return {
            "id": t.id,
            "departure_time": t.departure_time,
            "trip_date": str(t.trip_date),
            "trip_date_normalized": str(_normalize_date(t.trip_date) or ""),
            "start_lat": t.start_lat,
            "start_lng": t.start_lng,
        }
    def _r(r):
        return {
            "id": r.id,
            "departure_time": r.departure_time,
            "request_date": str(r.request_date),
            "request_date_normalized": str(_normalize_date(r.request_date) or ""),
            "pickup_lat": r.pickup_lat,
            "pickup_lng": r.pickup_lng,
        }
    
    skip_time = skip_coords = skip_matched = would_match = 0
    for t in trips:
        for r in requests:
            if r.matched_trip_id:
                skip_matched += 1
                continue
            td = time_difference_minutes(t.departure_time, r.departure_time)
            if td is None or td > 60:
                skip_time += 1
                continue
            if t.start_lat is None or t.start_lng is None or r.pickup_lat is None or r.pickup_lng is None:
                skip_coords += 1
                continue
            would_match += 1
    
    return {
        "target_date": str(target_date),
        "resort": resort,
        "trips_count": len(trips),
        "requests_count": len(requests),
        "pairs_with_time_ok": would_match + skip_coords,
        "pairs_would_match": would_match,
        "skip_time": skip_time,
        "skip_coords": skip_coords,
        "skip_matched": skip_matched,
        "trips_sample": [_t(t) for t in trips[:5]],
        "requests_sample": [_r(r) for r in requests[:5]],
    }

@app.post("/match-scheduled/{match_id}/confirm")
def confirm_scheduled_match(match_id: int, db: Session = Depends(get_db)):
    """Confirm a scheduled match and link the trip and request"""
    pass

# --- RIDE REQUESTS (PASSENGER) ---
@app.post("/ride-requests/", response_model=schemas.RideRequest)
def create_ride_request(req: schemas.RideRequestCreate, db: Session = Depends(get_db)):
    lat, lng = req.lat, req.lng
    is_scheduled = (req.departure_time or "").strip().lower() != "now"

    # Geocode if text address provided and no lat/lng
    pickup_text = (req.pickup_text or "").strip()
    if (not lat or not lng) and pickup_text:
        glat, glng = _geocode_address(req.pickup_text)
        if glat is not None and glng is not None:
            lat, lng = glat, glng

    # For scheduled rides: location is REQUIRED for optimal hub matching
    # For Ride Now: location is REQUIRED for real-time matching
    if not lat or not lng:
        if pickup_text:
            raise HTTPException(
                status_code=400,
                detail="We couldn't find that address. Try adding city/state (e.g. 'Sugar House, Salt Lake City' or 'Park City, UT') or use the 📍 button for GPS."
            )
        if is_scheduled:
            raise HTTPException(
                status_code=400,
                detail="Pickup location is required. Enter an address (e.g. 'Sugar House, Salt Lake City') or use the 📍 button for GPS."
            )
        raise HTTPException(
            status_code=400,
            detail="Pickup location is required. Use the 📍 button for GPS or enter a valid address."
        )

    # Initialize current location for real-time requests
    current_lat, current_lng = req.lat, req.lng
    is_realtime = (req.departure_time or "").strip().lower() == "now"
    if is_realtime and current_lat and current_lng:
        # For real-time requests, current location starts as pickup location
        pass
    else:
        current_lat, current_lng = None, None
    
    new_req = RideRequest(
        passenger_name=req.passenger_name,
        resort=req.resort,
        pickup_lat=lat,
        pickup_lng=lng,
        current_lat=current_lat,
        current_lng=current_lng,
        last_location_update=datetime.utcnow() if is_realtime and current_lat else None,
        departure_time=req.departure_time,
        request_date=req.request_date,
        status="pending"
    )
    db.add(new_req)
    db.commit()
    db.refresh(new_req)
    return new_req

@app.put("/ride-requests/{request_id}/location", response_model=schemas.RideRequest)
def update_ride_request_location(request_id: int, location: schemas.LocationUpdate, db: Session = Depends(get_db)):
    """Update passenger's current location for real-time ride requests"""
    db_request = db.query(RideRequest).filter(RideRequest.id == request_id).first()
    if not db_request:
        raise HTTPException(status_code=404, detail="Ride request not found")
    if db_request.departure_time != "Now":
        raise HTTPException(status_code=400, detail="Location updates only allowed for real-time ride requests")
    
    db_request.current_lat = location.current_lat
    db_request.current_lng = location.current_lng
    db_request.last_location_update = datetime.utcnow()
    db.commit()
    db.refresh(db_request)
    return db_request

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