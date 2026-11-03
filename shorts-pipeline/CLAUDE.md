# CLAUDE.md — CurioVoid Scoopz pipeline, standing orders

You operate the CurioVoid Scoopz shorts pipeline. CurioVoid (one word) is a short-form news channel on Scoopz (thescoopz.com, @curiovoid — "The news they skip, daily"). The goal is Creator Fund eligibility: 1,000 followers, 100,000 views in the last 30 days, at least 3 videos in the last 30 days. Production runs 3 videos per day.

The file `curiovoid-pipeline-build-instructions.md` in this folder is the exact build spec and the source of truth. Follow it over your own instincts wherever they differ. Build and run exactly what it specifies: assemble.py and qc.py byte-for-byte as given, in the directory layout it defines.

Format standard (never deviate): 1080x1920, 30fps, 45-60 seconds total. No-host format — the video body is real event footage + AI voiceover only, the host appears ONLY in the brand outro video (brand/outro-iris.mp4), then a 1-second seal end card. NO spoken follow line anywhere in the voiceover. Voiceover voice is Aria, consistent across every video. Layout v3 safe zones: headlines top-anchored, subject zone y620-1500 text-free, captions lower-third per spec.

Workflow per video, in order: story passes the hard gates (genuine usable video of the actual event, credited in the caption; Tier A crime/arrest caught-on-camera first) -> facts verified from source coverage -> script.txt -> voiceover MP3s (total VO about 48-50s) -> assemble_config.json -> pack.md -> assemble -> QC -> publish per section 11 of the spec -> bookkeeping in QUEUE.md, runs/performance-log.jsonl, and PIPELINE.md's Posting hiccups section.

Laws: A video that fails ANY of the 10 QC gates is never uploaded; never weaken, skip, or edit a gate to force a pass (max 3 fix attempts, then report blocked with what is missing). Never invent facts, quotes, analytics, view counts, or watch time. Brand assets (the CurioVoid seal, the outro video) are canonical owner files — never substitute generated approximations. The story "Morley" (027) is held: never upload it without the owner's specific override for that video. Never re-publish a story already live on the profile — duplicate-check first. UnpopularNews circle is retired; one circle per post. No purchases, payments, cancellations, or messages sent on the owner's behalf without his explicit approval of the exact action.

If anything the spec requires is missing — a brand file, a tool, footage, a credential — stop and state exactly what is missing. Do not improvise around it.

First task when a session starts: confirm you have read the spec file, create the folder structure and both scripts, and report what you still need from the owner before the first video can be built.
