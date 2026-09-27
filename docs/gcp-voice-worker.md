# Voice worker on Google Cloud (Compute Engine)

Run the LiveKit **voice worker** on a small GCE VM with **more RAM than Render free (512MB)**. Keep **Vercel** (UI) and **Render** (API) as they are; only move `voice_worker`.

## Why GCE (not Cloud Run)

The worker is a **long-lived** LiveKit agent process (`python main.py start`), not a short HTTP request. **Compute Engine + Docker** matches how Render runs it, with a machine size you control.

| Machine | RAM | Rough cost | Regula voice |
|---------|-----|------------|----------------|
| `e2-micro` | 1 GB | Free tier in select US regions only | Tight; consider `VOICE_TURN_DETECTION=stt` (future) |
| **`e2-small`** (default script) | 2 GB | ~\$12/mo if not covered by credits | **Recommended** |
| Render free | 512 MB | \$0 | OOM under load |

Billing must be enabled on GCP (free trial credits often cover the first months).

## Architecture

```text
Browser → Vercel → Render API
Browser → LiveKit Cloud ← voice worker on GCE (outbound WebRTC)
Worker  → Render API (REGULA_BACKEND_URL)
```

Only **one** worker should register as `LIVEKIT_AGENT_NAME=regula-voice`. Suspend or delete **Render `regula-agent-voice`** after GCP works.

## Prerequisites

1. [Google Cloud SDK (`gcloud`)](https://cloud.google.com/sdk/docs/install) installed and logged in:

   ```bash
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```

2. Same secrets as local voice: **LiveKit** (`LIVEKIT_*`), **Groq** (`GROQ_API_KEY`), backend URL.

3. Repo cloned locally.

## One-command provision (from repo root)

```bash
chmod +x deploy/gcp/provision-voice-gce.sh deploy/gcp/vm-install-voice.sh

# Optional overrides
export GCP_REGION=asia-south1          # Mumbai — good latency from India
export GCP_ZONE=asia-south1-a
export GCP_MACHINE_TYPE=e2-small

./deploy/gcp/provision-voice-gce.sh
```

This will:

- Enable Compute, Artifact Registry, Cloud Build APIs  
- Create Docker repo `regula` (if missing)  
- Build `docker/voice.Dockerfile` via Cloud Build and push `voice-worker:latest`  
- Create VM `regula-voice-worker` and open **TCP 8080** for wake/health  

## Configure env on the VM

SSH in:

```bash
gcloud compute ssh regula-voice-worker --zone=asia-south1-a
```

Create env file (secrets stay on the VM only):

```bash
sudo mkdir -p /etc/regula
sudo nano /etc/regula/voice.env
```

Use `deploy/gcp/voice-worker.env.example` as a template. Required:

- `REGULA_BACKEND_URL=https://regula-agent-api.onrender.com`  
- `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`  
- `GROQ_API_KEY`  
- `PORT=8080`, `OTEL_SDK_DISABLED=true`  

Do **not** set `RENDER=true` on GCP (production worker mode uses `python main.py start`).

Install/start container:

```bash
export VOICE_IMAGE=asia-south1-docker.pkg.dev/YOUR_PROJECT/regula/voice-worker:latest
# Copy vm-install-voice.sh to the VM, or paste from the repo:
sudo bash /path/to/vm-install-voice.sh
```

Check logs:

```bash
sudo docker logs -f regula-voice
```

You should see `Regula voice worker joining room=...` when you click **Voice** on the site.

## Point the frontend at GCP (wake URL)

On **Render free**, the UI wakes a sleeping worker. A GCE VM is always on; a quick HTTP GET still helps confirm the port is up.

1. Note the VM **external IP** (from `provision-voice-gce.sh` output or GCP console).  
2. In **Vercel → regula-agent → Environment Variables**, add:

   | Name | Value |
   |------|--------|
   | `VITE_VOICE_WAKE_URL` | `http://YOUR_VM_IP:8080/` |

3. Redeploy Vercel.

If `VITE_VOICE_WAKE_URL` is set, production uses it instead of Render voice wake URLs.

## Updates after code changes

From your laptop (repo root):

```bash
gcloud builds submit . --config deploy/gcp/cloudbuild.yaml \
  --substitutions=_REGION=asia-south1
```

On the VM:

```bash
export VOICE_IMAGE=asia-south1-docker.pkg.dev/YOUR_PROJECT/regula/voice-worker:latest
sudo bash vm-install-voice.sh
```

## Troubleshooting

| Issue | Check |
|--------|--------|
| Agent never joins | LiveKit keys match API on Render; only one worker named `regula-voice` |
| OOM on `e2-micro` | Switch to `e2-small` or run worker locally |
| No speech | Tap **Tap to hear Regula speak** in UI (browser autoplay) |
| Firewall | Tag `regula-voice`, rule `tcp:8080` |

## Optional: Secret Manager

For production, store `GROQ_API_KEY` and LiveKit secrets in [Secret Manager](https://cloud.google.com/secret-manager) and inject them in `vm-install-voice.sh` instead of a flat env file.

## Related

- Local worker: `docs/voice.md`  
- Render deployment: `docs/deployment.md`  
