import pygame
import sys
import random  
from config import *
from entities import Tower, Enemy, Projectile, astar

pygame.init()

# Load Assets
def load_tile(path):
    img = pygame.image.load(path)
    return pygame.transform.scale(img, (TILE, TILE))

# EASY TILE
TILE_GRASS = load_tile("assets/tiles/grass.png")
TILE_EPATH  = load_tile("assets/tiles/easy_path.png")

# MEDIUM TILE
TILE_SANDSTONE = load_tile("assets/tiles/sand.png")
TILE_MPATH = load_tile("assets/tiles/medium_path.png")

# HARD TILE
TILE_DUNGEON = load_tile("assets/tiles/dungeon.png")
TILE_HPATH = load_tile("assets/tiles/hard_path.png")

screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption("Dynamic Path - TD")
clock = pygame.time.Clock()

# Load Audio
victory_fx = None
defeat_fx = None
try:
    victory_fx = pygame.mixer.Sound(VICTORY_SOUND_PATH)
    victory_fx.set_volume(0.5) # Atur volume (0.0 sampai 1.0)
except Exception as e:
    print(f"Warning: Tidak bisa memuat suara Victory. Error: {e}")

try:
    defeat_fx = pygame.mixer.Sound(DEFEAT_SOUND_PATH)
    defeat_fx.set_volume(0.5)
except Exception as e:
    print(f"Warning: Tidak bisa memuat suara kekalahan. Error: {e}")

try:
    pygame.mixer.music.load(MENU_MUSIC_PATH)
    pygame.mixer.music.set_volume(0.4)
except Exception as e:
    print(f"Warning: Error loading music: {e}")

font = pygame.font.SysFont("Consolas", 16)
font_title = pygame.font.SysFont("Consolas", 20, bold=True)
font_menu_title = pygame.font.SysFont("Consolas", 40, bold=True)
font_menu_btn = pygame.font.SysFont("Consolas", 24, bold=True)
font_overlay = pygame.font.SysFont("Consolas", 50, bold=True)
font_small = pygame.font.SysFont("Consolas", 14)

# Menentukan difficulty game
def get_difficulty_zone(wave):
    if wave == 3:
        return "easy"
    elif wave == 6:
        return "medium"
    else:
        return "hard"

# Menentukan tile berdasarkan difficulty game
TILESETS = {
    "easy": {
        "base": TILE_GRASS,
        "path": TILE_EPATH
    },
    "medium": {
        "base": TILE_SANDSTONE,
        "path": TILE_MPATH
    },
    "hard": {
        "base": TILE_DUNGEON,
        "path": TILE_HPATH
    }
}

# Menentukan multiplier untuk tiap difficulty
DIFFICULTY_MULTIPLIER = {
    3: 1.0,    # EASY
    6: 1.5,    # MEDIUM
    10: 2.0    # HARD
}

MULTIPLIER_DECAY_PER_TOWER = 0.05
MIN_MULTIPLIER = 0.3


class GameState:
    def __init__(self, max_waves):
        # LOGIKA RANDOM POSISI START & GOAL
        self.start_pos = (0, random.randint(0, GRID_H - 1))
        self.goal_pos = (GRID_W - 1, random.randint(0, GRID_H - 1))
        

        self.grid_blocked = set()
        self.towers = []
        self.enemies = []
        self.projectiles = []
        self.money = STARTING_MONEY[max_waves]
        self.health = 20
        self.wave = 0
        self.max_waves = max_waves
        self.wave_in_progress = False
        self.spawn_timer = 0.0
        self.spawned = 0
        self.selected_tower_type = 1
        self.default_path = []
        self.game_result = None
        
        # POINT SYSTEM
        self.score = 0
        self.base_multiplier = DIFFICULTY_MULTIPLIER[max_waves]
        self.score_multiplier = self.base_multiplier
        self.towers_placed = 0

        self.recalc_all_paths()

    def recalc_all_paths(self):
        blocked = set(self.grid_blocked)
        
        if self.start_pos in blocked: blocked.remove(self.start_pos)
        if self.goal_pos in blocked: blocked.remove(self.goal_pos)
        
        path = astar(self.start_pos, self.goal_pos, blocked)
        self.default_path = path
        
        for e in self.enemies:
            cur_cell = (int(e.pos[0] // TILE), int(e.pos[1] // TILE))
            p = astar(cur_cell, self.goal_pos, blocked)
            e.set_path(p if p else [cur_cell])
            if p and p[0] != cur_cell: e.path.insert(0, cur_cell)

    def place_tower(self, cell):
        if self.game_result: return
        if self.wave_in_progress: return # Tidak bisa place saat wave jalan

        # Cek collision dengan start/goal dinamis
        if cell == self.start_pos or cell == self.goal_pos: return
        
        if cell in self.grid_blocked: return
        stats = TOWER_TYPES[self.selected_tower_type]
        if self.money < stats["cost"]: return

        # Multiplier penalty
        self.towers_placed += 1
        self.score_multiplier = max(
            MIN_MULTIPLIER,
            self.base_multiplier - (self.towers_placed * MULTIPLIER_DECAY_PER_TOWER)
        )
        
        self.grid_blocked.add(cell)
        # Cek apakah memblokir jalan dari start ke goal
        if astar(self.start_pos, self.goal_pos, self.grid_blocked) is None:
            self.grid_blocked.remove(cell)
            return 
        
        self.towers.append(Tower(cell, self.selected_tower_type))
        self.money -= stats["cost"]
        self.recalc_all_paths()

    def remove_tower(self, cell):
        if self.game_result: return
        for t in self.towers:
            if t.cell == cell:
                self.towers.remove(t)
                self.grid_blocked.remove(cell)
                self.money += int(TOWER_TYPES[t.type_id]["cost"] * 0.5)
                self.recalc_all_paths()
                return

    def start_wave(self):
        if self.wave_in_progress or self.game_result: return
        if self.wave >= self.max_waves: return
        self.wave += 1
        self.wave_in_progress = True
        self.spawn_timer = 0.0
        self.spawned = 0

    def update(self, dt):
        if self.game_result: return #Cek apakah game sudah selesai

        if self.health <= 0:
            self.game_result = "DEFEAT"

            pygame.mixer.music.stop()
            if defeat_fx:   
                defeat_fx.play()

            return
        if self.wave == self.max_waves and not self.wave_in_progress and len(self.enemies) == 0:
            self.game_result = "VICTORY"

            pygame.mixer.music.stop()
            if victory_fx:
                victory_fx.play()

            # POINT SYSTEM
            self.score += int(500 * self.score_multiplier)
            return

        if self.wave_in_progress:
            self.spawn_timer -= dt
            current_wave_count = BASE_WAVE_ENEMIES + (self.wave * 2)
            while self.spawned < current_wave_count and self.spawn_timer <= 0:
                
                e = Enemy(self.start_pos, self.wave)
                e.set_path(list(self.default_path) if self.default_path else [self.start_pos])
                self.enemies.append(e)
                self.spawned += 1
                self.spawn_timer += SPAWN_INTERVAL
            if self.spawned >= current_wave_count and len([e for e in self.enemies if e.hp > 0]) == 0:
                self.wave_in_progress = False
                self.money += 50 + (self.wave * 10)

                # POINT SYSTEM
                self.score += int(100 * self.score_multiplier)

        for e in list(self.enemies):
            e.update(dt)
            if e.reached_goal:
                self.health -= 1
                
                # POINT SYSTEM
                self.score = max(0, self.score - 5)

                self.enemies.remove(e)
            elif e.hp <= 0:
                self.money += 5 + self.wave

                # POINT SYSTEM
                gained = int((10 * self.wave) * self.score_multiplier)
                self.score += gained


                self.enemies.remove(e)

        for t in self.towers:
            t.cooldown -= dt
            if t.cooldown <= 0:
                target = None
                best = 1e9
                for e in self.enemies:
                    if e.hp > 0 and not e.reached_goal and t.in_range(e.pos):
                        d = (e.pos[0]-(t.cell[0]+0.5)*TILE)**2 + (e.pos[1]-(t.cell[1]+0.5)*TILE)**2
                        if d < best: best = d; target = e
                if target:
                    self.projectiles.append(Projectile(((t.cell[0]+0.5)*TILE, (t.cell[1]+0.5)*TILE), target, t.damage))
                    t.cooldown = t.fire_rate

        for p in list(self.projectiles):
            p.update(dt)
            if not p.alive: self.projectiles.remove(p)

# Drawing Functions
def draw_centered_text(surf, text, font, color, center_pos):
    t = font.render(text, True, color)
    r = t.get_rect(center=center_pos)
    surf.blit(t, r)

# Draw Instructions Screen
def draw_instructions(surf):
    surf.fill(MENU_BG)
    
    draw_centered_text(surf, "HOW TO PLAY", font_menu_title, (255, 255, 255), (SCREEN_W//2, 40))
    
    # Instructions content
    y_offset = 90
    x_margin = 80
    line_height = 24
    
    instructions = [
        ("OBJECTIVE:", (255, 200, 100)),
        ("Defend your base from waves of enemies!", (200, 200, 200)),
        ("", (0, 0, 0)),
        ("GAMEPLAY:", (255, 200, 100)),
        ("• Green cell = Enemy spawn point", (200, 200, 200)),
        ("• Red cell = Your base (protect it!)", (200, 200, 200)),
        ("• Enemies follow the gray path to your base", (200, 200, 200)),
        ("• Place towers to destroy enemies before they reach the red cell", (200, 200, 200)),
        ("", (0, 0, 0)),
        ("CONTROLS:", (255, 200, 100)),
        ("• LEFT CLICK - Place selected tower", (200, 200, 200)),
        ("• RIGHT CLICK - Remove tower (50% refund)", (200, 200, 200)),
        ("• SPACE or Click 'NEXT WAVE' - Start the next wave", (200, 200, 200)),
        ("• 1, 2, 3 Keys - Select tower type", (200, 200, 200)),
        ("• ESC - Return to menu", (200, 200, 200)),
        ("", (0, 0, 0)),
        ("TOWER TYPES:", (255, 200, 100)),
        ("• Standard ($50) - Balanced tower, good for general defense", (200, 200, 200)),
        ("• Sniper ($120) - Long range, high damage, slow fire rate", (200, 200, 200)),
        ("• Rapid ($90) - Short range, low damage, very fast fire rate", (200, 200, 200)),
        ("", (0, 0, 0)),
        ("TIPS:", (255, 200, 100)),
        ("• You cannot place towers during a wave", (200, 200, 200)),
        ("• You cannot block the enemy path completely", (200, 200, 200)),
        ("• Enemies get stronger each wave", (200, 200, 200)),
        ("• Earn money by killing enemies and completing waves", (200, 200, 200)),
        ("• You lose 1 life when an enemy reaches your base", (200, 200, 200)),
    ]
    
    for text, color in instructions:
        if text:  # Skip empty lines for spacing
            txt_surface = font_small.render(text, True, color)
            surf.blit(txt_surface, (x_margin, y_offset))
        y_offset += line_height
    
    # Back button
    mx, my = pygame.mouse.get_pos()
    back_btn = pygame.Rect(SCREEN_W//2 - 80, SCREEN_H - 60, 160, 45)
    btn_color = BTN_EXIT
    if back_btn.collidepoint(mx, my):
        btn_color = (min(255, BTN_EXIT[0]+40), min(255, BTN_EXIT[1]+40), min(255, BTN_EXIT[2]+40))
    
    pygame.draw.rect(surf, btn_color, back_btn, border_radius=10)
    draw_centered_text(surf, "BACK", font_menu_btn, (255, 255, 255), back_btn.center)
    
    return back_btn

def draw_menu(surf):
    surf.fill(MENU_BG)
    
    # Question mark button in upper left
    mx, my = pygame.mouse.get_pos()
    help_btn = pygame.Rect(20, 20, 50, 50)
    help_color = (80, 120, 180)
    if help_btn.collidepoint(mx, my):
        help_color = (100, 150, 220)
    
    pygame.draw.circle(surf, help_color, help_btn.center, 25)
    pygame.draw.circle(surf, (255, 255, 255), help_btn.center, 25, 3)
    draw_centered_text(surf, "?", font_menu_title, (255, 255, 255), help_btn.center)
    
    draw_centered_text(surf, "TOWER DEFENSE", font_menu_title, (255, 255, 255), (SCREEN_W//2, 80))
    draw_centered_text(surf, "Select Difficulty:", font, (200, 200, 200), (SCREEN_W//2, 140))
    
    buttons = [
        (pygame.Rect(SCREEN_W//2 - 100, 190, 200, 50), BTN_EASY, "EASY (3 Waves)", 3),
        (pygame.Rect(SCREEN_W//2 - 100, 260, 200, 50), BTN_MED, "MEDIUM (6 Waves)", 6),
        (pygame.Rect(SCREEN_W//2 - 100, 330, 200, 50), BTN_HARD, "HARD (10 Waves)", 10),
        (pygame.Rect(SCREEN_W//2 - 100, 400, 200, 50), BTN_EXIT, "EXIT GAME", "EXIT"),
    ]
    
    selection = None
    
    if help_btn.collidepoint(mx, my) and pygame.mouse.get_pressed()[0]:
        selection = "INSTRUCTIONS"
    
    for rect, col, txt, val in buttons:
        color = col
        if rect.collidepoint(mx, my):
            color = (min(255, col[0]+40), min(255, col[1]+40), min(255, col[2]+40))
            if pygame.mouse.get_pressed()[0]:
                selection = val
        pygame.draw.rect(surf, color, rect, border_radius=10)
        draw_centered_text(surf, txt, font_menu_btn, (255, 255, 255), rect.center)
    
    return selection

def draw_game(surf, state):
    # 1. Gambar Map / Tiles
    zone = get_difficulty_zone(state.max_waves)
    tileset = TILESETS[zone]

    for x in range(GRID_W):
        for y in range(GRID_H):
            surf.blit(tileset["base"], (x * TILE, y * TILE))

    if state.default_path:
        for cx, cy in state.default_path:
            surf.blit(tileset["path"], (cx * TILE, cy * TILE))

    # 2. Gambar Start & Goal
    sx, sy = state.start_pos
    gx, gy = state.goal_pos
    
    sx_px, sy_px = sx * TILE, sy * TILE
    gx_px, gy_px = gx * TILE, gy * TILE

    pygame.draw.rect(surf, (60,180,80), (sx_px+2, sy_px+2, TILE-4, TILE-4))
    pygame.draw.rect(surf, (180,60,60), (gx_px+2, gy_px+2, TILE-4, TILE-4))
    
    # Konfigurasi Bar
    bar_w = 40
    bar_h = 6
    
    # === A. Base Kita (Goal) ===
    if gy == 0:
        base_bar_y = gy_px + TILE + 4       # Di bawah tile
        base_text_y = gy_px + TILE + 18     # Di bawah bar
    else:
        base_bar_y = gy_px - 8              # Di atas tile
        base_text_y = gy_px - 22            # Di atas bar
    
    base_bar_x = gx_px + TILE//2 - bar_w//2

    # Gambar Teks (HP Base)
    draw_centered_text(surf, f"{int(state.health)}", font_small, (255, 255, 255), (gx_px + TILE//2, base_text_y))
    
    # Gambar HP Bar Base
    max_lives = 20.0
    lives_pct = max(0, state.health / max_lives)
    pygame.draw.rect(surf, (50, 0, 0), (base_bar_x, base_bar_y, bar_w, bar_h))
    pygame.draw.rect(surf, (0, 255, 0), (base_bar_x, base_bar_y, int(bar_w * lives_pct), bar_h))


    # B. Base Musuh (Start/Spawn)
    if sy == 0:
        spawn_bar_y = sy_px + TILE + 4
        spawn_text_y = sy_px + TILE + 18
    else:
        spawn_bar_y = sy_px - 8
        spawn_text_y = sy_px - 22
        
    spawn_bar_x = sx_px + TILE//2 - bar_w//2

    # Hitung data musuh
    if state.wave_in_progress:
        total_wave_enemies = BASE_WAVE_ENEMIES + (state.wave * 2)
        current_threat = (total_wave_enemies - state.spawned) + len(state.enemies)
        threat_pct = max(0, current_threat / total_wave_enemies)
        enemy_text = f"{int(current_threat)}"
    else:
        threat_pct = 0.0
        enemy_text = "0"
    
    # Gambar Teks (Sisa Musuh)
    draw_centered_text(surf, enemy_text, font_small, (255, 255, 255), (sx_px + TILE//2, spawn_text_y))
    
    # Gambar Bar Merah (Indikator Wave)
    pygame.draw.rect(surf, (50, 0, 0), (spawn_bar_x, spawn_bar_y, bar_w, bar_h))
    pygame.draw.rect(surf, (255, 50, 50), (spawn_bar_x, spawn_bar_y, int(bar_w * threat_pct), bar_h))


    # 3. Gambar Tower
    for t in state.towers:
        pygame.draw.rect(
            surf,
            t.color,
            (t.cell[0]*TILE+2, t.cell[1]*TILE+2, TILE-4, TILE-4)
        )
        pygame.draw.circle(
            surf,
            (30,30,30),
            (int((t.cell[0]+0.5)*TILE), int((t.cell[1]+0.5)*TILE)),
            6
        )

    # 4. Gambar Musuh
    for e in state.enemies:
        pygame.draw.circle(surf, e.color, (int(e.pos[0]), int(e.pos[1])), 10)
        pygame.draw.rect(
            surf,
            (0,200,0),
            (e.pos[0]-10, e.pos[1]-16, 20 * (e.hp/e.max_hp), 3)
        )

    # 5. Gambar Projectile
    for p in state.projectiles:
        pygame.draw.circle(
            surf,
            PROJECTILE_COLOR,
            (int(p.pos[0]), int(p.pos[1])),
            4
        )

    # 6. Gambar UI Sidebar
    pygame.draw.rect(
        surf,
        BG_SIDEBAR,
        (GRID_W * TILE, 0, SIDEBAR_W, SCREEN_H)
    )

    x_off = GRID_W * TILE + 15
    y_off = 15
    surf.blit(font_title.render("STATS", True, (255,255,255)), (x_off, y_off))
    y_off += 30

    for s in [
        f"Money : ${state.money}",
        f"Lives : {state.health}",
        f"Wave  : {state.wave} / {state.max_waves}",
        f"Score : {state.score}"
    ]:
        surf.blit(font.render(s, True, TEXT_COLOR), (x_off, y_off))
        y_off += 25

    y_off += 20
    mx, my = pygame.mouse.get_pos()

    for tid, data in TOWER_TYPES.items():
        r = pygame.Rect(x_off, y_off, SIDEBAR_W - 30, 50)
        col = BTN_SELECTED if state.selected_tower_type == tid else BTN_COLOR
        if r.collidepoint(mx, my) and state.selected_tower_type != tid:
            col = BTN_HOVER

        pygame.draw.rect(surf, col, r, border_radius=5)
        pygame.draw.rect(surf, data["color"], (x_off+5, y_off+5, 15, 15))
        surf.blit(
            font.render(f"{data['name']} (${data['cost']})", True, (255,255,255)),
            (x_off+25, y_off+5)
        )
        y_off += 60

    start_r = pygame.Rect(x_off, SCREEN_H - 120, SIDEBAR_W - 30, 40)
    col = (100, 60, 60) if state.wave_in_progress else (60, 120, 60)
    if not state.wave_in_progress and start_r.collidepoint(mx, my):
        col = (80, 140, 80)

    pygame.draw.rect(surf, col, start_r, border_radius=5)
    txt = "Wave Incoming" if state.wave_in_progress else "NEXT WAVE"
    draw_centered_text(surf, txt, font, (255,255,255), start_r.center)

    surf.blit(font.render("ESC: Menu", True, (150,150,150)),
              (x_off, SCREEN_H - 30))

    if state.game_result:
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surf.blit(overlay, (0,0))

        col = (100,255,100) if state.game_result == "VICTORY" else (255,100,100)
        draw_centered_text(
            surf,
            state.game_result,
            font_overlay,
            col,
            (SCREEN_W//2, SCREEN_H//2 - 50)
        )
        draw_centered_text(
            surf,
            f"Final Score: {state.score}",
            font_menu_btn,
            (255, 255, 255),
            (SCREEN_W//2, SCREEN_H//2 + 10)
        )
        draw_centered_text(
            surf,
            "Press ESC to Menu",
            font,
            (200,200,200),
            (SCREEN_W//2, SCREEN_H//2 + 60)
        )


# Main Execution
def main():
    game_state = None
    show_instructions = False
    running = True
    last_time = pygame.time.get_ticks() / 1000.0

    # Mulai Musik Menu Awal
    try:
        pygame.mixer.music.load(MENU_MUSIC_PATH)
        pygame.mixer.music.set_volume(0.4)
        pygame.mixer.music.play(-1) 
    except Exception as e:
        print(f"Music Error: {e}")

    while running:
        now = pygame.time.get_ticks() / 1000.0
        dt = now - last_time
        last_time = now

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            if show_instructions:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    show_instructions = False
            elif game_state is None:
                pass 
            else:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE: game_state.start_wave()
                    elif event.key == pygame.K_1: game_state.selected_tower_type = 1
                    elif event.key == pygame.K_2: game_state.selected_tower_type = 2
                    elif event.key == pygame.K_3: game_state.selected_tower_type = 3

                    # Escape to Menu
                    elif event.key == pygame.K_ESCAPE: 
                        game_state = None 
                        # Ganti kembali ke Musik Menu
                        try:
                            pygame.mixer.music.load(MENU_MUSIC_PATH)
                            pygame.mixer.music.set_volume(0.4)
                            pygame.mixer.music.play(-1)
                        except: pass
                 
                
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    mx, my = event.pos
                    if mx > GRID_W * TILE:
                        x_off = GRID_W * TILE + 15
                        y_off = 15 + 30 + 25*3 + 20
                        for tid in TOWER_TYPES:
                            if pygame.Rect(x_off, y_off, SIDEBAR_W-30, 50).collidepoint(mx, my):
                                game_state.selected_tower_type = tid
                            y_off += 60
                        if pygame.Rect(x_off, SCREEN_H - 120, SIDEBAR_W-30, 40).collidepoint(mx, my):
                            game_state.start_wave()
                    else:
                        cell = (mx // TILE, my // TILE)
                        if event.button == 1: game_state.place_tower(cell)
                        elif event.button == 3: game_state.remove_tower(cell)

        if show_instructions:
            back_btn = draw_instructions(screen)
            mx, my = pygame.mouse.get_pos()
            if back_btn.collidepoint(mx, my) and pygame.mouse.get_pressed()[0]:
                show_instructions = False
                pygame.time.wait(200) # Prevent instant click-through
        elif game_state is None:
            action = draw_menu(screen)
            if action == "EXIT":
                running = False
            elif action == "INSTRUCTIONS":
                show_instructions = True
                pygame.time.wait(200) # Prevent instant click-through
            elif action is not None:
                #START GAME (GANTI MUSIK KE DRUM)
                try:
                    pygame.mixer.music.stop() # Stop menu music
                    pygame.mixer.music.load(GAME_MUSIC_PATH) # Load drum
                    pygame.mixer.music.set_volume(0.5) # Set volume
                    pygame.mixer.music.play(-1) # Loop forever
                except Exception as e:
                    print(f"Game Music Error: {e}")
                
                game_state = GameState(action)
        else:
            game_state.update(dt)
            draw_game(screen, game_state)
            
            mx, my = pygame.mouse.get_pos()
            if mx < GRID_W * TILE and not game_state.game_result:
                hx, hy = mx // TILE, my // TILE
                valid = (hx, hy) not in game_state.grid_blocked \
                        and (hx, hy) != game_state.start_pos \
                        and (hx, hy) != game_state.goal_pos \
                        and not game_state.wave_in_progress
                col = TOWER_TYPES[game_state.selected_tower_type]["color"]
                s = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
                s.fill((col[0], col[1], col[2], 100) if valid else (200, 50, 50, 100))
                screen.blit(s, (hx*TILE, hy*TILE))
                if valid:
                     range_px = TOWER_TYPES[game_state.selected_tower_type]["range"] * TILE
                     pygame.draw.circle(screen, (255, 255, 255), (int((hx+0.5)*TILE), int((hy+0.5)*TILE)), int(range_px), 1)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()