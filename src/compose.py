"""
Merge all tile entries and PNGs in a compositing tileset directory into
a tile_config.json and tilesheet .png file(s) ready for use in CDDA.

Derivative of the original compose.py from Cataclysm DDA. See root/LICENSE.md
for details.

Summary of main changes/additions:
- Removed command line interface
- Added interface for communicating with Qt
- Added multithreading
- Fixed original ToDo about generating all JSON first
- Added option to compose only a subset of tilesheets
- Fixed various things linter complained about
"""

import contextlib
import json
import logging
import os
import subprocess
from enum import Enum, auto
from multiprocessing.pool import ThreadPool
from pathlib import Path
from typing import Any, Optional, Tuple, Union

from compose_logger import get_logger
from PySide6.QtCore import QObject, QRunnable, Signal, Slot

log = get_logger(name="compose")


class ComposeSignalType(Enum):
    """Defines the different types of messages the application reacts to."""

    PROGRESS_PERCENT = auto()
    PROGRESS_PNGNUM = auto()
    PROGRESS_IMAGE = auto()
    STATUS_MESSAGE = auto()
    LOADING = auto()
    COMPOSING = auto()
    FINISHED = auto()
    WARNING_MESSAGE = auto()
    ERROR_MESSAGE = auto()
    CRITICAL_MESSAGE = auto()


class MessageType(Enum):
    """
    More specific types for warning and error message signals.
    Used for color coded formatting in message box.
    """

    CRIT_GENERIC = auto()
    CRIT_ERROR_LOADING_JSON = auto()

    ERR_PNG_NOT_FOUND = auto()
    ERR_SPRITE_SIZE = auto()
    ERR_DUPLICATE_NAME = auto()
    ERR_DUPLICATE_ID = auto()
    ERR_NOT_USED = auto()
    ERR_VIPS = auto()

    WARN_SPRITE_UNREF = auto()
    WARN_NO_FORMATTER = auto()
    WARN_NOT_MENTIONED = auto()
    WARN_EMPTY_ENTRY = auto()
    WARN_FILLER_SKIP = auto()
    WARN_FILLER_DUPLICATE = auto()
    WARN_FILLER_UNUSED = auto()


# Generally not good practice, but in this case connection chain would be very
# complicated. Signal is connected one time in the whole app and composing has
# only this Signal.
class ComposeSignalWrapper(QObject):
    """Wraps the compose signal."""

    signal = Signal(ComposeSignalType, str, tuple, MessageType)


SIG_COMPOSE = ComposeSignalWrapper()


# These three functions could be class methods, but no "competitors" in this
# module -> simplify
def connect_compose_signal(receiver: Slot):
    """Connect a slot to the compose signal."""
    SIG_COMPOSE.signal.connect(receiver)


def emit(
    sig_type: ComposeSignalType,
    message: str = None,
    args: Tuple[str] = None,
    msg_type: MessageType = None,
) -> None:
    """
    Shortcut for emitting a message with the corresponding signal type and
    string replacement args.
    """
    SIG_COMPOSE.signal.emit(sig_type, message, args, msg_type)


def log_and_emit(
    log_level: int,
    sig_type: ComposeSignalType,
    message: str = None,
    args: Tuple[str] = None,
    msg_type: MessageType = None,
) -> None:
    """
    Shortcut for logging and emitting a message with the corresponding signal
    type and string replacement args.
    """
    formatted = message if not args else message.format(*args)
    log.log(log_level, formatted)
    # Message box handles color coded formatting later -> just forward
    emit(sig_type, message, args, msg_type)


# Original import code kept for compatibility outside bundled windows libvips
# or one manually copied to libvips folder
try:
    vips_path = os.getenv("LIBVIPS_PATH")
    if vips_path is not None and vips_path != "":
        os.environ["PATH"] += ";" + vips_path
    import pyvips

    Vips = pyvips
except ImportError:
    import gi  # type: ignore

    gi.require_version("Vips", "8.0")  # NoQA
    from gi.repository import Vips  # type: ignore

# File name to ignore containing directory
IGNORE_FILE = ".scratch"

# Parameters originally used in argparse. Logging related flags are removed
# entirely because GUI processes everything separately.
# TODO: Replace with corresponding Qt checkboxes

TMP_OBSOLETE_FILLERS = True
TMP_PALETTE_COPIES = True
TMP_PALETTE = True

PROPERTIES_FILENAME = "tileset.txt"

PNGSAVE_ARGS = {
    "compression": 9,
    "strip": True,
    "filter": 8,
}

FALLBACK = {
    "file": "fallback.png",
    "tiles": [],
    "ascii": [
        {"offset": 0, "bold": False, "color": "BLACK"},
        {"offset": 256, "bold": True, "color": "WHITE"},
        {"offset": 512, "bold": False, "color": "WHITE"},
        {"offset": 768, "bold": True, "color": "BLACK"},
        {"offset": 1024, "bold": False, "color": "RED"},
        {"offset": 1280, "bold": False, "color": "GREEN"},
        {"offset": 1536, "bold": False, "color": "BLUE"},
        {"offset": 1792, "bold": False, "color": "CYAN"},
        {"offset": 2048, "bold": False, "color": "MAGENTA"},
        {"offset": 2304, "bold": False, "color": "YELLOW"},
        {"offset": 2560, "bold": True, "color": "RED"},
        {"offset": 2816, "bold": True, "color": "GREEN"},
        {"offset": 3072, "bold": True, "color": "BLUE"},
        {"offset": 3328, "bold": True, "color": "CYAN"},
        {"offset": 3584, "bold": True, "color": "MAGENTA"},
        {"offset": 3840, "bold": True, "color": "YELLOW"},
    ],
}


def write_to_json(
    pathname: str,
    data: Union[dict, list],
    format_json: bool = False,
) -> None:
    """
    Write data to a JSON file.
    """
    kwargs = {
        "ensure_ascii": False,
    }
    if format_json:
        kwargs["indent"] = 2

    with open(pathname, "w", encoding="utf-8") as file:
        json.dump(data, file, **kwargs)

    if not format_json:
        return

    json_formatter = Path("tools/json_formatter.exe")
    if json_formatter.is_file():
        cmd = [json_formatter, pathname]
        subprocess.call(cmd)
    else:
        log_and_emit(
            logging.WARNING,
            ComposeSignalType.WARNING_MESSAGE,
            "{} not found, Python built-in formatter was used.",
            (json_formatter,),
            MessageType.WARN_NO_FORMATTER,
        )


def list_or_first(iterable: list) -> Any:
    """
    Strip unneeded container list if there is only one value.
    """
    return iterable[0] if len(iterable) == 1 else iterable


def read_properties(filepath: Path) -> dict:
    """
    tileset.txt reader.
    """
    with open(filepath, encoding="utf-8") as file:
        pairs = {}
        for line in file.readlines():
            line = line.strip()
            if line and not line.startswith("#"):
                key, value = line.split(":")
                pairs[key.strip()] = value.strip()
    return pairs


class ComposingException(Exception):
    """
    Base class for all composing exceptions.
    """


class StopComposing(Exception):
    """
    Exception for aborting the running composing process.
    """


class Tileset:
    """
    Referenced sprites memory and handling, tile entries conversion.
    """

    def __init__(
        self,
        source_dir: Path,
        output_dir: Path,
        no_use_all: bool = False,
        obsolete_fillers: bool = False,
        palette_copies: bool = False,
        palette: bool = False,
        format_json: bool = False,
        only_json: bool = False,
        output_conf_file: str = "",
        compose_subset=(),
    ) -> None:
        self.to_exit = False

        self.source_dir = source_dir
        self.output_dir = output_dir
        self.no_use_all = no_use_all
        self.obsolete_fillers = obsolete_fillers
        self.palette_copies = palette_copies
        self.palette = palette
        self.format_json = format_json
        self.only_json = only_json
        self.output_conf_file = output_conf_file

        self.compose_subset = compose_subset

        self.pngnum = 0
        self.pngnums = {}
        self.unreferenced_pngnames = {
            "main": [],
            "filler": [],
        }

        self.pngname_to_pngnum = {"null_image": 0}

        if not self.source_dir.is_dir() or not os.access(self.source_dir, os.R_OK):
            raise ComposingException(f"Error: cannot open directory {self.source_dir}")

        self.processed_ids = []
        info_path = self.source_dir.joinpath("tile_info.json")
        self.sprite_width = 16
        self.sprite_height = 16
        self.zlevel_height = 0
        self.pixelscale = 1
        self.iso = False
        self.retract_dist_min = -1.0
        self.retract_dist_max = 1.0
        self.info = [{}]

        if not os.access(info_path, os.R_OK):
            raise ComposingException(f"Error: cannot open {info_path}")

        with open(info_path, encoding="utf-8") as file:
            self.info = json.load(file)
            self.sprite_width = self.info[0].get("width", self.sprite_width)
            self.sprite_height = self.info[0].get("height", self.sprite_height)
            self.zlevel_height = self.info[0].get("zlevel_height", self.zlevel_height)
            self.pixelscale = self.info[0].get("pixelscale", self.pixelscale)
            self.retract_dist_min = self.info[0].get(
                "retract_dist_min", self.retract_dist_min
            )
            self.retract_dist_max = self.info[0].get(
                "retract_dist_max", self.retract_dist_max
            )
            self.iso = self.info[0].get("iso", self.iso)

        # Let's Turbocharge this with Multithreading.
        self.thread_pool = ThreadPool()

    def abort_composing(self, now=False):
        """
        Request aborting the composing process.
        Optionally abort right away -> Use only for main compose thread!
        """
        if not self.to_exit:
            log_and_emit(
                logging.INFO,
                ComposeSignalType.STATUS_MESSAGE,
                "Abort requested.",
            )
        self.to_exit = True
        if now:
            self.check_abort()

    def check_abort(self):
        """
        Abort composing process if requested earlier. Called in relevant
        submethods, primarily in the loops. -> Just throwing directly in
        abort_composing doesn't work with multithreading!
        """
        if self.to_exit:
            raise StopComposing()

    def determine_conffile(self) -> str:
        """Find the tileset properties file."""
        properties = {}

        for candidate_path in (self.source_dir, self.output_dir):
            properties_path = candidate_path.joinpath(PROPERTIES_FILENAME)
            if os.access(properties_path, os.R_OK):
                properties = read_properties(properties_path)
                if properties:
                    break

        if not properties:
            raise ComposingException(f"No valid {PROPERTIES_FILENAME} found")

        conf_filename = properties.get("JSON", None)
        if not conf_filename:
            raise ComposingException(f"No JSON key found in {PROPERTIES_FILENAME}")

        self.output_conf_file = conf_filename
        return self.output_conf_file

    def compose(self) -> None:
        """
        Convert a composing tileset into a package readable by the game.
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)
        tileset_confpath = self.output_dir.joinpath(self.determine_conffile())
        typed_sheets = {
            "main": [],
            "filler": [],
            "fallback": [],
        }
        fallback_name = "fallback.png"

        # loop through tilesheets and parse all configs in subdirectories,
        # create sheet images; each step is looped seperately.
        # -> Allows accessing json and sprite meta results before
        # starting the computationally heavy main image processing step.

        # This fixes original Todo about generating json first.
        # TODO: -> consider backporting to CDDA/Tileset repo

        added_first_null = False
        # For progress bars
        prev_pngnum = 0
        actual_pngnums = {}
        # TODO: Find out why this offset happens on first sheet only.
        #    -> Probably because first index in tile_config.json starts with 1?
        offset = -1
        # Step 1: Walk file tree and process json
        for config in self.info[1:]:
            prev_pngnum = self.pngnum
            sheet = Tilesheet(self, config)

            if not added_first_null:
                sheet.sprites.append(sheet.null_image)
                added_first_null = True

            if sheet.is_filler:
                sheet_type = "filler"
            elif sheet.is_fallback:
                sheet_type = "fallback"
            else:
                sheet_type = "main"

            log_and_emit(
                logging.INFO,
                ComposeSignalType.STATUS_MESSAGE,
                "Parsing JSON for: [{}] tilesheet {}.",
                (sheet_type, sheet.name),
            )

            if sheet_type != "fallback":
                sheet.walk_dirs()
                sheet.process_sheet_json()
            typed_sheets[sheet_type].append((sheet, sheet_type))

            log_and_emit(
                logging.INFO,
                ComposeSignalType.STATUS_MESSAGE,
                "Processing sprite file names for: [{}] tilesheet {}.",
                (sheet_type, sheet.name),
            )
            sheet.process_sheet_png_filenames()
            diff = sheet.sprites_across - (
                (len(sheet.png_files) % sheet.sprites_across) or sheet.sprites_across
            )

            if not self.compose_subset or sheet.name in self.compose_subset:
                actual_pngnums[sheet.name] = self.pngnum - prev_pngnum
            self.pngnum += diff + offset
            offset = 0
            sheet.max_index = self.pngnum

        # Combine config data in the correct order.
        sheet_configs = (
            typed_sheets["main"] + typed_sheets["filler"] + typed_sheets["fallback"]
        )
        emit(
            ComposeSignalType.PROGRESS_PNGNUM,
            str(sum(actual_pngnums.values())),
            (actual_pngnums),
        )

        # 2. Handle fillers, fallback, and unreferenced sprites.
        # Prepare "tiles-new", but remember max index of each sheet in keys.
        tiles_new_dict = {}

        def create_tile_entries_for_unused(
            unused: list,
            fillers: bool,
        ) -> None:
            """Create tile entries for unused sprite files."""
            # The list must be on no_use_all.
            for unused_png in unused:
                self.check_abort()
                if unused_png in self.processed_ids:
                    if not fillers:
                        log_and_emit(
                            logging.WARNING,
                            ComposeSignalType.WARNING_MESSAGE,
                            "Sprite {} was not mentioned in any "
                            "tile entry but there is a tile entry for the ID {}.",
                            (f"{unused_png}.png", unused_png),
                            MessageType.WARN_NOT_MENTIONED,
                        )
                    if fillers and self.obsolete_fillers:
                        log_and_emit(
                            logging.WARNING,
                            ComposeSignalType.WARNING_MESSAGE,
                            "There is a tile entry for {} in a non-filler sheet",
                            (unused_png,),
                            MessageType.WARN_FILLER_UNUSED,
                        )
                    continue
                unused_num = self.pngname_to_pngnum[unused_png]
                sheet_min_index = 0
                for sheet_max_index, sheet_data in tiles_new_dict.items():
                    if sheet_min_index < unused_num <= sheet_max_index:
                        sheet_data["tiles"].append(
                            {
                                "id": unused_png,
                                "fg": unused_num,
                            }
                        )
                        self.processed_ids.append(unused_png)
                        break
                    sheet_min_index = sheet_max_index

        main_finished = False

        for sheet, _ in sheet_configs:
            self.check_abort()
            if sheet.is_fallback:
                fallback_name = sheet.name
                if not sheet.is_standard():
                    self.non_standard_sheet(sheet, FALLBACK)
                continue
            if sheet.is_filler and not main_finished:
                create_tile_entries_for_unused(
                    self.handle_unreferenced_sprites("main"), fillers=True
                )
                main_finished = True
            sheet_entries = []

            for tile_entry in sheet.tile_entries:
                # TODO: pop?
                converted_tile_entry = tile_entry.convert()
                if converted_tile_entry:
                    sheet_entries.append(converted_tile_entry)

            sheet_conf = {
                "file": sheet.name,
                "//": f"range {sheet.first_index} to {sheet.max_index}",
            }

            if not sheet.is_standard():
                self.non_standard_sheet(sheet, sheet_conf)

            sheet_conf["tiles"] = sheet_entries

            tiles_new_dict[sheet.max_index] = sheet_conf

        if not main_finished:
            create_tile_entries_for_unused(
                self.handle_unreferenced_sprites("main"),
                fillers=False,
            )

        create_tile_entries_for_unused(
            self.handle_unreferenced_sprites("filler"),
            fillers=True,
        )

        # 3. Finalize "tiles-new" config.
        tiles_new = list(tiles_new_dict.values())

        FALLBACK["file"] = fallback_name
        tiles_new.append(FALLBACK)
        output_conf = {
            "tile_info": [
                {
                    "pixelscale": self.pixelscale,
                    "width": self.sprite_width,
                    "height": self.sprite_height,
                    "zlevel_height": self.zlevel_height,
                    "iso": self.iso,
                    "retract_dist_min": self.retract_dist_min,
                    "retract_dist_max": self.retract_dist_max,
                }
            ],
            "tiles-new": tiles_new,
        }
        write_to_json(
            tileset_confpath,
            output_conf,
            self.format_json,
        )
        if not self.only_json:
            self.thread_pool.map(self.load_and_compose_sheet, sheet_configs)

        log_and_emit(logging.INFO, ComposeSignalType.FINISHED, "Composing done.")

    def load_and_compose_sheet(self, work):
        sheet, sheet_type = work
        self.check_abort()
        if not self.compose_subset or sheet.name in self.compose_subset:
            log_and_emit(
                logging.INFO,
                ComposeSignalType.STATUS_MESSAGE,
                "Start Loading sprites for: [{}] tilesheet {}.",
                (sheet_type, sheet.name),
            )
            emit(ComposeSignalType.LOADING, args=[sheet.name])
            sheet.load_sheet_images()
            log_and_emit(
                logging.INFO,
                ComposeSignalType.STATUS_MESSAGE,
                "Start Composing: [{}] tilesheet {}.",
                (sheet_type, sheet.name),
            )
            emit(ComposeSignalType.COMPOSING)
            self.check_abort()
            if not sheet.write_composite_png():
                return
        else:
            log_and_emit(
                logging.INFO,
                ComposeSignalType.STATUS_MESSAGE,
                "Skipping composing for: [{}] tilesheet {}.",
                (sheet_type, sheet.name),
            )

    @staticmethod
    def non_standard_sheet(sheet, sheetconf):
        """Build configs for filler and fallback sheets."""
        sheetconf["sprite_width"] = sheet.sprite_width
        sheetconf["sprite_height"] = sheet.sprite_height
        sheetconf["sprite_offset_x"] = sheet.offset_x
        sheetconf["sprite_offset_y"] = sheet.offset_y
        if (
            sheet.offset_x_retracted != sheet.offset_x
            or sheet.offset_y_retracted != sheet.offset_y
        ):
            sheetconf["sprite_offset_x_retracted"] = sheet.offset_x_retracted
            sheetconf["sprite_offset_y_retracted"] = sheet.offset_y_retracted
        if str(sheet.pixelscale) != str(1.0):
            sheetconf["pixelscale"] = sheet.pixelscale

    def handle_unreferenced_sprites(
        self,
        sheet_type: str,
    ) -> list:
        """Either warn about unused sprites or return the list."""
        if self.no_use_all:
            for pngname in self.unreferenced_pngnames[sheet_type]:
                self.check_abort()
                if pngname in self.processed_ids:
                    (
                        log_and_emit(
                            logging.ERROR,
                            ComposeSignalType.ERROR_MESSAGE,
                            "{} was not used, but ID {} is mentioned in a tile entry.",
                            (f"{pngname}.png", pngname),
                            MessageType.ERR_NOT_USED,
                        ),
                    )

                else:
                    log_and_emit(
                        logging.WARNING,
                        ComposeSignalType.WARNING_MESSAGE,
                        "Sprite filename {} was not used in any {} {} entries.",
                        (f"{pngname}.png", sheet_type, self.output_conf_file),
                        MessageType.WARN_SPRITE_UNREF,
                    )
            return []

        return self.unreferenced_pngnames[sheet_type]


class Tilesheet(QObject):
    """Tilesheet reading and compositing."""

    def __init__(
        self,
        tileset: Tileset,
        config: dict,
    ) -> None:
        super().__init__()
        self.tileset = tileset

        self.name = next(iter(config))
        specs = config.get(self.name, {})

        self.sprite_width = specs.get("sprite_width", tileset.sprite_width)
        self.sprite_height = specs.get("sprite_height", tileset.sprite_height)
        self.offset_x = specs.get("sprite_offset_x", 0)
        self.offset_y = specs.get("sprite_offset_y", 0)
        self.offset_x_retracted = specs.get("sprite_offset_x_retracted", self.offset_x)
        self.offset_y_retracted = specs.get("sprite_offset_y_retracted", self.offset_y)

        self.pixelscale = specs.get("pixelscale", 1.0)

        self.sprites_across = specs.get("sprites_across", 16)
        self.exclude = specs.get("exclude", ())

        self.is_fallback = specs.get("fallback", False)
        self.is_filler = not self.is_fallback and specs.get("filler", False)

        output_root = self.name.split(".png")[0]
        dir_name = f"pngs_{output_root}_{self.sprite_width}x{self.sprite_height}"
        self.subdir_path = tileset.source_dir.joinpath(dir_name)

        self.output = tileset.output_dir.joinpath(self.name)

        self.json_files = []
        self.png_files = []
        self.images_loaded = 0

        self.tile_entries = []
        self.null_image = Vips.Image.grey(self.sprite_width, self.sprite_height)
        self.sprites = []

        self.first_index = self.tileset.pngnum + 1
        self.max_index = self.tileset.pngnum

    def is_standard(self) -> bool:
        """
        Check whether output object needs a non-standard size or offset config
        """
        if self.offset_x or self.offset_y:
            return False
        if (
            self.offset_x_retracted != self.offset_x
            or self.offset_y_retracted != self.offset_y
        ):
            return False
        if self.sprite_width != self.tileset.sprite_width:
            return False
        if self.sprite_height != self.tileset.sprite_height:
            return False
        if str(self.pixelscale) != str(1.0):
            return False
        return True

    def walk_dirs(self) -> None:
        """Find and process all JSON and PNG files within sheet directory."""

        def filtered_tree(excluded):
            """Walk the sheet directory and filter out excluded paths."""
            for root, dirs, filenames in os.walk(self.subdir_path, followlinks=True):
                # Replace dirs in-place to prevent walking down excluded paths.
                dirs[:] = [
                    d
                    for d in dirs
                    if Path(root).joinpath(d) not in excluded
                    and not Path(root).joinpath(d, IGNORE_FILE).is_file()
                ]
                yield [root, dirs, filenames]

        sorted_files = sorted(
            filtered_tree(list(map(self.subdir_path.joinpath, self.exclude))),
            key=lambda d: d[0],
        )
        for subdir_fpath, _, subdir_filenames in sorted_files:
            subdir_fpath = Path(subdir_fpath)
            for filename in sorted(subdir_filenames):
                filepath = subdir_fpath.joinpath(filename)

                if filepath.suffixes == [".json"]:
                    self.json_files.append(filepath)

                elif filepath.suffixes == [".png"]:
                    self.png_files.append(filepath)

    def process_sheet_json(self) -> None:
        """Parse JSON files for this tilesheet."""
        for filepath in self.json_files:
            self.tileset.check_abort()
            self.process_json(filepath)

    def process_sheet_png_filenames(self) -> None:
        """Parse PNG file names for this tilesheet."""
        for filepath in self.png_files:
            self.tileset.check_abort()
            self.process_png_filename(filepath)

    def process_png_filename(
        self,
        filepath: Path,
    ) -> None:
        """Verify image root name is unique, load it and register."""
        if filepath.stem in self.tileset.pngname_to_pngnum:
            if not self.is_filler:
                log_and_emit(
                    logging.ERROR,
                    ComposeSignalType.ERROR_MESSAGE,
                    "Duplicate root name for ID {}: {}.",
                    (filepath.stem, filepath),
                    MessageType.ERR_DUPLICATE_NAME,
                )
            if self.is_filler and self.tileset.obsolete_fillers:
                log_and_emit(
                    logging.WARNING,
                    ComposeSignalType.WARNING_MESSAGE,
                    "Root name {} is already present in a non-filler sheet: {}",
                    (filepath.stem, filepath),
                    MessageType.WARN_FILLER_DUPLICATE,
                )
            return

        self.tileset.pngnum += 1

        self.tileset.pngname_to_pngnum[filepath.stem] = self.tileset.pngnum
        self.tileset.unreferenced_pngnames[
            "filler" if self.is_filler else "main"
        ].append(filepath.stem)

    def load_sheet_images(self):
        """Load the found sprite PNG files."""
        for filepath in self.png_files:
            emit(ComposeSignalType.PROGRESS_IMAGE)
            self.sprites.append(self.load_image(filepath))

    def load_image(self, png_path: Union[str, Path]) -> pyvips.Image:
        """Load and verify a single image using pyvips"""
        self.tileset.check_abort()
        if self.tileset.only_json:
            return None
        try:
            image = Vips.Image.pngload(str(png_path), access="sequential")
        except pyvips.error.Error as pyvips_error:
            raise ComposingException(
                f"Cannot load {png_path}: {pyvips_error.message}"
            ) from None
        except UnicodeDecodeError:
            raise ComposingException(
                f"Cannot load {png_path} with UnicodeDecodeError, "
                "please report your setup at "
                "https://github.com/libvips/pyvips/issues/80"
            ) from None
        if image.interpretation != "srgb":
            image = image.colourspace("srgb")

        try:
            if not image.hasalpha():
                image = image.addalpha()
            if image.get_typeof("icc-profile-data") != 0:
                image = image.icc_transform("srgb")
        except Vips.Error as vips_error:
            log_and_emit(
                logging.ERROR,
                ComposeSignalType.ERROR_MESSAGE,
                "Vips error for file {}: {}",
                (png_path, vips_error),
                MessageType.ERR_VIPS,
            )

        if image.width != self.sprite_width or image.height != self.sprite_height:
            log_and_emit(
                logging.ERROR,
                ComposeSignalType.ERROR_MESSAGE,
                "{} is {}x{}, but {} sheet sprites have to be {}x{}.",
                (
                    png_path,
                    image.width,
                    image.height,
                    self.name,
                    self.sprite_width,
                    self.sprite_height,
                ),
                MessageType.ERR_SPRITE_SIZE,
            )

        self.images_loaded += 1
        return image

    def process_json(
        self,
        filepath: Path,
    ) -> None:
        """Load and store tile entries from the file."""
        with open(filepath, encoding="utf-8") as file:
            try:
                tile_entries = json.load(file)
            except Exception:
                log_and_emit(
                    logging.CRITICAL,
                    ComposeSignalType.CRITICAL_MESSAGE,
                    "Error loading {}. {}",
                    (filepath, "Auto-Aborting..."),
                    MessageType.CRIT_ERROR_LOADING_JSON,
                )
                self.tileset.abort_composing(now=True)

            if not isinstance(tile_entries, list):
                tile_entries = [tile_entries]
            for input_entry in tile_entries:
                self.tile_entries.append(TileEntry(self, input_entry, filepath))

    def write_composite_png(self) -> bool:
        """Compose and save tilesheet PNG if there are sprites to work with."""
        if not self.sprites:
            return False

        if self.tileset.only_json:
            return True

        if self.sprites:
            sheet_image = Vips.Image.arrayjoin(self.sprites, across=self.sprites_across)
            sheet_image.set_progress(True)

            # Unpack and forward to Qt Signal.
            def emit_percent(_, progress):
                emit(
                    ComposeSignalType.PROGRESS_PERCENT,
                    self.name,
                    (progress.percent,),
                )

            sheet_image.signal_connect("eval", emit_percent)
            sheet_image.signal_connect("posteval", emit_percent)

        pngsave_args = PNGSAVE_ARGS.copy()

        if self.tileset.palette:
            pngsave_args["palette"] = True

        sheet_image.pngsave(str(self.output), **pngsave_args)

        if self.tileset.palette_copies and not self.tileset.palette:
            sheet_image.pngsave(str(self.output) + "8", palette=True, **pngsave_args)

        log_and_emit(
            logging.INFO,
            ComposeSignalType.STATUS_MESSAGE,
            "Finished composing: tilesheet {}.",
            (self.name,),
        )

        return True


class TileEntry:
    """Tile entry handling."""

    def __init__(
        self,
        tilesheet: Tilesheet,
        data: dict,
        filepath: Union[str, Path],
    ) -> None:
        self.tilesheet = tilesheet
        self.data = data
        self.filepath = filepath

    def convert(
        self,
        entry: Union[dict, None] = None,
        prefix: str = "",
    ) -> Optional[dict]:
        """Recursively compile input into game-compatible objects in-place."""
        if entry is None:
            entry = self.data

        entry_ids = entry.get("id")
        fg_layer = entry.get("fg")
        bg_layer = entry.get("bg")

        if not entry_ids or (not fg_layer and not bg_layer):
            message = "Skipping empty entry in {}"
            message += " with IDs {}{}." if entry_ids else "."
            log_and_emit(
                logging.WARNING,
                ComposeSignalType.WARNING_MESSAGE,
                message,
                (self.filepath, prefix, entry_ids),
                MessageType.WARN_EMPTY_ENTRY,
            )
            return None

        # Make sure entry_ids is a list.
        if entry_ids and not isinstance(entry_ids, list):
            entry_ids = [entry_ids]

        # Convert fg value.
        if fg_layer:
            entry["fg"] = list_or_first(self.convert_entry_layer(fg_layer))
        else:
            # don't pop at the start because that affects order of the keys
            entry.pop("fg", None)

        # Convert bg value.
        if bg_layer:
            entry["bg"] = list_or_first(self.convert_entry_layer(bg_layer))
        else:
            # Don't pop at the start because that affects order of the keys.
            entry.pop("bg", None)

        # Recursively convert additional_tiles value.
        additional_entries = entry.get("additional_tiles", [])
        for additional_entry in additional_entries:
            # recursive part
            self.convert(additional_entry, f"{entry_ids[0]}_")

        # Remember processed IDs and remove duplicates.
        for entry_id in entry_ids:
            full_id = f"{prefix}{entry_id}"

            if full_id not in self.tilesheet.tileset.processed_ids:
                self.tilesheet.tileset.processed_ids.append(full_id)

            else:
                entry_ids.remove(entry_id)

                if self.tilesheet.is_filler:
                    if self.tilesheet.tileset.obsolete_fillers:
                        log_and_emit(
                            logging.WARNING,
                            ComposeSignalType.WARNING_MESSAGE,
                            "Skipping filler for {} from {}.",
                            (full_id, self.filepath),
                            MessageType.WARN_FILLER_SKIP,
                        )

                else:
                    log_and_emit(
                        logging.ERROR,
                        ComposeSignalType.ERROR_MESSAGE,
                        "ID {} encountered more than once, last time in {}.",
                        (full_id, self.filepath),
                        MessageType.ERR_DUPLICATE_ID,
                    )

        # Return converted entry if there are new IDs.
        if entry_ids:
            entry["id"] = list_or_first(entry_ids)
            return entry

        return None

    def convert_entry_layer(
        self,
        entry_layer: Union[list, str],
    ) -> list:
        """
        Convert sprite names to sprite indexes in one fg or bg tile entry part.
        """
        output = []

        if isinstance(entry_layer, list):
            # "fg": [ "f_fridge_S", "f_fridge_W", "f_fridge_N", "f_fridge_E" ]
            for layer_part in entry_layer:
                if isinstance(layer_part, dict):
                    # Weighted random variations.
                    variations, valid = self.convert_random_variations(
                        layer_part.get("sprite")
                    )
                    if valid:
                        layer_part["sprite"] = list_or_first(variations)
                        output.append(layer_part)
                else:
                    self.append_sprite_index(layer_part, output)
        else:
            # "bg": "t_grass"
            self.append_sprite_index(entry_layer, output)

        return output

    def convert_random_variations(
        self,
        sprite_names: Union[list, str],
    ) -> Tuple[list, bool]:
        """Convert list of random weighted variation objects."""
        valid = False
        converted_variations = []

        if isinstance(sprite_names, list):
            # List of rotations.
            converted_variations = []
            for sprite_name in sprite_names:
                valid |= self.append_sprite_index(sprite_name, converted_variations)
        else:
            # Single sprite.
            valid = self.append_sprite_index(sprite_names, converted_variations)
        return converted_variations, valid

    def append_sprite_index(
        self,
        sprite_name: str,
        entry: list,
    ) -> bool:
        """Get sprite index by sprite name and append it to entry."""
        if sprite_name:
            sprite_index = self.tilesheet.tileset.pngname_to_pngnum.get(sprite_name, 0)
            if sprite_index:
                sheet_type = "filler" if self.tilesheet.is_filler else "main"
                with contextlib.suppress(ValueError):
                    self.tilesheet.tileset.unreferenced_pngnames[sheet_type].remove(
                        sprite_name
                    )

                entry.append(sprite_index)
                return True
            sprite_name = f"{sprite_name}.png"
            log_and_emit(
                logging.ERROR,
                ComposeSignalType.ERROR_MESSAGE,
                "{} file for {} value from {} "
                "was not found. It will not be added to {}",
                (
                    sprite_name,
                    sprite_name,
                    self.filepath,
                    self.tilesheet.tileset.output_conf_file,
                ),
                MessageType.ERR_PNG_NOT_FOUND,
            )

        return False


class ComposeRunner(QRunnable):
    """Compose Runner for use in QThreadPool."""

    def __init__(
        self,
        source_dir: str,
        output_dir: str = None,
        flags: tuple[str] = (),
        compose_subset: tuple[str] = (),
    ):  # No *args as app generates list anyway.
        super().__init__()
        self.source_dir = Path(source_dir)
        self.output_dir = Path(output_dir) or self.source_dir
        (
            self.no_use_all,
            self.fail_fast,
            self.obsolete_fillers,
            self.palette_copies,
            self.palette,
            self.format_json,
            self.only_json,
        ) = [False] * 7

        for v in flags:
            if v in self.__dict__:
                setattr(self, v, True)
            else:
                raise ValueError(v)

        self.compose_subset = compose_subset

        if self.fail_fast:
            # TODO: Make handler part of compose_logger module and connect here
            #       instead of checking and resetting every time.
            create_handler = True
            for handler in log.handlers:
                if isinstance(handler, FailFastHandler):
                    create_handler = False
                    handler.parent = self
                    handler.triggered = False
                    break
            if create_handler:
                fail_fast_handler = FailFastHandler(self)
                fail_fast_handler.setLevel(logging.WARNING)
                log.addHandler(fail_fast_handler)

        self.tileset = None

    def create_tileset(self) -> None:
        """Create new tileset with the given parameters."""
        try:
            self.tileset = Tileset(
                source_dir=self.source_dir,
                output_dir=Path(self.output_dir or self.source_dir),
                no_use_all=self.no_use_all,
                obsolete_fillers=self.obsolete_fillers,
                palette_copies=self.palette_copies,
                palette=self.palette,
                format_json=self.format_json,
                only_json=self.only_json,
                compose_subset=self.compose_subset,
            )
        except ComposingException as ce:
            self.on_composing_exception(ce)

    def run(self) -> None:
        """Run the composing process."""
        try:
            self.tileset.compose()
        except ComposingException as ce:
            self.on_composing_exception(ce)
        except StopComposing:
            log_and_emit(
                logging.INFO,
                ComposeSignalType.FINISHED,
                "Composing aborted.",
            )

    def request_abort(self, by_user: bool = False):
        """Interface for requesting composing stop once possible."""
        if by_user:
            emit(
                ComposeSignalType.CRITICAL_MESSAGE,
                "User Request: {}...",
                ("Aborting",),
                MessageType.CRIT_GENERIC,
            )
        self.tileset.abort_composing()

    def on_composing_exception(
        self,
        exception: ComposingException,
    ) -> None:
        """Send message about encountered exception and auto-abort composing."""
        log_and_emit(
            logging.CRITICAL,
            ComposeSignalType.CRITICAL_MESSAGE,
            str(exception) + ". {}...",
            ("Auto-Aborting",),
            MessageType.CRIT_GENERIC,
        )
        self.tileset.abort_composing(now=True)


class FailFastHandler(logging.StreamHandler):
    """Stop composing if an error was encountered."""

    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.triggered = False  # Avoid recursion

    def emit(self, _):
        if not self.triggered:
            self.triggered = True
            log_and_emit(
                logging.CRITICAL,
                ComposeSignalType.CRITICAL_MESSAGE,
                "Fail Fast: {}...",
                ("Auto-Aborting",),
                MessageType.CRIT_GENERIC,
            )
            self.parent.request_abort()
