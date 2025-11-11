# HCI Project - Docker Setup

This project includes Docker configuration for easy deployment and development.

## Prerequisites

- Docker (version 20.10 or higher)
- Docker Compose (version 1.29 or higher)

## Quick Start

### Option 1: Using Docker Compose (Recommended for Development)

1. Start both backend and frontend services:
```bash
docker-compose up
```

2. Access the application:
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:5000

3. Stop the services:
```bash
docker-compose down
```

### Option 2: Using Dockerfile (Production Build)

1. Build the Docker image:
```bash
docker build -t hci-project .
```

2. Run the container:
```bash
docker run -p 5000:5000 hci-project
```

3. Access the backend API at http://localhost:5000

## Development

### Rebuilding After Changes

If you make changes to dependencies (package.json or requirements.txt):
```bash
docker-compose down
docker-compose up --build
```

### Viewing Logs

```bash
# All services
docker-compose logs -f

# Backend only
docker-compose logs -f backend

# Frontend only
docker-compose logs -f frontend
```

### Accessing Container Shell

```bash
# Backend
docker exec -it hci-backend /bin/bash

# Frontend
docker exec -it hci-frontend /bin/sh
```

## Services

- **Backend**: Flask server running on port 5000
- **Frontend**: Vite development server running on port 5173

## Troubleshooting

### Port Already in Use
If ports 5000 or 5173 are already in use, modify the port mappings in `docker-compose.yml`:
```yaml
ports:
  - "5001:5000"  # Change 5001 to any available port
```

### Permission Issues
If you encounter permission issues, try running with sudo:
```bash
sudo docker-compose up
```

### Clearing Everything
To remove all containers, networks, and volumes:
```bash
docker-compose down -v
docker system prune -a
```
