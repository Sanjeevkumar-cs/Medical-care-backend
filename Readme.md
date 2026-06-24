# 🏥 Medical Care - Backend API

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-green.svg)](https://fastapi.tiangolo.com/)
[![Groq](https://img.shields.io/badge/Groq-API-purple.svg)](https://groq.com/)
[![ElevenLabs](https://img.shields.io/badge/ElevenLabs-TTS-blue.svg)](https://elevenlabs.io/)
[![SQLite](https://img.shields.io/badge/SQLite-Database-green.svg)](https://sqlite.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> **Backend API for Medical Care - AI-Powered Health Assistant with Voice, Vision & Medication Management**

This is the backend service for the Medical Care. It provides REST APIs for AI doctor consultation, medication management, appointment tracking, and voice report generation.

## ✨ Features

| Feature                   | Description                               | Status |
| ------------------------- | ----------------------------------------- | ------ |
| 🎤 Speech-to-Text         | Whisper-large-v3 via Groq API             | ✅     |
| 🖼️ Image Analysis         | Llama 4 Vision for medical image analysis | ✅     |
| 🩺 AI Doctor              | Llama 4 provides medical insights         | ✅     |
| 🔊 Text-to-Speech         | ElevenLabs realistic voice response       | ✅     |
| 💊 Medication CRUD        | Add, edit, delete medications             | ✅     |
| ⚠️ Smart Refill Alerts    | Detects overdue and low stock             | ✅     |
| 📅 Appointment Management | Schedule and track appointments           | ✅     |
| 🎙️ Voice Report           | gTTS generates complete health summary    | ✅     |
| 💾 SQLite Database        | Persistent local storage                  | ✅     |

## 📋 Table of Contents

- [Project Structure](#-project-structure)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Running the Server](#-running-the-server)
- [API Endpoints](#-api-endpoints)
- [Database Schema](#-database-schema)
- [Common Mistakes & Solutions](#-common-mistakes--solutions)
- [Troubleshooting](#-troubleshooting)
- [Tech Stack](#-tech-stack)
- [License](#-license)

## 📁 Project Structure

```

backend/
│
├── app.py # Main FastAPI application
├── config.py # Configuration settings
├── voice_assistant.py # Text-to-Speech functions
├── brain_of_the_doctor.py # AI vision & LLM integration
├── voice_of_the_patient.py # Speech-to-text (Whisper)
├── voice_of_the_doctor.py # ElevenLabs TTS
├── requirements.txt # Python dependencies
├── Pipfile # Pipenv dependencies
├── Pipfile.lock # Locked dependencies
├── .env # API keys (create this)
│
└── database/ # Database package
├── **init**.py
├── db_connection.py # SQLite connection handling
├── db_setup.py # Table creation & sample data
├── db_medications.py # Medication CRUD operations
├── db_appointments.py # Appointment operations
├── db_conversations.py # Conversation history
├── db_alerts.py # Alert & reporting logic
└── elderly_care.db # SQLite database file (auto-created)

```

## 🛠️ Prerequisites

| Requirement | Version | Check Command      |
| ----------- | ------- | ------------------ |
| Python      | 3.8+    | `python --version` |
| pipenv      | Latest  | `pipenv --version` |
| ffmpeg      | Latest  | `ffmpeg -version`  |

### Install ffmpeg (Required for audio processing)

| OS      | Command                   |
| ------- | ------------------------- |
| Windows | `winget install ffmpeg`   |
| Mac     | `brew install ffmpeg`     |
| Linux   | `sudo apt install ffmpeg` |

## 📦 Installation

### Method 1: Using Pipenv (Recommended)

Clone the repository
```bash
git clone https://github.com/Sanjeevkumar-cs/Medical-care-backend.git
cd Medical-care-Backend
```
Install pipenv if not already installed

```bash
pip install pipenv
```

Install dependencies

```bash
pipenv install
```

Activate virtual environment

```bash
pipenv shell
```

### Method 2: Using pip + venv

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## 🔑 Configuration

### Step 1: Create `.env` File

Create a `.env` file in the backend directory:

```env
GROQ_API_KEY="your_groq_api_key_here"
ELEVENLABS_API_KEY="your_elevenlabs_api_key_here"
```

> **Get your API keys:**
>
> - **Groq API Key**: Visit [console.groq.com/keys](https://console.groq.com/keys)
> - **ElevenLabs API Key**: Visit [elevenlabs.io/app/settings/api-keys](https://elevenlabs.io/app/settings/api-keys)

### Step 2: Configure `config.py` (Optional)

```python
# User Configuration
CURRENT_USER_ID = 1

# AI Models
DOCTOR_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
STT_MODEL = "whisper-large-v3"

# Voice Settings (slow=True is better for elderly)
VOICE_SPEED_SLOW = True
VOICE_LANGUAGE = "en"
```

## 🚀 Running the Server

### Start the FastAPI Server

```bash
# Using pipenv
pipenv run python app.py

# Or if you're in the pipenv shell
python app.py
```

### Expected Output

```
🔧 Initializing database...
✅ All 6 tables created successfully!
✅ Database ready!

============================================================
🚀 Starting Elderly Care Companion API Server...
============================================================
📍 API URL: http://localhost:8000
📍 API Docs: http://localhost:8000/docs
✅ Auto-schedule creation is ENABLED
✅ Appointment endpoints are ENABLED
============================================================

INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### Verify Server is Running

Open your browser and visit:

- **Health Check**: [http://localhost:8000/api/health](http://localhost:8000/api/health)
- **API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)

## 📡 API Endpoints

| Method | Endpoint                  | Description            | Request Body                                                               |
| ------ | ------------------------- | ---------------------- | -------------------------------------------------------------------------- |
| GET    | `/api/health`             | Health check           | -                                                                          |
| POST   | `/api/consult`            | AI Doctor consultation | `audio` (file), `image` (optional)                                         |
| GET    | `/api/medications`        | Get all medications    | -                                                                          |
| POST   | `/api/medications`        | Add new medication     | `name`, `pill_count`, `daily_dosage`, `refill_date`                        |
| DELETE | `/api/medications/{name}` | Delete medication      | -                                                                          |
| POST   | `/api/appointments`       | Add appointment        | `doctor_name`, `appointment_date`, `appointment_time`, `location`, `notes` |
| GET    | `/api/alerts`             | Get refill alerts      | -                                                                          |
| GET    | `/api/summary`            | Get daily summary      | -                                                                          |
| POST   | `/api/voice-report`       | Generate voice report  | -                                                                          |

### API Documentation

Once running, interactive API documentation is available at:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## 🗄️ Database Schema

The database contains 6 tables:

| Table                  | Description                                                                |
| ---------------------- | -------------------------------------------------------------------------- |
| `users`                | Patient information                                                        |
| `medications`          | Medications with pill counts & refill dates (composite key: user_id, name) |
| `medication_schedule`  | Daily schedule (Morning/Evening) & taken status                            |
| `appointments`         | Doctor appointments                                                        |
| `conversation_history` | AI doctor interactions                                                     |
| `metrics`              | Adherence rates & analytics                                                |

### View Database

Use [DB Browser for SQLite](https://sqlitebrowser.org/) to view/edit the database file at `database/elderly_care.db`

## ❌ Common Mistakes & Solutions

### Mistake 1: ImportError - Circular Import

**Error:**

```python
ImportError: cannot import name 'create_tables' from 'database'
```

**Solution:** Remove the circular import. Don't import from `database` inside `database.py` itself.

### Mistake 2: strptime() argument must be str, not int

**Error:**

```
strptime() argument must be str, not int
```

**Solution:** Run the date fix script or ensure dates are stored as strings (YYYY-MM-DD format):

```bash
python fix_database_dates.py
```

### Mistake 3: Groq API Key Not Loading

**Error:**

```
GROQ_API_KEY not found
```

**Solution:**

- Create `.env` file in the backend directory (not parent directory)
- Ensure `.env` is in the same folder as `app.py`
- Load environment variables at the top of `app.py`:

```python
from dotenv import load_dotenv
load_dotenv()
```

### Mistake 4: 401 Unauthorized - ElevenLabs

**Error:**

```
401 Unauthorized - ElevenLabs API key invalid
```

**Solution:**

- Check if API key is expired
- Generate a new key from ElevenLabs dashboard
- Update `.env` file and restart server

### Mistake 5: CORS Errors with Frontend

**Error:**

```
Access to XMLHttpRequest at 'http://localhost:8000/api/...' from origin 'http://localhost:3000' has been blocked by CORS policy
```

**Solution:** Ensure CORS middleware is properly configured in `app.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Mistake 6: Database Locked Error

**Error:**

```
sqlite3.OperationalError: database is locked
```

**Solution:**

- Close DB Browser for SQLite if open
- Restart the backend server
- Ensure no other processes are using the database

### Mistake 7: gTTS Connection Error

**Error:**

```
Failed to connect. Probable cause: Unknown
```

**Solution:**

- Check internet connection
- Use offline TTS (pyttsx3) as fallback:

```bash
pip install pyttsx3
```

- Or use ElevenLabs for all TTS

### Mistake 8: Port Already in Use

**Error:**

```
OSError: [Errno 98] Address already in use
```

**Solution:**

```bash
# Find process using port 8000
netstat -ano | findstr :8000

# Kill the process (replace PID with actual process ID)
taskkill /PID <PID> /F
```

### Mistake 9: Module 'database' has no attribute 'add_appointment'

**Error:**

```
AttributeError: module 'database' has no attribute 'add_appointment'
```

**Solution:** Ensure `add_appointment` is imported in `database/__init__.py`:

```python
from .db_appointments import add_appointment
```

### Mistake 10: Auto-schedule Not Creating

**Issue:** Medication schedules not created automatically when adding medication.

**Solution:** The `create_medication_schedule` function is called automatically in `add_medication_endpoint`. Verify the logs show:

```
✅ Created 2 schedule(s) for [medication_name]
```

## 🔧 Troubleshooting

### Quick Diagnostic Commands

```bash
# Check if server is running
curl http://localhost:8000/api/health

# Check API keys are loaded
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('GROQ:', os.getenv('GROQ_API_KEY')[:10] if os.getenv('GROQ_API_KEY') else 'Missing')"

# Check database connection
python -c "from database import get_connection; conn = get_connection(); print('✅ Database connected'); conn.close()"

# Test Groq API
python -c "from groq import Groq; import os; from dotenv import load_dotenv; load_dotenv(); client = Groq(api_key=os.getenv('GROQ_API_KEY')); print('✅ Groq API working')"

# Test ElevenLabs API
python -c "from elevenlabs.client import ElevenLabs; import os; from dotenv import load_dotenv; load_dotenv(); client = ElevenLabs(api_key=os.getenv('ELEVENLABS_API_KEY')); print('✅ ElevenLabs API working')"
```

### View Database Contents

```bash
python -c "
from database import get_all_medications, get_refill_alerts
print('Medications:', get_all_medications(1))
print('Alerts:', get_refill_alerts(1))
"
```

## 🛠️ Tech Stack

| Category             | Technology              |
| -------------------- | ----------------------- |
| **Framework**        | FastAPI                 |
| **LLM**              | Groq (Llama 4)          |
| **Vision**           | Groq (Llama 4 Vision)   |
| **STT**              | Groq (Whisper-large-v3) |
| **TTS (Doctor)**     | ElevenLabs              |
| **TTS (Summary)**    | gTTS / pyttsx3          |
| **Database**         | SQLite                  |
| **Audio Processing** | pydub, ffmpeg           |
| **Environment**      | python-dotenv           |
| **Server**           | Uvicorn                 |

## 📝 License

MIT License - Free for educational and personal use.

---

**Made with ❤️ for elderly care**

```

This README now:
1. ✅ Focuses only on **Backend** (no frontend)
2. ✅ Includes **10 common mistakes** you encountered
3. ✅ Has **diagnostic commands** for testing
4. ✅ Provides **solutions** for each common issue
5. ✅ Includes proper setup instructions for Pipenv/pip
6. ✅ Has API documentation and troubleshooting guide
```
