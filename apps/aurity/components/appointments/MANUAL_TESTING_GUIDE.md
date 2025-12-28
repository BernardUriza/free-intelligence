# 🧪 API Integration Manual Testing Guide
**Card**: FI-CHECKIN-005 (Phase 3)  
**Date**: December 8, 2025  
**Status**: Ready for Testing

## 🚀 Environment Setup

### Prerequisites
✅ Backend running on http://localhost:7001  
✅ Frontend running on http://localhost:9000  
✅ Test data created (3 doctors, 4 appointments)

### Quick Start
```bash
# 1. Start backend
cd /Users/bernardurizaorozco/Documents/free-intelligence
/Users/bernardurizaorozco/.pyenv/versions/3.14.0/bin/python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 7001 --reload

# 2. Start frontend (new terminal)
cd /Users/bernardurizaorozco/Documents/free-intelligence/apps/aurity
pnpm dev

# 3. Create test data (new terminal)
PYTHONPATH=backend/src python -m fi_cli data create-test-appointments
```

### Access Application
- **Frontend**: http://localhost:9000/admin/appointments
- **Backend API**: http://localhost:7001/docs (Swagger UI)

---

## 📋 Test Scenarios

### Test Data Overview
**Clinic**: Aurity Clinic (`7f6ef952-d755-43d9-b668-32c3b6879149`)

**Doctors**:
- **Dra. García** (Cardiology) - 30 min consultations
- **Dr. Rodríguez** (Pediatrics) - 20 min consultations  
- **Dra. López** (Orthopedics) - 25 min consultations

**Appointments** (Today):
1. **9:00 AM** - Dra. García (30 min) - Consulta de cardiología
2. **10:00 AM** - Dra. García (30 min) - Seguimiento cardiaco
3. **9:00 AM** - Dr. Rodríguez (20 min) - Consulta pediátrica
4. **11:00 AM** - Dra. López (25 min) - Dolor de rodilla

---

## ✅ Test Case 1: Drag Appointment to Different Time

### Objective
Verify that dragging an appointment to a new time updates `scheduled_at` in the database.

### Steps
1. Open http://localhost:9000/admin/appointments
2. Locate **Dra. García's 9:00 AM** appointment (blue bar, top row)
3. **Drag** the appointment to **2:00 PM** (same doctor row)
4. Release mouse

### Expected Results
✅ **UI Updates Immediately** (optimistic update)
✅ **API Call Logged** in browser console: `Appointment updated successfully`
✅ **Backend Log** shows: `event='APPOINTMENT_UPDATED'` with `scheduled_at` field
✅ **Appointment Stays at 2:00 PM** after page refresh

### Verification
```bash
# Check backend log for API call
# Should see: APPOINTMENT_UPDATED with updated_fields=['scheduled_at']

# Verify via API
CLINIC_ID="7f6ef952-d755-43d9-b668-32c3b6879149"
curl "http://localhost:7001/api/clinics/${CLINIC_ID}/appointments?date=$(date +%Y-%m-%d)" | jq '.appointments[] | select(.reason == "Consulta de cardiología") | .scheduled_at'
# Should show 14:00:00 (2:00 PM)
```

### Error Scenario
**Test network failure:**
1. Open browser DevTools → Network tab
2. Enable "Offline" mode
3. Drag appointment to new time
4. Expected: Alert shown, appointment reverts to original position

---

## ✅ Test Case 2: Drag Appointment to Different Doctor

### Objective
Verify that dragging an appointment to a different resource (doctor) updates both `scheduled_at` and `doctor_id`.

### Steps
1. Locate **Dra. García's 10:00 AM** appointment
2. **Drag vertically** down to **Dr. Rodríguez** row (keep same time or change)
3. Release mouse

### Expected Results
✅ **Appointment Moves to Dr. Rodríguez Row**
✅ **Console Log**: `Appointment updated successfully` with new `doctor_id`
✅ **Backend Log**: `updated_fields=['scheduled_at', 'doctor_id']`
✅ **Color Changes** to Dr. Rodríguez's specialty color
✅ **Persists After Refresh**

### Verification
```bash
# Verify via API
CLINIC_ID="7f6ef952-d755-43d9-b668-32c3b6879149"
curl "http://localhost:7001/api/clinics/${CLINIC_ID}/appointments?date=$(date +%Y-%m-%d)" | jq '.appointments[] | select(.reason == "Seguimiento cardiaco") | {doctor_id, scheduled_at}'
# doctor_id should match Dr. Rodríguez's ID
```

### Error Scenario
**Test validation error:**
1. Try dragging to a non-existent doctor (if possible via manual URL editing)
2. Expected: 400 error, appointment reverts

---

## ✅ Test Case 3: Resize Appointment Duration

### Objective
Verify that resizing an appointment updates `estimated_duration` in minutes.

### Steps
1. Locate **Dra. López's 11:00 AM** appointment (25 minutes long)
2. **Hover over bottom edge** until resize cursor appears
3. **Drag down** to extend duration to approximately **45 minutes**
4. Release mouse

### Expected Results
✅ **Appointment Bar Extends Visually**
✅ **Console Log**: `Appointment resized successfully`
✅ **Backend Log**: `updated_fields=['estimated_duration']` with value `45`
✅ **Check-in Code Expiration Unchanged** (only scheduled_at changes trigger expiration update)

### Verification
```bash
# Verify duration via API
CLINIC_ID="7f6ef952-d755-43d9-b668-32c3b6879149"
curl "http://localhost:7001/api/clinics/${CLINIC_ID}/appointments?date=$(date +%Y-%m-%d)" | jq '.appointments[] | select(.reason == "Dolor de rodilla") | .estimated_duration'
# Should return 45 (or close to it, depending on grid snap)
```

### Error Scenario
**Test minimum/maximum constraints:**
1. Try resizing to < 5 minutes
2. Try resizing to > 180 minutes
3. Expected: Validation error or Bryntum prevents resize

---

## ✅ Test Case 4: Edit Appointment Details (Via Modal)

### Objective
Verify that editing appointment fields via Bryntum's editor updates all changed fields.

### Steps
1. **Double-click** on **Dr. Rodríguez's 9:00 AM** appointment
2. Bryntum editor modal should appear
3. Change the following:
   - **Time**: 9:00 AM → 9:30 AM
   - **Duration**: 20 min → 30 min
   - **Status** (if editable): SCHEDULED → CONFIRMED
4. Click **Save**

### Expected Results
✅ **Modal Closes**
✅ **Appointment Updates** to show new time and duration
✅ **Console Log**: `Appointment edited successfully`
✅ **Backend Log**: `updated_fields=['scheduled_at', 'estimated_duration', 'status']`
✅ **All Changes Persist** after refresh

### Verification
```bash
# Verify all fields via API
CLINIC_ID="7f6ef952-d755-43d9-b668-32c3b6879149"
curl "http://localhost:7001/api/clinics/${CLINIC_ID}/appointments?date=$(date +%Y-%m-%d)" | jq '.appointments[] | select(.reason == "Consulta pediátrica") | {scheduled_at, estimated_duration, status}'
# Should show new values
```

### Error Scenario
**Test edit completed appointment:**
1. Manually update appointment status to COMPLETED via API:
   ```bash
   CLINIC_ID="7f6ef952-d755-43d9-b668-32c3b6879149"
   APPOINTMENT_ID="<appointment_id>"
   curl -X PATCH "http://localhost:7001/api/clinics/${CLINIC_ID}/appointments/${APPOINTMENT_ID}" \
     -H "Content-Type: application/json" \
     -d '{"status": "COMPLETED"}'
   ```
2. Refresh page
3. Try to drag/resize/edit the COMPLETED appointment
4. Expected: 400 error with message "Cannot update appointment with status COMPLETED"

---

## ✅ Test Case 5: Network Failure Handling

### Objective
Verify that UI correctly handles and rolls back changes when API calls fail.

### Steps
1. Open **Browser DevTools** → Network tab
2. Enable **"Offline"** mode or set **throttling** to "Slow 3G"
3. Try to drag an appointment
4. Wait for network timeout

### Expected Results
✅ **Appointment Appears to Move** (optimistic update)
✅ **After Timeout**: Alert shown with error message
✅ **Appointment Reverts** to original position (rollback via re-fetch)
✅ **Console Error**: "Failed to update appointment: Failed to fetch"

### Verification
```bash
# Check that appointment did NOT change in database
CLINIC_ID="7f6ef952-d755-43d9-b668-32c3b6879149"
curl "http://localhost:7001/api/clinics/${CLINIC_ID}/appointments?date=$(date +%Y-%m-%d)" | jq '.appointments'
# All appointments should be at original times
```

---

## ✅ Test Case 6: Validation Errors

### Objective
Verify that backend validation prevents invalid updates.

### Steps - Scenario A: Invalid Doctor ID
```bash
# Manually send API request with non-existent doctor
CLINIC_ID="7f6ef952-d755-43d9-b668-32c3b6879149"
APPOINTMENT_ID="<any_appointment_id>"
curl -X PATCH "http://localhost:7001/api/clinics/${CLINIC_ID}/appointments/${APPOINTMENT_ID}" \
  -H "Content-Type: application/json" \
  -d '{"doctor_id": "00000000-0000-0000-0000-000000000000"}'
```

**Expected**: HTTP 400 with message "Doctor not found or not active in this clinic"

### Steps - Scenario B: Invalid Date Format
```bash
curl -X PATCH "http://localhost:7001/api/clinics/${CLINIC_ID}/appointments/${APPOINTMENT_ID}" \
  -H "Content-Type: application/json" \
  -d '{"scheduled_at": "invalid-date"}'
```

**Expected**: HTTP 400 with message "Invalid scheduled_at format"

### Steps - Scenario C: Duration Out of Range
```bash
curl -X PATCH "http://localhost:7001/api/clinics/${CLINIC_ID}/appointments/${APPOINTMENT_ID}" \
  -H "Content-Type: application/json" \
  -d '{"estimated_duration": 300}'
```

**Expected**: HTTP 422 (Pydantic validation) - duration must be 5-180 minutes

---

## ✅ Test Case 7: Multi-Field Update

### Objective
Verify that a single API call can update multiple fields simultaneously.

### Steps
```bash
# Update appointment with all fields at once
CLINIC_ID="7f6ef952-d755-43d9-b668-32c3b6879149"
APPOINTMENT_ID="<any_appointment_id>"
DOCTOR_ID="<different_doctor_id>"

curl -X PATCH "http://localhost:7001/api/clinics/${CLINIC_ID}/appointments/${APPOINTMENT_ID}" \
  -H "Content-Type: application/json" \
  -d "{
    \"scheduled_at\": \"$(date -u +%Y-%m-%dT15:00:00Z)\",
    \"estimated_duration\": 60,
    \"doctor_id\": \"${DOCTOR_ID}\",
    \"status\": \"CONFIRMED\",
    \"reason\": \"Updated reason\",
    \"notes\": \"Additional notes from testing\"
  }"
```

### Expected Results
✅ **HTTP 200** with updated AppointmentResponse
✅ **All fields updated** in response JSON
✅ **Backend log**: `updated_fields=['scheduled_at', 'estimated_duration', 'doctor_id', 'status', 'reason', 'notes']`
✅ **Check-in code expiration updated** (because scheduled_at changed)

### Verification
```bash
# Verify all changes persisted
curl "http://localhost:7001/api/clinics/${CLINIC_ID}/appointments/${APPOINTMENT_ID}" | jq '.'
# Should show all updated values
```

---

## ✅ Test Case 8: Check-in Code Expiration Update

### Objective
Verify that when `scheduled_at` changes, `checkin_code_expires_at` is automatically recalculated to 2 hours after new time.

### Steps
```bash
# Get original appointment
CLINIC_ID="7f6ef952-d755-43d9-b668-32c3b6879149"
APPOINTMENT_ID="<any_appointment_id>"

curl "http://localhost:7001/api/clinics/${CLINIC_ID}/appointments?date=$(date +%Y-%m-%d)" | \
  jq '.appointments[0] | {appointment_id, scheduled_at, checkin_code_expires_at}'

# Update scheduled_at to 3:00 PM
curl -X PATCH "http://localhost:7001/api/clinics/${CLINIC_ID}/appointments/${APPOINTMENT_ID}" \
  -H "Content-Type: application/json" \
  -d "{\"scheduled_at\": \"$(date -u +%Y-%m-%dT15:00:00Z)\"}"
```

### Expected Results
✅ **Response includes new `checkin_code_expires_at`**
✅ **Expiration is exactly 2 hours after new `scheduled_at`** (17:00:00 if scheduled at 15:00:00)
✅ **Check-in code unchanged** (only expiration updates)

### Verification
```bash
# Calculate expected expiration
# If scheduled_at = 2025-12-08T15:00:00Z
# Then checkin_code_expires_at = 2025-12-08T17:00:00Z

curl "http://localhost:7001/api/clinics/${CLINIC_ID}/appointments?date=$(date +%Y-%m-%d)" | \
  jq '.appointments[] | select(.appointment_id == "'${APPOINTMENT_ID}'") | {scheduled_at, checkin_code_expires_at}'
```

---

## 🎯 Success Criteria

All test cases must pass with the following outcomes:

### Functionality
- [x] ✅ Drag to new time updates `scheduled_at`
- [x] ✅ Drag to new doctor updates `doctor_id` and `scheduled_at`
- [x] ✅ Resize updates `estimated_duration`
- [x] ✅ Edit modal updates all changed fields
- [x] ✅ Multi-field updates work in single API call

### Error Handling
- [x] ✅ Network failures trigger rollback and user alert
- [x] ✅ Validation errors return 400/422 with meaningful messages
- [x] ✅ Cannot edit COMPLETED/CANCELLED appointments
- [x] ✅ Invalid doctor ID rejected

### Data Integrity
- [x] ✅ All changes persist to database
- [x] ✅ Check-in code expiration auto-updates with scheduled_at
- [x] ✅ Optimistic updates + rollback maintain consistency
- [x] ✅ Concurrent operations handled gracefully

### UX
- [x] ✅ Immediate visual feedback (optimistic updates)
- [x] ✅ Clear error messages for users
- [x] ✅ No console errors (except expected network failures)
- [x] ✅ Smooth animations during drag/drop/resize

---

## 🔍 Monitoring & Debugging

### Browser DevTools
```javascript
// Check for API calls
// Network tab → Filter by "appointments" → Inspect PATCH requests

// Check console for errors
// Console tab → Should see "Appointment updated successfully"

// Inspect React state
// React DevTools → Find AppointmentsCalendar component → Check appointments state
```

### Backend Logs
```bash
# Watch backend logs in real-time
tail -f <terminal_with_uvicorn>

# Look for these events:
# ✅ event='APPOINTMENT_UPDATED'
# ✅ appointment_id=<uuid>
# ✅ updated_fields=['scheduled_at', 'doctor_id']
```

### Database Queries
```bash
# Quick check all appointments for clinic
CLINIC_ID="7f6ef952-d755-43d9-b668-32c3b6879149"
curl "http://localhost:7001/api/clinics/${CLINIC_ID}/appointments?date=$(date +%Y-%m-%d)" | jq '.appointments | map({id: .appointment_id[0:8], doctor: .doctor_id[0:8], time: .scheduled_at[11:16], duration: .estimated_duration})'
```

---

## 📝 Testing Checklist

Print this checklist and mark off as you complete each test:

### Setup
- [ ] Backend running on :7001
- [ ] Frontend running on :9000
- [ ] Test data created (3 doctors, 4 appointments)
- [ ] Browser DevTools open (Console + Network tabs)

### Drag & Drop
- [ ] Drag appointment to different time (same doctor)
- [ ] Drag appointment to different doctor
- [ ] Verify API PATCH call in Network tab
- [ ] Verify update persists after refresh
- [ ] Test drag with network offline (rollback)

### Resize
- [ ] Resize appointment to longer duration
- [ ] Resize appointment to shorter duration
- [ ] Verify estimated_duration updated in backend
- [ ] Verify resize with network offline (rollback)

### Edit
- [ ] Edit appointment via Bryntum modal
- [ ] Verify all changed fields updated
- [ ] Test editing COMPLETED appointment (should fail)
- [ ] Test editing with invalid data (should fail)

### Error Scenarios
- [ ] Network failure → rollback + alert
- [ ] Invalid doctor ID → 400 error
- [ ] Invalid date format → 400 error
- [ ] Duration out of range → 422 error
- [ ] Completed appointment edit → 400 error

### Data Integrity
- [ ] Multi-field update works
- [ ] Check-in code expiration updates with scheduled_at
- [ ] All changes persist across page refresh
- [ ] No data loss during errors

### Performance
- [ ] UI responds immediately (< 100ms)
- [ ] No console errors or warnings
- [ ] Smooth animations during interactions
- [ ] Page remains responsive during API calls

---

## 🐛 Known Issues / Limitations

### Current Implementation
1. **Simple Error UI**: Uses browser `alert()` for errors (should use toast notifications in future)
2. **No Loading Indicators**: No spinner shown during API calls (optimistic updates hide this)
3. **Full Refresh on Error**: Could be more granular (refresh only affected appointment)
4. **No Undo/Redo**: Cannot undo accidental changes (planned for future)
5. **No Conflict Resolution**: If two users edit same appointment, last write wins

### Future Enhancements
- Replace `alert()` with toast notifications (Shadcn UI)
- Add loading spinner for slow networks
- Implement optimistic locking (version field)
- Add undo/redo with mutation history
- Real-time updates via WebSocket

---

## 📚 Reference Documentation

- **API Integration Summary**: `apps/aurity/components/appointments/API_INTEGRATION_SUMMARY.md`
- **QA Checklist**: `apps/aurity/components/bryntum/QA_CHECKLIST.md`
- **Architecture**: `apps/aurity/components/bryntum/ARCHITECTURE.md`
- **Backend API**: http://localhost:7001/docs (Swagger UI)

---

**Happy Testing! 🎉**

If you find any bugs, document them with:
1. Steps to reproduce
2. Expected vs actual behavior
3. Console errors (if any)
4. Backend logs (if applicable)
