import math
import random
from dataclasses import dataclass
from pathlib import Path

import pygame


@dataclass(frozen=True)
class Config:
    # Main window and match pacing.
    width: int = 1100
    height: int = 650
    fps: int = 60
    match_time: float = 60.0

    # Lane bounds keep the minions in one readable combat line.
    lane_y: int = 340
    lane_left: int = 90
    lane_right: int = 1010

    # Hero attack numbers are tuned for last-hit timing, not full combat.
    hero_speed: float = 260.0
    hero_attack_range: float = 150.0
    hero_attack_damage: int = 34
    hero_attack_cooldown: float = 0.82

    # Minions create the background damage that makes timing matter.
    minion_speed: float = 42.0
    minion_attack_range: float = 54.0
    minion_attack_damage: int = 9
    minion_attack_cooldown: float = 1.05
    minion_hp: int = 95
    wave_interval: float = 7.0
    gold_per_last_hit: int = 20
    minion_image_size: tuple[int, int] = (50, 38)
    tower_image_size: tuple[int, int] = (96, 92)
    blue_tower_x: int = 285
    red_tower_x: int = 815
    tower_y: int = 230
    tower_attack_range: float = 245.0
    tower_attack_damage: int = 46
    tower_attack_cooldown: float = 1.35

    # CPU takes only about 25% of its last-hit chances, so it misses around 75%.
    blue_ai_last_hit_chance: float = 0.25
    blue_ai_reaction_delay: float = 0.22


class Colors:
    bg = (22, 28, 34)
    lane = (64, 74, 66)
    lane_edge = (95, 108, 90)
    river = (36, 76, 92)
    grass = (32, 88, 56)
    wall = (66, 65, 73)
    blue = (72, 144, 232)
    blue_dark = (32, 79, 150)
    red = (226, 84, 74)
    red_dark = (145, 45, 46)
    hero = (236, 205, 96)
    hero_dark = (145, 113, 36)
    white = (238, 240, 232)
    muted = (154, 165, 163)
    black = (8, 10, 12)
    gold = (244, 198, 86)
    warning = (248, 226, 96)
    good = (118, 212, 142)
    bad = (236, 110, 104)
    tower_range = (126, 188, 255, 30)
    blue_range = (92, 166, 255, 38)
    red_range = (255, 110, 120, 38)


def clamp(value, low, high):
    return max(low, min(high, value))


def distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def draw_text(surface, font, text, pos, color=Colors.white, align="topleft"):
    image = font.render(text, True, color)
    rect = image.get_rect()
    setattr(rect, align, pos)
    surface.blit(image, rect)
    return rect


def load_image(path, size):
    image = pygame.image.load(path).convert_alpha()
    return pygame.transform.smoothscale(image, size)


def draw_range_circle(surface, pos, radius, color, width=2):
    # Draw on an alpha layer so ranges stay visible but not distracting.
    layer = pygame.Surface((Config.width, Config.height), pygame.SRCALPHA)
    pygame.draw.circle(layer, color, (int(pos[0]), int(pos[1])), int(radius), width)
    surface.blit(layer, (0, 0))


class FloatingText:
    def __init__(self, text, pos, color):
        self.text = text
        self.x, self.y = pos
        self.color = color
        self.life = 1.0

    def update(self, dt):
        # Small feedback text drifts upward and fades out.
        self.life -= dt
        self.y -= 34 * dt

    def draw(self, surface, font):
        if self.life <= 0:
            return
        alpha = clamp(int(255 * self.life), 0, 255)
        image = font.render(self.text, True, self.color)
        image.set_alpha(alpha)
        rect = image.get_rect(center=(self.x, self.y))
        surface.blit(image, rect)


class AttackMark:
    def __init__(self, start, end, color):
        self.start = start
        self.end = end
        self.color = color
        self.life = 0.12

    def update(self, dt):
        self.life -= dt

    def draw(self, surface):
        if self.life <= 0:
            return
        width = 4 if self.life > 0.06 else 2
        pygame.draw.line(surface, self.color, self.start, self.end, width)


class Minion(pygame.sprite.Sprite):
    def __init__(self, team, x, y, slot):
        super().__init__()
        self.team = team
        self.x = float(x)
        self.y = float(y + slot * 22)
        self.radius = 14
        self.max_hp = Config.minion_hp
        self.hp = self.max_hp
        self.attack_timer = random.uniform(0.0, Config.minion_attack_cooldown)
        self.target = None
        # Tracks who actually made the final hit.
        self.last_hit_by = None

    @property
    def pos(self):
        return self.x, self.y

    @property
    def alive(self):
        return self.hp > 0

    def enemy_team(self):
        return "red" if self.team == "blue" else "blue"

    def color(self):
        return Colors.blue if self.team == "blue" else Colors.red

    def dark_color(self):
        return Colors.blue_dark if self.team == "blue" else Colors.red_dark

    def find_target(self, minions):
        # Minions only care about nearby enemies, like a simple lane AI.
        enemies = [m for m in minions if m.team != self.team and m.alive]
        in_range = [m for m in enemies if distance(self.pos, m.pos) <= Config.minion_attack_range]
        if not in_range:
            self.target = None
            return
        self.target = min(in_range, key=lambda m: distance(self.pos, m.pos))

    def update(self, dt, minions):
        if not self.alive:
            return
        self.find_target(minions)
        self.attack_timer -= dt
        if self.target and self.target.alive:
            if self.attack_timer <= 0:
                self.target.hp -= Config.minion_attack_damage
                self.target.last_hit_by = "minion"
                self.attack_timer = Config.minion_attack_cooldown
            return

        # No target in range, so the wave keeps walking down the lane.
        direction = 1 if self.team == "blue" else -1
        self.x += direction * Config.minion_speed * dt
        self.x = clamp(self.x, Config.lane_left, Config.lane_right)

    def draw(self, surface, assets, predicted_color=None):
        image = assets["left_minion"] if self.team == "blue" else assets["right_minion"]

        if predicted_color:
            pygame.draw.circle(surface, predicted_color, (int(self.x), int(self.y)), 25, 3)

        rect = image.get_rect(center=(int(self.x), int(self.y)))
        surface.blit(image, rect)

        bar_w = 44
        bar_h = 5
        hp_ratio = clamp(self.hp / self.max_hp, 0, 1)
        x = int(self.x - bar_w / 2)
        y = int(self.y - 30)
        hp_color = Colors.blue if self.team == "blue" else Colors.red
        pygame.draw.rect(surface, Colors.black, (x, y, bar_w, bar_h))
        pygame.draw.rect(surface, hp_color, (x, y, int(bar_w * hp_ratio), bar_h))


class Hero:
    def __init__(self, team, name, x, y, keys, color, dark_color, range_color):
        self.team = team
        self.name = name
        self.x = float(x)
        self.y = float(y)
        self.keys = keys
        self.color = color
        self.dark_color = dark_color
        self.range_color = range_color
        self.radius = 19
        self.attack_timer = 0.0
        self.gold = 0
        self.last_hits = 0
        self.missed = 0
        self.shots = 0

    @property
    def pos(self):
        return self.x, self.y

    def key_down(self, action, held_keys):
        # Support both key codes and physical scan codes for safer keyboard input.
        key = self.keys[action]
        char = self.keys.get(f"{action}_char")
        scan = self.keys.get(f"{action}_scan")
        return key in held_keys or char in held_keys or ("scan", scan) in held_keys

    def update(self, dt, held_keys):
        vx = 0
        vy = 0
        if self.key_down("left", held_keys):
            vx -= 1
        if self.key_down("right", held_keys):
            vx += 1
        if self.key_down("up", held_keys):
            vy -= 1
        if self.key_down("down", held_keys):
            vy += 1

        if vx or vy:
            length = math.hypot(vx, vy)
            vx /= length
            vy /= length
            self.x += vx * Config.hero_speed * dt
            self.y += vy * Config.hero_speed * dt

        self.x = clamp(self.x, 70, Config.width - 70)
        self.y = clamp(self.y, 120, Config.height - 70)
        self.attack_timer = max(0.0, self.attack_timer - dt)

    def move_toward(self, target_pos, dt):
        # Used by the CPU hero to drift toward a useful lane position.
        dx = target_pos[0] - self.x
        dy = target_pos[1] - self.y
        length = math.hypot(dx, dy)
        if length < 4:
            return
        self.x += dx / length * Config.hero_speed * dt
        self.y += dy / length * Config.hero_speed * dt
        self.x = clamp(self.x, 70, Config.width - 70)
        self.y = clamp(self.y, 120, Config.height - 70)
        self.attack_timer = max(0.0, self.attack_timer - dt)

    def target_in_range(self, minions):
        # Player/CPU attacks the weakest enemy minion inside the range circle.
        enemies = [m for m in minions if m.team != self.team and m.alive]
        enemies = [m for m in enemies if distance(self.pos, m.pos) <= Config.hero_attack_range]
        if not enemies:
            return None
        return min(enemies, key=lambda m: (m.hp, distance(self.pos, m.pos)))

    def try_attack(self, minions):
        if self.attack_timer > 0:
            return None, "cooldown"
        target = self.target_in_range(minions)
        if not target:
            return None, "range"

        self.shots += 1
        target.hp -= Config.hero_attack_damage
        target.last_hit_by = self.team
        self.attack_timer = Config.hero_attack_cooldown
        return target, "hit"

    def draw(self, surface):
        draw_range_circle(surface, self.pos, Config.hero_attack_range, self.range_color)
        pygame.draw.circle(surface, (64, 55, 31), (int(self.x), int(self.y)), self.radius + 5)
        pygame.draw.circle(surface, self.dark_color, (int(self.x), int(self.y)), self.radius + 2)
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(surface, (255, 242, 145), (int(self.x - 5), int(self.y - 5)), 5)


class Tower:
    def __init__(self, team, x, y):
        self.team = team
        self.x = float(x)
        self.y = float(y)
        self.attack_timer = 0.35
        self.target = None

    @property
    def pos(self):
        return self.x, self.y

    def find_target(self, minions):
        # Towers pressure the lane by picking low-health enemy minions.
        enemies = [m for m in minions if m.team != self.team and m.alive]
        in_range = [m for m in enemies if distance(self.pos, m.pos) <= Config.tower_attack_range]
        self.target = min(in_range, key=lambda m: m.hp) if in_range else None

    def update(self, dt, minions):
        self.attack_timer -= dt
        self.find_target(minions)
        if not self.target or self.attack_timer > 0:
            return None

        self.target.hp -= Config.tower_attack_damage
        self.target.last_hit_by = "tower"
        self.attack_timer = Config.tower_attack_cooldown
        return self.target

    def draw(self, surface, assets):
        draw_range_circle(surface, self.pos, Config.tower_attack_range, Colors.tower_range)
        image = assets["tower"]
        rect = image.get_rect(center=(int(self.x), int(self.y)))
        surface.blit(image, rect)
        pygame.draw.circle(surface, Colors.blue if self.team == "blue" else Colors.red, (int(self.x), int(self.y + 38)), 7)


class LastHitTrainer:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Last Hit Trainer")
        self.screen = pygame.display.set_mode((Config.width, Config.height))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 22)
        self.small_font = pygame.font.SysFont("arial", 16)
        self.big_font = pygame.font.SysFont("arial", 42, bold=True)
        self.assets = self.load_assets()
        self.reset()

    def load_assets(self):
        # Image files live next to this script in fig/.
        root = Path(__file__).resolve().parent / "fig"
        return {
            "left_minion": load_image(root / "left.png", Config.minion_image_size),
            "right_minion": load_image(root / "right.png", Config.minion_image_size),
            "tower": load_image(root / "tower.png", Config.tower_image_size),
        }

    def reset(self):
        self.heroes = [
            Hero(
                "blue",
                "CPU",
                405,
                470,
                {},
                Colors.blue,
                Colors.blue_dark,
                Colors.blue_range,
            ),
            Hero(
                "red",
                "Player",
                695,
                470,
                {
                    "up": pygame.K_UP,
                    "down": pygame.K_DOWN,
                    "left": pygame.K_LEFT,
                    "right": pygame.K_RIGHT,
                    "up_scan": 82,
                    "down_scan": 81,
                    "left_scan": 80,
                    "right_scan": 79,
                    "attack": pygame.K_RETURN,
                    "attack_alt": pygame.K_KP_ENTER,
                },
                Colors.red,
                Colors.red_dark,
                Colors.red_range,
            ),
        ]
        self.towers = [
            Tower("blue", Config.blue_tower_x, Config.tower_y),
            Tower("red", Config.red_tower_x, Config.tower_y),
        ]
        self.minions = []
        self.floaters = []
        self.attack_marks = []
        self.elapsed = 0.0
        self.next_wave = 0.0
        self.wave_count = 0
        self.held_keys = set()
        # Per-minion CPU decision memory; prevents rerolling every frame.
        self.ai_choices = {}
        self.running = True
        self.game_over = False
        self.spawn_wave()

    def spawn_wave(self):
        # Three minions per side keeps the fight readable.
        offsets = [-1, 0, 1]
        for i, slot in enumerate(offsets):
            self.minions.append(Minion("blue", Config.lane_left + 25 - i * 16, Config.lane_y, slot))
            self.minions.append(Minion("red", Config.lane_right - 25 + i * 16, Config.lane_y, slot))
        self.wave_count += 1
        self.next_wave = Config.wave_interval

    def estimated_time_to_die(self, minion):
        # Rough DPS estimate from nearby enemy minions and enemy towers.
        dps = 0.0
        for other in self.minions:
            if other.team == minion.team or not other.alive:
                continue
            if distance(other.pos, minion.pos) <= Config.minion_attack_range + 8:
                dps += Config.minion_attack_damage / Config.minion_attack_cooldown
        for tower in self.towers:
            if tower.team != minion.team and distance(tower.pos, minion.pos) <= Config.tower_attack_range:
                dps += Config.tower_attack_damage / Config.tower_attack_cooldown
        if dps <= 0:
            return math.inf
        return minion.hp / dps

    def predicted_last_hit_targets(self):
        # Yellow outline marks targets that are likely to die soon.
        targets = {}
        for hero in self.heroes:
            for minion in self.minions:
                if minion.team == hero.team or not minion.alive:
                    continue
                if distance(hero.pos, minion.pos) > Config.hero_attack_range:
                    continue
                time_to_die = self.estimated_time_to_die(minion)
                if 0.0 < time_to_die <= 1.15:
                    targets[minion] = Colors.gold
        return targets

    def blue_ai_update(self, dt):
        cpu = self.hero_by_team("blue")
        if not cpu:
            return
        cpu.attack_timer = max(0.0, cpu.attack_timer - dt)

        red_minions = [m for m in self.minions if m.team == "red" and m.alive]
        if not red_minions:
            cpu.move_toward((405, 470), dt)
            return

        candidates = []
        for minion in red_minions:
            time_to_die = self.estimated_time_to_die(minion)
            # The CPU only considers minions that are close to a last-hit window.
            can_last_hit = minion.hp <= Config.hero_attack_damage or time_to_die <= 1.1
            if can_last_hit:
                candidates.append((time_to_die, minion))

        for _, minion in candidates:
            if minion not in self.ai_choices:
                # Roll once per minion: take the chance or intentionally miss it.
                self.ai_choices[minion] = {
                    "take": random.random() < Config.blue_ai_last_hit_chance,
                    "delay": Config.blue_ai_reaction_delay + random.uniform(0.0, 0.28),
                }

        active_candidates = [m for _, m in sorted(candidates, key=lambda item: item[0])]
        target = None
        for minion in active_candidates:
            choice = self.ai_choices.get(minion)
            if not choice or not choice["take"]:
                continue
            # A short delay makes the CPU feel less robotic.
            choice["delay"] -= dt
            target = minion
            if choice["delay"] <= 0:
                break

        if not target:
            # If not going for a last-hit, hover near the nearest useful target.
            target = min(red_minions, key=lambda m: (distance(cpu.pos, m.pos), m.hp))

        stand_pos = (target.x - 80, target.y + 86)
        if distance(cpu.pos, target.pos) > Config.hero_attack_range * 0.8:
            cpu.move_toward(stand_pos, dt)
            return

        choice = self.ai_choices.get(target)
        if choice and choice["take"] and choice["delay"] <= 0:
            attacked, _ = cpu.try_attack(self.minions)
            if attacked:
                self.attack_marks.append(AttackMark(cpu.pos, attacked.pos, cpu.color))

    def remove_dead_minions(self):
        survivors = []
        for minion in self.minions:
            if minion.alive:
                survivors.append(minion)
                continue
            self.ai_choices.pop(minion, None)

            # Only hero final hits pay gold.
            killer = self.hero_by_team(minion.last_hit_by)
            if killer and killer.team != minion.team:
                killer.gold += Config.gold_per_last_hit
                killer.last_hits += 1
                self.floaters.append(FloatingText(f"{killer.name} +{Config.gold_per_last_hit}", minion.pos, Colors.gold))
            else:
                for hero in self.heroes:
                    if hero.team != minion.team:
                        hero.missed += 1
                self.floaters.append(FloatingText("missed", minion.pos, Colors.bad))
        self.minions = survivors

    def hero_by_team(self, team):
        for hero in self.heroes:
            if hero.team == team:
                return hero
        return None

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                # Keep our own held-key set for continuous movement.
                self.held_keys.add(event.key)
                self.held_keys.add(("scan", event.scancode))
                if event.unicode:
                    self.held_keys.add(event.unicode.lower())
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_r:
                    self.reset()
                elif not self.game_over:
                    for hero in self.heroes:
                        # CPU has no keyboard bindings.
                        if not hero.keys:
                            continue
                        if event.key in (hero.keys["attack"], hero.keys.get("attack_alt")):
                            self.attack_with_hero(hero)
            elif event.type == pygame.KEYUP:
                self.held_keys.discard(event.key)
                self.held_keys.discard(("scan", event.scancode))
                key_name = pygame.key.name(event.key).lower()
                if len(key_name) == 1:
                    self.held_keys.discard(key_name)

    def attack_with_hero(self, hero):
        target, result = hero.try_attack(self.minions)
        if target:
            self.attack_marks.append(AttackMark(hero.pos, target.pos, hero.color))
        elif result == "range":
            self.floaters.append(FloatingText("out of range", (hero.x, hero.y - 38), Colors.muted))
        elif result == "cooldown":
            self.floaters.append(FloatingText("cooldown", (hero.x, hero.y - 38), Colors.muted))

    def update(self, dt):
        if self.game_over:
            for floater in self.floaters:
                floater.update(dt)
            self.floaters = [f for f in self.floaters if f.life > 0]
            return

        self.elapsed += dt
        self.next_wave -= dt
        if self.next_wave <= 0:
            self.spawn_wave()

        active_keys = set(self.held_keys)
        pressed = pygame.key.get_pressed()
        for hero in self.heroes:
            if not hero.keys:
                continue
            # get_pressed is a backup for any KEYUP/KEYDOWN event oddities.
            for key in hero.keys.values():
                if isinstance(key, int) and 0 <= key < len(pressed) and pressed[key]:
                    active_keys.add(key)
            hero.update(dt, active_keys)

        self.blue_ai_update(dt)

        # Update combat sources before removing dead minions.
        for minion in self.minions:
            minion.update(dt, self.minions)

        for tower in self.towers:
            tower_target = tower.update(dt, self.minions)
            if tower_target:
                color = Colors.blue if tower.team == "blue" else Colors.red
                self.attack_marks.append(AttackMark(tower.pos, tower_target.pos, color))

        self.remove_dead_minions()

        for floater in self.floaters:
            floater.update(dt)
        for mark in self.attack_marks:
            mark.update(dt)

        self.floaters = [f for f in self.floaters if f.life > 0]
        self.attack_marks = [m for m in self.attack_marks if m.life > 0]

        if self.elapsed >= Config.match_time:
            self.game_over = True

    def draw_map(self):
        self.screen.fill(Colors.bg)
        pygame.draw.rect(self.screen, Colors.river, (0, 0, Config.width, 90))
        pygame.draw.rect(self.screen, Colors.grass, (0, 90, Config.width, 120))
        pygame.draw.rect(self.screen, Colors.wall, (160, 205, 120, 55), border_radius=6)
        pygame.draw.rect(self.screen, Colors.wall, (820, 205, 120, 55), border_radius=6)

        lane_rect = pygame.Rect(50, Config.lane_y - 52, Config.width - 100, 104)
        pygame.draw.rect(self.screen, Colors.lane_edge, lane_rect, border_radius=20)
        pygame.draw.rect(self.screen, Colors.lane, lane_rect.inflate(-16, -16), border_radius=16)
        pygame.draw.line(self.screen, (108, 118, 103), (Config.lane_left, Config.lane_y), (Config.lane_right, Config.lane_y), 2)

        pygame.draw.circle(self.screen, Colors.blue_dark, (Config.lane_left - 35, Config.lane_y), 32)
        pygame.draw.circle(self.screen, Colors.red_dark, (Config.lane_right + 35, Config.lane_y), 32)

    def draw_ui(self):
        remaining = max(0, int(Config.match_time - self.elapsed))
        cpu, player = self.heroes
        cpu_cooldown = cpu.attack_timer / Config.hero_attack_cooldown
        player_cooldown = player.attack_timer / Config.hero_attack_cooldown

        pygame.draw.rect(self.screen, (16, 18, 20), (0, 0, Config.width, 74))
        draw_text(self.screen, self.font, f"CPU Gold: {cpu.gold}", (24, 14), Colors.blue)
        draw_text(self.screen, self.small_font, f"Last hits {cpu.last_hits} | Missed {cpu.missed} | Miss chance 75%", (24, 43), Colors.muted)
        draw_text(self.screen, self.font, f"Player Gold: {player.gold}", (Config.width - 245, 14), Colors.red)
        draw_text(self.screen, self.small_font, f"Last hits {player.last_hits} | Missed {player.missed}", (Config.width - 245, 43), Colors.muted)
        draw_text(self.screen, self.font, f"Time: {remaining}s", (Config.width // 2, 43), Colors.white, "midtop")

        cpu_bar = pygame.Rect(365, 18, 135, 14)
        player_bar = pygame.Rect(600, 18, 135, 14)
        for bar, hero, cooldown, label in [
            (cpu_bar, cpu, cpu_cooldown, "CPU auto"),
            (player_bar, player, player_cooldown, "ENTER attack"),
        ]:
            pygame.draw.rect(self.screen, Colors.black, bar)
            ready_w = int(bar.width * (1.0 - cooldown))
            pygame.draw.rect(self.screen, hero.color, (bar.x, bar.y, ready_w, bar.height))
            pygame.draw.rect(self.screen, Colors.white, bar, 1)
            draw_text(self.screen, self.small_font, label, (bar.centerx, bar.bottom + 5), Colors.muted, "midtop")

        hint = "Blue CPU attacks red minions automatically | Red player: ARROWS + ENTER attacks blue minions | R restart"
        draw_text(self.screen, self.small_font, hint, (Config.width // 2, Config.height - 28), Colors.muted, "midtop")

    def draw_game_over(self):
        overlay = pygame.Surface((Config.width, Config.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        cpu, player = self.heroes
        cpu_accuracy = 0 if cpu.shots == 0 else round(cpu.last_hits / cpu.shots * 100)
        player_accuracy = 0 if player.shots == 0 else round(player.last_hits / player.shots * 100)
        draw_text(self.screen, self.big_font, "Training Finished", (Config.width // 2, 210), Colors.white, "center")
        draw_text(self.screen, self.font, f"CPU Gold: {cpu.gold}    Last hits: {cpu.last_hits}    Accuracy: {cpu_accuracy}%", (Config.width // 2, 285), Colors.blue, "center")
        draw_text(self.screen, self.font, f"Player Gold: {player.gold}    Last hits: {player.last_hits}    Accuracy: {player_accuracy}%", (Config.width // 2, 325), Colors.red, "center")
        draw_text(self.screen, self.font, "Press R to restart or ESC to quit", (Config.width // 2, 380), Colors.muted, "center")

    def draw(self):
        self.draw_map()
        predicted = self.predicted_last_hit_targets()

        for tower in self.towers:
            tower.draw(self.screen, self.assets)

        for mark in self.attack_marks:
            mark.draw(self.screen)

        for minion in sorted(self.minions, key=lambda m: m.y):
            minion.draw(self.screen, self.assets, predicted_color=predicted.get(minion))

        for hero in self.heroes:
            hero.draw(self.screen)

        for floater in self.floaters:
            floater.draw(self.screen, self.small_font)

        self.draw_ui()

        if self.game_over:
            self.draw_game_over()

        pygame.display.flip()

    def run(self):
        while self.running:
            dt = self.clock.tick(Config.fps) / 1000.0
            self.handle_events()
            self.update(dt)
            self.draw()

        pygame.quit()


def main():
    game = LastHitTrainer()
    game.run()


if __name__ == "__main__":
    main()
