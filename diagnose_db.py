#!/usr/bin/env python3
"""
Query the DB from CLI to diagnose Ride Now matching.
Run with Cloud SQL Proxy and DATABASE_URL set (same as create_test_data.py).
"""
import math
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from database import engine

RESORTS = {
    "Alta": (40.5883, -111.6358),
    "Snowbird": (40.5830, -111.6563),
    "Brighton": (40.5981, -111.5831),
    "Solitude": (40.6199, -111.5919),
    "Park City Mountain": (40.6514, -111.5080),
    "Canyons Village": (40.6853, -111.5562),
    "Deer Valley": (40.6367, -111.4792),
    "Woodward Park City": (40.7589, -111.5761),
}


def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return 2 * math.asin(math.sqrt(a)) * R


def get_bearing(lat1, lon1, lat2, lon2):
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dlon = math.radians(lon2 - lon1)
    y = math.sin(dlon) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlon)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def xtd_km(d_lat, d_lon, r_lat, r_lon, p_lat, p_lon):
    R = 6371
    dist_dp = haversine(d_lat, d_lon, p_lat, p_lon)
    bearing_dr = get_bearing(d_lat, d_lon, r_lat, r_lon)
    bearing_dp = get_bearing(d_lat, d_lon, p_lat, p_lon)
    return abs(math.asin(math.sin(dist_dp / R) * math.sin(math.radians(bearing_dp - bearing_dr))) * R)


def main():
    if not os.getenv("DATABASE_URL"):
        print("Set DATABASE_URL and run Cloud SQL Proxy first, e.g.:")
        print('  export DATABASE_URL="postgresql://postgres:SkiPoolTest_1@127.0.0.1:5432/skipooldb"')
        print("  cloud-sql-proxy skipool-483602:us-central1:skipooldb=tcp:5432 &")
        sys.exit(1)

    with engine.connect() as conn:
        print("=" * 60)
        print("REALTIME TRIPS (Ride Now drivers)")
        print("=" * 60)
        r = conn.execute(text("""
            SELECT id, driver_name, resort, start_lat, start_lng, current_lat, current_lng, available_seats
            FROM trips WHERE is_realtime = true ORDER BY id DESC LIMIT 10
        """))
        rows = r.fetchall()
        if not rows:
            print("No realtime trips found.")
        else:
            for row in rows:
                sid = row[0]
                name = row[1]
                resort = row[2]
                slat, slng = row[3], row[4]
                clat, clng = row[5], row[6]
                seats = row[7]
                lat = clat if clat is not None else slat
                lng = clng if clng is not None else slng
                has_loc = lat is not None and lng is not None
                warn = "  <-- NO LOCATION (app did not send coords when posting)" if not has_loc else ""
                print(f"  id={sid}  {name}  resort={resort}  seats={seats}{warn}")
                print(f"    start_lat/lng={slat},{slng}  current_lat/lng={clat},{clng}  => has_location={has_loc}")

        print()
        print("=" * 60)
        print("PENDING RIDE NOW REQUESTS (passengers)")
        print("=" * 60)
        r = conn.execute(text("""
            SELECT id, passenger_name, resort, pickup_lat, pickup_lng, seats_needed, status, departure_time
            FROM ride_requests WHERE LOWER(TRIM(COALESCE(departure_time, ''))) = 'now' ORDER BY id DESC LIMIT 10
        """))
        rows = r.fetchall()
        if not rows:
            print("No Ride Now requests found.")
        else:
            for row in rows:
                print(f"  id={row[0]}  {row[1]}  resort={row[2]}  pickup={row[3]},{row[4]}  seats_needed={row[5]}  status={row[6]}")

        print()
        print("=" * 60)
        print("MATCH CHECK (each realtime trip vs pending passengers for its resort)")
        print("=" * 60)
        r = conn.execute(text("""
            SELECT id, driver_name, resort, start_lat, start_lng, current_lat, current_lng, available_seats
            FROM trips WHERE is_realtime = true ORDER BY id DESC
        """))
        trips = r.fetchall()
        for trip in trips:
            tid, tname, resort, slat, slng, clat, clng, seats = trip
            dlat = clat if clat is not None else slat
            dlng = clng if clng is not None else slng
            print(f"\n--- Trip id={tid}  {tname}  resort={resort} ---")
            if dlat is None or dlng is None:
                print("  NO LOCATION => match-nearby-passengers returns []. Set simulator Custom Location before opening app, then re-post.")
                continue
            if resort not in RESORTS:
                print(f"  Resort '{resort}' not in RESORTS map.")
                continue
            r_lat, r_lng = RESORTS[resort]
            r2 = conn.execute(text("""
                SELECT id, passenger_name, pickup_lat, pickup_lng, seats_needed
                FROM ride_requests WHERE LOWER(TRIM(COALESCE(departure_time, ''))) = 'now' AND status = 'pending' AND resort = :resort
            """), {"resort": resort})
            passengers = r2.fetchall()
            print(f"  Driver location=({dlat}, {dlng})  seats={seats}  pending passengers={len(passengers)}")
            for row in passengers:
                pid, pname, plat, plng, pseats = row
                if plat is None or plng is None:
                    print(f"    id={pid} {pname}  NO PICKUP COORDS  => skip")
                    continue
                xtd = xtd_km(dlat, dlng, r_lat, r_lng, plat, plng)
                ok_seats = seats >= (pseats or 1)
                ok_xtd = xtd < 2.0
                match = ok_seats and ok_xtd
                print(f"    id={pid} {pname}  pickup=({plat},{plng})  xtd={xtd:.3f}km  => {'MATCH' if match else 'no match'}")
        if not trips:
            print("No realtime trips to check.")

    print()
    print("Done.")


if __name__ == "__main__":
    main()
