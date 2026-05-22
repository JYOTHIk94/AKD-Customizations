app_name = "akd_customizations"
app_title = "Akd Customizations"
app_publisher = "jyothi"
app_description = "AKD Customizations"
app_email = "jyothi.p@quarkcs.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "akd_customizations",
# 		"logo": "/assets/akd_customizations/logo.png",
# 		"title": "Akd Customizations",
# 		"route": "/akd_customizations",
# 		"has_permission": "akd_customizations.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/akd_customizations/css/akd_customizations.css"
# app_include_js = "/assets/akd_customizations/js/akd_customizations.js"

# include js, css files in header of web template
# web_include_css = "/assets/akd_customizations/css/akd_customizations.css"
# web_include_js = "/assets/akd_customizations/js/akd_customizations.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "akd_customizations/public/scss/website"

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
# app_include_icons = "akd_customizations/public/icons.svg"

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

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "akd_customizations.utils.jinja_methods",
# 	"filters": "akd_customizations.utils.jinja_filters"
# }

# Installation
# ------------

after_install = "akd_customizations.install.after_install"
after_migrate = "akd_customizations.install.after_migrate"

# Uninstallation
# ------------

# before_uninstall = "akd_customizations.uninstall.before_uninstall"
# after_uninstall = "akd_customizations.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "akd_customizations.utils.before_app_install"
# after_app_install = "akd_customizations.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "akd_customizations.utils.before_app_uninstall"
# after_app_uninstall = "akd_customizations.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "akd_customizations.build.after_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "akd_customizations.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# FR-CRM-64/65 — reps see only their own Leads / Opportunities.
permission_query_conditions = {
	"Lead": "akd_customizations.overrides.crm_permissions.lead_query",
	"Opportunity": "akd_customizations.overrides.crm_permissions.opportunity_query",
	# FR-PROJ-62 — users see only projects they are assigned to.
	"Project": "akd_customizations.overrides.project_permissions.project_query",
	"Task": "akd_customizations.overrides.project_permissions.task_query",
}

# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------

doc_events = {
	"Sales Invoice": {
		"validate": [
			"akd_customizations.overrides.sales_invoice.validate_credit_limit",
			# FR-FA-55 — block selling an asset without disposal approval.
			"akd_customizations.overrides.asset_disposal.require_for_sales_invoice",
		],
	},
	# FR-CRM-25 — auto-create Customer when an Opportunity is won.
	"Opportunity": {
		"on_change": "akd_customizations.overrides.opportunity.create_customer_on_won",
	},
	# FR-FA-55 — block scrapping an asset without disposal approval.
	"Journal Entry": {
		"validate": "akd_customizations.overrides.asset_disposal.require_for_journal_entry",
	},
	# FR-FA-55 — stamp who approved the disposal (audit).
	"Asset": {
		"validate": "akd_customizations.overrides.asset_disposal.stamp_approver",
	},
}

# Scheduled Tasks
# ---------------

scheduler_events = {
	"daily": [
		"akd_customizations.tasks.supplier_payment_reminders.send",
		"akd_customizations.tasks.overdue_delivery_alert.send",
		"akd_customizations.tasks.blanket_order_expiry.send",
		"akd_customizations.tasks.quotation_expiry_alert.send",
		"akd_customizations.tasks.crm_first_response_overdue.send",
	],
	"weekly": [
		"akd_customizations.tasks.sales_target_progress.send",
		"akd_customizations.tasks.project_status_digest.send",
	],
	"monthly": [
		"akd_customizations.tasks.quality_review_reminder.send",
	],
}

# Fixtures
# --------
# Records exported from the dev site and re-imported on install / migrate.

fixtures = [
	{"dt": "Payment Term", "filters": [["name", "in", [
		"AKD-Net-30", "AKD-Net-45", "AKD-Net-60",
		"AKD-PIA", "AKD-Advance-50", "AKD-Delivery-50",
	]]]},
	{"dt": "Payment Terms Template", "filters": [["name", "in", [
		"AKD Customer Standard", "AKD Supplier Standard", "AKD 50/50 Split"
	]]]},
	# Bank Transfer and Cheque are standard ERPNext records; we don't ship them
	# as fixtures because doing so overwrites the per-company `accounts` child
	# rows that setup/modes_of_payment.py wires (regression seen 2026-05-14).
	# Per-company wiring is re-applied via the after_migrate hook below.
	{"dt": "Sales Taxes and Charges Template", "filters": [["name", "like", "AKD UAE VAT%"]]},
	{"dt": "Purchase Taxes and Charges Template", "filters": [["name", "like", "AKD UAE VAT%"]]},
	{"dt": "Notification", "filters": [["name", "like", "AKD %"]]},
	{"dt": "Auto Email Report", "filters": [["name", "like", "AKD %"]]},
	{"dt": "Print Format", "filters": [["name", "like", "AKD %"]]},
	{"dt": "Report", "filters": [["name", "like", "AKD %"]]},
	{"dt": "Property Setter", "filters": [["module", "=", "Accounting"]]},
	{"dt": "Custom Field", "filters": [["module", "=", "Accounting"]]},
	{"dt": "Supplier Group", "filters": [["name", "in", ["AKD OEM", "AKD Non-OEM"]]]},
	{"dt": "Workflow State", "filters": [["name", "in", [
		"Pending Line Manager", "Pending Management",
		"Pending Purchase Review", "Pending End User", "Pending Finance",
		"Pending Approval", "Pending Sales Manager", "Pending Finance Review",
		"In Progress", "Pending Timesheet Approval",
		"Timesheet Approved", "Timesheet Rejected",
	]]]},
	{"dt": "Workflow", "filters": [["name", "like", "AKD %"]]},
	{"dt": "Supplier Scorecard Criteria", "filters": [["name", "like", "AKD %"]]},
	{"dt": "Supplier Scorecard Standing", "filters": [["name", "like", "AKD %"]]},
	# CRM masters (FR-CRM-06/19/20) + round-robin rule (FR-CRM-09).
	{"dt": "UTM Source", "filters": [["name", "in", [
		"Website", "Phone / Walk-in", "Referral", "Social Media",
		"Email Campaign", "Trade Show / Event", "Paid Advertising",
		"Partner / Channel", "Cold Outreach",
	]]]},
	{"dt": "Opportunity Type", "filters": [["name", "in", [
		"Advisory", "Platforms", "Sustained Services", "Maintenance",
	]]]},
	{"dt": "Opportunity Lost Reason", "filters": [["name", "in", [
		"Price", "Lost to Competitor", "No Budget",
		"Timing / No Decision", "Requirement Not Met",
	]]]},
	{"dt": "Assignment Rule", "filters": [["name", "like", "AKD %"]]},
	# Projects masters (FR-PROJ-06/20/31).
	{"dt": "Project Type", "filters": [["name", "in", [
		"Advisory", "AI", "IT Implementation",
	]]]},
	{"dt": "Task Type", "filters": [["name", "in", [
		"Analysis", "Design", "Development", "Review",
		"Deployment", "Project Management",
	]]]},
	{"dt": "Activity Type", "filters": [["name", "in", [
		"Consulting", "Implementation", "Project Management",
		"Support", "Travel",
	]]]},
	{"dt": "Role", "filters": [["name", "in", [
		"Sales Executive", "General Manager",
		"Quality Inspector", "Quality Auditor", "Process Owner",
		"Marketing User", "CRM Admin", "Read-only Viewer",
		"Timesheet User",
	]]]},
]

# Testing
# -------

# before_tests = "akd_customizations.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "akd_customizations.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "akd_customizations.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "akd_customizations.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["akd_customizations.utils.before_request"]
# after_request = ["akd_customizations.utils.after_request"]

# Job Events
# ----------
# before_job = ["akd_customizations.utils.before_job"]
# after_job = ["akd_customizations.utils.after_job"]

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
# 	"akd_customizations.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

