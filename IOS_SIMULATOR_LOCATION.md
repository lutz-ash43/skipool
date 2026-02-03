# iOS Simulator Location Testing - Quick Reference

## Method 1: Custom Location (Manual)

1. **Set location**:
   - Simulator menu: **Features → Location → Custom Location...**
   - Enter coordinates: `40.7244, -111.8881` (Sugar House)
   - Click **OK**

2. **Update periodically**:
   - Change coordinates to simulate movement
   - Example progression to Alta:
     - `40.7244, -111.8881` (Sugar House)
     - `40.7000, -111.8000` (Moving)
     - `40.6500, -111.7500` (Canyon)
     - `40.5883, -111.6358` (Alta)

## Method 2: Built-in Movement (Automatic)

**Features → Location →**:
- **City Bicycle Ride** - Slow movement
- **City Run** - Medium speed
- **Freeway Drive** - Fast movement

These simulate continuous movement automatically.

## Method 3: GPX File (Most Realistic)

1. **Add GPX to Xcode project**:
   - Drag `test_route.gpx` into your Xcode project
   - Make sure it's included in the target

2. **Select in Simulator**:
   - **Features → Location → [Your GPX file name]**
   - Simulator follows the route automatically

3. **Create custom GPX**:
   - Use `test_route.gpx` as template
   - Add waypoints along your test route
   - Times are used for playback speed

## Method 4: Multiple Simulators (Driver + Passenger)

1. **Open second simulator**:
   - Xcode: **Window → Devices and Simulators**
   - Click **+** button
   - Select device type (e.g., iPhone 15)
   - Click **Create**

2. **Run app on both**:
   - Select different simulators in Xcode
   - Run app on each
   - Set different locations for each

3. **Test interaction**:
   - Driver on one simulator
   - Passenger on another
   - Watch real-time matching

## Common Test Locations

```
Sugar House:        40.7244, -111.8881
Downtown SLC:       40.7608, -111.8910
Midvale:            40.6192, -111.8983
Park City:          40.6461, -111.4980
Alta Resort:        40.5883, -111.6358
Snowbird Resort:    40.5830, -111.6563
Park City Mountain: 40.6514, -111.5080
```

## Testing Workflow

### Quick Test (Ride Now)

1. **Driver**:
   - Set location: Sugar House (`40.7244, -111.8881`)
   - Post trip to Alta
   - Use **Freeway Drive** to simulate movement

2. **Passenger**:
   - Set location: Sugar House (same—you're at pickup)
   - Post request to Alta
   - Should see driver matches

3. **Watch**:
   - As driver moves, passenger sees them on map
   - Driver sees passenger at **pickup** (static); navigates there. Passenger doesn't move.

### Scheduled Test (Day-of)

1. **Create match** (both confirm)
2. **Change simulator date to tomorrow**:
   - Simulator → **Device → Date & Time**
   - Uncheck "Set Automatically"
   - Set date to tomorrow
3. **Open app** → Should see "Today's ride" en-route screen
4. **Tap "I'm on my way"**
5. **Simulate movement** using any method above

## Pro Tips

1. **Use GPX for repeatable tests** - Same route every time
2. **Use Freeway Drive for quick tests** - Automatic movement
3. **Use Custom Location for precise control** - Exact coordinates
4. **Run two simulators** - Test driver/passenger interaction
5. **Combine with backend script** - Use `simulate_location.py` for **driver** DB updates (Ride Now) or **scheduled en-route**; passengers at pickup are not simulated.
