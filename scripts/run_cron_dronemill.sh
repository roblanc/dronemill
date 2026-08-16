#!/bin/bash
# DroneMill Autonomous Cron Job Wrapper
set -e

export PATH="/home/linuxbrew/.linuxbrew/bin:/home/linuxbrew/.linuxbrew/sbin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH"
export HOME="/root"

cd /home/brewuser/projects/dronemill
python3 /home/brewuser/projects/dronemill/scripts/cron_weekly_buffer.py >> /home/brewuser/projects/dronemill/output/cron_buffer.log 2>&1
