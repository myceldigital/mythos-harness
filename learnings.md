# Project Learnings

> Last updated: 2026-04-22

## Architectural Decisions
- [2026-04-22] – Local `Desktop/mythos harness` aligned to GitHub `myceldigital/mythos-harness`  
  **Rationale:** Local folder was an empty `git init` with no commits; the canonical history lives on `origin`.  
  **Alternatives considered:** None needed—fetch/checkout was sufficient.  
  **Impact:** `main` tracks `origin/main`; use normal pull/push for ongoing sync.

## Patterns & Conventions Established
- *(empty)*

## Gotchas & Solutions
- [2026-04-22] – Empty local git dir vs populated remote  
  **Root cause:** `git init` without remote doesn’t have commits; remote already had `main`.  
  **Solution:** `git remote add origin …`, `git fetch`, `git checkout -B main origin/main`.  
  **Code snippet:** N/A (git workflow)

## Tech Stack / Tooling Nuances
- *(TBD as project grows)*

## Performance & Optimization Notes
- *(empty)*

## Team / Workflow Agreements
- *(empty)*
