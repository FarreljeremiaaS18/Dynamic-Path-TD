import pygame
import sys
from config import * # Ambil setting
from entities import Tower, Enemy, Projectile, astar

pygame.init()
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption("Tower Defense A* - Modular")
clock = pygame.time.Clock()

# Font Setup
font = pygame.font.SysFont("Consolas", 16)
font_title = pygame.font.SysFont("Consolas", 20, bold=True)
font_menu_title = pygame.font.SysFont("Consolas", 40, bold=True)
font_menu_btn = pygame.font.SysFont("Consolas", 24, bold=True)
font_overlay = pygame.font.SysFont("Consolas", 50, bold=True)

class GameState:
    def __init__(self, max_waves):
        self.grid_blocked = set()
        self.towers = []
        self.enemies = []
        self.projectiles = []
        self.money = 250
        self.health = 20
        self.wave = 0
        self.max_waves = max_waves
        self.wave_in_progress = False
        self.spawn_timer = 0.0
        self.spawned = 0
        self.selected_tower_type = 1
        self.default_path = []
        self.game_result = None  # "VICTORY" or "DEFEAT"
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
            e.set_path(p if p else [cur_cell])
            if p and p[0] != cur_cell: e.path.insert(0, cur_cell)

    def place_tower(self, cell):
        if self.game_result: return
        if self.wave_in_progress: return 
        if cell == START_POS or cell == GOAL_POS: return
        if cell in self.grid_blocked: return
        
        stats = TOWER_TYPES[self.selected_tower_type]
        if self.money < stats["cost"]: return
        
        self.grid_blocked.add(cell)
        if astar(START_POS, GOAL_POS, self.grid_blocked) is None:
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
        if self.game_result: return

        if self.health <= 0:
            self.game_result = "DEFEAT"
            return
        if self.wave == self.max_waves and not self.wave_in_progress and len(self.enemies) == 0:
            self.game_result = "VICTORY"
            return

        if self.wave_in_progress:
            self.spawn_timer -= dt
            current_wave_count = BASE_WAVE_ENEMIES + (self.wave * 2)
            while self.spawned < current_wave_count and self.spawn_timer <= 0:
                e = Enemy(START_POS, self.wave)
                e.set_path(list(self.default_path) if self.default_path else [START_POS])
                self.enemies.append(e)
                self.spawned += 1
                self.spawn_timer += SPAWN_INTERVAL
            if self.spawned >= current_wave_count and len([e for e in self.enemies if e.hp > 0]) == 0:
                self.wave_in_progress = False
                self.money += 50 + (self.wave * 10)

        for e in list(self.enemies):
            e.update(dt)
            if e.reached_goal:
                self.health -= 1
                self.enemies.remove(e)
            elif e.hp <= 0:
                self.money += 5 + self.wave
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

def draw_menu(surf):
    surf.fill(MENU_BG)
    draw_centered_text(surf, "TOWER DEFENSE", font_menu_title, (255, 255, 255), (SCREEN_W//2, 80))
    draw_centered_text(surf, "Select Difficulty:", font, (200, 200, 200), (SCREEN_W//2, 140))
    
    mx, my = pygame.mouse.get_pos()
    
    buttons = [
        (pygame.Rect(SCREEN_W//2 - 100, 190, 200, 50), BTN_EASY, "EASY (3 Waves)", 3),
        (pygame.Rect(SCREEN_W//2 - 100, 260, 200, 50), BTN_MED, "MEDIUM (6 Waves)", 6),
        (pygame.Rect(SCREEN_W//2 - 100, 330, 200, 50), BTN_HARD, "HARD (10 Waves)", 10),
        (pygame.Rect(SCREEN_W//2 - 100, 400, 200, 50), BTN_EXIT, "EXIT GAME", "EXIT"), 
    ]
    
    selection = None
    for rect, col, txt, val in buttons:
        color = col
        if rect.collidepoint(mx, my):
            # Efek hover (sedikit lebih terang)
            color = (min(255, col[0]+40), min(255, col[1]+40), min(255, col[2]+40))
            if pygame.mouse.get_pressed()[0]:
                selection = val
        
        pygame.draw.rect(surf, color, rect, border_radius=10)
        draw_centered_text(surf, txt, font_menu_btn, (255, 255, 255), rect.center)
    
    return selection

def draw_game(surf, state):
    surf.fill(BG_GAME)
    # Path
    if state.default_path:
        pts = [((c[0]+0.5)*TILE, (c[1]+0.5)*TILE) for c in state.default_path]
        if len(pts) > 1: pygame.draw.lines(surf, PATH_COLOR, False, pts, 6)
    
    # Start/Goal
    pygame.draw.rect(surf, (60,180,80), (START_POS[0]*TILE+2, START_POS[1]*TILE+2, TILE-4, TILE-4))
    pygame.draw.rect(surf, (180,60,60), (GOAL_POS[0]*TILE+2, GOAL_POS[1]*TILE+2, TILE-4, TILE-4))

    # Objects
    for t in state.towers:
        pygame.draw.rect(surf, t.color, (t.cell[0]*TILE+2, t.cell[1]*TILE+2, TILE-4, TILE-4))
        pygame.draw.circle(surf, (30,30,30), (int((t.cell[0]+0.5)*TILE), int((t.cell[1]+0.5)*TILE)), 6)
    for e in state.enemies:
        pygame.draw.circle(surf, e.color, (int(e.pos[0]), int(e.pos[1])), 10)
        pygame.draw.rect(surf, (0,200,0), (e.pos[0]-10, e.pos[1]-16, 20 * (e.hp/e.max_hp), 3))
    for p in state.projectiles:
        pygame.draw.circle(surf, PROJECTILE_COLOR, (int(p.pos[0]), int(p.pos[1])), 4)

    # UI Sidebar
    pygame.draw.rect(surf, BG_SIDEBAR, (GRID_W * TILE, 0, SIDEBAR_W, SCREEN_H))
    x_off = GRID_W * TILE + 15
    y_off = 15
    surf.blit(font_title.render("STATS", True, (255,255,255)), (x_off, y_off))
    y_off += 30
    for s in [f"Money : ${state.money}", f"Lives : {state.health}", f"Wave  : {state.wave} / {state.max_waves}"]:
        surf.blit(font.render(s, True, TEXT_COLOR), (x_off, y_off))
        y_off += 25
    
    # Shop Buttons (Visual)
    y_off += 20
    mx, my = pygame.mouse.get_pos()
    for tid, data in TOWER_TYPES.items():
        r = pygame.Rect(x_off, y_off, SIDEBAR_W - 30, 50)
        col = BTN_SELECTED if state.selected_tower_type == tid else BTN_COLOR
        if r.collidepoint(mx, my) and state.selected_tower_type != tid: col = BTN_HOVER
        pygame.draw.rect(surf, col, r, border_radius=5)
        pygame.draw.rect(surf, data["color"], (x_off+5, y_off+5, 15, 15))
        surf.blit(font.render(f"{data['name']} (${data['cost']})", True, (255,255,255)), (x_off+25, y_off+5))
        y_off += 60

    # Start Wave Button
    start_r = pygame.Rect(x_off, SCREEN_H - 120, SIDEBAR_W - 30, 40)
    col = (100, 60, 60) if state.wave_in_progress else (60, 120, 60)
    if not state.wave_in_progress and start_r.collidepoint(mx, my): col = (80, 140, 80)
    pygame.draw.rect(surf, col, start_r, border_radius=5)
    txt = "Wave Incoming" if state.wave_in_progress else "NEXT WAVE"
    draw_centered_text(surf, txt, font, (255,255,255), start_r.center)
    
    # Instructions
    surf.blit(font.render("ESC: Menu", True, (150,150,150)), (x_off, SCREEN_H - 30))

    # Overlay
    if state.game_result:
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surf.blit(overlay, (0,0))
        col = (100, 255, 100) if state.game_result == "VICTORY" else (255, 100, 100)
        draw_centered_text(surf, state.game_result, font_overlay, col, (SCREEN_W//2, SCREEN_H//2 - 20))
        draw_centered_text(surf, "Press ESC to Menu", font, (200,200,200), (SCREEN_W//2, SCREEN_H//2 + 30))

# Main Execution
def main():
    game_state = None
    running = True
    last_time = pygame.time.get_ticks() / 1000.0

    while running:
        now = pygame.time.get_ticks() / 1000.0
        dt = now - last_time
        last_time = now

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            if game_state is None:
                pass 
            else:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE: game_state.start_wave()
                    elif event.key == pygame.K_1: game_state.selected_tower_type = 1
                    elif event.key == pygame.K_2: game_state.selected_tower_type = 2
                    elif event.key == pygame.K_3: game_state.selected_tower_type = 3
                    elif event.key == pygame.K_ESCAPE: game_state = None 
                
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

        # Draw / Update
        if game_state is None:
            action = draw_menu(screen)
            if action == "EXIT":
                running = False
            elif action is not None:
                game_state = GameState(action)
        else:
            game_state.update(dt)
            draw_game(screen, game_state)
            
            # Hover Ghost Tower
            mx, my = pygame.mouse.get_pos()
            if mx < GRID_W * TILE and not game_state.game_result:
                hx, hy = mx // TILE, my // TILE
                
                valid = (hx, hy) not in game_state.grid_blocked \
                        and (hx, hy) != START_POS \
                        and (hx, hy) != GOAL_POS \
                        and not game_state.wave_in_progress 

                col = TOWER_TYPES[game_state.selected_tower_type]["color"]
                s = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
                
                # Jika valid warna tower, jika tidak valid warna Merah (Invalid)
                s.fill((col[0], col[1], col[2], 100) if valid else (200, 50, 50, 100))
                screen.blit(s, (hx*TILE, hy*TILE))
                
                # Hanya gambar lingkaran range jika valid
                if valid:
                     range_px = TOWER_TYPES[game_state.selected_tower_type]["range"] * TILE
                     pygame.draw.circle(screen, (255, 255, 255), (int((hx+0.5)*TILE), int((hy+0.5)*TILE)), int(range_px), 1)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()