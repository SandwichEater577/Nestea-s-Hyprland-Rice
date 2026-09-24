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

"new" is the only flag the UI asks about. The settings menu shows View update
while any entry is new, Ignore flips that entry back to false, and apply()
installs the selected commit while leaving newer releases pending. Descriptions are resolved in this order:
src/data/updates.json, then Rice-Update-* commit trailers, then the commit
subject and body.
"""
import json
import os
from pathlib import Path
import re
import select
import shlex
import subprocess
import time
from collections import deque
from telemetry import maybe_check_in

HOME = Path.home()
SOURCE = HOME / '.local/share/rice/source'
STATE = HOME / '.local/state/rice'
FILE = STATE / 'update.json'
INSTALLED_REVISION = STATE / 'installed-revision'
PROGRESS_FILE = STATE / 'update-progress.json'
REQUEST_FILE = STATE / 'update-request.json'
PUBLIC = 'https://github.com/SandwichEater577/Nestea-s-Hyprland-Rice.git'
ISSUES = 'https://github.com/SandwichEater577/Nestea-s-Hyprland-Rice/issues/new'
CHECK_SECONDS = 1800
KINDS = ('optional', 'recommended', 'mandatory')
HISTORY = 20  # installed commits kept described in the Update history window
TRAILER = re.compile(r'^Rice-Update-(Summary|Detail|Kind|ID):[ \t]*(.*)$')
UPDATE_ID = re.compile(r'^0x[0-9a-fA-F]{5}$')
GIT_PROGRESS = re.compile(r'(Receiving objects|Resolving deltas):\s*\d+%\s*\((\d+)/(\d+)\)')
INSTALL_STEP = re.compile(r'^RICE_PROGRESS_STEP=(\d+)\t(.*)$')


class UpdateError(RuntimeError):
    pass


def _env():
    # Never prompt: a credential or passphrase dialog would hang a user service.
    env = dict(os.environ)
    ssh_config = HOME / '.ssh/config'
    ssh_config = ssh_config if ssh_config.is_file() else Path('/dev/null')
    env.update(GIT_TERMINAL_PROMPT='0',
               GIT_SSH_COMMAND=f'ssh -F {shlex.quote(str(ssh_config))} '
                               '-o BatchMode=yes -o ConnectTimeout=10')
    return env


def _git(args, timeout=45):
    return subprocess.run(['git', '-C', str(SOURCE), *args], capture_output=True,
                          text=True, timeout=timeout, env=_env())


def _out(args, check=True, timeout=45):
    result = _git(args, timeout=timeout)
    if check and result.returncode:
        raise UpdateError((result.stderr or result.stdout).strip() or 'git failed')
    return (result.stdout or '').strip()


def _run_stream(command, timeout, on_line=None, cwd=None, env=None):
    """Run a command without hiding its carriage-return progress or losing timeouts."""
    process = subprocess.Popen(command, cwd=cwd, env=env or _env(),
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    recent = deque(maxlen=20)
    pending = b''
    deadline = time.monotonic() + timeout

    def accept(raw):
        line = raw.decode('utf-8', 'replace').strip()
        if line:
            recent.append(line)
            if on_line:
                on_line(line)

    try:
        while True:
            if time.monotonic() >= deadline:
                raise UpdateError(f'{command[0]} timed out')
            ready, _, _ = select.select([process.stdout], [], [], 0.2)
            if not ready:
                continue
            chunk = os.read(process.stdout.fileno(), 4096)
            if not chunk:
                break
            parts = re.split(b'[\r\n]', pending + chunk)
            pending = parts.pop()
            for part in parts:
                accept(part)
        if pending:
            accept(pending)
        if process.wait(timeout=max(1, deadline - time.monotonic())):
            raise UpdateError(recent[-1] if recent else f'{command[0]} failed')
    except (OSError, subprocess.TimeoutExpired):
        raise UpdateError(f'{command[0]} failed or timed out')
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        process.stdout.close()


def read_progress():
    try:
        return json.loads(PROGRESS_FILE.read_text())
    except (OSError, ValueError):
        return {}


def write_progress(**fields):
    STATE.mkdir(parents=True, exist_ok=True)
    temp = PROGRESS_FILE.with_suffix('.tmp')
    temp.write_text(json.dumps(dict(fields, at=time.time())) + '\n')
    temp.replace(PROGRESS_FILE)


def write_request(sha):
    if not re.fullmatch(r'[0-9a-f]{12}', sha):
        raise UpdateError('Invalid update ID')
    STATE.mkdir(parents=True, exist_ok=True)
    temp = REQUEST_FILE.with_suffix('.tmp')
    temp.write_text(json.dumps({'sha': sha, 'at': time.time()}) + '\n')
    temp.replace(REQUEST_FILE)


def take_request():
    try:
        data = json.loads(REQUEST_FILE.read_text())
    except (OSError, ValueError):
        return None
    REQUEST_FILE.unlink(missing_ok=True)
    sha = data.get('sha') if isinstance(data, dict) else None
    if not isinstance(sha, str) or not re.fullmatch(r'[0-9a-f]{12}', sha):
        raise UpdateError('Invalid update request')
    if not isinstance(data.get('at'), (int, float)) or time.time() - data['at'] > 60:
        raise UpdateError('Update request expired; open the update again')
    return sha


def notify(title, body, icon='dialog-information-symbolic', urgency=None):
    args = ['notify-send', '-a', 'Rice', '-i', icon]
    if urgency:
        args += ['-u', urgency]
    subprocess.run(args + [title, body], capture_output=True, timeout=20, env=_env())


def pending_updates(state):
    """Entries still waiting to be downloaded, newest commit first."""
    found = [(sha, entry) for sha, entry in (state.get('updates') or {}).items()
             if entry.get('new') and not entry.get('applied')]
    found.sort(key=lambda item: (item[1].get('kind') == 'mandatory',
                                 item[1].get('when') or 0), reverse=True)
    return found


def display_name(entry):
    summary = entry.get('summary') or 'Rice update'
    identifier = entry.get('id') or ''
    return summary if not identifier or summary.startswith(identifier + ' ') else identifier + ' · ' + summary


def notify_update(state):
    # Urgency critical keeps the message on screen until it is dismissed; a five
    # second toast is too easy to miss for something that happens once a week.
    waiting = pending_updates(state)
    count = len(waiting)
    summary = (display_name(waiting[0][1]) if waiting else '') or (state.get('subject') or '').strip()
    detail = f"{count} new commit{'s' if count != 1 else ''}" if count else 'New commits ready'
    if summary:
        detail += ' · ' + (summary if len(summary) <= 60 else summary[:57] + '…')
    notify('Rice update available', detail + '\nSettings → View update',
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
        for key, default in (('new', False), ('summary', ''), ('detail', ''), ('id', ''),
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
        if entry.get('kind') == 'mandatory':
            return state
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


def _update_id(body, meta):
    value = str((meta or {}).get('id') or _trailers(body).get('ID') or '').strip()
    return value.lower() if UPDATE_ID.fullmatch(value) else ''


def _make(sha, when, body, meta, new, applied=0):
    summary, detail, kind = _describe(body, meta)
    try:
        when = float(when)
    except (TypeError, ValueError):
        when = 0.0
    return {'new': bool(new), 'summary': summary, 'detail': detail, 'kind': kind,
            'id': _update_id(body, meta),
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


def _installed_revision():
    """Commit last deployed by the installer, independent of checkout HEAD."""
    try:
        revision = INSTALLED_REVISION.read_text().strip()
    except OSError:
        return ''
    if not re.fullmatch(r'[0-9a-f]{40}', revision):
        return ''
    return revision if _git(['cat-file', '-e', revision + '^{commit}']).returncode == 0 else ''


def check():
    """Refresh the cached state from the upstream branch."""
    maybe_check_in()
    state = status()
    state['checked'] = time.time()
    if not (SOURCE / '.git').exists():
        state.update(available=False, count=0, error='Not a Git checkout')
        return save(state)
    name = branch()
    if _git(['fetch', '--quiet', '--no-tags', 'origin', name], timeout=60).returncode == 0:
        installed = _installed_revision()
        if installed and _git(['merge-base', '--is-ancestor', installed, 'FETCH_HEAD']).returncode == 0:
            pending = _log(f'{installed}..FETCH_HEAD')
        elif state.get('applied'):
            # Older installs have no revision marker. Their last successful
            # install time is safer than HEAD, which may already contain an
            # unpublished or locally committed update.
            pending = [item for item in _log('FETCH_HEAD')
                       if item[1] > state['applied']]
        else:
            pending = _log('HEAD..FETCH_HEAD')
        updates = state['updates']
        # Describe the installed history so Update history is never empty.
        local_catalog = _catalog()
        for sha, when, body in _log(installed or 'HEAD', limit=HISTORY):
            if sha not in updates:
                updates[sha] = _make(sha, when, body, local_catalog.get(sha),
                                     new=False, applied=when)
            elif not updates[sha].get('id'):
                updates[sha]['id'] = _update_id(body, local_catalog.get(sha))
        # Every fetched commit that is still ahead stays or becomes an entry.
        catalog = _catalog('FETCH_HEAD')
        for sha, when, body in pending:
            meta = catalog.get(sha)
            if sha in updates:
                entry = updates[sha]
                if entry.get('applied'):
                    # A previous check may have mistaken a commit in this
                    # development checkout for an installed update.
                    entry['applied'] = 0
                    entry['new'] = True
                entry['id'] = _update_id(body, meta)
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
        local = _installed_revision() or _out(['rev-parse', 'HEAD'], check=False)
        state.update(available=bool(local and remote != local), count=0,
                     sha=remote[:12], subject='', error='')
        return save(state)
    state['error'] = 'Could not reach GitHub'
    return save(state)


def apply(selected=None, progress=None):
    """Install one selected release snapshot and leave later releases pending."""
    if not (SOURCE / '.git').exists():
        raise UpdateError('Rice sources are not a Git checkout')
    def report(**fields):
        if progress:
            progress(**fields)

    report(phase='download', task='Checking for update files', done=0, total=0)

    def git_line(line):
        match = GIT_PROGRESS.search(line)
        if match:
            operation, done, total = match[1], int(match[2]), int(match[3])
            report(phase='download', task=operation, done=done, total=total)

    _run_stream(['git', '-C', str(SOURCE), 'fetch', '--progress', '--no-tags',
                 'origin', branch()], timeout=300, on_line=git_line)
    releases = _log('FETCH_HEAD')
    requested = selected is not None
    selected = str(selected if requested else (releases[0][0] if releases else ''))
    target = next((sha for sha, _, _ in releases if sha == selected), None)
    state = status()
    if not target or (requested and selected not in state['updates']):
        raise UpdateError('Selected update is no longer available')
    installed = _installed_revision()
    if installed and _git(['merge-base', '--is-ancestor', installed, target]).returncode:
        raise UpdateError('This update predates the installed release')
    if state['updates'].get(target, {}).get('applied'):
        raise UpdateError('This update is already installed')
    report(phase='download', task='Download complete', done=1, total=1)
    report(phase='install', task='Preparing selected release', done=0, total=5)
    head = _out(['rev-parse', 'HEAD'])
    clean = not _out(['status', '--porcelain'], check=False)
    if clean and _git(['merge-base', '--is-ancestor', head, target]).returncode == 0:
        # Keep the user's normal checkout as the installed source when the
        # selected release can safely advance it.
        _out(['merge', '--ff-only', target], timeout=300)
        release_dir = SOURCE.resolve()
    else:
        # An older selection must not reset or overwrite the user's checkout.
        release_dir = STATE / 'releases' / target
        if release_dir.exists():
            if _out(['-C', str(release_dir), 'rev-parse', '--short=12', 'HEAD']) != target:
                raise UpdateError('Selected release directory contains another revision')
        else:
            release_dir.parent.mkdir(parents=True, exist_ok=True)
            _out(['worktree', 'add', '--detach', str(release_dir), target], timeout=300)
    report(phase='install', task='Applying local settings', done=1, total=5)
    installer = release_dir / 'Installer'
    if not installer.exists():
        raise UpdateError('Installer missing from the checkout')
    command = [str(installer)] if os.access(installer, os.X_OK) else ['bash', str(installer)]

    def install_line(line):
        match = INSTALL_STEP.match(line)
        if match:
            step = int(match[1])
            report(phase='install', task=match[2], done=min(step, 5), total=5)

    install_env = _env()
    install_env['RICE_UPDATE_PROGRESS'] = '1'
    _run_stream(command + ['--install'], cwd=str(release_dir), timeout=1800,
                env=install_env, on_line=install_line)
    subject = next(body.splitlines()[0] for sha, _, body in releases if sha == target)
    when = time.time()
    for sha, entry in state['updates'].items():
        if not entry.get('applied') and _git(['merge-base', '--is-ancestor', sha, target]).returncode == 0:
            entry.update(applied=when, new=False)
    waiting = pending_updates(state)
    state.update(available=bool(waiting), count=len(waiting), subject=subject,
                 sha=releases[0][0], notified_sha='', applied=when, error='')
    save(state)
    return subject
