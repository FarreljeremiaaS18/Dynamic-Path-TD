import pygame
import sys
import math
import heapq
import random

# Konfigurasi Game
TILE = 32
GRID_W = 20
GRID_H = 15
SIDEBAR_W = 220  # Lebar tambahan untuk UI di sebelah kanan
SCREEN_W = TILE * GRID_W + SIDEBAR_W
SCREEN_H = TILE * GRID_H
FPS = 60

START_POS = (0, GRID_H // 2)
GOAL_POS = (GRID_W - 1, GRID_H // 2)

# Konfigurasi Tower (Tipe Tower)
TOWER_TYPES = {
    1: {
        "name": "Standard",
        "cost": 50,
        "range": 3.5,
        "damage": 1,
        "rate": 0.6,
        "color": (200, 160, 40)  # Emas
    },
    2: {
        "name": "Sniper",
        "cost": 120,
        "range": 7.0,
        "damage": 5,
        "rate": 1.5,
        "color": (50, 100, 200)  # Biru
    },
    3: {
        "name": "Rapid",
        "cost": 90,
        "range": 2.5,
        "damage": 0.4,
        "rate": 0.15,
        "color": (200, 50, 50)   # Merah
    }
}

# Konfigurasi Musuh Dasar
BASE_ENEMY_HEALTH = 3
BASE_ENEMY_SPEED = 1.5
WAVE_ENEMIES = 10
SPAWN_INTERVAL = 0.8

# Warna
BG_GAME = (20, 24, 30)      
BG_SIDEBAR = (40, 44, 52)    
BTN_COLOR = (60, 70, 80)
BTN_HOVER = (80, 90, 100)
BTN_SELECTED = (100, 180, 100)
PATH_COLOR = (50, 60, 70)   
TEXT_COLOR = (240, 240, 240)
PROJECTILE_COLOR = (255, 230, 150)

pygame.init()
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption("Tower Defense A*")
clock = pygame.time.Clock()
font = pygame.font.SysFont("Consolas", 16)
font_title = pygame.font.SysFont("Consolas", 20, bold=True)

#A* Implementation 
def heuristic(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def neighbors(node):
    x, y = node
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nx, ny = x + dx, y + dy
        if 0 <= nx < GRID_W and 0 <= ny < GRID_H:
            yield (nx, ny)

def astar(start, goal, blocked):
    if start == goal:
        return [start]
    open_heap = []
    heapq.heappush(open_heap, (0 + heuristic(start, goal), 0, start, None))
    came_from = {}
    gscore = {start: 0}
    closed = set()

    while open_heap:
        f, g, current, parent = heapq.heappop(open_heap)
        if current in closed:
            continue
        closed.add(current)
        came_from[current] = parent

        if current == goal:
            path = []
            node = current
            while node is not None:
                path.append(node)
                node = came_from[node]
            path.reverse()
            return path

        for nb in neighbors(current):
            if nb in blocked and nb != goal:
                continue
            tentative_g = g + 1
            if tentative_g < gscore.get(nb, float("inf")):
                gscore[nb] = tentative_g
                heapq.heappush(open_heap, (tentative_g + heuristic(nb, goal), tentative_g, nb, current))
    return None

#Game Entities
class Tower:
    def __init__(self, cell, type_id):
        stats = TOWER_TYPES[type_id]
        self.cell = cell
        self.type_id = type_id
        self.range = stats["range"]
        self.damage = stats["damage"]
        self.fire_rate = stats["rate"]
        self.color = stats["color"]
        self.cooldown = 0.0

    def in_range(self, pos):
        tx, ty = self.cell
        cx = (tx + 0.5) * TILE
        cy = (ty + 0.5) * TILE
        dx = cx - pos[0]
        dy = cy - pos[1]
        dist_tiles = math.hypot(dx, dy) / TILE
        return dist_tiles <= self.range

class Enemy:
    def __init__(self, spawn_cell, wave_number):
        self.pos = ((spawn_cell[0] + 0.5) * TILE, (spawn_cell[1] + 0.5) * TILE)
        self.cell = spawn_cell
        self.path = []
        
        # Scaling Musuh berdasarkan Wave
        scaling_factor = 1.0 + (wave_number * 0.2) # HP naik 20% tiap wave
        speed_factor = min(2.5, 1.0 + (wave_number * 0.05))  # Speed naik 5% tiap wave, max 2.5x
        
        self.max_hp = BASE_ENEMY_HEALTH * scaling_factor
        self.hp = self.max_hp
        self.speed = BASE_ENEMY_SPEED * speed_factor
        
        # Warna musuh berubah berdasarkan kekuatan 
        red_val = max(50, 255 - int(wave_number * 10))
        self.color = (red_val, 50, 50)
        
        self.reached_goal = False
        self.path_index = 0
        self.target = None

    def set_path(self, path):
        self.path = path
        self.path_index = 0
        self._update_target()

    def _update_target(self):
        if self.path_index + 1 < len(self.path):
            nxt = self.path[self.path_index + 1]
            self.target = ((nxt[0] + 0.5) * TILE, (nxt[1] + 0.5) * TILE)
        else:
            self.target = None

    def update(self, dt):
        if self.target is None:
            self.reached_goal = True
            return

        dx = self.target[0] - self.pos[0]
        dy = self.target[1] - self.pos[1]
        dist = math.hypot(dx, dy)
        
        move = (self.speed * TILE) * dt
        if move >= dist:
            self.pos = self.target
            self.path_index += 1
            if self.path_index + 1 >= len(self.path):
                self.reached_goal = True
                return
            self._update_target()
        else:
            self.pos = (self.pos[0] + (dx / dist) * move, self.pos[1] + (dy / dist) * move)

class Projectile:
    def __init__(self, pos, target_enemy, damage, speed=400):
        self.pos = pos
        self.target = target_enemy
        self.damage = damage
        self.speed = speed
        self.alive = True

    def update(self, dt):
        if not self.target or self.target.hp <= 0 or self.target.reached_goal:
            self.alive = False
            return
        dx = self.target.pos[0] - self.pos[0]
        dy = self.target.pos[1] - self.pos[1]
        dist = math.hypot(dx, dy)
        if dist < 5:
            self.target.hp -= self.damage
            self.alive = False
            return
        move = self.speed * dt
        self.pos = (self.pos[0] + dx / dist * move, self.pos[1] + dy / dist * move)

#Game State
class GameState:
    def __init__(self):
        self.grid_blocked = set()
        self.towers = []
        self.enemies = []
        self.projectiles = []
        self.money = 250
        self.health = 20
        self.wave = 0
        self.wave_in_progress = False
        self.spawn_timer = 0.0
        self.spawned = 0
        self.next_wave_delay = 2.0
        
        self.selected_tower_type = 1 # Default ke tipe 1
        self.default_path = []
        self.recalc_all_paths()

    def recalc_all_paths(self):
        blocked = set(self.grid_blocked)
        if START_POS in blocked: blocked.remove(START_POS)
        if GOAL_POS in blocked: blocked.remove(GOAL_POS)

        path = astar(START_POS, GOAL_POS, blocked)
        self.default_path = path

        for e in self.enemies:
            cur_cell = (int(e.pos[0] // TILE), int(e.pos[1] // TILE))
            p = astar(cur_cell, GOAL_POS, blocked)
            if p:
                if p[0] != cur_cell:
                    p.insert(0, cur_cell)
                e.set_path(p)
            else:
                e.set_path([cur_cell])

    def place_tower(self, cell):
        if cell == START_POS or cell == GOAL_POS:
            return False, "Area Start/Goal!"
        if cell in self.grid_blocked:
            return False, "Sudah ada tower!"
        
        stats = TOWER_TYPES[self.selected_tower_type]
        if self.money < stats["cost"]:
            return False, "Uang kurang!"
            
        self.grid_blocked.add(cell)
        path = astar(START_POS, GOAL_POS, self.grid_blocked)
        if path is None:
            self.grid_blocked.remove(cell)
            return False, "Memblokir jalan!"
            
        self.towers.append(Tower(cell, self.selected_tower_type))
        self.money -= stats["cost"]
        self.recalc_all_paths()
        return True, "Dibangun"

    def remove_tower(self, cell):
        for t in self.towers:
            if t.cell == cell:
                self.towers.remove(t)
                if cell in self.grid_blocked:
                    self.grid_blocked.remove(cell)
                # Refund 50%
                stats = TOWER_TYPES[t.type_id]
                self.money += int(stats["cost"] * 0.5)
                self.recalc_all_paths()
                return True
        return False

    def start_wave(self):
        if self.wave_in_progress:
            return
        self.wave += 1
        self.wave_in_progress = True
        self.spawn_timer = 0.0
        self.spawned = 0

    def update(self, dt):
        # Spawning
        if self.wave_in_progress:
            self.spawn_timer -= dt
            while self.spawned < WAVE_ENEMIES and self.spawn_timer <= 0:
                e = Enemy(START_POS, self.wave) # Pass wave number
                if self.default_path:
                    e.set_path(list(self.default_path))
                else:
                    e.set_path([START_POS])
                self.enemies.append(e)
                self.spawned += 1
                self.spawn_timer += SPAWN_INTERVAL
            
            # Cek wave selesai
            alive_enemies = [e for e in self.enemies if e.hp > 0 and not e.reached_goal]
            if self.spawned >= WAVE_ENEMIES and len(alive_enemies) == 0:
                self.wave_in_progress = False
                self.money += 50 + (self.wave * 10) # Bonus wave clear

        # Update Musuh
        for e in list(self.enemies):
            e.update(dt)
            if e.reached_goal:
                self.health -= 1
                self.enemies.remove(e)
            elif e.hp <= 0:
                self.money += 5 + self.wave # Lebih banyak uang di wave tinggi
                self.enemies.remove(e)

        # Tower Menembak
        for t in self.towers:
            t.cooldown -= dt
            if t.cooldown <= 0:
                target = None
                best_dist = 1e9
                for e in self.enemies:
                    if e.hp > 0 and not e.reached_goal and t.in_range(e.pos):
                        dx = (e.pos[0] - (t.cell[0] + 0.5) * TILE)
                        dy = (e.pos[1] - (t.cell[1] + 0.5) * TILE)
                        d = dx * dx + dy * dy
                        if d < best_dist:
                            best_dist = d
                            target = e
                if target:
                    proj = Projectile(
                        ((t.cell[0] + 0.5) * TILE, (t.cell[1] + 0.5) * TILE), 
                        target, 
                        damage=t.damage
                    )
                    self.projectiles.append(proj)
                    t.cooldown = t.fire_rate

        # Update Proyektil
        for p in list(self.projectiles):
            p.update(dt)
            if not p.alive:
                if p in self.projectiles:
                    self.projectiles.remove(p)

    def is_game_over(self):
        return self.health <= 0

#Rendering
def draw_path_line(surf, path):
    if not path: return
    points = [((c[0] + 0.5) * TILE, (c[1] + 0.5) * TILE) for c in path]
    if len(points) >= 2:
        pygame.draw.lines(surf, PATH_COLOR, False, points, 6)

def draw_sidebar(surf, state):
    # Background Sidebar
    pygame.draw.rect(surf, BG_SIDEBAR, (GRID_W * TILE, 0, SIDEBAR_W, SCREEN_H))
    
    x_offset = GRID_W * TILE + 15
    y_offset = 15

    # Judul
    title = font_title.render("Dynamic Path TD", True, (255, 255, 255))
    surf.blit(title, (x_offset, y_offset))
    y_offset += 40

    # Info Stats
    stats = [
        f"Money : ${state.money}",
        f"Lives : {state.health}",
        f"Wave  : {state.wave}"
    ]
    for s in stats:
        t = font.render(s, True, TEXT_COLOR)
        surf.blit(t, (x_offset, y_offset))
        y_offset += 25

    y_offset += 15
    pygame.draw.line(surf, (100, 100, 100), (x_offset, y_offset), (SCREEN_W - 15, y_offset))
    y_offset += 15

    # Shop / Tower Selection
    l_shop = font.render("Select Tower (1-3):", True, (200, 200, 200))
    surf.blit(l_shop, (x_offset, y_offset))
    y_offset += 25

    # Gambar tombol untuk setiap tipe tower
    mouse_pos = pygame.mouse.get_pos()
    
    for type_id, data in TOWER_TYPES.items():
        # Rect untuk tombol
        btn_rect = pygame.Rect(x_offset, y_offset, SIDEBAR_W - 30, 55)
        
        # Cek Hover / Selected
        is_selected = (state.selected_tower_type == type_id)
        color = BTN_SELECTED if is_selected else BTN_COLOR
        if btn_rect.collidepoint(mouse_pos):
            if not is_selected: color = BTN_HOVER
            
            # Klik mouse untuk memilih
            if pygame.mouse.get_pressed()[0]:
                state.selected_tower_type = type_id

        pygame.draw.rect(surf, color, btn_rect, border_radius=5)
        pygame.draw.rect(surf, data["color"], (x_offset + 5, y_offset + 5, 20, 20))
        
        name_txt = font.render(f"{data['name']} (${data['cost']})", True, (255, 255, 255))
        stats_txt = font.render(f"Dmg:{data['damage']} Spd:{data['rate']}s", True, (200, 200, 200))
        
        surf.blit(name_txt, (x_offset + 35, y_offset + 5))
        surf.blit(stats_txt, (x_offset + 35, y_offset + 25))
        
        y_offset += 65

    # Tombol Start Wave
    y_offset = SCREEN_H - 60
    start_rect = pygame.Rect(x_offset, y_offset, SIDEBAR_W - 30, 40)
    
    if state.wave_in_progress:
        col = (100, 60, 60)
        txt = "Wave Ongoing..."
    else:
        col = (60, 120, 60)
        if start_rect.collidepoint(mouse_pos):
            col = (80, 140, 80)
            if pygame.mouse.get_pressed()[0]:
                state.start_wave()
        txt = "START WAVE (Space)"
    
    pygame.draw.rect(surf, col, start_rect, border_radius=5)
    t_start = font.render(txt, True, (255,255,255))
    text_rect = t_start.get_rect(center=start_rect.center)
    surf.blit(t_start, text_rect)


def draw_game(state):
    screen.fill(BG_GAME)
    
    # Area Grid (tanpa garis grid)
    # Gambar jalur
    draw_path_line(screen, state.default_path)
    
    # Gambar Start/Goal
    pygame.draw.rect(screen, (60, 180, 80), (START_POS[0]*TILE+2, START_POS[1]*TILE+2, TILE-4, TILE-4))
    pygame.draw.rect(screen, (180, 60, 60), (GOAL_POS[0]*TILE+2, GOAL_POS[1]*TILE+2, TILE-4, TILE-4))

    # Gambar Tower
    for t in state.towers:
        x, y = t.cell
        # Base tower
        pygame.draw.rect(screen, t.color, (x*TILE+2, y*TILE+2, TILE-4, TILE-4))
        # Dekorasi 
        pygame.draw.circle(screen, (30,30,30), (int((x+0.5)*TILE), int((y+0.5)*TILE)), 6)

    # Gambar Musuh
    for e in state.enemies:
        ex, ey = e.pos
        pygame.draw.circle(screen, e.color, (int(ex), int(ey)), 11)
        # HP Bar kecil
        pct = max(0, e.hp) / e.max_hp
        bar_w = 20
        bar_x = ex - bar_w // 2
        bar_y = ey - 18
        pygame.draw.rect(screen, (50,0,0), (bar_x, bar_y, bar_w, 3))
        pygame.draw.rect(screen, (0,200,0), (bar_x, bar_y, bar_w * pct, 3))

    # Gambar Proyektil
    for p in state.projectiles:
        pygame.draw.circle(screen, PROJECTILE_COLOR, (int(p.pos[0]), int(p.pos[1])), 4)

    # Gambar Sidebar
    draw_sidebar(screen, state)


def main():
    state = GameState()
    hover_cell = None
    running = True
    last_time = pygame.time.get_ticks() / 1000.0

    while running:
        now = pygame.time.get_ticks() / 1000.0
        dt = now - last_time
        last_time = now

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            # Input Keyboard
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    state.start_wave()
                elif event.key == pygame.K_1:
                    state.selected_tower_type = 1
                elif event.key == pygame.K_2:
                    state.selected_tower_type = 2
                elif event.key == pygame.K_3:
                    state.selected_tower_type = 3
            
            # Input Mouse
            elif event.type == pygame.MOUSEMOTION:
                mx, my = event.pos
                if mx < GRID_W * TILE and my < GRID_H * TILE:
                    hover_cell = (mx // TILE, my // TILE)
                else:
                    hover_cell = None
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Klik Kiri (Bangun)
                if event.button == 1:
                    if hover_cell:
                        ok, msg = state.place_tower(hover_cell)
                        if not ok:
                            print(msg) 
                
                # Klik Kanan (Jual)
                elif event.button == 3:
                    if hover_cell:
                        state.remove_tower(hover_cell)

        state.update(dt)

        # Draw
        draw_game(state)

        # Draw Hover 
        if hover_cell:
            hx, hy = hover_cell
            valid = (hover_cell not in state.grid_blocked and 
                     hover_cell != START_POS and 
                     hover_cell != GOAL_POS)
            
            curr_stats = TOWER_TYPES[state.selected_tower_type]
            base_col = curr_stats["color"]
            
            s = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
            if valid:
                col = (base_col[0], base_col[1], base_col[2], 100) 
                # range indicator
                range_px = curr_stats["range"] * TILE
                cx, cy = (hx + 0.5) * TILE, (hy + 0.5) * TILE
      
            else:
                col = (200, 50, 50, 100) 
            
            s.fill(col)
            screen.blit(s, (hx * TILE, hy * TILE))
            
           
            if valid:
                range_px = curr_stats["range"] * TILE
                cx, cy = int((hx + 0.5) * TILE), int((hy + 0.5) * TILE)
                pygame.draw.circle(screen, (255, 255, 255), (cx, cy), int(range_px), 1)


        pygame.display.flip()
        clock.tick(FPS)

        if state.is_game_over():
            print("Game Over")
            running = False

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()