# GitHub CLI (gh) Skill

**Last Updated:** 2026-02-05
**Auth Status:** Logged in as `calenwalshe` via keyring

## Authentication

```bash
# Check auth status
gh auth status

# Re-authenticate if needed
gh auth login

# View current user
gh api user --jq '.login'
```

**Current Scopes:** `delete_repo`, `gist`, `read:org`, `repo`

## Rate Limits

```bash
# Check rate limit status
gh api rate_limit --jq '.resources.core | "Limit: \(.limit), Remaining: \(.remaining)"'
```

- **Limit:** 5000 requests/hour (authenticated)
- **Search API:** 30 requests/minute
- **GraphQL:** 5000 points/hour

---

## Common Commands

### Repositories

```bash
# Create new repo
gh repo create my-project --public --clone
gh repo create my-project --private --description "My project"

# Clone repo
gh repo clone owner/repo
gh repo clone calenwalshe/repo

# List your repos
gh repo list
gh repo list --limit 50 --json name,url

# View repo info
gh repo view owner/repo
gh repo view --web  # Opens in browser

# Fork a repo
gh repo fork owner/repo --clone

# Delete repo (requires delete_repo scope)
gh repo delete owner/repo --yes
```

### Pull Requests

```bash
# Create PR
gh pr create --title "Feature" --body "Description"
gh pr create --fill  # Auto-fill from commits
gh pr create --draft

# List PRs
gh pr list
gh pr list --state all
gh pr list --author @me

# View PR
gh pr view 123
gh pr view 123 --web

# Check out PR locally
gh pr checkout 123

# Merge PR
gh pr merge 123 --merge
gh pr merge 123 --squash
gh pr merge 123 --rebase

# Review PR
gh pr review 123 --approve
gh pr review 123 --request-changes --body "Please fix X"
```

### Issues

```bash
# Create issue
gh issue create --title "Bug" --body "Description"
gh issue create --label bug,urgent

# List issues
gh issue list
gh issue list --assignee @me
gh issue list --label bug

# View issue
gh issue view 123
gh issue view 123 --web

# Close issue
gh issue close 123
gh issue close 123 --reason completed

# Reopen issue
gh issue reopen 123
```

### Releases

```bash
# Create release
gh release create v1.0.0 --title "Version 1.0.0" --notes "Release notes"
gh release create v1.0.0 --generate-notes  # Auto-generate from commits

# Upload assets
gh release create v1.0.0 ./dist/*.zip

# List releases
gh release list

# Download release assets
gh release download v1.0.0

# Delete release
gh release delete v1.0.0 --yes
```

### Gists

```bash
# Create gist
gh gist create file.txt
gh gist create file.txt --public --desc "My gist"
gh gist create file1.txt file2.txt  # Multiple files

# List gists
gh gist list

# View gist
gh gist view <gist-id>

# Edit gist
gh gist edit <gist-id>
```

### Workflows (GitHub Actions)

```bash
# List workflows
gh workflow list

# View workflow runs
gh run list
gh run list --workflow=ci.yml

# View specific run
gh run view <run-id>

# Watch running workflow
gh run watch <run-id>

# Re-run failed workflow
gh run rerun <run-id>

# Download artifacts
gh run download <run-id>
```

---

## API Access

### REST API

```bash
# GET request
gh api repos/owner/repo
gh api user

# With jq filtering
gh api repos/owner/repo --jq '.stargazers_count'
gh api user/repos --jq '.[].name'

# POST request
gh api repos/owner/repo/issues --method POST --field title="New Issue" --field body="Description"

# Paginated results
gh api repos/owner/repo/issues --paginate

# Raw output
gh api repos/owner/repo --include  # Show headers
```

### GraphQL API

```bash
# Simple query
gh api graphql -f query='
  query {
    viewer {
      login
      name
    }
  }
'

# With variables
gh api graphql -f query='
  query($owner: String!, $repo: String!) {
    repository(owner: $owner, name: $repo) {
      stargazerCount
    }
  }
' -f owner=calenwalshe -f repo=myrepo
```

---

## Useful Patterns

### Create repo with initial structure

```bash
gh repo create my-project --public --clone && \
  cd my-project && \
  echo "# My Project" > README.md && \
  git add . && \
  git commit -m "Initial commit" && \
  git push
```

### Quick PR workflow

```bash
git add . && \
  git commit -m "feat: description" && \
  git push -u origin HEAD && \
  gh pr create --fill
```

### Search across repos

```bash
# Search code
gh search code "function_name" --repo owner/repo

# Search issues
gh search issues "bug" --repo owner/repo --state open

# Search PRs
gh search prs "feature" --author calenwalshe
```

---

## Shell Aliases (added to ~/.zshrc)

```bash
alias ghpr='gh pr create --fill'
alias ghprl='gh pr list'
alias ghprv='gh pr view'
alias ghissue='gh issue create'
alias ghil='gh issue list'
alias ghrepo='gh repo create'
alias ghclone='gh repo clone'
alias ghweb='gh repo view --web'
alias ghrate='gh api rate_limit --jq ".resources.core | \"Remaining: \(.remaining)/\(.limit)\""'
```

---

## Helper Scripts

Located in `~/bin/`:

| Script | Purpose |
|--------|---------|
| `gh-new-project.sh` | Create repo, clone, initial commit |
| `gh-quick-pr.sh` | Stage, commit, push, create PR |
| `gh-release.sh` | Tag and create release |

---

## Limitations & Notes

### What gh CAN do:
- Full CRUD on repos, PRs, issues, releases, gists
- Trigger and monitor GitHub Actions
- Access REST and GraphQL APIs
- Clone/fork repos over HTTPS
- Manage repo settings, labels, milestones

### What gh CANNOT do:
- Access private repos without proper scopes
- Bypass branch protection rules
- Access GitHub Enterprise without separate auth
- Modify billing or organization admin settings without admin scope

### Current Auth Scopes:
- `repo` - Full access to private repos
- `delete_repo` - Can delete repositories
- `gist` - Create and manage gists
- `read:org` - Read org membership (not write)

### Rate Limits:
- **REST API:** 5000/hour (authenticated)
- **Search API:** 30/minute
- **GraphQL:** 5000 points/hour
- **Git operations:** Unlimited for most cases
