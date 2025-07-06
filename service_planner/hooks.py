app_name = "service_planner"
app_title = "Service Planner"
app_publisher = "Kamel Elnemr"
app_description = "Service planner for managing projects and tasks"
app_email = "kamelelnemr1@gmail.com"
app_license = "mit"

# Apps
# ------------------

#####################


app_include_js = "/assets/service_planner/js/service_project.js"


permission_query_conditions = {
    "Service Task": "service_planner.service_planner.doctype.service_task.service_task.get_permission_query_conditions"
}

has_permission = {
    "Service Task": "service_planner.service_planner.doctype.service_task.service_task.has_permission"
}



fixtures = [
    {"dt": "Role", "filters": [["name", "in", [
        "Engineer", "Analyst", "Projects Manager", "Projects User", "Account Manager"
    ]]]},
    {"dt": "Workflow"},
    {"dt": "Permission Query Script", "filters": [["reference_doctype", "in", [
        "Service Project", "Service Task"
    ]]]}
]


fixtures = [
    {
        "dt": "Role",
        "filters": [["name", "in", [
            "Engineer", "Analyst", "Projects Manager", "Projects User", "Account Manager"
        ]]]
    },
    {"dt": "Workflow"}
]



fixtures = ["Custom Field", "Server Script"]


fixtures = ["Server Script"]

doc_events = {
    "Service Project": {
        "before_save": "service_planner.server_script.auto_generate_tasks.execute",
        "validate": "service_planner.server_script.auto_generate_tasks.validate_schedule_configuration"
    }
}


permission_query_conditions = {
    "Service Project": "service_planner.server_script.permission_query.get_permission_query_conditions",
    "Service Task": "service_planner.server_script.permission_query.task_permission_query_conditions"
}

app_include_js = [
    "/assets/service_planner/js/service_task.js"
]



fixtures = [
    {"dt": "Role", "filters": [["name", "in", [
        "Engineer", "Analyst", "Projects Manager", "Projects User", "Account Manager"
    ]]]},
    {"dt": "Workflow"},
    {"dt": "Custom Field"},
    {"dt": "Server Script", "filters": [["name", "=", "Auto Generate Tasks for Service Project"]]}
]





##################





# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "service_planner",
# 		"logo": "/assets/service_planner/logo.png",
# 		"title": "Service Planner",
# 		"route": "/service_planner",
# 		"has_permission": "service_planner.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/service_planner/css/service_planner.css"
# app_include_js = "/assets/service_planner/js/service_planner.js"

# include js, css files in header of web template
# web_include_css = "/assets/service_planner/css/service_planner.css"
# web_include_js = "/assets/service_planner/js/service_planner.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "service_planner/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "service_planner/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "service_planner.utils.jinja_methods",
# 	"filters": "service_planner.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "service_planner.install.before_install"
# after_install = "service_planner.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "service_planner.uninstall.before_uninstall"
# after_uninstall = "service_planner.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "service_planner.utils.before_app_install"
# after_app_install = "service_planner.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "service_planner.utils.before_app_uninstall"
# after_app_uninstall = "service_planner.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "service_planner.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"service_planner.tasks.all"
# 	],
# 	"daily": [
# 		"service_planner.tasks.daily"
# 	],
# 	"hourly": [
# 		"service_planner.tasks.hourly"
# 	],
# 	"weekly": [
# 		"service_planner.tasks.weekly"
# 	],
# 	"monthly": [
# 		"service_planner.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "service_planner.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "service_planner.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "service_planner.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["service_planner.utils.before_request"]
# after_request = ["service_planner.utils.after_request"]

# Job Events
# ----------
# before_job = ["service_planner.utils.before_job"]
# after_job = ["service_planner.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"service_planner.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

