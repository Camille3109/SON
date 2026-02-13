"""
SOUND WARD - Version Graphique
Basé sur l'architecture main.py / send_game_data.py / read_game_data.py
Lancement : python sound_ward.py

Dépendances : pygame  pyserial
  pip install pygame pyserial
"""

import pygame
import threading
import time
import random
import math
import sys

from send_game_data2 import find_arduino_port, BAUD, MODES, select_mode
from read_game_data import parse_frequency
import serial

SOUND_TRIGGER_DIST = 275   # distance en pixels du centre

# ── Fenêtre ───────────────────────────────────────────────────────────────────
W   = 900       # largeur de la fenêtre en pixels
H   = 650       # hauteur de la fenêtre en pixels
FPS = 60        # images par seconde

# ── Tolérance de fréquence ────────────────────────────────────────────────────
FREQ_TOL = 40   # le joueur doit être à ±FREQ_TOL Hz de la cible pour valider

# ── Difficulté : temps de réponse (secondes) ─────────────────────────────────
RESPONSE_TIME_BASE = 5.0    # temps accordé au départ
RESPONSE_TIME_MIN  = 1.5    # plancher (jamais moins que ça)
RESPONSE_TIME_STEP = 0.3    # réduction par palier de difficulté

# ── Difficulté : intervalle entre les spawns (secondes) ──────────────────────
SPAWN_BASE = 4.0    # intervalle de spawn au départ
SPAWN_MIN  = 1.5    # plancher
SPAWN_STEP = 0.25   # réduction par palier de difficulté

# ── Difficulté : palier (points) ─────────────────────────────────────────────
DIFF_STEP = 500     # tous les DIFF_STEP points, réponse + spawn s'accélèrent

# ── Difficulté : vitesse des monstres ────────────────────────────────────────
MONSTER_SPEED_BASE = 2.0   # vitesse de base (pixels/frame)
MONSTER_SPEED_MAX  = 4.5   # vitesse maximale
MONSTER_SPEED_AT   = 2000   # score auquel la vitesse maximale est atteinte

# ── Monstres ──────────────────────────────────────────────────────────────────
# Chaque monstre tire une fréquence aléatoire dans [freq_min, freq_max].
# Cette fréquence est envoyée au Teensy et affichée sur le monstre.
# Le joueur doit reproduire cette fréquence à ±FREQ_TOL Hz.
# pts : points accordés pour tuer ce type de monstre.

def get_monsters_for_mode(mode):
    """Generate monsters array based on selected mode"""
    if mode == 'male':
        # Male mode: 80-200 Hz
        return [
            {
                "name":     "Oni",
                "freq_min": 80,
                "freq_max": 120,
                "color":    (220, 60,  60),
                "emoji":    "👹",
                "pts":      100,
            },
            {
                "name":     "Fantome",
                "freq_min": 121,
                "freq_max": 160,
                "color":    (60,  140, 220),
                "emoji":    "👻",
                "pts":      150,
            },
            {
                "name":     "Spectre",
                "freq_min": 161,
                "freq_max": 200,
                "color":    (180, 60,  220),
                "emoji":    "🔮",
                "pts":      200,
            },
        ]
    else:  # female
        # Female mode: 250-450 Hz
        return [
            {
                "name":     "Oni",
                "freq_min": 250,
                "freq_max": 313,
                "color":    (220, 60,  60),
                "emoji":    "👹",
                "pts":      100,
            },
            {
                "name":     "Fantome",
                "freq_min": 314,
                "freq_max": 381,
                "color":    (60,  140, 220),
                "emoji":    "👻",
                "pts":      150,
            },
            {
                "name":     "Spectre",
                "freq_min": 382,
                "freq_max": 450,
                "color":    (180, 60,  220),
                "emoji":    "🔮",
                "pts":      200,
            },
        ]

# Default to female mode monsters (will be updated after mode selection)
MONSTERS = get_monsters_for_mode('female')

# ── Barre de fréquences (affichage bas d'écran) ───────────────────────────────
# Sera mise à jour selon le mode sélectionné
FREQ_BAR_MIN = 100  # Hz affiché à gauche de la barre (sera ajusté)
FREQ_BAR_MAX = 420  # Hz affiché à droite de la barre (sera ajusté)

# ── Palette de couleurs ───────────────────────────────────────────────────────
BG        = (8,   4,  20)   # fond général
CYAN      = (0,  230, 180)  # couleur joueur / accents positifs
PINK      = (255,  80, 160) # accents négatifs / game over
WHITE     = (240, 240, 255) # texte principal
DARK_GREY = (30,  20,  50)  # fond des barres

# ── Effets visuels ────────────────────────────────────────────────────────────
NB_STARS        = 120   # nombre d'étoiles en fond
PARTICLE_COUNT  = 30    # particules émises à la mort d'un monstre
SCREAM_DURATION = 1.8   # durée de l'écran "PERDU" en secondes
SCREEN_SHAKE    = 40    # intensité du screen-shake au game over (frames)

# ─── Pont série unique (lecture + écriture sur la même connexion) ─────────────
class SerialBridge(threading.Thread):
    """
    Une seule connexion série partagée pour :
      - lire en continu les fréquences (parse_frequency de read_game_data)
      - envoyer la fréquence cible au Teensy (comme send_set de send_game_data)
    Cela évite le PermissionError qui survenait en ouvrant le port deux fois.
    """
    def reset_freq(self):
        with self._lock:
            self._freq = 0.0

    def __init__(self):
        super().__init__(daemon=True)
        self._freq   = 0.0
        self._lock   = threading.Lock()
        self._active = True
        self._ser    = None
        self._try_connect()

    def _try_connect(self):
        PORT, _ = find_arduino_port()
        if PORT:
            try:
                self._ser = serial.Serial(PORT, BAUD, timeout=0.1)
                time.sleep(1.5)
                print(f"[SerialBridge] Connecté sur {PORT}")
            except Exception as e:
                print(f"[SerialBridge] Impossible d'ouvrir le port : {e}")
                self._ser = None
        else:
            print("[SerialBridge] Aucun Arduino/Teensy détecté (simulation)")

    def run(self):
        while self._active:
            if self._ser is None:
                time.sleep(0.5)
                continue
            try:
                line = self._ser.readline().decode("utf-8", errors="ignore")
                freq = parse_frequency(line)
                if freq is not None:
                    with self._lock:
                        self._freq = freq
            except Exception:
                pass

    def get_freq(self):
        with self._lock:
            return self._freq

    def send_freq(self, freq: int):
        """Envoie la fréquence cible au Teensy sur la connexion déjà ouverte."""
        if self._ser is None:
            print(f"[SerialBridge] Pas de connexion — {freq} Hz non envoyé")
            return
        try:
            with self._lock:
                self._ser.write(f"{freq}\n".encode())
            print(f"[SerialBridge] Fréquence envoyée : {freq} Hz")
        except Exception as e:
            print(f"[SerialBridge] Erreur envoi : {e}")

    def stop(self):
        self._active = False
        if self._ser:
            try: self._ser.close()
            except Exception: pass


# ─── Particules ───────────────────────────────────────────────────────────────
class Particle:
    def __init__(self, x, y, color):
        angle = random.uniform(0, 2*math.pi)
        speed = random.uniform(1.5, 5.0)
        self.x, self.y = float(x), float(y)
        self.vx     = math.cos(angle) * speed
        self.vy     = math.sin(angle) * speed
        self.color  = color
        self.life   = 1.0
        self.radius = random.randint(2, 5)

    def update(self):
        self.x  += self.vx
        self.y  += self.vy
        self.vy += 0.12
        self.life -= 0.032

    def draw(self, surf):
        if self.life <= 0:
            return
        a   = max(0, int(self.life * 255))
        tmp = pygame.Surface((self.radius*2, self.radius*2), pygame.SRCALPHA)
        pygame.draw.circle(tmp, (*self.color[:3], a),
                           (self.radius, self.radius), self.radius)
        surf.blit(tmp, (int(self.x - self.radius), int(self.y - self.radius)))


# ─── Monstre ──────────────────────────────────────────────────────────────────
class Monster:
    SIZE = 50   # diamètre du cercle en pixels

    def __init__(self, data, response_time, speed=1.0):
        self.name      = data["name"]
        self.color     = data["color"]
        self.emoji     = data["emoji"]
        self.pts       = data["pts"]
        self.max_timer = response_time
        self.alive     = True
        self.flash     = 0
        self.sound_triggered = False


        # Fréquence tirée aléatoirement dans la plage du type de monstre
        self.freq = random.randint(data["freq_min"], data["freq_max"])

        # Spawn depuis un bord aléatoire
        edge = random.choice(["top", "bottom", "left", "right"])
        if   edge == "top":    self.x, self.y = random.randint(80, W-80), -30
        elif edge == "bottom": self.x, self.y = random.randint(80, W-80), H+30
        elif edge == "left":   self.x, self.y = -30, random.randint(80, H-80)
        else:                  self.x, self.y = W+30, random.randint(80, H-80)

        # Vecteur vers le centre (position du joueur)
        dx   = W/2 - self.x
        dy   = H/2 - self.y
        norm = math.hypot(dx, dy) or 1
        self.vx = dx/norm * MONSTER_SPEED_BASE * speed
        self.vy = dy/norm * MONSTER_SPEED_BASE * speed

    def update(self, dt):
        self.x     += self.vx
        self.y     += self.vy
        if self.flash > 0:
            self.flash -= 1

    def draw(self, surf, font_em, font_xs):
        ix, iy = int(self.x), int(self.y)

        # Halo animé
        pulse = 0.7 + 0.3 * math.sin(time.time() * 4)
        r     = int(self.SIZE // 2 * 1.5 * pulse)
        halo  = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
        pygame.draw.circle(halo, (*self.color, 55), (r, r), r)
        surf.blit(halo, (ix - r, iy - r))

        # Corps
        col = WHITE if self.flash > 0 else self.color
        pygame.draw.circle(surf, col, (ix, iy), self.SIZE // 2)
        pygame.draw.circle(surf, BG,  (ix, iy), self.SIZE // 2 - 3)

        # Emoji
        em = font_em.render(self.emoji, True, col)
        surf.blit(em, em.get_rect(center=(ix, iy - 2)))

        # Nom + fréquence exacte à reproduire
        label = font_xs.render(f"{self.name}  {self.freq} Hz", True, col)
        surf.blit(label, label.get_rect(center=(ix, iy + self.SIZE // 2 + 10)))


        ix, iy = int(self.x), int(self.y)
        if self.sound_triggered:
            if int(time.time() * 6) % 2 == 0:
                warn = font_em.render("⚠", True, (255, 200, 0))
                surf.blit(warn, warn.get_rect(center=(ix, iy - self.SIZE)))



    def reached_player(self):
        return math.hypot(self.x - W/2, self.y - H/2) < 46


# ─── Jeu ──────────────────────────────────────────────────────────────────────
class Game:
    S_GENDER = "gender"
    S_MENU   = "menu"
    S_PLAY   = "playing"
    S_SCREAM = "scream"
    S_DEAD   = "dead"

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption("SOUND WARD")
        self.clock  = pygame.time.Clock()

        # Polices
        self.f_big = pygame.font.SysFont("monospace", 80, bold=True)
        self.f_med = pygame.font.SysFont("monospace", 28, bold=True)
        self.f_sm  = pygame.font.SysFont("monospace", 17)
        self.f_xs  = pygame.font.SysFont("monospace", 13)
        self.f_em  = pygame.font.SysFont("segoeuisymbol", 22)
        
        self.mode = None

        # Pont série unique
        self.serial = SerialBridge()
        self.serial.start()

        # Champ d'étoiles
        self.stars = [(random.randint(0, W), random.randint(0, H),
                       random.uniform(0.3, 1.0)) for _ in range(NB_STARS)]

        # État du jeu
        self.state = self.S_GENDER
        self.score    = 0
        self.hi_score = 0

        self.monster        = None   # un seul monstre actif à la fois
        self.particles      = []
        self.shake          = 0
        self.scream_t       = 0.0
        self.flash_msg      = ""
        self.flash_t        = 0.0
        self._spawn_timer   = 0.0
        self._waiting_spawn = True
        self._freq_already_used = False


    # ── Difficulté (calculée dynamiquement depuis le score) ───────────────────
    @property
    def response_time(self):
        paliers = self.score // DIFF_STEP
        return max(RESPONSE_TIME_MIN, RESPONSE_TIME_BASE - paliers * RESPONSE_TIME_STEP)

    @property
    def spawn_interval(self):
        paliers = self.score // DIFF_STEP
        return max(SPAWN_MIN, SPAWN_BASE - paliers * SPAWN_STEP)

    @property
    def speed_mult(self):
        ratio = min(1.0, self.score / MONSTER_SPEED_AT)
        return 1.0 + ratio * (MONSTER_SPEED_MAX / MONSTER_SPEED_BASE - 1.0)

    # ── Reset ─────────────────────────────────────────────────────────────────
    def reset(self):
        self.score          = 0
        self.monster        = None
        self.particles      = []
        self.shake          = 0
        self._spawn_timer   = 0.0
        self._waiting_spawn = True
        self.state          = self.S_PLAY

    # ── Spawn ─────────────────────────────────────────────────────────────────
    def _spawn(self):
        data         = random.choice(MONSTERS)
        self.monster = Monster(data, self.response_time, self.speed_mult)
        self._waiting_spawn = False
        # Envoi de la fréquence tirée au Teensy via la connexion partagée
        freq = self.monster.freq
        self._freq_already_used = False


    # ── Boucle principale ─────────────────────────────────────────────────────
    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            self._events()
            self._update(dt)
            self._draw()
            pygame.display.flip()

    # ── Événements ────────────────────────────────────────────────────────────
    def _events(self):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self.serial.stop(); pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                if self.state == self.S_PLAY:
                    self.state = self.S_MENU
                elif self.state == self.S_MENU:
                    self.state = self.S_GENDER
            if ev.type == pygame.MOUSEBUTTONDOWN:
                self._click(ev.pos)

    def _click(self, pos):
        mx, my = pos
        if self.state == self.S_GENDER:
            if 330 < mx < 570 and 370 < my < 430:
                self._set_mode('male')
            elif 330 < mx < 570 and 450 < my < 510:
                self._set_mode('female')
        elif self.state == self.S_MENU:
            if 330 < mx < 570 and 430 < my < 490:
                self.reset()
            elif 330 < mx < 570 and 510 < my < 570:
                self.serial.stop(); pygame.quit(); sys.exit()
        elif self.state == self.S_DEAD:
            if 310 < mx < 590 and 420 < my < 480:
                self.reset()
            elif 310 < mx < 590 and 500 < my < 558:
                self.state = self.S_MENU

    def _set_mode(self, mode):
        self.mode = mode

        global MONSTERS, FREQ_BAR_MIN, FREQ_BAR_MAX
        MONSTERS = get_monsters_for_mode(mode)

        if mode == 'male':
            FREQ_BAR_MIN = 60
            FREQ_BAR_MAX = 220
        else:
            FREQ_BAR_MIN = 220
            FREQ_BAR_MAX = 470

        print(f"\nMode sélectionné : {mode}\n")

        self.state = self.S_MENU

    # ── Update ────────────────────────────────────────────────────────────────
    def _update(self, dt):
        if self.state == self.S_PLAY:
            self._update_play(dt)
        elif self.state == self.S_SCREAM:
            self.scream_t += dt
            if self.scream_t >= SCREAM_DURATION:
                self.state = self.S_DEAD

        # Particules actives dans tous les états sauf menu
        if self.state != self.S_MENU:
            for p in self.particles:
                p.update()
            self.particles = [p for p in self.particles if p.life > 0]

        if self.flash_t > 0: self.flash_t -= dt
        if self.shake  > 0: self.shake  -= 1

    def _update_play(self, dt):
        # Attente avant le prochain spawn
        if self._waiting_spawn:
            self._spawn_timer += dt
            if self._spawn_timer >= self.spawn_interval:
                self._spawn_timer = 0.0
                self._spawn()
            return

        m = self.monster
        if m is None:
            return

        m.update(dt)

        # Distance au joueur (centre)
        dist = math.hypot(m.x - W/2, m.y - H/2)

        # Déclenchement du cri à une certaine distance
        if not m.sound_triggered and dist <= SOUND_TRIGGER_DIST:
            threading.Thread(
                target=self.serial.send_freq,
                args=(m.freq,),
                daemon=True
            ).start()
            m.sound_triggered = True


        # Lecture de la fréquence captée par le Teensy
        freq_user = self.serial.get_freq()

        # Condition de succès : même logique que main.py (target ± FREQ_TOL)
        if (
            m.sound_triggered
            and freq_user > 50
            and abs(freq_user - m.freq) <= FREQ_TOL
        ):
            self._success(m)
        elif m.reached_player():
            self._game_over()

    def _success(self, m):
        self.score    += m.pts
        self.hi_score  = max(self.hi_score, self.score)
        for _ in range(PARTICLE_COUNT):
            self.particles.append(Particle(m.x, m.y, m.color))
        self.flash_msg      = f"+{m.pts}"
        self.flash_t        = 1.2
        self.monster        = None
        self._waiting_spawn = True
        self._spawn_timer   = 0.0

        # IMPORTANT : vider la fréquence mémorisée
        self.serial.reset_freq()

    def _game_over(self):
        self.state    = self.S_SCREAM
        self.scream_t = 0.0
        self.shake    = SCREEN_SHAKE

    # ── Dessin général ────────────────────────────────────────────────────────
    def _draw(self):
        ox = random.randint(-self.shake//4, self.shake//4) if self.shake else 0
        oy = random.randint(-self.shake//4, self.shake//4) if self.shake else 0

        surf = pygame.Surface((W, H))
        surf.fill(BG)
        self._draw_stars(surf)
        self._draw_scanlines(surf)

        if   self.state == self.S_GENDER: self._draw_menu_gender(surf)
        elif self.state == self.S_MENU:   self._draw_menu(surf)
        elif self.state == self.S_PLAY:   self._draw_play(surf)
        elif self.state == self.S_SCREAM: self._draw_scream(surf)
        elif self.state == self.S_DEAD:   self._draw_dead(surf)

        self.screen.blit(surf, (ox, oy))

    # ── Fond étoilé ───────────────────────────────────────────────────────────
    def _draw_stars(self, surf):
        t = time.time()
        for sx, sy, bri in self.stars:
            c = int(bri * (0.6 + 0.4*math.sin(t*2 + sx)) * 180)
            pygame.draw.circle(surf, (c, c, min(255, c+30)), (sx, sy), 1)

    def _draw_scanlines(self, surf):
        sl = pygame.Surface((W, H), pygame.SRCALPHA)
        for y in range(0, H, 3):
            pygame.draw.line(sl, (0, 0, 0, 30), (0, y), (W, y))
        surf.blit(sl, (0, 0))

    def _draw_menu_gender(self, surf):
        t  = time.time()
        pc = int(180 + 60*math.sin(t*2))
        t1 = self.f_big.render("SOUND WARD", True, (0, pc, 180))
        
        surf.blit(t1, t1.get_rect(center=(W//2, 160)))

        sub = self.f_xs.render("─── Choisis un mode approprié pour ta voix ───",
                                True, (130, 120, 160))
        surf.blit(sub, sub.get_rect(center=(W//2, 290)))

        self._btn(surf, "  BASSE  ",  W//2, 400, PINK, (330, 570, 370, 430))
        self._btn(surf, " SOPRANO ",  W//2, 480, CYAN, (330, 570, 450, 510))
        
    # ── Écran Menu ────────────────────────────────────────────────────────────
    def _draw_menu(self, surf):
        t  = time.time()
        pc = int(180 + 60*math.sin(t*2))
        t1 = self.f_big.render("SOUND WARD", True, (0, pc, 180))
        surf.blit(t1, t1.get_rect(center=(W//2, 160)))

        sub = self.f_xs.render("─── Reproduis la fréquence pour survivre ───",
                                True, (130, 120, 160))
        surf.blit(sub, sub.get_rect(center=(W//2, 280)))

        # Icônes monstres avec leur plage de fréquences
        for i, m in enumerate(MONSTERS):
            x = 155 + i*295
            p = 0.85 + 0.15*math.sin(t*2 + i)
            pygame.draw.circle(surf, m["color"], (x, 330), int(26*p))
            pygame.draw.circle(surf, BG,         (x, 330), int(22*p))
            em = self.f_em.render(m["emoji"], True, m["color"])
            surf.blit(em, em.get_rect(center=(x, 328)))
            # Affiche la plage au lieu d'une fréquence fixe
            fl = self.f_xs.render(
                f"{m['freq_min']}–{m['freq_max']} Hz", True, m["color"])
            surf.blit(fl, fl.get_rect(center=(x, 360)))

        self._btn(surf, "  JOUER  ",  W//2, 460, CYAN, (330, 570, 430, 490))
        self._btn(surf, " QUITTER ",  W//2, 540, PINK, (330, 570, 510, 570))

        if self.hi_score:
            hi = self.f_xs.render(f"MEILLEUR SCORE : {self.hi_score}",
                                   True, (160, 140, 200))
            surf.blit(hi, hi.get_rect(center=(W//2, 548)))

    def _btn(self, surf, text, cx, cy, color, hover_zone=None):
        mx, my = pygame.mouse.get_pos()
        hover  = False
        if hover_zone:
            x1, x2, y1, y2 = hover_zone
            hover = x1 < mx < x2 and y1 < my < y2
        bw, bh = 240, 52
        rect   = pygame.Rect(cx - bw//2, cy - bh//2, bw, bh)
        alpha  = 60 if hover else 22
        bg     = pygame.Surface((bw, bh), pygame.SRCALPHA)
        bg.fill((*color[:3], alpha))
        surf.blit(bg, rect.topleft)
        pygame.draw.rect(surf, color, rect, 2, border_radius=6)
        lbl = self.f_med.render(text, True, color)
        surf.blit(lbl, lbl.get_rect(center=(cx, cy)))

    # ── Écran de jeu ──────────────────────────────────────────────────────────
    def _draw_play(self, surf):
        t = time.time()

        # Joueur au centre
        r    = int(20 + 2*math.sin(t*3))
        halo = pygame.Surface((80, 80), pygame.SRCALPHA)
        pygame.draw.circle(halo, (*CYAN, 38), (40, 40), 36)
        surf.blit(halo, (W//2 - 40, H//2 - 40))
        pygame.draw.circle(surf, CYAN, (W//2, H//2), r)
        pygame.draw.circle(surf, BG,   (W//2, H//2), r - 4)
        cross = self.f_sm.render("+", True, CYAN)
        surf.blit(cross, cross.get_rect(center=(W//2, H//2)))

        # Monstre actif
        if self.monster:
            self.monster.draw(surf, self.f_em, self.f_xs)

        # Compte à rebours avant le prochain spawn
        if self._waiting_spawn:
            rem  = max(0.0, self.spawn_interval - self._spawn_timer)
            stxt = self.f_xs.render(
                f"prochain monstre dans {rem:.1f}s", True, (100, 90, 130))
            surf.blit(stxt, stxt.get_rect(center=(W//2, H - 36)))

        # Particules
        for p in self.particles:
            p.draw(surf)

        # Flash score
        if self.flash_t > 0 and self.flash_msg:
            alpha = int(min(255, self.flash_t * 260))
            fc    = self.f_big.render(self.flash_msg, True, CYAN)
            tmp   = pygame.Surface(fc.get_size(), pygame.SRCALPHA)
            tmp.blit(fc, (0, 0))
            tmp.set_alpha(alpha)
            surf.blit(tmp, tmp.get_rect(center=(W//2, H//2 - 80)))

        self._draw_hud(surf)
        self._draw_freq_bar(surf)

    def _draw_hud(self, surf):
        surf.blit(self.f_med.render(f"SCORE  {self.score}", True, WHITE), (18, 14))
        surf.blit(self.f_sm.render(f"BEST {self.hi_score}", True, (130, 120, 160)), (18, 50))
        surf.blit(self.f_xs.render(f"SPAWN  {self.spawn_interval:.1f}s",
                                    True, (160, 200, 160)), (W - 162, 14))

        fu     = self.serial.get_freq()
        fc_txt = f"{fu:.0f} Hz" if fu > 50 else "–"
        fc     = self.f_sm.render(fc_txt, True, CYAN if fu > 50 else (80, 80, 110))
        surf.blit(fc, fc.get_rect(center=(W//2, 18)))

    def _draw_freq_bar(self, surf):
        """
        Barre horizontale en bas d'écran montrant les plages de chaque monstre
        et la position en temps réel de la fréquence du joueur.
        """
        bx, by, bw, bh = 80, H - 22, W - 160, 12
        pygame.draw.rect(surf, DARK_GREY, (bx, by, bw, bh), border_radius=4)

        span = FREQ_BAR_MAX - FREQ_BAR_MIN

        for m in MONSTERS:
            lo  = m["freq_min"]
            hi  = m["freq_max"]
            col = m["color"]
            zx  = bx + int((lo - FREQ_BAR_MIN) / span * bw)
            zw  = int((hi - lo) / span * bw)
            s   = pygame.Surface((zw, bh), pygame.SRCALPHA)
            s.fill((*col, 50))
            surf.blit(s, (zx, by))
            pygame.draw.rect(surf, (*col, 110), (zx, by, zw, bh), 1, border_radius=2)
            lbl = self.f_xs.render(f"{lo}", True, col)
            surf.blit(lbl, (zx, by - 14))

        # Curseur de la fréquence du joueur
        fu = self.serial.get_freq()
        if FREQ_BAR_MIN <= fu <= FREQ_BAR_MAX:
            cx = bx + int((fu - FREQ_BAR_MIN) / span * bw)
            pygame.draw.rect(surf, CYAN, (cx - 2, by - 4, 4, bh + 8), border_radius=2)

    # ── Écran Scream ──────────────────────────────────────────────────────────
    def _draw_scream(self, surf):
        r    = random.randint(0, 10)
        surf.fill((r, 0, 0))
        frac = min(1.0, self.scream_t / SCREAM_DURATION)
        col  = (255, int(255*(1 - frac)), int(255*(1 - frac)))
        txt  = self.f_big.render("!!  PERDU  !!", True, col)
        surf.blit(txt, txt.get_rect(center=(W//2 + random.randint(-6, 6),
                                             H//2 + random.randint(-5, 5))))
        if self.monster:
            em = self.f_em.render(self.monster.emoji, True, WHITE)
            surf.blit(em, em.get_rect(center=(W//2, H//2 + 70)))

    # ── Écran Game Over ───────────────────────────────────────────────────────
    def _draw_dead(self, surf):
        for p in self.particles:
            p.draw(surf)

        t     = time.time()
        title = self.f_big.render("GAME  OVER", True, PINK)
        surf.blit(title, title.get_rect(center=(W//2, 200)))

        sc = self.f_med.render(f"Score final :  {self.score}", True, WHITE)
        surf.blit(sc, sc.get_rect(center=(W//2, 295)))

        hi = self.f_med.render(f"Meilleur score :  {self.hi_score}", True, CYAN)
        surf.blit(hi, hi.get_rect(center=(W//2, 345)))

        pc = tuple(int(c * (0.85 + 0.15*math.sin(t*3))) for c in PINK)
        self._btn(surf, " RECOMMENCER ",  W//2, 450, pc,   (310, 590, 420, 480))
        self._btn(surf, "     MENU     ",  W//2, 527, CYAN, (310, 590, 500, 558))


# ─── Lancement ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    Game().run()
