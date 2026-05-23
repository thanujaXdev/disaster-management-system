# Disaster Management System

A full-stack web application built with Flask for managing disaster reports, volunteers, shelters, and alerts.

## Tech Stack
- **Frontend**: HTML, CSS, Bootstrap 5, Chart.js
- **Backend**: Python + Flask
- **Database**: SQLite (Flask-SQLAlchemy)
- **Maps**: Google Maps JavaScript API

## Setup & Run

### 1. Install Python (3.8+)
Download from https://python.org

### 2. Create Virtual Environment
```
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux
```

### 3. Install Dependencies
```
pip install -r requirements.txt
```

### 4. Run the App
```
python app.py
```

### 5. Open Browser
Go to: http://127.0.0.1:5000

## Default Admin Login
- Email: admin@disaster.com
- Password: admin123

## Features
- Role-based login (Citizen / Volunteer / Admin)
- Disaster reporting with photo upload
- Admin approval workflow
- Live alert system
- Google Maps shelter locator
- Admin dashboard with Chart.js graphs
- Volunteer task assignment
