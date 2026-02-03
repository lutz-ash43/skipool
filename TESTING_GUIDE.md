# Testing Guide for SkiPool App

## Overview

This guide covers how to test location tracking, matching, and real-time features using the iOS Simulator and test scripts.

**Ride Now**: Passengers are at pickup when they open the app; we do not track their location. Only **drivers** are simulated or updated. Use passenger simulation only for **scheduled en-route** (day-of, moving to hub).

## Prerequisites

1. **Backend running** (locally or deployed)
2. **Mobile app** running in iOS Simulator
3. **Database access** (for running test scripts). If you run scripts **locally** (e.g. `create_test_data.py`), use a TCP connection—see `LOCAL_DATABASE.md`.

## Part 1: Create Test Data

### Step 1: Run the test data script

```bash
cd /Users/ashley/skipool
python create_test_data.py
```

This creates:
- **Ride Now**: 2 drivers + 2 passengers (Alta and Park City)
- **Scheduled**: 2 drivers + 2 passengers (Alta and Snowbird, for tomorrow)

The script prints the IDs you'll need for testing.

### Step 2: Verify in database (optional)

```sql
-- Check Ride Now trips
SELECT id, driver_name, resort, available_seats, current_lat, current_lng 
FROM trips 
WHERE is_realtime = true;

-- Check Ride Now requests (passengers at pickup only; no current_lat/lng)
SELECT id, passenger_name, resort, seats_needed, pickup_lat, pickup_lng 
FROM ride_requests 
WHERE departure_time = 'Now';

-- Check Scheduled trips
SELECT id, driver_name, resort, trip_date, departure_time, available_seats 
FROM trips 
WHERE is_realtime = false;

-- Check Scheduled requests
SELECT id, passenger_name, resort, request_date, departure_time, seats_needed 
FROM ride_requests 
WHERE departure_time != 'Now';
```

## Part 2: Simulate Location in iOS Simulator

### Option A: Use Simulator's Location Features (Recommended)

1. **Set a custom location**:
   - In iOS Simulator: **Features → Location → Custom Location...**
   - Enter coordinates (e.g., `40.7244, -111.8881` for Sugar House)
   - Click **OK**

2. **Simulate movement**:
   - **Features → Location → Freeway Drive** (simulates movement)
   - Or use **City Run** or **City Bicycle Ride**
   - Or manually change location periodically

3. **For testing routes**:
   - Start at pickup location (e.g., Sugar House: `40.7244, -111.8881`)
   - Periodically update to locations along the route
   - Example route to Alta:
     - Start: `40.7244, -111.8881` (Sugar House)
     - Mid: `40.6500, -111.7500` (Canyon entrance)
     - End: `40.5883, -111.6358` (Alta)

### Option B: Use GPX Files (More Realistic)

1. **Create a GPX file** (`test_route.gpx`):
```xml
<?xml version="1.0"?>
<gpx version="1.1">
  <trk>
    <name>Route to Alta</name>
    <trkseg>
      <trkpt lat="40.7244" lon="-111.8881"><time>2026-01-22T10:00:00Z</time></trkpt>
      <trkpt lat="40.7000" lon="-111.8000"><time>2026-01-22T10:05:00Z</time></trkpt>
      <trkpt lat="40.6500" lon="-111.7500"><time>2026-01-22T10:10:00Z</time></trkpt>
      <trkpt lat="40.5883" lon="-111.6358"><time>2026-01-22T10:15:00Z</time></trkpt>
    </trkseg>
  </trk>
</gpx>
```

2. **Add to Xcode project**:
   - Drag `test_route.gpx` into your Xcode project
   - In Simulator: **Features → Location → [Your GPX file name]**

3. **The simulator will follow the route** automatically

## Part 3: Simulate Location Programmatically (Backend)

Use the `simulate_location.py` script to update locations in the database directly. This is useful for testing without the simulator.

### Simulate Driver Moving to Resort (Ride Now)

```bash
# Driver ID 1 moving to Alta (10 steps, 2 seconds each)
python simulate_location.py --trip-id 1 --steps 10 --delay 2.0
```

### Simulate Passenger Movement (Scheduled En-Route Only)

Ride Now passengers are at pickup; we don't track their location. Use this only for **scheduled** en-route testing.

```bash
# Passenger ID 3 or 4 (scheduled) moving around pickup / toward hub
python simulate_location.py --request-id 3 --steps 5 --delay 2.0
```

### Simulate Scheduled Driver En Route to Hub

```bash
# Driver ID 3 moving to meeting hub
python simulate_location.py --trip-id 3 --hub-lat 40.5897 --hub-lng -111.8856 --steps 10 --delay 2.0
```

## Part 4: Testing Scenarios

### Scenario 1: Ride Now - Driver Sees Passengers

1. **Setup**:
   - Run `create_test_data.py` (creates driver ID 1, passenger ID 1)
   - Both going to Alta, both at Sugar House

2. **In iOS Simulator**:
   - Open app as **Driver**
   - Select **Ride Now** mode
   - Enter name: "Test Driver - Alta"
   - Use GPS location (should be Sugar House)
   - Select **Alta** resort
   - Tap **Confirm** (or equivalent)
   - You should see passenger matches appear

3. **Simulate driver movement**:
   - Use Simulator location features OR
   - Run: `python simulate_location.py --trip-id 1 --steps 10 --delay 3.0`
   - Watch matches update in real-time

4. **Test matching**:
   - Passenger should appear on map (at pickup)
   - Tap **Accept** on passenger
   - Navigate to **pickup** (passenger is waiting there; no tracking)

### Scenario 2: Ride Now - Passenger Sees Drivers

1. **Setup**: Same test data

2. **In iOS Simulator**:
   - Open app as **Passenger**
   - Select **Ride Now** mode
   - Enter name: "Test Passenger - Alta"
   - Use GPS location
   - Select **Alta** resort
   - Tap **Confirm**

3. **Simulate driver movement**:
   - In another terminal: `python simulate_location.py --trip-id 1 --steps 10 --delay 3.0`
   - Watch driver appear on map as they get closer

4. **Test acceptance**:
   - Tap **Accept** on driver
   - Should see **driver** location tracking (driver approaching; passenger stays at pickup)

### Scenario 3: Scheduled Ride - Day-of En Route

1. **Setup**: 
   - Run `create_test_data.py` (creates scheduled driver ID 3, passenger ID 3)
   - Both going to Alta tomorrow, 7:00 AM and 7:30 AM

2. **In iOS Simulator**:
   - Open app as **Driver**
   - Select **Schedule** mode
   - Enter details matching test driver
   - Confirm match with passenger
   - **Change system date to tomorrow** (Simulator → Device → Date & Time → uncheck "Set Automatically" → set to tomorrow)

3. **Test en-route**:
   - App should show "Today's ride" en-route screen
   - Tap **"I'm on my way"**
   - Simulate movement: `python simulate_location.py --trip-id 3 --hub-lat 40.5897 --hub-lng -111.8856 --steps 10 --delay 3.0`
   - Passenger should see driver moving on map

### Scenario 4: Seat Matching

1. **Create test data with seat mismatch**:
   ```python
   # Driver with 2 seats
   # Passenger needing 3 seats
   # Should NOT match
   ```

2. **Test**:
   - Verify passenger doesn't see driver with insufficient seats
   - Verify driver doesn't see passenger needing more seats than available

## Part 5: Quick Test Commands

### Create fresh test data
```bash
python create_test_data.py
```

### Simulate driver moving (Ride Now)
```bash
python simulate_location.py --trip-id 1 --steps 15 --delay 2.0
```

### Simulate passenger movement (scheduled en-route only)
```bash
python simulate_location.py --request-id 3 --steps 5 --delay 2.0
```

### Simulate scheduled en-route
```bash
# Get hub coordinates from your match, then:
python simulate_location.py --trip-id 3 --hub-lat 40.5897 --hub-lng -111.8856 --steps 10 --delay 2.0
```

## Part 6: Testing Tips

### iOS Simulator Location Tips

1. **Multiple simulators**: Run two simulators side-by-side (one driver, one passenger)
   - Xcode → **Window → Devices and Simulators**
   - Click **+** to add another simulator

2. **Location presets**: Use built-in presets:
   - **Apple** (Cupertino)
   - **City Bicycle Ride** (moves automatically)
   - **City Run** (moves automatically)
   - **Freeway Drive** (moves automatically)

3. **Manual updates**: 
   - **Features → Location → Custom Location**
   - Update coordinates periodically to simulate movement

### Backend Testing Tips

1. **Watch logs**: Monitor backend logs to see location updates
2. **Check database**: Query `trips` for `current_lat`/`current_lng` (drivers). Ride Now passengers use `pickup_lat`/`pickup_lng` only.
3. **Use debug endpoint**: `GET /match-scheduled/debug?resort=Alta&target_date=2026-01-23`

### Common Issues

1. **No matches appearing**:
   - Check both have same resort
   - Check passenger **pickup** (and driver route) are close enough (within 2km of route)
   - Check seat availability
   - Use debug endpoint

2. **Location not updating** (drivers only; passengers not tracked for Ride Now):
   - Verify location permissions in simulator (driver)
   - Check backend logs for PUT `/trips/{id}/location` requests
   - Verify `current_lat`/`current_lng` in `trips` table

3. **Matches not refreshing**:
   - App polls every 15 seconds
   - Check network tab for API calls
   - Verify backend endpoints are working

## Part 7: Automated Testing Script

Run the full-flow script (driver movement only; Ride Now passengers are at pickup):

```bash
chmod +x test_full_flow.sh && ./test_full_flow.sh
```

This creates test data, then simulates **driver** movement. Passengers are at pickup—we don't simulate their location for Ride Now.
