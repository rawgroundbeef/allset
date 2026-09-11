"""Preparation feedback, released before an interactive terminal takes over."""
import os
import sys
import threading
import time
import unicodedata

_active = None


def clean(value):
    # Project names, branches and account labels must not control the terminal.
    return ''.join(ch if not unicodedata.category(ch).startswith('C') else ' ' for ch in str(value))


def elapsed(seconds):
    seconds = max(0, int(seconds))
    return f'{seconds // 60}m {seconds % 60:02d}s' if seconds >= 60 else f'{seconds}s'


def stage(key, title, detail=''):
    if _active is not None:
        _active.update(key, title, detail)
    else:
        print(clean(title) + (' — ' + clean(detail) if detail else ''), flush=True)


def note(message):
    if _active is not None:
        _active.note(message)
    else:
        print(clean(message), flush=True)


def active():
    return _active is not None


class Progress:
    """One current phase plus completed rows; plain text when output is captured.

    Callers report actual work, never estimated percentages. The worker only
    redraws text: it owns no provider operation and cannot outlive this scope.
    """
    def __init__(self, stream=None, *, summary='Workspace prepared'):
        self.stream = stream if stream is not None else sys.stdout
        self.summary = clean(summary)
        self.animated = self.stream.isatty() and os.environ.get('TERM') != 'dumb'
        self.color = self.animated and 'NO_COLOR' not in os.environ
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.worker = None
        self.started = time.monotonic()
        self.key = self.title = self.detail = ''
        self.notes = []
        self.frame = 0

    def __enter__(self):
        global _active
        if _active is not None:
            raise RuntimeError('Preparation display already active')
        _active = self
        self.started = time.monotonic()
        if self.animated:
            self.worker = threading.Thread(target=self.animate, name='allset-progress', daemon=True)
            self.worker.start()
        return self

    def write(self, text):
        self.stream.write(text)
        self.stream.flush()

    def row(self, marker, text, color='36'):
        mark = f'\033[{color}m{marker}\033[0m' if self.color else marker
        return f'  {mark} {text}'

    def clear(self):
        if self.animated:
            self.write('\r\033[2K')

    def draw(self):
        if not self.key:
            return
        try:
            width = os.get_terminal_size(self.stream.fileno()).columns or 80
        except (OSError, ValueError, AttributeError):
            width = 80
        suffix = ' · ' + elapsed(time.monotonic() - self.started)
        if width < len(suffix) + 8:
            suffix = ''
        text = self.title + (' — ' + self.detail if self.detail else '')
        # Keep the live row on one line even in a narrow pane or after resize.
        budget = max(0, width - 5 - len(suffix))
        fitted, cells = '', 0
        for char in text:
            size = 0 if unicodedata.combining(char) else (2 if unicodedata.east_asian_width(char) in ('W', 'F') else 1)
            if cells + size > budget:
                break
            fitted += char
            cells += size
        self.clear()
        self.write(self.row('⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'[self.frame % 10], fitted + suffix))
        self.frame += 1

    def animate(self):
        while not self.stop.wait(0.1):
            with self.lock:
                self.draw()

    def update(self, key, title, detail=''):
        title, detail = clean(title), clean(detail)
        with self.lock:
            if (key, title, detail) == (self.key, self.title, self.detail):
                return
            if self.animated and self.key and key != self.key:
                self.clear()
                self.write(self.row('✓', self.title, '32') + '\n')
            self.key, self.title, self.detail = key, title, detail
            if self.animated:
                self.draw()
            else:
                self.write(title + (' — ' + detail if detail else '') + '\n')

    def note(self, message):
        with self.lock:
            message = clean(message)
            if message not in self.notes:
                self.notes.append(message)

    def __exit__(self, kind, error, traceback):
        global _active
        self.stop.set()
        if self.worker is not None:
            self.worker.join()
        _active = None
        with self.lock:
            self.clear()
            if kind is None:
                if self.key and self.animated:
                    self.write(self.row('✓', self.title, '32') + '\n')
                self.write(self.row('✓', self.summary + ' · ' + elapsed(time.monotonic() - self.started), '32') + '\n')
            else:
                title = 'Stopped waiting' if issubclass(kind, KeyboardInterrupt) else 'Could not finish'
                self.write(self.row('!', title + (': ' + self.title if self.title else ''), '33') + '\n')
            for message in self.notes:
                self.write('  ' + message + '\n')
        return False
