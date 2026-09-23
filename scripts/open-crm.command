#!/bin/zsh
set -euo pipefail
cd "${0:A:h}/.."
crm_compose=(docker compose -f docker-compose.yml -f docker-compose.mail.yml)
export PATH="$HOME/.docker/bin:$PATH"
# This launcher is for a local Docker engine, never a remote deployment.
crm_engine="${DOCKER_HOST:-$(docker context inspect --format '{{.Endpoints.docker.Host}}')}"
if [[ "$crm_engine" != unix://* ]]; then
  print 'Open CRM requires a local Docker engine.'
  exit 1
fi
docker info >/dev/null
"${crm_compose[@]}" up -d db redis mailpit backend celery-worker celery-beat
crm_ready=0
for attempt in {1..60}; do
  if curl -fsS http://localhost:8000/healthz/ >/dev/null 2>&1; then crm_ready=1; break; fi
  sleep 1
done
if [[ "$crm_ready" != 1 ]]; then print 'The CRM backend did not start.'; exit 1; fi
if ! curl -fsS http://localhost:5173/login >/dev/null 2>&1; then
  command -v pnpm >/dev/null || { print 'Start the frontend first, or add pnpm to PATH.'; exit 1; }
  (cd frontend && nohup pnpm dev --host 127.0.0.1 --port 5173 > "${TMPDIR:-/tmp/}crm-local-frontend.log" 2>&1 < /dev/null &!)
fi
crm_ready=0
for attempt in {1..60}; do
  if curl -fsS http://localhost:5173/login >/dev/null 2>&1; then crm_ready=1; break; fi
  sleep 1
done
if [[ "$crm_ready" != 1 ]]; then print 'The CRM interface did not start.'; exit 1; fi
# The opt-in exists only for this command; no web login bypass is enabled.
crm_login_url="$("${crm_compose[@]}" exec -T -e CRM_LOCAL_LOGIN=1 backend python manage.py local_login_link --email "${1:-admin@example.com}")"
if [[ "$crm_login_url" != http://localhost:5173/login/verify\?token=* ]]; then
  print 'The local sign-in URL did not match this CRM instance.'
  exit 1
fi
open "$crm_login_url"
unset crm_login_url
print 'CRM opened in your browser. Select your organization if asked.'
