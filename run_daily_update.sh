#!/bin/bash
# Wrapper script for cron job to ensure proper environment

cd /home/absent/HermesAnalysis

# Set environment variables (replace with your actual values)
export HERMES_TELEGRAM_BOT_TOKEN="8777529075:AAGCRT_mV8EhrRQwTRNexk3--XU5t2nYQXQ"
export HERMES_TELEGRAM_CHAT_ID="6331906646"

# Ensure virtual environment or proper Python path
export PYTHONPATH="/home/absent/HermesAnalysis/src:$PYTHONPATH"

# Run the update script with the correct python
/home/absent/colabfold/localcolabfold/colabfold-conda/bin/python3 scripts/daily_update_notify.py

# Log completion
echo "Cron job completed at $(date)" >> logs/cron.log