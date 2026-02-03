# Testing Approaches: iOS Simulator vs Backend Scripts

## The Key Difference

### iOS Simulator Location (Freeway Drive)
- **Updates the simulator's location** → App reads it → **App sends to backend** → Backend updates DB
- Requires: App running, location permissions, app actively sending updates
- Tests: Full app flow including location permission, API calls, error handling

### Backend Script (`simulate_realtime_tracking.py`)
- **Directly updates the database** → Bypasses the app entirely
- Requires: Just the script running
- Tests: Matching logic, multiple users, scenarios without app

## When to Use Each

### Use iOS Simulator Location When:

✅ **Testing the full app flow**
- You want to test location permissions
- You want to test the app sending location updates
- You want to test error handling (network issues, etc.)
- You're testing as a single user (driver OR passenger)

✅ **Testing UI/UX**
- You want to see how the app behaves
- You want to test user interactions
- You want to verify the map updates correctly

### Use Backend Script When:

✅ **Testing matching logic**
- You want to test if matches appear correctly
- You want to test seat-based filtering
- You want to test route-based matching
- You don't need to test the app's location sending

✅ **Testing multiple users simultaneously**
- You want to simulate driver AND passenger at the same time
- You're testing scheduled rides (simulate the other person)
- You want to test edge cases (multiple drivers, multiple passengers)

✅ **Testing without app running**
- You want to populate test data
- You want to verify backend logic
- You're debugging matching issues

✅ **Testing specific scenarios**
- You want precise control over location updates
- You want to test specific routes or locations
- You want to test timing issues

## Recommended Approach

### For Most Testing: **iOS Simulator Only**

If you're testing as a **single user** (driver OR passenger), iOS Simulator with **Freeway Drive** is sufficient:

1. Open app in simulator
2. Set location: **Features → Location → Freeway Drive**
3. Post trip/request
4. App automatically sends location updates every 15 seconds
5. Watch matches appear and update

**You don't need the backend script for this!**

### When You DO Need Backend Script:

**Scenario 1: Testing Ride Now – Driver + Passenger**

- **Simulator**: Run app as driver, use Freeway Drive
- **Backend script**: Not needed for passenger. Ride Now passengers are **at pickup**; we don't track their location. Driver sees them at a **static** pickup point.
- **Result**: Driver sees passenger at pickup, navigates there. Use `create_test_data.py` to add a passenger at a pickup; no passenger simulation.

**Scenario 2: Testing Scheduled Rides**

- You confirm a match as driver
- On the day of, you want to see passenger moving to meeting point
- **Backend script**: Simulate passenger location
  ```bash
  python simulate_realtime_tracking.py --request-id 3 --interval 15.0
  ```
- **Result**: Driver sees passenger moving even if passenger app isn't running

**Scenario 3: Testing Multiple Matches (Ride Now)**

- You want to test if driver sees multiple passengers
- **Backend script**: Not needed. Use `create_test_data.py` to add multiple Ride Now passengers at different pickups. They're static; driver sees them on route.
- For **scheduled** en-route, you can simulate multiple passengers: `--request-id 3` and `--request-id 4` (optional).

## Hybrid Approach (Best of Both)

**For comprehensive testing:**

1. **iOS Simulator**: Test as driver with Freeway Drive (or as passenger at pickup)
2. **Backend script**: For Ride Now, use `create_test_data` only (passengers at pickups). For **scheduled en-route**, simulate the other person.
3. **Result**: Test full interaction; Ride Now drivers navigate to static pickup.

## Summary

| Scenario | iOS Simulator | Backend Script | Why |
|----------|---------------|----------------|-----|
| Single user testing | ✅ | ❌ | App handles everything |
| Ride Now: Driver + Passenger | ✅ | ❌ | Passenger at pickup (static); driver only moves |
| Scheduled ride (other person) | ✅ | ✅ | Simulate matched person en-route |
| Multiple matches (Ride Now) | ✅ | ❌ | create_test_data; passengers at pickups |
| Testing matching logic only | ❌ | ✅ | Don't need app |
| Testing app location sending | ✅ | ❌ | Need app to test (driver only for Ride Now) |

## Quick Decision Tree

**Q: Are you testing as a single user?**
- **Yes** → Use iOS Simulator only (Freeway Drive)
- **No** → Use iOS Simulator + Backend script

**Q: Do you need to see the other person moving?**
- **Ride Now** → No. Passenger is at pickup (static). iOS Simulator only.
- **Scheduled en-route** → Yes → Use backend script for the other person

**Q: Are you testing scheduled rides?**
- **Yes** → Use backend script to simulate matched person
- **No** → iOS Simulator might be enough

## Example: Testing Ride Now (Single User)

**You only need iOS Simulator:**

1. Open app as driver
2. Features → Location → Freeway Drive
3. Post trip
4. App sends location updates automatically
5. Watch for passenger matches

**No backend script needed!** ✅

## Example: Testing Ride Now (Both Users)

**iOS Simulator + create_test_data only:**

1. Run `create_test_data.py` (adds Ride Now driver + passenger at pickups)
2. **iOS Simulator**: Open app as driver, use Freeway Drive; or as passenger at pickup
3. **Result**: Driver sees passenger at **pickup** (static). Driver navigates there. No passenger location script—they're already there.

**TL;DR**: Ride Now: passengers at pickup, no tracking. Use backend scripts only for **scheduled en-route** (simulate the other person moving to hub) or driver movement.
