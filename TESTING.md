# SkiPool Testing Guide

## Overview

The SkiPool application now has a comprehensive end-to-end test suite that validates the entire ride lifecycle for both **Ride Now** and **Scheduled** rides.

## Quick Start

### Run Tests Locally

```bash
# Start the local development environment (in one terminal)
./dev.sh local

# Run tests (in another terminal)
./dev.sh test
```

### Run Tests Against Cloud

```bash
# Start cloud environment (in one terminal)
./dev.sh cloud

# Run tests (in another terminal)
./dev.sh test
```

## Test Script: `test_flows.py`

The test script can be run directly for more control:

```bash
# Default (localhost:8080)
python3 test_flows.py

# Explicit URL
python3 test_flows.py --base-url http://localhost:8080

# Cloud environment
python3 test_flows.py --base-url https://your-cloud-run-url.run.app

# Skip database wipe (run on existing data)
python3 test_flows.py --no-wipe
```

## What Gets Tested

### 1. Ride Now (Real-Time) Lifecycle
Tests the complete flow for immediate rides:
- ✓ Driver posts trip with GPS location
- ✓ Passenger posts ride request with pickup location
- ✓ Matching algorithms find each other
- ✓ Driver accepts passenger
- ✓ Both parties see match details
- ✓ Both parties confirm pickup
- ✓ Driver completes ride

### 2. Scheduled Ride Lifecycle
Tests the complete flow for future rides:
- ✓ Driver posts trip for today with departure time
- ✓ Passenger posts request with similar time window
- ✓ System finds optimal meeting hub
- ✓ Match is confirmed with hub selection
- ✓ Both parties see match + hub details
- ✓ Driver starts "en route" mode on scheduled day
- ✓ Driver location updates work
- ✓ Both confirm pickup at hub
- ✓ Driver completes ride

### 3. Edge Cases
Tests that invalid matches are correctly rejected:
- ✓ No match across different resorts (Solitude vs Park City)
- ✓ No match when insufficient seats (1 seat vs 2 needed)
- ✓ No match when passenger behind driver

## Test Data

### Automatic Database Reset
By default, the test script wipes all existing trips and ride requests before running, ensuring a clean slate every time.

### Realistic Test Locations
The script uses real Salt Lake City area locations to make tests more realistic:

**Driver Starting Points (Hotels/Residences):**
- The Engen Hus B&B
- Marriott SLC Downtown
- Hyatt Place Cottonwood
- Homewood Suites Midvale
- Hampton Inn Sandy
- Kimball Junction Lodges, Park City
- Treasure Mountain Inn, Park City
- Newpark Resort, Park City

**Passenger Pickup Points (Restaurants/Cafes):**
- Porcupine Pub & Grille
- Cotton Bottom Inn
- The Hogwallow Pub
- Bohemian Brewery
- Millcreek Coffee Roasters
- Squatters Roadhouse, Park City
- Wasatch Brew Pub, Park City
- Five Seed Cafe, Jeremy Ranch

Each test run randomly selects from these pools, so matching geometry varies between runs.

## Test Report

After each run, the script generates `test_report.md` with:
- Timestamp and target URL
- Summary statistics (total/passed/failed)
- Detailed results for each test step
- HTTP status codes and response details

Example output:
```
# SkiPool Test Report

**Date**: 2026-02-14 18:44:02  
**Target**: http://localhost:8080  
**DB Reset**: Yes

## Summary
- **Total Tests**: 22
- **Passed**: 22 ✓
- **Failed**: 0 ✗
- **Success Rate**: 100.0%
```

## Exit Codes

The test script exits with:
- `0` if all tests pass
- `1` if any tests fail

This makes it suitable for CI/CD pipelines.

## Troubleshooting

### API Not Running
```
Error: API is not reachable at http://localhost:8080
```
**Solution**: Start the API with `./dev.sh local` or `./dev.sh cloud`

### Tests Fail Due to Existing Data
```
Some tests failed due to unexpected matches
```
**Solution**: The script wipes the DB by default, but if you used `--no-wipe`, try running without it

### 500 Errors During Tests
Check the API terminal output for stack traces. The most recent fix addressed SQLAlchemy query issues with `.strip()` vs `func.trim()`.

## Integration with Development Workflow

1. **Before committing code**: Run `./dev.sh test` to ensure changes don't break functionality
2. **After merging**: Run tests to verify integration
3. **Before deploying**: Run tests against cloud environment with `./dev.sh cloud` then `./dev.sh test`

## Future Enhancements

Potential additions to the test suite:
- Return trip flows
- Multiple passengers per trip
- Trip cancellation flows
- Location tracking during ride
- Time-based matching edge cases
- Hub distance calculations
