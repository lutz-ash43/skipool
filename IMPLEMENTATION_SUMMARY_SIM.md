# Implementation Summary: Address Tests + Simulator Integration

## What Was Built

### 1. Address-Based API Tests ✓

Updated `test_flows.py` to validate geocoding by default:
- **Sends text addresses** instead of lat/lng (e.g., "Marriott Downtown, Salt Lake City, UT")
- **Validates geocoding accuracy** - checks returned coordinates are within 5km of expected
- **New flag**: `--skip-geocoding` for fast testing without geocoding delays
- **22+ test steps** now validate the geocoding pipeline

### 2. GPX Route Files ✓

Created three realistic route files in `gpx/`:
- `route_to_solitude.gpx` - Engen Hus B&B → Solitude (25 min, 10 waypoints)
- `route_to_park_city.gpx` - Kimball Junction → Park City (10 min, 6 waypoints)
- `route_to_hub_bcc_pr.gpx` - Midvale → Big Cottonwood P&R hub (10 min, 6 waypoints)

All follow actual canyon roads (not straight-line interpolation).

### 3. Simulation Setup Script ✓

Created `sim_ride.py` that automates the entire test setup:
- Wipes the database via API
- Seeds test data using addresses (validates geocoding)
- Sets iOS Simulator location via `xcrun simctl`
- Optionally starts GPX route playback
- Supports both Ride Now and Scheduled modes
- Supports driver and passenger perspectives

### 4. Dev.sh Commands ✓

Added two new commands:

```bash
./dev.sh sim-ride [resort]              # Ride Now simulation
./dev.sh sim-sched [resort] [driver|passenger]  # Scheduled simulation
```

---

## How To Use

### Quick Test (API Only)

```bash
# Terminal 1: Start API
./dev.sh local

# Terminal 2: Run tests
./dev.sh test

# Or with geocoding validation
python3 test_flows.py
```

### Full Simulator Test (Ride Now)

```bash
# Terminal 1: API running
./dev.sh local

# Terminal 2: Set up simulation
./dev.sh sim-ride solitude

# iOS Simulator: Open Expo app → Post trip as driver → See passenger → Drive (GPX playing)
```

### Full Simulator Test (Scheduled - Driver)

```bash
# Terminal 2:
./dev.sh sim-sched solitude driver

# iOS Simulator: Open app → See Today's Ride → Tap "I'm on my way" → Drive to hub
```

### Full Simulator Test (Scheduled - Passenger)

```bash
# Terminal 2:
./dev.sh sim-sched solitude passenger

# iOS Simulator: Open app as passenger → Watch driver approach hub (automated)
```

---

## What Gets Validated

### API Tests (`test_flows.py`)
- ✓ Geocoding accuracy for 16 unique addresses
- ✓ POST /trips/ with address-only input
- ✓ POST /ride-requests/ with address-only input
- ✓ Complete lifecycle: post → match → accept → pickup → complete
- ✓ Edge cases: cross-resort, seat overflow, behind driver

### Simulator Tests (via sim_ride.py)
- ✓ iOS app location tracking (CoreLocation → Expo → API)
- ✓ Real-time matching as driver moves along route
- ✓ Map rendering with markers and routes
- ✓ Pickup prompts trigger correctly
- ✓ Hub-based meeting (scheduled rides)
- ✓ "On the way" mode for scheduled rides
- ✓ Background driver simulation for passenger perspective

---

## Key Technical Points

### How GPX → API Flow Works

1. **GPX file loaded** → iOS Simulator CoreLocation
2. **Expo app polls** CoreLocation (continuously checks GPS)
3. **Every 15 seconds** → App sends `PUT /trips/{id}/location`
4. **Backend updates** `current_lat`, `current_lng`, `last_location_update`
5. **Matching re-runs** → Other user sees updated location

This is completely automated once the GPX starts playing.

### Why Addresses in Tests Matter

The original tests bypassed geocoding by sending lat/lng directly. This missed issues where:
- Addresses don't geocode (typos, ambiguous names)
- Geocoding times out (Nominatim slowness)
- Returned coordinates are wrong (Nominatim mistakes)

Now tests catch these before users do.

### Scheduled Ride Passenger Perspective

When you run `./dev.sh sim-sched solitude passenger`:
- Script creates driver + passenger
- Confirms their match at a hub
- Starts `simulate_realtime_tracking.py` in background
- This script moves the driver's location in the DB every 15 seconds
- Your Expo app polls the driver's location every 5 seconds
- You see the driver marker move on your map

To stop: `pkill -f simulate_realtime_tracking`

---

## Files Created/Modified

### New Files
- `gpx/route_to_solitude.gpx`
- `gpx/route_to_park_city.gpx`
- `gpx/route_to_hub_bcc_pr.gpx`
- `sim_ride.py`
- `SIMULATION_GUIDE.md`
- `TEST_VERIFICATION.md`
- `IMPLEMENTATION_SUMMARY_SIM.md` (this file)

### Modified Files
- `test_flows.py` - address-based tests, geocoding validation
- `dev.sh` - added `sim-ride` and `sim-sched` commands
- `.gitignore` - already has `test_report.md`

---

## Next Time You Need To Verify

After restarting the environment (`./dev.sh local`), run:

```bash
# 1. Fast API test
python3 test_flows.py --skip-geocoding

# 2. Full API test with geocoding
python3 test_flows.py

# 3. Simulator test
./dev.sh sim-ride solitude
```

All three should complete successfully!
