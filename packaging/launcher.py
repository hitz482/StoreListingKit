"""PyInstaller entry point."""

import multiprocessing
import sys

from storelistingkit.cli import main

if __name__ == "__main__":
    multiprocessing.freeze_support()
    sys.exit(main())
