Map for Women — Testing \& Defect Fix Log



1\. Document Information



Field



Value



Project



Map for Women



Environment



Local Development / Docker Compose



Branch



main



API



FastAPI / PostgreSQL



Web



Next.js



Database



PostgreSQL + PostGIS



Log Type



Functional Testing \& Defect Fix Log



Status



In Progress



Last Updated



20 August 2026



2\. Purpose



This document records defects identified during functional testing of the Map for Women application.



For each confirmed defect, the log captures:



Observed behaviour



Expected behaviour



Technical evidence



Root cause



Corrective action



Validation performed



Final result



Only issues that were actually observed, investigated, fixed, and retested should be added to this document.



3\. Defect Log



BUG-001 — Fake Call Invalid UUID Error



Field



Details



Issue ID



BUG-001



Feature



Fake Incoming Call



Severity



Medium



Status



Fixed \& Verified



Observed Behaviour



During Fake Call status polling, the frontend requested:



GET /api/fake-call/latest



The backend attempted to interpret the literal value latest as the PostgreSQL UUID of a Fake Call session.



This resulted in the following database error:



psycopg.errors.InvalidTextRepresentation:

invalid input syntax for type uuid: "latest"



Expected Behaviour



The frontend should poll the status using the actual UUID returned when the Fake Call session is created.



Root Cause



The endpoint:



/api/fake-call/{call\_id}



expects an actual Fake Call session UUID.



The frontend was initially passing:



latest



instead of the UUID of the newly created session.



Corrective Action



The Fake Call flow was updated so that:



A Fake Call session is created first.



The returned session ID is stored by the frontend.



Status polling uses that actual session ID.



The literal value latest is no longer sent to the UUID-based endpoint.



Validation Evidence



API logs showed successful requests using the actual session UUID:



GET /api/fake-call/<UUID> HTTP/1.1" 200 OK



Result



PASS — Fixed and Verified



BUG-002 — Fake Call Status Not Transitioning from SCHEDULED to TRIGGERED



Field



Details



Issue ID



BUG-002



Feature



Fake Incoming Call



Severity



High



Status



Fixed \& Verified



Observed Behaviour



A scheduled Fake Call remained in:



SCHEDULED



even after the configured scheduled time had passed.



Expected Behaviour



After the scheduled time passes, the Fake Call should automatically transition to:



TRIGGERED



and the UI should display the incoming simulated call.



Root Cause



The Fake Call store only retrieved the existing database record.



There was no server-side logic to evaluate whether:



current\_time >= scheduled\_at



and transition the session from SCHEDULED to TRIGGERED.



Corrective Action



The Fake Call store was updated so that when a scheduled session is requested:



The current time is compared with scheduled\_at.



If the session status is SCHEDULED and the scheduled time has passed, the status is changed to TRIGGERED.



triggered\_at is populated.



The updated session is returned to the frontend.



The PostgreSQL implementation performs this transition against the persistent:



fake\_call\_sessions



table.



Database Verification



The PostgreSQL table was verified and contains:



id

client\_id

caller\_name

caller\_number

scheduled\_at

triggered\_at

status

created\_at



The status constraint supports:



SCHEDULED

TRIGGERED

DISMISSED

EXPIRED



Validation Evidence



After rebuilding the API container, the API was confirmed healthy.



The Fake Call status was refreshed from the application and the UI displayed:



TRIGGERED

Incoming call from Mom

Triggered at 11:34 AM

Refresh status



Result



PASS — Fixed and Verified



4\. Functional Test Log



TEST-001 — API Health Validation



Field



Details



Test ID



TEST-001



Area



Infrastructure / API



Status



PASS



Objective



Verify that the API remains operational after the Fake Call backend changes.



Test Steps



Start the Docker Compose stack.



Verify Docker service status.



Call the API health endpoint.



Command



docker compose -f .\\infra\\compose.yaml ps



API health was then checked using:



curl.exe http://localhost:8000/health



Expected Result



The API should respond successfully.



Actual Result



{

&#x20; "status": "ok",

&#x20; "env": "development"

}



Docker services were running/healthy, including:



API



PostgreSQL/PostGIS



Redis



OSRM



Web



Result



PASS



TEST-002 — Fake Call End-to-End Validation



Field



Details



Test ID



TEST-002



Area



Fake Incoming Call



Status



PASS



Objective



Validate the complete Fake Call flow from creation through scheduled status transition.



Test Steps



Start the Docker Compose stack.



Open the Map for Women web application.



Navigate to the Emergency section.



Enter the caller name:



Mom



Trigger the Fake Call.



Confirm that a session is created.



Allow the configured scheduled time to pass.



Refresh the Fake Call status.



Verify the status transition.



Expected Result



The Fake Call card should transition from:



SCHEDULED



to:



TRIGGERED



and display:



Incoming call from Mom



Actual Result



The application displayed:



TRIGGERED

Incoming call from Mom

Triggered at 11:34 AM

Refresh status



API logs also showed successful status requests:



GET /api/fake-call/<UUID> → 200 OK



Result



PASS



5\. Defect Tracking Summary



ID



Feature



Issue



Root Cause



Status



BUG-001



Fake Call



latest caused UUID error



UUID endpoint received literal latest



Fixed \& Verified



BUG-002



Fake Call



SCHEDULED did not become TRIGGERED



No scheduled-time transition logic



Fixed \& Verified



6\. Test Execution Summary



Test Area



Result



Fake Call API



PASS



Fake Call Session Creation



PASS



Fake Call Status Polling



PASS



Scheduled → Triggered Transition



PASS



PostgreSQL Persistence



PASS



API Health



PASS



Docker API Container



PASS



End-to-End Fake Call UI



PASS

All future defects should receive a unique ID and should include sufficient evidence to support the recorded root cause and validation result.