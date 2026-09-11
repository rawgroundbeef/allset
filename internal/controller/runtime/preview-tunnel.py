#!/usr/bin/env python3
"""Keep a stable local listener while individual pinned SSH connections reconnect."""

import errno
import json
import os
from pathlib import Path
import selectors
import signal
import socket
import socketserver
import subprocess
import sys
import threading


class Tunnel(socketserver.ThreadingTCPServer):
    """Own one IPv6 loopback port; existing listeners are never replaced."""
    address_family = socket.AF_INET6
    daemon_threads = True
    allow_reuse_address = True


class Tunnel4(Tunnel):
    """Accept native local HTTPS proxies that dial IPv4 loopback."""
    address_family = socket.AF_INET


class Connection(socketserver.BaseRequestHandler):
    """Forward one browser connection through SSH; a new request rereads the current host alias."""
    def handle(self):
        """Pump raw HTTP/WebSocket bytes without inspecting or logging credentials."""
        config = self.server.config
        args = ['ssh', '-T', '-o', 'ControlMaster=auto', '-o', 'ControlPersist=60',
                '-o', 'ControlPath=' + config['control_path'], '-W',
                '127.0.0.1:' + str(config['remote_port']), config['ssh_alias']]
        with subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                              stderr=subprocess.DEVNULL, bufsize=0) as child:
            selector = selectors.DefaultSelector()
            selector.register(self.request, selectors.EVENT_READ, 'browser')
            selector.register(child.stdout, selectors.EVENT_READ, 'ssh')
            try:
                while True:
                    events = selector.select(60)
                    if not events and child.poll() is not None:
                        return
                    for key, _ in events:
                        if key.data == 'browser':
                            data = self.request.recv(65536)
                            if not data:
                                return
                            child.stdin.write(data)
                        else:
                            data = os.read(child.stdout.fileno(), 65536)
                            if not data:
                                return
                            self.request.sendall(data)
            except (BrokenPipeError, ConnectionError, OSError):
                pass
            finally:
                selector.close()
                child.terminate()


def main():
    """Bind before publishing readiness so concurrent task launches cannot claim the same port."""
    path = Path(sys.argv[1])
    config = json.loads(path.read_text())
    for attempt in range(10):
        try:
            server = Tunnel(('::1', config.get('local_port', 0)), Connection)
        except OSError as error:
            if error.errno != errno.EADDRINUSE: raise
            config['local_port'] = 0
            continue
        try:
            server4 = Tunnel4(('127.0.0.1', server.server_address[1]), Connection)
            break
        except OSError as error:
            server.server_close()
            if error.errno != errno.EADDRINUSE: raise
            config['local_port'] = 0
    else: raise RuntimeError('No free pair of loopback listeners')
    with server, server4:
        server.config = server4.config = config
        config.update(local_port=server.server_address[1], pid=os.getpid(), state='listening')
        temporary = path.with_suffix('.tmp')
        temporary.write_text(json.dumps(config)); temporary.chmod(0o600); temporary.replace(path)
        threading.Thread(target=server4.serve_forever, daemon=True).start()
        signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
        server.serve_forever()


if __name__ == '__main__':
    main()
