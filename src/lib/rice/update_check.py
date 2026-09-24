#!/usr/bin/env python3
"""Find rice updates on the configured Git upstream and install them.

status() only reads the cached state, so the settings panel never blocks on the
network. check() talks to the upstream and refreshes that cache, apply() pulls
the checkout and re-runs the installer. The desktop watcher calls check() on a
timer and turns a new upstream commit into a notification.

Every upstream commit is kept as its own entry under state["updates"], keyed by
the twelve character commit id:

    {"56e5b3e": {"new": true, "summary": "...", "detail": "...",
                 "kind": "recommended", "applied": 0, "when": 1790204500}}

"new" is the only flag the UI asks about. The settings menu shows Download
update while any entry is new, Ignore flips that entry back to false, and
apply() marks everything installed. Descriptions are resolved in this order:
src/data/updates.json, then Rice-Update-* commit trailers, then the commit
subject and body.
"""
import json
import os
from pathlib import Path
import re
import subprocess
import time

HOME = Path.home()
SOURCE = HOME / '.local/share/rice/source'
STATE = HOME / '.local/state/rice'
FILE = STATE / 'update.json'
PUBLIC = 'https://github.com/SandwichEater577/Nestea-s-Hyprland-Rice.git'
ISSUES = 'https://github.com/SandwichEater577/Nestea-s-Hyprland-Rice/issues/new'
CHECK_SECONDS = 1800
KINDS = ('optional', 'recommended')
HISTORY = 20  # installed commits kept described in the Update history window
TRAILER = re.compile(r'^Rice-Update-(Summary|Detail|Kind):[ \t]*(.*)$')


class UpdateError(RuntimeError):
    pass


def _env():
    # Never prompt: a credential or passphrase dialog would hang a user service.
    env = dict(os.environ)
    env.update(GIT_TERMINAL_PROMPT='0',
               GIT_SSH_COMMAND='ssh -o BatchMode=yes -o ConnectTimeout=10')
    return env


def _git(args, timeout=45):
    return subprocess.run(['git', '-C', str(SOURCE), *args], capture_output=True,
                          text=True, timeout=timeout, env=_env())


def _out(args, check=True, timeout=45):
    result = _git(args, timeout=timeout)
    if check and result.returncode:
        raise UpdateError((result.stderr or result.stdout).strip() or 'git failed')
    return (result.stdout or '').strip()


def notify(title, body, icon='dialog-information-symbolic', urgency=None):
    args = ['notify-send', '-a', 'Rice', '-i', icon]
    if urgency:
        args += ['-u', urgency]
    subprocess.run(args + [title, body], capture_output=True, timeout=20, env=_env())


def pending_updates(state):
    """Entries still waiting to be downloaded, newest commit first."""
    found = [(sha, entry) for sha, entry in (state.get('updates') or {}).items()
             if entry.get('new') and not entry.get('applied')]
    found.sort(key=lambda item: item[1].get('when') or 0, reverse=True)
    return found


def notify_update(state):
    # Urgency critical keeps the message on screen until it is dismissed; a five
    # second toast is too easy to miss for something that happens once a week.
    waiting = pending_updates(state)
    count = len(waiting)
    summary = (waiting[0][1].get('summary') if waiting else '') or (state.get('subject') or '').strip()
    detail = f"{count} new commit{'s' if count != 1 else ''}" if count else 'New commits ready'
    if summary:
        detail += ' · ' + (summary if len(summary) <= 60 else summary[:57] + '…')
    notify('Rice update available', detail + '\nSettings → Download update',
           icon='software-update-available-symbolic', urgency='critical')


def save(state):
    STATE.mkdir(parents=True, exist_ok=True)
    temp = FILE.with_suffix('.tmp')
    temp.write_text(json.dumps(state, indent=1) + '\n')
    temp.replace(FILE)
    return state


def status():
    """Cached state. Never touches the network, so the panel stays responsive."""
    try:
        state = json.loads(FILE.read_text())
    except (OSError, ValueError):
        state = {}
    for key, default in (('updates', {}), ('available', False), ('count', 0), ('subject', ''),
                         ('sha', ''), ('checked', 0), ('notified_sha', ''),
                         ('error', ''), ('applied', 0)):
        state.setdefault(key, default)
    if not isinstance(state['updates'], dict):
        state['updates'] = {}
    for entry in state['updates'].values():
        if not isinstance(entry, dict):
            continue
        for key, default in (('new', False), ('summary', ''), ('detail', ''),
                             ('kind', 'recommended'), ('applied', 0), ('when', 0)):
            entry.setdefault(key, default)
        if entry['kind'] not in KINDS:
            entry['kind'] = 'recommended'
    return state


def ignore(sha):
    """Hide one update from the settings menu; it stays listed in the history."""
    state = status()
    entry = state['updates'].get(str(sha)[:12])
    if entry:
        entry['new'] = False
    if not pending_updates(state):
        state['available'] = False
        state['count'] = 0
    return save(state)


def ago(stamp):
    if not stamp:
        return ''
    delta = max(0, int(time.time() - stamp))
    if delta < 60:
        return 'just now'
    if delta < 3600:
        return f'{delta // 60} min ago'
    if delta < 86400:
        return f'{delta // 3600} h ago'
    return f'{delta // 86400} d ago'


def branch():
    name = _out(['rev-parse', '--abbrev-ref', 'HEAD'], check=False)
    return name if name and name != 'HEAD' else 'main'


def _trailers(body):
    found = {}
    for line in (body or '').splitlines():
        match = TRAILER.match(line)
        if match:
            found[match.group(1)] = match.group(2).strip()
    return found


def _describe(body, meta):
    """summary, detail and kind for one commit body plus its updates.json entry."""
    if not isinstance(meta, dict):
        meta = {}
    trailer = _trailers(body)
    lines = [line for line in (body or '').strip().splitlines()]
    subject = lines[0].strip() if lines else ''
    prose = '\n'.join(line for line in lines[1:]
                      if not line.startswith('Rice-Update-')).strip()
    summary = str(meta.get('summary') or trailer.get('Summary') or subject).strip() or 'Rice update'
    detail = str(meta.get('detail') or trailer.get('Detail') or prose or subject).strip()
    kind = str(meta.get('kind') or trailer.get('Kind') or 'recommended').strip().lower()
    return summary, detail, (kind if kind in KINDS else 'recommended')


def _make(sha, when, body, meta, new, applied=0):
    summary, detail, kind = _describe(body, meta)
    try:
        when = float(when)
    except (TypeError, ValueError):
        when = 0.0
    return {'new': bool(new), 'summary': summary, 'detail': detail, 'kind': kind,
            'applied': float(applied or 0), 'when': when}


def _catalog(tree=None):
    """updates.json from the checkout, deepened with the fetched tree's copy."""
    merged = {}
    try:
        data = json.loads((SOURCE / 'src/data/updates.json').read_text())
        if isinstance(data, dict):
            merged.update({str(key)[:12]: value for key, value in data.items()
                           if isinstance(value, dict)})
    except (OSError, ValueError):
        pass
    if tree:
        raw = _out(['show', f'{tree}:src/data/updates.json'], check=False)
        try:
            data = json.loads(raw) if raw else {}
            if isinstance(data, dict):
                merged.update({str(key)[:12]: value for key, value in data.items()
                               if isinstance(value, dict)})
        except ValueError:
            pass
    return merged


def _log(rev, limit=None):
    """(sha12, commit time, full commit body) tuples, newest commit first."""
    args = ['log', '--format=%H%x00%ct%x00%B%x1e']
    if limit:
        args += ['-n', str(limit)]
    args.append(rev)
    found = []
    for chunk in _out(args, check=False).split('\x1e'):
        chunk = chunk.strip('\n')
        if not chunk:
            continue
        parts = chunk.split('\x00', 2)
        if len(parts) != 3:
            continue
        try:
            when = float(parts[1])
        except ValueError:
            when = 0.0
        found.append((parts[0].strip()[:12], when, parts[2]))
    return found


def _mark_installed(state, when=None):
    """Everything that was waiting is now in the checkout: stop calling it new."""
    when = when or time.time()
    for entry in state.get('updates', {}).values():
        if isinstance(entry, dict) and not entry.get('applied'):
            entry['applied'] = when
            entry['new'] = False
    return state


def check():
    """Refresh the cached state from the upstream branch."""
    state = status()
    state['checked'] = time.time()
    if not (SOURCE / '.git').exists():
        state.update(available=False, count=0, error='Not a Git checkout')
        return save(state)
    name = branch()
    if _git(['fetch', '--quiet', '--no-tags', 'origin', name], timeout=60).returncode == 0:
        pending = _log('HEAD..FETCH_HEAD')
        updates = state['updates']
        # Describe the installed history so Update history is never empty.
        local_catalog = _catalog()
        for sha, when, body in _log('HEAD', limit=HISTORY):
            if sha not in updates:
                updates[sha] = _make(sha, when, body, local_catalog.get(sha),
                                     new=False, applied=when)
        # Every fetched commit that is still ahead stays or becomes an entry.
        catalog = _catalog('FETCH_HEAD')
        for sha, when, body in pending:
            meta = catalog.get(sha)
            if sha in updates:
                entry = updates[sha]
                if isinstance(meta, dict):
                    summary, detail, kind = _describe(body, meta)
                    entry.update(summary=summary, detail=detail, kind=kind)
                entry['when'] = entry.get('when') or when
            else:
                updates[sha] = _make(sha, when, body, meta, new=True)
        waiting = [sha for sha, _, _ in pending if updates.get(sha, {}).get('new')]
        tip = pending[0][0] if pending else _out(['rev-parse', '--short=12', 'HEAD'], check=False)
        subject = (updates[waiting[0]]['summary'] if waiting
                   else (updates[pending[0][0]]['summary'] if pending else
                         _out(['log', '-1', '--format=%s'], check=False)))
        state.update(available=bool(waiting), count=len(waiting), sha=tip,
                     subject=subject, error='')
        return save(state)
    # Offline, or an upstream that needs credentials: fall back to the public
    # mirror, which can only compare heads but still detects a new release.
    line = _out(['ls-remote', PUBLIC, f'refs/heads/{name}'], check=False, timeout=30)
    if line:
        remote = line.split()[0]
        local = _out(['rev-parse', 'HEAD'], check=False)
        state.update(available=bool(local and remote != local), count=0,
                     sha=remote[:12], subject='', error='')
        return save(state)
    state['error'] = 'Could not reach GitHub'
    return save(state)


def apply():
    """Pull the checkout, redeploy it and clear the cached update."""
    if not (SOURCE / '.git').exists():
        raise UpdateError('Rice sources are not a Git checkout')
    _out(['pull', '--ff-only', 'origin', branch()], timeout=300)
    installer = SOURCE / 'Installer'
    if not installer.exists():
        raise UpdateError('Installer missing from the checkout')
    command = [str(installer)] if os.access(installer, os.X_OK) else ['bash', str(installer)]
    result = subprocess.run(command + ['--install'], cwd=str(SOURCE), capture_output=True,
                            text=True, timeout=1800, env=_env())
    if result.returncode:
        lines = [line for line in ((result.stdout or '') + '\n' + (result.stderr or '')).splitlines()
                 if line.strip()]
        raise UpdateError(lines[-1][:160] if lines else 'Installer failed')
    subject = _out(['log', '-1', '--format=%s'], check=False)
    state = status()
    _mark_installed(state)
    state.update(available=False, count=0, subject=subject,
                 sha=_out(['rev-parse', '--short=12', 'HEAD'], check=False),
                 notified_sha='', applied=time.time(), error='')
    save(state)
    return subject
