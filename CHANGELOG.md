# Changelog
## 0.1.3

### New Features/Changes
- Added global keyboard hotkeys for Compose/Abort buttons.
- Added optional sounds for finished composing, warnings/errors and using Compose hotkey.
- Added symlink support checks for relevant tilesets and help message if unsupported. [Suggestion by Discord user un.leash]

### Bug Fixes
- Fixed json_formatter.exe not being found in standalone version. [Reported by Discord user oogabooga] 
- Fixed Fail Fast triggering on warnings instead of just errors.

### Misc
- Added new dependecies pynput and six, plus relevant licensing information.

## 0.1.2
### New Features/Changes
- Integrated remaining compose error and warning messages into message box.
- Integrated remaining command line options of original `compose.py`.
- Added button for profile deletion.
- Larger main "Compose" and "Abort" buttons; rearranged layout.
- Added basic source directory validation icons for `tileset.txt`, `tile_info.json` etc.
- Changed behavior of specific tilesheet composing without any tilesheets selected to be more intuitive (i.e. equal to "Only JSON" option)
### Bug Fixes
- Fixed libvips wrongly loading modified sprites from cache.

### Misc
- Removed "Known Issues and Bugs [...]" section from `README.md` since the most notable issues have now been fixed.

## 0.1.1
### New Features
- Integrated more compose log messages (Only those about obsolete fillers are left to be included.)
- Automatic compose abort if critical error encountered. 

### Misc
- Various `README.md` fixes; added note about *Windows Defender*
- Fixed `compose.py` link in `LICENSE.md`
