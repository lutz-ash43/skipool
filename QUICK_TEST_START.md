# Quick Test Start Guide

## 🚀 Fastest Way to Test

### Step 1: Create Test Data (30 seconds)

```bash
cd /Users/ashley/skipool
python create_test_data.py
```

**Output**: You'll get IDs like:
- Driver 1 (Ride Now to Solitude): ID 1
- Passenger 1 (Ride Now to Solitude): ID 1
- Driver 3 (Scheduled to Solitude): ID 3
- Passenger 3 (Scheduled to Solitude): ID 3

### Step 2: Start Continuous Location Simulation

**Terminal 1** - Simulate driver:
```bash
python simulate_realtime_tracking.py --trip-id 1 --interval 15.0
```

Ride Now passengers are at pickup; we don't track their location. **Do not** run `--request-id` for Ride Now passengers. For **scheduled en-route** only, you can run:
```bash
python simulate_realtime_tracking.py --request-id 3 --interval 15.0
```

### Step 3: Test in iOS Simulator

1. **Open app** in iOS Simulator
2. **As Driver**:
   - Select "Ride Now"
   - Name: "Test Driver - Solitude"
   - Use GPS (or set custom location: `40.6409, -111.8175` for Engen Hus / Solitude route)
   - Select "Solitude" resort
   - Post trip
   - **Watch**: Passenger should appear as backend script updates locations

3. **As Passenger** (new simulator or switch):
   - Select "Ride Now"
   - Name: "Test Passenger - Solitude"
   - Use GPS **at pickup** (set custom: `40.621, -111.791` for The Swamp Lot)
   - Select "Solitude" resort
   - Post request
   - **Watch**: Driver should appear and move on map; you stay at pickup

## 📱 iOS Simulator Location Setup

### Quick Method (Recommended)

Test data uses **clustered locations** for faster matching:

1. **Features → Location → Custom Location**
2. **Solitude route**: `40.6409, -111.8175` (Engen Hus B&B – driver start)
3. **Passenger pickup**: `40.621, -111.791` (The Swamp Lot)
4. **Park City route**: `40.75, -111.57` (Quarry Condos) or `40.755, -111.572` (Jeremy Ranch)

### Automatic Movement

**Features → Location → Freeway Drive**

This simulates continuous movement automatically - perfect for testing!

## 🎯 Test Scenarios

### Scenario A: Ride Now – Solitude (5 minutes)

1. ✅ Run `create_test_data.py`
2. ✅ Start `simulate_realtime_tracking.py --trip-id 1`
3. ✅ Open app as **Driver** → Post trip to **Solitude** (use location `40.6409, -111.8175`)
4. ✅ Open app as **Passenger** → Post request to **Solitude** (use location `40.621, -111.791` – The Swamp Lot)
5. ✅ Watch matches appear and update in real-time

### Scenario B: Ride Now – Park City (5 minutes)

1. ✅ Run `create_test_data.py`
2. ✅ Start `simulate_realtime_tracking.py --trip-id 2`
3. ✅ Open app as **Driver** → Post trip to **Park City Mountain** (use `40.75, -111.57`)
4. ✅ Open app as **Passenger** → Post request to **Park City Mountain** (use `40.755, -111.572` – Jeremy Ranch)
5. ✅ Watch matches appear

### Scenario C: Scheduled En-Route – Solitude (10 minutes)

1. ✅ Run `create_test_data.py`
2. ✅ Open app as **Driver** → Schedule mode → Post trip (**Solitude**, 7:00 AM)
3. ✅ Open app as **Passenger** → Schedule mode → Post request (**Solitude**, 7:30 AM)
4. ✅ Confirm match
5. ✅ **Change simulator date to tomorrow** (Device → Date & Time)
6. ✅ App shows "Today's ride" → Tap "I'm on my way"
7. ✅ Run: `python simulate_location.py --trip-id 3 --hub-lat 40.62 --hub-lng -111.80 --steps 10 --delay 2.0`
8. ✅ Optional: `python simulate_location.py --request-id 3` (passenger moving to hub)
9. ✅ Watch driver/passenger move to meeting point on map

### Scenario D: Scheduled En-Route – Park City (10 minutes)

Same as C, but use **Park City Mountain**, trip-id **4**, request-id **4**, and hub near Jeremy Ranch (e.g. `40.755, -111.572`).

## 🔧 Troubleshooting

### No matches appearing?

1. **Set location before opening the app** – Simulator → Features → Location → Custom Location → `40.621, -111.791` (Swamp Lot). Then fully quit and reopen the app so it reads the new coordinates. If you set location after the app loaded, the trip may have no coordinates.
2. **Check locations**: Use the custom locations from the guide (Engen Hus, Swamp Lot, Jeremy Ranch)
3. **Check resort**: Tap **Solitude** on the map before posting; must match exactly
4. **Check seats**: Driver must have enough seats
5. **Debug endpoint**: After posting, call `GET /match-nearby-passengers/debug?trip_id=YOUR_TRIP_ID&resort=Solitude` to see why no matches (e.g. trip has no location)

### Location not updating?

1. **Check backend script**: Is it running? Check terminal output
2. **Check database**: Query `SELECT current_lat, current_lng FROM trips WHERE id = 1;`
3. **Check app**: Is location permission granted?

### Matches not refreshing?

- App polls every **15 seconds**
- Backend script updates every **15 seconds** (default)
- Wait a bit, or reduce interval: `--interval 5.0`

## 📊 Useful Commands

```bash
# Create fresh test data
python create_test_data.py

# Simulate one-time movement (10 steps, 2s each)
python simulate_location.py --trip-id 1 --steps 10 --delay 2.0

# Continuous tracking (updates every 15s)
python simulate_realtime_tracking.py --trip-id 1 --interval 15.0

# Check what's in database
# (Connect to your DB and run):
SELECT id, driver_name, resort, current_lat, current_lng, available_seats 
FROM trips 
WHERE driver_name LIKE 'Test%';
```

## 💡 Pro Tips

1. **Use two simulators**: One for driver, one for passenger
2. **Use Freeway Drive**: Automatic movement in simulator
3. **Combine methods**: Backend script + simulator location = best testing
4. **Watch backend logs**: See API calls in real-time
5. **Use debug endpoint**: `GET /match-scheduled/debug?resort=Solitude&target_date=YYYY-MM-DD` (use tomorrow's date)

## 🎬 Full Test Flow Example

```bash
# Terminal 1: Create data
python create_test_data.py

# Terminal 2: Simulate driver (Ride Now)
python simulate_realtime_tracking.py --trip-id 1 --interval 10.0

# iOS Simulator: Test app
# - Driver posts trip
# - Passenger posts request (at pickup)
# - Watch matches appear; driver navigates to pickup
# (No passenger simulation for Ride Now—they're at pickup.)
```

---

**See `TESTING_GUIDE.md` for detailed scenarios and `IOS_SIMULATOR_LOCATION.md` for location setup details.**
