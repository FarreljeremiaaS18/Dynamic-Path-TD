# Dynamic-Path-TD

"""
DP_TD.py
Simple Bloons-like Tower Defense Game using A* pathfinding (Python + pygame).
Run:
  pip install pygame
  python DP_TD.py
Controls:
  - Left click on a grid cell to place a tower (cost: 50).
  - Right click to remove a tower (refund 25%).
  - Space Start Wave
Notes:
  - Towers act as obstacles for pathfinding; enemies recalc path when map changes.
  
"""