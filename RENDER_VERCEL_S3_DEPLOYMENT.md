# PRAMAAN: Render + Vercel + S3 deployment

This is the lowest-maintenance SIH prototype topology:

```text
Vercel React frontend
        |
        v
Render FastAPI web service --> Render Postgres
        |
        v
Render ML/Tesseract web service

FastAPI <--> private AWS S3 bucket
```

Celery and Redis are intentionally not deployed for the initial prototype. Use
the synchronous `documents/upload` and `documents/{document_id}/process` route
pair. They store the original in S3 and send its bytes to ML over HTTPS.

Cloudflare R2 can replace AWS S3 without changing the application flow because
R2 exposes an S3-compatible API. Use
`deploy/render/backend-r2.env.example`, set the R2 endpoint, set the region to
`auto`, and set `STORAGE_SERVER_SIDE_ENCRYPTION=none`. R2 encrypts stored
objects automatically and does not accept AWS's standard SSE upload header.

## 1. AWS safety and S3

Create AWS Budget email alerts at USD 1 and USD 5 before provisioning anything.

Create a general-purpose S3 bucket in `ap-south-1`:

- keep all Block Public Access settings enabled;
- keep ACLs disabled;
- enable SSE-S3 default encryption;
- add a lifecycle rule that expires demo documents after 30 days.

Create a programmatic IAM user without console access. Replace the bucket name
in this bucket-scoped policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": "arn:aws:s3:::YOUR_BUCKET"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
      "Resource": "arn:aws:s3:::YOUR_BUCKET/*"
    }
  ]
}
```

Do not configure S3 CORS. The browser talks to FastAPI, not directly to S3.

## 2. Render Postgres

Create one Free Render Postgres database in the same Render region as the API.
Save its internal hostname, port, database, username, and password. Free Render
Postgres expires after 30 days, so create it close to the demo and export any
data that must survive.

## 3. Render ML web service

Create a Free Web Service connected to the GitHub repository:

```text
Branch: integrate/sih-backend
Root Directory: ml-services
Runtime: Docker
Health Check Path: /health
```

The existing Dockerfile installs Tesseract. Generate a service secret with
`openssl rand -hex 32` and add `ML_SHARED_SECRET` using
`deploy/render/ml.env.example` as the template. Keep the resulting public HTTPS
URL. Confirm that `/health` reports `ocr_engine_available: true`.

## 4. Render FastAPI web service

Create a second Free Web Service:

```text
Branch: integrate/sih-backend
Root Directory: backend
Runtime: Python
Build Command: pip install --upgrade pip && pip install -r requirements.txt
Start Command: alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips='*'
Health Check Path: /ready
```

Copy every variable in `deploy/render/backend.env.example` into Render and
replace its placeholders. The backend and ML `ML_SHARED_SECRET` values must be
identical. Do not add Redis or Celery services for the prototype.

Confirm these endpoints:

```text
https://YOUR_API.onrender.com/ready
https://YOUR_API.onrender.com/docs
https://YOUR_API.onrender.com/api/v1/openapi.json
```

## 5. Vercel frontend

Import the GitHub repository and configure:

```text
Branch: integrate/sih-backend
Root Directory: frontend
Framework: Vite
Install Command: npm ci
Build Command: npm run build
Output Directory: dist
```

Add these production variables:

```dotenv
VITE_API_BASE_URL=https://YOUR_API.onrender.com/api/v1
VITE_USE_MOCK=true
```

Deploy, copy the exact `https://....vercel.app` URL, set it as `CORS_ORIGINS`
on the Render API, and redeploy the API. Set `VITE_USE_MOCK=false` only after
the remaining frontend response mappings are connected.

## 6. End-to-end check

Wake the two free Render services before testing:

```bash
curl -fsS https://YOUR_ML.onrender.com/health
curl -fsS https://YOUR_API.onrender.com/ready
```

Then run from a local clone with `jq` installed:

```bash
backend/scripts/demo_smoke.sh \
  /absolute/path/to/tender.pdf \
  /absolute/path/to/udyam.png \
  https://YOUR_API.onrender.com/api/v1
```

Free Render web services sleep after 15 idle minutes. Wake both services a few
minutes before presenting and use small, known-good demo documents.
