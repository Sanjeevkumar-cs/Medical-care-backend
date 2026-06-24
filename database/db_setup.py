# database/db_setup.py - Updated with Prescription Tables
# ====================================================================
# DB_SETUP.PY - Database Table Creation and Initialization
# ====================================================================

import sqlite3
from datetime import date
from .db_connection import get_connection


def create_tables():
    """
    Creates all the tables in the database.
    Run this once when your app starts to make sure tables exist.
    
    Tables created:
    1. users - Patient information
    2. medications - Medication tracking (composite key: user_id, name)
    3. medication_schedule - Daily schedule for medications
    4. appointments - Doctor appointments
    5. conversation_history - AI doctor conversations
    6. metrics - Health metrics and adherence
    7. prescriptions - Uploaded prescription images and OCR data (NEW)
    8. prescription_medicines - Extracted medicines from prescriptions (NEW)
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # ==================================================================
    # TABLE 1: USERS
    # Stores basic information about each elderly user
    # ==================================================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER,
            phone TEXT,
            emergency_contact TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # ==================================================================
    # TABLE 2: MEDICATIONS
    # Stores medication information with composite primary key
    # PRIMARY KEY (user_id, name) = One user cannot have duplicate med names
    # ==================================================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS medications (
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            pill_count INTEGER DEFAULT 0,
            daily_dosage INTEGER DEFAULT 1,
            refill_date DATE,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, name),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # ==================================================================
    # TABLE 3: MEDICATION_SCHEDULE
    # Tracks when medications should be taken and if they were taken
    # ==================================================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS medication_schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            medication_name TEXT NOT NULL,
            time_of_day TEXT NOT NULL,
            taken BOOLEAN DEFAULT 0,
            scheduled_date DATE NOT NULL,
            FOREIGN KEY (user_id, medication_name) REFERENCES medications (user_id, name)
        )
    ''')
    
    # ==================================================================
    # TABLE 4: APPOINTMENTS
    # Stores doctor appointments and medical visits
    # ==================================================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            doctor_name TEXT NOT NULL,
            appointment_date DATE NOT NULL,
            appointment_time TEXT NOT NULL,
            location TEXT,
            notes TEXT,
            reminder_sent BOOLEAN DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # ==================================================================
    # TABLE 5: CONVERSATION_HISTORY
    # Logs all AI assistant conversations for analysis
    # ==================================================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            patient_question TEXT NOT NULL,
            doctor_response TEXT NOT NULL,
            image_analyzed BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # ==================================================================
    # TABLE 6: METRICS
    # Stores daily/weekly metrics for health monitoring
    # ==================================================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            metric_date DATE NOT NULL,
            medication_adherence_rate FLOAT,
            total_conversations INTEGER,
            avg_response_sentiment FLOAT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # ==================================================================
    # TABLE 7: PRESCRIPTIONS
    # Stores uploaded prescription images and OCR extracted data
    # ==================================================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS prescriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            image_path TEXT NOT NULL,
            extracted_text TEXT,
            medicines TEXT,
            instructions TEXT,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'processed',
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # ==================================================================
    # TABLE 8: PRESCRIPTION_MEDICINES
    # Stores individual medicines extracted from each prescription
    # ==================================================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS prescription_medicines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prescription_id INTEGER NOT NULL,
            medicine_name TEXT NOT NULL,
            dosage TEXT,
            is_confirmed BOOLEAN DEFAULT 0,
            added_to_medications BOOLEAN DEFAULT 0,
            FOREIGN KEY (prescription_id) REFERENCES prescriptions (id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ All 8 tables created successfully!")


def add_sample_data():
    """Add sample data for testing the application"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check if we already have users
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    
    if count == 0:
        # Add a sample user
        cursor.execute('''
            INSERT INTO users (name, age, phone, emergency_contact)
            VALUES (?, ?, ?, ?)
        ''', ("John Doe", 75, "555-1234", "Jane Doe: 555-5678"))
        
        user_id = cursor.lastrowid
        print(f"✅ Added sample user: John Doe (ID: {user_id})")
        
        # Add sample medications
        today = date.today().isoformat()
        
        cursor.execute('''
            INSERT OR IGNORE INTO medications (user_id, name, pill_count, daily_dosage, refill_date)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, "aspirin", 30, 2, "2026-06-15"))
        
        cursor.execute('''
            INSERT OR IGNORE INTO medications (user_id, name, pill_count, daily_dosage, refill_date)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, "metformin", 3, 1, "2026-05-25"))
        
        cursor.execute('''
            INSERT OR IGNORE INTO medications (user_id, name, pill_count, daily_dosage, refill_date)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, "paracetamol", 30, 1, "2026-04-17"))
        
        # Add sample schedule for today
        cursor.execute("SELECT name FROM medications WHERE user_id = ?", (user_id,))
        meds = cursor.fetchall()
        
        for med in meds:
            for time in ["Morning", "Evening"]:
                cursor.execute('''
                    INSERT OR IGNORE INTO medication_schedule 
                    (user_id, medication_name, time_of_day, scheduled_date)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, med['name'], time, today))
        
        conn.commit()
        print("✅ Sample data added successfully!")
    else:
        print("ℹ️ Sample data already exists, skipping...")
    
    conn.close()


def display_all_medications():
    """Display all medications in a nice formatted table"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT m.user_id, u.name as patient, m.name as medication, 
               m.pill_count, m.daily_dosage, m.refill_date
        FROM medications m
        JOIN users u ON m.user_id = u.id
        ORDER BY u.name, m.name
    ''')
    
    rows = cursor.fetchall()
    conn.close()
    
    print("\n" + "=" * 70)
    print("MY MEDICATIONS")
    print("=" * 70)
    print(f"{'Patient':<12} {'Medication':<15} {'Pills':<8} {'Daily':<8} {'Refill Date':<12}")
    print("-" * 70)
    
    for row in rows:
        print(f"{row['patient']:<12} {row['medication']:<15} {row['pill_count']:<8} {row['daily_dosage']:<8} {row['refill_date']:<12}")
    
    print("=" * 70)