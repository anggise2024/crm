# CRM Follow-up System

## Overview

This is a Flask-based CRM follow-up system that integrates with Google Sheets to track customer orders and manage follow-up activities. The system automatically processes order data from Google Sheets and provides a dashboard for CRM staff to manage customer follow-ups.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Architecture
- **Framework**: Flask (Python web framework)
- **Database**: SQLAlchemy ORM with SQLite as the default database
- **Scheduled Tasks**: APScheduler for automated data processing
- **External Integration**: Google Sheets API for data synchronization

### Frontend Architecture
- **Template Engine**: Jinja2 (Flask's default)
- **CSS Framework**: Bootstrap 5 with dark theme
- **JavaScript**: Vanilla JavaScript for client-side interactions
- **Icons**: Font Awesome

### Database Design
The system uses SQLite by default with two main models:
- **FollowUpRecord**: Stores order and follow-up information
- **SystemLog**: Tracks system activities and errors

## Key Components

### Core Application Files
- `app.py`: Flask application initialization and configuration
- `main.py`: Application entry point
- `models.py`: Database models using SQLAlchemy
- `routes.py`: Web routes and controllers
- `scheduler.py`: Background job scheduling

### Data Processing
- `data_processor.py`: Handles Google Sheets data processing and transformation
- `google_sheets_service.py`: Google Sheets API integration service

### Frontend
- Templates in `templates/` directory with Bootstrap-based UI
- Static assets in `static/` directory for CSS and JavaScript

## Data Flow

1. **Data Ingestion**: Scheduled job reads order data from Google Sheets every 2 minutes (configurable)
2. **Data Processing**: Raw data is cleaned, validated, and transformed
3. **Database Storage**: Processed data is stored in SQLite database
4. **Web Interface**: Flask routes serve data to web templates
5. **Follow-up Management**: CRM staff can update follow-up statuses through the web interface

## External Dependencies

### Google Sheets Integration
- Uses service account authentication (`service_account.json`)
- Reads from "order-update" sheet
- Writes to "followed-up" sheet
- Requires Google Sheets API v4 access

### Key Python Dependencies
- Flask and Flask-SQLAlchemy for web framework and ORM
- APScheduler for background task scheduling
- Google API client libraries for Sheets integration
- Pandas for data processing
- Werkzeug for WSGI utilities

## Deployment Strategy

### Development Environment
- SQLite database stored in `instance/crm_followup.db`
- Debug mode enabled
- Background scheduler runs every 2 minutes for testing

### Production Considerations
- Database can be switched to PostgreSQL via `DATABASE_URL` environment variable
- Session secret configurable via `SESSION_SECRET` environment variable
- ProxyFix middleware included for reverse proxy deployment
- Logging configured for debugging and monitoring

### Security Notes
- Service account credentials stored in `service_account.json`
- Session management with configurable secret key
- Database connection pooling with health checks enabled

### Key Configuration Points
- Scheduler frequency can be modified in `scheduler.py`
- Google Sheets ID and sheet names configured in `google_sheets_service.py`
- Database path and connection settings in `app.py`
- CRM staff names defined in `data_processor.py`