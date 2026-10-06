# 🚀 FeedbackXLR8 - Production Deployment Guide

This guide walks you through deploying FeedbackXLR8 in a production environment.

---

## 📋 **Pre-Deployment Checklist**

### **1. Security**
- [ ] Change all default passwords in `.env`
- [ ] Generate strong `SESSION_SECRET_KEY` (32+ characters)
- [ ] Remove demo credentials or disable login gate
- [ ] Review file permissions (`.env` should be read-only)
- [ ] Ensure service account JSON files are **not** in git
- [ ] Set `APP_ENV=production`

### **2. Configuration**
- [ ] Update `AUTH_ADMIN_EMAIL` and `AUTH_ADMIN_PASSWORD`
- [ ] Configure `GOOGLE_SERVICE_ACCOUNT_FILE` if using Google Play sync
- [ ] Set appropriate `LOG_LEVEL` (WARNING or ERROR for production)
- [ ] Disable `ENABLE_SURGE_SIMULATION` if not needed
- [ ] Review `MAX_BATCH_SIZE` based on server resources

### **3. Infrastructure**
- [ ] Server with minimum 2GB RAM, 2 CPU cores
- [ ] Python 3.8+ installed
- [ ] HTTPS/SSL certificate configured
- [ ] Firewall rules configured (port 8501 or custom)
- [ ] Backup strategy for `data/` directory

---

## 🐳 **Docker Deployment** (Recommended)

### **Step 1: Create Dockerfile**

Already included in project root:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create logs directory
RUN mkdir -p logs data

# Expose port
EXPOSE 8501

# Run application
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### **Step 2: Create docker-compose.yml**

```yaml
version: '3.8'

services:
  feedbackxlr8:
    build: .
    container_name: feedbackxlr8
    restart: unless-stopped
    ports:
      - "8501:8501"
    env_file:
      - .env
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./service-account.json:/app/service-account.json:ro
    environment:
      - APP_ENV=production
      - LOG_LEVEL=WARNING
```

### **Step 3: Build and Run**

```bash
# Build image
docker-compose build

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

---

## 🌐 **Traditional Server Deployment**

### **Option 1: Systemd Service (Linux)**

Create `/etc/systemd/system/feedbackxlr8.service`:

```ini
[Unit]
Description=FeedbackXLR8 Review Intelligence Platform
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/feedbackxlr8
Environment="PATH=/opt/feedbackxlr8/venv/bin"
EnvironmentFile=/opt/feedbackxlr8/.env
ExecStart=/opt/feedbackxlr8/venv/bin/streamlit run app.py --server.port=8501 --server.address=0.0.0.0
Restart=always

[Install]
WantedBy=multi-user.target
```

**Enable and start:**

```bash
sudo systemctl enable feedbackxlr8
sudo systemctl start feedbackxlr8
sudo systemctl status feedbackxlr8
```

### **Option 2: PM2 (Node.js Process Manager)**

```bash
# Install PM2
npm install -g pm2

# Create ecosystem file
cat > ecosystem.config.js << EOF
module.exports = {
  apps: [{
    name: 'feedbackxlr8',
    script: 'streamlit',
    args: 'run app.py --server.port=8501',
    interpreter: '/path/to/venv/bin/python',
    cwd: '/path/to/feedbackxlr8',
    env: {
      APP_ENV: 'production',
      LOG_LEVEL: 'WARNING'
    }
  }]
}
EOF

# Start
pm2 start ecosystem.config.js

# Save and auto-restart on reboot
pm2 save
pm2 startup
```

---

## 🔒 **HTTPS/SSL Setup with Nginx**

### **Install Nginx**

```bash
sudo apt update
sudo apt install nginx certbot python3-certbot-nginx
```

### **Configure Nginx**

Create `/etc/nginx/sites-available/feedbackxlr8`:

```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com www.your-domain.com;

    # SSL Configuration (managed by certbot)
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Proxy to Streamlit
    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_read_timeout 86400;
    }
}
```

**Enable site and get SSL:**

```bash
sudo ln -s /etc/nginx/sites-available/feedbackxlr8 /etc/nginx/sites-enabled/
sudo nginx -t
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
sudo systemctl reload nginx
```

---

## 📊 **Monitoring & Logging**

### **Application Logs**

Logs are written to `logs/feedbackxlr8.log` by default.

**View logs:**
```bash
# Tail live logs
tail -f logs/feedbackxlr8.log

# Search for errors
grep ERROR logs/feedbackxlr8.log

# Last 100 lines
tail -n 100 logs/feedbackxlr8.log
```

### **Log Rotation**

Create `/etc/logrotate.d/feedbackxlr8`:

```
/opt/feedbackxlr8/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    missingok
    create 0640 www-data www-data
}
```

### **Health Monitoring**

Add a health check endpoint or use external monitoring:

```bash
# Simple uptime check
curl -f https://your-domain.com || echo "Site is down!"

# Use UptimeRobot, Pingdom, or similar service
```

---

## 💾 **Backup Strategy**

### **What to Backup**

1. **Data directory**: `data/`
2. **Configuration**: `.env`
3. **Service account keys**: `*.json`
4. **Logs (optional)**: `logs/`

### **Automated Backup Script**

Create `backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/backups/feedbackxlr8"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup data
tar -czf $BACKUP_DIR/data_$DATE.tar.gz data/

# Backup config (encrypted)
openssl enc -aes-256-cbc -salt -in .env -out $BACKUP_DIR/env_$DATE.enc -k "your-encryption-password"

# Keep only last 30 days
find $BACKUP_DIR -mtime +30 -delete

echo "Backup completed: $DATE"
```

**Schedule with cron:**

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * /opt/feedbackxlr8/backup.sh >> /var/log/feedbackxlr8_backup.log 2>&1
```

---

## 🔧 **Performance Tuning**

### **1. Increase File Descriptors**

Add to `/etc/security/limits.conf`:

```
www-data soft nofile 65536
www-data hard nofile 65536
```

### **2. Optimize Streamlit**

Create `.streamlit/config.toml`:

```toml
[server]
maxUploadSize = 200
enableCORS = false
enableXsrfProtection = true

[browser]
gatherUsageStats = false

[runner]
fastReruns = true
```

### **3. Database Optimization (if using PostgreSQL later)**

```sql
-- Increase shared buffers
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
```

---

## 🚨 **Troubleshooting**

### **Application Won't Start**

```bash
# Check logs
journalctl -u feedbackxlr8 -n 50

# Verify Python path
which python
python --version

# Test manually
source venv/bin/activate
streamlit run app.py
```

### **Port Already in Use**

```bash
# Find process using port 8501
sudo lsof -i :8501

# Kill process
kill -9 <PID>
```

### **High Memory Usage**

```bash
# Check memory
free -h

# Monitor process
top -p $(pgrep -f streamlit)

# Reduce batch size in .env
MAX_BATCH_SIZE=5000
```

### **Slow Performance**

1. Check `USE_TRANSFORMER=false` to use faster lexicon engine
2. Increase `CACHE_TTL_SECONDS`
3. Reduce `MAX_BATCH_SIZE`
4. Monitor CPU/RAM usage

---

## 🔐 **Security Hardening**

### **1. Firewall (UFW)**

```bash
sudo ufw allow 22/tcp  # SSH
sudo ufw allow 80/tcp  # HTTP
sudo ufw allow 443/tcp # HTTPS
sudo ufw enable
```

### **2. Fail2Ban (Brute Force Protection)**

```bash
sudo apt install fail2ban

# Configure for nginx
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
sudo systemctl restart fail2ban
```

### **3. Regular Updates**

```bash
# System updates
sudo apt update && sudo apt upgrade -y

# Python dependencies
pip install --upgrade -r requirements.txt
```

---

## 📈 **Scaling Considerations**

### **Horizontal Scaling**

- Use load balancer (Nginx, HAProxy)
- Deploy multiple instances
- Share `data/` via NFS or S3
- Use Redis for session storage

### **Vertical Scaling**

- Increase server resources
- Use faster SSD storage
- Optimize `MAX_BATCH_SIZE`

---

## 📞 **Support**

For production deployment support:
- Email: support@feedbackxlr8.io
- Issues: [GitHub Issues](https://github.com/yourusername/feedbackxlr8/issues)
- Docs: [README.md](README.md)

---

**Last Updated**: 2026-10-06
