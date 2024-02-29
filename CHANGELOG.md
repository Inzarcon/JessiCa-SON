# Changelog
## 0.1.2
### Main
- Fixed libvips wrongly loading modified sprites from cache.
- Integrated remaining compose error and warning messages into message box.
- Integrated remaining command line options of original `compose.py`.
- Added button for profile deletion.
- Larger main "Compose" and "Abort" buttons; rearranged layout.
- Added basic source directory validation icons for `tileset.txt`, `tile_info.json` etc.
- Changed behavior of specific tilesheet composing without any tilesheets selected to be more intuitive (i.e. equal to "Only JSON" option)

### Misc
- Removed "Known Issues and Bugs [...]" section from `README.md` since the most notable issues have now been fixed.

## 0.1.1
### Main
- Integrated more compose log messages (Only those about obsolete fillers are left to be included.)
- Automatic compose abort if critical error encountered. 

### Misc
- Various `README.md` fixes; added note about *Windows Defender*
- Fixed `compose.py` link in `LICENSE.md`