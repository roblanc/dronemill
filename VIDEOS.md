# Dronemill — Video List & Backlog

Central list of planned / queued / available ambient videos for @timelessambience55.

This file is the single source of truth for what videos exist as concepts, what is queued, and what assets (images + audio) are ready.

---

## Current Active Queue (`queue.csv`)

```csv
procedural,auto,level_0.txt,0.93
procedural,auto,empty_mall.txt,0.93
procedural,silent terminal | empty airport lobby ambient | sunset liminal space,airport_terminal.txt,0.93
```

**Rendered (full render in pipeline):**  
`frozen 169 years | hms erebus deep ambient | dark arctic drone`  
- Audio: erebus_raw.mp3  
- Image: 013_hms_erebus_1777731330386.png (picked from queue)  
- Pitch: 0.93  
- Output: `output/frozen-169-years-hms-erebus-deep-ambient-dark-arctic-drone.mp4` (2.6 GB, 1h) ✅  
- Status: **Video rendered perfectly.** Upload failed (OAuth token expired/revoked - "invalid_grant").  
  Fix auth per SETUP-YOUTUBE.md, then we can upload the existing file with upload-yt.sh or re-run pipeline.  
  Check if image was marked used or still in queue.

**Rendered locally (liminal spaces with cosmic image):**  
`infinite lobby | level 0 backrooms ambient | yellow wallpaper drone`  
- Audio: liminal_ambient.mp3  
- Image: 017_subglacial_cavern.png (cosmic horror cavern from backup - underground maze feel)  
- Pitch: 0.93  
- Output: `output/infinite-lobby-level-0-backrooms-ambient-yellow-wallpaper-drone.mp4` (2.6 GB, 1h) ✅  
- Status: **Properly matched cosmic image to classic liminal description.** Not using only "liminal spaces" images. Sample + frame created and opened for review. This diversifies the visuals for the queued level_0 etc. (cosmic horror twist on nostalgic backrooms). Image still in queue. Ready for full pipeline.

**Meaning of "procedural,auto"**: Pipeline will auto-generate a good title from the description file + use the oldest available image from queue.

---

## Master Concepts (from `descriptions/`)

These are the ready-made video ideas. Each `.txt` contains full YouTube description, timestamps, tags, and mood.

| Concept              | File                    | First Line / Vibe                                      | Status     | Notes |
|----------------------|-------------------------|-------------------------------------------------------|------------|-------|
| Level 0 (The Lobby)  | level_0.txt            | Infinite yellow wallpaper maze, fluorescent hum       | Queued (auto) | Classic Backrooms |
| Empty Mall           | empty_mall.txt         | 3 AM retro-vaporwave shopping mall, neon, muzak       | Queued (auto) | Mallsoft |
| Airport Terminal     | airport_terminal.txt   | Liminal empty airport at sunset, distant echoes       | Queued (auto) | New in queue |
| Poolrooms            | poolrooms.txt          | Endless clean white tiles, water sounds               | Available | Strong visual match |
| Infinite Hotel       | infinite_hotel.txt     | Endless hotel corridors                               | Available | - |
| Library              | library.txt            | Infinite dark library aisles                          | Available | - |
| Classroom            | classroom.txt          | Empty school classroom, golden hour                   | Available | - |
| Laundromat           | laundromat.txt         | Empty laundromat at 3 AM, humming machines            | Available | - |
| Playplace            | playplace.txt          | Empty children's playground at night                  | Available | - |
| Lost in the Tiles    | lost_in_the_tiles.txt  | Surreal poolrooms / tile labyrinth                    | Available | Overlaps with poolrooms |
| Suburban Street      | suburban_street.txt    | Empty identical suburban street at night              | Available | - |
| Train Station        | train_station.txt      | Empty concrete transit platform at night              | Available | - |
| Template (Erebus)    | template.txt           | HMS Erebus arctic expedition, frozen ship, cosmic horror | Available | Good for deep drone |

**How to use**: Point `queue.csv` at a description file (or use "auto" + procedural mode).

---

## Pending / Generated Visuals

Images sitting in `images/queue/backup/` (not yet moved to main queue). These were generated for cosmic horror / liminal / arctic themes.

**Count**: 20 images

List (sorted):
- 004_cthulhu_harbor_...
- 005_drowned_cathedral_...
- 006_submerged_ruins_...
- 007_coastal_village_wave_...
- 008_antarctic_splitting_...
- 009_basalt_shoreline_...
- 010_ships_wheel_...
- 011_whale_fall_...
- 012_pier_midnight_...
- 013_hms_erebus_...
- 014_ice_cathedral_...
- 015_ice_floe_tent_...
- 016_mammoth_bone_...
- 017_subglacial_cavern_...
- cosmic_horror_ambience_cover_...
- cosmic_horror_landscape_1080p_...
- lovecraftian_lighthouse_painterly_...
- media__... (2 files)
- openrouter_image_gen_python_code_... (probably a test)

**Important note on images vs descriptions** (after proper audit):
- Backup images (20 new): **cosmic horror / arctic / ruins style** (cthulhu harbor, drowned cathedral, submerged ruins, antarctic, hms erebus, ice cathedral, subglacial cavern, whale fall, pier midnight, lovecraftian lighthouse etc.). These are **not** clean "liminal spaces" (yellow wallpaper, fluorescent malls). They are dark, monstrous, expedition horror — perfect for cosmic horror ambient or "horror-tinged liminal".
- Dedicated "liminal spaces" image: only 019_poolrooms.png (endless tiles + water) + older numbered ones in used/.
- Descriptions: mostly "nostalgic liminal space" (level_0 yellow maze, empty_mall, airport, hotel, library etc.) + poolrooms specific + 1 cosmic template (erebus).
- Matching rule: Use poolrooms image for poolrooms/liminal tiles. Use backup cosmic images for level_0/empty_mall/airport etc. to give them a horror/cosmic edge (not "tot imagine de liminal spaces"). Pure nostalgic liminal would need more clean empty-space images (not in current backup).

**Recommendation**: Move the best-matching ones into `images/queue/` when you want to queue a specific concept (e.g. Erebus images with the arctic template, cavern image with level_0 for underground maze horror).

Already used images live in `images/used/`.

---

## Available Audio Sources (`audio/used/`)

Long ambient tracks ready to be paired with images + descriptions.

- analog_loops.mp3
- erebus_raw.mp3 (strong match for arctic / Erebus concept)
- liminal_ambience.mp3
- liminal_ambient.mp3
- lost_in_liminal.mp3
- no_one_here.mp3
- the_complex.mp3
- Several "The Backrooms", "Poolrooms", "Dreamcore" playlists (found footage style)

**Note**: The pipeline supports pitch shifting (0.85 = deep doom, 0.93 = default subtle, 1.07 = alien high).

---

## Production Notes

- Typical output: 1-hour videos
- Naming: slugified title → `output/slugified-title.mp4`
- Title format (branding): `[hook 3-5 words] | [main descriptor] | [tag/duration]`
- Upload cadence: usually scheduled daily at ~18:00 local via `scheduler.sh`
- After successful upload: image moves from queue → used, entry can be removed from queue.csv

**Current queue.csv is very light.** Most "work" is currently in the description concepts + the 20 backup images.

---

## Suggested Next Steps / How to Add to the List

1. **To queue an existing concept**:
   - Add a line to `queue.csv`: `audio_file.mp3,"Exact Title Here",description_file.txt,0.93`
   - Or use `procedural,auto,description_file.txt,0.93` for auto title generation.

2. **To use one of the backup images**:
   - Move the chosen PNG from `images/queue/backup/` to `images/queue/`
   - The pipeline will pick the oldest first when in auto mode.

3. **To generate a completely new one**:
   - Use `autopilot.py` (it searches YouTube for new liminal audio, generates title + image prompt via LLM, creates image, then runs the pipeline).

4. **Just render without uploading**:
   ```bash
   cd scripts
   ./render-only.sh ../audio/erebus_raw.mp3 "the ice remembers | hms erebus ambient | 1 hour" 0.93
   ```

---

## Backlog Items (from BACKLOG.md + current state)

- [ ] Move promising images from `backup/` into active `queue/`
- [ ] Expand `queue.csv` with more explicit entries from the master descriptions
- [ ] Improve batch processing (currently autopilot is the main automation)
- [ ] Create better matching between images in backup and specific description concepts
- [ ] Consider adding a `status` column or separate `PLANNED.md` (this file can evolve into that)

---

**This file (VIDEOS.md) is now the human-readable master list.**

Update it whenever you add new concepts, generate new images, or finish videos.

Last updated: by AI assistant after project audit.
