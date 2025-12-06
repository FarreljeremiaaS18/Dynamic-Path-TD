# Ukuran Layar & Grid
TILE = 32
GRID_W = 20
GRID_H = 15
SIDEBAR_W = 220
SCREEN_W = TILE * GRID_W + SIDEBAR_W
SCREEN_H = TILE * GRID_H
FPS = 60

# Posisi Start & Finish
#START_POS = (0, GRID_H // 2)
#GOAL_POS = (GRID_W - 1, GRID_H // 2)

# Konfigurasi Tower (Tipe 1, 2, 3)
TOWER_TYPES = {
    1: {"name": "Standard", "cost": 50, "range": 3.5, "damage": 1, "rate": 0.6, "color": (200, 160, 40)},
    2: {"name": "Sniper",   "cost": 120,"range": 7.0, "damage": 5, "rate": 1.5, "color": (50, 100, 200)},
    3: {"name": "Rapid",    "cost": 90, "range": 2.5, "damage": 0.4,"rate": 0.15,"color": (200, 50, 50)}
}

# Konfigurasi Musuh Dasar
BASE_ENEMY_HEALTH = 3
BASE_ENEMY_SPEED = 1.5
BASE_WAVE_ENEMIES = 10
SPAWN_INTERVAL = 0.8

# Warna-warna
BG_GAME = (20, 24, 30)
BG_SIDEBAR = (40, 44, 52)
BTN_COLOR = (60, 70, 80)
BTN_HOVER = (80, 90, 100)
BTN_SELECTED = (100, 180, 100)
PATH_COLOR = (50, 60, 70)
TEXT_COLOR = (240, 240, 240)
PROJECTILE_COLOR = (255, 230, 150)

# Warna Menu
MENU_BG = (15, 20, 25)
BTN_EASY = (60, 160, 80)
BTN_MED = (200, 160, 40)
BTN_HARD = (200, 60, 60)
BTN_EXIT = (80, 80, 80)