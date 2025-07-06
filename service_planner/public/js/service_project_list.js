frappe.listview_settings['Service Project'] = {
    onload(listview) {
        if ($('#my-tasks-btn').length) return;

        const $btn = $(`
            <button class="btn btn-primary btn-sm dropdown-toggle" id="my-tasks-btn" style="margin-left: 10px;">
                🧾 مهامي
            </button>
        `);

        const $menu = $(`
            <div class="dropdown-menu show" style="position: absolute; z-index: 1000;">
                <a class="dropdown-item" href="/my_tasks" target="_blank">🕒 مهامي اليوم</a>
                <a class="dropdown-item" href="/completed-tasks" target="_blank">✅ المهام المكتملة</a>
                <a class="dropdown-item" href="/all-my-tasks" target="_blank">📅 كل مهامي</a>
            </div>
        `).hide();

        listview.page.add_inner_button('🧾 مهامي', () => {
            $menu.toggle();
        });

        $menu.appendTo(listview.page.wrapper.find('.page-head'));

        $(document).on('click', function (e) {
            if (!$(e.target).closest('#my-tasks-btn').length && !$(e.target).closest('.dropdown-menu').length) {
                $menu.hide();
            }
        });
    }
};
