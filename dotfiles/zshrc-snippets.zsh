# ============================================================================
# Personal .zshrc Snippets
# Drop these into your .zshrc as needed
# ============================================================================

# ============================================================================
# tmux Grid Layouts — quick N-pane tiled grids
# ============================================================================
tmux3() {
  local session="${1:-grid3}"
  tmux new-session -d -s "$session" \
    && tmux split-window -h -t "$session" \
    && tmux split-window -h -t "$session" \
    && tmux select-layout -t "$session" even-horizontal \
    && tmux attach -t "$session"
}

tmux6() {
  local session="${1:-grid6}"
  tmux new-session -d -s "$session" \
    && tmux split-window -v -t "$session" \
    && tmux select-pane -t "$session:0.0" \
    && tmux split-window -h -t "$session" \
    && tmux split-window -h -t "$session" \
    && tmux select-pane -t "$session:0.3" \
    && tmux split-window -h -t "$session" \
    && tmux split-window -h -t "$session" \
    && tmux select-layout -t "$session" tiled \
    && tmux select-pane -t "$session:0.0" \
    && tmux attach -t "$session"
}

tmux9() {
  local session="${1:-grid9}"
  tmux new-session -d -s "$session" \
    && tmux split-window -v -t "$session" \
    && tmux split-window -v -t "$session" \
    && tmux select-pane -t "$session:0.0" \
    && tmux split-window -h -t "$session" \
    && tmux split-window -h -t "$session" \
    && tmux select-pane -t "$session:0.3" \
    && tmux split-window -h -t "$session" \
    && tmux split-window -h -t "$session" \
    && tmux select-pane -t "$session:0.6" \
    && tmux split-window -h -t "$session" \
    && tmux split-window -h -t "$session" \
    && tmux select-layout -t "$session" tiled \
    && tmux select-pane -t "$session:0.0" \
    && tmux attach -t "$session"
}

# ============================================================================
# GitHub CLI (gh) — Aliases and Helpers
# ============================================================================
export GITHUB_USER="calenwalshe"

# Quick aliases
alias ghpr='gh pr create --fill'
alias ghprl='gh pr list'
alias ghprv='gh pr view'
alias ghprc='gh pr checkout'
alias ghprm='gh pr merge'
alias ghissue='gh issue create'
alias ghil='gh issue list'
alias ghiv='gh issue view'
alias ghrepo='gh repo create'
alias ghclone='gh repo clone'
alias ghweb='gh repo view --web'
alias ghrate='gh api rate_limit --jq ".resources.core | \"Remaining: \(.remaining)/\(.limit)\""'
alias ghrel='gh release create'
alias ghrun='gh run list'
alias ghwatch='gh run watch'

# Helper scripts
alias gh-new-project='~/.claude/skills/github-cli/gh-new-project.sh'
alias gh-quick-pr='~/.claude/skills/github-cli/gh-quick-pr.sh'
alias gh-release='~/.claude/skills/github-cli/gh-release.sh'

# Quick functions
ghsearch() {
  # Search code in a repo: ghsearch "pattern" owner/repo
  gh search code "$1" --repo "${2:-}"
}

ghstatus() {
  # Show auth status and rate limit
  gh auth status
  echo ""
  gh api rate_limit --jq '.resources.core | "Rate limit: \(.remaining)/\(.limit) (resets: \(.reset | strftime("%H:%M:%S")))"'
}

# ============================================================================
# iTerm2 Keybindings & Path Aliases
# ============================================================================

# Option + Arrow key word navigation (iTerm2)
bindkey "^[[1;3C" forward-word
bindkey "^[[1;3D" backward-word

# Full path listing
alias lsf='ls -d "$PWD"/*'
alias lsfa='ls -d "$PWD"/*(D)'  # Include hidden files

# ============================================================================
# SSH Wrapper — Tints terminal background on remote sessions
# ============================================================================
# Requires ~/.terminal-status.zsh (optional — auto-syncs to remote hosts)
ssh() {
  local destination=""
  local args=("$@")

  for arg in "${args[@]}"; do
    if [[ ! "$arg" =~ ^- ]] && [[ -n "$arg" ]]; then
      destination="$arg"
      break
    fi
  done

  if [[ -n "$destination" ]] && [[ -f ~/.terminal-status.zsh ]]; then
    scp -q ~/.terminal-status.zsh "${destination}:~/" 2>/dev/null
    command ssh "${destination}" "grep -q '.terminal-status.zsh' ~/.zshrc 2>/dev/null || echo '
# Terminal Activity Status Indicator
if [ -f ~/.terminal-status.zsh ]; then
  source ~/.terminal-status.zsh
fi' >> ~/.zshrc" 2>/dev/null
  fi

  # Subtle blue-purple tint for SSH sessions
  printf '\033]11;#1a1a2e\007'
  command ssh "$@"
  local exit_code=$?
  # Restore black background on disconnect
  printf '\033]11;#000000\007'
  return $exit_code
}
