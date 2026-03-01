# Dotfiles

Personal shell configuration snippets and configs.

## Files

| File | Description |
|------|-------------|
| `zshrc-snippets.zsh` | Portable .zshrc snippets — source or copy into your .zshrc |
| `tmux.conf` | Full tmux config — copy to `~/.tmux.conf` |

## What's in zshrc-snippets.zsh

- **tmux grid layouts** — `tmux3`, `tmux6`, `tmux9` for quick N-pane tiled grids
- **GitHub CLI aliases** — 15+ `gh` shortcuts (`ghpr`, `ghclone`, `ghweb`, etc.) plus `ghsearch()` and `ghstatus()`
- **iTerm2 keybindings** — Option+Arrow word navigation, full-path `lsf`/`lsfa` aliases
- **SSH wrapper** — Auto-tints terminal background blue-purple during SSH sessions, restores on disconnect

## What's in tmux.conf

- Cmd+Option+Arrow pane navigation (requires iTerm2 key mapping)
- Alt+\` pane-select mode (vim-style hjkl)
- Vi copy mode + mouse support
- Alt+u/j quarter-page scroll
- Heavy pane borders (blue active, green inactive) with directory labels
- Alt+z/f zoom, Alt+1-9 pane jump, Alt+Enter expand/equalize
- 3x3 grid workflow bindings (Alt+g, Alt+=, F1, F2)
- 500K line history, TPM plugin manager, fzf-url plugin, OSC 52 clipboard

## Installation

```bash
# tmux config
cp dotfiles/tmux.conf ~/.tmux.conf
tmux source-file ~/.tmux.conf

# zshrc snippets (append to existing)
cat dotfiles/zshrc-snippets.zsh >> ~/.zshrc
source ~/.zshrc
```

## Dependencies

- tmux 3.2+ (for heavy pane borders)
- [TPM](https://github.com/tmux-plugins/tpm) — `git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm`
- iTerm2 (for Cmd+Option keybindings and terminal color tinting)
- GitHub CLI (`brew install gh`)
