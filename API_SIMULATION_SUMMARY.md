# API-Driven Route Simulation - Implementation Summary

## What Changed

The simulation is now **fully automated** and tests the **actual production data flow** by pushing location updates via the API instead of relying on iOS Simulator's manual GPS features.

## Before vs After

### Before
- Script created passenger, printed instructions
- User had to manually open app as driver, post trip, accept match
- Freeway Drive went on random route (not toward passenger)
- GPX files required Xcode's debugger (doesn't work with Expo CLI)

### After
- Script creates **both** passenger and driver
- Script matches them and accepts automatically
- Script **pushes location updates via API** every 10 seconds using GPX waypoints
- **Fully automated** - just watch the driver move on the map!
- Works perfectly with Expo CLI workflow

## How It Works

```
sim_ride.py does:
1. POST /ride-requests/ (create passenger)
2. POST /trips/ (create driver)
3. GET /match-nearby-passengers/ (find match)
4. POST /trips/{id}/accept-passenger (accept match)
5. Loop through GPX waypoints:
   - PUT /trips/{id}/location (update driver position)
   - xcrun simctl location set (center Simulator map)
   - sleep 10 seconds
   - repeat

Expo app (running on Simulator):
- **Driver screen**: Polls GET /trips/{trip_id}/matched-passenger every 5 seconds
  - Gets passenger pickup location and navigation target
  - Receives `distance_km` and `near_pickup` flag
  - Shows "Confirm pickup" prompt when `near_pickup` is true (within 100m)
- **Passenger screen**: Polls GET /ride-requests/{id}/matched-driver every 5 seconds
  - Sees driver's updated location
  - Renders driver marker moving on map
```

### Pickup Proximity Notification

**API: `GET /trips/{trip_id}/matched-passenger`**

Returns (when matched):
- `passenger_name` - Name of matched passenger
- `current_lat`, `current_lng` - Navigation target (pickup for Ride Now, hub for scheduled)
- `pickup_lat`, `pickup_lng` - Original pickup location
- **`distance_km`** - Distance from driver's current position to nav target (float, nullable)
- **`near_pickup`** - True when driver is within 500m (0.5 km) of nav target (boolean)

**Driver app behavior:**
- Poll this endpoint every 5 seconds after match is accepted
- When `near_pickup` becomes `true`, show "You've arrived - confirm pickup" notification
- Keep the prompt visible until the driver taps to confirm (do not auto-dismiss)
- On confirm: call `POST /trips/{trip_id}/confirm-pickup`; passenger confirms via `POST /ride-requests/{id}/confirm-pickup`; then complete the trip
- Threshold: 500m (0.5 km) so the alert triggers with time to react before passing the rider
```

## Files Modified

### 1. `sim_ride.py`
**New functions:**
- `parse_gpx_waypoints()` - Extracts lat/lon from GPX `<trkpt>` elements
- `simulate_driver_route()` - Loops through waypoints, posts `PUT /trips/{id}/location` every 10s

**Updated functions:**
- `sim_ride_now()` - Now creates driver trip, matches, accepts, and runs route simulation
- `sim_scheduled()` - Driver perspective now runs route simulation to hub

**New arguments:**
- `--interval` - Configurable update frequency (default 10s)
- Removed `--auto-gpx` (no longer needed)

### 2. `gpx/route_to_solitude.gpx`
- Added 9 intermediate waypoints (10 → 19 total)
- Now ~3 minutes at 10-second intervals (was ~2 minutes)
- Smoother visual progression on map

### 3. `dev.sh`
**Updated commands:**
- `sim-ride [resort] [interval]` - Now fully automated
- `sim-sched [resort] [driver|passenger] [interval]` - Driver perspective automated

### 4. `SIMULATION_GUIDE.md`
- Updated to reflect fully automated flow
- Clarified GPX files are used by the script (not loaded in Xcode)
- Added explanation of API-driven approach

## Usage

### Ride Now Simulation
```bash
# Terminal 1
./dev.sh local

# Terminal 2
./dev.sh sim-ride solitude

# Open Expo app on Simulator - watch driver move automatically!
```

**What you'll see:**
```
✓ Database wiped
✓ Passenger created (ID: 42) at Holladay, Utah
✓ Driver created (ID: 43) at Sugar House
✓ Match found! Driver matched with passenger
✓ Match accepted!
✓ Simulator location set to (40.7178, -111.8689)

Ready to Simulate!
Open the Expo app on iOS Simulator to watch:
• Driver marker will move along the route
• Location updates every 10 seconds
• Watch the driver approach the passenger!

[1/19] Start: Sugar House - 7.22km to passenger
[2/19] Moving East - 6.95km to passenger
[3/19] Highland Dr - 6.68km to passenger
...
[8/19] Approaching P&R - 0.45km to passenger

Driver Approaching Passenger!
✓ Driver is within 100m of passenger pickup

Route simulation complete!
```

### Scheduled Ride Simulation
```bash
./dev.sh sim-sched solitude driver

# Opens app, driver moves to hub automatically
```

## Why This Is Better

### 1. Tests Production Data Flow
- Uses `PUT /trips/{id}/location` endpoint (same as Expo app)
- Tests API location update logic
- Validates database updates
- Tests polling frequency and responsiveness

### 2. No Manual Intervention
- Old: Open app, post trip, accept match, load GPX, etc.
- New: Script does everything, you just watch

### 3. Works with Expo CLI
- Old: GPX required Xcode debugger
- New: API updates work with any app setup

### 4. Configurable Speed
```bash
./dev.sh sim-ride solitude 5   # 5-second intervals (fast)
./dev.sh sim-ride solitude 10  # 10-second intervals (default)
./dev.sh sim-ride solitude 15  # 15-second intervals (matches production)
```

### 5. Distance Tracking
Script prints distance to passenger at each waypoint, making it easy to verify matching algorithm behavior.

## Next Steps

The simulation is now production-ready. To test:

```bash
# Terminal 1: Start API
./dev.sh local

# Terminal 2: Run simulation
./dev.sh sim-ride solitude

# iOS Simulator: Open Expo app, watch the magic happen!
```

You can now test the entire real-time matching and tracking experience without any manual GPS manipulation. The script handles everything via API calls, just like production! 🚀
