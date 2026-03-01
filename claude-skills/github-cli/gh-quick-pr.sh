#!/bin/bash
# gh-quick-pr.sh - Quick PR workflow: stage, commit, push, create PR
# Usage: gh-quick-pr.sh "commit message" [--draft]

set -e

COMMIT_MSG="$1"
DRAFT_FLAG=""

if [[ -z "$COMMIT_MSG" ]]; then
    echo "Usage: gh-quick-pr.sh \"commit message\" [--draft]"
    exit 1
fi

if [[ "$2" == "--draft" ]]; then
    DRAFT_FLAG="--draft"
fi

# Get current branch
BRANCH=$(git branch --show-current)

if [[ "$BRANCH" == "main" || "$BRANCH" == "master" ]]; then
    echo "⚠️  You're on $BRANCH. Create a feature branch first:"
    echo "   git checkout -b feature/my-feature"
    exit 1
fi

echo "📝 Staging changes..."
git add .

echo "💾 Committing: $COMMIT_MSG"
git commit -m "$COMMIT_MSG"

echo "🚀 Pushing to origin/$BRANCH..."
git push -u origin "$BRANCH"

echo "📬 Creating PR..."
gh pr create --fill $DRAFT_FLAG

echo ""
echo "✅ PR created successfully!"
gh pr view --web
