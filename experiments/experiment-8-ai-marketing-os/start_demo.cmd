@echo off
cd /d "%~dp0"
echo AI Marketing OS classroom demo
echo Open http://127.0.0.1:8503 in your browser.
echo Keep this window open. Press Ctrl+C to stop.
python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8503 --server.headless true --browser.gatherUsageStats false
if errorlevel 1 (
  echo Launch failed. See docs/classroom_walkthrough.md for troubleshooting.
  pause
)
