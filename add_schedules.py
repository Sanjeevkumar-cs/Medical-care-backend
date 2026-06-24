# add_schedules.py
from database import get_connection
from datetime import date

def add_medication_schedules():
    """Add schedules for existing medications"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get all medications for user 1
    cursor.execute("SELECT id, name FROM medications WHERE user_id = 1")
    medications = cursor.fetchall()
    
    today = date.today().isoformat()
    
    schedules_added = 0
    
    for med in medications:
        med_id = med['id']
        med_name = med['name']
        
        # Add morning and evening schedules for each medication
        for time in ["Morning", "Evening"]:
            # Check if schedule already exists for today
            cursor.execute('''
                SELECT COUNT(*) FROM medication_schedule 
                WHERE medication_id = ? AND scheduled_date = ? AND time_of_day = ?
            ''', (med_id, today, time))
            
            count = cursor.fetchone()[0]
            
            if count == 0:
                cursor.execute('''
                    INSERT INTO medication_schedule (medication_id, time_of_day, scheduled_date, taken)
                    VALUES (?, ?, ?, ?)
                ''', (med_id, time, today, 0))
                schedules_added += 1
                print(f"   ✅ Added schedule: {med_name} at {time}")
    
    conn.commit()
    conn.close()
    print(f"\n📋 Added {schedules_added} medication schedules for today!")

if __name__ == "__main__":
    print("\n🔧 Adding medication schedules...")
    add_medication_schedules()
    
    # Test the daily summary again
    from database import get_daily_summary
    print("\n📋 Updated Daily Summary:")
    print("="*40)
    print(get_daily_summary(1))