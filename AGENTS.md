# Instructions for AI assistants

You are working on Nestea's Hyprland rice. Develop and verify changes locally. Publish a downloadable update only after the user explicitly says to push; never install it locally yourself. Read this file first; it describes a machine-specific workflow that is not obvious from the source tree.

## Golden rules

1. **Never run `./Installer --install` (or `Installer --install`) yourself.** The user downloads published updates from the desktop and wants to watch that flow. Do not push until the user explicitly authorizes it.
2. **Never commit secrets or personal data.** `.gitignore` is an allowlist: only `.gitignore`,
   `README.md`, `AGENTS.md`, `Installer`, `install.sh`, the three `*-Options.example.json`
   templates, `src/**` and `wallpaper/.gitkeep` are ever tracked. Do not widen it for personal
   files, keys or state.
3. **QuickShell owns the topbar** (`src/quickshell/`). Keep its status and actions in `src/bin/` and `src/lib/rice/` in sync. Preserve Hyprland and its Lua config in `src/config/hyprland.lua`.
4. **Nothing is mandatory.** Updates are `optional` or `recommended`; there is no forced install,
   ever ("not like Windows").
5. **Git identity is global and permanent on this machine** (NesTea). Just commit; do not set a
   per-repo identity and do not use `--author`.
6. Run git commands **serially** — two parallel git invocations have raced on `.git/index.lock`
   here before.

## Where things live

| Path | Purpose |
| --- | --- |
| `src/config/` | Lua sources generating configs; `apply.lua` + `manifest.lua` render them, `mako.lua` styles notifications |
| `src/lib/rice/panels.py` | GTK control panel: docked `Panel` pages plus the centered `UpdatesOverlay` window |
| `src/lib/rice/update_check.py` | Update state machine: `check()`, `status()`, `ignore()`, `apply()`, `notify_update()` |
| `src/lib/rice/panels.css` | Panel and overlay styles (`.device-row`, `.primary`, `.secondary`, …) |
| `src/data/updates.json` | Per-update descriptions and tags, keyed by 12-char commit id |
| `src/bin/` | Installed commands: `desktop-panel`, `rice-update`, `rice-update-watch`, … |
| `src/installer/install.sh` | Deploy step run by the installer (also runs `makoctl reload`) |
| `src/systemd/` | User services (`rice-bar`, `rice-controls`, `rice-update-watch`, …) |
| `~/.local/state/rice/update.json` | Live update state (machine-local, never committed) |
| `~/.config/bash/local.bash` | Machine-local `push-next-rice-update` helper (not in the repo) |

Generated files (`~/.config`, `~/.local/bin`, `~/.local/lib/rice`) are **outputs**. Edit sources
under `src/` only; the installer regenerates the rest when the user applies an update.

## The update flow

State lives in `~/.local/state/rice/update.json`:

```json
{
  "updates": {
    "56e5b3eb3dba": {"new": false, "summary": "...", "detail": "...", "id": "",
                     "kind": "recommended", "applied": 1790204532, "when": 1790204500}
  },
  "available": false, "count": 0, "subject": "...", "sha": "...",
  "checked": 0, "notified_sha": "", "error": "", "applied": 0
}
```

- `check()` fetches the upstream branch and records every commit ahead of `HEAD` as an entry with
  `new: true`. `status()` only reads the file, so the panel never blocks on the network.
- `rice-update-watch.service` checks every 30 minutes and notifies only while some entry is still
  `new: true`. `systemctl --user restart rice-update-watch.service` forces an instant check
  (first check runs ~45 s after the restart).
- **Download update** shows at the top of Settings only while an entry is new. **Ignore** beside
  it sets `new: false`: the row disappears and the update lives on only in **Update history**.
- **Update history** (bottom of Settings, below **Share an idea**) and the per-update detail view
  are centered `UpdatesOverlay` windows — separate surfaces, like floating terminals, not panel
  pages. Only one surface may hold the exclusive keyboard grab; `App.open_updates()` closes the
  panel first.
- Clicking **Download update** closes Settings and shows the detail overlay. **Install** launches
  `rice-update-progress`, a separate GTK process that survives `rice-controls` restarting. It
  starts `rice-update.service` and shows measured Git transfer counts and installer stages until
  success or failure. **Cancel** closes the detail overlay without installing.

### Describing an update

Resolution order: `src/data/updates.json` → `Rice-Update-*` commit trailers → commit subject/body.

```json
"56e5b3eb3dba": {"summary": "Smaller shuffle and repeat glyphs",
                  "detail": "One line what changed, then why it matters…",
                  "kind": "optional"}
```

Trailers (final paragraph of the commit message):

```
Rice-Update-Summary: 1-10 word description
Rice-Update-Detail: longer sentence shown in the detail overlay
Rice-Update-Kind: optional | recommended
Rice-Update-ID: 0x00002
```

A commit cannot know its own id, so `src/data/updates.json` describes **earlier** commits
(enrich them in a later commit); the trailers carry the fresh commit's metadata. Summary is what
the list window shows; detail is what the overlay expands to.
Number new updates with a five-digit hexadecimal ID in `Rice-Update-ID`, starting at `0x00001`
for commit `27843e5`; increment by one for each subsequent shipped update.

## Preparing and shipping a change

1. Read this file, `README.md`, and every file you will touch.
2. Edit sources under `src/` only.
3. Verify (never against the live HOME for generated configs):
   ```sh
   python3 -m py_compile src/lib/rice/*.py src/bin/rice-update src/bin/rice-update-watch
   luac -p src/config/*.lua
   bash -n src/installer/install.sh src/bin/desktop-panel
   /usr/lib/qt6/bin/qmlformat src/quickshell/shell.qml >/dev/null
   /usr/lib/qt6/bin/qmlformat src/quickshell/BarButton.qml >/dev/null
   # Config generation test against a throwaway HOME:
   mkdir -p /tmp/opencode/fake-home/.config
   HOME=/tmp/opencode/fake-home lua src/config/apply.lua
   ```
4. For a local commit, use trailers (identity is already configured):
   ```sh
   git add -A
   git commit -m "Describe the change" -m "Rice-Update-Summary: 1-10 words
   Rice-Update-Detail: longer description for the detail overlay
   Rice-Update-Kind: recommended"
   ```
   or, from inside `~/config`, the machine helper:
   ```sh
   push-next-rice-update -k recommended -s "Short summary" -d "Long description" "Commit subject"
   ```
5. Push **only with explicit user authorization**, without installing: `git push` (or let `push-next-rice-update` push for you).
6. Tell the user it is published; for an immediate desktop notification, restart the watcher:
   `systemctl --user restart rice-update-watch.service`.
7. The change only reaches the desktop after the user chooses **Download update**. If the new UI
   itself must be demonstrated, ship a small follow-up commit — the first update cannot show its
   own new screens until it has been applied.

## Notifications (mako)

- Send with `notify-send -a Rice -i <icon> -u critical "Title" "Body"`; critical urgency keeps
  the notification on screen until dismissed (see `update_check.notify`).
- The ✕ near the right edge is part of the notification **text**: `format` and
  `text-alignment=right` in `src/config/mako.lua`. mako 1.11 cannot draw a real close widget, so
  a left click anywhere on the notification dismisses it (`on-button-left=dismiss`).
- `install.sh` regenerates configs and runs `makoctl reload`. For a quick local test:
  `lua src/config/apply.lua && makoctl reload` — but remember rule 1: prefer just pushing.

## Control panel conventions

- Pages are rows built from `row()`, `section()`, `action_button()`, `switch_row()`; classes come
  from `panels.css`.
- Adding a **page**: add a `render_<page>` method, register the loader in `Panel.load`, add the
  name to the page tuple in `App.do_startup` and the allow-list in `App.do_command_line`.
  `src/bin/desktop-panel` passes the page name through unchanged.
- Floating windows: a separate `Gtk.Window`, `GtkLayerShell.init_for_window`, **no edge anchors**
  (an unanchored layer surface is centered), namespace `rice-updates`, card `#panel`, transparent
  `window#rice-overlay`. Esc closes. See `UpdatesOverlay`.
- Anything slow or network-bound goes through `Panel.work()` (thread pool + spinner + feedback).

## Services

`rice-bar`, `rice-controls`, `rice-hotspot`, `rice-update-watch` are enabled
user services; `rice-update.service` is started on demand only. Logs:
`journalctl --user -u <name> -b`. The QuickShell bar is the only bar engine; `rice-bar.service` runs `src/quickshell/shell.qml`.

## When unsure

Stop and ask the user; they prefer short multiple-choice prompts for real decisions and want work
to just get done for everything else.
