document.addEventListener("DOMContentLoaded", function () {
  new Vue({
    el: "#app",
    data: {
      tasks: []
    },
    methods: {
      async loadTasks() {
        try {
          const res = await fetch("/api/method/service_planner.www.my_tasks.get_tasks");
          const data = await res.json();
          this.tasks = data.message;
        } catch (err) {
          alert("فشل في تحميل المهام");
        }
      },
      async markAsCompleted(task) {
        try {
          const res = await fetch(`/api/method/service_planner.www.my_tasks.mark_completed?name=${task.name}`, {
            method: "GET",
            headers: {
              "X-Frappe-CSRF-Token": frappe.csrf_token
            }
          });
          const data = await res.json();
          task.status = data.message.status;
        } catch (err) {
          alert("فشل في تحديث المهمة");
        }
      }
    },
    mounted() {
      this.loadTasks();
    }
  });
});
