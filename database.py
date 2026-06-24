# ====================================================================
# DATABASE.PY - ELDERLY CARE COMPANION
# ====================================================================
# THIS FILE HANDLES ALL DATABASE OPERATIONS FOR THE ELDERLY CARE SYSTEM
# ====================================================================
# Changes Made:
# 1. Composite Primary Key (user_id, name) for medications table
# 2. Proper refill date checking (overdue detection)
# 3. Stock prediction logic (will it last until refill date?)
# 4. No duplicate medications allowed at database level
# ====================================================================

import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime, date
from typing import List, Dict, Optional
import os

# ====================================================================
# PART 1: DATABASE SETUP AND CONNECTION
# ====================================================================

# Create a folder called 'database' in your project
DB_DIR = Path("database")
DB_DIR.mkdir(exist_ok=True)

# This is the actual database file path
DB_PATH = DB_DIR / "elderly_care.db"

def get_connection():
    """
    Creates and returns a connection to the SQLite database.
    Checks for corruption before connecting.
    """
    # Check if database file is corrupted before connecting
    if DB_PATH.exists():
        try:
            test_conn = sqlite3.connect(str(DB_PATH))
            test_conn.cursor().execute("SELECT 1")
            test_conn.close()
        except sqlite3.DatabaseError:
            print("⚠️ Corrupted database found. Creating new one...")
            DB_PATH.unlink()  # Delete the corrupted file
    
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row  # Access columns by name (like row['name'])
    return conn


def create_tables():
    """
    Creates all the tables in the database.
    Run this once when your app starts to make sure tables exist.
    
    KEY CHANGE: Medications table now uses composite primary key (user_id, name)
    This prevents duplicate medications at the database level.
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
    
    conn.commit()
    conn.close()
    print("✅ All 6 tables created successfully!")


# ====================================================================
# PART 2: MEDICATION FUNCTIONS (CRUD Operations)
# ====================================================================

def add_medication(user_id: int, name: str, pill_count: int, daily_dosage: int, refill_date: str = None):
    """
    Add a new medication to the database.
    If medication already exists for this user, update it instead.
    
    KEY CHANGE: Uses INSERT OR REPLACE to handle duplicates automatically.
    No more duplicate entries!
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Convert name to lowercase for consistent comparison
    name = name.lower().strip()
    
    try:
        cursor.execute('''
            INSERT INTO medications (user_id, name, pill_count, daily_dosage, refill_date)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, name, pill_count, daily_dosage, refill_date))
        conn.commit()
        print(f"✅ Added medication: {name}")
    except sqlite3.IntegrityError:
        # Medication already exists, update it instead
        cursor.execute('''
            UPDATE medications 
            SET pill_count = ?, daily_dosage = ?, refill_date = ?, last_updated = CURRENT_TIMESTAMP
            WHERE user_id = ? AND name = ?
        ''', (pill_count, daily_dosage, refill_date, user_id, name))
        conn.commit()
        print(f"🔄 Updated existing medication: {name}")
    
    conn.close()


def get_all_medications(user_id: int) -> List[Dict]:
    """
    Get all medications for a specific user.
    Returns a list of dictionaries with medication details.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT name, pill_count, daily_dosage, refill_date, last_updated
        FROM medications
        WHERE user_id = ?
        ORDER BY name
    ''', (user_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    medications = []
    for row in rows:
        medications.append({
            'name': row['name'],
            'pill_count': row['pill_count'],
            'daily_dosage': row['daily_dosage'],
            'refill_date': row['refill_date'],
            'last_updated': row['last_updated']
        })
    return medications


def update_pill_count(user_id: int, name: str, new_count: int):
    """
    Update how many pills are left for a specific medication.
    Uses user_id + name composite key instead of medication_id.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    name = name.lower().strip()
    
    cursor.execute('''
        UPDATE medications
        SET pill_count = ?, last_updated = CURRENT_TIMESTAMP
        WHERE user_id = ? AND name = ?
    ''', (new_count, user_id, name))
    
    conn.commit()
    conn.close()
    print(f"✅ Updated pill count for {name} to {new_count}")


def record_medication_taken(user_id: int, name: str, time_of_day: str):
    """
    Mark that a patient took their medication.
    Automatically decreases pill count by daily_dosage.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    name = name.lower().strip()
    
    cursor.execute('''
        SELECT daily_dosage FROM medications 
        WHERE user_id = ? AND name = ?
    ''', (user_id, name))
    
    result = cursor.fetchone()
    
    if result:
        daily_dosage = result['daily_dosage']
        
        # Decrease pill count
        cursor.execute('''
            UPDATE medications
            SET pill_count = pill_count - ?, last_updated = CURRENT_TIMESTAMP
            WHERE user_id = ? AND name = ?
        ''', (daily_dosage, user_id, name))
        
        # Record in schedule
        today = date.today().isoformat()
        cursor.execute('''
            INSERT OR REPLACE INTO medication_schedule 
            (user_id, medication_name, time_of_day, taken, scheduled_date)
            VALUES (?, ?, ?, 1, ?)
        ''', (user_id, name, time_of_day, today))
        
        conn.commit()
        print(f"✅ Recorded: {name} taken at {time_of_day}")
    else:
        print(f"⚠️ Medication '{name}' not found for user {user_id}")
    
    conn.close()


def delete_medication(user_id: int, name: str):
    """
    Delete a medication from the database.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    name = name.lower().strip()
    
    cursor.execute('''
        DELETE FROM medications
        WHERE user_id = ? AND name = ?
    ''', (user_id, name))
    
    conn.commit()
    conn.close()
    print(f"✅ Deleted medication: {name}")


# ====================================================================
# PART 3: SMART MEDICATION ALERTS (The Core Logic)
# ====================================================================

def get_low_stock_medications(user_id: int, threshold: int = 5) -> List[Dict]:
    """
    Find medications that need attention because:
    1. Refill date has passed (OVERDUE)
    2. Low pill count (less than threshold)
    3. Will run out before refill date (PREDICTIVE)
    
    KEY CHANGE: Now checks refill_date vs today, not just pill count!
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT name, pill_count, daily_dosage, refill_date
        FROM medications
        WHERE user_id = ?
    ''', (user_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    today = date.today()
    needs_attention = []
    
    for row in rows:
        refill_date_str = row['refill_date']
        pill_count = row['pill_count']
        daily_dosage = row['daily_dosage'] if row['daily_dosage'] > 0 else 1
        name = row['name']
        
        # Initialize flags
        refill_overdue = False
        days_overdue = 0
        low_stock = False
        will_run_out = False
        days_until_refill = 0
        
        # ============================================================
        # CASE 1: Check if refill date has passed (OVERDUE)
        # ============================================================
        if refill_date_str:
            refill_date = datetime.strptime(refill_date_str, '%Y-%m-%d').date()
            if today > refill_date:
                refill_overdue = True
                days_overdue = (today - refill_date).days
        
        # ============================================================
        # CASE 2: Check low pill count
        # ============================================================
        low_stock = pill_count < threshold
        
        # ============================================================
        # CASE 3: Check if stock will last until refill date (PREDICTIVE)
        # ============================================================
        if refill_date_str and not refill_overdue:
            refill_date = datetime.strptime(refill_date_str, '%Y-%m-%d').date()
            days_until_refill = (refill_date - today).days
            if days_until_refill > 0:
                required_pills = daily_dosage * days_until_refill
                if pill_count < required_pills:
                    will_run_out = True
        
        # ============================================================
        # Add to attention list if any condition is true
        # ============================================================
        if low_stock or refill_overdue or will_run_out:
            days_remaining = pill_count // daily_dosage if daily_dosage > 0 else 0
            needs_attention.append({
                'name': name,
                'pill_count': pill_count,
                'daily_dosage': daily_dosage,
                'refill_date': refill_date_str,
                'days_remaining': days_remaining,
                'refill_overdue': refill_overdue,
                'days_overdue': days_overdue if refill_overdue else 0,
                'will_run_out': will_run_out,
                'days_until_refill': days_until_refill if not refill_overdue else 0
            })
    
    return needs_attention


def get_refill_alerts(user_id: int) -> str:
    """
    Generate a human-readable alert message about medications needing refill.
    Returns formatted string with emojis for different severity levels.
    """
    meds_needing_attention = get_low_stock_medications(user_id, threshold=7)
    
    if not meds_needing_attention:
        return "✅ All medications have sufficient stock."
    
    alert = "⚠️ MEDICATION ALERTS:\n"
    
    for med in meds_needing_attention:
        if med['refill_overdue']:
            alert += f"  🔴 {med['name']}: REFILL OVERDUE by {med['days_overdue']} days! Please refill immediately.\n"
        elif med['will_run_out']:
            alert += f"  🟡 {med['name']}: Will run out before refill date ({med['refill_date']}). Only {med['pill_count']} pills left.\n"
        else:
            alert += f"  🟠 {med['name']}: Low stock - Only {med['pill_count']} pills left ({med['days_remaining']} days remaining)\n"
    
    return alert


def get_medication_status_report(user_id: int) -> str:
    """
    Generate a detailed report showing status of ALL medications
    including whether they are on track or need attention.
    
    KEY FEATURE: Shows complete picture for every medication.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT name, pill_count, daily_dosage, refill_date
        FROM medications
        WHERE user_id = ?
        ORDER BY name
    ''', (user_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    today = date.today()
    report = "📊 **MEDICATION STATUS REPORT**\n\n"
    
    for row in rows:
        name = row['name']
        pill_count = row['pill_count']
        daily_dosage = row['daily_dosage'] if row['daily_dosage'] > 0 else 1
        refill_date_str = row['refill_date']
        
        days_remaining_stock = pill_count // daily_dosage
        
        if refill_date_str:
            refill_date = datetime.strptime(refill_date_str, '%Y-%m-%d').date()
            
            if today > refill_date:
                days_overdue = (today - refill_date).days
                status = f"🔴 REFILL OVERDUE by {days_overdue} days"
            else:
                days_until_refill = (refill_date - today).days
                required_pills = daily_dosage * days_until_refill
                
                if pill_count >= required_pills:
                    status = f"✅ On track - Enough until {refill_date_str}"
                else:
                    shortage = required_pills - pill_count
                    status = f"⚠️ Will run out - Need {shortage} more pills to reach {refill_date_str}"
        else:
            status = f"ℹ️ No refill date set - {days_remaining_stock} days remaining"
        
        report += f"💊 {name}\n"
        report += f"   • Pills left: {pill_count}\n"
        report += f"   • Daily dosage: {daily_dosage} pill(s)/day\n"
        report += f"   • Days of stock left: {days_remaining_stock} days\n"
        report += f"   • Status: {status}\n\n"
    
    return report


# ====================================================================
# PART 4: APPOINTMENT FUNCTIONS
# ====================================================================

def add_appointment(user_id: int, doctor_name: str, appointment_date: str, 
                    appointment_time: str, location: str = "", notes: str = ""):
    """
    Schedule a new doctor appointment.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO appointments (user_id, doctor_name, appointment_date, appointment_time, location, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, doctor_name, appointment_date, appointment_time, location, notes))
    
    conn.commit()
    conn.close()
    print(f"✅ Appointment scheduled with Dr. {doctor_name} on {appointment_date}")


def get_upcoming_appointments(user_id: int) -> List[Dict]:
    """
    Get all future appointments for a user.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT doctor_name, appointment_date, appointment_time, location, notes
        FROM appointments
        WHERE user_id = ? AND appointment_date >= DATE('now')
        ORDER BY appointment_date ASC
    ''', (user_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    appointments = []
    for row in rows:
        appointments.append({
            'doctor_name': row['doctor_name'],
            'date': row['appointment_date'],
            'time': row['appointment_time'],
            'location': row['location'],
            'notes': row['notes']
        })
    return appointments


def get_todays_appointments(user_id: int) -> List[Dict]:
    """
    Get all appointments for today.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT doctor_name, appointment_date, appointment_time, location, notes
        FROM appointments
        WHERE user_id = ? AND appointment_date = DATE('now')
        ORDER BY appointment_time ASC
    ''', (user_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    appointments = []
    for row in rows:
        appointments.append({
            'doctor_name': row['doctor_name'],
            'date': row['appointment_date'],
            'time': row['appointment_time'],
            'location': row['location'],
            'notes': row['notes']
        })
    return appointments


# ====================================================================
# PART 5: CONVERSATION FUNCTIONS
# ====================================================================

def save_conversation(user_id: int, patient_question: str, doctor_response: str, image_analyzed: bool = False):
    """
    Save each AI assistant interaction for history and analysis.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO conversation_history (user_id, patient_question, doctor_response, image_analyzed)
        VALUES (?, ?, ?, ?)
    ''', (user_id, patient_question, doctor_response, image_analyzed))
    
    conn.commit()
    conn.close()
    print("✅ Conversation saved to history")


def get_conversation_history(user_id: int, limit: int = 10) -> List[Dict]:
    """
    Get recent conversation history for a user.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT patient_question, doctor_response, created_at
        FROM conversation_history
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
    ''', (user_id, limit))
    
    rows = cursor.fetchall()
    conn.close()
    
    history = []
    for row in rows:
        history.append({
            'question': row['patient_question'],
            'response': row['doctor_response'],
            'timestamp': row['created_at']
        })
    return history


# ====================================================================
# PART 6: DAILY SUMMARY FUNCTION
# ====================================================================

def get_daily_summary(user_id: int) -> str:
    """
    Generate a complete daily summary including:
    - Today's medication schedule
    - Refill alerts
    - Today's appointments
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    today = date.today().isoformat()
    
    # Get today's medication schedule
    cursor.execute('''
        SELECT medication_name, time_of_day, taken
        FROM medication_schedule
        WHERE user_id = ? AND scheduled_date = ?
        ORDER BY time_of_day
    ''', (user_id, today))
    
    today_schedule = cursor.fetchall()
    conn.close()
    
    summary = "📋 **DAILY SUMMARY**\n\n"
    
    # Medications section
    summary += "💊 TODAY'S MEDICATIONS:\n"
    if today_schedule:
        for med in today_schedule:
            status = "✅ Taken" if med['taken'] else "⏳ Pending"
            summary += f"  • {med['medication_name']} ({med['time_of_day']}): {status}\n"
    else:
        summary += "  No medications scheduled for today.\n"
    
    # Appointments section
    summary += "\n📅 TODAY'S APPOINTMENTS:\n"
    today_appointments = get_todays_appointments(user_id)
    if today_appointments:
        for apt in today_appointments:
            summary += f"  • Dr. {apt['doctor_name']} at {apt['time']} - {apt['location']}\n"
    else:
        summary += "  No appointments scheduled for today.\n"
    
    # Alerts section
    summary += f"\n{get_refill_alerts(user_id)}"
    
    return summary


# ====================================================================
# PART 7: METRICS & ANALYSIS FUNCTIONS
# ====================================================================

def generate_adherence_report(user_id: int) -> pd.DataFrame:
    """
    Use PANDAS to analyze medication adherence over time.
    Returns DataFrame with adherence percentage by date.
    """
    conn = get_connection()
    
    query = '''
        SELECT 
            scheduled_date,
            medication_name,
            time_of_day,
            taken
        FROM medication_schedule
        WHERE user_id = ?
        ORDER BY scheduled_date DESC
    '''
    
    df = pd.read_sql_query(query, conn, params=(user_id,))
    conn.close()
    
    if df.empty:
        return pd.DataFrame()
    
    # Calculate adherence by day
    adherence_by_day = df.groupby('scheduled_date')['taken'].mean() * 100
    return adherence_by_day


def log_daily_metrics(user_id: int):
    """
    Calculate and log daily metrics for a user.
    Call this at the end of each day.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    today = date.today().isoformat()
    
    # Calculate today's adherence
    cursor.execute('''
        SELECT 
            CAST(SUM(CASE WHEN taken = 1 THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) * 100 as adherence
        FROM medication_schedule
        WHERE user_id = ? AND scheduled_date = ?
    ''', (user_id, today))
    
    result = cursor.fetchone()
    adherence = result['adherence'] if result and result['adherence'] else 0
    
    # Count today's conversations
    cursor.execute('''
        SELECT COUNT(*) as count
        FROM conversation_history
        WHERE user_id = ? AND DATE(created_at) = ?
    ''', (user_id, today))
    
    conv_count = cursor.fetchone()['count']
    
    # Save metrics
    cursor.execute('''
        INSERT INTO metrics (user_id, metric_date, medication_adherence_rate, total_conversations)
        VALUES (?, ?, ?, ?)
        ON CONFLICT DO UPDATE SET
            medication_adherence_rate = excluded.medication_adherence_rate,
            total_conversations = excluded.total_conversations
    ''', (user_id, today, adherence, conv_count))
    
    conn.commit()
    conn.close()
    print(f"✅ Metrics logged for {today}: Adherence = {adherence:.1f}%")


# ====================================================================
# PART 8: INITIALIZE DATABASE & ADD SAMPLE DATA
# ====================================================================

def add_sample_data():
    """
    Add sample data for testing the application.
    This creates a demo user and some medications.
    """
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
        
        # Medication 1: Aspirin (On track)
        cursor.execute('''
            INSERT OR IGNORE INTO medications (user_id, name, pill_count, daily_dosage, refill_date)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, "aspirin", 30, 2, "2026-06-15"))
        
        # Medication 2: Metformin (Low stock)
        cursor.execute('''
            INSERT OR IGNORE INTO medications (user_id, name, pill_count, daily_dosage, refill_date)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, "metformin", 3, 1, "2026-05-25"))
        
        # Medication 3: Paracetamol (Overdue - for testing)
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
    """
    Display all medications in a nice formatted table.
    Useful for debugging and verification.
    """
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


# ====================================================================
# PART 9: DATABASE MAINTENANCE FUNCTIONS
# ====================================================================

def clean_duplicate_medications():
    """
    Clean up any duplicate medications that might exist from old schema.
    Keeps the entry with the highest pill_count (most recent).
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Find duplicates
    cursor.execute('''
        SELECT user_id, name, COUNT(*) as count, MAX(pill_count) as max_pills
        FROM medications
        GROUP BY user_id, name
        HAVING COUNT(*) > 1
    ''')
    
    duplicates = cursor.fetchall()
    
    if not duplicates:
        print("✅ No duplicate medications found.")
        conn.close()
        return
    
    for dup in duplicates:
        user_id = dup['user_id']
        name = dup['name']
        
        # Keep only the entry with highest pill count
        cursor.execute('''
            DELETE FROM medications
            WHERE user_id = ? AND name = ? 
            AND pill_count < (SELECT MAX(pill_count) FROM medications m2 WHERE m2.user_id = ? AND m2.name = ?)
        ''', (user_id, name, user_id, name))
        
        print(f"🔄 Cleaned duplicates for {name}")
    
    conn.commit()
    conn.close()
    print("✅ Duplicate cleanup complete!")


def backup_database():
    """
    Create a backup of the database file.
    """
    import shutil
    from datetime import datetime
    
    if DB_PATH.exists():
        backup_name = DB_DIR / f"elderly_care_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        shutil.copy(DB_PATH, backup_name)
        print(f"✅ Database backed up to: {backup_name}")
    else:
        print("⚠️ No database file found to backup.")


# ====================================================================
# PART 10: MAIN EXECUTION (For Testing)
# ====================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("🔧 ELDERLY CARE DATABASE SETUP")
    print("=" * 70)
    
    # Create all tables
    create_tables()
    
    # Add sample data
    add_sample_data()
    
    # Clean any potential duplicates
    clean_duplicate_medications()
    
    # Display all medications
    display_all_medications()
    
    # Show refill alerts
    print("\n" + "=" * 70)
    print("REFILL ALERTS")
    print("=" * 70)
    print(get_refill_alerts(1))
    
    # Show detailed status report
    print("\n" + get_medication_status_report(1))
    
    # Show daily summary
    print("\n" + get_daily_summary(1))
    
    print(f"\n📁 Database saved at: {DB_PATH}")
    print("=" * 70)