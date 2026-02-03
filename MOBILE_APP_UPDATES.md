# Mobile App Updates Required for Scheduled Rides

## Current Issues

1. **Missing Date Field**: The app doesn't send `trip_date` or `request_date` when posting scheduled rides
2. **No Matching Call**: After posting, it doesn't call `/match-scheduled/` endpoint
3. **No Match Display**: No UI to show matches or hub suggestions
4. **Immediate Mode Switch**: After posting scheduled ride, it switches back to "now" mode instead of showing matches

## Required Changes to `skipool-mobile/app/(tabs)/index.tsx`

### 1. Add State for Matches and Date

```typescript
const [scheduledMatches, setScheduledMatches] = useState<any[]>([]);
const [showMatches, setShowMatches] = useState(false);
const [postedTripId, setPostedTripId] = useState<number | null>(null);
```

### 2. Update `submitTrip` Function

**Add date field when posting:**
```typescript
// Calculate tomorrow's date
const tomorrow = new Date();
tomorrow.setDate(tomorrow.getDate() + 1);
const tomorrowStr = tomorrow.toISOString().split('T')[0]; // Format: "2026-01-23"

const body = role === 'driver' 
  ? {
      // ... existing fields ...
      trip_date: mode === 'future' ? tomorrowStr : null,  // ADD THIS
      is_realtime: mode === 'now'
    }
  : {
      // ... existing fields ...
      request_date: mode === 'future' ? tomorrowStr : null,  // ADD THIS
    };
```

**After successful post, fetch matches (for scheduled rides):**
```typescript
if (res.ok) {
  const data = await res.json();
  
  if (mode === 'future') {
    // Store the posted trip/request ID
    setPostedTripId(data.id);
    
    // Fetch matches
    await fetchScheduledMatches(selectedResort.name);
    setShowMatches(true);
  } else {
    Alert.alert("Success", "Your request is active!");
    if (mode === 'future') setMode('now');
  }
}
```

### 3. Add `fetchScheduledMatches` Function

**Important:** Check `res.ok` before calling `res.json()`. If the server returns 500 or plain text, `res.json()` throws "SyntaxError: JSON parse error unexpected character : I" (e.g. body is "Internal Server Error").

```typescript
const fetchScheduledMatches = async (resort: string) => {
  try {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const tomorrowStr = tomorrow.toISOString().split('T')[0];

    const res = await fetch(
      `${API_URL}/match-scheduled/?resort=${encodeURIComponent(resort)}&target_date=${tomorrowStr}`
    );
    if (!res.ok) {
      const text = await res.text();
      console.warn("match-scheduled non-OK:", res.status, text);
      setScheduledMatches([]);
      return;
    }
    const data = await res.json();
    setScheduledMatches(Array.isArray(data) ? data : []);
  } catch (e) {
    console.error("Error fetching matches:", e);
    setScheduledMatches([]);
    Alert.alert("Error", "Could not fetch matches");
  }
};
```

### 4. Add Match Display UI

**Add after the "Confirm Schedule" button in Schedule mode:**

```typescript
{showMatches && scheduledMatches.length > 0 && (
  <View style={styles.matchesContainer}>
    <Text style={styles.matchesTitle}>Available Matches</Text>
    {scheduledMatches.map((match, idx) => (
      <View key={idx} style={styles.matchCard}>
        <View style={styles.matchHeader}>
          <Text style={styles.matchName}>
            {role === 'driver' ? match.passenger_name : match.driver_name}
          </Text>
          <Text style={styles.matchTime}>
            {role === 'driver' 
              ? `Passenger: ${match.passenger_departure_time}`
              : `Driver: ${match.driver_departure_time}`
            }
          </Text>
        </View>
        
        <View style={styles.hubInfo}>
          <Text style={styles.hubLabel}>Suggested Pickup:</Text>
          <Text style={styles.hubName}>{match.suggested_hub.name}</Text>
          <Text style={styles.hubDistance}>
            {role === 'driver'
              ? `Your distance: ${match.hub_distance_driver.toFixed(1)} km`
              : `Your distance: ${match.hub_distance_passenger.toFixed(1)} km`
            }
          </Text>
        </View>
        
        <TouchableOpacity 
          style={styles.confirmBtn}
          onPress={() => handleConfirmMatch(match)}
        >
          <Text style={styles.confirmBtnText}>Confirm Match</Text>
        </TouchableOpacity>
      </View>
    ))}
  </View>
)}

{showMatches && scheduledMatches.length === 0 && (
  <View style={styles.noMatchesContainer}>
    <Text style={styles.noMatchesText}>
      No matches found yet. Check back later!
    </Text>
    <TouchableOpacity 
      style={styles.refreshBtn}
      onPress={() => fetchScheduledMatches(selectedResort.name)}
    >
      <Text style={styles.refreshBtnText}>Refresh</Text>
    </TouchableOpacity>
  </View>
)}
```

### 5. Add Confirm Match Handler

```typescript
const handleConfirmMatch = async (match: any) => {
  // Update the ride request with matched trip and hub
  try {
    const res = await fetch(`${API_URL}/ride-requests/${match.request_id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        matched_trip_id: match.trip_id,
        suggested_hub_id: match.suggested_hub.id,
        status: 'matched'
      })
    });
    
    if (res.ok) {
      Alert.alert(
        "Match Confirmed!", 
        `Meet at ${match.suggested_hub.name} at ${match.driver_departure_time}`
      );
      setShowMatches(false);
      setMode('now');
    }
  } catch (e) {
    Alert.alert("Error", "Could not confirm match");
  }
};
```

### 6. Add Styles

```typescript
matchesContainer: {
  marginTop: 20,
  padding: 15,
  backgroundColor: '#F8F9FB',
  borderRadius: 12,
},
matchesTitle: {
  fontSize: 18,
  fontWeight: '800',
  marginBottom: 15,
},
matchCard: {
  backgroundColor: '#fff',
  padding: 15,
  borderRadius: 12,
  marginBottom: 15,
  borderWidth: 1,
  borderColor: '#E5E5EA',
},
matchHeader: {
  marginBottom: 10,
},
matchName: {
  fontSize: 16,
  fontWeight: '700',
  marginBottom: 5,
},
matchTime: {
  fontSize: 14,
  color: '#8E8E93',
},
hubInfo: {
  backgroundColor: '#F8F9FB',
  padding: 12,
  borderRadius: 8,
  marginBottom: 10,
},
hubLabel: {
  fontSize: 12,
  color: '#8E8E93',
  marginBottom: 5,
},
hubName: {
  fontSize: 16,
  fontWeight: '600',
  marginBottom: 5,
},
hubDistance: {
  fontSize: 14,
  color: '#007AFF',
},
confirmBtn: {
  backgroundColor: '#34C759',
  padding: 12,
  borderRadius: 8,
  alignItems: 'center',
},
confirmBtnText: {
  color: '#fff',
  fontWeight: 'bold',
  fontSize: 16,
},
noMatchesContainer: {
  marginTop: 20,
  padding: 20,
  alignItems: 'center',
},
noMatchesText: {
  fontSize: 16,
  color: '#8E8E93',
  marginBottom: 15,
  textAlign: 'center',
},
refreshBtn: {
  backgroundColor: '#007AFF',
  padding: 12,
  borderRadius: 8,
  paddingHorizontal: 20,
},
refreshBtnText: {
  color: '#fff',
  fontWeight: '600',
},
```

### 7. Add PATCH Endpoint to Backend (if not exists)

You may need to add a PATCH endpoint to update ride requests:

```python
@app.patch("/ride-requests/{request_id}", response_model=schemas.RideRequest)
def update_ride_request(request_id: int, updates: dict, db: Session = Depends(get_db)):
    db_request = db.query(RideRequest).filter(RideRequest.id == request_id).first()
    if not db_request:
        raise HTTPException(status_code=404, detail="Ride request not found")
    
    for key, value in updates.items():
        if hasattr(db_request, key):
            setattr(db_request, key, value)
    
    db.commit()
    db.refresh(db_request)
    return db_request
```

## Summary of Changes

1. ✅ Add `trip_date`/`request_date` when posting scheduled rides
2. ✅ Call `/match-scheduled/` after posting
3. ✅ Display matches with hub suggestions
4. ✅ Allow users to confirm matches
5. ✅ Add PATCH endpoint for updating ride requests (if needed)

These changes will enable the full scheduled ride matching flow in the mobile app.
