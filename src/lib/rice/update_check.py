#!/usr/bin/env python3
"""Find rice updates on the configured Git upstream and install them.

status() only reads the cached state, so the settings panel never blocks on the
network. check() talks to the upstream and refreshes that cache, apply() pulls
the checkout and re-runs the installer. The desktop watcher calls check() on a
timer and turns a new upstream commit into a notification.
"""
import json
import os
from pathlib import Path
import subprocess
import time

HOME = Path.home()
SOURCE = HOME / '.local/share/rice/source'
STATE = HOME / '.local/state/rice'
FILE = STATE / 'update.json'
PUBLIC = 'https://github.com/SandwichEater577/Nestea-s-Hyprland-Rice.git'
ISSUES = 'https://github.com/SandwichEater577/Nestea-s-Hyprland-Rice/issues/new'
CHECK_SECONDS = 1800


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


def notify_update(state):
    # Urgency critical keeps the message on screen until it is dismissed; a five
    # second toast is too easy to miss for something that happens once a week.
    count = state.get('count') or 0
    detail = f"{count} new commit{'s' if count != 1 else ''}" if count else 'New commits ready'
    subject = (state.get('subject') or '').strip()
    if subject:
        detail += ' · ' + (subject if len(subject) <= 60 else subject[:57] + '…')
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
    for key, default in (('available', False), ('count', 0), ('subject', ''),
                         ('sha', ''), ('checked', 0), ('notified_sha', ''),
                         ('error', '')):
        state.setdefault(key, default)
    return state


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


def check():
    """Refresh the cached state from the upstream branch."""
    state = status()
    state['checked'] = time.time()
    if not (SOURCE / '.git').exists():
        state.update(available=False, error='Not a Git checkout')
        return save(state)
    name = branch()
    if _git(['fetch', '--quiet', '--no-tags', 'origin', name], timeout=60).returncode == 0:
        count = _out(['rev-list', '--count', 'HEAD..FETCH_HEAD'], check=False)
        state.update(available=bool(count and int(count) > 0),
                     count=int(count or 0),
                     sha=_out(['rev-parse', 'FETCH_HEAD'], check=False)[:12],
                     subject=_out(['log', '-1', '--format=%s', 'FETCH_HEAD'], check=False),
                     error='')
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
    state.update(available=False, count=0, subject=subject,
                 sha=_out(['rev-parse', 'HEAD'], check=False)[:12],
                 notified_sha='', applied=time.time(), error='')
    save(state)
    return subject
