from fastapi import FastAPI, Query, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text, inspect, func
from typing import List, Optional, Tuple
import math
import time
from datetime import datetime, date, timedelta
from geopy.geocoders import Nominatim
import httpx

# Database & Models
from database import engine, get_db, Base, verify_connection
from models import Trip, RideRequest
import schemas
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Tables are managed by migrations / existing DB; no create_all at startup (Cloud Run has no DB on 127.0.0.1 at import time)

app = FastAPI()
geolocator = Nominatim(user_agent="skipool_app", timeout=5)  # 5 second timeout (reduced for local dev)

# CORS: allow simulator, localhost, and common dev origins so requests don't stall on preflight
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Verify database connection on startup before serving traffic."""
    logger.info("=" * 60)
    logger.info("SkiPool API Starting Up")
    logger.info("=" * 60)
    
    try:
        logger.info("Verifying database connection...")
        verify_connection(engine)
        logger.info("✅ Database connection verified - ready to serve traffic")
        logger.info("=" * 60)
    except Exception as e:
        logger.error("=" * 60)
        logger.error("❌ STARTUP FAILED: Database connection could not be established")
        logger.error(f"Error: {e}")
        logger.error("=" * 60)
        logger.error("\n⚠️  The application will not function correctly without a database connection.")
        logger.error("Please fix the connection issue and restart the application.\n")
        # Don't raise - let the app start but log the error prominently
        # This allows health checks to work even if DB is temporarily down


def _is_departure_now(val) -> bool:
    """True if departure_time means 'Ride Now' (case-insensitive, null-safe)."""
    if val is None:
        return False
    return (str(val).strip().lower() == "now")


def _geocode_address(raw: str) -> Tuple[Optional[float], Optional[float]]:
    """Try to geocode an address. Tries several query formats. Returns (lat, lng) or (None, None)."""
    s = (raw or "").strip()
    if not s:
        return None, None
    
    logger.info(f"🗺️  Geocoding address: '{s}'")
    queries = [
        f"{s}, Utah",
        s,
        f"{s}, Utah, USA",
    ]
    for i, q in enumerate(queries, 1):
        try:
            logger.debug(f"Attempt {i}/3: geocoding '{q}'")
            loc = geolocator.geocode(q, timeout=5)  # Reduced from 10 to 5 seconds
            if loc and loc.latitude is not None and loc.longitude is not None:
                logger.info(f"✅ Geocoded '{s}' -> ({loc.latitude}, {loc.longitude})")
                return float(loc.latitude), float(loc.longitude)
        except Exception as e:
            logger.warning(f"Geocoding attempt {i} failed: {type(e).__name__}")
            continue
    
    logger.warning(f"❌ Could not geocode address: '{s}'")
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
    "h1": {
        "name": "Historic Sandy Station",
        "lat": 40.5897,
        "lng": -111.8856,
        "address": "8662 S. 255 E., Sandy, UT 84070",
        "transit": True,
        "bus_routes": ["UTA TRAX Red Line", "UTA 953 (Ski Bus)"],
        "description": "UTA TRAX station with ski bus connections"
    },
    "h2": {
        "name": "9400 S. Highland Dr.",
        "lat": 40.5815,
        "lng": -111.8085,
        "address": "9400 S. Highland Dr., Sandy, UT 84092",
        "transit": True,
        "bus_routes": ["UTA 953 (Ski Bus)"],
        "description": "UTA Park & Ride with ski bus service"
    },
    "h3": {
        "name": "Midvale Fort Union Station",
        "lat": 40.6192,
        "lng": -111.8983,
        "address": "7200 S. 1300 E., Midvale, UT 84047",
        "transit": True,
        "bus_routes": ["UTA TRAX Red Line", "UTA 953 (Ski Bus)"],
        "description": "UTA TRAX station with ski bus connections"
    },
    "h4": {
        "name": "6200 S. Wasatch Blvd. (Swamp Lot)",
        "lat": 40.6375,
        "lng": -111.7997,
        "address": "6200 S. Wasatch Blvd., Salt Lake City, UT 84121",
        "transit": True,
        "bus_routes": ["UTA 953 (Ski Bus)", "UTA 994 (Ski Bus)"],
        "description": "Popular ski bus pickup location"
    },
    "h5": {
        "name": "Big Cottonwood Canyon P&R",
        "lat": 40.6194,
        "lng": -111.7870,
        "address": "6450 S. Wasatch Blvd., Salt Lake City, UT 84121",
        "transit": True,
        "bus_routes": ["UTA 953 (Ski Bus)", "UTA 994 (Ski Bus)"],
        "description": "UTA Park & Ride at canyon entrance"
    },
    "h6": {
        "name": "Richardson Flat",
        "lat": 40.6711,
        "lng": -111.4496,
        "address": "Richardson Flat Rd., Park City, UT 84098",
        "transit": True,
        "bus_routes": ["Park City Transit"],
        "description": "Park & Ride with free Park City Transit"
    },
    "h7": {
        "name": "Ecker Hill P&R",
        "lat": 40.7461,
        "lng": -111.5734,
        "address": "I-80 Exit 146, Park City, UT 84098",
        "transit": True,
        "bus_routes": ["Park City Transit"],
        "description": "Park & Ride with free Park City Transit"
    },
    "h8": {
        "name": "Kimball Junction Transit Center",
        "lat": 40.7241,
        "lng": -111.5467,
        "address": "1751 Sidewinder Dr., Park City, UT 84060",
        "transit": True,
        "bus_routes": ["Park City Transit", "UTA 902"],
        "description": "Major transit hub with multiple bus routes"
    },
    "h9": {
        "name": "Park City High School",
        "lat": 40.6587,
        "lng": -111.5034,
        "address": "1752 Kearns Blvd., Park City, UT 84060",
        "transit": True,
        "bus_routes": ["Park City Transit"],
        "description": "Park & Ride with free Park City Transit"
    },
    "h10": {
        "name": "Jeremy Ranch P&R",
        "lat": 40.7589,
        "lng": -111.5761,
        "address": "I-80 Exit 141, Park City, UT 84098",
        "transit": True,
        "bus_routes": ["Park City Transit"],
        "description": "Park & Ride with free Park City Transit"
    }
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

# Ride Now: max cross-track distance (km) for "on route" — canyon roads curve so 2km was too strict
RIDE_NOW_ROUTE_KM = 8.0

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

def is_ahead_on_route(driver_lat, driver_lng, resort_lat, resort_lng, point_lat, point_lng) -> bool:
    """True if point projects onto the driver->resort segment (not behind driver or past resort).
    Uses along-track projection to ensure passenger is between driver and resort."""
    # Calculate direction vector from driver to resort
    dx = math.radians(resort_lng - driver_lng) * math.cos(math.radians((driver_lat + resort_lat) / 2))
    dy = math.radians(resort_lat - driver_lat)
    
    # Calculate direction vector from driver to point
    px = math.radians(point_lng - driver_lng) * math.cos(math.radians((driver_lat + point_lat) / 2))
    py = math.radians(point_lat - driver_lat)
    
    # Project point onto driver->resort line segment
    dot = px * dx + py * dy
    seg_len_sq = dx * dx + dy * dy
    
    if seg_len_sq == 0:
        return False
    
    # Parameter t: 0 = at driver, 1 = at resort
    t = dot / seg_len_sq
    
    # Only match if passenger is between driver and resort (0 <= t <= 1)
    return 0.0 <= t <= 1.0

# --- ROOT & HEALTH ---
@app.get("/")
def root():
    """Root endpoint - API info and links."""
    return {
        "name": "SkiPool API",
        "docs": "/docs",
        "health": "/health",
        "health_db": "/health/db",
        "resorts": "/resorts/",
    }


@app.get("/health")
def health():
    """Simple health check (no DB)."""
    return {"status": "ok"}


# --- UTILITY ENDPOINTS ---
@app.get("/resorts/")
def get_resorts():
    return [r["name"] for r in RESORTS_DATA]

@app.get("/hubs-for-resort/")
def get_hubs_for_resort(resort: str):
    allowed_ids = RESORT_HUB_MAP.get(resort, [])
    return {hid: HUBS[hid] for hid in allowed_ids if hid in HUBS}

@app.get("/hubs-for-match/")
def get_hubs_for_match(trip_id: int, request_id: int, db: Session = Depends(get_db)):
    """Get all valid hubs for a specific trip-request match pair, scored by distance.
    Allows passenger to see all options and choose if auto-selected hub doesn't work."""
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    request = db.query(RideRequest).filter(RideRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Ride request not found")
    
    if not trip.start_lat or not trip.start_lng or not request.pickup_lat or not request.pickup_lng:
        raise HTTPException(status_code=400, detail="Missing location data for trip or request")
    
    resort_coords = next((r for r in RESORTS_DATA if r["name"] == trip.resort), None)
    if not resort_coords:
        raise HTTPException(status_code=404, detail="Resort not found")
    
    valid_hub_ids = RESORT_HUB_MAP.get(trip.resort, [])
    HUB_ROUTE_KM = 5.0
    scored_hubs = []
    
    # Score all valid hubs for this resort
    for hub_id in valid_hub_ids:
        if hub_id not in HUBS:
            continue
        hub = HUBS[hub_id]
        
        # Check if hub is within 5km cross-track of driver's route
        driver_xtd = get_cross_track_distance(
            trip.start_lat, trip.start_lng,
            resort_coords["lat"], resort_coords["lng"],
            hub["lat"], hub["lng"]
        )
        
        if driver_xtd > HUB_ROUTE_KM:
            continue
        
        # Calculate distances
        dist_driver = haversine(trip.start_lat, trip.start_lng, hub["lat"], hub["lng"])
        dist_passenger = haversine(request.pickup_lat, request.pickup_lng, hub["lat"], hub["lng"])
        
        # Parse departure times for time difference
        time_diff = time_difference_minutes(trip.departure_time or "", request.departure_time or "")
        if time_diff is None:
            time_diff = 0
        
        # Score: lower is better (distance + small time factor)
        score = dist_driver + dist_passenger + (time_diff * 0.1)
        
        scored_hubs.append({
            "id": hub_id,
            "name": hub["name"],
            "lat": hub["lat"],
            "lng": hub["lng"],
            "address": hub.get("address", ""),
            "transit": hub.get("transit", False),
            "bus_routes": hub.get("bus_routes", []),
            "description": hub.get("description", ""),
            "driver_distance_km": round(dist_driver, 2),
            "passenger_distance_km": round(dist_passenger, 2),
            "total_distance_km": round(dist_driver + dist_passenger, 2),
            "score": round(score, 2)
        })
    
    # Include driver's start location as fallback option
    if trip.start_lat and trip.start_lng:
        dist_passenger = haversine(request.pickup_lat, request.pickup_lng, trip.start_lat, trip.start_lng)
        scored_hubs.append({
            "id": "driver_start",
            "name": "Meet at driver's start",
            "lat": trip.start_lat,
            "lng": trip.start_lng,
            "address": trip.start_location_text or "Driver's starting location",
            "transit": False,
            "bus_routes": [],
            "description": "Meet at the driver's starting location (no return transit available)",
            "driver_distance_km": 0.0,
            "passenger_distance_km": round(dist_passenger, 2),
            "total_distance_km": round(dist_passenger, 2),
            "score": round(dist_passenger, 2)
        })
    
    # Sort by score (lower is better)
    scored_hubs.sort(key=lambda x: x["score"])
    
    return {
        "trip_id": trip_id,
        "request_id": request_id,
        "resort": trip.resort,
        "hubs": scored_hubs
    }

@app.get("/health/schema")
def check_database_schema(db: Session = Depends(get_db)):
    """Return actual column names for trips and ride_requests. Use this to verify migrations applied."""
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        schema = {}
        for table in ("trips", "ride_requests"):
            if table in tables:
                schema[table] = [c["name"] for c in inspector.get_columns(table)]
            else:
                schema[table] = None
        return {
            "status": "ok",
            "tables": schema,
            "ride_requests_has_picked_up_at": (
                "ride_requests" in schema and schema["ride_requests"] is not None
                and "picked_up_at" in schema["ride_requests"]
            ),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


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

# --- PUSH NOTIFICATION HELPERS ---
async def send_expo_push_notification(push_token: str, title: str, body: str, data: dict = None):
    """Send a push notification via Expo's push service"""
    if not push_token or not push_token.startswith('ExponentPushToken'):
        logger.warning(f"Invalid push token format: {push_token}")
        return False
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                'https://exp.host/--/api/v2/push/send',
                json={
                    'to': push_token,
                    'sound': 'default',
                    'title': title,
                    'body': body,
                    'data': data or {},
                },
                headers={'Content-Type': 'application/json'},
                timeout=10.0
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('data', {}).get('status') == 'ok':
                    logger.info(f"Push notification sent successfully to {push_token[:20]}...")
                    return True
                else:
                    logger.warning(f"Push notification failed: {result}")
                    return False
            else:
                logger.error(f"Expo push API error: {response.status_code} - {response.text}")
                return False
    except Exception as e:
        logger.error(f"Error sending push notification: {e}")
        return False

# --- PUSH NOTIFICATION ENDPOINTS ---
@app.post("/register-push-token")
def register_push_token(
    token: str,
    trip_id: Optional[int] = None,
    request_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Register an Expo push token for a trip or ride request"""
    if not token:
        raise HTTPException(status_code=400, detail="Push token is required")
    
    if not trip_id and not request_id:
        raise HTTPException(status_code=400, detail="Either trip_id or request_id must be provided")
    
    try:
        if trip_id:
            trip = db.query(Trip).filter(Trip.id == trip_id).first()
            if not trip:
                raise HTTPException(status_code=404, detail="Trip not found")
            trip.push_token = token
            logger.info(f"Registered push token for trip {trip_id}")
        
        if request_id:
            request = db.query(RideRequest).filter(RideRequest.id == request_id).first()
            if not request:
                raise HTTPException(status_code=404, detail="Ride request not found")
            request.push_token = token
            logger.info(f"Registered push token for request {request_id}")
        
        db.commit()
        return {"success": True, "message": "Push token registered"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering push token: {e}")
        raise HTTPException(status_code=500, detail="Failed to register push token")

# --- TRIP ENDPOINTS (DRIVER) ---
@app.post("/trips/", response_model=schemas.Trip)
def create_trip(trip: schemas.TripCreate, db: Session = Depends(get_db)):
    t0 = time.perf_counter()
    logger.info(f"📥 POST /trips/ received (driver={getattr(trip, 'driver_name', '?')}, resort={getattr(trip, 'resort', '?')}, has_lat_lng={trip.current_lat is not None and trip.current_lng is not None})")
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
    elapsed = time.perf_counter() - t0
    logger.info(f"✅ POST /trips/ completed in {elapsed:.2f}s (trip_id={new_trip.id})")
    return new_trip

@app.get("/trips/{trip_id}", response_model=schemas.Trip)
def get_trip(trip_id: int, db: Session = Depends(get_db)):
    """Get a trip by ID"""
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    return trip

@app.patch("/trips/{trip_id}")
def update_trip(trip_id: int, updates: dict, db: Session = Depends(get_db)):
    """Update trip fields. Used for testing/debugging."""
    db_trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not db_trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    # Only allow safe fields to be updated
    allowed_fields = {'is_realtime', 'status', 'available_seats'}
    for key, value in updates.items():
        if key in allowed_fields and hasattr(db_trip, key):
            setattr(db_trip, key, value)
    
    db.commit()
    db.refresh(db_trip)
    return {"message": "Trip updated", "trip_id": trip_id}

@app.delete("/trips/{trip_id}")
def delete_trip(trip_id: int, db: Session = Depends(get_db)):
    db_trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not db_trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    # Clear any ride_requests that reference this trip (foreign key constraint)
    db.query(RideRequest).filter(RideRequest.matched_trip_id == trip_id).update(
        {"matched_trip_id": None},
        synchronize_session=False
    )
    
    db.delete(db_trip)
    db.commit()
    return {"message": "Trip deleted successfully"}

@app.delete("/ride-requests/{request_id}")
def delete_ride_request(request_id: int, db: Session = Depends(get_db)):
    db_request = db.query(RideRequest).filter(RideRequest.id == request_id).first()
    if not db_request:
        raise HTTPException(status_code=404, detail="Ride request not found")
    
    db.delete(db_request)
    db.commit()
    return {"message": "Ride request deleted successfully"}

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

@app.post("/ride-requests/{request_id}/accept-driver")
def accept_driver_match(request_id: int, trip_id: int = Query(...), db: Session = Depends(get_db)):
    """Accept a driver match for Ride Now - links passenger to driver"""
    request = db.query(RideRequest).filter(RideRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Ride request not found")
    if not _is_departure_now(request.departure_time):
        raise HTTPException(status_code=400, detail="This endpoint is only for real-time ride requests")
    
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if not trip.is_realtime:
        raise HTTPException(status_code=400, detail="This endpoint is only for real-time trips")
    if trip.available_seats <= 0:
        raise HTTPException(status_code=400, detail="No available seats")
    
    request.matched_trip_id = trip_id
    request.status = "matched"
    trip.status = "matched"
    trip.available_seats -= 1
    db.commit()
    db.refresh(request)
    db.refresh(trip)
    return {"message": "Match accepted", "matched_trip_id": trip_id, "remaining_seats": trip.available_seats}

@app.get("/ride-requests/{request_id}/matched-driver")
def get_matched_driver_location(request_id: int, db: Session = Depends(get_db)):
    """Get the matched driver's current location for a passenger"""
    request = db.query(RideRequest).filter(RideRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Ride request not found")
    if not request.matched_trip_id:
        return {"matched": False}
    
    trip = db.query(Trip).filter(Trip.id == request.matched_trip_id).first()
    if not trip:
        return {"matched": False}
    
    return {
        "matched": True,
        "driver_name": trip.driver_name,
        "current_lat": trip.current_lat,
        "current_lng": trip.current_lng,
        "start_lat": trip.start_lat,
        "start_lng": trip.start_lng,
        "last_location_update": trip.last_location_update.isoformat() if trip.last_location_update else None
    }

@app.post("/trips/{trip_id}/accept-passenger")
def accept_passenger_match(trip_id: int, request_id: int = Query(...), db: Session = Depends(get_db)):
    """Accept a passenger match for Ride Now - links driver to passenger"""
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if not trip.is_realtime:
        raise HTTPException(status_code=400, detail="This endpoint is only for real-time trips")
    if trip.available_seats <= 0:
        raise HTTPException(status_code=400, detail="No available seats")
    
    request = db.query(RideRequest).filter(RideRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Ride request not found")
    if not _is_departure_now(request.departure_time):
        raise HTTPException(status_code=400, detail="This endpoint is only for real-time ride requests")
    
    request.matched_trip_id = trip_id
    request.status = "matched"
    trip.status = "matched"
    trip.available_seats -= 1
    db.commit()
    db.refresh(request)
    db.refresh(trip)
    return {"message": "Match accepted", "matched_request_id": request_id, "remaining_seats": trip.available_seats}

@app.get("/trips/{trip_id}/matched-passenger")
def get_matched_passenger_location(trip_id: int, db: Session = Depends(get_db)):
    """Get the matched passenger's current location for a driver.
    
    Returns passenger navigation target (pickup for Ride Now, hub/current for scheduled),
    plus distance_km and near_pickup flag to trigger pickup confirmation prompt.
    """
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    request = db.query(RideRequest).filter(
        RideRequest.matched_trip_id == trip_id,
        RideRequest.status == "matched"
    ).first()
    
    if not request:
        return {"matched": False}
    
    # Ride Now: passenger is at pickup. Driver navigates to pickup (no tracking).
    # Scheduled en-route: we use current_lat/lng if updated, else pickup.
    use_pickup = _is_departure_now(request.departure_time)
    nav_lat = request.pickup_lat if use_pickup else (request.current_lat or request.pickup_lat)
    nav_lng = request.pickup_lng if use_pickup else (request.current_lng or request.pickup_lng)
    
    # Calculate driver distance to pickup/nav target for proximity notifications
    distance_km = None
    near_pickup = False
    
    # Get driver's current position (use current if available, else start)
    driver_lat = trip.current_lat if trip.current_lat else trip.start_lat
    driver_lng = trip.current_lng if trip.current_lng else trip.start_lng
    
    if driver_lat and driver_lng and nav_lat and nav_lng:
        distance_km = haversine(driver_lat, driver_lng, nav_lat, nav_lng)
        # Within 500m (0.5 km) - show pickup confirmation prompt; stays active until driver confirms
        near_pickup = distance_km < 0.5
    
    return {
        "matched": True,
        "passenger_name": request.passenger_name,
        "current_lat": nav_lat,
        "current_lng": nav_lng,
        "pickup_lat": request.pickup_lat,
        "pickup_lng": request.pickup_lng,
        "last_location_update": request.last_location_update.isoformat() if request.last_location_update else None,
        "distance_km": round(distance_km, 2) if distance_km is not None else None,
        "near_pickup": near_pickup
    }

@app.get("/trips/{trip_id}/scheduled-match")
def get_scheduled_match_driver(trip_id: int, db: Session = Depends(get_db)):
    """Get confirmed scheduled match + meeting hub for a driver (en-route screen)."""
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip or trip.is_realtime:
        return {"matched": False}
    request = db.query(RideRequest).filter(
        RideRequest.matched_trip_id == trip_id,
        RideRequest.status == "matched"
    ).first()
    if not request or not request.suggested_hub_id:
        return {"matched": False}
    if request.suggested_hub_id == "driver_start" and trip.start_lat and trip.start_lng:
        hub = {
            "id": "driver_start",
            "name": "Meet at driver's start",
            "lat": trip.start_lat,
            "lng": trip.start_lng,
            "address": trip.start_location_text or "Driver's starting location",
            "transit": False,
            "bus_routes": [],
            "description": "Meet at the driver's starting location (no return transit available)"
        }
    else:
        hub_data = HUBS.get(request.suggested_hub_id)
        if not hub_data:
            return {"matched": False}
        hub = {
            "id": request.suggested_hub_id,
            "name": hub_data["name"],
            "lat": hub_data["lat"],
            "lng": hub_data["lng"],
            "address": hub_data.get("address", ""),
            "transit": hub_data.get("transit", False),
            "bus_routes": hub_data.get("bus_routes", []),
            "description": hub_data.get("description", "")
        }
    return {
        "matched": True,
        "trip_id": trip.id,
        "request_id": request.id,
        "passenger_name": request.passenger_name,
        "resort": trip.resort,
        "hub": hub,
        "driver_departure_time": trip.departure_time,
        "trip_date": str(trip.trip_date) if trip.trip_date else None,
        "driver_on_the_way": trip.driver_en_route_at is not None,
        "current_lat": request.current_lat,
        "current_lng": request.current_lng,
    }

@app.post("/trips/{trip_id}/start-en-route")
async def start_trip_en_route(trip_id: int, db: Session = Depends(get_db)):
    """Driver marks scheduled trip as 'On the way'. Only allowed on the scheduled day. Enables sharing driver location to matched passenger(s)."""
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if trip.is_realtime:
        raise HTTPException(status_code=400, detail="This endpoint is for scheduled trips only.")
    if not trip.trip_date:
        raise HTTPException(status_code=400, detail="Trip has no scheduled date.")
    today = date.today()
    if not _date_eq(trip.trip_date, today):
        raise HTTPException(status_code=400, detail="Only available on the scheduled day.")
    if trip.driver_en_route_at:
        return {"en_route": True, "started_at": trip.driver_en_route_at.isoformat()}
    trip.driver_en_route_at = datetime.utcnow()
    if trip.start_lat is not None and trip.start_lng is not None and (trip.current_lat is None or trip.current_lng is None):
        trip.current_lat = trip.start_lat
        trip.current_lng = trip.start_lng
        trip.last_location_update = datetime.utcnow()
    db.commit()
    db.refresh(trip)
    
    # Send push notification to matched passenger(s)
    matched_requests = db.query(RideRequest).filter(
        RideRequest.matched_trip_id == trip_id,
        RideRequest.status == "matched"
    ).all()
    
    for request in matched_requests:
        if request.push_token:
            await send_expo_push_notification(
                push_token=request.push_token,
                title="Your driver is on the way!",
                body=f"{trip.driver_name} is heading to the meeting point. Track their location in the app.",
                data={
                    "request_id": request.id,
                    "trip_id": trip_id,
                    "action": "track_driver"
                }
            )
    
    return {"en_route": True, "started_at": trip.driver_en_route_at.isoformat()}

@app.post("/trips/{trip_id}/confirm-pickup")
def confirm_trip_pickup(trip_id: int, db: Session = Depends(get_db)):
    """Driver confirms they picked up the passenger. Sets picked_up_at on trip.
    Only allowed when matched. For Ride Now: always. For Scheduled: after 'On the way'."""
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    # Find matched passenger
    request = db.query(RideRequest).filter(
        RideRequest.matched_trip_id == trip_id,
        RideRequest.status == "matched"
    ).first()
    if not request:
        raise HTTPException(status_code=400, detail="No matched passenger found for this trip")
    
    # For scheduled trips, must be en-route first
    if not trip.is_realtime and not trip.driver_en_route_at:
        raise HTTPException(status_code=400, detail="Driver must be 'On the way' before confirming pickup for scheduled rides")
    
    # Set driver's pickup confirmation
    if not trip.picked_up_at:
        trip.picked_up_at = datetime.utcnow()
    
    # If both parties confirmed, transition status to picked_up
    if trip.picked_up_at and request.picked_up_at:
        trip.status = "picked_up"
        request.status = "picked_up"
    else:
        trip.status = "matched"
    
    db.commit()
    db.refresh(trip)
    db.refresh(request)
    
    return {
        "message": "Pickup confirmed by driver",
        "driver_confirmed": True,
        "passenger_confirmed": request.picked_up_at is not None,
        "both_confirmed": trip.status == "picked_up",
        "picked_up_at": trip.picked_up_at.isoformat() if trip.picked_up_at else None
    }

@app.post("/ride-requests/{request_id}/confirm-pickup")
def confirm_request_pickup(request_id: int, db: Session = Depends(get_db)):
    """Passenger confirms they were picked up. Sets picked_up_at on request.
    If both parties confirm, status transitions to picked_up."""
    request = db.query(RideRequest).filter(RideRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Ride request not found")
    
    if not request.matched_trip_id:
        raise HTTPException(status_code=400, detail="Ride request has no matched trip")
    
    trip = db.query(Trip).filter(Trip.id == request.matched_trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Matched trip not found")
    
    # Set passenger's pickup confirmation
    if not request.picked_up_at:
        request.picked_up_at = datetime.utcnow()
    
    # If both parties confirmed, transition status to picked_up
    if trip.picked_up_at and request.picked_up_at:
        trip.status = "picked_up"
        request.status = "picked_up"
    else:
        request.status = "matched"
    
    db.commit()
    db.refresh(trip)
    db.refresh(request)
    
    return {
        "message": "Pickup confirmed by passenger",
        "passenger_confirmed": True,
        "driver_confirmed": trip.picked_up_at is not None,
        "both_confirmed": request.status == "picked_up",
        "picked_up_at": request.picked_up_at.isoformat() if request.picked_up_at else None
    }

@app.post("/trips/{trip_id}/complete")
def complete_trip(trip_id: int, db: Session = Depends(get_db)):
    """Driver marks ride as completed (arrived at resort). Sets completed_at, status to completed, and frees the seat."""
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    if trip.status == "completed":
        return {"message": "Trip already completed", "completed_at": trip.completed_at.isoformat() if trip.completed_at else None}
    
    # Find matched passenger(s)
    requests = db.query(RideRequest).filter(
        RideRequest.matched_trip_id == trip_id
    ).all()
    
    # Mark trip as completed
    trip.completed_at = datetime.utcnow()
    trip.status = "completed"
    
    # Mark all matched requests as completed
    for request in requests:
        if request.status != "completed":
            request.completed_at = datetime.utcnow()
            request.status = "completed"
    
    db.commit()
    db.refresh(trip)
    
    return {
        "message": "Ride completed",
        "status": trip.status,
        "completed_at": trip.completed_at.isoformat() if trip.completed_at else None,
        "passengers_completed": len(requests)
    }

@app.post("/ride-requests/{request_id}/complete")
def complete_ride_request(request_id: int, db: Session = Depends(get_db)):
    """Passenger marks ride as completed. Sets completed_at and status to completed."""
    request = db.query(RideRequest).filter(RideRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Ride request not found")
    
    if request.status == "completed":
        return {"message": "Ride already completed", "completed_at": request.completed_at.isoformat() if request.completed_at else None}
    
    # Mark request as completed
    request.completed_at = datetime.utcnow()
    request.status = "completed"
    
    db.commit()
    db.refresh(request)
    
    return {
        "message": "Ride completed by passenger",
        "status": request.status,
        "completed_at": request.completed_at.isoformat() if request.completed_at else None
    }

@app.get("/ride-requests/{request_id}/scheduled-match")
def get_scheduled_match_passenger(request_id: int, db: Session = Depends(get_db)):
    """Get confirmed scheduled match + meeting hub for a passenger (en-route screen)."""
    request = db.query(RideRequest).filter(RideRequest.id == request_id).first()
    if not request or _is_departure_now(request.departure_time):
        return {"matched": False}
    if not request.matched_trip_id or request.status != "matched":
        return {"matched": False}
    trip = db.query(Trip).filter(Trip.id == request.matched_trip_id).first()
    if not trip:
        return {"matched": False}
    if request.suggested_hub_id == "driver_start" and trip.start_lat and trip.start_lng:
        hub = {
            "id": "driver_start",
            "name": "Meet at driver's start",
            "lat": trip.start_lat,
            "lng": trip.start_lng,
            "address": trip.start_location_text or "Driver's starting location",
            "transit": False,
            "bus_routes": [],
            "description": "Meet at the driver's starting location (no return transit available)"
        }
    else:
        hub_data = HUBS.get(request.suggested_hub_id) if request.suggested_hub_id else None
        if not hub_data:
            return {"matched": False}
        hub = {
            "id": request.suggested_hub_id,
            "name": hub_data["name"],
            "lat": hub_data["lat"],
            "lng": hub_data["lng"],
            "address": hub_data.get("address", ""),
            "transit": hub_data.get("transit", False),
            "bus_routes": hub_data.get("bus_routes", []),
            "description": hub_data.get("description", "")
        }
    return {
        "matched": True,
        "trip_id": trip.id,
        "request_id": request.id,
        "driver_name": trip.driver_name,
        "resort": trip.resort,
        "hub": hub,
        "driver_departure_time": trip.departure_time,
        "request_date": str(request.request_date) if request.request_date else None,
        "driver_on_the_way": trip.driver_en_route_at is not None,
        "current_lat": trip.current_lat if trip.driver_en_route_at else None,
        "current_lng": trip.current_lng if trip.driver_en_route_at else None,
    }

@app.put("/trips/{trip_id}/location", response_model=schemas.Trip)
def update_trip_location(trip_id: int, location: schemas.LocationUpdate, db: Session = Depends(get_db)):
    """Update driver's current location. Ride Now: always. Scheduled: only on the day-of after driver has tapped 'On the way'."""
    db_trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not db_trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    today = date.today()
    if db_trip.is_realtime:
        can_update = True
    else:
        # Scheduled: only on scheduled day and only after driver has started en route
        can_update = (
            db_trip.trip_date is not None
            and _normalize_date(db_trip.trip_date) == today
            and db_trip.driver_en_route_at is not None
        )
    if not can_update:
        raise HTTPException(
            status_code=400,
            detail="Location updates only for Ride Now or for scheduled trips after you tap 'On the way' on the day of the ride."
        )

    # When trip has a matched passenger, only accept updates that don't move driver farther from pickup.
    # This prevents the app's location (e.g. simulator reporting start) from overwriting script/progress.
    matched_req = db.query(RideRequest).filter(
        RideRequest.matched_trip_id == trip_id,
        RideRequest.status == "matched"
    ).first()
    if matched_req and matched_req.pickup_lat and matched_req.pickup_lng and location.current_lat and location.current_lng:
        nav_lat = matched_req.pickup_lat if _is_departure_now(matched_req.departure_time) else (matched_req.current_lat or matched_req.pickup_lat)
        nav_lng = matched_req.pickup_lng if _is_departure_now(matched_req.departure_time) else (matched_req.current_lng or matched_req.pickup_lng)
        if nav_lat and nav_lng:
            driver_lat = db_trip.current_lat or db_trip.start_lat
            driver_lng = db_trip.current_lng or db_trip.start_lng
            dist_new = haversine(location.current_lat, location.current_lng, nav_lat, nav_lng)
            if driver_lat is not None and driver_lng is not None:
                dist_current = haversine(driver_lat, driver_lng, nav_lat, nav_lng)
                if dist_new > dist_current:
                    # Reject update that moves driver farther from pickup (e.g. app sending stale start)
                    db.refresh(db_trip)
                    return db_trip

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

    # Only match real-time requests (departure_time is "Now", any case)
    requests = db.query(RideRequest).filter(
        RideRequest.resort == resort,
        RideRequest.status == "pending",
        func.lower(func.trim(func.coalesce(RideRequest.departure_time, ""))) == "now"
    ).all()

    matches = []
    for req in requests:
        # Ride Now: passenger is already at pickup (they open app once there). Use pickup only.
        passenger_lat = req.pickup_lat
        passenger_lng = req.pickup_lng
        
        if not passenger_lat or not passenger_lng:
            continue
        
        # Check seat availability: driver must have enough seats for passenger's needs
        seats_needed = getattr(req, 'seats_needed', None)
        if seats_needed is None or seats_needed < 1:
            seats_needed = 1
        if (trip.available_seats or 0) < seats_needed:
            continue
            
        # Check if passenger's pickup is on/near driver's route (driver -> resort)
        xtd = get_cross_track_distance(
            driver_lat, driver_lng, 
            resort_coords["lat"], resort_coords["lng"], 
            passenger_lat, passenger_lng
        )
        if xtd < RIDE_NOW_ROUTE_KM:
            # Additional check: passenger must be ahead of driver (not behind)
            if is_ahead_on_route(
                driver_lat, driver_lng,
                resort_coords["lat"], resort_coords["lng"],
                passenger_lat, passenger_lng
            ):
                matches.append(req)
    return matches


@app.get("/match-nearby-passengers/debug")
def match_passengers_debug(trip_id: int, resort: str, db: Session = Depends(get_db)):
    """Debug why match-nearby-passengers returns no matches."""
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        return {"error": "Trip not found", "trip_id": trip_id}
    if not trip.is_realtime:
        return {"error": "Trip is not realtime", "trip_id": trip_id}

    driver_lat = trip.current_lat or trip.start_lat
    driver_lng = trip.current_lng or trip.start_lng
    if not driver_lat or not driver_lng:
        return {
            "error": "Trip has no location. Set simulator Custom Location before opening app, then re-post.",
            "trip_id": trip_id,
            "current_lat": trip.current_lat,
            "current_lng": trip.current_lng,
            "start_lat": trip.start_lat,
            "start_lng": trip.start_lng,
        }

    resort_coords = next((r for r in RESORTS_DATA if r["name"] == resort), None)
    if not resort_coords:
        return {"error": "Resort not found", "resort": resort}

    requests = db.query(RideRequest).filter(
        RideRequest.resort == resort,
        RideRequest.status == "pending",
        func.lower(func.trim(func.coalesce(RideRequest.departure_time, ""))) == "now",
    ).all()

    passengers = []
    for req in requests:
        xtd = get_cross_track_distance(
            driver_lat, driver_lng,
            resort_coords["lat"], resort_coords["lng"],
            req.pickup_lat, req.pickup_lng,
        )
        ahead = is_ahead_on_route(
            driver_lat, driver_lng,
            resort_coords["lat"], resort_coords["lng"],
            req.pickup_lat, req.pickup_lng
        )
        would_match = xtd < RIDE_NOW_ROUTE_KM and ahead and trip.available_seats >= (req.seats_needed or 1)
        
        skip_reason = None
        if not would_match:
            if xtd >= RIDE_NOW_ROUTE_KM:
                skip_reason = f"xtd>={RIDE_NOW_ROUTE_KM}km"
            elif not ahead:
                skip_reason = "behind driver or past resort"
            else:
                skip_reason = "seats"
        
        passengers.append({
            "id": req.id,
            "passenger_name": req.passenger_name,
            "pickup_lat": req.pickup_lat,
            "pickup_lng": req.pickup_lng,
            "xtd_km": round(xtd, 3),
            "ahead_of_driver": ahead,
            "would_match": would_match,
            "skip_reason": skip_reason,
        })

    return {
        "trip_id": trip_id,
        "driver_lat": driver_lat,
        "driver_lng": driver_lng,
        "resort": resort,
        "available_seats": trip.available_seats,
        "route_km_threshold": RIDE_NOW_ROUTE_KM,
        "pending_passengers": len(requests),
        "passengers": passengers,
    }


@app.get("/match-nearby-drivers/")
def match_drivers(request_id: int, resort: str, db: Session = Depends(get_db)):
    """Find active drivers who will pass the passenger's pickup (for real-time rides)
    
    Passenger is already at pickup when they open the app. We match drivers who will pass that point.
    """
    request = db.query(RideRequest).filter(RideRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Ride request not found")
    if not _is_departure_now(request.departure_time):
        raise HTTPException(status_code=400, detail="This endpoint is only for real-time ride requests")
    
    # Ride Now: passenger is at pickup. Use pickup only.
    passenger_lat = request.pickup_lat
    passenger_lng = request.pickup_lng
    
    if not passenger_lat or not passenger_lng:
        return []  # No location available
    
    resort_coords = next((r for r in RESORTS_DATA if r["name"] == resort), None)
    if not resort_coords: 
        return []

    # Get active real-time trips going to the same resort (need at least start or current location)
    trips = db.query(Trip).filter(
        Trip.resort == resort,
        Trip.is_realtime == True,
        Trip.available_seats > 0,
    ).all()

    matches = []
    for trip in trips:
        # Use driver's current location, fallback to start (so trips with only start still match)
        driver_lat = trip.current_lat or trip.start_lat
        driver_lng = trip.current_lng or trip.start_lng

        if not driver_lat or not driver_lng:
            continue

        # Check seat availability: driver must have enough seats for passenger's needs
        seats_needed = getattr(request, 'seats_needed', None)
        if seats_needed is None or seats_needed < 1:
            seats_needed = 1
        if (trip.available_seats or 0) < seats_needed:
            continue

        # Check if passenger's pickup is on/near driver's route (driver -> resort)
        xtd = get_cross_track_distance(
            driver_lat, driver_lng,
            resort_coords["lat"], resort_coords["lng"],
            passenger_lat, passenger_lng
        )
        if xtd < RIDE_NOW_ROUTE_KM:
            # Additional check: passenger must be ahead of driver (not behind)
            if is_ahead_on_route(
                driver_lat, driver_lng,
                resort_coords["lat"], resort_coords["lng"],
                passenger_lat, passenger_lng
            ):
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
        now_expr = func.lower(func.trim(func.coalesce(RideRequest.departure_time, ""))) == "now"
        if is_realtime:
            query = query.filter(now_expr)
        else:
            query = query.filter(~now_expr)
    
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

def _parse_target_date(value: Optional[str]) -> date:
    """Parse target_date from query (YYYY-MM-DD or ISO string). Defaults to tomorrow."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return date.today() + timedelta(days=1)
    s = value.strip()
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        try:
            return datetime.strptime(s[:10], "%Y-%m-%d").date()
        except ValueError:
            pass
    return date.today() + timedelta(days=1)

def _safe_float(x, default: float = 0.0) -> float:
    """Return a JSON-serializable float (no NaN)."""
    if x is None:
        return default
    try:
        f = float(x)
        return f if math.isfinite(f) else default
    except (TypeError, ValueError):
        return default

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
def match_scheduled_rides(
    resort: str,
    target_date: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Match scheduled trips and ride requests for a specific date.
    Optimizes for timing compatibility and closest hub.
    target_date: optional "YYYY-MM-DD" or ISO string (e.g. from JS toISOString()); defaults to tomorrow.
    Always returns JSON so clients never get parse errors.
    """
    try:
        target_date_parsed = _parse_target_date(target_date)

        # Get scheduled trips (not real-time) for the target date
        trips = db.query(Trip).filter(
            Trip.resort == resort,
            Trip.is_realtime == False,
            Trip.available_seats > 0
        ).all()
        trips = [t for t in trips if _date_eq(t.trip_date, target_date_parsed)]

        # Get scheduled ride requests for the target date (exclude Ride Now)
        now_expr = func.lower(func.trim(func.coalesce(RideRequest.departure_time, ""))) == "now"
        requests = db.query(RideRequest).filter(
            RideRequest.resort == resort,
            RideRequest.status == "pending",
            ~now_expr
        ).all()
        requests = [r for r in requests if _date_eq(r.request_date, target_date_parsed)]

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
                # Ensure str for time comparison (DB can have null)
                t_dep = (trip.departure_time or "").strip() or "?"
                r_dep = (req.departure_time or "").strip() or "?"
                time_diff = time_difference_minutes(t_dep, r_dep)
                if time_diff is None or time_diff > 60:
                    continue

                seats_needed = req.seats_needed if hasattr(req, 'seats_needed') and req.seats_needed else 1
                if trip.available_seats < seats_needed:
                    continue
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
                        driver_name=trip.driver_name or "",
                        passenger_name=req.passenger_name or "",
                        resort=resort,
                        suggested_hub={
                            "id": str(best_hub["id"]),
                            "name": str(best_hub["name"]),
                            "lat": _safe_float(best_hub["lat"]),
                            "lng": _safe_float(best_hub["lng"]),
                        },
                        driver_departure_time=t_dep,
                        passenger_departure_time=r_dep,
                        hub_distance_driver=_safe_float(best_hub.get("driver_distance")),
                        hub_distance_passenger=_safe_float(best_hub.get("passenger_distance")),
                    ))

        matches.sort(key=lambda x: x.hub_distance_driver + x.hub_distance_passenger)
        return matches[:10]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"match-scheduled error: {str(e)}")

@app.get("/match-scheduled/debug")
def match_scheduled_debug(resort: str, target_date: Optional[str] = None, db: Session = Depends(get_db)):
    """Debug why match-scheduled returns no matches. Use same resort & target_date as match-scheduled."""
    target_date_parsed = _parse_target_date(target_date)

    trips = db.query(Trip).filter(
        Trip.resort == resort,
        Trip.is_realtime == False,
        Trip.available_seats > 0
    ).all()
    trips = [t for t in trips if _date_eq(t.trip_date, target_date_parsed)]

    now_expr = func.lower(func.trim(func.coalesce(RideRequest.departure_time, ""))) == "now"
    requests = db.query(RideRequest).filter(
        RideRequest.resort == resort,
        RideRequest.status == "pending",
        ~now_expr
    ).all()
    requests = [r for r in requests if _date_eq(r.request_date, target_date_parsed)]

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
        "target_date": str(target_date_parsed),
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

@app.post("/match-scheduled/confirm")
def confirm_scheduled_match(
    trip_id: int = Query(...),
    request_id: int = Query(...),
    hub_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """Confirm a scheduled match and link the trip and request with selected hub.
    
    Args:
        trip_id: The driver's trip ID
        request_id: The passenger's ride request ID
        hub_id: The selected hub ID (or "driver_start")
    """
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    request = db.query(RideRequest).filter(RideRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Ride request not found")
    
    # Validate hub exists (or is driver_start)
    if hub_id != "driver_start" and hub_id not in HUBS:
        raise HTTPException(status_code=400, detail="Invalid hub ID")
    
    # Check if trip has available seats
    seats_needed = request.seats_needed if hasattr(request, 'seats_needed') and request.seats_needed else 1
    if trip.available_seats < seats_needed:
        raise HTTPException(status_code=400, detail="Not enough available seats")
    
    # Check if request is already matched
    if request.matched_trip_id:
        raise HTTPException(status_code=400, detail="Ride request is already matched")
    
    # Create the match
    request.matched_trip_id = trip_id
    request.suggested_hub_id = hub_id
    request.status = "matched"
    trip.available_seats -= seats_needed
    trip.status = "matched"
    
    db.commit()
    db.refresh(trip)
    db.refresh(request)
    
    # Get hub details for response
    if hub_id == "driver_start" and trip.start_lat and trip.start_lng:
        hub = {
            "id": "driver_start",
            "name": "Meet at driver's start",
            "lat": trip.start_lat,
            "lng": trip.start_lng,
            "address": trip.start_location_text or "Driver's starting location"
        }
    else:
        hub_data = HUBS.get(hub_id)
        hub = {
            "id": hub_id,
            "name": hub_data["name"],
            "lat": hub_data["lat"],
            "lng": hub_data["lng"],
            "address": hub_data.get("address", "")
        }
    
    return {
        "message": "Scheduled match confirmed",
        "trip_id": trip_id,
        "request_id": request_id,
        "hub": hub,
        "remaining_seats": trip.available_seats,
        "driver_name": trip.driver_name,
        "passenger_name": request.passenger_name,
        "resort": trip.resort
    }

# --- RIDE REQUESTS (PASSENGER) ---
@app.post("/ride-requests/", response_model=schemas.RideRequest)
def create_ride_request(req: schemas.RideRequestCreate, db: Session = Depends(get_db)):
    t0 = time.perf_counter()
    logger.info(f"📥 POST /ride-requests/ received (passenger={getattr(req, 'passenger_name', '?')}, resort={getattr(req, 'resort', '?')}, has_lat_lng={req.lat is not None and req.lng is not None})")
    lat, lng = req.lat, req.lng
    is_scheduled = not _is_departure_now(req.departure_time)

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

    # Ride Now: passenger is at pickup when they open app; we do not track location.
    # Scheduled: we set current_lat/lng for en-route tracking on the day-of.
    is_realtime = _is_departure_now(req.departure_time)
    if is_realtime:
        current_lat, current_lng = None, None
        last_location_update = None
    else:
        current_lat, current_lng = lat, lng
        last_location_update = datetime.utcnow()
    
    new_req = RideRequest(
        passenger_name=req.passenger_name,
        resort=req.resort,
        pickup_lat=lat,
        pickup_lng=lng,
        current_lat=current_lat,
        current_lng=current_lng,
        last_location_update=last_location_update,
        departure_time=req.departure_time,
        request_date=req.request_date,
        seats_needed=req.seats_needed if hasattr(req, 'seats_needed') else 1,
        status="pending"
    )
    db.add(new_req)
    db.commit()
    db.refresh(new_req)
    elapsed = time.perf_counter() - t0
    logger.info(f"✅ POST /ride-requests/ completed in {elapsed:.2f}s (request_id={new_req.id})")
    return new_req

@app.get("/ride-requests/{request_id}", response_model=schemas.RideRequest)
def get_ride_request(request_id: int, db: Session = Depends(get_db)):
    """Get a ride request by ID"""
    request = db.query(RideRequest).filter(RideRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Ride request not found")
    return request

@app.put("/ride-requests/{request_id}/location", response_model=schemas.RideRequest)
def update_ride_request_location(request_id: int, location: schemas.LocationUpdate, db: Session = Depends(get_db)):
    """Update passenger's current location. Only for scheduled requests on the day-of (en route).
    
    Ride Now: passengers are already at pickup when they open the app; we do not track their location.
    This ensures drivers never wait for passengers.
    """
    db_request = db.query(RideRequest).filter(RideRequest.id == request_id).first()
    if not db_request:
        raise HTTPException(status_code=404, detail="Ride request not found")
    today = date.today()
    is_realtime = _is_departure_now(db_request.departure_time)
    if is_realtime:
        raise HTTPException(
            status_code=400,
            detail="Passenger location is not tracked for Ride Now. Passengers are at pickup when they open the app."
        )
    scheduled_today = (
        db_request.request_date is not None
        and _date_eq(db_request.request_date, today)
    )
    if not scheduled_today:
        raise HTTPException(
            status_code=400,
            detail="Location updates only for scheduled requests on the day of the ride (en route)."
        )
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
    prev_matched = db_request.matched_trip_id
    for key, value in update_data.items():
        if hasattr(db_request, key):
            setattr(db_request, key, value)
    
    # Scheduled match confirm: decrement driver's trip seats (once)
    if (
        update_data.get("matched_trip_id") is not None
        and update_data.get("status") == "matched"
        and not _is_departure_now(db_request.departure_time)
        and prev_matched != update_data["matched_trip_id"]
    ):
        trip = db.query(Trip).filter(Trip.id == db_request.matched_trip_id).first()
        if trip and trip.available_seats > 0:
            trip.available_seats -= 1
    
    db.commit()
    db.refresh(db_request)
    return db_request