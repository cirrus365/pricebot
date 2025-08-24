# Docker Setup for Nifty Bot

This directory contains Docker configuration files for containerizing the Nifty Bot application.

## Prerequisites

- Docker Engine 20.10+ installed
- Docker Compose 2.0+ installed (optional, for using docker-compose)
- A configured `.env` file in the project root

## Building the Docker Image

### Method 1: Using Docker directly

From the project root directory:

```bash
# Build the image
docker build -f Docker/Dockerfile -t nifty-bot:latest .

# Or from within the Docker directory
cd Docker
docker build -f Dockerfile -t nifty-bot:latest ..
```

### Method 2: Using Docker Compose

From the project root directory:

```bash
# Build and start the container
docker-compose -f Docker/docker-compose.yml up --build

# Run in detached mode (background)
docker-compose -f Docker/docker-compose.yml up -d --build

# Or from within the Docker directory
cd Docker
docker-compose up --build
```

## Running the Container

### Using Docker directly:

```bash
# Run with .env file
docker run --env-file .env --name nifty-bot nifty-bot:latest

# Run in detached mode with auto-restart
docker run -d --restart unless-stopped --env-file .env --name nifty-bot nifty-bot:latest

# Run with port mapping for Twilio webhooks
docker run -d --restart unless-stopped --env-file .env -p 5000:5000 --name nifty-bot nifty-bot:latest
```

### Using Docker Compose:

```bash
# Start the services
docker-compose -f Docker/docker-compose.yml up

# Stop the services
docker-compose -f Docker/docker-compose.yml down

# View logs
docker-compose -f Docker/docker-compose.yml logs -f

# Restart the service
docker-compose -f Docker/docker-compose.yml restart
```

## Environment Variables

The container expects environment variables to be provided via:
- An `.env` file (recommended)
- Docker run `-e` flags
- Docker Compose environment section

Make sure your `.env` file is properly configured before running the container.

## Volumes

The Docker setup includes a named volume `bot-data` for persisting any data the bot might need to store. This ensures data persistence across container restarts.

## Networking

- If using Twilio integrations (WhatsApp, Messenger, Instagram), uncomment the ports section in `docker-compose.yml` to expose port 5000
- The bot runs in a bridge network named `bot-network` for isolation

## Security Notes

- The container runs as a non-root user (`botuser`) for security
- Sensitive files like `.env` are excluded via `.dockerignore`
- The image is based on Python slim for a smaller attack surface

## Troubleshooting

### Container won't start
- Check logs: `docker logs nifty-bot`
- Verify `.env` file exists and is properly formatted
- Ensure all required environment variables are set

### Permission issues
- The container runs as UID 1000 by default
- Adjust the Dockerfile if you need a different UID

### Build failures
- Ensure you're building from the project root directory
- Check that all required files are present
- Try clearing Docker cache: `docker build --no-cache -f Docker/Dockerfile .`

## Updating the Image

When you update the bot code:

```bash
# Rebuild the image
docker-compose -f Docker/docker-compose.yml build --no-cache

# Restart with new image
docker-compose -f Docker/docker-compose.yml up -d
```

## Resource Limits

To add resource limits, modify the `docker-compose.yml`:

```yaml
services:
  nifty-bot:
    # ... other config ...
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
```
