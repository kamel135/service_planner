frappe.call('service_planner.api.task_api.get_todays_tasks')
  .then(r => {
    const tasks = r.message;
    const container = document.getElementById('tasks-container');
    container.innerHTML = '';

    if (!tasks.length) {
      container.innerHTML = '✅ No tasks for today!';
      return;
    }

    tasks.forEach(task => {
      const color = {
        "Pending": "orange",
        "In Progress": "blue",
        "Completed": "green",
        "Cancelled": "red"
      }[task.status] || "gray";

      const div = document.createElement('div');
      div.style.border = `2px solid ${color}`;
      div.style.padding = "10px";
      div.style.margin = "10px";
      div.style.borderRadius = "10px";

      div.innerHTML = `
        <strong>${task.task_title}</strong> <span style="color:${color}">(${task.status})</span><br>
        Due: ${task.due_date}<br>
        <button onclick="markCompleted('${task.name}')">✅ Mark as Completed</button>
      `;

      container.appendChild(div);
    });
  });

function markCompleted(name) {
  frappe.call({
    method: 'frappe.client.set_value',
    args: {
      doctype: 'Service Task',
      name: name,
      fieldname: {
        'status': 'Completed'
      }
    },
    callback: () => {
      frappe.msgprint("🎉 Task marked as completed");
      location.reload();
    }
  });
}
