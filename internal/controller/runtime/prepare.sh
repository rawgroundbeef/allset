#!/usr/bin/env bash
# Project preparation requires explicit setup commands in the private profile.
set -euo pipefail
printf '%s\n' 'This task has no project setup profile. Configure its setup commands before preparing it.' >&2
exit 1
