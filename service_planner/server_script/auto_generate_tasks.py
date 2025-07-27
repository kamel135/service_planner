import frappe
import calendar
import pytz
from datetime import datetime, time, timedelta
from frappe.utils import add_days, getdate, get_time, nowdate, format_datetime, get_datetime_str
from functools import lru_cache
from frappe import _

class TimezoneManager:
    """Class to handle all timezone-related operations"""
    
    def __init__(self):
        self.system_timezone = frappe.db.get_single_value("System Settings", "time_zone") or "UTC"
    
    @lru_cache(maxsize=128)
    def get_user_timezone(self, user):
        """Get user timezone with caching"""
        try:
            return frappe.db.get_value("User", user, "time_zone") or self.system_timezone
        except Exception:
            return self.system_timezone
    
    def is_dst_active(self, timezone_str, dt=None):
        """Check if daylight saving is active for timezone"""
        try:
            tz = pytz.timezone(timezone_str)
            dt = dt or datetime.now(tz)
            return bool(tz.dst(dt))
        except Exception:
            return False
    
    def get_timezone_offset(self, timezone_str, dt=None):
        """Get current UTC offset for timezone"""
        try:
            tz = pytz.timezone(timezone_str)
            dt = dt or datetime.now(tz)
            return dt.strftime("%z")
        except Exception:
            return "+0000"
    
    def convert_datetime(self, dt, from_tz_str, to_tz_str):
        """Convert datetime between two timezones."""
        try:
            from_tz = pytz.timezone(from_tz_str)
            to_tz = pytz.timezone(to_tz_str)
            
            # Make the datetime "aware" of its source timezone
            if not dt.tzinfo:
                dt = from_tz.localize(dt)
            
            # Convert to the target timezone
            return dt.astimezone(to_tz)
        except Exception as e:
            frappe.log_error(f"Timezone conversion error: {str(e)}", "Timezone Conversion")
            return dt

tz_manager = TimezoneManager()

def execute(doc, method):
    """Main hook function triggered on document save."""
    validate_schedule_configuration(doc, method)
    
    # Check if we need to regenerate tasks or just update task titles
    if should_regenerate_tasks(doc):
        generate_service_tasks(doc)
    elif should_update_task_titles(doc):
        update_task_titles(doc)
    
    validate_timezone_settings(doc)

def should_regenerate_tasks(doc):
    """Determine if tasks need to be regenerated based on changes to critical fields."""
    if doc.is_new():
        return True

    old_doc = doc.get_doc_before_save()
    if not old_doc:
        return False

    critical_fields = [
        'schedule_type', 'start_date', 'end_date', 'weekly_days',
        'interval_days', 'task_time', 'default_role', 'duration_hours'
    ]

    return any(getattr(doc, field) != getattr(old_doc, field) 
              for field in critical_fields 
              if hasattr(doc, field) and hasattr(old_doc, field))

def should_update_task_titles(doc):
    """Check if only task titles need to be updated (when task_template changes)."""
    if doc.is_new():
        return False

    old_doc = doc.get_doc_before_save()
    if not old_doc:
        return False

    # Check if task_template or project_name changed
    template_changed = getattr(doc, 'task_template', '') != getattr(old_doc, 'task_template', '')
    name_changed = getattr(doc, 'project_name', '') != getattr(old_doc, 'project_name', '')
    
    return template_changed or name_changed

def update_task_titles(doc):
    """Update task titles for existing tasks when template changes."""
    try:
        updated_count = 0
        
        for task in doc.service_tasks:
            if not task or not task.auto_generated:
                continue  # Skip manually created tasks
            
            # Get the task date from due_date
            task_date = getdate(task.due_date)
            
            # Generate new title using current template
            new_title = generate_task_title(doc, task_date)
            
            # Update only if title actually changed
            if task.task_title != new_title:
                task.task_title = new_title
                updated_count += 1
        
        if updated_count > 0:
            frappe.msgprint(
                _("Updated {0} task titles based on new template").format(updated_count),
                indicator="green"
            )
    
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Task Title Update Error")
        frappe.throw(_("Error updating task titles. Please check system logs for details."))

def get_task_dates(doc, start_date, end_date):
    """Calculate all dates on which tasks should be created based on the schedule."""
    dates = []
    current_date = getdate(start_date)
    end_date = getdate(end_date) if doc.end_date else None
    max_days = 365 * 2  # Safety limit to prevent infinite loops

    while (not end_date or current_date <= end_date) and len(dates) < max_days:
        if doc.schedule_type == "Daily":
            dates.append(current_date)
            current_date = add_days(current_date, 1)

        elif doc.schedule_type == "Weekly" and hasattr(doc, 'weekly_days'):
            if is_selected_weekday(doc, current_date):
                dates.append(current_date)
            current_date = add_days(current_date, 1)

        elif doc.schedule_type == "Every X Days":
            dates.append(current_date)
            interval = max(1, int(doc.interval_days or 1))
            current_date = add_days(current_date, interval)

        else:
            current_date = add_days(current_date, 1)

    return dates

def is_selected_weekday(doc, date_obj):
    """Check if the day of the week for a given date is in the selected weekdays."""
    if not hasattr(doc, 'weekly_days') or not doc.weekly_days:
        return False
    
    weekday = calendar.day_name[date_obj.weekday()]
    return any(d.day == weekday for d in doc.weekly_days)

def generate_task_title(doc, task_date):
    """Generate a title for the task using template if available."""
    try:
        if getattr(doc, 'task_template', None):
            # Use the task template with dynamic replacements
            title = doc.task_template.format(
                date=format_datetime(task_date, "dd-MM-yyyy"),
                project=doc.project_name or "",
                organization=doc.organization or ""
            )
            return title[:140]  # Ensure title length is within limits
    except Exception:
        # If template formatting fails, fall back to default
        pass
    
    # Default title format
    default_title = f"{doc.project_name or 'Task'} - {format_datetime(task_date, 'dd-MM-yyyy')}"
    return default_title[:140]

def parse_task_time(time_str) -> time:
    """Parse a time string into a time object with robust validation."""
    default_time = time(9, 0, 0) # 09:00:00
    
    if not time_str:
        return default_time
        
    try:
        if isinstance(time_str, time):
            return time_str
        if isinstance(time_str, datetime):
            return time_str.time()
        if isinstance(time_str, str):
            # Handle formats like "14:30:00" or "14:30"
            parts = time_str.split(':')
            hour, minute = int(parts[0]), int(parts[1])
            second = int(parts[2].split('.')[0]) if len(parts) > 2 else 0
            return time(hour, minute, second)
    except (ValueError, TypeError, IndexError):
        frappe.log_error(f"Could not parse time: '{time_str}'. Using default.", "Time Parsing Error")
        return default_time
    
    return default_time

def has_manual_modifications(task):
    """Check if a task has been manually modified by the user."""
    # A task is considered manually modified if:
    # 1. It has an assigned_to user (manual assignment)
    # 2. Its status is not 'Pending' (user changed status)
    # 3. It has custom notes beyond the auto-generated ones
    # 4. It's not marked as auto_generated
    
    if not task.auto_generated:
        return True
    
    if task.assigned_to:
        return True
    
    if task.status and task.status != 'Pending':
        return True
    
    # Check if notes contain more than just the auto-generated content
    auto_notes = generate_task_notes_for_comparison(task)
    if task.notes and task.notes.strip() != auto_notes.strip():
        return True
    
    return False

def generate_task_notes_for_comparison(task):
    """Generate the expected auto-generated notes for comparison."""
    # This should match the format used in generate_task_notes
    notes = [
        f"Project: {task.get('project_name') or 'N/A'}", 
        f"Schedule: {task.get('schedule_type') or 'N/A'}"
    ]
    return "\n".join(notes)

def generate_service_tasks(doc):
    """
    The main function to generate tasks with correct UTC and local time handling.
    It preserves manually modified tasks while updating auto-generated ones.
    """
    try:
        # Step 1: Preserve ALL existing tasks that have been manually modified
        # This includes completed, in-progress, and pending tasks with manual changes
        preserved_tasks = {}
        manually_modified_tasks = []
        
        for task in doc.service_tasks:
            if not task:
                continue
                
            task_date_str = getdate(task.due_date).strftime('%Y-%m-%d')
            
            # Always preserve completed and in-progress tasks
            if task.status in ['Completed', 'In Progress']:
                preserved_tasks[task_date_str] = task
                manually_modified_tasks.append(task)
            # Also preserve pending tasks that have been manually modified
            elif has_manual_modifications(task):
                preserved_tasks[task_date_str] = task
                manually_modified_tasks.append(task)

        # Step 2: Clear the existing task list in the document. We will rebuild it.
        doc.service_tasks = []

        # Step 3: Get the schedule parameters from the parent document.
        start_date = getdate(doc.start_date)
        end_date = getdate(doc.end_date) if doc.end_date else None
        task_dates = get_task_dates(doc, start_date, end_date)
        task_time = parse_task_time(doc.task_time)
        
        # Step 4: Determine the timezone of the user creating or editing the project.
        creator_user = doc.owner or frappe.session.user
        creator_tz_str = tz_manager.get_user_timezone(creator_user)
        creator_tz = pytz.timezone(creator_tz_str)

        # Step 5: Loop through each calculated date to create or re-add tasks.
        for task_date in task_dates:
            task_date_str = task_date.strftime('%Y-%m-%d')
            
            # If a task for this day already exists and has been preserved, re-add it
            if task_date_str in preserved_tasks:
                doc.append('service_tasks', preserved_tasks[task_date_str])
                continue

            # --- Core Timezone Logic for New Tasks ---

            # 5a. Create a "naive" datetime object (without timezone info) from the date and time.
            naive_dt = datetime.combine(task_date, task_time)
            
            # 5b. Make this datetime "aware" by localizing it to the creator's timezone.
            # pytz will automatically handle DST if applicable!
            creator_aware_dt = creator_tz.localize(naive_dt)

            # 5c. Convert this local reference time to UTC for storage.
            utc_dt = creator_aware_dt.astimezone(pytz.utc)

            # 5d. The `local_due_date` will be the creator's aware time.
            local_dt = creator_aware_dt

            # 5e. Remove timezone info for database storage
            due_date_for_db = utc_dt.replace(tzinfo=None)
            local_due_date_for_db = local_dt.replace(tzinfo=None)

            # 5f. Prepare the dictionary with all data for the new task.
            task_data = {
                'task_title': generate_task_title(doc, task_date),
                'due_date': due_date_for_db,  # UTC time
                'due_date_utc': due_date_for_db,  # Same value for consistency
                'local_due_date': local_due_date_for_db,
                'assigned_role': doc.default_role,
                'status': 'Pending',
                'organization': doc.organization,
                'notes': generate_task_notes(doc),
                'duration_hours': doc.duration_hours or 1.0,
                'user_timezone': creator_tz_str,
                'auto_generated': 1,  # Mark as auto-generated
                # Important: Add flag to indicate due_date is already UTC
                'flags': {'due_date_is_utc': True}
            }
            
            # 5g. Append the new task to the document's child table.
            doc.append('service_tasks', task_data)

        # Step 6: Sort the final list of tasks by their due date.
        doc.service_tasks.sort(key=lambda x: x.due_date)
        
        # Step 7: Inform the user about the operation results.
        total_tasks = len(doc.service_tasks)
        preserved_count = len(manually_modified_tasks)
        new_count = total_tasks - preserved_count
        
        if preserved_count > 0:
            frappe.msgprint(
                _("Successfully updated tasks: {0} new, {1} preserved (manually modified)").format(
                    new_count, preserved_count
                ), 
                indicator="green"
            )
        else:
            frappe.msgprint(_("Successfully updated {0} tasks").format(total_tasks), indicator="green")

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Task Generation Error")
        frappe.throw(_("Error during task generation. Please check system logs for details."))


def generate_task_notes(doc):
    """Generate standardized notes for a task."""
    notes = [
        _("Project: {0}").format(doc.project_name or _("Not specified")),
        _("Schedule Type: {0}").format(doc.schedule_type),
        _("Duration: {0} hours").format(doc.duration_hours or 1)
    ]
    
    if doc.schedule_type == "Weekly":
        notes.append(_("Selected Days: {0}").format(", ".join(d.day for d in doc.weekly_days)))
    elif doc.schedule_type == "Every X Days":
        notes.append(_("Interval: Every {0} days").format(doc.interval_days))
    
    return "\n".join(notes)

def validate_timezone_settings(doc):
    """Warn if an assigned user doesn't have a timezone set."""
    for task in doc.service_tasks:
        if task.assigned_to:
            user_tz = tz_manager.get_user_timezone(task.assigned_to)
            if user_tz == tz_manager.system_timezone:
                frappe.msgprint(
                    _("User {0} is using the system default timezone ({1}).").format(task.assigned_to, user_tz),
                    indicator="orange",
                    alert=True
                )

@frappe.whitelist()
def get_timezone_info(task):
    """Get detailed timezone information for task"""
    doc = frappe.get_doc("Service Task", task)
    user_tz = tz_manager.get_user_timezone(doc.assigned_to or frappe.session.user)
    
    return {
        "local_time": format_datetime(doc.local_due_date),
        "utc_time": format_datetime(doc.due_date),
        "user_timezone": user_tz,
        "dst_active": tz_manager.is_dst_active(user_tz),
        "timezone_offset": tz_manager.get_timezone_offset(user_tz),
        "system_timezone": tz_manager.system_timezone
    }

@frappe.whitelist()
def regenerate_tasks(project_name):
    """API endpoint for manual task regeneration"""
    try:
        doc = frappe.get_doc("Service Project", project_name)
        if not frappe.has_permission("Service Project", "write", doc):
            frappe.throw(_("You don't have permission to modify this project"))

        generate_service_tasks(doc)
        doc.save()

        return {
            "success": True,
            "message": _("Tasks regenerated successfully"),
            "task_count": len(doc.service_tasks)
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e),
            "error": frappe.get_traceback()
        }

@frappe.whitelist()
def preview_next_tasks(project_name, days=7):
    """Preview upcoming tasks for the next X days"""
    try:
        doc = frappe.get_doc("Service Project", project_name)
        start_date = getdate(nowdate())
        end_date = add_days(start_date, int(days))

        task_dates = get_task_dates(doc, start_date, end_date)

        return {
            "success": True,
            "dates": [format_datetime(d, "yyyy-MM-dd") for d in task_dates],
            "count": len(task_dates)
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }

def validate_schedule_configuration(doc, method):
    """Validate schedule settings before saving"""
    errors = []
    
    if not doc.start_date:
        errors.append(_("Start Date is required"))
    
    if doc.end_date and getdate(doc.end_date) < getdate(doc.start_date):
        errors.append(_("End Date cannot be before Start Date"))
    
    if doc.schedule_type == "Every X Days":
        try:
            if int(doc.interval_days or 0) <= 0:
                errors.append(_("Interval Days must be a positive number"))
        except ValueError:
            errors.append(_("Invalid Interval Days value"))
    
    if doc.schedule_type == "Weekly" and not doc.weekly_days:
        errors.append(_("At least one weekday must be selected for weekly schedule"))
    
    if errors:
        frappe.throw("<br>".join(errors))

def on_task_completion(doc, method):
    """Actions when task is completed"""
    if doc.status == "Completed" and not doc.completion_notes:
        doc.completion_notes = _("Completed on {0} by {1}").format(
            format_datetime(nowdate(), "yyyy-MM-dd"),
            frappe.session.user
        )
