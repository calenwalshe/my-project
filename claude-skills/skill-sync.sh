#!/bin/bash
# skill-sync.sh - Sync Claude skills between OD and Mac via Google Drive
#
# Architecture:
#   OD: ~/.claude/skills/ <--rsync--> ~/gdrive/skills/ <--gdrive--> Mac: ~/.claude/skills/
#
# Usage:
#   skill-sync push              # Push local skills to gdrive hub
#   skill-sync pull              # Pull skills from gdrive hub to local
#   skill-sync status            # Show sync status and conflicts
#   skill-sync resolve <skill>   # Resolve a conflict interactively

set -euo pipefail

# Detect environment
if [[ -d "/home/calenwalshe" ]]; then
    ENV="od"
    SKILLS_DIR="$HOME/.claude/skills"
    GDRIVE_SKILLS="$HOME/gdrive/skills"
    MANIFEST="$GDRIVE_SKILLS/.manifest-od.json"
else
    ENV="mac"
    SKILLS_DIR="$HOME/.claude/skills"
    GDRIVE_SKILLS="$HOME/Library/CloudStorage/GoogleDrive-calenwalshe@meta.com/My Drive/claude/skills"
    MANIFEST="$GDRIVE_SKILLS/.manifest-mac.json"
fi

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_ok() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Get list of syncable skills (directories only, no symlinks, no hidden)
get_local_skills() {
    find "$SKILLS_DIR" -maxdepth 1 -type d ! -name '.*' ! -name 'skills' -printf '%f\n' 2>/dev/null | sort || \
    ls -d "$SKILLS_DIR"/*/ 2>/dev/null | xargs -I{} basename {} | sort
}

# Get skills from gdrive hub
get_hub_skills() {
    find "$GDRIVE_SKILLS" -maxdepth 1 -type d ! -name '.*' ! -name 'skills' -printf '%f\n' 2>/dev/null | sort || \
    ls -d "$GDRIVE_SKILLS"/*/ 2>/dev/null | xargs -I{} basename {} | sort
}

# Get mtime of a skill (newest file inside)
get_skill_mtime() {
    local dir="$1"
    if [[ -d "$dir" ]]; then
        find "$dir" -type f -exec stat -f %m {} \; 2>/dev/null | sort -rn | head -1 || \
        find "$dir" -type f -exec stat -c %Y {} \; 2>/dev/null | sort -rn | head -1 || \
        echo 0
    else
        echo 0
    fi
}

# Create/update manifest
update_manifest() {
    local skills
    skills=$(get_local_skills)

    echo "{" > "$MANIFEST"
    echo "  \"env\": \"$ENV\"," >> "$MANIFEST"
    echo "  \"updated\": \"$(date -Iseconds)\"," >> "$MANIFEST"
    echo "  \"skills\": {" >> "$MANIFEST"

    local first=true
    for skill in $skills; do
        local mtime=$(get_skill_mtime "$SKILLS_DIR/$skill")
        if [[ "$first" == "true" ]]; then
            first=false
        else
            echo "," >> "$MANIFEST"
        fi
        echo -n "    \"$skill\": {\"mtime\": $mtime}" >> "$MANIFEST"
    done

    echo "" >> "$MANIFEST"
    echo "  }" >> "$MANIFEST"
    echo "}" >> "$MANIFEST"

    log_ok "Updated manifest: $MANIFEST"
}

# Push local skills to gdrive hub
cmd_push() {
    log_info "Pushing skills from $ENV to gdrive hub..."

    local skills
    skills=$(get_local_skills)

    local count=0
    for skill in $skills; do
        # Skip symlinks
        if [[ -L "$SKILLS_DIR/$skill" ]]; then
            log_warn "Skipping symlink: $skill"
            continue
        fi

        if [[ -d "$SKILLS_DIR/$skill" ]]; then
            log_info "Syncing: $skill"
            rsync -av --delete "$SKILLS_DIR/$skill/" "$GDRIVE_SKILLS/$skill/"
            ((count++))
        fi
    done

    update_manifest
    log_ok "Pushed $count skills to gdrive hub"
}

# Pull skills from gdrive hub to local
cmd_pull() {
    log_info "Pulling skills from gdrive hub to $ENV..."

    local hub_skills
    hub_skills=$(get_hub_skills)

    local count=0
    for skill in $hub_skills; do
        # Skip if local has symlink with same name
        if [[ -L "$SKILLS_DIR/$skill" ]]; then
            log_warn "Skipping (local symlink exists): $skill"
            continue
        fi

        local local_mtime=$(get_skill_mtime "$SKILLS_DIR/$skill")
        local hub_mtime=$(get_skill_mtime "$GDRIVE_SKILLS/$skill")

        if [[ -d "$SKILLS_DIR/$skill" ]] && [[ "$local_mtime" -gt "$hub_mtime" ]]; then
            log_warn "Conflict: $skill (local is newer, skipping)"
            continue
        fi

        log_info "Pulling: $skill"
        mkdir -p "$SKILLS_DIR/$skill"
        rsync -av --delete "$GDRIVE_SKILLS/$skill/" "$SKILLS_DIR/$skill/"
        ((count++))
    done

    log_ok "Pulled $count skills from gdrive hub"
}

# Show sync status
cmd_status() {
    echo ""
    log_info "Skill Sync Status ($ENV)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    printf "%-30s %-12s %-12s %s\n" "SKILL" "LOCAL" "HUB" "STATUS"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # Get all skills (union of local and hub)
    local all_skills
    all_skills=$(echo -e "$(get_local_skills)\n$(get_hub_skills)" | sort -u | grep -v '^$')

    for skill in $all_skills; do
        local local_exists="no"
        local hub_exists="no"
        local status=""
        local is_symlink=""

        if [[ -L "$SKILLS_DIR/$skill" ]]; then
            local_exists="symlink"
            is_symlink="(symlink)"
        elif [[ -d "$SKILLS_DIR/$skill" ]]; then
            local_exists="yes"
        fi

        if [[ -d "$GDRIVE_SKILLS/$skill" ]]; then
            hub_exists="yes"
        fi

        if [[ "$local_exists" == "symlink" ]]; then
            status="${YELLOW}skip (symlink)${NC}"
        elif [[ "$local_exists" == "yes" ]] && [[ "$hub_exists" == "yes" ]]; then
            local local_mtime=$(get_skill_mtime "$SKILLS_DIR/$skill")
            local hub_mtime=$(get_skill_mtime "$GDRIVE_SKILLS/$skill")
            if [[ "$local_mtime" -gt "$hub_mtime" ]]; then
                status="${YELLOW}local newer${NC}"
            elif [[ "$local_mtime" -lt "$hub_mtime" ]]; then
                status="${YELLOW}hub newer${NC}"
            else
                status="${GREEN}synced${NC}"
            fi
        elif [[ "$local_exists" == "yes" ]]; then
            status="${BLUE}local only${NC}"
        elif [[ "$hub_exists" == "yes" ]]; then
            status="${BLUE}hub only${NC}"
        fi

        printf "%-30s %-12s %-12s %b\n" "$skill" "$local_exists" "$hub_exists" "$status"
    done

    echo ""
}

# Force sync a specific skill (local -> hub)
cmd_force_push() {
    local skill="$1"

    if [[ -L "$SKILLS_DIR/$skill" ]]; then
        log_error "Cannot push symlink: $skill"
        exit 1
    fi

    if [[ ! -d "$SKILLS_DIR/$skill" ]]; then
        log_error "Skill not found locally: $skill"
        exit 1
    fi

    log_info "Force pushing: $skill"
    rsync -av --delete "$SKILLS_DIR/$skill/" "$GDRIVE_SKILLS/$skill/"
    log_ok "Force pushed: $skill"
}

# Force pull a specific skill (hub -> local)
cmd_force_pull() {
    local skill="$1"

    if [[ -L "$SKILLS_DIR/$skill" ]]; then
        log_error "Cannot overwrite symlink: $skill"
        exit 1
    fi

    if [[ ! -d "$GDRIVE_SKILLS/$skill" ]]; then
        log_error "Skill not found in hub: $skill"
        exit 1
    fi

    log_info "Force pulling: $skill"
    mkdir -p "$SKILLS_DIR/$skill"
    rsync -av --delete "$GDRIVE_SKILLS/$skill/" "$SKILLS_DIR/$skill/"
    log_ok "Force pulled: $skill"
}

# Main
case "${1:-status}" in
    push)
        cmd_push
        ;;
    pull)
        cmd_pull
        ;;
    status)
        cmd_status
        ;;
    force-push)
        if [[ -z "${2:-}" ]]; then
            log_error "Usage: skill-sync force-push <skill-name>"
            exit 1
        fi
        cmd_force_push "$2"
        ;;
    force-pull)
        if [[ -z "${2:-}" ]]; then
            log_error "Usage: skill-sync force-pull <skill-name>"
            exit 1
        fi
        cmd_force_pull "$2"
        ;;
    *)
        echo "Usage: skill-sync <command>"
        echo ""
        echo "Commands:"
        echo "  status              Show sync status (default)"
        echo "  push                Push local skills to gdrive hub"
        echo "  pull                Pull skills from gdrive hub"
        echo "  force-push <skill>  Force push a specific skill"
        echo "  force-pull <skill>  Force pull a specific skill"
        echo ""
        echo "Environment: $ENV"
        echo "Local skills: $SKILLS_DIR"
        echo "Hub: $GDRIVE_SKILLS"
        ;;
esac
