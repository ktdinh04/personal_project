# Personal Hub

A modern, production-ready personal portfolio and project demo platform with a plugin/module architecture. Built for self-hosting on personal servers with GPU support for AI/ML workloads.

![Personal Hub Architecture](docs/architecture.png)

## Features

- **Landing Page** - Configurable personal portfolio with bio, skills, social links
- **Authentication** - JWT-based auth with access/refresh tokens and RBAC
- **Dashboard** - Modern SaaS-style dashboard with sidebar navigation
- **Module System** - Plugin architecture for easy project integration
- **Admin Panel** - User management, role assignment, audit logging
- **GPU Support** - NVIDIA Container Toolkit integration for AI/ML workloads

### Included Demo Modules

1. **DeepStream Camera Stream** - GPU-accelerated RTSP camera streaming
2. **Person Detection** - Real-time person detection using YOLO

## Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS, shadcn/ui |
| Backend | FastAPI, Python 3.11, SQLAlchemy 2.0 |
| Database | MySQL 8.0 |
| Cache | Redis 7 |
| Media Relay | go2rtc |
| AI/ML | PyTorch, YOLO, NVIDIA DeepStream |
| Container | Docker Compose with GPU profiles |

## Quick Start

### Prerequisites

- Docker and Docker Compose v2
- (Optional) NVIDIA GPU with nvidia-container-toolkit for GPU features
- Git

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/personal-hub.git
cd personal-hub
```

2. **Copy environment file**
```bash
cp .env.example .env
```

3. **Configure environment variables**
Edit `.env` with your settings:
```bash
# Required
JWT_SECRET_KEY=your_super_secret_key_here
MYSQL_PASSWORD=your_secure_password
INIT_ADMIN_EMAIL=admin@yourdomain.com
INIT_ADMIN_PASSWORD=YourSecurePassword123!

# Optional - Camera URL for DeepStream
DEFAULT_CAMERA_URL=rtsp://user:pass@camera-ip:554/stream
```

4. **Start services**

**CPU Mode (default):**
```bash
docker compose up -d
```

**GPU Mode (with person detection GPU):**
```bash
docker compose --profile gpu up -d
```

**Full GPU Mode (with DeepStream):**
```bash
docker compose --profile gpu --profile deepstream up -d
```

5. **Access the application**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000/api/docs
- go2rtc: http://localhost:1984

6. **Login with default admin**
- Email: admin@personalhub.local (or your INIT_ADMIN_EMAIL)
- Password: ChangeThisPassword123! (or your INIT_ADMIN_PASSWORD)

## Project Structure

```
personal-hub/
├── frontend/                 # Next.js frontend application
│   ├── src/
│   │   ├── app/             # App Router pages
│   │   ├── components/      # React components
│   │   ├── hooks/           # Custom hooks
│   │   ├── lib/             # Utilities and API client
│   │   └── types/           # TypeScript types
│   └── Dockerfile
├── backend/                  # FastAPI backend application
│   ├── app/
│   │   ├── api/             # API endpoints
│   │   ├── core/            # Config and security
│   │   ├── db/              # Database models
│   │   ├── schemas/         # Pydantic schemas
│   │   └── services/        # Business logic
│   ├── alembic/             # Database migrations
│   └── Dockerfile
├── modules/                  # Plugin modules
│   ├── deepstream-camera-stream/
│   │   └── module.json      # Module manifest
│   └── person-detection/
│       └── module.json
├── config/
│   └── profile.yaml         # Landing page configuration
├── docker/
│   ├── nginx/               # Nginx reverse proxy
│   ├── go2rtc/              # Media relay
│   ├── deepstream/          # DeepStream service
│   └── person-detection/    # YOLO detection service
├── docker-compose.yml
├── .env.example
└── README.md
```

## Configuration

### Profile Configuration (Landing Page)

Edit `config/profile.yaml` to customize your landing page:

```yaml
profile:
  displayName: "Your Name"
  tagline: "Senior Full-Stack & MLOps Engineer"
  bio: "Your bio here..."
  avatarUrl: "/images/avatar.jpg"

theme:
  accentColor: "#6366f1"
  primaryGradient: "from-indigo-500 via-purple-500 to-pink-500"
  darkMode: true

socialLinks:
  github: "https://github.com/yourusername"
  linkedin: "https://linkedin.com/in/yourusername"

skills:
  - category: "Languages"
    items:
      - name: "Python"
        level: 95
```

### Camera Configuration

For the DeepStream module, configure your camera in `.env`:

```bash
DEFAULT_CAMERA_URL=rtsp://admin:password@192.168.1.100:554/stream1
CAMERA_NAME=main_camera
```

Or edit `docker/go2rtc/go2rtc.yaml` for multiple cameras:

```yaml
streams:
  camera_1:
    - "rtsp://user:pass@192.168.1.101:554/stream1"
  camera_2:
    - "rtsp://user:pass@192.168.1.102:554/stream1"
```

## Module System

### Adding a New Module

1. **Create module directory**
```bash
mkdir -p modules/my-module
```

2. **Create module manifest** (`modules/my-module/module.json`):
```json
{
  "id": "my-module",
  "name": "My Module",
  "description": "Description of my module",
  "version": "1.0.0",
  "tags": ["example", "demo"],
  "ui": {
    "path": "/modules/my-module",
    "icon": "Box",
    "nav_order": 30
  },
  "api": {
    "base_path": "/api/modules/my-module",
    "health_path": "/health"
  },
  "permissions_required": ["user"],
  "services": {
    "main": "my-module-service"
  },
  "config_schema": {
    "setting_1": {
      "type": "string",
      "default": "value",
      "description": "Setting description"
    }
  }
}
```

3. **Create Docker service** (if needed) in `docker/my-module/`

4. **Add to docker-compose.yml**:
```yaml
my-module-service:
  build:
    context: ./docker/my-module
  # ... configuration
```

5. **Create UI page** in `frontend/src/app/(dashboard)/modules/my-module/page.tsx`

6. **Restart and reload**:
```bash
docker compose restart backend
# Or use the admin UI to reload modules
```

### Module Manifest Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | string | Yes | Unique module identifier |
| name | string | Yes | Display name |
| description | string | No | Module description |
| version | string | Yes | Semantic version |
| tags | string[] | No | Categorization tags |
| ui.path | string | No | Frontend route path |
| ui.icon | string | No | Lucide icon name |
| ui.nav_order | number | No | Sidebar sort order |
| api.base_path | string | No | API route prefix |
| api.health_path | string | No | Health check endpoint |
| permissions_required | string[] | No | Required roles |
| services | object | No | Docker service mapping |
| config_schema | object | No | Configuration options |

## API Reference

### Authentication

```bash
# Login
POST /api/v1/auth/login
{
  "email": "user@example.com",
  "password": "password"
}

# Refresh token
POST /api/v1/auth/refresh
{
  "refresh_token": "..."
}

# Get current user
GET /api/v1/auth/me
Authorization: Bearer <access_token>
```

### Users (Admin)

```bash
# List users
GET /api/v1/users

# Create user
POST /api/v1/users
{
  "email": "new@example.com",
  "name": "New User",
  "password": "password123",
  "roles": ["user"]
}
```

### Modules

```bash
# List modules
GET /api/v1/modules

# Get module
GET /api/v1/modules/{module_id}

# Enable/disable module
POST /api/v1/modules/{module_id}/enable
POST /api/v1/modules/{module_id}/disable

# Check health
POST /api/v1/modules/{module_id}/health
```

## Production Deployment

### HTTPS with Nginx

1. **Generate SSL certificates** (using Let's Encrypt):
```bash
certbot certonly --standalone -d yourdomain.com
```

2. **Copy certificates**:
```bash
cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem docker/nginx/ssl/
cp /etc/letsencrypt/live/yourdomain.com/privkey.pem docker/nginx/ssl/
```

3. **Enable SSL in nginx config** - uncomment SSL sections in `docker/nginx/conf.d/default.conf`

4. **Start with production profile**:
```bash
docker compose --profile production up -d
```

### Environment Variables

For production, ensure these are set:

```bash
APP_ENV=production
DEBUG=false
JWT_SECRET_KEY=<strong-random-key>
MYSQL_PASSWORD=<strong-password>
CORS_ORIGINS=https://yourdomain.com
```

## Development

### Running Locally

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

### Database Migrations

```bash
cd backend

# Create migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Code Quality

**Backend:**
```bash
ruff check .
black .
mypy .
```

**Frontend:**
```bash
npm run lint
npm run format
```

## Troubleshooting

### GPU Not Detected

1. Verify nvidia-container-toolkit is installed:
```bash
nvidia-ctk --version
```

2. Check Docker GPU access:
```bash
docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi
```

### Camera Stream Not Working

1. Test RTSP URL directly:
```bash
ffprobe rtsp://user:pass@camera-ip:554/stream
```

2. Check go2rtc logs:
```bash
docker compose logs go2rtc
```

### Database Connection Issues

```bash
# Check MySQL is running
docker compose logs mysql

# Connect to MySQL
docker compose exec mysql mysql -u personalhub -p
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Support

- GitHub Issues: [Report bugs or request features](https://github.com/yourusername/personal-hub/issues)
- Documentation: [Full documentation](docs/README.md)
