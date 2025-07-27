// service_planner/public/js/my_tasks.js

frappe.ready(function() {
   

    if (typeof applyServicePlannerTranslations === 'function') {
        applyServicePlannerTranslations();
    }

    // إضافة سجلات التصحيح
    console.log("Current language:", frappe.boot.lang);
    console.log("Translation test:", __("My Tasks"));
    
    // تهيئة الصفحة
    initializePage();
    
    // تحميل المهام عند بدء التشغيل
    loadTasks();
    
    // ربط أحداث الفلاتر
    bindFilterEvents();
    
    // تحديث تلقائي كل 5 دقائق
    setInterval(loadTasks, 300000);
});

function initializePage() {
    // إضافة مؤشر التحميل
    showLoadingIndicator(true, __("Loading tasks..."));
    
    // تهيئة الإحصائيات
    updateStats({
        total: 0,
        completed: 0,
        in_progress: 0,
        pending: 0,
        overdue: 0
    });
}

function bindFilterEvents() {
    let filterTimeout;
    
    $("#status-filter, #due-filter").on("change", function() {
        clearTimeout(filterTimeout);
        showLoadingIndicator(true, __("Applying filters..."));
        
        filterTimeout = setTimeout(() => {
            loadTasks();
        }, 300);
    });
    
    // إضافة حدث البحث
    $("#search-input").on("input", function() {
        clearTimeout(filterTimeout);
        showLoadingIndicator(true, __("Searching..."));
        
        filterTimeout = setTimeout(() => {
            loadTasks();
        }, 500);
    });
}

function loadTasks() {
    const statusFilter = $("#status-filter").val();
    const dueFilter = $("#due-filter").val();
    const searchTerm = $("#search-input").val().trim();

    console.log(__("Loading tasks with filters:"), { 
        status: statusFilter, 
        due_filter: dueFilter,
        search: searchTerm 
    });

    frappe.call({
        method: "service_planner.api.task_api.get_my_tasks",
        args: {
            status: statusFilter === "All" ? null : statusFilter,
            due_filter: dueFilter === "all" ? null : dueFilter,
            search_term: searchTerm || null
        },
        callback: function(r) {
            showLoadingIndicator(false);
            
            if (r.message && r.message.success) {
                const { tasks, stats, count } = r.message;
                
                if (!tasks || tasks.length === 0) {
                    showNoTasks();
                    updateTaskCounter(0);
                    updateStats(stats || {total: 0, completed: 0, in_progress: 0, pending: 0, overdue: 0});
                    return;
                }

                renderTasks(tasks);
                updateTaskCounter(count);
                updateStats(stats);
            } else {
                showError(r.message?.message || __("Error loading tasks"));
            }
        },
        error: function(err) {
            console.error(__("API Error:"), err);
            showLoadingIndicator(false);
            showError(__("Server connection failed"));
        }
    });
}

function showLoadingIndicator(show, message = '') {
    const loadingStatus = $("#loading-status");
    if (show) {
        loadingStatus.html(`
            <div class="alert alert-info">
                <div class="spinner-border spinner-border-sm" role="status">
                    <span class="sr-only">${__("Loading...")}</span>
                </div>
                <span class="ml-2">${message}</span>
            </div>
        `).show();
    } else {
        loadingStatus.hide();
    }
}

function renderTasks(tasks) {
    const tableBody = $("#tasks-table tbody");
    let html = '';

    tasks.forEach(task => {
        const utcDate = task.due_date;
        const localDate = task.local_due_date || task.due_date;

        html += `
            <tr class="${isOverdue(localDate) && task.status !== "Completed" ? "table-danger" : ""}">
                <td>
                    <strong>${frappe.utils.escape_html(task.task_title_translated || task.task_title)}</strong>
                                        ${task.notes ? `<br><small class="text-muted">${frappe.utils.escape_html(task.notes)}</small>` : ""}
                </td>
                <td>
                    <span class="${isOverdue(localDate) && task.status !== "Completed" ? "text-danger" : ""}">
                        ${formatDateSimple(utcDate)}
                    </span>
                </td>
                <td>
                    <span class="${isOverdue(localDate) && task.status !== "Completed" ? "text-danger font-weight-bold" : "font-weight-bold"}">
                        ${formatDateSimple(localDate)}
                    </span>
                </td>
                <td>
                    <span class="badge badge-${getStatusClass(task.status)}">
                        ${frappe.utils.escape_html(task.status_translated || task.status)}
                    </span>
                </td>
                <td>${task.assigned_to || "—"}</td>
                <td>${task.assigned_role || "—"}</td>
                <td>
                    <div class="btn-group">
                        ${task.status !== "Completed" && task.can_edit ? `
                            <button class="btn btn-success btn-sm" onclick="completeTask('${task.name}')">
                                <i class="fa fa-check"></i> ${__("Complete")}
                            </button>
                        ` : ""}
                        <button class="btn btn-info btn-sm" onclick="viewTaskDetails('${task.name}')">
                            <i class="fa fa-eye"></i> ${__("View")}
                        </button>
                    </div>
                </td>
            </tr>
        `;
    });

    tableBody.html(html);
}

function showNoTasks() {
    $("#tasks-table tbody").html(`
        <tr>
            <td colspan="7" class="text-center">
                <div class="alert alert-info mb-0">${__("No tasks found")}</div>
            </td>
        </tr>
    `);
}

function showError(message) {
    $("#tasks-table tbody").html(`
        <tr>
            <td colspan="7" class="text-center">
                <div class="alert alert-danger mb-0">
                    <i class="fa fa-exclamation-triangle"></i>
                    ${message}
                </div>
            </td>
        </tr>
    `);
}

function updateStats(stats) {
    if (!stats) return;
    
    $("#stats-container").html(`
        <div class="col-md-3">
            <div class="card stat-card total-card">
                <div class="card-body">
                    <h5>${__("Total Tasks")}</h5>
                    <h3 id="total-tasks">${stats.total || 0}</h3>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card stat-card completed-card">
                <div class="card-body">
                    <h5>${__("Completed")}</h5>
                    <h3 id="completed-tasks">${stats.completed || 0}</h3>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card stat-card progress-card">
                <div class="card-body">
                    <h5>${__("In Progress")}</h5>
                    <h3 id="in-progress-tasks">${stats.in_progress || 0}</h3>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card stat-card overdue-card">
                <div class="card-body">
                    <h5>${__("Overdue")}</h5>
                    <h3 id="overdue-tasks">${stats.overdue || 0}</h3>
                </div>
            </div>
        </div>
    `);
}

function formatDateSimple(dateStr) {
    if (!dateStr) return "—";
    
    try {
        const date = new Date(dateStr);
        if (isNaN(date.getTime())) return "—";
        
        const day = String(date.getDate()).padStart(2, '0');
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const year = date.getFullYear();
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        
        return `${day}/${month}/${year} ${hours}:${minutes}`;
    } catch (err) {
        console.error("Error formatting date:", dateStr, err);
        return dateStr;
    }
}

function formatDate(dateStr) {
    if (!dateStr) return "—";
    
    try {
        return frappe.datetime.str_to_user(dateStr);
    } catch (e) {
        return formatDateSimple(dateStr);
    }
}

function getStatusClass(status) {
    const classes = {
        "Pending": "warning",
        "In Progress": "info",
        "Completed": "success",
        "Open": "primary"
    };
    return classes[status] || "secondary";
}

function updateTaskCounter(count) {
    const counterElement = $("#task-counter");
    if (counterElement.length) {
        // استخدم "مهام" مباشرة للعربي
        const taskWord = frappe.boot.lang === 'ar' ? 'مهام' : 'Task(s)';
        counterElement.text(`(${count} ${taskWord})`);
    }
}
function isOverdue(dueDateStr) {
    if (!dueDateStr) return false;
    
    try {
        const taskDate = new Date(dueDateStr);
        const now = new Date();

        if (isNaN(taskDate.getTime())) return false;

        taskDate.setHours(0, 0, 0, 0);
        now.setHours(0, 0, 0, 0);

        return taskDate < now;
    } catch (e) {
        console.error("Error parsing date:", dueDateStr, e);
        return false;
    }
}

function completeTask(taskName) {
    frappe.show_alert({
        message: __("Updating task..."),
        indicator: "blue"
    });

    frappe.call({
        method: "service_planner.api.task_api.mark_task_completed",
        args: { task_name: taskName },
        callback: function(r) {
            if (r.message && r.message.success) {
                frappe.show_alert({
                    message: r.message.message || __("Task completed successfully"),
                    indicator: "green"
                });
                
                loadTasks();
            } else {
                frappe.show_alert({
                    message: r.message?.message || __("Failed to update task"),
                    indicator: "red"
                });
            }
        },
        error: function(err) {
            frappe.show_alert({
                message: __("An unexpected error occurred"),
                indicator: "red"
            });
            console.error(__("Error completing task:"), err);
        }
    });
}

function viewTaskDetails(taskName) {
    frappe.call({
        method: "service_planner.api.task_api.get_task_details",
        args: { task_name: taskName },
        callback: function(r) {
            if (r.message && r.message.success) {
                const task = r.message.task;
                frappe.msgprint({
                    title: __("Task Details"),
                    message: `
                        <div class="task-details-popup">
                            <h4>${frappe.utils.escape_html(task.task_title_translated || task.task_title)}</h4>
                            <div class="task-details">
                                <div class="row">
                                    <div class="col-md-6">
                                        <p>
                                            <strong>${__("Status:")}</strong> 
                                            <span class="badge badge-${getStatusClass(task.status)}">
                                                ${frappe.utils.escape_html(task.status_translated || task.status)}
                                            </span>
                                        </p>
                                        <p><strong>${__("UTC Due Date:")}</strong> ${formatDate(task.due_date)}</p>
                                        <p><strong>${__("Local Due Date:")}</strong> <span class="font-weight-bold text-primary">${formatDate(task.local_due_date || task.due_date)}</span></p>
                                        <p><strong>${__("Assigned To:")}</strong> ${task.assigned_to || "—"}</p>
                                        <p><strong>${__("Role:")}</strong> ${task.assigned_role || "—"}</p>
                                    </div>
                                    <div class="col-md-6">
                                        <p><strong>${__("Creation Date:")}</strong> ${formatDate(task.creation)}</p>
                                        <p><strong>${__("Last Modified:")}</strong> ${formatDate(task.modified)}</p>
                                        ${task.parent ? `<p><strong>${__("Project:")}</strong> ${task.parent}</p>` : ""}
                                    </div>
                                </div>
                                ${task.notes ? `
                                    <div class="task-notes mt-3">
                                        <strong>${__("Notes:")}</strong>
                                        <div class="notes-content">
                                            ${frappe.utils.escape_html(task.notes)}
                                        </div>
                                    </div>
                                ` : ""}
                            </div>
                        </div>
                    `,
                    indicator: getStatusClass(task.status),
                    wide: true
                });
            } else {
                frappe.msgprint({
                    title: __("Error"),
                    message: r.message?.message || __("Error fetching task details"),
                    indicator: "red"
                });
            }
        },
        error: function(err) {
            console.error("Error fetching task details:", err);
            frappe.msgprint({
                title: __("Error"),
                message: __("An unexpected error occurred"),
                indicator: "red"
            });
        }
    });
}

// دوال مساعدة إضافية
function exportTasks() {
    const statusFilter = $("#status-filter").val();
    const dueFilter = $("#due-filter").val();
    const searchTerm = $("#search-input").val().trim();

    frappe.call({
        method: "service_planner.api.task_api.export_tasks",
        args: {
            filters: {
                status: statusFilter === "All" ? null : statusFilter,
                due_filter: dueFilter === "all" ? null : dueFilter,
                search_term: searchTerm || null
            }
        },
        callback: function(r) {
            if (r.message && r.message.success) {
                const csv = convertToCSV(r.message.data);
                downloadCSV(csv, 'my_tasks.csv');
            } else {
                frappe.show_alert({
                    message: __("Failed to export tasks"),
                    indicator: "red"
                });
            }
        }
    });
}

function convertToCSV(data) {
    if (!data || data.length === 0) return '';
    
    const headers = Object.keys(data[0]);
    const csvHeaders = headers.join(',');
    
    const csvRows = data.map(row => {
        return headers.map(header => {
            const value = row[header] || '';
            return `"${value.toString().replace(/"/g, '""')}"`;
        }).join(',');
    });
    
    return csvHeaders + '\n' + csvRows.join('\n');
}

function downloadCSV(csv, filename) {
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement("a");
    
    if (link.download !== undefined) {
        const url = URL.createObjectURL(blob);
        link.setAttribute("href", url);
        link.setAttribute("download", filename);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
}

// إضافة زر التصدير إذا لزم الأمر
$(document).ready(function() {
    if ($("#export-btn").length === 0 && $(".container h1").length) {
        $(".container h1").append(`
            <button id="export-btn" class="btn btn-secondary btn-sm ml-3" onclick="exportTasks()">
                <i class="fa fa-download"></i> ${__("Export")}
            </button>
        `);
    }
});

$(document).ready(function() {
    // انتظر قليلاً حتى يتم تحميل الصفحة
    setTimeout(function() {
        // ترجمة العناوين في الـ select
        $('#status-filter option[value="All"]').text(__("All Statuses"));
        $('#status-filter option[value="Open"]').text(__("Open"));
        $('#status-filter option[value="Pending"]').text(__("Pending"));
        $('#status-filter option[value="In Progress"]').text(__("In Progress"));
        $('#status-filter option[value="Completed"]').text(__("Completed"));
        
        $('#due-filter option[value="all"]').text(__("All Dates"));
        $('#due-filter option[value="today"]').text(__("Today"));
        $('#due-filter option[value="week"]').text(__("This Week"));
        $('#due-filter option[value="month"]').text(__("This Month"));
        $('#due-filter option[value="overdue"]').text(__("Overdue"));
        
        // ترجمة الـ labels
        $('label[for="status-filter"]').text(__("Task Status"));
        $('label[for="due-filter"]').text(__("Due Date"));
        $('label[for="search-input"]').text(__("Search Tasks"));
        
        // ترجمة رؤوس الجدول
        $('#tasks-table th:eq(0)').text(__("Task"));
        $('#tasks-table th:eq(1)').text(__("UTC Due Date"));
        $('#tasks-table th:eq(2)').text(__("Local Due Date"));
        $('#tasks-table th:eq(3)').text(__("Status"));
        $('#tasks-table th:eq(4)').text(__("Assigned To"));
        $('#tasks-table th:eq(5)').text(__("Role"));
        $('#tasks-table th:eq(6)').text(__("Actions"));
        
        // ترجمة placeholder
        $('#search-input').attr('placeholder', __('Search by title or notes...'));
        
        // إضافة زر التصدير إذا لم يكن موجود
        if ($("#export-btn").length === 0 && $(".container h1").length) {
            $(".container h1").append(`
                <button id="export-btn" class="btn btn-secondary btn-sm ml-3" onclick="exportTasks()">
                    <i class="fa fa-download"></i> ${__("Export")}
                </button>
            `);
        }
    }, 100);
});
