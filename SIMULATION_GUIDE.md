# SkiPool Simulation Testing Guide

## Overview

SkiPool now has comprehensive tools for testing both the API endpoints and the real-time experience with **hybrid manual/automated route simulation**.

### Key Feature: Hybrid Interactive Testing

The simulation uses a **hybrid approach** that combines the best of both worlds:

1. **You control the app UI** - Open the app, post trips, and interact naturally
2. **Script automates location updates** - No manual GPS manipulation needed
3. **Watch real-time behavior** - See the driver move on the map exactly as users would

**How it works:**
- Script creates test data (passengers) and waits for you to post a driver trip in the app
- Once detected, the script takes over and pushes driver location updates via `PUT /trips/{id}/location` every 10 seconds
- This **exactly matches production behavior** (Expo app sends location every 15s)
- You watch the app UI as the driver moves toward the passenger automatically

**Why this approach:**
- Tests the actual production data flow (API location updates)
- Lets you see and interact with the real app UI
- No need for manual GPS manipulation or Xcode GPX loading
- Fully observable - watch matches, prompts, and location updates in real-time
- Configurable speed (5s, 10s, or custom intervals)

## Quick Start

### 1. Start the Development Environment

```bash
# Terminal 1: Start API + Database
./dev.sh local
```

Wait for: `API will be available at: http://localhost:8080`

### 2. Run API Tests

```bash
# Terminal 2: Run endpoint tests
./dev.sh test

# Or with address-based geocoding validation (slower)
python3 test_flows.py --base-url http://localhost:8080

# Or skip geocoding for faster tests
python3 test_flows.py --base-url http://localhost:8080 --skip-geocoding
```

### 3. Run Simulator Tests (Hybrid Mode)

```bash
# Terminal 2: Ride Now simulation (hybrid: you post driver, script moves you)
./dev.sh sim-ride solitude

# Or with custom driver name:
./dev.sh sim-ride solitude "Ashley"

# Or with faster simulation (5-second intervals):
./dev.sh sim-ride solitude "Ashley" 5

# Or: Scheduled ride (driver perspective, hybrid mode)
./dev.sh sim-sched solitude driver

# Or: Scheduled ride (passenger perspective, driver moves automatically)
./dev.sh sim-sched solitude passenger
```

**Hybrid workflow:**
1. Script wipes database and creates a passenger
2. Script tells you to open the app and post a driver trip
3. You open Expo app and post trip (e.g., as "Sim Driver" or custom name)
4. Script detects your trip and automatically accepts the match
5. Script moves your driver via location updates (every 10s)
6. You watch the driver (you!) move toward the passenger on the map
7. When driver reaches within 500m, the app shows "Confirm pickup" prompt
   - The API's `GET /trips/{trip_id}/matched-passenger` returns `near_pickup: true` at 0.5 km
   - Keep the prompt visible until the driver taps to confirm; then call confirm-pickup and complete the trip
8. You accept pickup and complete the ride when prompted

---

## Part 1: API Endpoint Tests (`test_flows.py`)

### What Changed

The test suite now validates **geocoding by default**:
- Sends **text addresses only** (no lat/lng)
- API geocodes them via Nominatim
- Tests verify returned coordinates are within 5km of expected location
- Catches geocoding failures that users experience

### Two Modes

#### Address Mode (Default)
```bash
python3 test_flows.py
```
- Tests geocoding pipeline
- Slower (~10-15 seconds due to Nominatim rate limiting)
- Validates addresses like "Sugar House, Salt Lake City" and "Holladay, Utah"
- Uses simple city/neighborhood names that geocode reliably

#### Fast Mode (Skip Geocoding)
```bash
python3 test_flows.py --skip-geocoding
```
- Uses lat/lng directly
- Fast (~5 seconds)
- Skips geocoding validation

### Test Coverage

Both modes test:
- Ride Now full lifecycle (post -> match -> accept -> pickup -> complete)
- Scheduled ride full lifecycle (post -> match -> confirm -> en-route -> pickup -> complete)
- Edge cases (cross-resort, seat overflow, behind driver)

Address mode additionally tests:
- Geocoding accuracy for 8 driver origins
- Geocoding accuracy for 8 passenger pickups
- Reports which addresses fail to geocode

---

## Part 2: iOS Simulator Testing

### Ride Now Simulation (Hybrid Mode)

The simulation uses a **hybrid approach**: you post the driver trip in the app, then the script automatically moves you via API updates.

```bash
# Terminal 1: API running (./dev.sh local)
# Terminal 2:
./dev.sh sim-ride solitude

# Or with custom driver name:
./dev.sh sim-ride solitude "Ashley"

# Or with faster updates (5 seconds):
./dev.sh sim-ride solitude "Ashley" 5
```

**What the script does:**
1. Wipes the database
2. Creates a passenger at a pickup location (e.g., Holladay)
3. **Prints instructions and waits for you to post a driver trip**
4. Polls the API every 2 seconds looking for a driver trip with your specified name (default: "Sim Driver")
5. Once detected, matches and accepts automatically
6. **Pushes your driver location updates via API every 10 seconds** (from GPX waypoints)
7. Updates iOS Simulator location at each waypoint so the map centers correctly
8. Prints progress as you approach the passenger

**What you do:**
1. Wait for script to print "Passenger Ready - Waiting for Driver"
2. Open Expo app on iOS Simulator
3. Select "Ride Now" → "Driver"
4. Post a trip with name "Sim Driver" (or your custom name), destination: Solitude
5. Watch as the script automatically accepts the match
6. Watch your driver marker move toward the passenger automatically on the map
7. Accept pickup when prompted
8. Complete the ride

**Why hybrid?**
- You see the actual app UI and interaction flow
- Script handles tedious location updates (no manual GPX manipulation)
- Tests real user experience from posting to pickup
- Fully observable - watch matches, prompts, and location updates happen in real-time

**How it works:**
- Script posts `PUT /trips/{id}/location` every 10 seconds with GPX waypoints
- This is EXACTLY how production works (Expo app sends location every 15s)
- The Expo app polls the API every 5 seconds and renders the driver's position
- You see yourself approaching the passenger in real-time
- No manual GPS manipulation needed!

### Scheduled Ride Simulation (Hybrid Mode)

Simulates a scheduled ride with pre-confirmed meeting hub.

#### Driver Perspective (Hybrid)
```bash
./dev.sh sim-sched solitude driver
```

**What the script does:**
1. Wipes database
2. Creates driver + passenger (scheduled for today, 7:00 AM / 7:15 AM)
3. Finds and confirms match with optimal hub (e.g., Big Cottonwood Canyon P&R)
4. **Prints instructions and waits for you to tap "I'm on my way"**
5. Polls the API every 2 seconds looking for `driver_en_route_at` to be set
6. Once detected, starts automated route simulation
7. **Pushes driver location updates via API every 10 seconds** (from hub GPX waypoints)
8. Updates iOS Simulator location at each waypoint

**What you do:**
1. Wait for script to print "Match Confirmed - Waiting for En-Route"
2. Open Expo app on iOS Simulator
3. See "Today's Ride" with hub details
4. Tap the "I'm on my way" button
5. Watch as the script automatically starts moving you toward the hub
6. Watch the driver marker move toward the hub on the map
7. Confirm pickup when you arrive at the hub
8. Complete ride

#### Passenger Perspective
```bash
./dev.sh sim-sched solitude passenger
```

**What the script does:**
1. Wipes database
2. Creates driver + passenger (you)
3. Confirms match with hub
4. Sets your Simulator location to passenger pickup
5. **Starts background driver simulation** (driver moves toward hub automatically via `simulate_realtime_tracking.py`)

**What you do:**
1. Open Expo app on iOS Simulator as passenger
2. See "Today's Ride" with hub details
3. Watch driver's marker move toward the hub on your map (automated)
4. Confirm pickup when driver arrives
5. Complete ride

To stop background driver simulation: `pkill -f simulate_realtime_tracking`

---

## GPX Route Files

### Available Routes

| File | Route | Duration | Waypoints |
|------|-------|----------|-----------|
| `gpx/route_to_solitude.gpx` | Sugar House → Solitude | ~3 min @ 10s intervals | 19 |
| `gpx/route_to_park_city.gpx` | Kimball Junction → Park City Mtn | ~1 min @ 10s intervals | 6 |
| `gpx/route_to_hub_bcc_pr.gpx` | Midvale → Big Cottonwood P&R | ~1 min @ 10s intervals | 6 |

### How to Use GPX Files

**Important**: `xcrun simctl` does NOT support GPX files directly. You must use Xcode's Debug menu.

#### Method 1: Via Xcode (Required for GPX files)
1. Open Xcode with your app project
2. Run app on Simulator
3. Xcode menu: **Debug > Simulate Location > Add GPX File...**
4. Navigate to and select: `/Users/ashley/skipool/gpx/route_to_solitude.gpx`
5. Route plays automatically
6. Or: Add GPX to Xcode project first, then select from Debug menu

#### Method 2: Via Simulator Menu (Single Points)
1. Simulator menu: **Features > Location > Custom Location**
2. Enter coordinates manually
3. Or use built-in options: Freeway Drive, City Run, etc.

### GPX Waypoint Times

The `<time>` values in GPX files control playback speed:
- 5-minute gaps = real-time speed
- 1-minute gaps = 5x speed (faster testing)
- 10-second gaps = 30x speed (very fast)

Current routes use **2-minute gaps** (2.5x real-time) for reasonable testing speed.

---

## Complete Test Workflow

### Before Each Test Session
```bash
# Restart the environment if DB connection dropped
# Terminal 1:
./dev.sh local
```

### Full Validation Workflow
```bash
# 1. API tests with geocoding
python3 test_flows.py

# 2. Ride Now simulation
./dev.sh sim-ride solitude
# ... open app, test as driver ...

# 3. Scheduled ride (driver perspective)
./dev.sh sim-sched solitude driver
# ... open app, test as driver ...

# 4. Scheduled ride (passenger perspective)
./dev.sh sim-sched solitude passenger
# ... open app, test as passenger ...
```

### Test Report

After API tests, check `test_report.md` for detailed results including geocoding accuracy.

---

## Address Format Best Practices

The API uses OpenStreetMap's Nominatim geocoder. These address formats work best:

### ✅ Good Addresses (Reliably Geocode)
- Neighborhood + City: `"Sugar House, Salt Lake City"`
- City + State: `"Holladay, Utah"`
- Well-known place: `"Kimball Junction"`
- City name: `"Park City"`
- Area + State: `"Cottonwood Heights"`

### ⚠️ Problematic Addresses
- Specific businesses: `"Marriott Downtown, Salt Lake City, UT"` (too specific)
- Abbreviated state: `"Sandy, UT"` when geocoder adds ", Utah" → `"Sandy, UT, Utah"` (redundant)
- Restaurant names: `"Porcupine Pub & Grille"` (not in OSM database)
- Hotels: `"Homewood Suites Midvale"` (inconsistent in OSM)

### 💡 Tips
- Let the API add "Utah" automatically - don't include "UT" or "Utah" in your address
- Use neighborhoods and cities instead of specific businesses
- When in doubt, use the 📍 GPS button in the app instead of text entry

---

## Troubleshooting

### "API is not reachable"
**Solution**: Start the API with `./dev.sh local` first

### "Failed to set Simulator location"
**Cause**: iOS Simulator not running or `xcrun` not in PATH
**Solution**: 
1. Launch iOS Simulator first
2. Or manually set location: Features > Location > Custom Location

### "Failed to wipe database"
**Cause**: Database connection dropped
**Solution**: Restart: `./dev.sh stop` then `./dev.sh local`

### Geocoding Tests Failing
Check the API logs in Terminal 1 for geocoding errors. Common issues:
- Nominatim timeout (API reduces timeout to 5s for dev)
- Ambiguous addresses (solution: use well-known place names like "Sugar House, Salt Lake City" not specific businesses)
- Rate limiting (solution: use `--skip-geocoding` for fast iteration)
- Too specific addresses (Nominatim works better with neighborhoods/cities than individual businesses)

### GPX Route Not Playing
- Make sure you're using `xcrun simctl location booted start <gpx-file>`
- Or load via Xcode: Debug > Simulate Location
- Check GPX file exists and has correct XML format

---

## Dev Workflow Integration

### Pre-Commit Testing
```bash
# Quick validation before commit
python3 test_flows.py --skip-geocoding
```

### Full Testing Before Deploy
```bash
# Test geocoding + full flows
python3 test_flows.py

# Manual simulator test
./dev.sh sim-ride solitude
```

### Debugging Address Issues
When users report geocoding problems:
```bash
# Test with specific addresses
python3 test_flows.py  # Uses real addresses
# Check test_report.md for which addresses failed
```
