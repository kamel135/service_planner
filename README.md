# Service Planner

🎯 A simple ERPNext module to manage service-based projects with auto-generated tasks.

## Features

- Create Service Projects with scheduling
- Auto-generate tasks based on role and time
- Role-based permissions and filters
- Color-coded tasks and inline actions

## Tech Stack

- 🔧 ERPNext + Frappe Framework
- 📦 Custom App
- 📁 Fixtures-based setup
- ✏️ Client Scripts + Server Scripts

## Installation

```bash
# inside your bench instance
bench get-app service_planner https://github.com/kamel135/service_planner.git
bench --site [your-site] install-app service_planner
