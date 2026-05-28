import pygame
import random
import time
import sys

# ── Constants ──────────────────────────────────────────────────────────────────
GRID = 4                     # 4×4 = 15-puzzle
TILE  = 120                  # pixel size per tile
GAP   = 6
COLS  = GRID
ROWS  = GRID
W     = COLS * (TILE + GAP) + GAP + 240   # extra panel on right
H     = ROWS * (TILE + GAP) + GAP + 60    # extra bar at bottom
FPS   = 60

# Colours
BG        = (18,  18,  35)
PANEL     = (28,  28,  50)
TILE_COL  = (72, 130, 210)
TILE_HOV  = (100, 165, 255)
EMPTY_COL = (35,  35,  60)
TEXT_COL  = (230, 240, 255)
ACCENT    = (255, 200,  60)
GREEN     = ( 60, 200, 100)
BTN_COL   = (55,  90, 160)
BTN_HOV   = (80, 120, 200)

BOARD_X = GAP
BOARD_Y = GAP
PANEL_X = COLS * (TILE + GAP) + GAP * 2 + 10
PANEL_W = 210

# ── Puzzle logic ───────────────────────────────────────────────────────────────
def goal_state():
    nums = list(range(1, GRID * GRID)) + [0]   # 0 = empty
    return nums

def is_solvable(tiles):
    """Check if a flat list (0 = blank) is solvable for a 4×4 grid."""
    lst = [t for t in tiles if t != 0]
    inv = sum(1 for i in range(len(lst)) for j in range(i+1, len(lst)) if lst[i] > lst[j])
    blank_row_from_bottom = GRID - (tiles.index(0) // GRID)   # 1-indexed from bottom
    if GRID % 2 == 1:
        return inv % 2 == 0
    else:
        return (inv + blank_row_from_bottom) % 2 == 0

def shuffle_tiles():
    tiles = goal_state()
    while True:
        random.shuffle(tiles)
        if is_solvable(tiles):
            return tiles

def blank_pos(tiles):
    i = tiles.index(0)
    return i // GRID, i % GRID    # row, col

def neighbors(tiles):
    r, c = blank_pos(tiles)
    moves = []
    for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
        nr, nc = r+dr, c+dc
        if 0 <= nr < GRID and 0 <= nc < GRID:
            moves.append((nr, nc))
    return moves

def slide(tiles, row, col):
    """Slide tile at (row,col) into blank if adjacent. Returns new list or None."""
    br, bc = blank_pos(tiles)
    if abs(br - row) + abs(bc - col) == 1:
        new = tiles[:]
        bi = br * GRID + bc
        ti = row * GRID + col
        new[bi], new[ti] = new[ti], new[bi]
        return new
    return None

def is_solved(tiles):
    return tiles == goal_state()

# ── Animation helper ───────────────────────────────────────────────────────────
class Animator:
    def __init__(self):
        self.active = False
        self.start_pos = (0, 0)
        self.end_pos   = (0, 0)
        self.tile_val  = 0
        self.t         = 0.0
        self.duration  = 0.12   # seconds

    def start(self, tile_val, start_px, end_px):
        self.active    = True
        self.tile_val  = tile_val
        self.start_pos = start_px
        self.end_pos   = end_px
        self.t         = 0.0

    def update(self, dt):
        if not self.active:
            return
        self.t += dt / self.duration
        if self.t >= 1.0:
            self.t = 1.0
            self.active = False

    def current_pos(self):
        ease = self.t * self.t * (3 - 2 * self.t)   # smooth-step
        x = self.start_pos[0] + (self.end_pos[0] - self.start_pos[0]) * ease
        y = self.start_pos[1] + (self.end_pos[1] - self.start_pos[1]) * ease
        return int(x), int(y)

# ── Pixel helpers ──────────────────────────────────────────────────────────────
def tile_rect(row, col):
    x = BOARD_X + col * (TILE + GAP)
    y = BOARD_Y + row * (TILE + GAP)
    return pygame.Rect(x, y, TILE, TILE)

def px_to_tile(mx, my):
    for r in range(GRID):
        for c in range(GRID):
            if tile_rect(r, c).collidepoint(mx, my):
                return r, c
    return None, None

# ── Draw helpers ───────────────────────────────────────────────────────────────
def draw_tile(surf, val, rect, font, hovered=False, moving=False):
    colour = TILE_HOV if hovered else TILE_COL
    if moving:
        colour = ACCENT
    pygame.draw.rect(surf, colour, rect, border_radius=12)
    # subtle shadow
    shadow = pygame.Rect(rect.x+3, rect.y+3, rect.w, rect.h)
    pygame.draw.rect(surf, (10, 10, 25), shadow, border_radius=12)
    pygame.draw.rect(surf, colour, rect, border_radius=12)
    # number
    txt = font.render(str(val), True, TEXT_COL)
    surf.blit(txt, txt.get_rect(center=rect.center))

def draw_button(surf, rect, label, font, hovered):
    col = BTN_HOV if hovered else BTN_COL
    pygame.draw.rect(surf, col, rect, border_radius=10)
    txt = font.render(label, True, TEXT_COL)
    surf.blit(txt, txt.get_rect(center=rect.center))

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("15-Puzzle")
    clock  = pygame.time.Clock()

    font_big  = pygame.font.SysFont("segoeui", 52, bold=True)
    font_med  = pygame.font.SysFont("segoeui", 28, bold=True)
    font_sm   = pygame.font.SysFont("segoeui", 20)
    font_tiny = pygame.font.SysFont("segoeui", 16)

    tiles    = shuffle_tiles()
    moves    = 0
    best     = None
    start_t  = time.time()
    won      = False
    animator = Animator()

    btn_new  = pygame.Rect(PANEL_X, H // 2 - 30, PANEL_W, 50)
    btn_easy = pygame.Rect(PANEL_X, H // 2 + 40, PANEL_W, 40)

    diff_moves = {"Easy": 20, "Normal": None}  # None = full shuffle

    def elapsed():
        return int(time.time() - start_t)

    def new_game(easy=False):
        nonlocal tiles, moves, start_t, won
        if easy:
            # generate solvable board by making N random moves from goal
            t = goal_state()
            for _ in range(30):
                nb = neighbors(t)
                r, c = random.choice(nb)
                t = slide(t, r, c)
            tiles = t
        else:
            tiles = shuffle_tiles()
        moves   = 0
        start_t = time.time()
        won     = False

    while True:
        dt = clock.tick(FPS) / 1000.0
        mx, my = pygame.mouse.get_pos()
        hr, hc = px_to_tile(mx, my)

        # ── Events ──────────────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    new_game()
                if event.key == pygame.K_e:
                    new_game(easy=True)

                if not won and not animator.active:
                    arrow_map = {
                        pygame.K_UP:    ( 1,  0),
                        pygame.K_DOWN:  (-1,  0),
                        pygame.K_LEFT:  ( 0,  1),
                        pygame.K_RIGHT: ( 0, -1),
                    }
                    if event.key in arrow_map:
                        dr, dc = arrow_map[event.key]
                        br, bc = blank_pos(tiles)
                        nr, nc = br + dr, bc + dc
                        if 0 <= nr < GRID and 0 <= nc < GRID:
                            moved = slide(tiles, nr, nc)
                            if moved:
                                val = tiles[nr * GRID + nc]
                                animator.start(val, tile_rect(nr, nc).topleft,
                                               tile_rect(br, bc).topleft)
                                tiles = moved
                                moves += 1

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if btn_new.collidepoint(mx, my):
                    new_game()
                elif btn_easy.collidepoint(mx, my):
                    new_game(easy=True)
                elif not won and not animator.active and hr is not None:
                    br, bc = blank_pos(tiles)
                    moved = slide(tiles, hr, hc)
                    if moved:
                        val = tiles[hr * GRID + hc]
                        animator.start(val, tile_rect(hr, hc).topleft,
                                       tile_rect(br, bc).topleft)
                        tiles = moved
                        moves += 1

        animator.update(dt)

        if not won and is_solved(tiles):
            won = True
            elapsed_sec = elapsed()
            if best is None or elapsed_sec < best:
                best = elapsed_sec

        # ── Draw ─────────────────────────────────────────────────────────────
        screen.fill(BG)

        # Board background
        board_bg = pygame.Rect(BOARD_X - GAP, BOARD_Y - GAP,
                               GRID * (TILE + GAP) + GAP,
                               GRID * (TILE + GAP) + GAP)
        pygame.draw.rect(screen, PANEL, board_bg, border_radius=16)

        # Tiles
        for i, val in enumerate(tiles):
            r, c = i // GRID, i % GRID
            rect = tile_rect(r, c)
            if val == 0:
                pygame.draw.rect(screen, EMPTY_COL, rect, border_radius=12)
                continue
            # if this tile is animating, skip normal draw
            if animator.active and animator.tile_val == val:
                continue
            hovered = (r == hr and c == hc and not won)
            draw_tile(screen, val, rect, font_big, hovered)

        # Animated tile
        if animator.active:
            ax, ay = animator.current_pos()
            arect = pygame.Rect(ax, ay, TILE, TILE)
            draw_tile(screen, animator.tile_val, arect, font_big, moving=True)

        # ── Side panel ───────────────────────────────────────────────────────
        pygame.draw.rect(screen, PANEL,
                         pygame.Rect(PANEL_X - 10, 0, PANEL_W + 20, H),
                         border_radius=14)

        # Title
        title = font_med.render("15-Puzzle", True, ACCENT)
        screen.blit(title, (PANEL_X, 18))

        # Stats
        def stat(label, val, y):
            l = font_sm.render(label, True, (150, 160, 190))
            v = font_med.render(str(val), True, TEXT_COL)
            screen.blit(l, (PANEL_X, y))
            screen.blit(v, (PANEL_X, y + 22))

        stat("Moves", moves, 80)
        stat("Time", f"{elapsed()}s", 150)
        stat("Best", f"{best}s" if best else "—", 220)

        # Buttons
        draw_button(screen, btn_new,  "New Game (R)", font_sm,
                    btn_new.collidepoint(mx, my))
        draw_button(screen, btn_easy, "Easy (E)",     font_sm,
                    btn_easy.collidepoint(mx, my))

        # Hint
        hint_lines = ["Click a tile", "next to the gap", "to slide it.",
                      "", "Arrow keys", "also work!"]
        for k, line in enumerate(hint_lines):
            ht = font_tiny.render(line, True, (120, 130, 160))
            screen.blit(ht, (PANEL_X, H - 170 + k * 18))

        # Win overlay
        if won:
            overlay = pygame.Surface((W, H), pygame.SRCALPHA)
            overlay.fill((10, 10, 30, 180))
            screen.blit(overlay, (0, 0))
            wt = font_big.render("🎉 Solved!", True, GREEN)
            screen.blit(wt, wt.get_rect(center=(board_bg.centerx, board_bg.centery - 30)))
            st = font_med.render(f"{moves} moves · {elapsed()}s", True, ACCENT)
            screen.blit(st, st.get_rect(center=(board_bg.centerx, board_bg.centery + 40)))
            rt = font_sm.render("Press R for a new game", True, TEXT_COL)
            screen.blit(rt, rt.get_rect(center=(board_bg.centerx, board_bg.centery + 90)))

        pygame.display.flip()

if __name__ == "__main__":
    main()