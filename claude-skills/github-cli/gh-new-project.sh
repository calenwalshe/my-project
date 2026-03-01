#!/bin/bash
# gh-new-project.sh - Create new GitHub repo with initial structure
# Usage: gh-new-project.sh <project-name> [--private]

set -e

PROJECT_NAME="$1"
VISIBILITY="--public"

if [[ -z "$PROJECT_NAME" ]]; then
    echo "Usage: gh-new-project.sh <project-name> [--private]"
    exit 1
fi

if [[ "$2" == "--private" ]]; then
    VISIBILITY="--private"
fi

echo "Creating repository: $PROJECT_NAME ($VISIBILITY)"

# Create and clone repo
gh repo create "$PROJECT_NAME" $VISIBILITY --clone --description "Created by gh-new-project.sh"
cd "$PROJECT_NAME"

# Create initial structure
cat > README.md << EOF
# $PROJECT_NAME

Created on $(date +%Y-%m-%d)

## Description

TODO: Add project description

## Installation

\`\`\`bash
# TODO: Add installation instructions
\`\`\`

## Usage

\`\`\`bash
# TODO: Add usage examples
\`\`\`

## License

MIT
EOF

# Create .gitignore
cat > .gitignore << 'GITIGNORE'
# OS
.DS_Store
Thumbs.db

# Editor
.vscode/
.idea/
*.swp
*.swo

# Dependencies
node_modules/
venv/
__pycache__/

# Build
dist/
build/
*.egg-info/

# Environment
.env
.env.local
GITIGNORE

# Initial commit
git add .
git commit -m "Initial commit: project structure"
git push

echo ""
echo "✅ Repository created: https://github.com/$(gh api user --jq .login)/$PROJECT_NAME"
echo "📁 Local directory: $(pwd)"
