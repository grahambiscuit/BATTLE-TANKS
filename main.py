import pygame
import math
import random
from collections import deque
import heapq

# Initialize Pygame
pygame.init()

# Constants
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1020
FPS = 60

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (220, 50, 50)
BLUE = (50, 50, 220)
GREEN = (50, 220, 50)
GRAY = (100, 100, 100)
DARK_GRAY = (60, 60, 60)
YELLOW = (255, 255, 0)
ORANGE = (255, 165, 0)

# Game settings
TANK_SIZE = 30
TANK_SPEED = 5
ROTATION_SPEED = 2
BULLET_SPEED = 10
BULLET_SIZE = 6
WALL_THICKNESS = 5
TILE_WIDTH = 70
TILE_HEIGHT = 45
GRID_SIZE = TILE_WIDTH  # Keep for backward compatibility
BORDER_THICKNESS = 0
MATCH_SECONDS = 90

# Path tracking removed — we no longer store tank position history in-game.

class Tile:
    """A tile-sized obstacle with optional texture support.

    Tiles live on a TILE_WIDTH x TILE_HEIGHT grid and define a rect at (grid_x * TILE_WIDTH, grid_y * TILE_HEIGHT).
    """
    def __init__(self, grid_x, grid_y, texture=None, collidable=True):
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.texture = texture
        self.collidable = collidable

        # Use TILE_WIDTH and TILE_HEIGHT for placement and sizing
        self.width = TILE_WIDTH
        self.height = TILE_HEIGHT
        self.rect = pygame.Rect(grid_x * TILE_WIDTH, grid_y * TILE_HEIGHT, self.width, self.height)

    def draw(self, screen):
        if self.texture:
            try:
                # Draw texture scaled to TILE_WIDTH x TILE_HEIGHT
                tex = pygame.transform.smoothscale(self.texture, (self.width, self.height))
                screen.blit(tex, (self.rect.x, self.rect.y))
            except Exception:
                pygame.draw.rect(screen, DARK_GRAY, self.rect)
                pygame.draw.rect(screen, GRAY, self.rect, 2)
        else:
            pygame.draw.rect(screen, DARK_GRAY, self.rect)
            pygame.draw.rect(screen, GRAY, self.rect, 2)

    def collides(self):
        return self.collidable

def load_texture(path, size=None, keep_original=False):
    """Load an image file and optionally scale it.

    - path: asset path
    - size: None (default) -> scale to GRID_SIZE x GRID_SIZE
            tuple (w,h) -> scale to the given size

    Returns a pygame.Surface or None on failure.
    """
    try:
        surf = pygame.image.load(path).convert_alpha()
        if keep_original:
            return surf
        if size is None:
            size = (GRID_SIZE, GRID_SIZE)
        # allow passing an int for square sizing
        if isinstance(size, int):
            size = (size, size)
        return pygame.transform.smoothscale(surf, size)
    except Exception:
        return None


def load_sound(path):
    """Try loading a sound and return pygame.mixer.Sound or None on error.

    Files can be wav/ogg etc. We handle missing assets gracefully.
    """
    try:
        snd = pygame.mixer.Sound(path)
        return snd
    except Exception:
        return None


def try_load_textures(names, size=None, keep_original=False):
    """Try multiple filenames, returning the first texture that loads.

    names: iterable of relative paths (tried in order)
    size: passed to load_texture
    keep_original: passed to load_texture
    """
    for n in names:
        tex = load_texture(n, size=size, keep_original=keep_original)
        if tex:
            return tex
    return None

class MapGenerator:
    """Generates random maze-like maps with MAP1 or MAP2 variants"""
    @staticmethod
    def generate_map(map_type=None):
        """Generate a random map. If map_type is None, randomly pick MAP1 or MAP2.
        
        Returns: (tiles, map_bg, border_image)
            - tiles: list of Tile objects for obstacles only (no border tiles)
            - map_bg: background image texture
            - border_image: full border image (drawn as single large sprite at edges)
        """
        tiles = []

        # Grid dimensions based on TILE_WIDTH and TILE_HEIGHT
        grid_w = max(1, SCREEN_WIDTH // TILE_WIDTH)
        grid_h = max(1, SCREEN_HEIGHT // TILE_HEIGHT)

        # Randomly select map type if not specified
        if map_type is None:
            map_type = random.choice(['map1', 'map2'])

        # Load border and obstacle textures based on map type
        if map_type == 'map1':
            border_image = load_texture('assets/map1/map1/BORDER1.png', keep_original=True)
            obstacle_texture1 = load_texture('assets/map1/map1/STEELBOX.png')
            obstacle_texture2 = load_texture('assets/map1/map1/WOODENCRATE.png')
            map_bg = load_texture('assets/map1/map1/MAPBG1.png', keep_original=True)
        else:  # map2
            border_image = load_texture('assets/map2/map2/BORDER2.png', keep_original=True)
            obstacle_texture1 = load_texture('assets/map2/map2/ROCK1.png')
            obstacle_texture2 = load_texture('assets/map2/map2/ROCK2.png')
            map_bg = load_texture('assets/map2/map2/MAPBG2.png', keep_original=True)

        # Internal random obstacles — place a few tiles around the map (no border tiles)
        num_tiles = random.randint(max(1, int(grid_w * grid_h * 0.04)), max(1, int(grid_w * grid_h * 0.12)))
        tries = 0
        placed = 0
        while placed < num_tiles and tries < num_tiles * 6:
            gx = random.randint(2, max(2, grid_w - 3))  # Keep away from borders
            gy = random.randint(2, max(2, grid_h - 3))

            # Avoid around spawn corners
            if (gx, gy) in [(2, 2), (grid_w - 3, grid_h - 3)]:
                tries += 1
                continue

            if any(t.grid_x == gx and t.grid_y == gy for t in tiles):
                tries += 1
                continue

            tiles.append(Tile(gx, gy, texture=obstacle_texture1 if random.random() < 0.5 else obstacle_texture2))
            placed += 1
            tries += 1

        # Return tiles, map background, and border image
        return tiles, map_bg, border_image

class Bullet:   
    def __init__(self, x, y, angle, owner):
        self.x = x
        self.y = y
        self.angle = angle
        self.owner = owner
        self.speed = BULLET_SPEED
        self.size = BULLET_SIZE
        self.bounces = 0
        self.max_bounces = 4
        self.active = True
    
    def update(self, tiles):
        if not self.active:
            return
        
        # Move bullet
        self.x += math.cos(math.radians(self.angle)) * self.speed
        self.y -= math.sin(math.radians(self.angle)) * self.speed
        
        # Check border collisions
        border_thickness = BORDER_THICKNESS
        bullet_rect = pygame.Rect(self.x - self.size/2, self.y - self.size/2, self.size, self.size)
        
        # Check if bullet hit border edges
        if (self.x - self.size/2 < border_thickness or self.x + self.size/2 > SCREEN_WIDTH - border_thickness or
            self.y - self.size/2 < border_thickness or self.y + self.size/2 > SCREEN_HEIGHT - border_thickness):
            self.bounces += 1
            if self.bounces > self.max_bounces:
                self.active = False
                return
            
            # Bounce back based on which border was hit
            if self.x - self.size/2 < border_thickness or self.x + self.size/2 > SCREEN_WIDTH - border_thickness:
                self.angle = 180 - self.angle
            else:
                self.angle = -self.angle
            return
        
        # Check obstacle tile collisions
        for tile in tiles:
            if not getattr(tile, 'collides', lambda: True)():
                continue
            if bullet_rect.colliderect(tile.rect):
                self.bounces += 1
                if self.bounces > self.max_bounces:
                    self.active = False
                    return
                
                # Determine bounce direction
                overlap_left = bullet_rect.right - tile.rect.left
                overlap_right = tile.rect.right - bullet_rect.left
                overlap_top = bullet_rect.bottom - tile.rect.top
                overlap_bottom = tile.rect.bottom - bullet_rect.top
                
                min_overlap = min(overlap_left, overlap_right, overlap_top, overlap_bottom)
                
                if min_overlap in (overlap_top, overlap_bottom):
                    self.angle = -self.angle
                else:
                    self.angle = 180 - self.angle
                
                # Move bullet away from wall
                self.x += math.cos(math.radians(self.angle)) * self.speed * 2
                self.y -= math.sin(math.radians(self.angle)) * self.speed * 2
                break
        
        # Check screen boundaries (should be redundant now but kept for safety)
        if self.x < 0 or self.x > SCREEN_WIDTH or self.y < 0 or self.y > SCREEN_HEIGHT:
            self.active = False
    
    def draw(self, screen):
        if self.active:
            pygame.draw.circle(screen, YELLOW, (int(self.x), int(self.y)), self.size)
            pygame.draw.circle(screen, ORANGE, (int(self.x), int(self.y)), self.size // 2)

class Tank:
    def __init__(self, x, y, color, controls, is_ai=False, texture=None, move_sound=None, shoot_sound=None, spawn_point=None):
        self.x = x
        self.y = y
        self.angle = 0
        self.color = color
        self.size = TANK_SIZE
        self.speed = TANK_SPEED
        self.controls = controls
        self.bullets = []
        self.alive = True
        self.is_ai = is_ai
        # Optional sprite texture for the tank (pygame.Surface)
        # Expect the texture to be square and reasonably sized; we'll draw it centered and rotated.
        self.texture = texture
        # Optional sounds for movement and shooting
        self.move_sound = move_sound
        self.shoot_sound = shoot_sound
        # cooldown to avoid spamming the movement sound every frame
        self._move_sound_cooldown = 0
        # scoring and respawn info
        self.kills = 0
        self.suicides = 0
        self.deaths = 0
        # spawn_point (x,y) to be used for instant respawn
        self.spawn_point = spawn_point if spawn_point is not None else (x, y)
        # path tracking removed
        self.shoot_cooldown = 0.5
        self.max_cooldown = 30
        # turret attributes left intentionally unused — turret textures are removed
        # so we keep these for compatibility but never load separate turret art.
        self.turret_texture = None
        self.turret_offset = (0, 0)
        self.turret_scale = 1.0
        self.turret_angle_offset = 0
        self.turret_debug = False
        
        # AI specific
        self.ai_state = "patrol"
        self.ai_target = None
        self.ai_path = []
        self.patrol_point = None
        self.ai_shoot_timer = 0.5
    
    def get_rect(self):
        return pygame.Rect(self.x - self.size/2, self.y - self.size/2, self.size, self.size)
    
    def move(self, dx, dy, tiles):
        new_x = self.x + dx
        new_y = self.y + dy
        
        # Check collision with border (BORDER_THICKNESS on all edges)
        border_thickness = max(BORDER_THICKNESS, max(TILE_WIDTH, TILE_HEIGHT))
        can_move = True
        
        # Test if new position hits any border
        if new_x - self.size/2 < border_thickness or new_x + self.size/2 > SCREEN_WIDTH - border_thickness:
            can_move = False
        if new_y - self.size/2 < border_thickness or new_y + self.size/2 > SCREEN_HEIGHT - border_thickness:
            can_move = False
        
        # Check collision with obstacle tiles
        if can_move:
            test_rect = pygame.Rect(new_x - self.size/2, new_y - self.size/2, self.size, self.size)
            for tile in tiles:
                if not getattr(tile, 'collides', lambda: True)():
                    continue
                if test_rect.colliderect(tile.rect):
                    can_move = False
                    break
        
        if can_move:
            self.x = new_x
            self.y = new_y
            
            # Path tracking removed — we no longer store position history

            # Play movement sound periodically while moving
            if self.move_sound:
                if self._move_sound_cooldown <= 0:
                    try:
                        self.move_sound.play()
                    except Exception:
                        pass
                    self._move_sound_cooldown = 8
                else:
                    self._move_sound_cooldown -= 1
    
    def rotate(self, direction):
        self.angle += direction * ROTATION_SPEED
        self.angle %= 360
    
    def shoot(self):
        if self.shoot_cooldown <= 0 and len(self.bullets) < 3:
            barrel_length = self.size
            bullet_x = self.x + math.cos(math.radians(self.angle)) * barrel_length
            bullet_y = self.y - math.sin(math.radians(self.angle)) * barrel_length
            self.bullets.append(Bullet(bullet_x, bullet_y, self.angle, self))
            # play shoot sound if available
            if self.shoot_sound:
                try:
                    self.shoot_sound.play()
                except Exception:
                    pass
            self.shoot_cooldown = self.max_cooldown

    def respawn(self):
        """Respawn tank instantly at its spawn point and clear bullets."""
        self.alive = True
        # reset bullets to avoid immediate re-death
        self.bullets.clear()
        self.x, self.y = self.spawn_point
        # minor reset of trackers
        self._move_sound_cooldown = 0
    
    def update_ai(self, tiles, target_tank, grid_map):
        """A* pathfinding AI"""
        if not target_tank or not target_tank.alive:
            self.ai_state = "patrol"
        
        # Update AI state
        dist_to_target = math.sqrt((self.x - target_tank.x)**2 + (self.y - target_tank.y)**2)
        
        if dist_to_target < 200 and self.has_line_of_sight(target_tank, tiles):
            self.ai_state = "attack"
        elif dist_to_target < 400:
            self.ai_state = "pursue"
        else:
            self.ai_state = "patrol"
        
        # Execute AI behavior
        if self.ai_state == "attack":
            # Aim at target
            angle_to_target = math.degrees(math.atan2(self.y - target_tank.y, target_tank.x - self.x))
            angle_diff = (angle_to_target - self.angle + 180) % 360 - 180
            
            if abs(angle_diff) > 5:
                self.rotate(1 if angle_diff > 0 else -1)
            
            # Shoot if aimed
            if abs(angle_diff) < 15:
                self.ai_shoot_timer += 1
                if self.ai_shoot_timer > 30:
                    self.shoot()
                    self.ai_shoot_timer = 0
            
        elif self.ai_state == "pursue":
            # Use A* to pursue target
            if random.random() < 0.1:  # Recalculate path periodically
                self.ai_path = self.astar_pathfind(target_tank, grid_map)
            
            if self.ai_path:
                target_pos = self.ai_path[0]
                self.move_towards(target_pos, tiles)
                
                if math.sqrt((self.x - target_pos[0])**2 + (self.y - target_pos[1])**2) < 30:
                    self.ai_path.pop(0)
        
        else:  # patrol
            if not self.patrol_point or random.random() < 0.01:
                self.patrol_point = (random.randint(100, SCREEN_WIDTH-100), 
                                    random.randint(100, SCREEN_HEIGHT-100))
            
            self.move_towards(self.patrol_point, tiles)
    
    def astar_pathfind(self, target, grid_map):
        """A* pathfinding algorithm"""
        start = (int(self.x // TILE_WIDTH), int(self.y // TILE_HEIGHT))
        goal = (int(target.x // TILE_WIDTH), int(target.y // TILE_HEIGHT))
        
        if start == goal:
            return []
        
        frontier = []
        heapq.heappush(frontier, (0, start))
        came_from = {start: None}
        cost_so_far = {start: 0}
        
        while frontier and len(came_from) < 200:  # Limit iterations
            current = heapq.heappop(frontier)[1]
            
            if current == goal:
                break
            
            for dx, dy in [(0,1), (1,0), (0,-1), (-1,0), (1,1), (-1,-1), (1,-1), (-1,1)]:
                next_pos = (current[0] + dx, current[1] + dy)
                
                if not (0 <= next_pos[0] < len(grid_map) and 0 <= next_pos[1] < len(grid_map[0])):
                    continue
                
                if grid_map[next_pos[0]][next_pos[1]]:
                    continue
                
                new_cost = cost_so_far[current] + (1.4 if abs(dx) + abs(dy) == 2 else 1)
                
                if next_pos not in cost_so_far or new_cost < cost_so_far[next_pos]:
                    cost_so_far[next_pos] = new_cost
                    priority = new_cost + abs(next_pos[0] - goal[0]) + abs(next_pos[1] - goal[1])
                    heapq.heappush(frontier, (priority, next_pos))
                    came_from[next_pos] = current
        
        # Reconstruct path
        if goal not in came_from:
            return []
        
        path = []
        current = goal
        while current != start:
            path.append((current[0] * TILE_WIDTH + TILE_WIDTH//2,
                        current[1] * TILE_HEIGHT + TILE_HEIGHT//2))
            current = came_from[current]
        path.reverse()
        
        return path[:10]  # Return first 10 waypoints
    
    def move_towards(self, target_pos, tiles):
        angle_to_target = math.degrees(math.atan2(self.y - target_pos[1], target_pos[0] - self.x))
        angle_diff = (angle_to_target - self.angle + 180) % 360 - 180
        
        if abs(angle_diff) > 5:
            self.rotate(1 if angle_diff > 0 else -1)
        else:
            dx = math.cos(math.radians(self.angle)) * self.speed
            dy = -math.sin(math.radians(self.angle)) * self.speed
            self.move(dx, dy, tiles)
    
    def has_line_of_sight(self, target, tiles):
        steps = 20
        dx = (target.x - self.x) / steps
        dy = (target.y - self.y) / steps
        
        for i in range(steps):
            check_x = self.x + dx * i
            check_y = self.y + dy * i
            check_rect = pygame.Rect(check_x - 5, check_y - 5, 10, 10)
            
            for wall in tiles:
                if not getattr(wall, 'collides', lambda: True)():
                    continue
                if check_rect.colliderect(wall.rect):
                    return False
        return True
    
    def update(self, keys, tiles, target_tank=None, grid_map=None):
        if not self.alive:
            return
        
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1
        
        if self.is_ai:
            self.update_ai(tiles, target_tank, grid_map)
        else:
            # Player controls
            dx, dy = 0, 0
            
            if keys[self.controls['up']]:
                dx = math.cos(math.radians(self.angle)) * self.speed
                dy = -math.sin(math.radians(self.angle)) * self.speed
            if keys[self.controls['down']]:
                dx = -math.cos(math.radians(self.angle)) * self.speed
                dy = math.sin(math.radians(self.angle)) * self.speed
            
            if dx != 0 or dy != 0:
                self.move(dx, dy, tiles)
            
            if keys[self.controls['left']]:
                self.rotate(1)
            if keys[self.controls['right']]:
                self.rotate(-1)
        
        # Update bullets
        for bullet in self.bullets[:]:
            bullet.update(tiles)
            if not bullet.active:
                self.bullets.remove(bullet)
    
    def draw(self, screen):
        if not self.alive:
            return
        # If a texture is present, draw rotated sprite centered on the tank.
        if self.texture:
            try:
                img = self.texture
                iw, ih = img.get_size()
                if iw <= 0 or ih <= 0:
                    raise Exception('invalid texture')

                # target max dimension: fit inside a square around the tank (avoid stretching)
                max_dim = int(self.size * 2)
                scale = min(max_dim / iw, max_dim / ih)
                # allow small upscaling, but don't get zero
                scale = max(scale, 0.01)
                new_w = max(1, int(iw * scale))
                new_h = max(1, int(ih * scale))

                scaled = pygame.transform.smoothscale(img, (new_w, new_h))
                # Rotate the sprite to match the same angle convention used by
                # the barrel math (cos/sin uses +angle for CCW rotation) so
                # the sprite and barrel point the same direction.
                rotated = pygame.transform.rotate(scaled, self.angle)
                rect = rotated.get_rect(center=(int(self.x), int(self.y)))
                screen.blit(rotated, rect.topleft)
            except Exception:
                # fallback to polygon drawing
                self.texture = None

        if not self.texture:
            # Tank body (fallback)
            points = []
            for angle in [135, 45, -45, -135]:
                rad = math.radians(self.angle + angle)
                px = self.x + math.cos(rad) * self.size * 0.7
                py = self.y - math.sin(rad) * self.size * 0.7
                points.append((px, py))
            pygame.draw.polygon(screen, self.color, points)
            pygame.draw.polygon(screen, BLACK, points, 2)
        
        # Tank barrel (always draw overlay now - turret textures are removed)
            barrel_length = self.size * 1.2
            end_x = self.x + math.cos(math.radians(self.angle)) * barrel_length
            end_y = self.y - math.sin(math.radians(self.angle)) * barrel_length
            pygame.draw.line(screen, BLACK, (self.x, self.y), (end_x, end_y), 5)
            # Tank turret (visual)
            pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.size // 3)
            pygame.draw.circle(screen, BLACK, (int(self.x), int(self.y)), self.size // 3, 2)
        
        # Draw bullets
        for bullet in self.bullets:
            bullet.draw(screen)

class Game:
    def __init__(self):
        # Allow the user to resize the window
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
        pygame.display.set_caption("METAL BREAKOUT")
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = "menu"
        self.mode = None
        
        self.tiles = []
        self.tanks = []
        self.grid_map = None
        self.winner = None
        # runtime tooling removed for turret alignment (turret textures are disabled)
        # UI / menu image slots (user will add assets later)
        # (title bar removed - menu_title area used instead; user will provide assets later)
        # Store reserved UI geometry so artwork can be placed / replaced later
        self.ui_reserved = {
            'title_area_height': 300,
            'button_size': (300, 64),
            'button_spacing': 10
        }

        # Large menu title image (optional) — load original image and preserve aspect ratio on draw
        self.ui_menu_title = try_load_textures([
            'assets/menu_title.png'
        ], keep_original=True)

        # Menu background (optional): try several common names
        self.ui_menu_bg = try_load_textures([
            'assets/menu_bg.png'
        ], keep_original=True)

        # Menu button images for PvP / PvC — try multiple filename variants
        btn_w, btn_h = self.ui_reserved.get('button_size', (300, 64))
        # Load original button images (we'll scale them at draw time while preserving aspect)
        self.ui_button_pvp = try_load_textures([
            'assets/button_pvp.png'
        ], keep_original=True)
        self.ui_button_pvc = try_load_textures([
            'assets/button_pvc.png'
        ], keep_original=True)

        # Optional audio assets
        # short movement sound and shooting sound and Destruction & respawn sounds
        self.sfx_move = load_sound('assets/sfx_move.wav')
        
        if self.sfx_move:
            try:
                self.sfx_move.set_volume(0.05)  # 5% volume 
            except Exception:
                pass

        
        self.sfx_shoot = load_sound('assets/sfx_shoot.wav')
        self.sfx_destroy = load_sound('assets/sfx_destroy.wav')
        self.sfx_respawn = load_sound('assets/sfx_respawn.wav')

        # Background music — try a few common extensions and play if found
        # UI fonts - try to use Joystix Monospace in assets, fallback to system fonts
        ui_font_path = 'assets/joystix-monospace.ttf'
        try:
            self.font_big = pygame.font.Font(ui_font_path, 60)
            self.font_option = pygame.font.Font(ui_font_path, 48)
            self.font_medium = pygame.font.Font(ui_font_path, 36)
            self.font_info = pygame.font.Font(ui_font_path, 32)
            self.font_small = pygame.font.Font(ui_font_path, 28)
            # HUD-specific smaller font so the timer and K/D/S fit nicely in a compact bar
            self.font_hud = pygame.font.Font(ui_font_path, 18)
        except Exception:
            # Fall back to system/default fonts
            self.font_big = pygame.font.SysFont(None, 60)
            self.font_option = pygame.font.SysFont(None, 48)
            self.font_medium = pygame.font.SysFont(None, 36)
            self.font_info = pygame.font.SysFont(None, 32)
            self.font_small = pygame.font.SysFont(None, 28)
            # HUD-specific smaller font (fallback when joystix TTF is missing)
            self.font_hud = pygame.font.SysFont(None, 18)
        self.music_loaded = False
        for mfile in ('assets/music_bg.mp3', 'assets/music_bg.ogg', 'assets/music_bg.wav'):
            try:
                pygame.mixer.music.load(mfile)
                pygame.mixer.music.set_volume(0.5)
                pygame.mixer.music.play(-1)  # loop indefinitely
                self.music_loaded = True
                break
            except Exception:
                # try next
                self.music_loaded = False
    
    def create_grid_map(self):
        """Create grid representation for pathfinding"""
        grid_w = max(1, SCREEN_WIDTH // TILE_WIDTH)
        grid_h = max(1, SCREEN_HEIGHT // TILE_HEIGHT)
        grid = [[False for _ in range(grid_h)] for _ in range(grid_w)]

        # Mark border cells as obstacles for pathfinding using BORDER_THICKNESS
        border_cols = max(1, math.ceil(BORDER_THICKNESS / TILE_WIDTH))
        border_rows = max(1, math.ceil(BORDER_THICKNESS / TILE_HEIGHT))
        for x in range(grid_w):
            for by in range(border_rows):
                if 0 <= by < grid_h:
                    grid[x][by] = True  # top border rows
                if 0 <= grid_h - 1 - by < grid_h:
                    grid[x][grid_h - 1 - by] = True  # bottom border rows
        for y in range(grid_h):
            for bx in range(border_cols):
                if 0 <= bx < grid_w:
                    grid[bx][y] = True  # left border cols
                if 0 <= grid_w - 1 - bx < grid_w:
                    grid[grid_w - 1 - bx][y] = True  # right border cols
        
        # Mark interior obstacle tiles
        for tile in self.tiles:
            x, y = tile.grid_x, tile.grid_y
            if 0 <= x < grid_w and 0 <= y < grid_h and tile.collides():
                grid[x][y] = True
        
        return grid
    
    def start_game(self, mode):
        self.mode = mode
        self.state = "playing"
        self.winner = None
        
        # Generate map (obstacles only, border drawn separately)
        self.tiles, self.map_bg, self.border_image = MapGenerator.generate_map()
        self.grid_map = self.create_grid_map()
        
        # Create tanks
        player1_controls = {
            'up': pygame.K_w,
            'down': pygame.K_s,
            'left': pygame.K_a,
            'right': pygame.K_d,
            'shoot': pygame.K_SPACE
        }
        
        player2_controls = {
            'up': pygame.K_UP,
            'down': pygame.K_DOWN,
            'left': pygame.K_LEFT,
            'right': pygame.K_RIGHT,
            'shoot': pygame.K_RETURN
        }
        
        # Place tanks on safe spawn cells (centers of grid cells away from obstacles)
        grid_w = max(1, SCREEN_WIDTH // TILE_WIDTH)
        grid_h = max(1, SCREEN_HEIGHT // TILE_HEIGHT)

        spawn1 = (2 * TILE_WIDTH + TILE_WIDTH//2, 2 * TILE_HEIGHT + TILE_HEIGHT//2)
        spawn2 = ((grid_w - 3) * TILE_WIDTH + TILE_WIDTH//2, (grid_h - 3) * TILE_HEIGHT + TILE_HEIGHT//2)

        # Load optional tank textures (user can provide files later)
        # Load original tank textures (preserve aspect ratio on draw; do not pre-stretch)
        red_tex = load_texture('assets/tank_red.png', keep_original=True)
        blue_tex = load_texture('assets/tank_blue.png', keep_original=True)

        # Create tanks and set their spawn points so we can respawn them.
        t1 = Tank(spawn1[0], spawn1[1], RED, player1_controls, texture=red_tex, move_sound=self.sfx_move, shoot_sound=self.sfx_shoot, spawn_point=spawn1)
        t2 = Tank(spawn2[0], spawn2[1], BLUE, player2_controls if mode == 'pvp' else {}, texture=blue_tex, move_sound=self.sfx_move, shoot_sound=self.sfx_shoot, spawn_point=spawn2)
        if mode == "pvp":
            self.tanks = [t1, t2]
        else:
            t2.is_ai = True
            self.tanks = [t1, t2]

        # Match timer
        self.match_start = pygame.time.get_ticks()
        self.match_end = self.match_start + MATCH_SECONDS * 1000
        
        # (previous behavior appended tanks here; removed duplicate creation)
    
    def check_collisions(self):
        for tank in self.tanks:
            if not tank.alive:
                continue
            
            for other_tank in self.tanks:
                # allow checking bullets fired by any tank including the same tank (self-inflicted)
                if not other_tank.alive:
                    continue
                
                for bullet in other_tank.bullets[:]:
                    bullet_rect = pygame.Rect(bullet.x - bullet.size/2, bullet.y - bullet.size/2,
                                              bullet.size, bullet.size)
                    if bullet.active and tank.get_rect().colliderect(bullet_rect):
                        # Bullet hit — mark bullet inactive
                        bullet.active = False

                        # play destruction sound if available
                        try:
                            if self.sfx_destroy:
                                self.sfx_destroy.play()
                        except Exception:
                            pass

                        # Track scoring and deaths
                        if bullet.owner == tank:
                            # Self-inflicted
                            tank.suicides += 1
                            tank.deaths += 1
                        else:
                            # Killed by opponent
                            try:
                                bullet.owner.kills += 1
                            except Exception:
                                pass
                            tank.deaths += 1

                        # Immediately respawn the tank (instant respawn mechanic)
                        tank.respawn()

                        # play respawn sound if available
                        try:
                            if self.sfx_respawn:
                                self.sfx_respawn.play()
                        except Exception:
                            pass
    
    def draw_menu(self):
        # Draw menu background if available (cover screen while preserving aspect ratio), otherwise fill white
        if self.ui_menu_bg:
            try:
                bg = self.ui_menu_bg
                bw, bh = bg.get_size()
                # scale to cover the screen so there are no empty borders
                scale = max(SCREEN_WIDTH / bw, SCREEN_HEIGHT / bh)
                new_w = max(1, int(bw * scale))
                new_h = max(1, int(bh * scale))
                scaled_bg = pygame.transform.smoothscale(bg, (new_w, new_h))
                rect = scaled_bg.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
                self.screen.blit(scaled_bg, rect.topleft)
            except Exception:
                self.ui_menu_bg = None
                self.screen.fill(WHITE)
        else:
            self.screen.fill(WHITE)

        # Menu title area at the top — reserved region for an image if present
        title_area_h = self.ui_reserved.get('title_area_height', 350)
        title_y = 10

        # If an image for the menu title exists, draw it; otherwise use text
        if self.ui_menu_title:
            try:
                img = self.ui_menu_title
                # preserve aspect ratio when drawing — fit within box without stretching
                # Based on the attached art, fit the title into a wide box (75% of screen width)
                box_w = int(SCREEN_WIDTH * 0.75)
                box_h = title_area_h - 40
                img_w, img_h = img.get_size()
                if img_w == 0 or img_h == 0:
                    raise Exception('invalid image')
                scale = min(box_w / img_w, box_h / img_h)
                # Prevent scaling to 0
                scale = max(scale, 0.01)
                new_w = max(1, int(img_w * scale))
                new_h = max(1, int(img_h * scale))
                scaled = pygame.transform.smoothscale(img, (new_w, new_h))
                rect = scaled.get_rect(center=(SCREEN_WIDTH // 2, title_y + title_area_h // 2 - 10))
                self.screen.blit(scaled, rect.topleft)
            except Exception:
                self.ui_menu_title = None

        if not self.ui_menu_title:
            # Use the centralized UI font (Joystix if available)
            font_title = self.font_big
            title = font_title.render("METAL BREAKOUT", True, BLACK)
            self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, title_y + 20))

        # Buttons area — center buttons under the title area, use images if present
        # Resize buttons based on screen proportions (preserve aspect ratio)
        button_w = int(SCREEN_WIDTH * 0.18)  # about 18% of width (keeps them visually similar to the art)
        button_h = int(SCREEN_HEIGHT * 0.12)  # taller pixel-art looking buttons for clarity
        button_spacing = self.ui_reserved.get('button_spacing', 24)

        btn_x = SCREEN_WIDTH // 2 - button_w // 2
        btn1_y = title_y + title_area_h - 10
        btn2_y = btn1_y + button_h + button_spacing

        # Draw PvP button (preserve aspect ratio)
        if self.ui_button_pvp:
            try:
                img = self.ui_button_pvp
                iw, ih = img.get_size()
                if iw > 0 and ih > 0:
                    scale = min(button_w / iw, button_h / ih)
                    nw = max(1, int(iw * scale))
                    nh = max(1, int(ih * scale))
                    # ensure pixel-art style preserved where possible — use smoothscale for general support
                    scaled = pygame.transform.smoothscale(img, (nw, nh))
                    draw_x = btn_x + (button_w - nw) // 2
                    draw_y = btn1_y + (button_h - nh) // 2
                    self.screen.blit(scaled, (draw_x, draw_y))
                    # store the button rect so it can be clickable
                    self.menu_button_rects = getattr(self, 'menu_button_rects', {})
                    self.menu_button_rects['pvp'] = pygame.Rect(draw_x, draw_y, nw, nh)
                else:
                    raise Exception('invalid image')
            except Exception:
                self.ui_button_pvp = None

        if not self.ui_button_pvp:
            font_option = self.font_option
            pvp_text = font_option.render("1. Player vs Player", True, RED)
            self.screen.blit(pvp_text, (SCREEN_WIDTH // 2 - pvp_text.get_width() // 2, btn1_y + (button_h - pvp_text.get_height())//2))

        # Draw PvC button (preserve aspect ratio)
        if self.ui_button_pvc:
            try:
                img = self.ui_button_pvc
                iw, ih = img.get_size()
                if iw > 0 and ih > 0:
                    scale = min(button_w / iw, button_h / ih)
                    nw = max(1, int(iw * scale))
                    nh = max(1, int(ih * scale))
                    scaled = pygame.transform.smoothscale(img, (nw, nh))
                    draw_x = btn_x + (button_w - nw) // 2
                    draw_y = btn2_y + (button_h - nh) // 2
                    self.screen.blit(scaled, (draw_x, draw_y))
                    self.menu_button_rects = getattr(self, 'menu_button_rects', {})
                    self.menu_button_rects['pvc'] = pygame.Rect(draw_x, draw_y, nw, nh)
                else:
                    raise Exception('invalid image')
            except Exception:
                self.ui_button_pvc = None

        if not self.ui_button_pvc:
            font_option = self.font_option
            pvc_text = font_option.render("2. Player vs Computer", True, BLUE)
            self.screen.blit(pvc_text, (SCREEN_WIDTH // 2 - pvc_text.get_width() // 2, btn2_y + (button_h - pvc_text.get_height())//2))

        # Instruction / control info below buttons
        info_font = self.font_info
        info1 = info_font.render("Player 1: WASD + SPACE", True, GRAY)
        info2 = info_font.render("Player 2: Arrows + ENTER", True, GRAY)

        info_y = btn2_y + button_h + 30
        # Info line to make controls explicit (keyboard and mouse)
        info_small = self.font_info if hasattr(self, 'font_info') else self.font_small
        self.screen.blit(info1, (SCREEN_WIDTH // 2 - info1.get_width() // 2, info_y))
        self.screen.blit(info2, (SCREEN_WIDTH // 2 - info2.get_width() // 2, info_y + 36))
    
    def draw_game(self):
        self.screen.fill(WHITE)
        
        # Draw map background if available (preserve aspect ratio)
        if hasattr(self, 'map_bg') and self.map_bg:
            try:
                bg = self.map_bg
                bw, bh = bg.get_size()
                if bw > 0 and bh > 0:
                    # scale to cover the screen
                    scale = max(SCREEN_WIDTH / bw, SCREEN_HEIGHT / bh)
                    new_w = max(1, int(bw * scale))
                    new_h = max(1, int(bh * scale))
                    scaled_bg = pygame.transform.smoothscale(bg, (new_w, new_h))
                    rect = scaled_bg.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
                    self.screen.blit(scaled_bg, rect.topleft)
            except Exception:
                pass
        
        # Draw border image inset by BORDER_THICKNESS so the frame appears smaller
        if hasattr(self, 'border_image') and self.border_image:
            try:
                bi = self.border_image
                inner_w = max(1, SCREEN_WIDTH - 2 * BORDER_THICKNESS)
                inner_h = max(1, SCREEN_HEIGHT - 2 * BORDER_THICKNESS)
                border_scaled = pygame.transform.smoothscale(bi, (inner_w, inner_h))
                self.screen.blit(border_scaled, (BORDER_THICKNESS, BORDER_THICKNESS))
            except Exception:
                pass
        
        # Draw tiles (map obstacles only — no border tiles)
        for tile in self.tiles:
            tile.draw(self.screen)
        
        # Draw tanks
        for tank in self.tanks:
            tank.draw(self.screen)
        
        # Compact top HUD bar — small, readable, and centered so timer and K/D/S are always visible
        hud_h = 36
        hud_rect = pygame.Rect(0, 0, SCREEN_WIDTH, hud_h)
        hud_surf = pygame.Surface((SCREEN_WIDTH, hud_h), pygame.SRCALPHA)
        hud_surf.fill((*DARK_GRAY, 220))
        self.screen.blit(hud_surf, (0, 0))

        # left: mode and per-tank K/D/S — limit width so it can't overlap center
        hud_font = getattr(self, 'font_hud', self.font_small)
        mode_text = "PvP" if self.mode == "pvp" else "PvC"
        left_text = f"Mode: {mode_text}"
        # inline K/D/S for each tank, small and compact
        parts = []
        for tank in self.tanks:
            short = 'R' if tank.color == RED else 'B'
            parts.append(f"{short} K:{tank.kills} D:{tank.deaths} S:{tank.suicides}")
        if parts:
            left_text += '  |  ' + '   '.join(parts)

        # reserve left area (percentage of screen) and truncate if needed
        left_area_w = int(SCREEN_WIDTH * 0.45) - 16

        def truncate_to_width(text, font, max_w):
            # quick ellipsize from the end
            if font.size(text)[0] <= max_w:
                return text
            if max_w <= 16:
                return ''
            s = text
            # keep trimming until it fits, then append ellipsis
            while font.size(s + '…')[0] > max_w and len(s) > 0:
                s = s[:-1]
            return s + '…' if s else ''

        safe_left = truncate_to_width(left_text, hud_font, left_area_w)
        left_surf = hud_font.render(safe_left, True, WHITE)
        self.screen.blit(left_surf, (8, (hud_h - left_surf.get_height()) // 2))

        # Determine top scorer using a selection algorithm (no built-in sort)
        top = None
        top_kills = -1
        tie = False
        for t in self.tanks:
            if t.kills > top_kills:
                top_kills = t.kills
                top = t
                tie = False
            elif t.kills == top_kills:
                tie = True

        # center: top scorer small
        center_text = "Top: —"
        if top and not tie and top_kills > 0:
            center_text = ('Top: Red' if top.color == RED else 'Top: Blue') + f" ({top_kills})"
        center_surf = hud_font.render(center_text, True, WHITE)
        cx = SCREEN_WIDTH // 2 - center_surf.get_width() // 2
        self.screen.blit(center_surf, (cx, (hud_h - center_surf.get_height()) // 2))

        # right: timer
        now = pygame.time.get_ticks()
        remaining_ms = max(0, getattr(self, 'match_end', now) - now)
        remaining_s = remaining_ms // 1000
        mins = remaining_s // 60
        secs = remaining_s % 60
        timer_str = f"{mins:01d}:{secs:02d}"
        timer_surf = hud_font.render(timer_str, True, WHITE)
        tx = SCREEN_WIDTH - timer_surf.get_width() - 12
        self.screen.blit(timer_surf, (tx, (hud_h - timer_surf.get_height()) // 2))
    
    def draw_game_over(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(200)
        overlay.fill(WHITE)
        self.screen.blit(overlay, (0, 0))
        
        font_title = self.font_big
        font_text = self.font_medium
        
        # Final top-scorer: use the same selection algorithm to identify the winner
        top = None
        top_kills = -1
        tie = False
        for t in self.tanks:
            if t.kills > top_kills:
                top_kills = t.kills
                top = t
                tie = False
            elif t.kills == top_kills:
                tie = True

        if top is None or top_kills <= 0 or tie:
            title = font_title.render("No clear winner", True, BLACK)
            self.screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 150))
        else:
            winner_color = top.color
            winner_name = "Red Tank" if winner_color == RED else "Blue Tank"
            title = font_title.render(f"{winner_name} Wins ({top_kills} kills)", True, winner_color)
            self.screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 150))
        
        # Draw K/D/S statistics for each tank
        y_offset = 250
        for i, tank in enumerate(self.tanks):
            color_name = "Red" if tank.color == RED else "Blue"
            kds_text = font_text.render(
                f"{color_name} — K:{tank.kills}  D:{tank.deaths}  S:{tank.suicides}",
                True, tank.color
            )
            self.screen.blit(kds_text, (SCREEN_WIDTH//2 - kds_text.get_width()//2, y_offset))
            y_offset += 50
        
        restart_text = font_text.render("Press R to restart or ESC for menu", True, BLACK)
        self.screen.blit(restart_text, (SCREEN_WIDTH//2 - restart_text.get_width()//2, 500))
    
    def run(self):
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                
                if event.type == pygame.KEYDOWN:
                    if self.state == "menu":
                        if event.key == pygame.K_1:
                            self.start_game("pvp")
                        elif event.key == pygame.K_2:
                            self.start_game("pvc")
                    elif self.state == "game_over":
                        if event.key == pygame.K_r:
                            self.start_game(self.mode)
                        elif event.key == pygame.K_ESCAPE:
                            self.state = "menu"
                    elif self.state == "playing":
                        if event.key == pygame.K_ESCAPE:
                            self.state = "menu"
                
                # Menu mouse clicks (buttons)
                if event.type == pygame.MOUSEBUTTONDOWN and self.state == "menu":
                    if event.button == 1:  # left click
                        pos = event.pos
                        rects = getattr(self, 'menu_button_rects', {})
                        if rects.get('pvp') and rects['pvp'].collidepoint(pos):
                            self.start_game("pvp")
                        elif rects.get('pvc') and rects['pvc'].collidepoint(pos):
                            self.start_game("pvc")
                # Handle window resize events
                if event.type == pygame.VIDEORESIZE:
                    try:
                        # Update module-level screen size so all code using SCREEN_WIDTH/HEIGHT adapts
                        global SCREEN_WIDTH, SCREEN_HEIGHT
                        SCREEN_WIDTH, SCREEN_HEIGHT = max(100, event.w), max(100, event.h)
                        # Recreate the display surface with the new size and keep it resizable
                        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
                        # If in a game, update the grid map so pathfinding and HUD adapt to new size
                        if self.state == 'playing':
                            self.grid_map = self.create_grid_map()
                    except Exception:
                        # Ignore resize errors
                        pass
            
            if self.state == "playing":
                keys = pygame.key.get_pressed()
                
                # Update tanks
                for tank in self.tanks:
                    if tank.is_ai:
                        target = [t for t in self.tanks if t != tank and t.alive]
                        target = target[0] if target else None
                        tank.update(keys, self.tiles, target, self.grid_map)
                    else:
                        tank.update(keys, self.tiles)
                
                # Shooting — use continuous key polling so SPACE and ENTER fire reliably
                for tank in self.tanks:
                    if not tank.is_ai and 'shoot' in tank.controls:
                        if keys[tank.controls['shoot']]:
                            tank.shoot()

                
                # Check collisions
                self.check_collisions()
                
                # Check timed match end; respawn tanks instantly if killed
                now = pygame.time.get_ticks()

                # check collisions and respawn in check_collisions

                # End match when time's up
                if now >= getattr(self, 'match_end', 0):
                    self.state = "game_over"
                
                self.draw_game()
            
            elif self.state == "menu":
                self.draw_menu()
            
            elif self.state == "game_over":
                self.draw_game()
                self.draw_game_over()
            
            pygame.display.flip()
            self.clock.tick(FPS)
        
        pygame.quit()

if __name__ == "__main__":
    game = Game()
    game.run()