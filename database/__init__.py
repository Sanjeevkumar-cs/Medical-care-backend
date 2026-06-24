# ====================================================================
# DATABASE PACKAGE INITIALIZATION
# ====================================================================
# This file makes the 'database' folder a Python package
# It exports all the main functions for easy importing
# ====================================================================

from .db_connection import get_connection, DB_PATH
from .db_setup import create_tables, add_sample_data, display_all_medications
from .db_medications import (
    add_medication,
    get_all_medications,
    update_pill_count,
    delete_medication,
    record_medication_taken
)
from .db_appointments import (
    add_appointment,
    get_upcoming_appointments,
    get_todays_appointments
)
from .db_conversations import (
    save_conversation,
    get_conversation_history
)
from .db_alerts import (
    get_low_stock_medications,
    get_refill_alerts,
    get_medication_status_report,
    get_daily_summary
)

__all__ = [
    # Connection
    'get_connection',
    'DB_PATH',
    
    # Setup
    'create_tables',
    'add_sample_data',
    'display_all_medications',
    
    # Medications
    'add_medication',
    'get_all_medications',
    'update_pill_count',
    'delete_medication',
    'record_medication_taken',
    
    # Appointments
    'add_appointment',
    'get_upcoming_appointments',
    'get_todays_appointments',
    
    # Conversations
    'save_conversation',
    'get_conversation_history',
    
    # Alerts
    'get_low_stock_medications',
    'get_refill_alerts',
    'get_medication_status_report',
    'get_daily_summary',
]