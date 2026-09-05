---
name: render-server-wakeup
description: >-
  Provides the implementation plan, prompt, and step-by-step procedure to set up automated GitHub Actions 
  keep-alive pings and frontend cold-start warmup UI for Render-hosted backend services (render-server-wakeup).
  Use whenever the user asks for render-server-wakeup or wants to keep a Render free tier server active and warm.
---

# Render Backend Keep-Alive & Cold-Start Warmup

This skill provides the reusable blueprint and procedure to prevent Render free-tier web services from sleeping, and to handle initial load latency smoothly in client applications.

## Overview
Render free-tier web services automatically spin down after 15 minutes of inactivity. When a request arrives after being idle, Render takes ~30–60 seconds to boot up the container ("cold start").

This skill implements a 2-part solution:
1. **Automated Ping (GitHub Actions)**: Pings `GET /health` every 10 minutes to prevent Render from sleeping.
2. **Frontend Pre-flight Warmup (React / Web App)**: Pings `GET /health` on initial load and displays a floating "Waking up server..." status banner if cold-boot latency occurs.

---

## Step 1: Backend Health Check
Ensure the backend API has a simple, fast health check endpoint:

```python
# FastAPI Example
@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
```

---

## Step 2: GitHub Actions Keep-Alive Workflow
Create `.github/workflows/keep-alive.yml` in the project repository:

```yaml
name: Render Backend Keep-Alive

on:
  schedule:
    # Runs every 10 minutes to keep Render free tier awake
    - cron: '*/10 * * * *'
  workflow_dispatch:

jobs:
  ping-backend:
    runs-on: ubuntu-latest
    steps:
      - name: Ping Health Endpoint
        run: |
          URL="${{ secrets.RENDER_BACKEND_URL }}"
          if [ -z "$URL" ]; then
            echo "RENDER_BACKEND_URL secret not set. Please set it in GitHub repo settings."
            exit 1
          fi
          HEALTH_URL="${URL%/}/health"
          echo "Pinging backend health endpoint: $HEALTH_URL"
          STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 30 "$HEALTH_URL")
          echo "HTTP Status Code: $STATUS"
```

---

## Step 3: Frontend Warmup Toast Component
Create a floating health check banner component (e.g. `ServerWarmupBanner.jsx`):

```jsx
import { useState, useEffect } from "react";

export default function ServerWarmupBanner({ apiBaseUrl }) {
  const [status, setStatus] = useState("idle"); // 'idle' | 'warming' | 'ready' | 'hidden'

  useEffect(() => {
    const healthUrl = `${apiBaseUrl.replace(/\/api\/v1\/?$/, "")}/health`;
    let isMounted = true;

    const timerId = setTimeout(() => {
      if (isMounted && status === "idle") {
        setStatus("warming");
      }
    }, 1800);

    fetch(healthUrl)
      .then((res) => {
        if (res.ok && isMounted) {
          clearTimeout(timerId);
          setStatus("ready");
          setTimeout(() => { if (isMounted) setStatus("hidden"); }, 3000);
        }
      })
      .catch(() => {});

    return () => {
      isMounted = false;
      clearTimeout(timerId);
    };
  }, [apiBaseUrl]);

  if (status === "idle" || status === "hidden") return null;

  return (
    <div className={`warmup-banner warmup-banner--${status}`}>
      {status === "warming" ? "⚡ Waking up cloud backend server (Render free tier may take ~30s)..." : "✅ Server active and ready!"}
    </div>
  );
}
```

---

## Reusable AI Master Prompt

When setting up this feature in any external project, use this prompt:

> "Set up a Render keep-alive and cold-start warmup system for this full-stack project.
> 1. Add a `.github/workflows/keep-alive.yml` workflow running every 10 mins (`cron: '*/10 * * * *'`) that pings `<BACKEND_URL>/health`.
> 2. Create a frontend `ServerWarmupBanner` component that pings `/health` on app mount and shows a non-intrusive 'Waking up backend server...' message if response takes > 1.8s.
> 3. Verify the setup with `npm run build` and test the workflow."
