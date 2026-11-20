---
title: How to sync
aliases: [sync, setup, obsidian git]
type: guide
tags: [guide, git]
created: 2026-11-19
updated: 2026-11-19
summary: One-time setup and the daily routine for working on the vault together through GitHub with the Obsidian Git plugin.
---
# How to sync (Obsidian + GitHub)

The whole repo is the Obsidian vault. GitHub is the shared copy: each
person pulls the other's changes and pushes their own. Back to [[Home]].

## One-time setup (each person)
1. **Git and a GitHub account.** Install [Git for Windows](https://git-scm.com/download/win) and sign in to GitHub. Guru adds Yuvraj under the repo's *Settings → Collaborators*.
2. **Clone the repo** into a folder that is **not** inside OneDrive. OneDrive and git fight over the `.git` folder.
   ```
   git clone https://github.com/Guru-Balaji18/beginners-in-the-herd.git "%USERPROFILE%\Desktop\Stem Fair"
   ```
3. **Open it in Obsidian:** *Open folder as vault* → pick that folder.
4. **Install Obsidian Git:** *Settings → Community plugins → Turn on → Browse → "Git" (by Vinzent) → Install → Enable*. The shared settings already in the repo then apply:
   - pull when Obsidian starts;
   - pull every 10 minutes;
   - commit-and-sync is manual.
5. **Optional:** add a hotkey for *Git: Commit-and-sync* (*Settings → Hotkeys*).

## Every session
1. **Pull first.** Obsidian does it at startup. In a terminal or Claude Code: `git pull`.
2. Work: notes in `notes/`, code and docs as usual.
3. **Add your UPDATE** to the top of [[UPDATE log]].
4. **Sync:** *Ctrl+P → "Git: Commit-and-sync"*, or `git add` / `git commit` / `git push` in a terminal.

## Rules that keep it clean
- Pre-registration first: commit the plan or deviation entry **alone**, then the code, then the results.
- Don't commit while a simulation is still writing its results file.
- `data/` is never committed (759 MB, gitignored).
- Move or rename notes **inside Obsidian** so links update.
- If a pull reports a conflict, open the file, keep both people's text, remove the `<<<<<<<` / `=======` / `>>>>>>>` lines, then commit-and-sync.
