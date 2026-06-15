Step 26 Testing: Security Hardening in Postman
Make sure your server is running.

Test 1: Normal Login Still Works
Login as operator first to confirm nothing broke.

Method: POST
URL: {{base_url}}/auth/login/
Body → raw → JSON:

json{
    "email": "operator1@test.com",
    "password": "newpass2026"
}
Expected response (200 OK) with tokens.
Save as Security Hardening - Normal Login Works.

Test 2: Wrong Password Increments Failure Count

Method: POST
URL: {{base_url}}/auth/login/
Body → raw → JSON:

json{
    "email": "operator1@test.com",
    "password": "wrongpassword"
}
Expected response (401 Unauthorized):
json{
    "detail": "No active account found with the given credentials"
}
Run this 4 more times (5 total failed attempts).
Save as Security Hardening - Wrong Password Attempt.

Test 3: Account Locked After 5 Failed Attempts
After 5 failed attempts try once more:

Method: POST
URL: {{base_url}}/auth/login/
Body → raw → JSON:

json{
    "email": "operator1@test.com",
    "password": "wrongpassword"
}
Expected response (403 Forbidden):
json{
    "detail": "Access attempt limit exceeded."
}

Django Axes has locked the account after 5 failed attempts from the same IP.

Save as Security Hardening - Account Locked After 5 Attempts.

Test 4: Correct Password Also Blocked While Locked

Method: POST
URL: {{base_url}}/auth/login/
Body → raw → JSON:

json{
    "email": "operator1@test.com",
    "password": "newpass2026"
}
Expected response (403 Forbidden) — even the correct password is rejected while the account is locked.
Save as Security Hardening - Correct Password Blocked While Locked.

Test 5: Reset the Lockout via Django Admin
Go to http://127.0.0.1:8000/admin/ and login with your superuser credentials.

Click Access attempts under the Axes section in the left panel
Select all records
Click Action dropdown → select Reset access attempts
Click Go

Now try logging in again with correct credentials — it should work.
Save a note as Security Hardening - Reset Lockout via Admin.

Test 6: Normal Login Works After Reset

Method: POST
URL: {{base_url}}/auth/login/
Body → raw → JSON:

json{
    "email": "operator1@test.com",
    "password": "newpass2026"
}
Expected response (200 OK) with tokens.
Save as Security Hardening - Login Works After Reset.

Test 7: Test Rate Limiting on Registration
Send 6 registration requests quickly one after another. Use a new email each time so they do not fail on duplicate email validation.
Run these 6 times changing the email number each time:

Method: POST
URL: {{base_url}}/auth/register/
Body → raw → JSON:

json{
    "email": "ratelimit_test_1@test.com",
    "password": "test1234",
    "first_name": "Test",
    "last_name": "User",
    "phone": "08011111111"
}
Change email to ratelimit_test_2@test.com, ratelimit_test_3@test.com etc for each request.
The first 5 should return 201 Created. The 6th should return:
Expected response (429 Too Many Requests):
json{
    "detail": "Too many registration attempts from this IP address. Please try again later."
}
Save as Security Hardening - Rate Limit Registration.

Test 8: Security Headers Are Present

Method: GET
URL: {{base_url}}/auth/me/

After getting the response click the Headers tab in Postman to see the response headers.
You should see these security headers present:
HeaderExpected ValueX-Frame-OptionsDENYX-Content-Type-OptionsnosniffReferrer-Policysame-origin
Save as Security Hardening - Security Headers Present.

Test 9: Environment Validator Works
To test the environment validator stop your server. Then temporarily rename your .env file to .env.backup.
In your terminal run:
bashpython manage.py check
Expected output:
============================================================
ISCOOA FACITECH — MISSING ENVIRONMENT VARIABLES
============================================================
  ✗  SECRET_KEY is not set
  ✗  DB_NAME is not set
  ✗  DB_USER is not set
  ✗  DB_PASSWORD is not set
  ✗  DB_HOST is not set
  ✗  DB_PORT is not set

Please check your .env file.
Reference: backend/.env.example
============================================================
Then rename .env.backup back to .env and confirm the server starts normally again.
Save as Security Hardening - Environment Validator Works.

Test 10: CORS Headers Are Present

Method: OPTIONS
URL: {{base_url}}/auth/login/
Add this header manually in Postman:

KeyValueOriginhttp://localhost:3000
Click Send
Check the response headers. You should see:
HeaderExpected ValueAccess-Control-Allow-Originhttp://localhost:3000Access-Control-Allow-MethodsGET, POST, PUT, PATCH, DELETE, OPTIONSAccess-Control-Allow-Headersauthorization, content-type, ...
Save as Security Hardening - CORS Headers Present.

Test 11: Blocked Origin is Rejected
Add a new header in Postman:
KeyValueOriginhttp://malicious-site.com

Method: OPTIONS
URL: {{base_url}}/auth/login/

Expected: The Access-Control-Allow-Origin header should NOT be present in the response for an origin not in your allowed list.
Save as Security Hardening - Blocked Origin Rejected.

Test 12: Deactivated Account Cannot Login
We deactivated fake.president@test.com earlier. Confirm it still cannot login:

Method: POST
URL: {{base_url}}/auth/login/
Body → raw → JSON:

json{
    "email": "fake.president@test.com",
    "password": "test1234"
}
Expected response (401 Unauthorized)
Save as Security Hardening - Deactivated Account Still Blocked.

Test 13: Verify Whitenoise Serves Static Files
Run this in your terminal first to collect static files:
bashpython manage.py collectstatic --noinput
Then open in your browser:
http://127.0.0.1:8000/static/admin/css/base.css
You should see the Django admin CSS file served directly. This confirms Whitenoise is working.
Save as Security Hardening - Whitenoise Static Files.

Test 14: Confirm Axes is Tracking Access Attempts
Go to http://127.0.0.1:8000/admin/ and click Access attempts under the Axes section.
You should see records of all the failed login attempts from Test 2 and Test 3 including:

IP address
Username attempted
Number of failures
Locked status

Save as Security Hardening - Axes Tracking Attempts.

Test 15: Verify All Previous Endpoints Still Work
Run a quick smoke test to confirm security hardening did not break anything:

GET {{base_url}}/auth/me/ — should return 200 with operator profile
GET {{base_url}}/kyc/my-application/ — should return 200
GET {{base_url}}/shops/my-shops/ — should return 200
GET {{base_url}}/bills/my-bills/ — should return 200
GET {{base_url}}/wallet/my-wallet/ — should return 200

All should return 200 OK confirming the security changes did not break any existing functionality.
Save as Security Hardening - Smoke Test All Endpoints.

✅ Full Test Checklist
TestExpectedNormal login works200 — tokens returnedWrong password 5 times401 each timeAccount locked after 5403 — access attempt limitCorrect password blocked while locked403 — still blockedReset lockout via adminLockout clearedLogin works after reset200 — tokens returnedRate limit registration429 on 6th attemptSecurity headers presentX-Frame-Options, nosniff etcEnvironment validatorClear error message on missing varsCORS headers presentAccess-Control headers showingBlocked origin rejectedNo CORS header for malicious originDeactivated account blocked401 UnauthorizedWhitenoise static filesCSS file served from /static/Axes tracking attemptsRecords visible in adminSmoke test all endpointsAll return 200

Tell me all tests pass and we move to Step 27: Supabase Database Migration — switching from local PostgreSQL to Supabase managed PostgreSQL.