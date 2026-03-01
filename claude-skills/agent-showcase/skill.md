# Agent Showcase

Deploy and share web projects from agents. Mobile-optimized dashboard for quick review.

---

## Quick Deploy

```bash
# 1. Package your project (must include index.html)
tar czf project.tar.gz index.html styles.css app.js

# 2. Deploy (no auth required)
curl -X POST https://showcase.calenwalshe.com/deploy \
  -F "name=my-app" \
  -F "files=@project.tar.gz"

# 3. View at:
# https://showcase.calenwalshe.com/p/my-app/
```

---

## Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Dashboard (mobile-friendly grid of all projects) |
| `/p/{name}/` | GET | View deployed project |
| `/deploy` | POST | Deploy new project |
| `/delete/{name}` | GET | Delete a project |
| `/health` | GET | Health check |

---

## Deploy Request

**URL:** `https://showcase.calenwalshe.com/deploy`
**Method:** POST
**Content-Type:** multipart/form-data

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Project name (alphanumeric, hyphens, underscores) |
| `files` | file | Yes | tar.gz archive containing project files |

**Response:**
```json
{
  "success": true,
  "name": "my-app",
  "url": "/p/my-app/",
  "message": "Deployed to /p/my-app/"
}
```

---

## Requirements

- Project must include `index.html` (shown as "ready" badge on dashboard)
- Archive must be `.tar.gz` format
- Project name: letters, numbers, hyphens, underscores only
- Max file size: 50MB

---

## Example Workflow

```bash
# Build React app and deploy
npm run build
cd dist
tar czf ../app.tar.gz .
curl -X POST https://showcase.calenwalshe.com/deploy \
  -F "name=react-demo" \
  -F "files=@../app.tar.gz"
```

---

## Dashboard Features

- Mobile-optimized card grid
- Shows project name and last modified time
- "ready" badge when index.html exists
- Delete button (X) with confirmation
- Auto-refresh every 30 seconds

---

## URLs

| URL | Purpose |
|-----|---------|
| `https://showcase.calenwalshe.com/` | Dashboard |
| `https://showcase.calenwalshe.com/p/{name}/` | View project |
| `https://showcase.calenwalshe.com/health` | Health check |

---

## Troubleshooting

**Deploy fails with "Invalid project name"**
- Use only letters, numbers, hyphens, underscores
- No spaces or special characters

**Project shows "no index" badge**
- Ensure `index.html` is in the root of the archive
- Check tar was created in the correct directory

**File too large**
- Max upload is 50MB
- Compress images or split into smaller projects
