#!/usr/bin/env bash
# Run ON the GCE VM (after SSH) to install/update the voice worker container.
set -euo pipefail

IMAGE="${VOICE_IMAGE:?Set VOICE_IMAGE to your Artifact Registry URL, e.g. asia-south1-docker.pkg.dev/PROJECT/regula/voice-worker:latest}"
ENV_FILE="${VOICE_ENV_FILE:-/etc/regula/voice.env}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE — create it from deploy/gcp/voice-worker.env.example"
  exit 1
fi

sudo mkdir -p /etc/regula
sudo apt-get update -qq
sudo apt-get install -y -qq docker.io
sudo systemctl enable --now docker

sudo docker pull "$IMAGE"
sudo docker rm -f regula-voice 2>/dev/null || true
sudo docker run -d \
  --name regula-voice \
  --restart unless-stopped \
  -p 8080:8080 \
  --env-file "$ENV_FILE" \
  "$IMAGE"

echo "Voice worker running. Logs: sudo docker logs -f regula-voice"
