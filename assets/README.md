Place tile images here for the game to use.

Supported filenames (the game checks these names):

- tile_border.png
- tile_obstacle.png

Tank sprites (optional):

- tank_red.png
- tank_blue.png

- Menu / UI images (optional):
- menu_title.png (recommended size: 600x140 — the game will scale to fit)
- menu_bg.png (optional background image for the main menu; the game will scale it to fill the screen)
- joystix-monospace.ttf (optional — place the Joystix Monospace TTF here to use it as the game's UI font)
- menu_title.png (recommended size: 600x140 — the game will scale to fit)
- button_pvp.png (recommended size: 360x64) — will be scaled to fit while preserving aspect ratio (no stretching)
- button_pvc.png (recommended size: 360x64) — will be scaled to fit while preserving aspect ratio (no stretching)

Sound & Music files (optional):

- sfx_move.wav (short movement sound for tanks)
- sfx_move.wav (short movement sound for tanks) — default volume reduced to 25%; change in `main.py` if needed
- sfx_shoot.wav (shooting sound effect)
- music_bg.mp3 / music_bg.ogg (background music loop)

Destruction & respawn effects (optional):

- sfx_destroy.wav — explosion / destruction SFX when a tank is hit
- sfx_respawn.wav — short respawn sound effect when a tank comes back to life

Images will be scaled to GRID_SIZE x GRID_SIZE (50x50 by default). If these files are missing the game will use default colored rectangles instead.
