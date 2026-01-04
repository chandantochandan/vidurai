# Vidurai Proxy - Deployment Guide

Quick guide for deploying Vidurai Proxy to production.

## 📋 Prerequisites

- Python 3.10+
- OpenAI API key (for compression)
- AI provider API keys (Anthropic, OpenAI, Google)
- 512MB RAM minimum (1GB recommended)

## 🚀 Local Deployment

### 1. Clone and Setup
```bash
git clone https://github.com/chandantochandan/vidurai-proxy.git
cd vidurai-proxy

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure
```bash
cp .env.example .env
nano .env  # Add OPENAI_API_KEY
```

**Required:**
- `OPENAI_API_KEY` - For Vidurai compression (uses gpt-4o-mini)

**Optional:**
- `PROXY_PORT` - Override default port 8080
- `LOG_LEVEL` - Change from INFO to DEBUG
- `VIDURAI_COMPRESSION_THRESHOLD` - Change from 10 messages

### 3. Run
```bash
# Option A: Direct
python3 src/main.py

# Option B: Using script
./run.sh

# Option C: Background process
nohup python3 src/main.py > proxy.log 2>&1 &
```

Server runs on `http://localhost:8080`

### 4. Test
```bash
# Health check
curl http://localhost:8080/health

# Metrics
curl http://localhost:8080/metrics
```

### 5. Use with AI Tools
```bash
# Claude Code
export ANTHROPIC_BASE_URL=http://localhost:8080

# OpenAI SDK
export OPENAI_BASE_URL=http://localhost:8080/v1
```

## ☁️ Cloud Deployment

### Docker

**Dockerfile:**
```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["python3", "src/main.py"]
```

**Build and run:**
```bash
docker build -t vidurai-proxy .
docker run -p 8080:8080 -e OPENAI_API_KEY=your-key vidurai-proxy
```

### AWS EC2 / DigitalOcean / VPS
```bash
# 1. SSH into server
ssh user@your-server

# 2. Install dependencies
sudo apt update
sudo apt install python3 python3-pip python3-venv git -y

# 3. Clone and setup
git clone https://github.com/chandantochandan/vidurai-proxy.git
cd vidurai-proxy
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 4. Configure
cp .env.example .env
nano .env  # Add keys

# 5. Run as systemd service
sudo nano /etc/systemd/system/vidurai-proxy.service
```

**vidurai-proxy.service:**
```ini
[Unit]
Description=Vidurai Proxy Server
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/vidurai-proxy
Environment="PATH=/home/ubuntu/vidurai-proxy/.venv/bin"
ExecStart=/home/ubuntu/vidurai-proxy/.venv/bin/python3 src/main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

**Start service:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable vidurai-proxy
sudo systemctl start vidurai-proxy
sudo systemctl status vidurai-proxy
```

## 🔒 Security Considerations

### API Keys
- Never commit `.env` to git
- Use environment variables in production
- Rotate keys regularly

### Network
- Use HTTPS in production (add reverse proxy like nginx)
- Restrict access with firewall rules
- Consider authentication for public deployments

## 📊 Monitoring

### Health Check
```bash
curl http://localhost:8080/health
```

### Metrics
```bash
curl http://localhost:8080/metrics
```

### Logs
```bash
tail -f logs/proxy.log
```

## 🐛 Troubleshooting

See [README.md](README.md#troubleshooting) for common issues.

## 📞 Support

- GitHub: https://github.com/chandantochandan/vidurai-proxy
- Issues: https://github.com/chandantochandan/vidurai-proxy/issues
- Vidurai Core: https://github.com/chandantochandan/vidurai
