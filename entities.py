import pygame
import math
import heapq
from config import * 

#A* Algorithm 
def heuristic(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def neighbors(node):
    x, y = node
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nx, ny = x + dx, y + dy
        if 0 <= nx < GRID_W and 0 <= ny < GRID_H:
            yield (nx, ny)

def astar(start, goal, blocked):
    if start == goal: return [start]
    open_heap = []
    heapq.heappush(open_heap, (0 + heuristic(start, goal), 0, start, None))
    came_from = {}
    gscore = {start: 0}
    closed = set()

    while open_heap:
        f, g, current, parent = heapq.heappop(open_heap)
        if current in closed: continue
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
            if nb in blocked and nb != goal: continue
            tentative_g = g + 1
            if tentative_g < gscore.get(nb, float("inf")):
                gscore[nb] = tentative_g
                heapq.heappush(open_heap, (tentative_g + heuristic(nb, goal), tentative_g, nb, current))
    return None

# Game Classes
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
        cx, cy = (tx + 0.5) * TILE, (ty + 0.5) * TILE
        dist_tiles = math.hypot(cx - pos[0], cy - pos[1]) / TILE
        return dist_tiles <= self.range

class Enemy:
    def __init__(self, spawn_cell, wave_number):
        self.pos = ((spawn_cell[0] + 0.5) * TILE, (spawn_cell[1] + 0.5) * TILE)
        self.cell = spawn_cell
        self.path = []
        
        # Scaling difficulty
        hp_scale = 1.0 + (wave_number * 0.25)
        speed_scale = min(2.5, 1.0 + (wave_number * 0.08))
        
        self.max_hp = BASE_ENEMY_HEALTH * hp_scale
        self.hp = self.max_hp
        self.speed = BASE_ENEMY_SPEED * speed_scale
        
        red_val = max(50, 255 - int(wave_number * 12))
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
        dx, dy = self.target[0] - self.pos[0], self.target[1] - self.pos[1]
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
        dx, dy = self.target.pos[0] - self.pos[0], self.target.pos[1] - self.pos[1]
        dist = math.hypot(dx, dy)
        if dist < 5:
            self.target.hp -= self.damage
            self.alive = False
            return
        move = self.speed * dt
        self.pos = (self.pos[0] + dx / dist * move, self.pos[1] + dy / dist * move)