#!/bin/zsh
# Morning scan: run yfinance screen, commit scan.json, push to GitHub. Logs to scan.log.
cd "$(dirname "$0")" || exit 1
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
echo "=== $(date '+%Y-%m-%d %H:%M') ===" >> scan.log
./venv/bin/python scan.py >> scan.log 2>&1 || { echo "scan failed" >> scan.log; exit 1; }
git add scan.json && git commit -qm "scan $(date '+%Y-%m-%d')" >> scan.log 2>&1
git push -q origin main >> scan.log 2>&1 && echo "pushed" >> scan.log
