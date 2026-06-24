# backend/app.py - FastAPI Server for Elderly Care Companion
# ====================================================================
# This is the main backend server for the Elderly Care Companion application.
# It provides REST APIs for AI doctor consultation, medication management,
# appointment tracking, voice reports, and prescription OCR.
# ====================================================================

import os
import uuid
import tempfile
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
import uvicorn

# ====================================================================
# SECTION 1: CONFIGURATION & HELPERS IMPORTS
# ====================================================================
from config import CURRENT_USER_ID, SYSTEM_PROMPT, DOCTOR_MODEL, STT_MODEL
from brain_of_the_doctor import encode_image, analyze_image_with_query
from voice_of_the_patient import transcribe_with_groq
from voice_of_the_doctor import text_to_speech_with_elevenlabs
from voice_assistant import text_to_speech_gtts, cleanup_old_audio_files

# Database imports
from database import (
    create_tables, add_sample_data,
    get_all_medications, get_refill_alerts,
    get_daily_summary, get_upcoming_appointments,
    save_conversation, add_medication,
    get_medication_status_report, delete_medication,
    add_appointment
)

# Prescription OCR imports
from ocr_service import extract_medicines_from_prescription
from database.db_prescriptions import (
    save_prescription,
    get_user_prescriptions,
    get_prescription_details,
    # delete_prescription_from_db  # Commented out - we'll implement inline
)
from database.db_connection import get_connection  # For direct DB operations


# ====================================================================
# SECTION 2: DATABASE INITIALIZATION
# ====================================================================

print("🔧 Initializing database...")
create_tables()      # Creates all 8 tables (users, medications, schedules, appointments, conversations, metrics, prescriptions, prescription_medicines)
add_sample_data()    # Adds a demo user (John Doe) and sample medications
print("✅ Database ready!")

# Clean up old audio files from previous sessions (keeps only 20 most recent)
cleanup_old_audio_files(max_files=20)

# Create upload directory for prescription images
PRESCRIPTION_UPLOAD_DIR = "prescriptions"
os.makedirs(PRESCRIPTION_UPLOAD_DIR, exist_ok=True)


# ====================================================================
# SECTION 3: HELPER FUNCTION - AUTO-CREATE SCHEDULES
# ====================================================================

def create_medication_schedule(user_id: int, medication_name: str):
    """
    Automatically create daily schedule entries for a new medication.
    Creates Morning and Evening schedule entries for today.
    This runs automatically when a new medication is added.
    
    Args:
        user_id: ID of the user
        medication_name: Name of the medication (will be converted to lowercase)
    
    Returns:
        int: Number of schedules created (0, 1, or 2)
    """
    from datetime import date
    from database.db_connection import get_connection
    
    conn = get_connection()
    cursor = conn.cursor()
    today = date.today().isoformat()
    
    schedules_created = 0
    for time_of_day in ["Morning", "Evening"]:
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO medication_schedule 
                (user_id, medication_name, time_of_day, scheduled_date, taken)
                VALUES (?, ?, ?, ?, 0)
            ''', (user_id, medication_name.lower().strip(), time_of_day, today))
            if cursor.rowcount > 0:
                schedules_created += 1
        except Exception as e:
            print(f"⚠️ Could not create schedule for {medication_name} at {time_of_day}: {e}")
    
    conn.commit()
    conn.close()
    print(f"✅ Created {schedules_created} schedule(s) for {medication_name}")
    return schedules_created


# ====================================================================
# SECTION 4: CREATE FASTAPI APP & CORS CONFIGURATION
# ====================================================================

app = FastAPI(
    title="Elderly Care Companion API",
    description="Backend API for AI-powered elderly care assistant",
    version="2.0.0"
)

# CORS (Cross-Origin Resource Sharing) - Allows React frontend to communicate with this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # React dev server addresses
    allow_credentials=True,
    allow_methods=["*"],      # Allow all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],      # Allow all headers
)


# ====================================================================
# SECTION 5: HEALTH CHECK ENDPOINT
# ====================================================================

@app.get("/api/health")
async def health_check():
    """
    Simple health check endpoint to verify backend is running.
    Used by the React frontend to check connection status.
    
    Returns:
        dict: Status message with timestamp
    """
    return {
        "status": "healthy",
        "message": "Elderly Care Companion API is running",
        "timestamp": datetime.now().isoformat()
    }


# ====================================================================
# SECTION 6: AI DOCTOR CONSULTATION ENDPOINT
# ====================================================================

@app.post("/api/consult")
async def consult_doctor(
    audio: UploadFile = File(...),
    image: Optional[UploadFile] = File(None)
):
    """
    AI Doctor consultation endpoint.
    Processes voice recording and optional image, returns AI-generated medical advice.
    
    Flow:
    1. Save uploaded audio (and optional image) temporarily
    2. Convert speech to text using Groq Whisper
    3. Analyze text + image using Groq Llama 4 (Vision model)
    4. Save conversation to database
    5. Generate voice response using ElevenLabs TTS
    6. Return response with audio URL and medication summary
    
    Args:
        audio: Audio file recording from user
        image: Optional image file (symptom photo, prescription, etc.)
    
    Returns:
        JSONResponse: Contains transcript, doctor response, medication summary, alerts, and audio URL
    """
    
    # Step 1: Save audio file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_audio:
        audio_content = await audio.read()
        tmp_audio.write(audio_content)
        audio_path = tmp_audio.name
    
    # Step 2: Save image if provided
    image_path = None
    if image and image.filename:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_image:
            image_content = await image.read()
            tmp_image.write(image_content)
            image_path = tmp_image.name
    
    try:
        # Step 3: Speech to Text (STT) using Groq Whisper
        speech_to_text = transcribe_with_groq(
            model=STT_MODEL,
            file_path=audio_path
        )
        
        # Step 4: AI Doctor Response using Groq Llama 4
        if image_path:
            doctor_response = analyze_image_with_query(
                query=SYSTEM_PROMPT + " " + speech_to_text,
                encoded_image=encode_image(image_path),
                model=DOCTOR_MODEL
            )
            image_analyzed = True
        else:
            doctor_response = "No image provided. " + speech_to_text
            image_analyzed = False
        
        # Step 5: Save conversation to database for history
        save_conversation(
            user_id=CURRENT_USER_ID,
            patient_question=speech_to_text,
            doctor_response=doctor_response,
            image_analyzed=image_analyzed
        )
        
        # Step 6: Generate voice response using ElevenLabs
        audio_output_path = "final.mp3"
        text_to_speech_with_elevenlabs(
            input_text=doctor_response,
            output_filepath=audio_output_path
        )
        
        # Step 7: Get medication summary and alerts
        medication_summary = get_daily_summary(CURRENT_USER_ID)
        refill_alerts = get_refill_alerts(CURRENT_USER_ID)
        appointments = get_upcoming_appointments(CURRENT_USER_ID)
        
        # Step 8: Return response
        return JSONResponse({
            "success": True,
            "transcript": speech_to_text,
            "response": doctor_response,
            "medication_summary": medication_summary,
            "refill_alerts": refill_alerts,
            "appointments": [dict(apt) for apt in appointments],
            "audio_url": f"/api/audio/{os.path.basename(audio_output_path)}"
        })
        
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)
    
    finally:
        # Cleanup temporary files
        if os.path.exists(audio_path):
            os.unlink(audio_path)
        if image_path and os.path.exists(image_path):
            os.unlink(image_path)


# ====================================================================
# SECTION 7: MEDICATION MANAGEMENT ENDPOINTS
# ====================================================================

@app.get("/api/medications")
async def get_medications():
    """
    Get all medications for the current user.
    Returns list of medications with pill counts, dosages, and refill dates.
    
    Returns:
        JSONResponse: List of medications or error message
    """
    try:
        medications = get_all_medications(CURRENT_USER_ID)
        return JSONResponse({
            "success": True,
            "medications": medications
        })
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@app.post("/api/medications")
async def add_medication_endpoint(
    name: str = Form(...),
    pill_count: int = Form(...),
    daily_dosage: int = Form(...),
    refill_date: Optional[str] = Form(None)
):
    """
    Add a new medication to the user's list.
    Automatically creates morning and evening schedules for today.
    
    Request body (form-data):
    - name: Medication name (e.g., "Aspirin")
    - pill_count: Number of pills remaining
    - daily_dosage: Pills to take per day
    - refill_date: When refill is needed (YYYY-MM-DD format)
    
    Returns:
        JSONResponse: Success message or error
    """
    try:
        # Add medication to database
        add_medication(
            user_id=CURRENT_USER_ID,
            name=name,
            pill_count=pill_count,
            daily_dosage=daily_dosage,
            refill_date=refill_date
        )
        
        # Auto-create medication schedules (Morning and Evening)
        create_medication_schedule(CURRENT_USER_ID, name)
        
        return JSONResponse({
            "success": True,
            "message": f"Added {name} successfully with daily schedules"
        })
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@app.delete("/api/medications/{name}")
async def delete_medication_endpoint(name: str):
    """
    Delete a medication from the user's list.
    Note: This does NOT delete associated schedule entries (they remain for history).
    
    Args:
        name: Name of the medication to delete
    
    Returns:
        JSONResponse: Success message or error
    """
    try:
        delete_medication(CURRENT_USER_ID, name)
        return JSONResponse({
            "success": True,
            "message": f"Deleted {name} successfully"
        })
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


# ====================================================================
# SECTION 8: APPOINTMENT MANAGEMENT ENDPOINTS
# ====================================================================

@app.post("/api/appointments")
async def add_appointment_endpoint(
    doctor_name: str = Form(...),
    appointment_date: str = Form(...),
    appointment_time: str = Form(...),
    location: Optional[str] = Form(None),
    notes: Optional[str] = Form(None)
):
    """
    Schedule a new doctor appointment.
    
    Request body (form-data):
    - doctor_name: Name of the doctor
    - appointment_date: Date of appointment (YYYY-MM-DD)
    - appointment_time: Time of appointment (HH:MM)
    - location: Clinic/Hospital address (optional)
    - notes: Additional notes (optional)
    
    Returns:
        JSONResponse: Success message or error
    """
    try:
        add_appointment(
            user_id=CURRENT_USER_ID,
            doctor_name=doctor_name,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            location=location or "",
            notes=notes or ""
        )
        return JSONResponse({
            "success": True,
            "message": f"Appointment with Dr. {doctor_name} added successfully"
        })
    except Exception as e:
        print(f"Error adding appointment: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


# ====================================================================
# SECTION 9: ALERTS & SUMMARY ENDPOINTS
# ====================================================================

@app.get("/api/alerts")
async def get_alerts():
    """
    Get medication refill alerts.
    Returns list of medications that are:
    - Overdue for refill (refill date passed)
    - Low on stock (less than 7 pills)
    - Will run out before refill date
    
    Returns:
        JSONResponse: List of alerts or error message
    """
    try:
        alerts = get_refill_alerts(CURRENT_USER_ID)
        return JSONResponse({
            "success": True,
            "alerts": alerts
        })
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@app.get("/api/summary")
async def get_summary():
    """
    Get daily summary including:
    - Today's medication schedule
    - Refill alerts
    - Upcoming appointments
    - Detailed medication status report
    
    Returns:
        JSONResponse: Complete daily summary or error
    """
    try:
        summary = get_daily_summary(CURRENT_USER_ID)
        status = get_medication_status_report(CURRENT_USER_ID)
        appointments = get_upcoming_appointments(CURRENT_USER_ID)
        
        return JSONResponse({
            "success": True,
            "daily_summary": summary,
            "status_report": status,
            "appointments": [dict(apt) for apt in appointments]
        })
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


# ====================================================================
# SECTION 10: VOICE REPORT ENDPOINT
# ====================================================================

@app.post("/api/voice-report")
async def generate_voice_report():
    """
    Generate a complete voice health report using gTTS (free).
    Creates a concise summary of all medications and alerts.
    Returns audio URL for playback and download.
    
    Returns:
        JSONResponse: Audio URL or error message
    """
    try:
        medications = get_all_medications(CURRENT_USER_ID)
        alerts = get_refill_alerts(CURRENT_USER_ID)
        
        # Build concise, natural-sounding text for voice
        complete_text = "Hello. Here is your complete health report. "
        
        if medications:
            complete_text += f"You have {len(medications)} medications. "
            for med in medications[:3]:  # Limit to first 3 for brevity
                days_left = med['pill_count'] // med['daily_dosage'] if med['daily_dosage'] > 0 else 0
                complete_text += f"{med['name']} has {med['pill_count']} pills remaining. "
                complete_text += f"You take {med['daily_dosage']} pill per day. "
                if days_left > 0:
                    complete_text += f"This will last about {days_left} days. "
                if med.get('refill_date'):
                    complete_text += f"Refill needed by {med['refill_date']}. "
            if len(medications) > 3:
                complete_text += f"And {len(medications) - 3} more medications. "
        else:
            complete_text += "You have no medications. "
        
        # Clean up alerts (remove emojis and formatting)
        clean_alerts = alerts.replace("⚠️ MEDICATION ALERTS:", "")
        clean_alerts = clean_alerts.replace("🔴", "").replace("🟡", "").replace("🟠", "")
        complete_text += clean_alerts
        complete_text += " Take care of yourself."
        
        # Generate voice using gTTS
        audio_file = text_to_speech_gtts(complete_text, "complete_health_report.mp3")
        
        return JSONResponse({
            "success": True,
            "audio_url": f"/api/audio/{os.path.basename(audio_file)}"
        })
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@app.get("/api/audio/{filename}")
async def get_audio(filename: str):
    """
    Serve audio files (voice responses and reports).
    Checks both audio_cache folder and current directory.
    
    Args:
        filename: Name of the audio file to retrieve
    
    Returns:
        FileResponse: Audio file or JSON error
    """
    audio_paths = [
        f"audio_cache/{filename}",
        filename
    ]
    
    for audio_path in audio_paths:
        if os.path.exists(audio_path):
            return FileResponse(audio_path, media_type="audio/mpeg")
    
    return JSONResponse({"error": "File not found"}, status_code=404)


# ====================================================================
# SECTION 11: PRESCRIPTION OCR ENDPOINTS
# ====================================================================

@app.post("/api/prescription/upload")
async def upload_prescription(
    prescription_image: UploadFile = File(...)
):
    """
    Upload and process a handwritten prescription using OCR.
    Extracts medicines, dosages, and instructions using OCR.space API.
    
    Flow:
    1. Validate and save uploaded image
    2. Perform OCR to extract text
    3. Parse extracted text to identify medicines
    4. Save prescription data to database
    5. Return extracted medicines for user confirmation
    
    Args:
        prescription_image: Image file of the prescription
    
    Returns:
        JSONResponse: Extracted medicines, instructions, and prescription ID
    """
    # Validate file type
    allowed_extensions = ('.png', '.jpg', '.jpeg', '.webp')
    if not prescription_image.filename.lower().endswith(allowed_extensions):
        return JSONResponse({
            "success": False,
            "error": "Only image files (PNG, JPG, JPEG, WEBP) are allowed."
        }, status_code=400)
    
    # Generate unique filename to avoid collisions
    file_extension = prescription_image.filename.split('.')[-1]
    unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
    file_path = os.path.join(PRESCRIPTION_UPLOAD_DIR, unique_filename)
    
    # Save uploaded image
    content = await prescription_image.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Perform OCR and extract medicine data
    try:
        result = extract_medicines_from_prescription(file_path)
    except Exception as e:
        if os.path.exists(file_path):
            os.unlink(file_path)
        return JSONResponse({
            "success": False,
            "error": f"OCR processing failed: {str(e)}"
        }, status_code=500)
    
    if result['success']:
        # Save to database
        prescription_id = save_prescription(
            user_id=CURRENT_USER_ID,
            image_path=file_path,
            extracted_text=result['full_text'],
            medicines=result['medicines'],
            instructions=result.get('instructions', [])
        )
        
        return JSONResponse({
            "success": True,
            "prescription_id": prescription_id,
            "medicines": result['medicines'],
            "instructions": result.get('instructions', []),
            "full_text": result['full_text'],
            "image_url": f"/api/prescription/image/{unique_filename}"
        })
    else:
        # Clean up file if OCR failed
        if os.path.exists(file_path):
            os.unlink(file_path)
        return JSONResponse({
            "success": False,
            "error": result.get('error', 'Could not extract text. Please ensure the image is clear and well-lit.')
        }, status_code=400)


@app.get("/api/prescriptions")
async def get_prescriptions():
    """
    Get all prescriptions uploaded by the current user.
    Returns list with prescription IDs, upload dates, and preview text.
    
    Returns:
        JSONResponse: List of prescriptions or error
    """
    try:
        prescriptions = get_user_prescriptions(CURRENT_USER_ID)
        return JSONResponse({
            "success": True,
            "prescriptions": prescriptions
        })
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@app.get("/api/prescription/{prescription_id}")
async def get_prescription_detail(prescription_id: int):
    """
    Get full details of a specific prescription.
    Includes all extracted medicines and the full OCR text.
    
    Args:
        prescription_id: ID of the prescription to retrieve
    
    Returns:
        JSONResponse: Full prescription details or error
    """
    try:
        details = get_prescription_details(prescription_id)
        if not details:
            return JSONResponse({
                "success": False,
                "error": "Prescription not found"
            }, status_code=404)
        return JSONResponse({
            "success": True,
            "details": details
        })
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@app.get("/api/prescription/image/{filename}")
async def get_prescription_image(filename: str):
    """
    Serve the original prescription image file.
    Used to display the uploaded image in the frontend.
    
    Args:
        filename: Name of the image file to retrieve
    
    Returns:
        FileResponse: Image file or JSON error
    """
    file_path = os.path.join(PRESCRIPTION_UPLOAD_DIR, filename)
    if os.path.exists(file_path):
        # Determine content type based on file extension
        content_type = "image/jpeg"
        if filename.endswith('.png'):
            content_type = "image/png"
        elif filename.endswith('.webp'):
            content_type = "image/webp"
        return FileResponse(file_path, media_type=content_type)
    return JSONResponse({"error": "File not found"}, status_code=404)


# ====================================================================
# SECTION 12: PRESCRIPTION DELETE ENDPOINT (WITH INLINE IMPLEMENTATION)
# ====================================================================

def delete_prescription_from_db(prescription_id: int):
    """
    Helper function to delete a prescription from the database.
    This is defined inline to avoid import issues.
    
    Args:
        prescription_id: ID of the prescription to delete
    
    Returns:
        bool: True if deletion was successful
    
    Raises:
        Exception: If deletion fails
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # First check if the prescription exists
        cursor.execute("SELECT id FROM prescriptions WHERE id = ?", (prescription_id,))
        if not cursor.fetchone():
            raise ValueError(f"Prescription with ID {prescription_id} not found")
        
        # Delete the prescription (cascade will handle related records)
        cursor.execute("DELETE FROM prescriptions WHERE id = ?", (prescription_id,))
        conn.commit()
        print(f"✅ Deleted prescription ID {prescription_id} from database")
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error deleting prescription {prescription_id}: {e}")
        raise e
    finally:
        conn.close()


@app.delete("/api/prescription/{prescription_id}")
async def delete_prescription(prescription_id: int):
    """
    Delete a prescription from the database.
    Also deletes associated medicines and the image file.
    
    This endpoint handles:
    1. Validating prescription exists
    2. Deleting the physical image file from disk
    3. Deleting the prescription record from database (cascades to associated medicines)
    4. Returning appropriate success/error responses
    
    Args:
        prescription_id: ID of the prescription to delete
    
    Returns:
        JSONResponse: Success message or error with appropriate status code
    """
    try:
        # Step 1: Get prescription details to verify existence and find image path
        details = get_prescription_details(prescription_id)
        if not details:
            return JSONResponse({
                "success": False,
                "error": f"Prescription with ID {prescription_id} not found"
            }, status_code=404)
        
        # Step 2: Get the image path from details
        image_path = details.get('image_path')
        
        # Step 3: Delete the physical image file if it exists
        if image_path and os.path.exists(image_path):
            try:
                os.unlink(image_path)
                print(f"🗑️ Successfully deleted image file: {image_path}")
            except OSError as e:
                # Log error but continue with database deletion
                print(f"⚠️ Could not delete image file {image_path}: {e}")
        elif image_path:
            print(f"⚠️ Image file not found at path: {image_path}")
        
        # Step 4: Delete from database using the inline helper function
        delete_prescription_from_db(prescription_id)
        print(f"🗑️ Successfully deleted prescription ID {prescription_id} from database")
        
        return JSONResponse({
            "success": True,
            "message": f"Prescription ID {prescription_id} deleted successfully",
            "deleted_image": bool(image_path and os.path.exists(image_path))
        })
        
    except ValueError as e:
        # Handle "not found" errors
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=404)
    except Exception as e:
        print(f"❌ Error deleting prescription {prescription_id}: {e}")
        return JSONResponse({
            "success": False,
            "error": f"Failed to delete prescription: {str(e)}"
        }, status_code=500)


# ====================================================================
# SECTION 13: ADDITIONAL DELETE ENDPOINTS
# ====================================================================

@app.delete("/api/prescription/filename/{filename}")
async def delete_prescription_by_filename(filename: str):
    """
    Delete a prescription by its image filename.
    Useful when the frontend only has the filename.
    
    Args:
        filename: Name of the prescription image file
    
    Returns:
        JSONResponse: Success message or error
    """
    try:
        # Find prescription with this image filename
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id FROM prescriptions 
            WHERE user_id = ? AND image_path LIKE ?
        ''', (CURRENT_USER_ID, f'%{filename}'))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return JSONResponse({
                "success": False,
                "error": f"Prescription with filename {filename} not found"
            }, status_code=404)
        
        # Delete using the main delete endpoint function
        return await delete_prescription(result['id'])
        
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@app.delete("/api/prescriptions/bulk")
async def delete_multiple_prescriptions(prescription_ids: list[int]):
    """
    Delete multiple prescriptions at once.
    Useful for batch cleanup operations.
    
    Args:
        prescription_ids: List of prescription IDs to delete
    
    Returns:
        JSONResponse: Summary of deletions
    """
    deleted_count = 0
    failed_ids = []
    errors = []
    
    for pid in prescription_ids:
        try:
            # Use the main delete function
            response = await delete_prescription(pid)
            if response.status_code == 200:
                deleted_count += 1
            else:
                failed_ids.append(pid)
                # Try to extract error message
                response_data = response.body
                import json
                try:
                    error_data = json.loads(response_data)
                    errors.append(f"ID {pid}: {error_data.get('error', 'Unknown error')}")
                except:
                    errors.append(f"ID {pid}: Deletion failed")
        except Exception as e:
            failed_ids.append(pid)
            errors.append(f"ID {pid}: {str(e)}")
    
    return JSONResponse({
        "success": True,
        "message": f"Deleted {deleted_count} prescriptions",
        "total_requested": len(prescription_ids),
        "deleted": deleted_count,
        "failed": failed_ids,
        "errors": errors if errors else None
    })


# ====================================================================
# SECTION 14: SERVER LAUNCH
# ====================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("🚀 Starting Elderly Care Companion API Server...")
    print("="*70)
    print("📍 API URL: http://localhost:8000")
    print("📍 API Docs (Swagger): http://localhost:8000/docs")
    print("📍 ReDoc: http://localhost:8000/redoc")
    print("-"*70)
    print("✅ Auto-schedule creation is ENABLED")
    print("✅ Appointment endpoints are ENABLED")
    print("✅ Prescription OCR endpoints are ENABLED (OCR.space API)")
    print("✅ Prescription DELETE endpoints are ENABLED")
    print("  - DELETE /api/prescription/{id} - Delete by ID")
    print("  - DELETE /api/prescription/filename/{filename} - Delete by filename")
    print("  - DELETE /api/prescriptions/bulk - Bulk delete")
    print("="*70 + "\n")
    
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        reload=False,
        log_level="info"
    )