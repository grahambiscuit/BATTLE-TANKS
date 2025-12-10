Tank Trouble — Tile-based obstacles and textures

What's changed

- Obstacles are now tile-sized objects (GRID_SIZE x GRID_SIZE) represented by the `Tile` class.
- `Tile` objects can optionally have textures (pygame Surfaces).
- `MapGenerator` now produces a tile grid (border + random tiles). It will attempt to load textures if you add them.
- Game code has been updated to use tiles everywhere (collision, LOS, bullet bounces, pathfinding grid).

How to add textures (you provide assets later)

Drop textures into the `assets/` folder with these recommended names:

- `assets/tile_border.png` — texture used for border tiles around the map
- `assets/tile_obstacle.png` — texture used for internal/tile obstacles
- `assets/tile_obstacle.png` — texture used for internal/tile obstacles

Optional tank textures (user-provided):

- `assets/tank_red.png` — sprite used for the red player's tank
- `assets/tank_blue.png` — sprite used for the blue player's tank

Menu / UI images (optional):

- `assets/menu_title.png` — a large centered title image for the main menu (will be drawn preserving aspect ratio)
- `assets/button_pvp.png` — image for the Player vs Player menu button
- `assets/button_pvc.png` — image for the Player vs Computer menu button

UI font (optional):

- `assets/joystix-monospace.ttf` — place the Joystix Monospace TTF here to use it as the game's primary UI font

Sound & music (optional):

- `assets/sfx_move.wav` — short movement/rumble SFX for tank movement
- `assets/sfx_shoot.wav` — shooting sound effect for firing
- `assets/music_bg.mp3` or `assets/music_bg.ogg` — background music file (looped)

Texture tips

- Tile textures should be square and high-quality; the code will scale/smooth them down to `GRID_SIZE x GRID_SIZE`.
- GRID_SIZE is 50 by default (see `main.py`) — if you change that, you may need to prepare accordingly.

If assets are missing, the game will gracefully fall back to simple rectangle coloring.

Happy modding — add your images to `assets/` and re-run the game to see them applied!

Self-inflicted damage

- Bullets can now hurt the tank that fired them (self-inflicted).
- If a tank kills itself and a single other tank remains alive, that surviving tank will be considered the winner. If multiple are left or none, the game shows "No winner (self-destruct)".
