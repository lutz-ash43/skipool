# Ride Now Logic - Fixed Implementation

## How It Should Work

### Driver Flow:
1. Driver posts trip → Gets `trip_id`
2. Driver's location is tracked via `PUT /trips/{trip_id}/location` (polling every 10-30 seconds)
3. Driver calls `GET /match-nearby-passengers/?trip_id={trip_id}&resort={resort}`
   - Backend uses driver's **current location** from the trip (updated as they drive)
   - Finds passengers whose **current location** is on the route
4. Passengers appear on map as driver drives

### Passenger Flow:
1. Passenger posts request → Gets `request_id`
2. Passenger's location is tracked via `PUT /ride-requests/{request_id}/location` (polling every 10-30 seconds)
3. Passenger calls `GET /match-nearby-drivers/?request_id={request_id}&resort={resort}`
   - Backend uses passenger's **current location** from the request (updated as they move)
   - Finds drivers whose **current location** shows they will pass the passenger
4. Drivers appear on map as passenger waits

## Changes Made

### Backend Changes:

1. **Added passenger location tracking**:
   - Added `current_lat`, `current_lng`, `last_location_update` to `RideRequest` model
   - Added `PUT /ride-requests/{request_id}/location` endpoint

2. **Fixed `match-nearby-passengers`**:
   - **Before**: Took `lat, lng` as parameters
   - **After**: Takes `trip_id` parameter, gets driver's current location from database
   - Uses driver's **current location** (updated as they drive)
   - Uses passenger's **current location** (if available), fallback to pickup location

3. **Fixed `match-nearby-drivers`**:
   - **Before**: Took `lat, lng` as parameters  
   - **After**: Takes `request_id` parameter, gets passenger's current location from database
   - Uses passenger's **current location** (updated as they move)
   - Uses driver's **current location** (updated as they drive)

## Mobile App Updates Needed

The mobile app needs to be updated to match the new API:

### For Drivers:
```typescript
// After posting trip, store trip_id
setPostedTripId(data.id);

// Poll to update location
useEffect(() => {
  if (mode === 'now' && role === 'driver' && postedTripId && location) {
    const interval = setInterval(async () => {
      // Update driver location
      await fetch(`${API_URL}/trips/${postedTripId}/location`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          current_lat: location.latitude,
          current_lng: location.longitude
        })
      });
      
      // Refresh matches using trip_id (not lat/lng)
      if (selectedResort && postedTripId) {
        const res = await fetch(
          `${API_URL}/match-nearby-passengers/?trip_id=${postedTripId}&resort=${selectedResort.name}`
        );
        const matches = await res.json();
        setMatches(Array.isArray(matches) ? matches : []);
      }
    }, 15000); // Every 15 seconds
    
    return () => clearInterval(interval);
  }
}, [mode, role, postedTripId, location, selectedResort]);
```

### For Passengers:
```typescript
// After posting request, store request_id
setPostedRequestId(data.id);

// Poll to update location
useEffect(() => {
  if (mode === 'now' && role === 'passenger' && postedRequestId && location) {
    const interval = setInterval(async () => {
      // Update passenger location
      await fetch(`${API_URL}/ride-requests/${postedRequestId}/location`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          current_lat: location.latitude,
          current_lng: location.longitude
        })
      });
      
      // Refresh matches using request_id (not lat/lng)
      if (selectedResort && postedRequestId) {
        const res = await fetch(
          `${API_URL}/match-nearby-drivers/?request_id=${postedRequestId}&resort=${selectedResort.name}`
        );
        const matches = await res.json();
        setMatches(Array.isArray(matches) ? matches : []);
      }
    }, 15000); // Every 15 seconds
    
    return () => clearInterval(interval);
  }
}, [mode, role, postedRequestId, location, selectedResort]);
```

## Database Migration Needed

Add these columns to `ride_requests` table:
- `current_lat` (FLOAT, nullable)
- `current_lng` (FLOAT, nullable)  
- `last_location_update` (TIMESTAMP, nullable)

Run the updated migration script or SQL fix.

## Summary

✅ **Backend is now correct**:
- Uses stored current locations from database
- Driver's current location tracked via PUT endpoint
- Passenger's current location tracked via PUT endpoint
- Matching uses current locations, not static parameters

⚠️ **Mobile app needs updates**:
- Store trip_id/request_id after posting
- Update API calls to use trip_id/request_id instead of lat/lng
- Add polling to update locations
- Add passenger view with location tracking
