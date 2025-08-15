# DuckDNS + Nginx Docker Setup

This setup allows you to expose webpages from your home computer using DuckDNS for dynamic DNS and Nginx as a reverse proxy.

## Setup Instructions

1. **Get a DuckDNS domain**:
   - Go to https://www.duckdns.org
   - Sign in and create a subdomain
   - Copy your token

2. **Configure environment**:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and add your DuckDNS subdomain and token.

3. **Start the containers**:
   ```bash
   docker-compose up -d
   ```

4. **Configure your router**:
   - Forward port 80 (and 443 for HTTPS) to your computer's IP address
   - Make sure your firewall allows these ports

## Directory Structure

- `nginx/conf.d/` - Main Nginx configuration files
- `nginx/sites-enabled/` - Individual site configurations
- `nginx/ssl/` - SSL certificates (for HTTPS)
- `www/` - Static web content
- `duckdns/config/` - DuckDNS configuration

## Adding a New Site

1. Create a new configuration file in `nginx/sites-enabled/`
2. Use the example configuration as a template
3. Restart Nginx: `docker-compose restart nginx`

## Proxying to Local Applications

To proxy requests to applications running on your host machine:
- Use `host.docker.internal` as the hostname
- Example: `proxy_pass http://host.docker.internal:3000;`

## SSL/HTTPS Setup

For HTTPS, you'll need SSL certificates. You can:
1. Use Let's Encrypt with Certbot
2. Use self-signed certificates for testing
3. Purchase certificates from a CA

## Commands

- Start: `docker-compose up -d`
- Stop: `docker-compose down`
- View logs: `docker-compose logs -f`
- Restart Nginx: `docker-compose restart nginx`