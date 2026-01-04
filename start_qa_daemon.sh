echo "🚀 Starting Vidurai Daemon (QA Mode)..."
export PYTHONPATH=$PYTHONPATH:$(pwd)
python3 vidurai-daemon/daemon.py
