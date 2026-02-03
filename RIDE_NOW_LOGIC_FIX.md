# Ride Now Logic

## Core Principle: Drivers Never Wait

**Passengers are already at pickup when they open the app.** We do not track passenger location. This ensures drivers never wait for passengers.

## How It Works

### Driver Flow
1. Driver posts trip → gets `trip_id`
2. Driver's location is tracked via `PUT /trips/{trip_id}/location` (every 15s)
3. Driver calls `GET /match-nearby-passengers/?trip_id={trip_id}&resort={resort}`
   - Backend uses driver's **current location** (as they drive)
   - Finds passengers whose **pickup** (where they're waiting) is on the route
4. Passengers appear on map as driver drives
5. Driver accepts → navigates to **pickup** (static). Passenger is waiting there.

### Passenger Flow
1. Passenger is **already at pickup** when they open the app
2. Passenger posts request → gets `request_id`
3. **No location tracking** for Ride Now passengers
4. Passenger calls `GET /match-nearby-drivers/?request_id={request_id}&resort={resort}` (poll every 15s)
   - Backend uses passenger's **pickup** (where they're waiting)
   - Finds drivers who will pass that point
5. Drivers appear on map. Passenger accepts → sees driver approaching (we track driver).

## Backend

- **match-nearby-passengers**: Uses passenger **pickup_lat/lng** only. Passenger is at pickup.
- **match-nearby-drivers**: Uses passenger **pickup_lat/lng** only.
- **PUT /ride-requests/{id}/location**: **Rejected** for Ride Now. Only scheduled en-route.
- **create_ride_request**: Ride Now → `current_lat`/`current_lng` = `None`. Pickup only.
- **matched-passenger**: Returns **pickup** as navigate-to for Ride Now (driver goes to pickup).

## Mobile

- **Drivers**: Location updates every 15s. Match polling. When matched, navigate to pickup.
- **Passengers**: No location updates. Match polling only (15s). When matched, track driver.
- **Copy**: "Navigate to pickup — passenger is waiting", "Passenger is at pickup. Navigate there to pick them up!"

## Scheduled Rides

Scheduled en-route still tracks both driver and passenger (they're moving to the meeting hub). Ride Now is pickup-only for passengers.
