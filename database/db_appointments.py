# ====================================================================
# DB_APPOINTMENTS.PY - Appointment Operations
# ====================================================================
# Responsible for:
# 1. Adding new appointments
# 2. Getting upcoming appointments
# 3. Getting today's appointments
# ====================================================================

from typing import List, Dict
from .db_connection import get_connection


def add_appointment(user_id: int, doctor_name: str, appointment_date: str, 
                    appointment_time: str, location: str = "", notes: str = ""):
    """
    Schedule a new doctor appointment.
    
    Args:
        user_id: ID of the user
        doctor_name: Name of the doctor
        appointment_date: Date of appointment (YYYY-MM-DD)
        appointment_time: Time of appointment (HH:MM)
        location: Clinic/Hospital address (optional)
        notes: Additional notes (optional)
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
    
    Args:
        user_id: ID of the user
    
    Returns:
        List of dictionaries with appointment details
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
    
    Args:
        user_id: ID of the user
    
    Returns:
        List of dictionaries with today's appointments
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