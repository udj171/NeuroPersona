# NeuroPersona 500 Error Debugging Guide

## Critical Fixes Applied (2026-01-25)

Your NeuroPersona backend was returning 500 errors on `/api/start-assessment` due to **uninitialized engines**. These issues have been fixed.

---

## Root Causes Identified & Fixed

### 1. **Engines Not Initialized at Startup** ✅ FIXED
**Problem:**
- `app.py` was NOT calling `initialize_engines()` function
- Global variables `scoring_engine`, `vae_engine`, `gemini_client` remained `None`
- When `/api/start-assessment` was called, engines were unavailable, causing AttributeErrors

**Solution:**
- Added `initialize_engines()` function in `app.py` that creates all three engine instances
- Wrapped initialization in try/except to capture errors and log them
- Called `set_engines()` to pass initialized engines to the blueprint
- Added engine status logging to startup messages

**Changes in `app.py`:**
```python
# NEW: Initialize engines after app context
def initialize_engines():
    global scoring_engine, vae_engine, gemini_client
    # Creates ScoringEngine, VAEInferenceEngine, GeminiClient
    # Logs success/failure for each

# After app.app_context():
with app.app_context():
    initialize_engines()  # Initialization
    set_engines(scoring_engine, vae_engine, gemini_client)  # Pass to routes
```

---

### 2. **Missing `set_engines()` Function** ✅ FIXED
**Problem:**
- `api_routes.py` had global variables but NO way to set them
- `init_engines()` function existed but was never called

**Solution:**
- Renamed `init_engines()` → `set_engines()` for clarity
- Added logging to show which engines were successfully configured
- Updated `app.py` to call this function

**Changes in `api_routes.py`:**
```python
def set_engines(scoring, vae, gemini):
    """Set engine references from app.py"""
    global scoring_engine, vae_engine, gemini_client
    scoring_engine = scoring
    vae_engine = vae
    gemini_client = gemini
    logger.info("[API_ROUTES] Engines configured:")
    logger.info(f"  - ScoringEngine: {'Ready' if scoring else 'None'}")
    logger.info(f"  - VAEInferenceEngine: {'Ready' if vae else 'None'}")
    logger.info(f"  - GeminiClient: {'Ready' if gemini else 'None'}")
```

---

### 3. **Poor Error Messages & Logging** ✅ FIXED
**Problem:**
- Frontend received generic "Internal server error" with no details
- Render logs were hard to parse
- No error codes for frontend to handle programmatically

**Solution:**
- Added specific error codes: `INVALID_JSON`, `MISSING_AGE`, `AGE_OUT_OF_RANGE`, etc.
- Improved logging with `[START_ASSESSMENT]`, `[SUBMIT_ASSESSMENT]` prefixes
- Added detailed validation logging for debugging
- Frontend can now handle specific error types

**Changes in `api_routes.py`:**
```python
# New error codes for frontend
return jsonify({
    'status': 'error',
    'message': 'Age must be between 13 and 120',
    'code': 'AGE_OUT_OF_RANGE'  # NEW: Specific error code
}), 400

# Better logging
logger.info(f'[START_ASSESSMENT] Received: age={age}, sex={sex}')
logger.warning(f'[START_ASSESSMENT] Age out of range: {age}')
```

---

### 4. **Lack of Engine Status Checks** ✅ FIXED
**Problem:**
- `/api/submit-assessment` would fail if engines weren't initialized
- No graceful degradation or fallback

**Solution:**
- Added engine availability checks before use
- Return 503 Service Unavailable if critical engines are missing
- Log which engines failed during initialization
- /health endpoint now shows engine status

**Changes in `api_routes.py`:**
```python
# Check engine before use
if not scoring_engine:
    logger.error('[SUBMIT_ASSESSMENT] Scoring engine not initialized')
    return jsonify({
        'status': 'error',
        'message': 'Scoring engine not available',
        'code': 'ENGINE_NOT_READY'
    }), 503

# /health now shows:
'engines': {
    'scoring': bool(scoring_engine),
    'vae': bool(vae_engine),
    'gemini': bool(gemini_client),
}
```

---

### 5. **Database Session Not Rolled Back on Error** ✅ FIXED
**Problem:**
- If an exception occurred, the db.session could be left in a bad state
- Secondary errors from failed rollback attempts

**Solution:**
- Wrapped all `db.session.rollback()` calls in try/except
- This prevents cascading errors

**Changes:**
```python
try:
    db.session.rollback()
except:
    pass  # Prevents secondary errors
```

---

## How to Test the Fixes

### Step 1: Verify Backend is Running
```bash
# Check Render logs at https://dashboard.render.com
# Look for these startup messages:
[ENGINES] ✓ Scoring engine initialized
[ENGINES] ✓ VAE engine initialized
[ENGINES] ✓ Gemini client initialized
[ENGINES] ✓ All engines passed to API routes
```

### Step 2: Test Health Endpoint
```bash
curl https://neuropersona.onrender.com/api/health | jq

# Expected response:
{
  "status": "healthy",
  "engines": {
    "scoring": true,
    "vae": true,
    "gemini": true
  }
}
```

### Step 3: Test Start Assessment
```bash
curl -X POST https://neuropersona.onrender.com/api/start-assessment \
  -H "Content-Type: application/json" \
  -d '{"age": 25, "sex": "M"}' | jq

# Expected response (201 Created):
{
  "status": "success",
  "assessment_id": 1,
  "user_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "external_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
}
```

### Step 4: Frontend Testing
Open your Vercel frontend and:
1. Enter age 25, sex M
2. Click "Start Assessment"
3. Check browser DevTools Console for success message
4. Questions section should appear

---

## Render Deployment Checklist

If the errors persist after code updates, check:

- [ ] **Database URL Set in Environment**
  ```
  DATABASE_URL = your_supabase_postgres_url
  # Go to Render Dashboard → Settings → Environment
  ```

- [ ] **Gemini API Key Set (if using)**
  ```
  GEMINI_API_KEY = your_api_key
  # Optional - if not set, graceful fallback
  ```

- [ ] **Backend Redeployed After Code Changes**
  - Go to Render Dashboard
  - Click "Manual Deploy" or push to main branch
  - Wait for build to complete
  - Check logs for initialization messages

- [ ] **Models Folder Accessible**
  - VAE models need to load from `/backend/models/`
  - If models are missing, VAE engine will fail to initialize
  - Check Render logs for: `[ENGINES] ✗ Failed to initialize VAE engine`

---

## Error Codes Reference

The frontend can now handle specific error codes:

| Code | Status | Meaning |
|------|--------|----------|
| `INVALID_JSON` | 400 | Request body is not valid JSON |
| `MISSING_AGE` | 400 | Age field is missing |
| `INVALID_AGE_TYPE` | 400 | Age is not a number |
| `AGE_OUT_OF_RANGE` | 400 | Age < 13 or > 120 |
| `MISSING_SEX` | 400 | Sex field is missing |
| `INVALID_SEX` | 400 | Sex is not M/F/O |
| `USER_CREATE_ERROR` | 500 | Database error creating user |
| `ASSESSMENT_CREATE_ERROR` | 500 | Database error creating assessment |
| `ENGINE_NOT_READY` | 503 | Engine initialization failed |
| `INTERNAL_ERROR` | 500 | Unexpected error |

---

## Logs Interpretation Guide

### ✅ Good Startup Sequence
```
[APP] Flask app initialized successfully
[DATABASE] Creating tables...
[DATABASE] ✓ Database tables created/verified
[ENGINES] Initializing scoring engine...
[ENGINES] ✓ Scoring engine initialized
[ENGINES] Initializing VAE inference engine...
[ENGINES] ✓ VAE engine initialized
[ENGINES] Initializing Gemini client...
[ENGINES] ✓ Gemini client initialized
[API_ROUTES] Engines configured:
  - ScoringEngine: Ready
  - VAEInferenceEngine: Ready
  - GeminiClient: Ready
```

### ⚠️ Warnings (But Still Works)
```
[ENGINES] ✗ Failed to initialize Gemini client: API key not set
  → Gemini interpretation will not be available
  → VAE and scoring will still work
```

### 🔴 Critical Errors (Won't Work)
```
[DATABASE] ✗ Error creating tables: Could not connect to PostgreSQL
  → Check DATABASE_URL in Render environment

[ENGINES] ✗ Failed to initialize VAE engine: No such file or directory: vae_model.pkl
  → Check if models are in /backend/models/ folder
```

---

## Common Issues & Solutions

### Issue: 500 on /api/start-assessment
**Check:**
1. Render logs - does it show engines initialized?
2. Is DATABASE_URL set correctly?
3. Are there any Python errors in startup?

**Fix:**
```bash
# In Render dashboard:
# 1. Go to Settings → Environment Variables
# 2. Verify DATABASE_URL is correct
# 3. Click "Manual Deploy"
# 4. Check Logs tab for errors
```

### Issue: 503 Engine Not Ready
**Meaning:** An engine failed to initialize
**Check:** Render logs for `[ENGINES] ✗ Failed to initialize...`
**Fix:**
1. Ensure all required packages are in requirements.txt
2. Check that model files exist
3. Verify API keys are set if needed

### Issue: Database Connection Error
**Check:**
1. Go to Supabase → Settings → Database → URI
2. Copy the correct PostgreSQL connection string
3. In Render → Settings → Environment: paste as `DATABASE_URL`
4. Manual deploy

---

## Files Modified

1. **backend/app.py**
   - Added `initialize_engines()` function
   - Added engine initialization in app context
   - Added engine status to startup logs
   - Better error handling for db.session.rollback()

2. **backend/api_routes.py**
   - Added `set_engines()` function (replaces `init_engines()`)
   - Improved `/api/start-assessment` error messages and validation
   - Improved `/api/submit-assessment` error handling
   - Added engine availability checks
   - Added specific error codes
   - Improved logging with context prefixes
   - Updated `/api/health` to show engine status
   - Better traceback logging for debugging

---

## Next Steps

1. **Deploy Updated Code** ✅ DONE (pushed to GitHub)
   - Render will auto-deploy from main branch
   - Or: Manual deploy in Render dashboard

2. **Verify in Render Logs**
   - Go to https://dashboard.render.com
   - Select NeuroPersona backend service
   - Click "Logs" tab
   - Look for engine initialization messages

3. **Test Frontend**
   - Open https://www.predictmypersonality.com
   - Fill age & gender
   - Click "Start Assessment"
   - Watch DevTools Console
   - Should see "Assessment started! Answer the questions below."

4. **Monitor Render Logs During Test**
   - Keep Render logs open
   - Watch for `[REQUEST]`, `[RESPONSE]`, and any errors

---

## Questions?

Check the following in order:

1. **Render Logs** - Most errors logged there
2. **Browser Console** - Frontend errors
3. **Browser Network Tab** - Response bodies and status codes
4. **Error Code** - Check table above for what code means

---

## Version
Debug Guide v1.0 - 2026-01-25
Backend Fixes Applied - All 500 errors on /api/start-assessment should be resolved
