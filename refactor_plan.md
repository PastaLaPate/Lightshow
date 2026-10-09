```
.
├── pyproject.toml, uv.lock, Makefile, README.md, LICENSE.txt
├── docs/                      # was specs/ (mh_head_protocole.md lives here)
├── packaging/                 # installer/*, lightshow.spec
├── tools/                     # cz_conventional_chore.py, debug_audio.py
├── tests/
└── src/lightshow/
    ├── __main__.py, app.py
    ├── core/                  # NO Qt imports
    │   ├── config.py, logger.py, colors.py, update_checker.py
    │   ├── events.py          # replaces ui_signals (plain callbacks or a tiny event bus)
    │   └── device_manager.py  # was gui/controllers/device_controller.py
    ├── audio/
    │   ├── streams.py, types.py, processors.py
    │   └── detectors/ (+ methods/)
    ├── media/                 # was tracks_tracker (abstract, linux, windows, factory)
    ├── devices/
    │   ├── base.py            # was device.py + devices_types.py
    │   ├── launchpad/
    │   ├── projector/         # when it exists
    │   └── moving_head/
    │       ├── device.py, controller.py, colors.py
    │       └── animations/    # shared base moved to devices/animations/base.py
    ├── show/                  # NEW, pure Python/pydantic
    │   ├── model.py           # groups, selectors, scenes, blocks
    │   ├── commands.py        # undo/redo
    │   └── evaluator.py       # resolves groups/selectors → fixture values
    ├── net/wifi_scanner.py
    └── gui/
        ├── main_window.py, dialogs/, components/, panels/, assets/
        ├── editor/            # timeline widgets for the show mode
        └── visualizers/       # was visualization/

```
