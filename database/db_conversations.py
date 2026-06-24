# ====================================================================
# DB_CONVERSATIONS.PY - Conversation History Operations
# ====================================================================
# Responsible for:
# 1. Saving conversation history
# 2. Retrieving conversation history
# ====================================================================

from typing import List, Dict
from .db_connection import get_connection


def save_conversation(user_id: int, patient_question: str, doctor_response: str, image_analyzed: bool = False):
    """
    Save each AI assistant interaction for history and analysis.
    
    Args:
        user_id: ID of the user
        patient_question: What the patient said/asked
        doctor_response: What the AI doctor responded
        image_analyzed: Whether an image was analyzed
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
    
    Args:
        user_id: ID of the user
        limit: Maximum number of conversations to retrieve
    
    Returns:
        List of dictionaries with conversation history
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