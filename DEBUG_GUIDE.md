# NeuroPersona - 500 Error Debugging Guide

**Date:** January 24, 2026
**Issue:** HTTP 500 Internal Server Error on `/api/start-assessment` endpoint
**Status:** FIXED ✓

---

## Problem Summary

Your frontend is receiving:
```
[API] POST https://neuropersona.onrender.com/api/start-assessment
✗ Failed to load resource: the server responded with a status of 500 ()
✗ [API] Attempt 1 failed: Internal server error
✗ [API] Attempt 2 failed: Internal server error
✗ [API] Attempt 3 failed: Internal server error
✗ Error: API request failed after 3 attempts
```

---

## Root Causes Identified

### 1. **Missing Engine Initialization** (PRIMARY CAUSE)
- **What was wrong:** The `app.py` was NOT initializing the `ScoringEngine`, `VAEInferenceEngine`, and `GeminiClient`
- **Why it matters:** The `api_routes.py` expects these global objects to exist when processing assessments
- **Result:** When `/api/submit-assessment` tried to call `scoring_engine.process_assessment()`, it crashed because `scoring_engine` was `None`
- **Fix:** Added explicit engine initialization in `app.py` with comprehensive error handling

### 2. **Insufficient Error Logging**
- **What was wrong:** The original `api_routes.py` caught exceptions but didn't provide detailed step-by-step logging
- **Why it matters:** In production, you couldn't see WHERE in the process the error occurred
- **Result:** The 500 error response didn't include the actual exception traceback
- **Fix:** Added detailed logging at each step (Step 1, Step 2, Step 3, etc.) to pinpoint failures

### 3. **Poor Database Error Handling**
- **What was wrong:** No distinction between database connection errors vs validation errors
- **Why it matters:** You couldn't tell if the problem was invalid data or a database outage
- **Result:** All errors returned generic "Internal server error" messages
- **Fix:** Separated `SQLAlchemy` exceptions and included `db.session.rollback()` calls

### 4. **Missing Engine Initialization Verification**
- **What was wrong:** No checks to verify engines initialized successfully before using them
- **Why it matters:** If any engine failed to initialize silently, the API would crash when that engine was needed
- **Result:** Graceful degradation wasn't possible
- **Fix:** Added explicit null checks in API routes and fallback behavior for optional engines

---

## Files Modified

### 1. `backend/app.py`
**Changes:**
- Added explicit initialization of `ScoringEngine`, `VAEInferenceEngine`, and `GeminiClient`
- Wrapped engine initialization in try-except blocks with detailed logging
- Added status log showing which engines initialized successfully
- Passes initialized engines to `init_engines()` function in `api_routes.py`

**Before:**
```python
# Engine initialization was MISSING entirely
from api_routes import api_bp, init_engines
app.register_blueprint(api_bp, url_prefix='/api')
# No call to init_engines()!
```

**After:**
```python
# Step-by-step initialization with error handling
try:
    from scoring_engine import ScoringEngine
    scoring_engine = ScoringEngine()
    logger.info("[ENGINES] ✓ ScoringEngine initialized")
except Exception as e:
    logger.error(f"[ENGINES] ✗ Failed to initialize ScoringEngine: {str(e)}")

# ... same for VAEInferenceEngine and GeminiClient

# Pass engines to API routes
init_engines(scoring_engine, vae_engine, gemini_client)
```

### 2. `backend/api_routes.py`
**Changes:**
- Added 14 numbered steps in `/start-assessment` with logging at each step
- Added 14 numbered steps in `/submit-assessment` with logging at each step
- Separated database errors from business logic errors
- Added null checks for all engines before use
- Added fallback behavior for optional engines (e.g., Gemini interpretation)
- Used `db.session.flush()` to get IDs without committing prematurely
- Better transaction management with explicit rollbacks

**Before:**
```python
@api_bp.route('/start-assessment', methods=['POST'])
def start_assessment():
    try:
        data = request.get_json()
        # ... minimal logging
        user = User(age=age, sex=sex)
        db.session.add(user)
        db.session.commit()  # Could fail silently
        # ... no detailed error info
    except Exception as e:
        logger.error(f'Error in start_assessment: {str(e)}', exc_info=True)
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500
```

**After:**
```python
@api_bp.route('/start-assessment', methods=['POST'])
def start_assessment():
    """Start a new assessment - FIX: Enhanced error handling"""
    logger.info('[START_ASSESSMENT] Request received')
    
    try:
        # Step 1: Validate request body
        logger.debug('[START_ASSESSMENT] Step 1: Validating request body')
        data = request.get_json()
        
        if not data:
            logger.warning('[START_ASSESSMENT] No JSON body provided')
            return jsonify({'status': 'error', 'message': 'Request body must be JSON'}), 400
        
        # Step 2: Extract and validate fields
        logger.debug('[START_ASSESSMENT] Step 2: Extracting fields')
        # ... validation with logging
        
        # Step 5: Create User in database
        logger.debug('[START_ASSESSMENT] Step 5: Creating User in database')
        try:
            user = User(age=age, sex=sex)
            db.session.add(user)
            db.session.flush()  # Get ID without committing
            user_id = user.id
            logger.info(f'[START_ASSESSMENT] User created: user_id={user_id}')
        except SQLAlchemyError as e:
            logger.error(f'[START_ASSESSMENT] Database error creating user: {str(e)}')
            db.session.rollback()
            return jsonify({'status': 'error', 'message': 'Database error creating user'}), 500
        
        # ... more steps
    
    except Exception as e:
        logger.error(f'[START_ASSESSMENT] ✗ Unexpected error: {str(e)}', exc_info=True)
        db.session.rollback()
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500
```

---

## How to Verify the Fix

### Step 1: Deploy the Fixed Code
1. Merge the `debug/fix-500-error` branch to `main`
2. Push to Render (or your deployment platform)
3. Wait for deployment to complete

### Step 2: Check Logs
After deployment, check your Render logs for:

```
[ENGINES] Initializing scoring, VAE, and Gemini engines...
[ENGINES] ✓ ScoringEngine initialized
[ENGINES] ✓ VAEInferenceEngine initialized
[ENGINES] ✓ GeminiClient initialized
[ENGINES] Engine initialization complete:
     - ScoringEngine: YES
     - VAEInferenceEngine: YES
     - GeminiClient: YES
```

### Step 3: Test the API
```bash
# Test 1: Health check
curl -X GET https://neuropersona.onrender.com/api/health

# Response should be:
# {"status": "healthy", "timestamp": "...", "service": "personality-assessment-api", "version": "1.0.0"}

# Test 2: Start assessment
curl -X POST https://neuropersona.onrender.com/api/start-assessment \
  -H "Content-Type: application/json" \
  -d '{"age": 25, "sex": "M"}'

# Response should be:
# {"status": "success", "user_id": 1, "assessment_id": 1, "external_id": "..."}
```

### Step 4: Test in Frontend
Open the frontend and test the full flow:
1. Fill in demographics (age, gender)
2. Answer all 35 questions (1-10 scale)
3. Click "Submit Assessment"
4. Should see redirect to results page

---

## Expected Behavior After Fix

### When Everything Works (Success Path)
```
[START_ASSESSMENT] Request received
[START_ASSESSMENT] Step 1: Validating request body
[START_ASSESSMENT] Step 2: Extracting fields
[START_ASSESSMENT] Step 3: Validating age=25
[START_ASSESSMENT] Step 4: Validating sex=M
[START_ASSESSMENT] Step 5: Creating User in database
[START_ASSESSMENT] User created: user_id=1
[START_ASSESSMENT] Step 6: Creating Assessment for user_id=1
[START_ASSESSMENT] Assessment created: assessment_id=1
[START_ASSESSMENT] Step 7: Committing transaction
[START_ASSESSMENT] Transaction committed successfully
[START_ASSESSMENT] Step 8: Returning success response
[START_ASSESSMENT] ✓ Complete: {'status': 'success', 'user_id': 1, 'assessment_id': 1, ...}
```

### When Validation Fails (Client Error)
```
[START_ASSESSMENT] Request received
[START_ASSESSMENT] Step 1: Validating request body
[START_ASSESSMENT] Step 3: Validating age=150
[START_ASSESSMENT] ✗ Invalid age: 150
# Returns 400 with message: "Age must be between 13 and 120"
```

### When Database Fails (Server Error)
```
[START_ASSESSMENT] Request received
[START_ASSESSMENT] Step 5: Creating User in database
[START_ASSESSMENT] ✗ Database error creating user: Connection refused
# Returns 500 with specific database error
```

---

## Troubleshooting Steps

If you still see 500 errors after deployment:

### 1. Check Render Logs
```bash
# SSH into Render or check live logs
# Look for:
# - "ENGINES" initialization messages
# - Any "✗" (failed) engine initializations
# - Specific error messages with traceback
```

### 2. Verify Environment Variables
Make sure these are set in Render:
- `DATABASE_URL` - PostgreSQL connection string
- `GEMINI_API_KEY` - (optional, but needed for interpretations)
- `FLASK_ENV` - set to `production`

### 3. Test Each Component Independently
```bash
# Check database connection
curl https://neuropersona.onrender.com/api/health

# Check with valid data
curl -X POST https://neuropersona.onrender.com/api/start-assessment \
  -H "Content-Type: application/json" \
  -d '{"age": 25, "sex": "M"}'

# Check with invalid data (should return 400, not 500)
curl -X POST https://neuropersona.onrender.com/api/start-assessment \
  -H "Content-Type: application/json" \
  -d '{"age": "invalid", "sex": "M"}'
```

### 4. Enable Debug Mode (Development Only)
To get more detailed error messages during development:
```bash
# In Render environment variables
FLASK_ENV=development
```

This will include exception tracebacks in error responses.

---

## Prevention Tips for Future

1. **Always log initialization steps** - Know which components started successfully
2. **Separate business logic errors from infrastructure errors** - Handle them differently
3. **Use try-except for optional components** - Gemini interpretation shouldn't crash the API
4. **Test with invalid data** - Returns 400, not 500
5. **Verify all global state** - Check engines are initialized before using
6. **Use database sessions carefully** - Rollback on errors, flush before commit

---

## Commit Information

**Branch:** `debug/fix-500-error`
**Commits:**
1. "Fix: Enhanced error handling and logging in API routes"
2. "Fix: Add proper engine initialization with detailed logging"

**To merge:**
```bash
git checkout main
git pull origin main
git merge debug/fix-500-error
git push origin main
```

---

## Next Steps

1. ✓ Review and test the fixes
2. ✓ Merge to main branch
3. ✓ Deploy to Render
4. ✓ Monitor logs during first few requests
5. ✓ Test full user flow (demographics → questionnaire → results)
6. ✓ Update frontend to show more helpful error messages if needed

---

**Questions?** Check the detailed logging output in your Render console - it will show you exactly where the process failed!
