#!/usr/bin/env python3
import os, json, glob
ROOT="/home/brewuser/projects/dronemill"
hist_path=f"{ROOT}/output/upload_history.json"
out_dir=f"{ROOT}/output"
if not os.path.exists(hist_path):
    print("No history")
    exit(0)
with open(hist_path) as f:
    hist=json.load(f)
# Build set of local_path where video_id exists
uploaded={e.get("local_path") for e in hist if e.get("video_id") and e.get("local_path")}
# Also check mp4s on disk
for mp4 in glob.glob(f"{out_dir}/*.mp4"):
    base=os.path.basename(mp4)
    if base in uploaded:
        try:
            size=os.path.getsize(mp4)/1024/1024
            os.remove(mp4)
            print(f"Deleted already-uploaded: {base} ({size:.0f} MB)")
        except Exception as e:
            print(f"Failed to delete {base}: {e}")
    else:
        # Check if mp4 exists but history says not uploaded - keep for retry
        pass
# Also clean orphan _master.wav and /tmp hybrids
for wav in glob.glob(f"{out_dir}/*_master.wav"):
    try:
        os.remove(wav)
        print(f"Deleted orphan master wav: {os.path.basename(wav)}")
    except: pass
for pat in [
    f"{ROOT}/tmp/hybrid_dsp_*.wav",
    f"{ROOT}/tmp/hybrid_rb_*.wav",
    "/tmp/hybrid_dsp_*.wav",
    "/tmp/hybrid_rb_*.wav"
]:
    for f in glob.glob(pat):
        try:
            os.remove(f)
            print(f"Deleted tmp: {f}")
        except: pass
print("Cleanup done")
