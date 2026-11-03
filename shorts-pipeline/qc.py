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
