from frappe.utils import add_days, nowdate

def on_submit(doc, method):
    schedule = doc.schedule_type
    start = doc.start_date or nowdate()
    interval = int(doc.interval_days or 1)
    
    for i in range(7):
        if schedule == 'Daily':
            task_date = add_days(start, i)
        elif schedule == 'Weekly' and i % 7 == 0:
            task_date = add_days(start, i)
        elif schedule == 'Every X Days' and i % interval == 0:
            task_date = add_days(start, i)
        else:
            continue
        
        doc.append('service_tasks', {
            'task_title': f'Auto Task for {task_date}',
            'due_date': task_date,
            'assigned_role': 'Engineer',
            'status': 'Pending'
        })
