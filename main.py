if __name__ == "__main__":
    import os
    import sys

    cur_dir = os.path.dirname(__file__)
    sys.path.append(os.path.join(cur_dir, "src"))
    # Local libvips BEFORE other entries to avoid dll conflicts.
    os.environ["PATH"] = os.path.join(cur_dir, "libvips/bin") + ";" + os.environ["PATH"]

    from main_window import run  # type: ignore

    run()
