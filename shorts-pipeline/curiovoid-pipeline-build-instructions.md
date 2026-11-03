# BUILD INSTRUCTIONS — CurioVoid Scoopz Shorts Pipeline (exact rebuild)

**For Claude:** This file instructs you to build, from scratch, a working copy of the
CurioVoid short-form news video pipeline: story intake → script → AI voiceover →
programmatic editing/assembly (ffmpeg) → a 10-gate automated QC → publishing to
Scoopz. Build it exactly as specified. The two Python programs in §6 and §7 are
complete and verbatim — save them byte-for-byte. Where this file and your instincts
disagree, this file wins: every number in it was earned from a real failure.

**Owner context:** The channel is **CurioVoid** (one word) — short-form news on
Scoopz (thescoopz.com), handle @curiovoid, bio "The news they skip, daily."
Output: 45–60s vertical videos, 3 per day, built from real event footage
(dashcam/bodycam/news clips) with an AI voiceover. The current format is
**no-host**: the video body is footage + voiceover only; the host (Iris) appears
ONLY in a pre-made outro video appended at the end. There is NO spoken
"follow" line in the voiceover — that was retired; do not reintroduce it.

---

## 1. Requirements

- Linux machine, `ffmpeg`/`ffprobe` (built against 8.1.2), Python 3 with
  `Pillow` and `numpy`.
- Font: **Liberation Sans** (Bold) installed at
  `/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf` — the caption
  width measurement in both programs loads this exact path. If your distro puts
  it elsewhere, install `fonts-liberation` rather than editing the path.
- `yt-dlp` for footage sourcing.
- A TTS voice (see §5). The reference voice is named **Aria**
  (voice id `avocado_v2:MAI_01` in the owner's runtime). If your environment has
  a different TTS, use a comparable warm female newsreader voice and keep it
  CONSISTENT across every video — voice consistency is the channel's identity.
  Do NOT use the runtime's default voice; the owner rejected it as "way off".
- RAM caution: the reference box has ~7.7 GB. Run ONE heavy render at a time;
  check `free -h` before a dissolve/assembly. Never stage large files in `/tmp`
  (it may be a small tmpfs — the reference box's is 512 MB); use workspace disk.

## 2. Directory layout

```
shorts-pipeline/
  assemble.py            # §6, verbatim
  qc.py                  # §7, verbatim
  PIPELINE.md            # living spec + "Posting hiccups" log (you maintain)
  QUEUE.md               # published/queued story ledger (you maintain)
  brand/
    curiovoid-seal-master.png   # canonical seal, 1600x1600 (owner-supplied, §3)
    logo.jpg                    # 1600x1600, derived from the seal master
    logo-circle.png             # 480x480 RGBA circular seal (watermark)
    follow-pill.png             # 560x128 RGBA "follow" pill graphic
    outro-iris.mp4              # canonical outro video (§3)
  runs/
    performance-log.jsonl       # one line per run, updated IN PLACE
    YYYY-MM-DD-<slug>/          # one folder per video (§4)
      script.txt
      assemble_config.json
      pack.md
      audio/vo-a-hook.mp3
      audio/vo-b-story.mp3
      footage/<source clip>
      host/placeholder.mp4      # unused in no-host mode, still required as an input slot
      (generated) vo-full.wav, vo-list.txt, words.json, captions.ass,
      scoopz-final.mp4, qc/*.jpg
```

## 3. Brand assets (owner-supplied — do NOT generate substitutes)

These are canonical brand files. **Never replace the seal with a generated
approximation** — a generated seal garbles the lettering and the owner rejects
it on sight. Get the originals from the owner.

- `curiovoid-seal-master.png` — 1600×1600, the gold CurioVoid v6 seal
  (pyramid/eye emblem, "CURIOVOID" lettering, concentric target circles in the
  center — there is NO eyeball in the center; an eyeball-centered seal is a
  generator invention). Reference MD5 of the canonical file:
  `d87e03b1dbb39f741c7999dad830a4f4`. If the owner's file hashes differently,
  use the owner's file anyway — his copy is the source of truth.
- `logo.jpg` — 1600×1600 JPEG derived from the seal master (used for the seal
  end card, scaled to 880×880 by the assembler).
- `logo-circle.png` — 480×480 RGBA, the seal in a circle (used as the corner
  watermark, scaled to 130×130 at 0.9 alpha).
- `follow-pill.png` — 560×128 RGBA pill graphic (shown bottom-center, final 3s).
- `outro-iris.mp4` — 720×1280, 24 fps, 7.93 s, h264 + AAC **with its own audio
  track** (the outro's audio is part of the format; the assembler concatenates
  it after the VO). Content: the host at a server-monitor wall turning to
  camera. The QC brand gate (§7) frame-correlates the finished video against
  THIS file, so whatever sits at this path defines the standard.

## 4. Run folder inputs

### 4.1 `script.txt` — segment-marked VO script

Exact format (note the bracket tags; the assembler parses them):

```
[HOST-A — hook]
An ICE officer's own body camera is now the prosecution's star witness — and on Monday, he turned himself in.

[FOOTAGE — VO over bodycam/surveillance]
October tenth, near Clay Road in Houston. Federal officers tried to stop a white pickup, and two men ran. ...

[HOST-B — close]
This is the outro segment. Not spoken.
```

Rules:
- In the current no-host + outro format only TWO segments are spoken: the
  `[HOST-A]` hook text is narrated over the OPENING FOOTAGE (there is no host
  clip), and the `[FOOTAGE]` text is the story body. `[HOST-B]` is a stub —
  keep the tag, put a placeholder line, it is never voiced.
- Write numbers the way they should be SPOKEN ("October tenth",
  "thirty-thousand-dollar bond", "nine-one-one") — TTS mangles raw digits.
- No spoken follow/CTA clause anywhere. The word "follow" must not appear in
  the spoken text at all (QC gate `content.noclause` counts it).
- Length budget: final video must land 45–60 s TOTAL, and the outro (7.93 s) +
  end card (1.0 s) come out of that. **Target total VO ≈ 48–50 s** (hook ~5–7 s
  + story ~42–44 s). An early Houston cut ran 61 s of VO and failed the
  duration gate — trim the script, never weaken the gate.

### 4.2 `assemble_config.json` — per-run edit decision list

Real example from a published run (steal this shape):

```json
{
 "band_crop": "360:202:0:330",
 "footage": "footage/source-news.mp4",
 "footage_cuts": [[0.0, 22.0], [23.0, 42.0]],
 "headline_events": [[0.0, null, "HIS OWN BODYCAM\\NINDICTED HIM"]],
 "host_a": "host/placeholder.mp4",
 "host_b": "host/placeholder.mp4",
 "nohost": true,
 "outro": "brand/outro-iris.mp4"
}
```

Fields:
- `footage` — path (run-relative) to the source clip.
- `band_crop` — ffmpeg crop string `w:h:x:y` selecting the clean band of the
  source. Sources are often low-res (360×640) or split-screen (e.g. a news
  clip with surveillance on top, bodycam below): crop to the ONE band that
  carries the story and has no burned-in news graphics crossing it.
- `footage_cuts` — list of `[start, end]` source-second windows to keep, in
  order. Cut OUT dead windows (empty highway, sky/hedge footage, anchor
  intros). In no-host mode the assembler retimes the kept windows to cover the
  full VO (see §8) — a slowdown factor near 0.9–1.25× reads as natural dashcam
  motion; if your factor lands far outside that, pick better windows.
- `headline_events` — `[start_offset, end_offset_or_null, "TEXT"]` timed
  relative to the footage segment (which in no-host mode starts at t=0).
  `null` end = until the segment ends. Use `\N` for the line break. Headline
  style: ≤2 lines, short, does not spoil the whole outcome (an open loop
  out-retains a summary). It renders top-anchored (see §8 safe zones).
- `nohost: true` and `outro: "brand/outro-iris.mp4"` — the current format.
  Both keys are REQUIRED for the current format; the legacy host mode
  (bookend host clips, spoken close) exists in the code but is RETIRED —
  do not use it.

### 4.3 `pack.md` — the publishing pack (written by you per run)

Contains, verbatim-ready:
- **Title** — also the first line of the caption.
- **Caption** — ONE Scoopz text field: title line, then the caption body,
  then a footage credit line `Footage: <source>, via <outlet>.`, then
  hashtags. Credit is mandatory — the channel only posts credited footage.
- **Pinned comment** — the author's first comment, posted verbatim after
  publishing. Standard shape: a genuine either/or question about the video
  plus the line `Follow for tomorrow's — we post 3x a day.`
- **Facts** — the verified fact list the script was built from (dates,
  names, charges, denials/fairness notes). Facts are verified from source
  coverage BEFORE scripting; never invent a detail, a quote, or a number.

## 5. Voiceover production

- Generate two MP3s from `script.txt` in the channel voice (Aria, §1):
  `audio/vo-a-hook.mp3` = the `[HOST-A]` text; `audio/vo-b-story.mp3` = the
  `[FOOTAGE]` text. (A third close segment existed in the retired host
  format; in outro mode it is not produced.)
- Probe both durations (`ffprobe`). If hook + story > ~51 s, trim the SCRIPT
  and re-generate — do not time-stretch audio to fit.
- If the VO changes after an assembly, DELETE `words.json` and
  `captions.ass` in the run folder before re-assembling. The assembler
  regenerates both from `script.txt` on every run, and stale copies are how
  caption/VO mismatches slip past a tired operator. (A words-only spelling
  fix with unchanged audio is the one exception: fix the word in
  `words.json` in place and keep timings.)

## 6. `assemble.py` — save verbatim as `shorts-pipeline/assemble.py`

Usage: `python3 assemble.py <run_dir>`. It prints a `DONE ... duration=...`
line on success — trust ONLY that line plus a fresh `ffprobe` of the output
(never a piped exit code; `tee` and friends mask assembler death).

```python
#!/usr/bin/env python3
"""CurioVoid Scoopz assembler (rebuilt Nov 2, 2026 from the locked PIPELINE.md spec).

Host-embedded format: Iris host clip (hook) -> footage segment -> Iris host clip
(close) -> seal end card. VO is one continuous TTS track across all segments.

Usage: assemble.py <run_dir>
Run dir must contain: audio/vo-a-hook.mp3, audio/vo-b-story.mp3,
audio/vo-c-close.mp3, footage cuts config in assemble_config.json,
host/host-a.mp4, host/host-b.mp4, script.txt (segments marked by [HOST-A]/[FOOTAGE]/[HOST-B]).
Writes: vo-full.wav, words.json, captions.ass, scoopz-final.mp4
"""
import json, math, os, re, subprocess, sys

RUN = os.path.abspath(sys.argv[1])
PIPE = os.path.dirname(os.path.abspath(__file__))
BRAND = os.path.join(PIPE, 'brand')
CFG = json.load(open(os.path.join(RUN, 'assemble_config.json')))
# Outro format (Nov 2, 2026, Jacob's order): no HOST-B / spoken follow line.
# VO = hook + story; the Iris outro video (CFG['outro'], pipeline-relative)
# replaces the close segment, with its own audio; seal end card still follows.
OUTRO_MODE = bool(CFG.get('outro'))
OUTRO_PATH = os.path.join(PIPE, CFG['outro']) if OUTRO_MODE else None
# No-host format (Nov 2, 2026, Jacob's order): Iris appears ONLY in the outro.
# Body = footage + full VO (hook line narrated over the opening footage).
NOHOST = bool(CFG.get('nohost'))

def sh(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        print(r.stdout[-2000:]); print(r.stderr[-3000:]); sys.exit(f'FAILED: {cmd[0]}')
    return r

def probe_dur(path):
    r = sh(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'csv=p=0', path])
    return float(r.stdout.strip())

# --- 1. VO track: concat the segments gapless, 44.1kHz wav --------------------
segs_audio = ['audio/vo-a-hook.mp3', 'audio/vo-b-story.mp3'] if OUTRO_MODE else \
             ['audio/vo-a-hook.mp3', 'audio/vo-b-story.mp3', 'audio/vo-c-close.mp3']
durs = [probe_dur(os.path.join(RUN, p)) for p in segs_audio]
listfile = os.path.join(RUN, 'vo-list.txt')
with open(listfile, 'w') as f:
    for p in segs_audio:
        f.write(f"file '{os.path.join(RUN, p)}'\n")
sh(['ffmpeg', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', listfile,
    '-ar', '44100', '-ac', '1', os.path.join(RUN, 'vo-full.wav'), '-y'])
vo_total = sum(durs)
ENDCARD = 1.0
outro_dur = probe_dur(OUTRO_PATH) if OUTRO_MODE else 0.0
total = vo_total + outro_dur + ENDCARD
print(f'VO segments: {[round(d,3) for d in durs]} total={vo_total:.3f} outro={outro_dur:.3f} video={total:.3f}')

# --- 2. words.json from script.txt --------------------------------------------
raw = open(os.path.join(RUN, 'script.txt')).read()
blocks = re.split(r'\[(HOST-A|FOOTAGE|HOST-B)[^\]]*\]\s*', raw)
seg_texts = {}
it = iter(blocks[1:])
for tag, text in zip(it, it):
    seg_texts[tag] = ' '.join(text.split())
order = [('FOOTAGE', seg_texts['HOST-A']), ('FOOTAGE', seg_texts['FOOTAGE'])] if NOHOST else \
        [('HOST-A', seg_texts['HOST-A']), ('FOOTAGE', seg_texts['FOOTAGE'])] if OUTRO_MODE else \
        [('HOST-A', seg_texts['HOST-A']), ('FOOTAGE', seg_texts['FOOTAGE']),
         ('HOST-B', seg_texts['HOST-B'])]
words = []
t = 0.0
for (tag, text), dur in zip(order, durs):
    ws = text.split()
    weights = [max(len(w.strip('—–-.,!?"\'')), 1) for w in ws]
    wsum = sum(weights)
    for w, wt in zip(ws, weights):
        wdur = dur * wt / wsum
        words.append({'w': w, 'start': round(t, 3), 'end': round(t + wdur, 3), 'seg': tag})
        t += wdur
if NOHOST:
    _segments = [{'tag': 'FOOTAGE', 'start': 0.0, 'dur': round(vo_total, 3)}]
else:
    _segments = [{'tag': tag, 'start': round(sum(durs[:i]), 3), 'dur': round(durs[i], 3)}
                 for i, (tag, _) in enumerate(order)]
json.dump({'segments': _segments, 'words': words},
          open(os.path.join(RUN, 'words.json'), 'w'), indent=1)
print(f'words.json: {len(words)} words')

# --- 3. captions.ass ------------------------------------------------------------
def ts(sec):
    h = int(sec // 3600); m = int(sec % 3600 // 60); s = sec % 60
    return f'{h}:{m:02d}:{s:05.2f}'

# group words into caption chunks by MEASURED pixel width (Liberation Sans
# Bold 64px, budget 920px inside the 960px margin box) and max 5 words;
# WrapStyle 2 never auto-wraps, so an over-wide chunk clips off-frame.
# Break on sentence punctuation too.
from PIL import ImageFont
_capfont = ImageFont.truetype('/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf', 64)
def _capw(ws):
    return _capfont.getlength(' '.join(w['w'] for w in ws))
chunks, cur = [], []
for wd in words:
    trial = cur + [wd]
    if cur and (_capw(trial) > 920 or len(trial) > 5):
        chunks.append(cur); cur = [wd]
    else:
        cur = trial
    if wd['w'].endswith(('.', '!', '?', ':')):
        chunks.append(cur); cur = []
if cur: chunks.append(cur)

ass = ["""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,Liberation Sans,64,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,4,1,2,60,60,480,1
Style: Headline,Liberation Sans,88,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,5,1,8,60,60,140,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""]
for c in chunks:
    text = ' '.join(w['w'] for w in c)
    ass.append(f"Dialogue: 0,{ts(c[0]['start'])},{ts(c[-1]['end'])},Caption,,0,0,0,,{text}")
seg2_start, seg2_end = (0.0, vo_total) if NOHOST else (durs[0], durs[0] + durs[1])
for line_start, line_end, text in CFG['headline_events']:
    s = seg2_start + line_start; e = seg2_start + (line_end if line_end else (seg2_end - seg2_start))
    ass.append(f"Dialogue: 1,{ts(s)},{ts(e)},Headline,,0,0,0,,{text}")
open(os.path.join(RUN, 'captions.ass'), 'w').write('\n'.join(ass) + '\n')
print(f'captions.ass: {len(chunks)} caption chunks, {len(CFG["headline_events"])} headline events')

# --- 4. ffmpeg assembly ---------------------------------------------------------
foot = os.path.join(RUN, CFG['footage'])
crop = CFG['band_crop']  # "360:202:0:222"
cuts = CFG['footage_cuts']  # [[start, end], ...] in source seconds
fc = []
# footage windows
win_labels = []
for i, (s, e) in enumerate(cuts):
    fc.append(f"[0:v]trim=start={s}:end={e},setpts=PTS-STARTPTS,crop={crop},setsar=1,split=2[fg{i}][bg{i}]")
    fc.append(f"[bg{i}]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=42,eq=brightness=-0.28[bgb{i}]")
    fc.append(f"[fg{i}]scale=1080:608[fgc{i}]")
    fc.append(f"[bgb{i}][fgc{i}]overlay=0:700,setsar=1[fwin{i}]")
    win_labels.append(f'[fwin{i}]')
if NOHOST:
    # footage must cover the FULL VO: retime the cut windows (89%-style slowdown
    # reads as natural dashcam motion; never pad with dead source or freezes)
    _avail = sum(e - s for s, e in cuts)
    _factor = vo_total / _avail
    fc.append(''.join(win_labels) + f'concat=n={len(cuts)}:v=1:a=0,setpts={_factor:.4f}*PTS,fps=30,tpad=stop_mode=clone:stop_duration=2,trim=duration={vo_total:.3f}[seg2]')
    print(f'nohost: footage {_avail:.2f}s retimed x{_factor:.4f} -> {vo_total:.3f}s')
else:
    fc.append(''.join(win_labels) + f'concat=n={len(cuts)}:v=1:a=0,fps=30,tpad=stop_mode=clone:stop_duration=2,trim=duration={durs[1]:.3f}[seg2]')
# host segments (seg3 = outro video in outro mode, else the HOST-B close clip)
if not NOHOST:
    fc.append(f"[1:v]scale=1080:1920,setsar=1,fps=30,trim=duration={durs[0]:.3f},setpts=PTS-STARTPTS[seg1]")
if OUTRO_MODE:
    fc.append(f"[2:v]scale=1080:1920,setsar=1,fps=30,trim=duration={outro_dur:.3f},setpts=PTS-STARTPTS[seg3]")
else:
    fc.append(f"[2:v]scale=1080:1920,setsar=1,fps=30,trim=duration={durs[2]:.3f},setpts=PTS-STARTPTS[seg3]")
# end card: black + seal centered
fc.append(f"color=c=black:s=1080x1920:r=30:d={ENDCARD}[cardbg]")
fc.append(f"[3:v]scale=880:880[cardlogo]")
fc.append(f"[cardbg][cardlogo]overlay=(W-w)/2:(H-h)/2[seg4]")
fc.append("[seg2][seg3][seg4]concat=n=3:v=1:a=0[base]" if NOHOST else
          "[seg1][seg2][seg3][seg4]concat=n=4:v=1:a=0[base]")
# watermark (not on end card: enable only before total-ENDCARD)
fc.append(f"[4:v]scale=130:130,format=rgba,colorchannelmixer=aa=0.9[wm]")
fc.append(f"[base][wm]overlay=W-w-28:36:enable='lt(t,{total - ENDCARD:.3f})'[marked]")
# follow pill: final 3.0s of the whole video
fc.append(f"[5:v]format=rgba[pill]")
fc.append(f"[marked][pill]overlay=(W-w)/2:1665:enable='between(t,{total-3.0:.3f},{total:.3f})'[pilled]")
fc.append(f"[pilled]ass={os.path.join(RUN, 'captions.ass')}[vout]")
if OUTRO_MODE:
    # audio: VO track, then the outro's own audio, then silence over the end card
    fc.append(f"[6:a]aresample=44100,aformat=sample_rates=44100:channel_layouts=mono[voa]")
    fc.append(f"[2:a]aresample=44100,aformat=sample_rates=44100:channel_layouts=mono[outa]")
    fc.append(f"[voa][outa]concat=n=2:v=0:a=1,apad=whole_dur={total:.3f},atrim=duration={total:.3f}[aout]")
else:
    fc.append(f"[6:a]aresample=44100,apad=whole_dur={total:.3f},atrim=duration={total:.3f}[aout]")

out = os.path.join(RUN, 'scoopz-final.mp4')
cmd = ['ffmpeg', '-v', 'error', '-stats',
       '-i', foot,
       '-i', os.path.join(RUN, CFG.get('host_a', 'host/host-a.mp4')),
       '-i', OUTRO_PATH if OUTRO_MODE else os.path.join(RUN, CFG.get('host_b', 'host/host-b.mp4')),
       '-i', os.path.join(BRAND, 'logo.jpg'),
       '-i', os.path.join(BRAND, 'logo-circle.png'),
       '-i', os.path.join(BRAND, 'follow-pill.png'),
       '-i', os.path.join(RUN, 'vo-full.wav'),
       '-filter_complex', ';'.join(fc),
       '-map', '[vout]', '-map', '[aout]',
       '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-r', '30',
       '-c:a', 'aac', '-b:a', '160k', '-ar', '44100',
       '-movflags', '+faststart', out, '-y']
r = subprocess.run(cmd, capture_output=True, text=True)
if r.returncode != 0:
    print(r.stderr[-9000:]); sys.exit('ffmpeg FAILED')
dur = probe_dur(out)
print(f'DONE {out} duration={dur:.2f} size={os.path.getsize(out)}')
```

## 7. `qc.py` — save verbatim as `shorts-pipeline/qc.py`

Usage: `python3 qc.py <run_dir>`. Exit code 0 and `QC RESULT: ALL PASS` is the
only publishable outcome (see §10 QC law).

```python
#!/usr/bin/env python3
"""CurioVoid Scoopz QC gate (rebuilt Nov 2, 2026 from the locked PIPELINE.md spec).

Usage: qc.py <run_dir>
Checks scoopz-final.mp4 + words.json + captions.ass. Prints PASS/FAIL per gate
and exits non-zero if any gate fails. Also extracts QC frames for eyeballing.
"""
import json, os, re, subprocess, sys

RUN = os.path.abspath(sys.argv[1])
FINAL = os.path.join(RUN, 'scoopz-final.mp4')
fails = []

def gate(name, ok, detail=''):
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}")
    if not ok: fails.append(name)

def sh(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)

def probe(path):
    r = sh(['ffprobe', '-v', 'error', '-show_entries',
            'stream=codec_type,codec_name,width,height,avg_frame_rate,sample_rate',
            '-show_entries', 'format=duration', '-of', 'json', path])
    return json.loads(r.stdout)

# --- format gate ---------------------------------------------------------------
info = probe(FINAL)
v = next(s for s in info['streams'] if s['codec_type'] == 'video')
a = next(s for s in info['streams'] if s['codec_type'] == 'audio')
dur = float(info['format']['duration'])
fps = eval(v['avg_frame_rate'])
gate('format.spec', v['width'] == 1080 and v['height'] == 1920 and abs(fps - 30) < 0.6
     and v['codec_name'] == 'h264' and a['codec_name'] == 'aac' and a['sample_rate'] == '44100',
     f"{v['width']}x{v['height']}@{fps:.2f} {v['codec_name']}/{a['codec_name']}@{a['sample_rate']}")
gate('format.duration', 45.0 <= dur <= 60.0, f'{dur:.2f}s')

# --- content gates on words.json (actual VO words) ------------------------------
wj = json.load(open(os.path.join(RUN, 'words.json')))
norm = ' '.join(w['w'].lower().strip('.,!?"\'—–-') for w in wj['words'])
follow_hits = [(w['w'], w['seg']) for w in wj['words'] if w['w'].lower().strip('.,!?"') == 'follow']
last_seg = wj['segments'][-1]['tag']
OUTRO_FMT = 'HOST-A' not in [s['tag'] for s in wj['segments']]  # outro video closes; covers no-host format too
if OUTRO_FMT:
    # Brand gate (outro standard, Nov 2 2026): the Iris outro video must be the
    # closing segment. Verify by frame correlation at mid-outro vs the master.
    import numpy as np
    from PIL import Image
    vo_end = sum(s['dur'] for s in wj['segments'])
    t_mid = vo_end + 3.5
    outro_master = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'brand', 'outro-iris.mp4')
    fa, fb = os.path.join(RUN, 'qc', '_brand_a.jpg'), os.path.join(RUN, 'qc', '_brand_b.jpg')
    os.makedirs(os.path.join(RUN, 'qc'), exist_ok=True)
    sh(['ffmpeg', '-v', 'error', '-ss', str(t_mid), '-i', FINAL, '-frames:v', '1', fa, '-y'])
    sh(['ffmpeg', '-v', 'error', '-ss', '3.5', '-i', outro_master, '-frames:v', '1', fb, '-y'])
    try:
        ia = np.asarray(Image.open(fa).convert('L').resize((160, 284)), dtype=float).ravel()
        ib = np.asarray(Image.open(fb).convert('L').resize((160, 284)), dtype=float).ravel()
        corr = float(np.corrcoef(ia, ib)[0, 1])
    except Exception:
        corr = -1.0
    gate('content.brand', corr >= 0.80, f'outro frame correlation at {t_mid:.1f}s: {corr:.3f} (>=0.80)')
    gate('content.noclause', len(follow_hits) == 0,
         f'no spoken follow clause in VO (outro standard); hits: {follow_hits}')
else:
    gate('content.brand', 'curio void' in norm, '"curio void" present in VO words')
    gate('content.noclause', len(follow_hits) == 1 and follow_hits[0][1] == last_seg,
         f'follow occurrences: {follow_hits}')

# --- layout gates on captions.ass ------------------------------------------------
ass = open(os.path.join(RUN, 'captions.ass')).read()
def style_marginv(style_name):
    for line in ass.splitlines():
        if line.startswith(f'Style: {style_name},'):
            parts = line.split(',')
            # Style fields: 0 name, 18 Alignment, 19 MarginL, 20 MarginR, 21 MarginV
            return int(parts[21])
    return None
cap_mv_val = style_marginv('Caption')
head_mv_val = style_marginv('Headline')
gate('layout.captions_marginv', cap_mv_val is not None and 430 <= cap_mv_val <= 520,
     f"Caption MarginV={cap_mv_val}")
gate('layout.headline_marginv', head_mv_val is not None and head_mv_val <= 200,
     f"Headline MarginV={head_mv_val} (top-anchored, must end by y580)")

def ass_t(s):
    h, m, sec = s.split(':'); return int(h) * 3600 + int(m) * 60 + float(sec)
seg2 = next(s for s in wj['segments'] if s['tag'] == 'FOOTAGE')
head_events = [l for l in ass.splitlines() if l.startswith('Dialogue: 1,')]
ok_head = True
for l in head_events:
    parts = l.split(',', 9)
    if ass_t(parts[1]) < seg2['start'] - 0.05 or ass_t(parts[2]) > seg2['start'] + seg2['dur'] + 0.05:
        ok_head = False
gate('layout.headline_window', ok_head and len(head_events) >= 1,
     f'{len(head_events)} headline event(s), confined to footage segment')

cap_events = [l for l in ass.splitlines() if l.startswith('Dialogue: 0,')]
from PIL import ImageFont
_capfont = ImageFont.truetype('/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf', 64)
overlong = []
for l in cap_events:
    text = l.split(',', 9)[9].replace('\\N', ' ')
    wpx = _capfont.getlength(text)
    if wpx > 1000:
        overlong.append(f'{text!r} = {wpx:.0f}px')
gate('layout.caption_width', not overlong,
     f'caption lines >1000px measured: {overlong if overlong else "none"} ({len(cap_events)} caption events)')

# --- visual freeze gate on the footage segment ------------------------------------
r = sh(['ffmpeg', '-v', 'info', '-ss', str(seg2['start']), '-i', FINAL,
        '-t', str(seg2['dur']), '-vf', 'freezedetect=n=0.003:d=1.5', '-an', '-f', 'null', '-'])
freezes = re.findall(r'freeze_duration: ([\d.]+)', r.stderr)
gate('visual.freeze', not freezes, f'freezes>1.5s: {freezes if freezes else "none"}')

# --- audio presence ----------------------------------------------------------------
r = sh(['ffmpeg', '-v', 'info', '-i', FINAL, '-af', 'volumedetect', '-vn', '-f', 'null', '-'])
mean = re.search(r'mean_volume: (-[\d.]+) dB', r.stderr)
gate('audio.present', mean and float(mean.group(1)) > -45, f"mean_volume={mean.group(1) if mean else '?'} dB")

# --- QC frames for visual inspection --------------------------------------------------
os.makedirs(os.path.join(RUN, 'qc'), exist_ok=True)
for name, t in [('host-open', 3.0), ('footage', seg2['start'] + 6), ('footage-late', seg2['start'] + seg2['dur'] - 5),
                ('host-close-pill', dur - 1.6), ('endcard', dur - 0.4)]:
    sh(['ffmpeg', '-v', 'error', '-ss', str(t), '-i', FINAL, '-frames:v', '1',
        os.path.join(RUN, 'qc', f'{name}.jpg'), '-y'])
print(f'QC frames in {os.path.join(RUN, "qc")}')

print('QC RESULT:', 'ALL PASS' if not fails else f'FAILED: {fails}')
sys.exit(1 if fails else 0)
```

### The 10 gates

| Gate | What it enforces |
|---|---|
| `format.spec` | 1080×1920, ~30 fps, h264, AAC at 44100 Hz |
| `format.duration` | total runtime 45.0–60.0 s |
| `content.brand` | outro present: frame at VO-end + 3.5 s correlates ≥ 0.80 with `brand/outro-iris.mp4` at 3.5 s |
| `content.noclause` | the word "follow" appears ZERO times in the spoken VO |
| `layout.captions_marginv` | Caption style MarginV within 430–520 (current build: 480) |
| `layout.headline_marginv` | Headline style MarginV ≤ 200 (current: 140, top-anchored) |
| `layout.headline_window` | ≥1 headline event, all confined to the footage segment |
| `layout.caption_width` | every caption line measures ≤ 1000 px (Liberation Sans Bold 64 px) |
| `visual.freeze` | no freeze > 1.5 s inside the footage segment (ffmpeg freezedetect) |
| `audio.present` | mean volume > −45 dB (the video is not silent) |

QC also extracts five frames (`qc/host-open.jpg`, `footage.jpg`,
`footage-late.jpg`, `host-close-pill.jpg`, `endcard.jpg`). **A human/agent
must actually LOOK at these frames** before publishing — the scripted gates
do not catch a wrong band crop, a garbled headline, or dead footage.

## 8. Editing feature inventory (what the assembler actually does)

- **Canvas:** 1080×1920, 30 fps, libx264 crf 18 / preset medium, AAC 160k at
  44.1 kHz, `+faststart`. (Final AAC MUST be `-ar 44100` or `format.spec`
  fails — learned the hard way.)
- **Footage treatment (the "window" look):** each kept source window is
  band-cropped, then split in two: a **background** copy scaled to fill
  1080×1920, gaussian-blurred (`gblur=sigma=42`) and darkened
  (`eq=brightness=-0.28`); and a **foreground** copy scaled to 1080×608 and
  overlaid at `y=700`. Result: low-res 360p source sits as a clean 16:9-ish
  band in the middle of the frame over its own blurred backdrop. A 360p
  source upscales acceptably this way.
- **Layout v3 safe zones (locked):** subject zone **y620–1500 stays
  text-free**; headlines live above it, captions below it.
  - Headline style: Liberation Sans Bold 88 px, top-anchored, MarginV 140,
    max ~2 lines / ≤120 px per line, must end by y580.
  - Caption style: Liberation Sans Bold 64 px, bottom-anchored, MarginV 480.
- **Captions are generated, never hand-timed:** the assembler estimates word
  timings by distributing each VO segment's real duration across its words
  weighted by character length, then chunks words into caption cards by
  MEASURED pixel width (≤920 px at build time, ≤5 words per card, break at
  sentence punctuation). ASS `WrapStyle 2` never auto-wraps — an over-wide
  card clips off-frame, which is why chunking is measured, not estimated.
- **Retiming (no-host):** kept footage windows are concatenated and
  `setpts`-scaled by `VO_duration / available_footage` so real footage —
  never a freeze or pad — covers the whole narration. A `tpad` clone-pad +
  trim is only a safety net; `visual.freeze` fails the video if a freeze
  > 1.5 s survives.
- **Watermark:** circular seal, 130×130, alpha 0.9, top-right (28 px in,
  36 px down), present for the whole video EXCEPT the end card.
- **Follow pill:** `brand/follow-pill.png` bottom-center at y=1665, shown
  only in the final 3.0 s (over the outro).
- **Outro:** the canonical outro video (720×1280) is scaled to 1080×1920;
  audio chain is VO → outro's own audio → silence padded/trimmed to the
  exact total.
- **Seal end card:** final 1.0 s — black background, `logo.jpg` at 880×880
  centered. Nothing else. No text, no watermark.
- **Segment order (current format):** [footage + full VO] → [outro] →
  [end card]. Total = VO + 7.93 + 1.0.

## 9. Production workflow (per video, in order)

1. **Story selection — hard gates, no exceptions:**
   - **Video-only gate:** the story must have genuine, usable video of the
     ACTUAL event, creditable in the caption. Stills-only stories are
     rejected, however good the story is.
   - **Tiers:** Tier A (visceral real event — crime/arrest caught on camera
     is the channel's verified best niche) is #1 whenever one verifies;
     Tier B human drama second; Tier C talking/policy only when no A/B
     verifies. Stories come from the last ~48 h.
   - Verify every fact from the source coverage (names, dates, charges,
     outcomes, and the other side's denial where one exists) BEFORE
     scripting. Never repeat a story already on the profile (check
     `QUEUE.md` + the live profile).
2. **Source the footage** into `footage/`. YouTube via yt-dlp: the default
   web route hits a "sign in to confirm you're not a bot" wall; use
   `--extractor-args youtube:player_client=android` (format 18, 640×360,
   downloads cleanly). Some news-site CDNs (PerimeterX) block scripted
   fetches entirely — use the outlet's syndicated/YouTube copy instead.
3. **Pick the band + windows:** watch the source; set `band_crop` to the
   clean story band; list `footage_cuts` excluding dead windows (empty
   road, sky, anchor desk, replay slates). The excluded window in the
   reference "Hop On" run was 13 s of empty highway — nobody retains that.
4. **Write `script.txt`** (§4.1), **generate the two VO MP3s** (§5), check
   durations against the ~51 s budget.
5. **Write `assemble_config.json`** (§4.2) and **`pack.md`** (§4.3).
6. **Assemble:** `python3 assemble.py <run_dir>` — require the `DONE` line,
   then `ffprobe` the output's duration yourself.
7. **QC:** `python3 qc.py <run_dir>` — require `ALL PASS`, then EYEBALL the
   five QC frames (§7).
8. **Publish** (§11) with the pack's caption + pinned comment verbatim.
9. **Bookkeep** (§13) the same run, every run.

## 10. QC law

- A video that does not pass **10/10** is NEVER uploaded. Fix the cause and
  re-run the FULL QC (max 3 attempts), or report the run blocked with what
  is missing.
- **Never weaken, skip, or edit a gate to force a pass.** Every gate in §7
  exists because its failure already shipped once.
- A scripted pass is necessary, not sufficient: the QC frames get a visual
  check too (band crop right? headline legible and inside its zone?
  footage-late frame still real event footage? pill + end card clean?).

## 11. Publishing to Scoopz (proven route — deviations are how publishes fail)

- Enter through the target circle page's **"Create a post"** button
  (`thescoopz.com/c/<circle>`). NEVER use the bare `thescoopz.com/upload`
  picker — its file input cannot be driven reliably.
- Sign in as CurioVoid via **"Continue with Google"**. A saved site password
  does not substitute for the Google flow.
- Stage the MP4 at a world-readable path (`chmod 644`) on workspace disk
  BEFORE the upload attempt.
- **Duplicate-check before every upload:** scan the profile + circle feed
  for the story. Never re-publish anything already live.
- **One upload at a time**, with a gap after each publish. If an attach
  stalls, STOP the attempt and relaunch fresh — never park an upload on a
  "tap the file for me" prompt, and never retry-storm (silent picker
  failures fit an anti-spam throttle).
- Circle rules: **one circle per post.** TrueCrime bans fully-AI videos
  (this format is real footage + VO, which is fine); Bodycam is raw footage
  only (this VO format is excluded there); PublicFreakout needs a genuine
  freakout; USPolitics is the natural home for political/enforcement
  stories. **UnpopularNews is RETIRED — never post there.**
- After publishing, post the pack's **pinned comment verbatim as the first
  comment**. The web UI has NO pin control — first comment is first/only by
  position. **Never click unnamed buttons near comments** — one turned out
  to be a vote control and briefly set a comment's score to −1.
- **Verification:** a success toast is NOT proof. Verify from a FRESH
  profile load: post count incremented, tile opens, video plays, comment
  sits first. New posts can sit on a "Your video is processing..." card for
  a long while (one took >2.5 h) and cold-loaded share links 404 during
  propagation — neither is proof of failure. Feed comment counters can be
  stale; read the comment panel itself.
- **Deletes are unreliable:** "Video deleted successfully" + a 404 URL does
  NOT prove removal — the profile tile/modal can keep playing the deleted
  video for hours (a ghost). Judge deletes by the profile modal's
  playability over time, and expect a ghost window after any delete.
- Circle changes are moves, not copies: delete the old post first (owner's
  explicit order), accept the ghost window, then repost to the new circle.

## 12. ffmpeg / tooling traps (all previously paid for)

- `setsar=1` is required on zoompan AND footage branches and after overlay:
  `scale ... force_original_aspect_ratio=increase` silently changes SAR and
  breaks concat.
- Re-cuts of finished videos: cut with `-ss`/`-t` INPUT seeking into
  separate files + the concat demuxer. `trim`/`atrim` with nonzero starts
  is broken on finals.
- A runtime restart can kill an assembly mid-write and leave a final with
  no moov atom — check the output's duration/mtime, and relaunch clean
  rather than trying to repair the corpse.
- Check `free -h` before heavy assemblies; renders die mid-mux under RAM
  pressure.
- The assembler's config key for headline text uses ASS `\N` for line
  breaks; in JSON that is written `"...\\N..."`.

## 13. Bookkeeping (same run, every run)

- `runs/performance-log.jsonl` — one line per published video; update the
  run's line IN PLACE, never append a duplicate line for the same publish
  (a materially different publish event, e.g. a repost, gets its own line).
- `QUEUE.md` — record what published where, with the live URL; record held
  items as held.
- **Posting hiccups:** after EVERY publish attempt, append what broke and
  the workaround that fixed it to `PIPELINE.md`'s "Posting hiccups" section
  (owner's standing order). Future-you is the audience.
- Report verified numbers only (followers, views, post counts as observed
  on the profile) — never invent analytics, watch time, or CTR; the web
  dashboard exposes none of the latter.

## 14. Channel standing rules (owner's orders — treat as law)

- The name is **CurioVoid**, one word, on everything.
- The spoken follow line is RETIRED; the outro video is the close (§0).
- **Morley (story 027) is HELD** — never upload it without the owner's
  specific override for that video.
- No purchases, payments, cancellations, subscription or account-security
  changes, and no messages sent on the owner's behalf, without his explicit
  approval of the EXACT action.
- Trash files, never permanently delete, unless he approves that exact item.

## 15. Dormant systems (in the code, intentionally unused)

- **Host mode:** `assemble.py` still supports bookend host clips
  (`host/host-a.mp4`, `host/host-b.mp4`, a third VO segment, the legacy
  `content.brand`/`noclause` gate branch) from the retired host format.
  The owner retired on-camera host segments on Nov 2, 2026; the current
  config keys (`"nohost": true`, `"outro": ...`) bypass them. Leave the
  code paths intact; do not "clean them up" — the gates branch on them.
- **Lipsync rig:** a local Wav2Lip setup (venv + wav2lip_gan + s3fd face
  detection, ~4.5 s/frame on CPU) was built to sync host clips to the VO,
  plus a CodeFormer pass for face restoration and a seal-compositing fix
  step. It is dormant with the host format. You do not need it to build or
  run the current pipeline.

---

*Reference implementation state: this spec describes the pipeline exactly as
rebuilt and run on Nov 2–3, 2026 — three videos produced under it
("Hop On" Pinellas Park FHP pursuit; Thurston County I-5 pursuit; Houston
ICE SUV indictment), all QC 10/10, all published to Scoopz via §11.*
