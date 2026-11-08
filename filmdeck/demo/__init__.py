"""A stand-in for the of135i driver, for trying FilmDeck without a scanner (FILMDECK_DEMO=1).

It is run exactly like the real driver (``python -m of135i ...`` with this folder on
PYTHONPATH), prints the same messages for the parts FilmDeck reads, and writes small
synthetic 16-bit TIFFs in the real driver's folder layout.
"""
