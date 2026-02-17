# Where to See Logs When Testing with the Simulator

## 1. API (backend) logs – **main place to look**

**Where:** The **same terminal** where you ran:

```bash
./dev.sh local
```

That terminal shows:

- Uvicorn startup: `Uvicorn running on http://127.0.0.1:8080`
- **Every HTTP request**, e.g. `INFO: 127.0.0.1:xxxxx - "POST /ride-requests/ HTTP/1.1" 200 OK`
- Our custom lines when you submit a ride:
  - `📥 POST /ride-requests/ received (...)` or `📥 POST /trips/ received (...)`
  - `✅ POST /ride-requests/ completed in 0.02s (request_id=1)` or similar

**If the simulator “stalls” when you submit:**

- **You do NOT see** `📥 POST /ride-requests/ received` (or `/trips/`) in that terminal  
  → The request is **not** reaching your local API. The app is almost certainly using the **wrong base URL** (e.g. production instead of localhost). Fix the app’s API base URL (see below).

- **You DO see** `📥 ... received` but **no** `✅ ... completed`  
  → The request reaches the API but the handler is hanging (e.g. DB or geocoding). The next step is to add more logging inside that handler.

- **You see both** `📥 received` and `✅ completed`  
  → The API is responding. If the simulator still looks stuck, the issue is on the **client** (e.g. wrong URL for a *different* request, or UI not handling the response).

So: **keep that terminal visible** while you tap “Submit” in the simulator and watch for those lines.

---

## 2. Simulator / app logs (optional)

If you want to see what the **app** is doing (e.g. which URL it’s calling):

- **iOS (Xcode):** Run the app from Xcode and use the **Debug console** at the bottom (or View → Debug Area → Activate Console). You’ll see `print()` and `os_log` output, and any network or error logs.
- **Android (Android Studio):** Use the **Logcat** tab and filter by your app’s package name.

There you can confirm the base URL (e.g. `http://localhost:8080` vs `https://skidb-backend-xxx.run.app`).

---

## 3. Make sure the simulator hits your local API

For **local** testing, the app must call your Mac, not production:

- **iOS Simulator:** use `http://localhost:8080` or `http://127.0.0.1:8080` as the API base URL.
- **Physical phone on same Wi‑Fi:** use your Mac’s LAN IP, e.g. `http://192.168.1.x:8080` (find the IP in System Settings → Network).

If the app is hardcoded or configured to use `https://skidb-backend-....run.app`, change it to the local URL above for development so requests and logs appear in the terminal where you ran `./dev.sh local`.
