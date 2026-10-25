## v1.0.4 (2026-10-25)

## v1.0.3 (2026-10-25)

## v1.0.2 (2026-10-25)

## v1.0.1 (2026-10-25)

## v1.0.0 (2026-10-25)

### Feat

- **makefile**: added ways to bump versions
- **ui**: better runtime_schema vizualisation
- **moving_head**: added more modulation transformers
- **ui/devices**: moved reverse possibility to controller to avoid the animation reversing in manual mode + fixed some bugs
- **moving_head**: wayyy better circle animation
- **ui**: fixed manual packet sender
- **ui**: little arrows on checkboxes + badge on device list (need to resolve ghosting text bug)
- **ui**: reintroduced duplicate + fixed repetitions in launchpad + splitted theme
- **ui**: badge color per device
- **ui**: way better UI for Fields & Runtime
- **ui**: whole theme system
- field categories
- **ui**: start of device_props showing
- **moving_head**: much better animations + better integration with launchpad
- **moving_head**: new calibration system for angles
- **ui**: now connects to devices async
- **ui**: connection buttons working
- **ui**: implemented setEnabled on every field type
- splitted UISignals class into subclasses for each part of the app, TODO: rename everything + add types help in the class
- **ui**: added non implemented connect button to device details
- **ui**: device_details react to new device status
- **ui**: fixed some random bugs in SpikeDetectorVisualizer
- **ui**: rewritten frequencies_visualizer for better curves & performances
- you can now start streams, also separated main window to a audio controller + settings now have a signal instead of being handled in main_window
- **ui**: correct title name for path_selector + implemented different modes + preview_button pointinghandcursor
- **ui**: (exp) file selection dialog
- **ui**: field validation
- **cz**: added args possibilities when doing make commit
- **fields**: new field validator, needs integration with UI
- **ui**: added qcolordialog to the color picker
- **ui**: basic color picker, needs dialog implementation
- **form_builder**: use gt/ge and lt/le for spinners
- **ui**: show placeholder for lineedits
- working field edition + undo
- experimental field edition
- **debug**: created new debug file
- **shortcuts**: new features: new bugs ! for some reason doing undo add more things to the history... need to debug
- **input**: added shortcuts base: mapping + most used
- start for undo/redo stack
- **config**: added new config system, need to refactor the rest
- **ui**: added badge comp
- yay it changes
- **ui**: typing should be good, ready for ui integration
- **ui**: finished form builder, implementing
- **ui**: added form builder, still needs the builder itself
- **ui**: added numeric slider spinbox
- **forms**: added pydantic compatible ui fields
- migrated to pyside6, made ty check pass
- **pyproject.toml**: added commitizen to pyproject

### Fix

- **ui**: better theme
- **ui**: fixed not displaying runtime schema
- **ui**: fixed some types in devices + show runtime schema
- **launchpad**: fixed launchpad/moving_head connection issues
- **launchpad**: fixed launchpad not detecting moving head's connection
- **launchpad**: fixed controller references after refactor
- fixed some bugs before full controller refactor
- **ui**: fixed fields not being locked when selected a device already connected
- **launchpad**: fixed animations constructors
- **moving_head**: logical config, now has a real config thats really used
- **signals**: fixed all signals names
- fixed OPENGL status message being printed twice
- **ui**: fixed renaming a device creating another rename entry in the undo stack caused by an event triggering itself in devices_panel's listbox
- fixed typing
- **ui**: made device_details_panel's header actually rename devices + devices_panel just edit the corresponding device row's text instead of refreshing
- **ui**: made the ui at least a little reactive to renames
- made ui selection reactive to device type
- finally fixed cyclic imports
- tried to fix circular imports (again)
- tried to fix circular imports
- temporary refactor for new device config system
- Fixed device type name
- **\**: fixed linter errors
- fixed update message variable
- immovable plots

### Refactor

- **events**: better splitted events
- **all**: big refactor across everything, need to fix each violation
- **moving_head_controller**: big refactor, much more organized
- **form_builder**: some cleanup, made basefieldfactory generic of its widget
- refactored everything
- better status indicator, base for header, ready for migration to pyside6

## v0.32.1 (2026-08-04)

## v0.32.0 (2026-05-31)

## v0.31.0 (2026-05-09)

## v0.30.0 (2026-04-21)

## v0.29.1 (2026-04-20)

## v0.29.0 (2026-04-20)

## v0.28.0 (2026-04-19)

## v0.27.2 (2026-03-22)

## v0.27.1 (2026-03-14)
