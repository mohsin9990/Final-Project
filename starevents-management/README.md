# StarEvents Management System
## Digital Transformation Platform for SMEs

A comprehensive web-based event management system with advanced security, inventory tracking, and reporting capabilities.

## Project Structure

```
starevents-management/
├── backend/          # Django REST API
├── frontend/         # React.js Frontend
├── docker-compose.yml
└── README.md
```

## Technology Stack

### Backend
- Python 3.11+
- Django 4.2+
- Django REST Framework
- PostgreSQL 15
- JWT Authentication
- ReportLab (PDF generation)
- openpyxl (Excel export)
- face_recognition (biometric auth)

### Frontend
- React 18
- React Router v6
- Axios
- Tailwind CSS
- Recharts
- React Hook Form

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 18+
- Python 3.11+

### Development Setup

1. Clone the repository
2. Copy `.env.example` to `.env` and configure
3. Run `docker-compose up` for full stack
4. Or run backend/frontend separately (see below)

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### Frontend Setup
```bash
cd frontend
npm install
npm start
```

## Module Contributors

1. **Security & Authentication** - Muhammad Shamail Tariq
2. **Event Management & Booking** - Muhammad Mohsin Khan
3. **Inventory & Reporting** - Md Masum Rana
4. **Database & DevOps** - Muhammad Musharaf

## License
Academic Project - University of the West of Scotland
