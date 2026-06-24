# ====================================================================
# DB_ALERTS.PY - Smart Medication Alerts and Reporting
# ====================================================================
# Responsible for:
# 1. Detecting low stock and overdue medications
# 2. Predicting if stock will last until refill date
# 3. Generating alert messages
# 4. Creating detailed status reports
# 5. Daily summary generation
# ====================================================================

from datetime import datetime, date
from typing import List, Dict
from .db_connection import get_connection
from .db_appointments import get_todays_appointments


def parse_date(date_value):
    """
    Safely parse date from any format (string, integer, None) to date object.
    
    Args:
        date_value: Can be string (YYYY-MM-DD), integer (timestamp), or None
    
    Returns:
        date object or None if parsing fails
    """
    if date_value is None:
        return None
    
    # If it's already a date object
    if isinstance(date_value, date):
        return date_value
    
    # If it's a string
    if isinstance(date_value, str):
        try:
            return datetime.strptime(date_value, '%Y-%m-%d').date()
        except ValueError:
            try:
                # Try parsing with time
                return datetime.strptime(date_value, '%Y-%m-%d %H:%M:%S').date()
            except ValueError:
                return None
    
    # If it's an integer (Unix timestamp)
    if isinstance(date_value, (int, float)):
        try:
            return datetime.fromtimestamp(date_value).date()
        except (ValueError, OSError):
            return None
    
    # Try converting to string as last resort
    try:
        return datetime.strptime(str(date_value)[:10], '%Y-%m-%d').date()
    except ValueError:
        return None


def get_low_stock_medications(user_id: int, threshold: int = 5) -> List[Dict]:
    """
    Find medications that need attention because:
    1. Refill date has passed (OVERDUE)
    2. Low pill count (less than threshold)
    3. Will run out before refill date (PREDICTIVE)
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
        refill_date_value = row['refill_date']
        pill_count = row['pill_count']
        daily_dosage = row['daily_dosage'] if row['daily_dosage'] > 0 else 1
        name = row['name']
        
        # Initialize flags
        refill_overdue = False
        days_overdue = 0
        low_stock = False
        will_run_out = False
        days_until_refill = 0
        
        # Parse the refill date (handles string, int, or None)
        refill_date_obj = parse_date(refill_date_value)
        
        # CASE 1: Check if refill date has passed (OVERDUE)
        if refill_date_obj:
            if today > refill_date_obj:
                refill_overdue = True
                days_overdue = (today - refill_date_obj).days
        
        # CASE 2: Check low pill count
        low_stock = pill_count < threshold
        
        # CASE 3: Check if stock will last until refill date (PREDICTIVE)
        if refill_date_obj and not refill_overdue:
            days_until_refill = (refill_date_obj - today).days
            if days_until_refill > 0:
                required_pills = daily_dosage * days_until_refill
                if pill_count < required_pills:
                    will_run_out = True
        
        # Add to attention list if any condition is true
        if low_stock or refill_overdue or will_run_out:
            days_remaining = pill_count // daily_dosage if daily_dosage > 0 else 0
            needs_attention.append({
                'name': name,
                'pill_count': pill_count,
                'daily_dosage': daily_dosage,
                'refill_date': str(refill_date_obj) if refill_date_obj else None,
                'days_remaining': days_remaining,
                'refill_overdue': refill_overdue,
                'days_overdue': days_overdue if refill_overdue else 0,
                'will_run_out': will_run_out,
                'days_until_refill': days_until_refill if not refill_overdue else 0
            })
    
    return needs_attention


def get_refill_alerts(user_id: int) -> str:
    """Generate a human-readable alert message about medications needing refill."""
    meds_needing_attention = get_low_stock_medications(user_id, threshold=7)
    
    if not meds_needing_attention:
        return "✅ All medications have sufficient stock."
    
    alerts = []
    
    # Separate overdue and low stock
    overdue_items = []
    low_stock_items = []
    
    for med in meds_needing_attention:
        if med['refill_overdue']:
            overdue_items.append({
                'name': med['name'],
                'days': med['days_overdue'],
                'pills': med['pill_count']
            })
        else:
            low_stock_items.append({
                'name': med['name'],
                'pills': med['pill_count'],
                'days_left': med['days_remaining']
            })
    
    # Build overdue alerts
    if overdue_items:
        alerts.append("🔴 OVERDUE REFILLS")
        for med in overdue_items:
            alerts.append(f"  • {med['name']}: REFILL OVERDUE by {med['days']} days! Only {med['pills']} pills left.")
    
    # Build low stock alerts
    if low_stock_items:
        if overdue_items:
            alerts.append("")
        alerts.append("🟠 LOW STOCK WARNING")
        for med in low_stock_items:
            alerts.append(f"  • {med['name']}: Only {med['pills']} pills left ({med['days_left']} days remaining).")
    
    return "\n".join(alerts)

def get_medication_status_report(user_id: int) -> str:
    """
    Generate a detailed report showing status of ALL medications.
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
    
    # Track counts for summary
    total_medications = 0
    overdue_count = 0
    low_stock_count = 0
    on_track_count = 0
    
    for row in rows:
        total_medications += 1
        name = row['name']
        pill_count = row['pill_count']
        daily_dosage = row['daily_dosage'] if row['daily_dosage'] > 0 else 1
        refill_date_value = row['refill_date']
        
        days_remaining_stock = pill_count // daily_dosage
        
        # Parse the refill date
        refill_date_obj = parse_date(refill_date_value)
        
        if refill_date_obj:
            if today > refill_date_obj:
                days_overdue = (today - refill_date_obj).days
                status = f"🔴 OVERDUE by {days_overdue} days"
                overdue_count += 1
            else:
                days_until_refill = (refill_date_obj - today).days
                required_pills = daily_dosage * days_until_refill
                
                if pill_count >= required_pills:
                    status = f"✅ On track - Enough until {refill_date_obj}"
                    on_track_count += 1
                else:
                    shortage = required_pills - pill_count
                    status = f"⚠️ Will run out - Need {shortage} more pills"
                    low_stock_count += 1
        else:
            # No refill date set
            if days_remaining_stock <= 7:
                status = f"🟠 Low stock - {days_remaining_stock} days remaining"
                low_stock_count += 1
            else:
                status = f"ℹ️ No refill date set - {days_remaining_stock} days remaining"
                on_track_count += 1
        
        report += f"💊 **{name.upper()}**\n"
        report += f"   • Pills left: {pill_count}\n"
        report += f"   • Daily dosage: {daily_dosage} pill(s)/day\n"
        report += f"   • Days of stock left: {days_remaining_stock} days\n"
        report += f"   • Status: {status}\n\n"
    
    # Add summary
    report += "─" * 40 + "\n"
    report += f"📈 SUMMARY: {total_medications} medications | "
    report += f"✅ {on_track_count} on track | "
    report += f"🟠 {low_stock_count} low stock | "
    report += f"🔴 {overdue_count} overdue\n"
    
    return report


def get_daily_summary(user_id: int) -> str:
    """
    Generate a complete daily summary including medications, alerts, and appointments.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    today = date.today().isoformat()
    today_date = date.today().strftime("%A, %B %d, %Y")
    
    # Get today's medication schedule
    cursor.execute('''
        SELECT medication_name, time_of_day, taken
        FROM medication_schedule
        WHERE user_id = ? AND scheduled_date = ?
        ORDER BY time_of_day
    ''', (user_id, today))
    
    today_schedule = cursor.fetchall()
    conn.close()
    
    # Header
    summary = f"📋 **DAILY SUMMARY**\n"
    summary += f"📅 {today_date}\n\n"
    
    # Medications section
    summary += "💊 **TODAY'S MEDICATIONS**\n"
    if today_schedule:
        for med in today_schedule:
            status = "✅ Taken" if med['taken'] else "⏳ Pending"
            summary += f"   • {med['medication_name'].upper()} ({med['time_of_day']}): {status}\n"
    else:
        summary += "   No medications scheduled for today.\n"
    
    # Appointments section
    summary += "\n📅 **TODAY'S APPOINTMENTS**\n"
    today_appointments = get_todays_appointments(user_id)
    if today_appointments:
        for apt in today_appointments:
            summary += f"   • Dr. {apt['doctor_name']} at {apt['time']}"
            if apt['location']:
                summary += f" - {apt['location']}"
            summary += "\n"
    else:
        summary += "   No appointments scheduled for today.\n"
    
    # Alerts section
    summary += f"\n{get_refill_alerts(user_id)}"
    
    return summary


def get_overdue_medications(user_id: int) -> List[Dict]:
    """
    Get only overdue medications (refill date passed).
    """
    meds = get_low_stock_medications(user_id)
    return [med for med in meds if med['refill_overdue']]


def get_low_stock_only(user_id: int, threshold: int = 7) -> List[Dict]:
    """
    Get only low stock medications (not overdue).
    """
    meds = get_low_stock_medications(user_id, threshold)
    return [med for med in meds if not med['refill_overdue'] and not med['will_run_out']]