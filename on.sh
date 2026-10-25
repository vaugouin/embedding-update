#!/bin/bash
# Switch embedding-update.sh back on: removes the flag file CRON_OFF that off.sh wrote.
cd "$(dirname "$(readlink -f "$0")")" || exit 1
# A launcher renamed by the old off.sh (<name>-off.sh, before 2026-10-25) is put back,
# or dropped when git has already restored the tracked one.
[ -f embedding-update-off.sh ] && { [ -f embedding-update.sh ] && rm -f embedding-update-off.sh || mv embedding-update-off.sh embedding-update.sh; }
rm -f CRON_OFF && echo "embedding-update: on (CRON_OFF removed)"
