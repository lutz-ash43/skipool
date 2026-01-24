# No Matches – Troubleshooting

## Changes made to fix “no matches”

### 1. **Hub filter relaxed**
- **Before**: Hub had to be within **1.5 km** of the driver’s route → often no hubs qualified.
- **After**: Hub within **5 km** of the route.
- **Fallback**: If no hub is on the route, we still create a match with **“Meet at driver’s start”** as the meeting point.

### 2. **Time parsing**
- **Before**: `"7:00 AM"` could fail (e.g. `"00 "` with trailing space).
- **After**: More robust parsing with `.strip()` and clearer handling of `AM`/`PM`.

### 3. **Date handling**
- **Mobile**: “Tomorrow” now uses **local date** (`toLocalDateStr`) instead of `toISOString()`, so driver and passenger use the same calendar date.
- **Backend**: Date comparison handles both `date` and `datetime` from the DB.

### 4. **Debug endpoint**
- **`GET /match-scheduled/debug?resort=Alta&target_date=2026-01-23`**
- Use the **same** `resort` and `target_date` as your `match-scheduled` call.
- Returns:
  - `trips_count` / `requests_count` for that date
  - `pairs_with_time_ok` (time window ≤ 60 min)
  - Sample trips and requests

## How to debug

### 1. Call the debug endpoint

```bash
# Use tomorrow's date in YYYY-MM-DD, and your resort
curl "https://YOUR_API/match-scheduled/debug?resort=Alta&target_date=2026-01-23"
```

Check:
- `trips_count` and `requests_count` > 0
- `pairs_with_time_ok` > 0  
If any of these are 0, that explains why you get no matches.

### 2. Verify Schedule flow

- **Driver**: Schedule tab → name, location, resort, time → **Confirm Schedule**.
- **Passenger**: Same → **Confirm Schedule**.
- Both must use **Schedule** (not Ride Now), same **resort**, same **date** (tomorrow), and **departure times within 60 minutes**.

### 3. Ride Now vs Schedule

- **Ride Now**: Driver and passenger must **post** a trip/request first (e.g. from a “Go” / “Find ride” flow). The map matching uses those posted trips/requests.
- **Schedule**: Both post via **Confirm Schedule**; matching is done by **match-scheduled** (date, time, resort, hub).

## Quick checklist

- [ ] **Tap Refresh** if you posted first (e.g. as driver). Matches are fetched only after *you* post; the other person may post later.
- [ ] Driver and passenger both used **Schedule** (not Ride Now).
- [ ] Same **resort** (e.g. both “Alta”).
- [ ] Same **date** (tomorrow); debug endpoint uses same `target_date`.
- [ ] **Departure times within 60 minutes** (e.g. 7:00 AM and 7:30 AM).
- [ ] Both provided **location** (GPS or address).
- [ ] Debug endpoint shows `trips_count` and `requests_count` > 0 and `pairs_with_time_ok` > 0.

## If you still get no matches

1. Run the **debug** request and share:
   - `trips_count`, `requests_count`, `pairs_would_match`, `skip_time`, `skip_coords`
   - One sample from `trips_sample` and `requests_sample`.
2. Confirm **resort** string matches exactly (e.g. `"Alta"` vs `"Park City Mountain"`).
3. Confirm **target_date** format is `YYYY-MM-DD` and matches what the app sends for “tomorrow”.
