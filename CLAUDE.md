# CLAUDE.md

This file provides guidance to AI assistants (Claude and others) working on the **Ron** repository.

## Project Overview

**Ron** is a newly initialized project. As of the last update to this file, the repository contains only a README and no source code yet. This document will be updated as the project evolves.

- **Repository**: `hockandr19-gif/Ron`
- **Status**: Early initialization — no source code, dependencies, or framework selected yet

## Repository Structure

```
Ron/
├── CLAUDE.md       # This file — guidance for AI assistants
└── README.md       # Project title only
```

As the project grows, update the structure diagram above to reflect new directories and files.

## Git Workflow

### Branch Naming

- **Main branch**: `master`
- **Claude-generated branches**: must start with `claude/` and end with the session ID suffix
  - Example: `claude/claude-md-mm5zq9k24hmhsv6h-z4yO5`

### Standard Git Operations

```bash
# Push a branch (always use -u to set upstream)
git push -u origin <branch-name>

# Fetch a specific branch
git fetch origin <branch-name>

# Pull a specific branch
git pull origin <branch-name>
```

### Push Retry Policy

If a push fails due to a network error (not a permissions/403 error), retry up to 4 times with exponential backoff:
- Wait 2s, retry
- Wait 4s, retry
- Wait 8s, retry
- Wait 16s, retry

A 403 error means wrong branch — verify the branch name starts with `claude/`.

### Commit Messages

Write clear, concise commit messages in the imperative mood:
- `Add user authentication module`
- `Fix null pointer in data parser`
- `Update README with setup instructions`

Avoid vague messages like `fix`, `update`, or `changes`.

## Development Conventions

Since the project has no source code yet, these conventions should be established when the stack is chosen:

### When a language/framework is selected, document here:
- [ ] Language and version
- [ ] Framework and version
- [ ] Package manager and lockfile policy
- [ ] Code style / formatting tool and config
- [ ] Linting tool and config
- [ ] Testing framework and how to run tests
- [ ] Build commands
- [ ] Environment variable requirements

## Task Workflow for AI Assistants

1. **Read before editing**: Always read a file fully before modifying it
2. **Minimal changes**: Only change what is necessary for the task — avoid refactoring unrelated code
3. **No speculative features**: Do not add error handling, abstractions, or features beyond what is explicitly requested
4. **Commit and push**: After completing a task, commit with a descriptive message and push to the designated branch
5. **Update this file**: When project structure, dependencies, or conventions change, update CLAUDE.md to reflect the current state

## Updating This File

Whenever significant changes are made to the project (new dependencies, new tooling, structural reorganization, CI/CD setup, etc.), update the relevant sections of this file so future AI assistants have accurate context.
