# Roadmap

Big goal: **premade concerts** — a mode next to live mode where a show is
composed on a timeline (drag effects and colors onto per-device tracks,
synced to a song) and played back without live audio analysis.

Steps are ordered so each one ships on its own. The pre-existing items
are kept and folded in where they belong.

## Phase 1 — Audio foundations (source-agnostic listener)

The pipeline today is hard-wired to loopback capture
(`LoopbackAudioStreamHandler` in `audio/streams.py` → bounded queue →
GUI drain → `SpectrumProcessor` → listeners). Everything below keeps
that contract so detectors and device packets work unchanged.

### 1. File playback source (mp3/wav) — first step
- New `FileAudioStreamHandler` + `FileAudioCapture` implementing the
  same `AAudioStreamHandler` / `AAudioCapture` contract as the loopback
  ones.
- Extract the shared queue/listener plumbing of `LoopbackAudioCapture`
  (bounded queue, `process_queued_samples`, listener management) into a
  `QueuedAudioCapture` base so the file capture does not duplicate it.
- Decode with `soundfile` (bundles libsndfile >= 1.2: wav/mp3/flac/ogg —
  mp3 round-trip verified) to mono float32, resampled to 44.1 kHz so
  every existing detector (they assume 44100 / 1024 / mono) keeps
  working unchanged.
- Play through the speaker with soundcard's blocking `player` in the
  capture thread and enqueue the same chunks: the playback clock IS the
  analysis clock (perfect sync, no loopback device needed).
- Audible by design: playback goes to the selected output device, so the
  user hears the song while it is analyzed — what is heard is exactly
  what is analyzed.
- Transport primitives on the capture: play / stop / pause / resume /
  seek, plus `position` and `duration` — the future timeline clock.
- UI (audio panel): a "Play file..." button opening a file dialog;
  loopback and file sources are mutually exclusive; Start/Stop Stream
  drives whichever source is active.
- Verify with a headless script (pattern of `scripts/debug_audio.py`)
  using a fake player sink, plus one short audible test.

### 2. Transport UI
- Progress bar + play/pause/seek on the audio panel for file playback.
- Playback position exposed through `audio/events.py` so any widget
  (later: the timeline) can follow it.
- Seeking is audible: moving through the file relocates the speaker
  playback (fast jumps land on the new position, no silent cursor).

### 3. Pre-computed analysis track — limit at any time x
- Today the limit is a function of streaming state:
  `DetectionMethod.register_energy()` feeds `energy_history` and
  `get_limit()` derives from it (Percentile: smoothed percentile
  baseline; Average Difference: moving average) — at time x it is only
  correct if the history up to x has actually been processed. A user
  moving very quickly through the file cannot get that live.
- At file load, run the same pipeline offline over the whole decoded
  song (SpectrumProcessor -> detection method), once, sequentially, and
  store per-chunk arrays: energy, limit, beat flags.
- Expose O(1) lookups by time: `limit_at(x)`, `energy_at(x)`,
  `beats_between(a, b)` (x -> chunk index = x * sample_rate /
  chunk_size). Safe for very fast timeline scrubbing — no streaming
  state, no re-simulation.
- Reuse the real detector classes (`audio/detectors/methods/*`) so the
  offline curve matches what live mode would show at the same position;
  they need a clean reset/replay entry point for the pass.
- Cache per file, keyed by chunk size / method / sensitivity; rebuild
  when those settings change.
- Same pass yields the beat grid for timeline snapping (Phase 3).
- Verify headless: generated click-track file, assert `limit_at(x)`
  behaves around each beat and `beats_between(0, end)` matches a live
  replay of the same file.

### 4. Make the listener less dependent on UI (existing item)
- `MainAudioListener` binds to a single handler instance and the drain
  loop lives in `UIManager._update_visualizations` — move draining out
  of the GUI tick so the pipeline can run headless.
- Fix while there: `chunk_size` is read via
  `getattr(config, "chunk_size", 1024)` but that attribute no longer
  exists (it moved to managed settings) — the CHUNK_SIZE setting is
  currently dead; both handlers should read it from
  `config.settings[SETTINGS.CHUNK_SIZE]`.

### 5. Detection Method Benchmark (existing item)
- Now cheap: benchmark detectors on decoded files with known beats,
  no live audio / GUI needed; the offline pass (step 3) is the harness.

## Phase 2 — Show data model (prerequisites for the timeline)

### 5. Make Animation and colors independent (existing item)
- Today animation and color are coupled on the moving head; timeline
  clips need them as separate, draggable objects — this becomes a hard
  prerequisite and should land before the editor.

### 6. Concert document model
- A concert = audio file reference + one track per device + clips
  (effect, color, parameter automation) placed in time.
- Reuse `document/history.py` undo/redo for clip edits.
- Serialize to a `.lightshow` file (JSON), audio referenced by path.

### 7. Timeline playback engine (headless)
- A clock driven by the file playback position (from step 1)
  dispatching clip start/stop to devices — no live analysis required.
- Optional hybrid layer on top: beats/drops still modulate intensity
  while the timeline drives structure.

## Phase 3 — Concert editor UI

### 8. Timeline panel
- pyqtgraph-based: time ruler, one lane per device track, drag & drop
  of clips, snap to grid; beat grid from the offline analysis pass
  (step 3).

### 9. Clip editing
- Drag effects/colors from a palette onto clips; property editors;
  copy/paste; undo/redo via `global_history`.

### 10. Mode switch
- Live / Concert mode selection; concert open/save; concert playback
  driving devices end to end.

## Parallel track

- UI Tests (existing item) — start with headless pipeline tests (they
  become possible after the listener-decoupling step), then
  QTest-based panel tests.
