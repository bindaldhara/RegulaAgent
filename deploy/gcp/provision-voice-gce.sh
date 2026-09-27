#!/usr/bin/env bash
# One-time GCP setup from your laptop (requires gcloud CLI + billing enabled).
set -euo pipefail

PROJECT_ID="${GCP_PROJECT:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${GCP_REGION:-asia-south1}"
ZONE="${GCP_ZONE:-asia-south1-a}"
REPOSITORY="${GCP_ARTIFACT_REPO:-regula}"
MACHINE_TYPE="${GCP_MACHINE_TYPE:-e2-small}"
INSTANCE_NAME="${GCP_VOICE_INSTANCE:-regula-voice-worker}"

if [[ -z "$PROJECT_ID" || "$PROJECT_ID" == "(unset)" ]]; then
  echo "Set GCP_PROJECT or run: gcloud config set project YOUR_PROJECT_ID"
  exit 1
fi

echo "Project: $PROJECT_ID  Region: $REGION  Zone: $ZONE  Machine: $MACHINE_TYPE"

gcloud config set project "$PROJECT_ID"
gcloud services enable compute.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com --quiet

if ! gcloud artifacts repositories describe "$REPOSITORY" --location="$REGION" &>/dev/null; then
  gcloud artifacts repositories create "$REPOSITORY" \
    --repository-format=docker \
    --location="$REGION" \
    --description="RegulaAgent containers"
fi

gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
gcloud builds submit "$ROOT" --config="$ROOT/deploy/gcp/cloudbuild.yaml" \
  --substitutions="_REGION=${REGION}"

IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/voice-worker:latest"

if gcloud compute instances describe "$INSTANCE_NAME" --zone="$ZONE" &>/dev/null; then
  echo "Instance $INSTANCE_NAME already exists. SSH in and run vm-install-voice.sh with VOICE_IMAGE=$IMAGE"
  exit 0
fi

gcloud compute instances create "$INSTANCE_NAME" \
  --zone="$ZONE" \
  --machine-type="$MACHINE_TYPE" \
  --boot-disk-size=20GB \
  --tags=regula-voice \
  --metadata=google-logging-enabled=true

gcloud compute firewall-rules create regula-voice-http \
  --allow=tcp:8080 \
  --target-tags=regula-voice \
  --description="Wake/health for Regula voice worker" \
  2>/dev/null || true

EXTERNAL_IP="$(gcloud compute instances describe "$INSTANCE_NAME" --zone="$ZONE" --format='get(networkInterfaces[0].accessConfigs[0].natIP)')"
echo ""
echo "VM created: $INSTANCE_NAME"
echo "External IP: $EXTERNAL_IP"
echo ""
echo "Next steps:"
echo "  1. gcloud compute ssh $INSTANCE_NAME --zone=$ZONE"
echo "  2. sudo mkdir -p /etc/regula && sudo nano /etc/regula/voice.env"
echo "     (paste secrets from deploy/gcp/voice-worker.env.example + your LiveKit/Groq keys)"
echo "  3. On the VM:"
echo "       export VOICE_IMAGE=$IMAGE"
echo "       curl -sSL https://raw.githubusercontent.com/bindaldhara/RegulaAgent/main/deploy/gcp/vm-install-voice.sh | bash"
echo "     Or copy deploy/gcp/vm-install-voice.sh from the repo and run it."
echo "  4. Vercel env: VITE_VOICE_WAKE_URL=http://${EXTERNAL_IP}:8080/"
echo "  5. Optional: stop Render regula-agent-voice so only one worker registers as regula-voice."
