// service_planner/public/js/my_tasks.js

frappe.ready(function() {
    // تحميل المهام عند تحميل الصفحة
    loadTasks();
    
    // ربط أحداث الفلاتر
    $('#status-filter').on('change', loadTasks);
    $('#due-filter').on('change', loadTasks);

    // تحديث المهام كل 5 دقائق
    setInterval(loadTasks, 300000);
});

function loadTasks() {
    const tableBody = $('#tasks-table tbody');
    showLoading(tableBody);

    const statusFilter = $('#status-filter').val();
    const dueFilter = $('#due-filter').val();

    frappe.call({
        method: "service_planner.api.task_api.get_my_tasks",
        args: {
            status: statusFilter === 'All' ? null : statusFilter,
            due_filter: dueFilter === 'all' ? null : dueFilter
        },
        callback: function(r) {
            console.log("API Response:", r.message);
            
            if (r.message && r.message.success) {
                const tasks = r.message.tasks;
                
                if (tasks.length === 0) {
                    showNoTasks(tableBody);
                    updateTaskCounter(0);
                    return;
                }

                // عرض المهام
                let html = '';
                tasks.forEach(task => {
                    html += `
                        <tr>
                            <td>
                                <strong>${frappe.utils.escape_html(task.task_title)}</strong>
                                ${task.notes ? `<br><small class="text-muted">${frappe.utils.escape_html(task.notes)}</small>` : ''}
                            </td>
                            <td>${formatDate(task.due_date)}</td>
                            <td>
                                <span class="badge badge-${getStatusClass(task.status)}">
                                    ${translateStatus(task.status)}
                                </span>
                            </td>
                            <td>${task.assigned_to || '—'}</td>
                            <td>${task.assigned_role || '—'}</td>
                            <td>
                                ${task.status !== 'Completed' ? `
                                    <button class="btn btn-success btn-sm" onclick="completeTask('${task.name}')">
                                        <i class="fa fa-check"></i> إكمال
                                    </button>
                                ` : ''}
                                <button class="btn btn-info btn-sm" onclick="viewTaskDetails('${task.name}')">
                                    <i class="fa fa-eye"></i> عرض
                                </button>
                            </td>
                        </tr>
                    `;
                });
                
                tableBody.html(html);
                
                // تحديث العداد
                updateTaskCounter(tasks.length);
            } else {
                showError(tableBody, "حدث خطأ في تحميل المهام");
            }
        },
        error: function(err) {
            console.error("API Error:", err);
            showError(tableBody, "فشل الاتصال بالخادم");
        }
    });
}

function showLoading(tableBody) {
    tableBody.html(`
        <tr>
            <td colspan="6" class="text-center">
                <div class="spinner-border text-primary" role="status">
                    <span class="sr-only">جاري التحميل...</span>
                </div>
            </td>
        </tr>
    `);
}

function showNoTasks(tableBody) {
    tableBody.html(`
        <tr>
            <td colspan="6" class="text-center">
                لا توجد مهام
            </td>
        </tr>
    `);
}

function showError(tableBody, message) {
    tableBody.html(`
        <tr>
            <td colspan="6" class="text-center text-danger">
                <i class="fa fa-exclamation-triangle"></i>
                ${message}
            </td>
        </tr>
    `);
}

function formatDate(dateStr) {
    if (!dateStr) return '—';
    const date = new Date(dateStr);
    const options = {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    };
    return date.toLocaleDateString('ar-EG', options);
}

function getStatusClass(status) {
    const classes = {
        'Pending': 'warning',
        'In Progress': 'info',
        'Completed': 'success',
        'Open': 'primary'
    };
    return classes[status] || 'secondary';
}

function translateStatus(status) {
    const translations = {
        'Pending': 'قيد الانتظار',
        'In Progress': 'قيد التنفيذ',
        'Completed': 'مكتمل',
        'Open': 'مفتوح'
    };
    return translations[status] || status;
}

function updateTaskCounter(count) {
    const counterElement = $('#task-counter');
    if (counterElement.length) {
        counterElement.text(`إجمالي المهام: ${count}`);
    }
}

async function completeTask(taskName) {
    try {
        // عرض مربع تأكيد
        const confirmed = await new Promise(resolve => {
            frappe.confirm(
                'هل أنت متأكد من إكمال هذه المهمة؟',
                () => resolve(true),
                () => resolve(false)
            );
        });

        if (!confirmed) return;

        // عرض مؤشر التحميل
        frappe.show_alert({
            message: 'جاري تحديث المهمة...',
            indicator: 'blue'
        });

        const result = await frappe.call({
            method: "service_planner.api.task_api.mark_task_completed",
            args: { task_name: taskName }
        });

        if (result.message && result.message.success) {
            frappe.show_alert({
                message: result.message.message || 'تم إكمال المهمة بنجاح',
                indicator: 'green'
            });
            
            // تحديث عرض المهام
            loadTasks();
        } else {
            throw new Error(result.message.message || 'فشل تحديث المهمة');
        }
    } catch (err) {
        frappe.show_alert({
            message: err.message || 'حدث خطأ غير متوقع',
            indicator: 'red'
        });
        console.error('Error completing task:', err);
    }
}
function viewTaskDetails(taskName) {
    frappe.call({
        method: "service_planner.api.task_api.get_task_details",
        args: { task_name: taskName },
        callback: function(r) {
            if (r.message && r.message.success) {
                const task = r.message.task;
                frappe.msgprint({
                    title: 'تفاصيل المهمة',
                    message: `
                        <div class="task-details-popup">
                            <h4>${frappe.utils.escape_html(task.task_title)}</h4>
                            <div class="task-details">
                                <div class="row">
                                    <div class="col-md-6">
                                        <p>
                                            <strong>الحالة:</strong> 
                                            <span class="badge badge-${getStatusClass(task.status)}">
                                                ${translateStatus(task.status)}
                                            </span>
                                        </p>
                                        <p><strong>الموعد:</strong> ${formatDate(task.due_date)}</p>
                                        <p><strong>المسند إليه:</strong> ${task.assigned_to || '—'}</p>
                                        <p><strong>الدور:</strong> ${task.assigned_role || '—'}</p>
                                    </div>
                                    <div class="col-md-6">
                                        <p><strong>تاريخ الإنشاء:</strong> ${formatDate(task.creation)}</p>
                                        <p><strong>آخر تحديث:</strong> ${formatDate(task.modified)}</p>
                                        ${task.parent ? `<p><strong>المشروع:</strong> ${task.parent}</p>` : ''}
                                    </div>
                                </div>
                                ${task.notes ? `
                                    <div class="task-notes mt-3">
                                        <strong>ملاحظات:</strong>
                                        <div class="notes-content">
                                            ${frappe.utils.escape_html(task.notes)}
                                        </div>
                                    </div>
                                ` : ''}
                            </div>
                        </div>
                    `,
                    indicator: getStatusClass(task.status),
                    wide: true
                });
            } else {
                frappe.msgprint({
                    title: 'خطأ',
                    message: r.message.message || 'حدث خطأ في جلب تفاصيل المهمة',
                    indicator: 'red'
                });
            }
        }
    });
}
// دالة مساعدة للتحقق من التاريخ
function isOverdue(dueDate) {
    if (!dueDate) return false;
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const taskDate = new Date(dueDate);
    return taskDate < today;
}

// دالة لتحديث حالة التحميل
function updateLoadingStatus(message, isError = false) {
    const statusElement = $('#loading-status');
    if (statusElement.length) {
        statusElement.html(`
            <div class="alert alert-${isError ? 'danger' : 'info'} mb-3">
                ${message}
            </div>
        `);
    }
}

// دالة لتنسيق وقت مضى
function timeAgo(dateStr) {
    const date = new Date(dateStr);
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);
    
    let interval = Math.floor(seconds / 31536000);
    if (interval > 1) return `منذ ${interval} سنة`;
    
    interval = Math.floor(seconds / 2592000);
    if (interval > 1) return `منذ ${interval} شهر`;
    
    interval = Math.floor(seconds / 86400);
    if (interval > 1) return `منذ ${interval} يوم`;
    
    interval = Math.floor(seconds / 3600);
    if (interval > 1) return `منذ ${interval} ساعة`;
    
    interval = Math.floor(seconds / 60);
    if (interval > 1) return `منذ ${interval} دقيقة`;
    
    return 'منذ لحظات';
}
