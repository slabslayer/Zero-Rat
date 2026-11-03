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
