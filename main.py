import os
import sys
from pathlib import Path

# TODO: Option for user to set their own preferred location?
# TODO: Also consider Qt's resource management. (Though overkill at this stage)
ROOT_PATH = Path(__file__).resolve().parent
CFG_PATH = ROOT_PATH.joinpath(".config")
ICON_PATH = ROOT_PATH.joinpath("resources/icons")

if __name__ == "__main__":
    sys.path.append(str(ROOT_PATH))
    sys.path.append(str(ROOT_PATH.joinpath("src")))
    # Local libvips BEFORE other entries to avoid dll conflicts.
    os.environ["PATH"] = (
        str(ROOT_PATH.joinpath("libvips/bin")) + ";" + os.environ["PATH"]
    )

    from main_window import run  # type: ignore

    run()
