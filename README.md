# HANDOFF

**A collaborative workspace and visual review platform.**

HANDOFF is a web-based collaboration platform designed to help teams organize their workspaces, manage projects, and collaborate through a centralized environment.

The project is structured as a monorepo containing a Next.js frontend and a Django REST API backend, backed by PostgreSQL.

## Tech Stack

### Frontend
- **Next.js 16** — React framework
- **React 19**
- **TypeScript**
- **Tailwind CSS 4**
- **TanStack Query** — Server-state management
- **Lucide React** — Icons

### Backend
- **Python / Django 6.1**
- **Django REST Framework**
- **Simple JWT** — Token-based authentication
- **PostgreSQL** — Relational database
- **django-cors-headers** — Cross-origin configuration
- **drf-spectacular** — OpenAPI schema and Swagger documentation

## Project Structure

```text
HANDOFF/
├── backend/
│   ├── accounts/       # Authentication and user management
│   ├── config/         # Django project configuration
│   ├── projects/       # Project management API
│   ├── workspaces/     # Workspace management API
│   ├── .env.example
│   ├── manage.py
│   └── requirements.txt
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── app/        # Next.js application routes
│   │   ├── components/ # Reusable UI components
│   │   ├── lib/        # API client and application contexts
│   │   └── types/      # TypeScript definitions
│   ├── package.json
│   └── tsconfig.json
│
└── README.md
```

## Getting Started

### Prerequisites

Make sure you have the following installed:

- Python 3.12 or a compatible version
- Node.js and npm
- PostgreSQL
- Git

### 1. Clone the repository

```bash
git clone <YOUR_REPOSITORY_URL>
cd HANDOFF
```

### 2. Backend Setup

Navigate to the backend directory:

```bash
cd backend
```

Create and activate a virtual environment.

**Windows PowerShell:**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**macOS / Linux:**

```bash
python -m venv venv
source venv/bin/activate
```

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Create your local environment file:

**Windows PowerShell:**

```powershell
Copy-Item .env.example .env
```

**macOS / Linux:**

```bash
cp .env.example .env
```

Open `backend/.env` and configure your local environment:

```env
SECRET_KEY=your-generated-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

DB_NAME=handoff_db
DB_USER=postgres
DB_PASSWORD=your-postgres-password
DB_HOST=localhost
DB_PORT=5432

AUTH_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False

CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
CSRF_TRUSTED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

Generate a new Django secret key instead of using the placeholder:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Create a PostgreSQL database named `handoff_db`, or update `DB_NAME` to match your database.

Apply database migrations:

```bash
python manage.py migrate
```

Optionally, create an administrator account:

```bash
python manage.py createsuperuser
```

Start the backend development server:

```bash
python manage.py runserver
```

The backend API will be available at:

```text
http://localhost:8000
```

### 3. Frontend Setup

Open a separate terminal and navigate to the frontend directory:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Create a `.env.local` file in the `frontend/` directory:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Start the frontend development server:

```bash
npm run dev
```

The frontend will be available at:

```text
http://localhost:3000
```

## Application Routes

The current frontend includes the following routes:

| Route | Description |
|---|---|
| `/` | Main landing page |
| `/login` | User login |
| `/register` | User registration |
| `/dashboard` | Workspace dashboard |

## API Documentation

The backend exposes versioned REST API endpoints under:

```text
/api/v1/
```

Main API areas include:

| Endpoint | Purpose |
|---|---|
| `/api/v1/auth/` | Authentication |
| `/api/v1/invitations/accept/` | Invitation acceptance |
| `/api/v1/workspaces/` | Workspace operations and project-related routes |

Interactive API documentation is available through Swagger UI:

```text
http://localhost:8000/api/docs/
```

The OpenAPI schema is available at:

```text
http://localhost:8000/api/schema/
```

## Development Commands

### Frontend

```bash
npm run dev       # Start development server
npm run build     # Build production application
npm run start     # Start production server
npm run lint      # Run ESLint
```

### Backend

```bash
python manage.py runserver       # Start Django server
python manage.py migrate         # Apply migrations
python manage.py makemigrations  # Generate migrations
python manage.py test            # Run Django tests
```

## Environment Variables

### Backend

| Variable | Description |
|---|---|
| `SECRET_KEY` | Django secret key |
| `DEBUG` | Enables or disables debug mode |
| `ALLOWED_HOSTS` | Allowed Django hosts |
| `DB_NAME` | PostgreSQL database name |
| `DB_USER` | PostgreSQL username |
| `DB_PASSWORD` | PostgreSQL password |
| `DB_HOST` | Database host |
| `DB_PORT` | Database port |
| `AUTH_COOKIE_SECURE` | Secure authentication cookie setting |
| `CSRF_COOKIE_SECURE` | Secure CSRF cookie setting |
| `CORS_ALLOWED_ORIGINS` | Allowed frontend origins |
| `CSRF_TRUSTED_ORIGINS` | Trusted CSRF origins |

### Frontend

| Variable | Description |
|---|---|
| `NEXT_PUBLIC_API_URL` | Backend API base URL |

## Security Notes

- Keep real environment files out of version control.
- Never commit production secrets, passwords, or private keys.
- Use a unique Django secret key for each environment.
- Configure secure cookies and production hosts before deployment.
- Restrict CORS and CSRF trusted origins to the domains that actually need access.

## Project Status

HANDOFF is under active development. Features and application structure may evolve as development progresses.

---

**Built with Next.js, React, Django REST Framework, and PostgreSQL.**