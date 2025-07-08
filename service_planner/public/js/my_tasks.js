async function loadTasks() {
  const status = document.getElementById("status-filter").value;
  const due = document.getElementById("due-filter").value;
  const table = document.querySelector("#tasks-table tbody");

  table.innerHTML = `<tr><td colspan="4">⏳ جاري التحميل...</td></tr>`;

  try {
    const response = await fetch(
      `/api/method/service_planner.api.task_api.get_my_tasks?status=${status}&due_filter=${due}`
    );
    const result = await response.json();
    const tasks = result.message;

    if (!tasks.length) {
      table.innerHTML = `<tr><td colspan="4">🚫 لا توجد مهام</td></tr>`;
      return;
    }

    table.innerHTML = "";
    tasks.forEach(task => {
      const row = document.createElement("tr");
      row.className = `status-${task.status.toLowerCase()}`;
      row.innerHTML = `
        <td>${task.task_title}</td>
        <td>${task.due_date}</td>
        <td>${task.status}</td>
        <td>${task.status === "Pending" ? `<button onclick="completeTask('${task.name}')">✔️ إكمال</button>` : "—"}</td>
      `;
      table.appendChild(row);
    });
  } catch (err) {
    console.error(err);
    table.innerHTML = `<tr><td colspan="4">❌ فشل التحميل</td></tr>`;
  }
}

async function completeTask(task_name) {
  if (!confirm("هل أنت متأكد أنك تريد إكمال المهمة؟")) return;
  await fetch(`/api/method/service_planner.api.task_api.mark_task_completed`, {
    method: "POST",
    headers: { 
      "Content-Type": "application/json",
      "X-Frappe-CSRF-Token": frappe.csrf_token
    },
    body: JSON.stringify({ task_name })
  });
  loadTasks();
}

window.addEventListener("DOMContentLoaded", loadTasks);
