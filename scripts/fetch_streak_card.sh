#!/usr/bin/env bash
# Snapshot the streak card into the repo.
#
# streak-stats.demolab.com runs on Heroku behind cf-cache-status: DYNAMIC, so every
# request hits the origin and takes 10-18s. GitHub's camo proxy gives up at ~5s, so
# hotlinking the card renders a broken image roughly three times out of four.
# Serving a committed copy from GitHub raw takes camo out of the loop entirely.
#
# A failed fetch leaves the previously committed SVG in place: a card that is one day
# stale beats a card that is broken.
set -uo pipefail

BASE="https://streak-stats.demolab.com"
COMMON="user=${CARD_USER:-Jah-yee}&type=svg&border_radius=12&ring=FA5C21&fire=FA5C21"

# Geometry and palette match the ghfind card this sits beside: 12px radius, and a
# hairline border made from the accent at 32% over the card background.
LIGHT="$COMMON&background=ffffff&border=FDCBB8&currStreakLabel=1f2328&sideLabels=656d76&dates=afb8c1&currStreakNum=1f2328&sideNums=1f2328"
DARK="$COMMON&background=0a0a0b&border=59291A&currStreakLabel=f4f4f5&sideLabels=a1a1aa&dates=52525b&currStreakNum=f4f4f5&sideNums=f4f4f5"

fetch() {
  local out=$1 query=$2 i
  for i in 1 2 3 4 5; do
    if curl -fsS --max-time 45 -o "$out.tmp" "$BASE?$query" \
       && head -c 4 "$out.tmp" | grep -q '<svg'; then
      mv "$out.tmp" "$out"
      echo "ok: $out"
      return 0
    fi
    echo "attempt $i failed for $out; retrying in 10s"
    sleep 10
  done
  rm -f "$out.tmp"
  echo "WARNING: could not refresh $out; keeping the committed copy" >&2
  return 0
}

mkdir -p cards
fetch cards/streak-light.svg "$LIGHT"
fetch cards/streak-dark.svg  "$DARK"
