# Running DB Scripts Locally (create_test_data, simulate_*, etc.)

The app uses Cloud SQL. The default config uses a **Unix socket** (`/cloudsql/...`), which exists only when running **in GCP** (e.g. Cloud Run) or when the **Cloud SQL Auth Proxy** is running locally.

When you run `create_test_data.py` or other scripts on your Mac, that socket is not available, so you get:

```
connection to server on socket "/cloudsql/..." failed: No such file or directory
```

## Fix: Use a TCP connection via `DATABASE_URL`

### Option 1: Cloud SQL Auth Proxy (recommended)

1. **Install the proxy** (if needed):
   ```bash
   # macOS with Homebrew
   brew install cloud-sql-proxy
   ```

2. **Start the proxy** (TCP on port 5432):
   ```bash
   cloud_sql_proxy -instances=skipool-483602:us-central1:skipooldb=tcp:5432
   ```
   Leave this running in a terminal.

3. **In another terminal**, set `DATABASE_URL` and run your script:
   ```bash
   export DATABASE_URL="postgresql://postgres:SkiPoolTest_1@127.0.0.1:5432/skipooldb"
   python create_test_data.py
   ```

   Use your actual DB password if it differs from `SkiPoolTest_1`.

### Option 2: Public IP (if your instance has it enabled)

If your Cloud SQL instance has a public IP and your IP is authorized:

```bash
export DATABASE_URL="postgresql://postgres:YOUR_PASSWORD@YOUR_PUBLIC_IP:5432/skipooldb"
python create_test_data.py
```

---

**Summary:** Set `DATABASE_URL` to a **TCP** URL (host:port). The app still uses the socket URL when `DATABASE_URL` is not set (e.g. on Cloud Run).
