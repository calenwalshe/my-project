# Deploy App to Showcase

Deploy web applications to the Agent Showcase platform for viewing and sharing.

---

## When to Use

Use this skill when:
- User says "deploy an app", "deploy this", "push to showcase"
- Agent has generated HTML/CSS/JS that should be viewable
- User wants to share work via a URL

---

## Quick Deploy (Single Command)

```bash
# From project directory containing index.html
tar czf /tmp/deploy.tar.gz . && \
curl -s -X POST https://showcase.calenwalshe.com/deploy \
  -F "name=PROJECT_NAME" \
  -F "files=@/tmp/deploy.tar.gz" && \
rm /tmp/deploy.tar.gz
```

Replace `PROJECT_NAME` with a descriptive name (letters, numbers, hyphens, underscores only).

---

## Best Practices

### 1. Project Structure

```
project/
├── index.html      # REQUIRED - entry point
├── styles.css      # Optional - styling
├── app.js          # Optional - JavaScript
├── assets/         # Optional - images, fonts
│   ├── logo.png
│   └── icon.svg
└── data/           # Optional - JSON data files
    └── config.json
```

### 2. Naming Conventions

| Good Names | Bad Names |
|------------|-----------|
| `weather-app` | `my app` (spaces) |
| `dashboard_v2` | `dashboard@v2` (special chars) |
| `user-analytics` | `../../etc` (path traversal) |

### 3. File Size Limits

- **Max upload:** 50MB
- **Recommendation:** Keep under 10MB for fast deploys
- Compress images before including
- Minify JS/CSS for production

### 4. Self-Contained Apps

Apps should be self-contained with relative paths:

```html
<!-- GOOD - relative paths -->
<link rel="stylesheet" href="styles.css">
<script src="app.js"></script>
<img src="assets/logo.png">

<!-- BAD - absolute paths that won't work -->
<link rel="stylesheet" href="/styles.css">
<script src="http://localhost:3000/app.js"></script>
```

### 5. No Server-Side Code

The showcase serves static files only. For dynamic features:
- Use client-side JavaScript
- Fetch from external APIs
- Store state in localStorage

---

## Deployment Workflow

### Step 1: Prepare Files

Ensure you have an `index.html` in your project root:

```bash
# Check for required file
ls index.html || echo "ERROR: No index.html found"
```

### Step 2: Create Archive

```bash
# From project directory
tar czf /tmp/deploy.tar.gz .

# Verify contents
tar tzf /tmp/deploy.tar.gz | head -10
```

### Step 3: Deploy

```bash
curl -s -X POST https://showcase.calenwalshe.com/deploy \
  -F "name=my-project" \
  -F "files=@/tmp/deploy.tar.gz"
```

**Success Response:**
```json
{
  "success": true,
  "name": "my-project",
  "url": "/p/my-project/",
  "message": "Deployed to /p/my-project/"
}
```

### Step 4: Verify

```bash
# Check it's accessible
curl -s -I https://showcase.calenwalshe.com/p/my-project/ | head -1

# Open in browser
open https://showcase.calenwalshe.com/p/my-project/
```

---

## Common Patterns

### Deploy React/Vue/Vite Build

```bash
npm run build
cd dist
tar czf /tmp/app.tar.gz .
curl -s -X POST https://showcase.calenwalshe.com/deploy \
  -F "name=react-app" \
  -F "files=@/tmp/app.tar.gz"
```

### Deploy Single HTML File

```bash
# Create minimal project structure
mkdir -p /tmp/deploy-temp
cp my-page.html /tmp/deploy-temp/index.html
cd /tmp/deploy-temp
tar czf /tmp/deploy.tar.gz .
curl -s -X POST https://showcase.calenwalshe.com/deploy \
  -F "name=my-page" \
  -F "files=@/tmp/deploy.tar.gz"
rm -rf /tmp/deploy-temp
```

### Deploy with Assets

```bash
# Ensure all assets use relative paths
mkdir -p /tmp/deploy-temp
cp index.html styles.css app.js /tmp/deploy-temp/
cp -r images /tmp/deploy-temp/
cd /tmp/deploy-temp
tar czf /tmp/deploy.tar.gz .
curl -s -X POST https://showcase.calenwalshe.com/deploy \
  -F "name=full-app" \
  -F "files=@/tmp/deploy.tar.gz"
rm -rf /tmp/deploy-temp
```

---

## Update Existing Deployment

Deploying with the same name overwrites the previous version:

```bash
# Just deploy again with same name
curl -s -X POST https://showcase.calenwalshe.com/deploy \
  -F "name=existing-project" \
  -F "files=@/tmp/deploy.tar.gz"
```

---

## Delete Deployment

```bash
# Via curl
curl -s https://showcase.calenwalshe.com/delete/project-name

# Or use the dashboard
open https://showcase.calenwalshe.com/
# Click the X on the project card
```

---

## Troubleshooting

### "Invalid project name"
- Use only: letters, numbers, hyphens (`-`), underscores (`_`)
- No spaces or special characters

### "No files uploaded"
- Ensure `-F "files=@..."` has the `@` symbol
- Check the tar.gz file exists

### Project shows "no index" badge
- Add `index.html` to the root of your archive
- Check tar was created from the correct directory

### 404 on deployed project
- Wait a few seconds after deploy
- Check the URL matches the project name exactly

### Files not loading (CSS/JS)
- Use relative paths, not absolute
- Check file names match exactly (case-sensitive)

---

## URLs Reference

| URL | Purpose |
|-----|---------|
| `https://showcase.calenwalshe.com/` | Dashboard (view all) |
| `https://showcase.calenwalshe.com/p/{name}/` | View project |
| `https://showcase.calenwalshe.com/deploy` | Deploy endpoint |
| `https://showcase.calenwalshe.com/health` | Health check |
