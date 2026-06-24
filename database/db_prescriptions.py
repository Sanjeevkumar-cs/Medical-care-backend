# ====================================================================
# DB_PRESCRIPTIONS.PY - Prescription Database Operations
# ====================================================================
# Responsible for:
# 1. Saving uploaded prescription data
# 2. Retrieving user prescriptions
# 3. Getting prescription details
# ====================================================================

import json
from typing import List, Dict
from .db_connection import get_connection

def save_prescription(user_id: int, image_path: str, extracted_text: str,
                      medicines: List[Dict], instructions: List[str]) -> int:
    """
    Save a processed prescription and its extracted medicines to the database.
    
    Args:
        user_id: ID of the user
        image_path: Path where the prescription image is stored
        extracted_text: Full OCR extracted text
        medicines: List of detected medicines (each with name, dosage)
        instructions: List of extracted instructions
    
    Returns:
        prescription_id: Auto-generated primary key
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Insert the prescription record
    cursor.execute('''
        INSERT INTO prescriptions (user_id, image_path, extracted_text, medicines, instructions, status)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        user_id,
        image_path,
        extracted_text[:2000] if extracted_text else '',
        json.dumps(medicines),
        json.dumps(instructions),
        'processed'
    ))
    
    prescription_id = cursor.lastrowid
    
    # Insert each medicine into the prescription_medicines table
    for med in medicines:
        cursor.execute('''
            INSERT INTO prescription_medicines (prescription_id, medicine_name, dosage, is_confirmed)
            VALUES (?, ?, ?, ?)
        ''', (prescription_id, med.get('name', ''), med.get('dosage', ''), 0))
    
    conn.commit()
    conn.close()
    return prescription_id

def get_user_prescriptions(user_id: int) -> List[Dict]:
    """
    Retrieve all prescriptions for a specific user, ordered by most recent first.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, image_path, extracted_text, upload_date, status
        FROM prescriptions
        WHERE user_id = ?
        ORDER BY upload_date DESC
    ''', (user_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    prescriptions = []
    for row in rows:
        prescriptions.append({
            'id': row['id'],
            'image_path': row['image_path'],
            'extracted_text': row['extracted_text'][:150] if row['extracted_text'] else '',
            'upload_date': row['upload_date'],
            'status': row['status']
        })
    return prescriptions

def get_prescription_details(prescription_id: int) -> Dict:
    """
    Get full details of a specific prescription, including its medicines.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM prescriptions WHERE id = ?', (prescription_id,))
    prescription = cursor.fetchone()
    
    if not prescription:
        conn.close()
        return {}
    
    cursor.execute('SELECT * FROM prescription_medicines WHERE prescription_id = ?', (prescription_id,))
    medicines = cursor.fetchall()
    
    conn.close()
    
    return {
        'id': prescription['id'],
        'image_path': prescription['image_path'],
        'extracted_text': prescription['extracted_text'],
        'medicines': [dict(m) for m in medicines],
        'upload_date': prescription['upload_date'],
        'status': prescription['status']
    }
# database/db_prescriptions.py - Add this function

def delete_prescription_from_db(prescription_id: int):
    """
    Delete a prescription from the database by ID.
    This will cascade delete associated prescription_medicines due to foreign key constraints.
    
    Args:
        prescription_id: ID of the prescription to delete
    
    Returns:
        bool: True if deletion was successful
    
    Raises:
        Exception: If deletion fails
    """
    from database.db_connection import get_connection
    
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