import pygame
import random
import sys
import math
import array
import os
import json

# 1. गेम इंजन और विंडो सेटिंग्स
pygame.init()
pygame.mixer.init(frequency=22050, size=-16, channels=2) 
WIDTH, HEIGHT = 400, 750  
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("X2 Merge Block - Crown Edition")
clock = pygame.time.Clock()

ROWS, COLS, BLOCK_SIZE, OFFSET_X, OFFSET_Y = 8, 5, 70, 25, 100  
board = [[0 for _ in range(COLS)] for _ in range(ROWS)]
score, current_level, celebration_mode, game_over = 0, 1, False, False
last_dropped_col, last_merge_pos = -1, None
star_alpha, star_alpha_dir = 255, -1
gravity_timer = merge_timer = 0
celebration_start_time = 0

game_over_sequence_started = False
combo_count = 0
combo_text_timer = 0
combo_text_str = ""
high_score = 0

current_box_rect = pygame.Rect(150, 35, 42, 42)
next_box_rect = pygame.Rect(250, 42, 28, 28)
hammer_active = False
hammer_btn_rect = pygame.Rect(110, 680, 45, 45)
close_btn_rect = pygame.Rect(245, 680, 45, 45)

# हाई स्कोर लोड/सेव सिस्टम
def load_high_score():
    global high_score
    try:
        if os.path.exists("highscore.txt"):
            with open("highscore.txt", "r") as f: 
                high_score = int(f.read().strip())
    except: 
        high_score = 0

def save_high_score():
    try:
        with open("highscore.txt", "w") as f: 
            f.write(str(high_score))
    except: 
        pass

# गेम स्टेट ऑटो-सेव सिस्टम
def save_game_state():
    if game_over:
        if os.path.exists("gamestate.txt"): 
            try: os.remove("gamestate.txt")
            except: pass
        return
    try:
        state = {
            "board": board, "score": score, "current_level": current_level,
            "current_block": current_block, "next_block": next_block
        }
        with open("gamestate.txt", "w") as f: 
            json.dump(state, f)
    except: 
        pass

def load_game_state():
    global board, score, current_level, current_block, next_block
    try:
        if os.path.exists("gamestate.txt"):
            with open("gamestate.txt", "r") as f:
                state = json.load(f)
                board = state["board"]
                score = state["score"]
                current_level = state["current_level"]
                current_block = state["current_block"]
                next_block = state["next_block"]
                return True
    except: 
        pass
    return False

# 🌟 बिल्कुल सटीक फिक्स: TypeError को रोकने के लिए एरे का सही इनिशियलाइज़ेशन [0] * n_samples से किया गया
def generate_beep_sound(frequency, duration_ms):
    sample_rate = 22050
    n_samples = int(sample_rate * (duration_ms / 1000.0))
    buf = array.array('h', [0] * n_samples)
    for i in range(n_samples):
        t = float(i) / sample_rate
        buf[i] = int(16384 * math.sin(2.0 * math.pi * frequency * t))
    return pygame.mixer.Sound(buffer=buf)

# सुरक्षित तरीके से साउंड्स लोड करना
try: merge_sound = pygame.mixer.Sound("merge.wav")
except Exception: merge_sound = generate_beep_sound(523.25, 150)

try: drop_sound = pygame.mixer.Sound("drop.wav")
except Exception: drop_sound = generate_beep_sound(392.00, 80)

try: gameover_sound = pygame.mixer.Sound("gameover.wav")
except Exception: gameover_sound = generate_beep_sound(196.00, 500)

particles = []
class Particle:
    def __init__(self, x, y, color, speed_mult=1.0):
        self.x, self.y = x, y
        self.vx = random.uniform(-4, 4) * speed_mult
        self.vy = random.uniform(-6, 2) * speed_mult
        self.color, self.radius, self.alpha, self.gravity = color, random.randint(3, 7), 255, 0.25
    def update(self):
        self.x += self.vx; self.y += self.vy; self.vy += self.gravity; self.alpha -= 5
        if self.alpha < 0: self.alpha = 0
    def draw(self, surf):
        if self.alpha > 0:
            s = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*self.color, self.alpha), (self.radius, self.radius), self.radius)
            surf.blit(s, (int(self.x - self.radius), int(self.y - self.radius)))
def spawn_particles(r, c, color, speed_mult=1.0):
    bx = OFFSET_X + c * BLOCK_SIZE + BLOCK_SIZE // 2
    by = OFFSET_Y + r * BLOCK_SIZE + BLOCK_SIZE // 2
    for _ in range(10): 
        particles.append(Particle(bx, by, color, speed_mult))

def trigger_game_over_blast():
    for r in range(ROWS):
        for c in range(COLS):
            if board[r][c] != 0:
                block_color = get_block_color(board[r][c])
                spawn_particles(r, c, block_color, speed_mult=2.2)
                board[r][c] = 0

def draw_custom_hammer(surf, rect, active):
    pygame.draw.line(surf, (200, 150, 100), (rect.x + 12, rect.y + 33), (rect.x + 28, rect.y + 17), 4)
    head_color = (255, 165, 0) if active else (180, 185, 190)
    pygame.draw.rect(surf, head_color, pygame.Rect(rect.x + 22, rect.y + 10, 14, 10), border_radius=2)
    pygame.draw.rect(surf, (100, 105, 110), pygame.Rect(rect.x + 18, rect.y + 13, 5, 4))

def draw_custom_close(surf, rect):
    pygame.draw.line(surf, (255, 255, 255), (rect.x + 14, rect.y + 14), (rect.x + 31, rect.y + 31), 4)
    pygame.draw.line(surf, (255, 255, 255), (rect.x + 31, rect.y + 14), (rect.x + 14, rect.y + 31), 4)

def draw_block_crown(surf, rect):
    crown_color = (255, 215, 0)
    cx, cy = rect.centerx, rect.y + 8
    points = [(cx - 14, cy + 8), (cx - 14, cy - 2), (cx - 7, cy + 3), (cx, cy - 6), (cx + 7, cy + 3), (cx + 14, cy - 2), (cx + 14, cy + 8)]
    pygame.draw.polygon(surf, crown_color, points)
    pygame.draw.line(surf, (200, 160, 0), (cx - 14, cy + 8), (cx + 14, cy + 8), 2)

def setup_base_blocks():
    global board
    for r in range(ROWS):
        for c in range(COLS): board[r][c] = 0

def generate_next_block():
    if current_level > 1: pool = [2, 4, 8, 16, 32, 64]
    else: pool = [2, 4, 8, 16, 32]
    return random.choice(pool)

setup_base_blocks()
load_high_score()
current_block = generate_next_block()
next_block = generate_next_block()

def get_block_color(val):
    colors = {2: (220, 60, 80), 4: (0, 200, 220), 8: (242, 140, 40), 16: (235, 90, 60), 32: (246, 60, 120), 64: (180, 50, 240), 128: (100, 80, 255), 256: (0, 220, 255), 512: (50, 220, 150), 1024: (90, 70, 150), 2048: (45, 30, 65)}
    return colors.get(val, (30, 30, 30))

font, score_font, ui_font, crown_font, combo_font = pygame.font.Font(None, 28), pygame.font.Font(None, 34), pygame.font.Font(None, 20), pygame.font.Font(None, 24), pygame.font.Font(None, 48)

def draw_embossed(surf, color, rect, radius=8, border=0):
    if border == 0: pygame.draw.rect(surf, (10, 12, 18), pygame.Rect(rect.x, rect.y + 3, rect.width, rect.height), border_radius=radius)
    pygame.draw.rect(surf, color, rect, border, border_radius=radius)
    if border == 0: 
        glow_color = (min(255, color[0] + 40), min(255, color[1] + 40), min(255, color[2] + 40))
        pygame.draw.rect(surf, glow_color, rect, 2, border_radius=radius)

def draw_stars(surf, rect, alpha):
    st = pygame.Surface((12, 12), pygame.SRCALPHA)
    pygame.draw.line(st, (255, 215, 0, alpha), (6, 0), (6, 12), 2)
    pygame.draw.line(st, (255, 215, 0, alpha), (0, 6), (12, 6), 2)
    pygame.draw.circle(st, (255, 255, 255, alpha), (6, 6), 2)
    surf.blit(st, (rect.x + 4, rect.y + 4)); surf.blit(st, (rect.right - 16, rect.y + 4))
    surf.blit(st, (rect.x + 4, rect.bottom - 16)); surf.blit(st, (rect.right - 16, rect.bottom - 16))

def find_connected_blocks(start_r, start_c, target_value, visited):
    queue, group = [(start_r, start_c)], [(start_r, start_c)]
    visited.add((start_r, start_c))
    while queue:
        r, c = queue.pop(0)
        for nr, nc in [(r+1, c), (r-1, c), (r, c+1), (r, c-1)]:
            if 0 <= nr < ROWS and 0 <= nc < COLS and (nr, nc) not in visited and board[nr][nc] == target_value:
                visited.add((nr, nc)); queue.append((nr, nc)); group.append((nr, nc))
    return group

def apply_gravity():
    g = False
    for c in range(COLS):
        for r in range(ROWS-1, 0, -1):
            if board[r][c] == 0 and board[r-1][c] != 0: board[r][c] = board[r-1][c]; board[r-1][c] = 0; g = True
    return g

def apply_merging():
    global score, celebration_mode, current_level, last_merge_pos, celebration_start_time, combo_count, combo_text_str, combo_text_timer, high_score
    visited, merge = set(), False
    for r in range(ROWS-1, -1, -1):
        for c in range(COLS):
            if board[r][c] == 0 or (r, c) in visited: continue
            val = board[r][c]
            group = find_connected_blocks(r, c, val, visited)
            if len(group) > 1:
                dropped_in_group = [g for g in group if g[1] == last_dropped_col]
                if dropped_in_group: target = max(dropped_in_group, key=lambda g: g[0])
                else: target = max(group, key=lambda g: g)
                
                tr, tc = target
                block_color = get_block_color(val)
                for gr, gc in group:
                    if (gr, gc) != (tr, tc):
                        spawn_particles(gr, gc, block_color)
                        board[gr][gc] = 0
                
                combo_count += 1
                base_earned = val * (2 ** (len(group)-1))
                score += base_earned * combo_count
                
                if score > high_score:
                    high_score = score
                    save_high_score()
                
                if combo_count > 1:
                    combo_text_str = f"COMBO X{combo_count}!"
                    combo_text_timer = 45
                
                board[tr][tc] = base_earned
                merge = True
                last_merge_pos = (tr, tc)
                
                if merge_sound: merge_sound.play()
                if board[tr][tc] >= 1024: 
                    celebration_mode = True
                    celebration_start_time = pygame.time.get_ticks()
                break
        if merge: break
    return merge

def drop_block(col):
    global current_block, next_block, game_over, last_dropped_col, last_merge_pos, combo_count, game_over_sequence_started
    if board[0][col] != 0: 
        return
    combo_count = 0
    target_row = ROWS - 1
    while target_row >= 0 and board[target_row][col] != 0: target_row -= 1
    if target_row >= 0:
        board[target_row][col] = current_block
        last_dropped_col = col
        last_merge_pos = (target_row, col)
        if drop_sound: drop_sound.play()
        current_block = next_block
        next_block = generate_next_block()
        
    is_board_full = True
    for r in range(ROWS):
        for c in range(COLS):
            if board[r][c] == 0:
                is_board_full = False
                break
                
    if is_board_full and not game_over_sequence_started:
        game_over_sequence_started = True
        trigger_game_over_blast()
        if gameover_sound: gameover_sound.play()
# 2. मुख्य गेम लूप
while True:
    pygame.event.pump()
    screen.fill((20, 22, 30))
    
    star_alpha += 12 * star_alpha_dir
    if star_alpha >= 255: star_alpha, star_alpha_dir = 255, -1
    if star_alpha <= 40: star_alpha, star_alpha_dir = 40, 1

    # 2 सेकंड बाद लेवल अप संदेश को अपने आप हटा देना
    if celebration_mode:
        current_time = pygame.time.get_ticks()
        if current_time - celebration_start_time >= 2000:
            celebration_mode = False

    # केवल स्कोर संख्या डिस्प्ले
    screen.blit(score_font.render(str(score), True, (255, 255, 255)), (25, 20))
    
    # टॉप राइट कॉर्नर में हाई स्कोर डिस्प्ले
    hs_text = ui_font.render(f"HIGH: {high_score}", True, (255, 215, 0))
    screen.blit(hs_text, (WIDTH - hs_text.get_width() - 25, 28))
    
    # वर्तमान ब्लॉक रेंडर (42x42 साइज)
    draw_embossed(screen, get_block_color(current_block), current_box_rect, radius=6)
    screen.blit(font.render(str(current_block), True, (255, 255, 255)), font.render(str(current_block), True, (255, 255, 255)).get_rect(center=current_box_rect.center))
    
    # अगला आने वाला ब्लॉक (Size में छोटा 28x28)
    screen.blit(ui_font.render("NEXT:", True, (140, 150, 170)), (210, 48))
    draw_embossed(screen, get_block_color(next_block), next_box_rect, radius=4)
    next_font = pygame.font.Font(None, 18)
    screen.blit(next_font.render(str(next_block), True, (255, 255, 255)), next_font.render(str(next_block), True, (255, 255, 255)).get_rect(center=next_box_rect.center))

    mx, my = pygame.mouse.get_pos()
    clicked_col = max(0, min(COLS-1, (mx - OFFSET_X) // BLOCK_SIZE))

    for event in pygame.event.get():
        if event.type == pygame.QUIT: 
            save_game_state()
            pygame.quit(); sys.exit()
        
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if close_btn_rect.collidepoint(event.pos):
                save_game_state()
                pygame.quit()
                sys.exit()
            
            elif celebration_mode:
                celebration_mode = False
                
            # 🌟 बिल्कुल सटीक फिक्स 1: गेम ओवर होने पर माउस क्लिक से फ्रेश गेम रीस्टार्ट करने का सुधरा लॉजिक
            elif game_over:
                score, current_level, celebration_mode, game_over, last_dropped_col, last_merge_pos = 0, 1, False, False, -1, None
                game_over_sequence_started = False
                setup_base_blocks()
                current_block = generate_next_block()
                next_block = generate_next_block()
                particles.clear()
                combo_count = 0
                
            elif not game_over and not game_over_sequence_started:
                if hammer_btn_rect.collidepoint(event.pos): 
                    hammer_active = not hammer_active
                elif hammer_active:
                    gc, gr = (mx - OFFSET_X) // BLOCK_SIZE, (my - OFFSET_Y) // BLOCK_SIZE
                    if 0 <= gr < ROWS and 0 <= gc < COLS and board[gr][gc] != 0: 
                        board[gr][gc] = 0; hammer_active = False; apply_merging()
                else: 
                    drop_block(clicked_col)
                
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r and game_over: 
                score, current_level, celebration_mode, game_over, last_dropped_col, last_merge_pos = 0, 1, False, False, -1, None
                game_over_sequence_started = False
                setup_base_blocks()
                current_block = generate_next_block()
                next_block = generate_next_block()
                particles.clear()
                combo_count = 0
            if event.key == pygame.K_RETURN and celebration_mode: 
                celebration_mode = False

    if not game_over and not celebration_mode and not game_over_sequence_started:
        gravity_timer += 1
        if gravity_timer >= 4: 
            gravity_timer = 0; apply_gravity()
        
        merge_timer += 1
        if merge_timer >= 24: 
            merge_timer = 0
            if apply_merging(): pygame.time.delay(100) 

    # पार्टिकल्स अपडेट और ड्रा
    for p in particles[:]:
        p.update(); p.draw(screen)
        if p.alpha <= 0: particles.remove(p)

    # 🌟 बिल्कुल सटीक फिक्स 2: जब ब्लास्ट सीक्वेंस चालू हो और सारे पार्टिकल्स खत्म हो जाएं, तभी स्क्रीन पर मैसेज ओवरले आए
    if game_over_sequence_started and not game_over:
        if len(particles) == 0:
            game_over = True

    max_val = 0
    for r in range(ROWS):
        for c in range(COLS):
            if board[r][c] > max_val: max_val = board[r][c]

    # ग्रिड और ब्लॉक रेंडरिंग
    for r in range(ROWS):
        for c in range(COLS):
            rect = pygame.Rect(OFFSET_X + c * BLOCK_SIZE + 3, OFFSET_Y + r * BLOCK_SIZE + 3, BLOCK_SIZE - 6, BLOCK_SIZE - 4)
            val = board[r][c]
            if val == 0: 
                pygame.draw.rect(screen, (32, 35, 48), rect, border_radius=6)
            else:
                draw_embossed(screen, get_block_color(val), rect, radius=8)
                text_surf = font.render(str(val), True, (255, 255, 255))
                screen.blit(text_surf, text_surf.get_rect(center=rect.center))
                
                if val == max_val and max_val > 0: draw_stars(screen, rect, star_alpha)
                
                if val >= 1024:
                    draw_block_crown(screen, rect)

    # स्क्रीन पर "COMBO X2 / X3" फ्लोटिंग टेक्स्ट एनीमेशन दिखाना
    if combo_text_timer > 0:
        combo_text_timer -= 1
        c_surf = combo_font.render(combo_text_str, True, (0, 220, 255))
        c_rect = c_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 50))
        shadow_surf = combo_font.render(combo_text_str, True, (10, 12, 18))
        screen.blit(shadow_surf, (c_rect.x + 2, c_rect.y + 2))
        screen.blit(c_surf, c_rect)

    # नीचे के स्पेस में बटन्स ड्रा करना
    draw_embossed(screen, (255, 165, 0) if hammer_active else (50, 55, 70), hammer_btn_rect, radius=10)
    draw_embossed(screen, (220, 60, 80), close_btn_rect, radius=10)

    # मैन्युअल शेप आधारित कस्टम हैमर और क्लोज़ आइकॉन रेंडरिंग
    draw_custom_hammer(screen, hammer_btn_rect, hammer_active)
    draw_custom_close(screen, close_btn_rect)

    # लेवल अप बधाई स्क्रीन ओवरले
    if celebration_mode:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((15, 10, 25, 220))
        screen.blit(overlay, (0, 0))
        
        cel_rect = pygame.Rect(40, HEIGHT // 2 - 120, 320, 220)
        draw_embossed(screen, (45, 40, 65), cel_rect, radius=15)
        
        lvl_font = pygame.font.Font(None, 44)
        sub_font = pygame.font.Font(None, 24)
        
        txt_lvl = lvl_font.render("LEVEL UP!", True, (255, 215, 0))
        txt_congrat = font.render("Congratulations!", True, (255, 255, 255))
        txt_info = sub_font.render(f"You reached Level {current_level}", True, (50, 220, 150))
        txt_close = sub_font.render("Auto-closing in 2 seconds...", True, (140, 150, 170))
        
        screen.blit(txt_lvl, txt_lvl.get_rect(centerx=WIDTH // 2, centery=HEIGHT // 2 - 70))
        screen.blit(txt_congrat, txt_congrat.get_rect(centerx=WIDTH // 2, centery=HEIGHT // 2 - 25))
        screen.blit(txt_info, txt_info.get_rect(centerx=WIDTH // 2, centery=HEIGHT // 2 + 15))
        screen.blit(txt_close, txt_close.get_rect(centerx=WIDTH // 2, centery=HEIGHT // 2 + 65))

    # गेम ओवर स्क्रीन ओवरले (अब यह ब्लास्ट खत्म होने के बाद ही दिखेगा)
    if game_over:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 12, 18, 200))
        screen.blit(overlay, (0, 0))
        
        go_rect = pygame.Rect(50, HEIGHT // 2 - 100, 300, 180)
        draw_embossed(screen, (35, 38, 50), go_rect, radius=15)
        
        go_font = pygame.font.Font(None, 42)
        go_text = go_font.render("GAME OVER", True, (255, 60, 80))
        screen.blit(go_text, go_text.get_rect(centerx=WIDTH // 2, centery=HEIGHT // 2 - 60))
        
        fs_text = font.render(f"Final Score: {score}", True, (255, 255, 255))
        screen.blit(fs_text, fs_text.get_rect(centerx=WIDTH // 2, centery=HEIGHT // 2 - 15))
        
        restart_text = ui_font.render("Click Anywhere / 'R' to Restart", True, (140, 150, 170))
        screen.blit(restart_text, restart_text.get_rect(centerx=WIDTH // 2, centery=HEIGHT // 2 + 35))

    pygame.display.flip()
    clock.tick(60)
