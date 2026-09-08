# PRAMAAN deployment

The recommended SIH prototype layout does not require Docker:

```text
Vercel (optional React frontend)
              |
          HTTPS API
              |
AWS EC2: Nginx -> FastAPI -> PostgreSQL
                         |-> Redis -> Celery
                         |-> ML/Tesseract
                         |-> local document directory
```

For the quickest all-in-one deployment, Nginx can serve the built React files
from the same EC2 instance. For the cleaner split, deploy only the React frontend
to Vercel and keep every stateful or long-running service on EC2.

The frontend currently defaults to `VITE_USE_MOCK=true`. Authentication and the
backend/ML APIs remain available, but dashboard data stays mocked until the
frontend contracts are connected to the tender-scoped backend endpoints.

## 1. Create the EC2 host

Use Ubuntu 24.04 LTS, at least 2 vCPU and 8 GB RAM (for example `t3.large`), and
40 GB or more of encrypted gp3 EBS storage. For an India-based demonstration,
`ap-south-1` is normally the closest region.

Security-group inbound rules:

- TCP 22 from your own public IP only.
- TCP 80 from the internet during initial setup.
- TCP 443 from the internet after TLS is configured.
- Never expose PostgreSQL 5432, Redis 6379, backend 8000, or ML 8001.

Associate an Elastic IP if the instance will be addressed directly. When using
an Application Load Balancer, allow EC2 port 80 only from the load balancer's
security group.

## 2. Install native dependencies

Connect to the instance and run:

```bash
sudo apt update
sudo apt install -y \
  git nginx postgresql redis-server tesseract-ocr \
  python3 python3-venv python3-pip build-essential libgl1
sudo systemctl enable --now postgresql redis-server nginx
```

Node.js is needed on EC2 only when EC2 will also build and serve the frontend.
Install the current Node.js 22 LTS release and verify:

```bash
node --version
npm --version
```

## 3. Install the application

Until the integration branch is merged, clone that branch explicitly:

```bash
sudo useradd --system --home /opt/pramaan --shell /usr/sbin/nologin pramaan
sudo mkdir -p /opt/pramaan /var/lib/pramaan/documents /etc/pramaan
sudo chown "$USER":pramaan /opt/pramaan
sudo chown -R pramaan:pramaan /var/lib/pramaan

git clone --branch integrate/sih-backend \
  https://github.com/Pradeep-10x/BidCompliance.git /opt/pramaan
```

After the branch is merged, clone `main` instead.

Create isolated Python environments:

```bash
cd /opt/pramaan/backend
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

cd /opt/pramaan/ml-services
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
```

## 4. Create PostgreSQL credentials

Create the application role and database:

```bash
sudo -u postgres createuser pramaan
sudo -u postgres createdb --owner=pramaan pramaan
sudo -u postgres psql -c '\password pramaan'
```

Enter a long, URL-safe random password. Generate one with:

```bash
openssl rand -hex 32
```

## 5. Configure the services

Install the environment template:

```bash
sudo install -m 640 -o root -g pramaan \
  /opt/pramaan/deploy/backend.env.example /etc/pramaan/backend.env
sudoedit /etc/pramaan/backend.env
```

Replace both placeholder secrets and the example domain. The PostgreSQL password
must match the password created in the previous step. A minimal domain setup is:

```dotenv
POSTGRES_PASSWORD=YOUR_DATABASE_PASSWORD
SECRET_KEY=A_DIFFERENT_RANDOM_SECRET
TRUSTED_HOSTS=api.pramaan.example.com,localhost,127.0.0.1
CORS_ORIGINS=https://your-project.vercel.app
```

For an all-in-one EC2 deployment, use the frontend domain as both the trusted
host and CORS origin.

Install and start the systemd units:

```bash
sudo install -m 644 /opt/pramaan/deploy/systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now pramaan-ml pramaan-backend pramaan-worker
```

`pramaan-backend` runs `alembic upgrade head` before starting FastAPI.

Verify the services:

```bash
sudo systemctl status --no-pager pramaan-ml pramaan-backend pramaan-worker
curl http://127.0.0.1:8001/health
curl http://127.0.0.1:8000/ready
```

View logs with:

```bash
sudo journalctl -u pramaan-backend -u pramaan-worker -u pramaan-ml -f
```

## 6A. Serve the frontend from EC2

Build the current mock-backed dashboard:

```bash
cd /opt/pramaan/frontend
npm ci
VITE_API_BASE_URL=/api/v1 VITE_USE_MOCK=true npm run build
sudo mkdir -p /var/www/pramaan
sudo cp -a dist/. /var/www/pramaan/
```

Install Nginx configuration and replace `pramaan.example.com` with the real
domain before enabling it:

```bash
sudo install -m 644 /opt/pramaan/deploy/nginx/pramaan.conf \
  /etc/nginx/sites-available/pramaan
sudoedit /etc/nginx/sites-available/pramaan
sudo unlink /etc/nginx/sites-enabled/default
sudo ln -s /etc/nginx/sites-available/pramaan /etc/nginx/sites-enabled/pramaan
sudo nginx -t
sudo systemctl reload nginx
```

Check:

```bash
curl http://127.0.0.1/healthz
curl http://YOUR_EC2_IP/api/v1/openapi.json
```

## 6B. Serve the frontend from Vercel

Deploy the EC2 API first with a public HTTPS hostname such as
`https://api.pramaan.example.com`.

In Vercel:

1. Import the GitHub repository.
2. Set **Root Directory** to `frontend`.
3. Select the Vite framework preset.
4. Use `npm ci`, `npm run build`, and output directory `dist`.
5. Add the following production variables:

```dotenv
VITE_API_BASE_URL=https://api.pramaan.example.com/api/v1
VITE_USE_MOCK=true
```

6. Deploy and copy the exact Vercel production URL.
7. Add that URL to `/etc/pramaan/backend.env` on EC2:

```dotenv
CORS_ORIGINS=https://your-project.vercel.app
```

8. Restart the API:

```bash
sudo systemctl restart pramaan-backend pramaan-worker
```

Vite variables are embedded at build time, so changing either variable requires
a new Vercel deployment. Change `VITE_USE_MOCK` to `false` only after the
frontend/backend endpoint and response mappings are implemented.

## 7. Add HTTPS

For a single-instance prototype, install Certbot and let it update Nginx:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d pramaan.example.com
sudo certbot renew --dry-run
```

For an AWS-managed setup, put an Application Load Balancer in front of EC2,
configure target port 80 with health path `/healthz`, and attach an ACM
certificate to the HTTPS listener. Point the domain to the load balancer with a
Route 53 alias record.

After HTTPS works, remove HTTP origins from `CORS_ORIGINS`.

## 8. Updating the native deployment

Back up PostgreSQL before applying migrations:

```bash
sudo -u postgres pg_dump pramaan | gzip > "$HOME/pramaan-$(date +%F-%H%M).sql.gz"
cd /opt/pramaan
git pull --ff-only

backend/.venv/bin/pip install -r backend/requirements.txt
ml-services/.venv/bin/pip install -r ml-services/requirements.txt

cd frontend
npm ci
VITE_API_BASE_URL=/api/v1 VITE_USE_MOCK=true npm run build
sudo cp -a dist/. /var/www/pramaan/

sudo systemctl restart pramaan-ml pramaan-backend pramaan-worker
sudo nginx -t && sudo systemctl reload nginx
```

Also configure automatic encrypted EBS snapshots or AWS Backup. PostgreSQL and
uploaded documents are stateful data and must not rely on the EC2 instance alone.

## 9. Optional Docker fallback

Docker is no longer required by the primary deployment. The existing
`compose.yaml` and Dockerfiles are retained for reproducible local development or
an emergency all-in-one deployment:

```bash
cp .env.production.example .env
docker compose --env-file .env config --quiet
docker compose --env-file .env up -d --build
```

Never run `docker compose down -v` on an environment containing real data.
