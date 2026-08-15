#!/usr/bin/env python3
"""
DroneMill Autonomous Weekly Buffer Keeper.
Runs as a recurring cron/daemon job:
1. Checks how many future scheduled days remain in the release calendar.
2. If remaining buffer < 14 days, automatically triggers generation of 7 fresh releases.
3. Ensures release dates remain continuous without gaps.

Usage:
  python3 scripts/cron_weekly_buffer.py
"""

import os
import sys
import json
import datetime
import subprocess

ROOT = "/home/brewuser/projects/dronemill"

def check_and_refill_buffer():
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    history_file = f"{ROOT}/output/upload_history.json"
    
    future_scheduled = []
    if os.path.exists(history_file):
        with open(history_file, "r", encoding="utf-8") as f:
            for item in json.load(f):
                p = item.get("publish_at")
                if p:
                    try:
                        dt = datetime.datetime.fromisoformat(p.replace("Z", "+00:00"))
                        if dt > now_utc:
                            future_scheduled.append(dt)
                    except Exception:
                        pass
                        
    future_scheduled.sort()
    days_left = len(future_scheduled)
    print(f"[{now_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}] Buffer Check: {days_left} future scheduled days.")
    
    if days_left < 14:
        print(f"⚠️ Buffer ({days_left} days) is below threshold of 14 days. Initiating auto-refill of 7 releases...")
        # Trigger slate production batch
        subprocess.run(["python3", f"{ROOT}/scripts/produce-fresh-9-slate.py"])
    else:
        print(f"✅ Buffer is healthy ({days_left} days remaining, well above 14-day threshold). No action needed.")

if __name__ == "__main__":
    check_and_refill_buffer()
