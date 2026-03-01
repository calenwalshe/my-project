#!/bin/bash
# gh-release.sh - Create a GitHub release with optional assets
# Usage: gh-release.sh <version> [--notes "Release notes"] [asset1 asset2 ...]

set -e

VERSION="$1"
shift || true

if [[ -z "$VERSION" ]]; then
    echo "Usage: gh-release.sh <version> [--notes \"Release notes\"] [asset1 asset2 ...]"
    echo ""
    echo "Examples:"
    echo "  gh-release.sh v1.0.0"
    echo "  gh-release.sh v1.0.0 --notes \"Bug fixes and improvements\""
    echo "  gh-release.sh v1.0.0 dist/*.zip"
    exit 1
fi

# Parse arguments
NOTES=""
ASSETS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --notes)
            NOTES="$2"
            shift 2
            ;;
        *)
            ASSETS+=("$1")
            shift
            ;;
    esac
done

# Check if tag exists
if git rev-parse "$VERSION" >/dev/null 2>&1; then
    echo "⚠️  Tag $VERSION already exists"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "🏷️  Creating tag: $VERSION"
    git tag "$VERSION"
    git push origin "$VERSION"
fi

echo "📦 Creating release: $VERSION"

# Build release command
if [[ -n "$NOTES" ]]; then
    if [[ ${#ASSETS[@]} -gt 0 ]]; then
        gh release create "$VERSION" --notes "$NOTES" "${ASSETS[@]}"
    else
        gh release create "$VERSION" --notes "$NOTES"
    fi
else
    if [[ ${#ASSETS[@]} -gt 0 ]]; then
        gh release create "$VERSION" --generate-notes "${ASSETS[@]}"
    else
        gh release create "$VERSION" --generate-notes
    fi
fi

echo ""
echo "✅ Release $VERSION created!"
gh release view "$VERSION" --web
