#!/usr/bin/env bash
# Installs the pinned remote tools without credentials or project side effects.
# Safe to rerun on a new/resumed Box. Everything lives in snapshot-backed home.
set -euo pipefail
umask 077
with_herdr=false
case "${1:-}" in
  "") ;;
  --with-herdr) with_herdr=true ;;
  *) echo "Unsupported tooling option" >&2; exit 2 ;;
esac
mkdir -p "$HOME/.local/bin" "$HOME/.box-herdr" "$HOME/.codex" "$HOME/.cursor"
if [ "$(uname -s)-$(uname -m)" != Linux-x86_64 ]; then
  echo 'This template requires a Linux x86_64 Box.' >&2
  exit 1
fi
# One successful tooling check per script revision and Linux boot. A resumed VM
# has a new boot ID, so its kernel sandbox policy is always loaded again.
bootstrap_stamp="$(sha256sum "$0" | cut -d ' ' -f 1):$(cat /proc/sys/kernel/random/boot_id):$with_herdr"
if test -f "$HOME/.box-herdr/bootstrap-ready" &&
   test "$(cat "$HOME/.box-herdr/bootstrap-ready")" = "$bootstrap_stamp" &&
   { ! "$with_herdr" || test -x "$HOME/.local/bin/herdr"; } &&
   test -x "$HOME/.local/bin/pnpm" &&
   test -x "$HOME/.local/bin/infisical"; then
  exit 0
fi
if "$with_herdr" && ! "$HOME/.local/bin/herdr" --version 2>/dev/null | grep -qx 'herdr 0.9.0'; then
  curl --retry 3 -fsSL https://github.com/herdrdev/herdr/releases/download/v0.9.0/herdr-linux-x86_64 -o "$HOME/.local/bin/herdr.download"
  chmod 755 "$HOME/.local/bin/herdr.download"
  mv "$HOME/.local/bin/herdr.download" "$HOME/.local/bin/herdr"
fi
if ! "$HOME/.local/bin/pnpm" --version 2>/dev/null | grep -qx '9.15.4'; then
  npm install --prefix "$HOME/.box-herdr/tools" --no-audit --no-fund pnpm@9.15.4
  ln -sfn "$HOME/.box-herdr/tools/node_modules/.bin/pnpm" "$HOME/.local/bin/pnpm"
fi
export PATH="$HOME/.local/bin:$PATH"
if ! infisical --version 2>/dev/null | grep -q '0.43.121'; then
  cli_archive="$HOME/.box-herdr/infisical.tar.gz"
  curl --retry 3 -fsSL https://github.com/Infisical/cli/releases/download/v0.43.121/cli_0.43.121_linux_amd64.tar.gz -o "$cli_archive"
  printf '0b4f6d13e742c6e6cb67a2f67560aa508308aef277a82360263f56fcbee33be8  %s\n' "$cli_archive" | sha256sum -c -
  tar -xzf "$cli_archive" -C "$HOME/.local/bin" infisical
  rm "$cli_archive"
fi
if [ "$(node -p 'process.versions.node.split(".")[0]')" -lt 24 ]; then
  echo 'Node 24+ is required; current Box images include it.' >&2
  exit 1
fi
command -v bun codex claude cursor-agent git gh python3 rsync google-chrome-stable
# Ubuntu 24.04 needs its distro-provided bubblewrap AppArmor profile. This
# enables Codex's sandbox without disabling global user-namespace restrictions.
# https://learn.chatgpt.com/docs/sandboxing
if ! test -f /etc/apparmor.d/bwrap-userns-restrict; then
  sudo apt-get update -qq
  sudo DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=l apt-get install -y -qq apparmor-profiles apparmor-utils bubblewrap
  sudo install -m 0644 /usr/share/apparmor/extra-profiles/bwrap-userns-restrict /etc/apparmor.d/bwrap-userns-restrict
fi
sudo apparmor_parser -r /etc/apparmor.d/bwrap-userns-restrict
# The normal Box shell exports PATH; add only our user-local tool location.
if ! grep -q '# box-herdr tools' "$HOME/.bashrc"; then
  printf '\n# box-herdr tools\nexport PATH="$HOME/.local/bin:$PATH"\n' >> "$HOME/.bashrc"
fi
if "$with_herdr"; then
  for provider in codex claude cursor; do
    herdr integration install "$provider"
  done
fi
printf 'pnpm=%s\nnode=%s\nbun=%s\ncodex=%s\n' \
  "$(pnpm --version)" "$(node --version)" "$(bun --version)" "$(codex --version)" > "$HOME/.box-herdr/tools-ready"
cat "$HOME/.box-herdr/tools-ready"
printf '%s\n' "$bootstrap_stamp" > "$HOME/.box-herdr/bootstrap-ready"
