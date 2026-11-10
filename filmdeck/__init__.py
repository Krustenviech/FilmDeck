"""FilmDeck - a small scanning front-end for the Plustek OpticFilm 135i on Linux.

It drives the community driver https://github.com/cgillinger/opticfilm135i-linux
(the ``of135i`` command line tool) and adds: strip and whole-film scanning,
film/camera presets, a JPEG preview, an update check for the driver and a
shortcut to NegPy.
"""

__version__ = "0.1.3"
APP_NAME = "FilmDeck"
APP_ID = "filmdeck"
REPO_URL = "https://github.com/Krustenviech/filmdeck"
DRIVER_URL = "https://github.com/cgillinger/opticfilm135i-linux"
NEGPY_URL = "https://github.com/marcinz606/NegPy"
