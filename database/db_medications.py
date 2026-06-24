# ====================================================================
# DB_MEDICATIONS.PY - Medication CRUD Operations
# ====================================================================
# Responsible for:
# 1. Adding medications (with duplicate prevention)
# 2. Getting medication lists
# 3. Updating pill counts
# 4. Recording when medication is taken
# 5. Deleting medications
# ====================================================================

import sqlite3
from datetime import date
from typing import List, Dict
from .db_connection import get_connection


# In db_medications.py, update the add_medication function:

def add_medication(user_id: int, name: str, pill_count: int, daily_dosage: int, refill_date=None):
    """
    Add a new medication to the database.
    If medication already exists for this user, update it instead.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Convert name to lowercase for consistent comparison
    name = name.lower().strip()
    
    # Convert refill_date to string if it's a number
    if refill_date is not None:
        if isinstance(refill_date, (int, float)):
            from datetime import datetime
            refill_date = datetime.fromtimestamp(refill_date).strftime('%Y-%m-%d')
        elif hasattr(refill_date, 'strftime'):
            refill_date = refill_date.strftime('%Y-%m-%d')
    
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
    
    Args:
        user_id: ID of the user
    
    Returns:
        List of dictionaries with medication details
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
    
    Args:
        user_id: ID of the user
        name: Name of the medication
        new_count: New pill count
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
    
    Args:
        user_id: ID of the user
        name: Name of the medication
        time_of_day: When it was taken (Morning/Evening)
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
    
    Args:
        user_id: ID of the user
        name: Name of the medication to delete
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