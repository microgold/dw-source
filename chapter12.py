"""A Pygame face for the unchanged Chapter 11 game.

Run: python chapter12.py
Preview: python chapter12.py --screenshot preview.png
"""

from __future__ import annotations

import argparse
from collections import deque
from contextlib import redirect_stdout
import importlib.util
import io
import os
from pathlib import Path
import re
import sys

os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame


ROOT = Path(__file__).resolve().parent
WIDTH, HEIGHT = 1440, 950
MAP_RECT = pygame.Rect(34, 70, 1022, 565)
SIDE_RECT = pygame.Rect(1076, 70, 330, 565)
BOTTOM_RECT = pygame.Rect(34, 655, 1372, 250)
OVERLAY_RECT = pygame.Rect(150, 95, 1140, 750)
COLORS = {
    'background': (7, 12, 15), 'panel': (9, 15, 19),
    'border': (199, 208, 200), 'text': (236, 239, 226),
    'muted': (145, 159, 157), 'gold': (234, 183, 71),
    'floor': (236, 196, 65), 'wall': (218, 221, 214),
    'player': (85, 247, 111), 'enemy': (245, 111, 87),
    'magic': (89, 213, 250), 'scroll': (232, 124, 245),
    'ally': (121, 233, 161), 'danger': (250, 105, 104),
}
ANSI = re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]')
STATUS_PREFIXES = (
    'Warrior  CON', 'Rogue  CON', 'Wizard  CON', 'HP:', 'Damage:',
    'HP at next level:', 'Mana at next level:', 'Weapon:', 'Spells:',
    'Floor:', 'Backpack:', 'Allies:', 'w/a/s/d:', 'Items here:',
    'You are at the store.', '> Press', '< Press',
)


class WindowClosed(Exception):
    """Leave nested game menus cleanly when the window closes."""


def load_engine():
    # Use an isolated module instance: no edits or global patches to chapter11.
    spec = importlib.util.spec_from_file_location('dungeon_face_engine', ROOT / 'chapter11.py')
    if spec is None or spec.loader is None:
        raise RuntimeError('chapter11.py must be beside chapter12.py')
    engine = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(engine)
    return engine


class DungeonFace(io.TextIOBase):
    """Render engine state and adapt its existing print/get_key menus."""

    def __init__(self, engine, screenshot=False):
        super().__init__()
        self.engine = engine
        pygame.init()
        pygame.display.set_caption('The Deeper Down - Giving Your Dungeon a Face')
        info = pygame.display.Info()
        window_size = (min(WIDTH, max(900, info.current_w - 80)),
                       min(HEIGHT, max(650, info.current_h - 80)))
        flags = pygame.HIDDEN if screenshot else pygame.RESIZABLE
        self.window = pygame.display.set_mode(window_size, flags)
        self.canvas = pygame.Surface((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.fonts = {size: pygame.font.SysFont('consolas,couriernew,dejavusansmono,monospace', size)
                      for size in (16, 18, 20, 22, 24, 26, 30)}
        self.glyphs = {}
        self.text_buffer = ''
        self.harvested_lines = 0
        self.menu_scroll = 0
        self.history = deque(maxlen=60)
        self.player = None
        self.game_map = None
        self.monsters = []
        self.items = []
        self.projectile = None
        self.blast = None
        self.ended = False
        self.dirty = True

    def write(self, text):
        self.text_buffer += ANSI.sub('', str(text))
        self.dirty = True
        return len(text)

    def flush(self):
        self.dirty = True

    def isatty(self):
        return False

    def clear_text(self):
        self.text_buffer = ''
        self.harvested_lines = 0
        self.menu_scroll = 0
        self.projectile = None
        self.blast = None
        self.dirty = True

    def capture_map(self, game_map, player, monsters, items=None, projectile=None, blast=None):
        self.game_map, self.player, self.monsters = game_map, player, monsters
        if items is not None:
            self.items = items
        self.projectile, self.blast = projectile, blast
        self.dirty = True

    def is_game_screen(self):
        return 'w/a/s/d: move' in self.text_buffer

    def harvest_messages(self):
        if not self.is_game_screen():
            return
        lines = self.text_buffer.splitlines()
        for line in lines[self.harvested_lines:]:
            if line.strip() and not line.startswith(STATUS_PREFIXES):
                self.history.append(line.strip())
        self.harvested_lines = len(lines)

    def install(self):
        self.engine.get_key = self.read_key
        self.engine.clear_screen = self.clear_text
        self.engine.render_map = self.capture_map
        self.engine.animate_magic_missile = self.animate_missile
        self.engine.show_title_screen = self.title_screen
        original_stats = self.engine.show_character_stats

        def capture_stats(player):
            self.player = player
            original_stats(player)
        self.engine.show_character_stats = capture_stats

    def title_screen(self):
        self.clear_text()
        self.write('THE DEEPER DOWN\n\nA dungeon with a memory.\n\n'
                   'Choose your adventurer. Explore, learn magic, and return upstairs to shop.\n\n'
                   'Move: WASD or arrows\nInventory: i     Cast: c     Shop: b\n'
                   'Pick up: g      Wait: .     Stairs: Enter\n\n'
                   'Menus: number keys, Enter to confirm when prompted, Escape to cancel.\n'
                   'Scroll long panels with the mouse wheel.\n\n'
                   'Press Enter to choose your character.\n')
        while self.read_key() not in ('\r', '\n'):
            pass

    @staticmethod
    def translate_key(event):
        special = {pygame.K_ESCAPE: '\x1b', pygame.K_RETURN: '\r',
                   pygame.K_KP_ENTER: '\r', pygame.K_UP: 'w',
                   pygame.K_DOWN: 's', pygame.K_LEFT: 'a', pygame.K_RIGHT: 'd'}
        if event.key in special:
            return special[event.key]
        text = getattr(event, 'unicode', '').lower()
        return text if len(text) == 1 else ''

    def process_window_event(self, event):
        if event.type == pygame.QUIT:
            raise WindowClosed()
        if event.type == pygame.VIDEORESIZE:
            self.window = pygame.display.set_mode((max(640, event.w), max(440, event.h)), pygame.RESIZABLE)
            self.dirty = True
        if event.type == pygame.MOUSEWHEEL:
            self.menu_scroll = max(0, self.menu_scroll - event.y * 3)
            self.dirty = True

    def read_key(self):
        self.harvest_messages()
        self.dirty = True
        while True:
            for event in pygame.event.get():
                self.process_window_event(event)
                if event.type == pygame.KEYDOWN:
                    key = self.translate_key(event)
                    if key:
                        return key
            if self.dirty:
                self.present()
            self.clock.tick(60)

    def animate_missile(self, player, target, game_map, monsters, items):
        if not self.engine.ANIMATE_SPELLS:
            return
        old_projectile = self.projectile
        path = self.engine.missile_path((player.x, player.y), (target.x, target.y))
        for point in path[1:]:
            self.capture_map(game_map, player, monsters, items, projectile=point)
            self.draw_scene(show_overlay=False)
            self.show_canvas()
            duration = (self.engine.MISSILE_IMPACT_SECONDS if point == path[-1]
                        else self.engine.MISSILE_FRAME_SECONDS)
            until = pygame.time.get_ticks() + int(duration * 1000)
            while pygame.time.get_ticks() < until:
                for event in pygame.event.get():
                    self.process_window_event(event)
                self.clock.tick(60)
        self.projectile = old_projectile
        self.dirty = True

    def text(self, value, position, size=20, color=None):
        image = self.fonts[size].render(str(value), True, color or COLORS['text'])
        self.canvas.blit(image, position)
        return image.get_width()

    def wrap(self, value, max_width, size=20):
        font = self.fonts[size]
        if not value:
            return ['']
        words = value.split(' ')
        result, line = [], ''
        for word in words:
            candidate = word if not line else line + ' ' + word
            if font.size(candidate)[0] <= max_width:
                line = candidate
            else:
                if line:
                    result.append(line)
                # Also split unusually long tokens such as generated names.
                line = ''
                for char in word:
                    if font.size(line + char)[0] > max_width and line:
                        result.append(line)
                        line = ''
                    line += char
        result.append(line)
        return result

    def panel(self, rect, title=None):
        pygame.draw.rect(self.canvas, COLORS['panel'], rect, border_radius=7)
        pygame.draw.rect(self.canvas, COLORS['border'], rect, width=2, border_radius=7)
        if title:
            self.text(title, (rect.x + 18, rect.y + 12), 24, COLORS['gold'])
            pygame.draw.line(self.canvas, (62, 74, 76),
                             (rect.x + 15, rect.y + 48), (rect.right - 15, rect.y + 48))

    def frame(self):
        self.canvas.fill(COLORS['background'])
        shades = [(85, 53, 19), (227, 168, 56), (255, 221, 131), (141, 95, 30)]
        for index, color in enumerate(shades):
            inset = 10 + index * 3
            pygame.draw.rect(self.canvas, color, (inset, inset, WIDTH - inset * 2, HEIGHT - inset * 2),
                             width=3, border_radius=15 - index * 2)
        self.text('THE DEEPER DOWN', (42, 35), 22, COLORS['gold'])
        self.text('A PYTHON ROGUELIKE', (1120, 39), 16, COLORS['muted'])

    def draw_map(self):
        self.panel(MAP_RECT)
        if self.game_map is None:
            self.text('Your next descent awaits.', (MAP_RECT.x + 270, MAP_RECT.y + 250), 24, COLORS['muted'])
            return
        actor_positions = {(m.x, m.y): m for m in self.monsters if m.alive}
        item_positions = {(item.x, item.y): item for item in self.items}
        cell_width, cell_height = 24, 26
        start_x = MAP_RECT.x + (MAP_RECT.width - len(self.game_map[0]) * cell_width) // 2
        start_y = MAP_RECT.y + 18
        for y, row in enumerate(self.game_map):
            for x, tile in enumerate(row):
                point = x, y
                symbol = tile.symbol
                color = COLORS['wall'] if symbol == '#' else COLORS['floor']
                if symbol in ('>', '<'):
                    color = COLORS['magic']
                elif symbol == '$':
                    color = COLORS['gold']
                if point in item_positions:
                    symbol = item_positions[point].symbol
                    color = COLORS['scroll'] if symbol == '?' else COLORS['magic']
                if point in actor_positions:
                    actor = actor_positions[point]
                    symbol = actor.symbol
                    color = (COLORS['ally'] if actor.friendly else
                             COLORS['scroll'] if actor.undead else COLORS['enemy'])
                if self.player and point == (self.player.x, self.player.y):
                    symbol, color = '@', COLORS['player']
                    if self.player.is_invisible:
                        color = (52, 126, 86)
                if self.projectile == point:
                    symbol, color = '*', COLORS['magic']
                if self.blast is not None and point in self.blast:
                    color = COLORS['danger']
                cache_key = symbol, color
                if cache_key not in self.glyphs:
                    self.glyphs[cache_key] = self.fonts[26].render(symbol, True, color)
                glyph = self.glyphs[cache_key]
                self.canvas.blit(glyph, (start_x + x * cell_width + (cell_width - glyph.get_width()) // 2,
                                         start_y + y * cell_height))

    def draw_sidebar(self):
        self.panel(SIDE_RECT, 'Legend')
        entries = [('@', 'You', 'player'), ('g', 'Goblin / rat', 'enemy'),
                   ('s', 'Skeleton', 'scroll'), ('h', 'Friendly ally', 'ally'),
                   ('!', 'Potion / item', 'magic'), ('?', 'Spell scroll', 'scroll'),
                   (')', 'Weapon', 'magic'), ('[', 'Armor / shield', 'magic'),
                   ('<>', 'Stairs (Enter)', 'magic'), ('$', 'Store (b)', 'gold')]
        y = SIDE_RECT.y + 66
        for symbol, label, color in entries:
            self.text(symbol, (SIDE_RECT.x + 22, y), 24, COLORS[color])
            self.text(label, (SIDE_RECT.x + 76, y + 3), 18)
            y += 31
        y += 15
        pygame.draw.line(self.canvas, (62, 74, 76), (SIDE_RECT.x + 16, y), (SIDE_RECT.right - 16, y))
        y += 12
        self.text('Equipped', (SIDE_RECT.x + 20, y), 20, COLORS['gold'])
        y += 29
        if self.player:
            for slot, item in self.player.equipment.items():
                name = item.name if item else 'none'
                for line in self.wrap(f'{slot.title()}: {name}', SIDE_RECT.width - 40, 16):
                    self.text(line, (SIDE_RECT.x + 20, y), 16)
                    y += 22

    def draw_status(self):
        self.panel(BOTTOM_RECT)
        p = self.player
        if p:
            self.text(f'{p.class_name}  CON {p.constitution}  STR {p.strength}  DEX {p.dexterity}  INT {p.intelligence}',
                      (55, 671), 24)
            self.text(f'HP: {p.hp}/{p.max_hp}   Mana: {p.mana}/{p.max_mana}   AC: {p.armor_class}   '
                      f'Damage: {max(1, 1 + p.damage_bonus)}-{max(1, p.weapon_damage + p.damage_bonus)}',
                      (55, 708), 22)
            spell_text = 'Spells: ' + (', '.join(p.spells) if p.spells else 'find a scroll to learn')
            for index, line in enumerate(self.wrap(spell_text, 1000, 16)[:2]):
                self.text(line, (55, 743 + index * 19), 16, COLORS['magic'])
            for index, (label, value) in enumerate([
                ('Floor', p.depth), ('Deepest', p.max_depth_reached), ('Level', p.level),
                ('XP', f'{p.xp}/{self.engine.xp_for_next_level(p.level)}'), ('Gold', p.gold),
                ('Pack', f'{len(p.inventory)}/9')]):
                self.text(f'{label}: {value}', (1110, 675 + index * 34), 22,
                          COLORS['gold'] if label == 'Gold' else COLORS['text'])
        log_rect = pygame.Rect(51, 784, 1025, 108)
        pygame.draw.rect(self.canvas, (5, 10, 14), log_rect, border_radius=5)
        pygame.draw.rect(self.canvas, (95, 115, 117), log_rect, 1, border_radius=5)
        log_lines = []
        for message in self.history:
            log_lines.extend(self.wrap(message, log_rect.width - 26, 18))
        if not log_lines:
            log_lines = ['The dungeon waits for your next decision.']
        for index, line in enumerate(log_lines[-4:]):
            color = COLORS['text']
            if any(word in line.lower() for word in ('missile', 'mana', 'learn', 'spell')):
                color = COLORS['magic']
            elif any(word in line.lower() for word in ('damage', 'slain', 'dies', 'critical')):
                color = COLORS['danger']
            self.text(line, (log_rect.x + 13, log_rect.y + 8 + index * 24), 18, color)
        self.text('WASD / arrows: move   i: pack   c: cast   b: shop   g: pick up   Enter: stairs   .: wait   q: quit',
                  (43, 909), 16, COLORS['muted'])

    def draw_overlay(self):
        blast_preview = self.blast is not None and not self.ended
        if not blast_preview:
            veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            veil.fill((0, 0, 0, 170))
            self.canvas.blit(veil, (0, 0))
        # Leave the map visible when the player must inspect a blast area.
        rect = SIDE_RECT if blast_preview else OVERLAY_RECT
        title = ('Fireball preview' if blast_preview else
                 'The expedition is over' if self.ended else 'The Deeper Down')
        self.panel(rect, title)
        wrapped = []
        for line in self.text_buffer.splitlines():
            wrapped.extend(self.wrap(line, rect.width - 56, 18))
        visible_lines = (rect.height - 98) // 25
        self.menu_scroll = min(self.menu_scroll, max(0, len(wrapped) - visible_lines))
        for index, line in enumerate(wrapped[self.menu_scroll:self.menu_scroll + visible_lines]):
            color = COLORS['text']
            if line.startswith(('>', 'After your', 'Current character', 'In blast:')):
                color = COLORS['gold']
            if 'FATAL' in line or 'HURTS YOU' in line or 'YOU at' in line:
                color = COLORS['danger']
            self.text(line, (rect.x + 26, rect.y + 65 + index * 25), 18, color)
        if len(wrapped) > visible_lines:
            self.text('Mouse wheel: scroll panel', (rect.x + 26, rect.bottom - 29), 16, COLORS['muted'])
        if self.ended:
            self.text('Enter or Escape: close window', (rect.x + 26, rect.bottom - 29), 16, COLORS['gold'])

    def draw_scene(self, show_overlay=True):
        self.frame()
        self.draw_map()
        self.draw_sidebar()
        self.draw_status()
        if show_overlay and (self.ended or (self.text_buffer.strip() and not self.is_game_screen())):
            self.draw_overlay()

    def show_canvas(self):
        width, height = self.window.get_size()
        scale = min(width / WIDTH, height / HEIGHT)
        size = max(1, int(WIDTH * scale)), max(1, int(HEIGHT * scale))
        surface = pygame.transform.smoothscale(self.canvas, size)
        self.window.fill((0, 0, 0))
        self.window.blit(surface, ((width - size[0]) // 2, (height - size[1]) // 2))
        pygame.display.flip()
        self.dirty = False

    def present(self):
        self.draw_scene()
        self.show_canvas()

    def run(self):
        self.install()
        try:
            with redirect_stdout(self):
                self.engine.main()
                self.harvest_messages()
                if not self.is_game_screen() and self.player and not self.player.alive:
                    # Fatal spells can finish while a confirmation panel is open.
                    lines = self.text_buffer.splitlines()
                    death_index = next((index for index, line in enumerate(lines)
                                        if line.startswith('You died on floor')), None)
                    if death_index is not None:
                        for line in lines[max(0, death_index - 1):]:
                            if line.strip():
                                self.history.append(line.strip())
                if self.game_map is None:
                    return
                self.text_buffer = '\n'.join(list(self.history)[-10:])
                self.ended = True
                while self.read_key() not in ('\r', '\n', '\x1b', 'q'):
                    pass
        except WindowClosed:
            pass
        finally:
            pygame.quit()

    def preview(self):
        state = self.engine.random.getstate()
        try:
            self.engine.random.seed(23)
            floor = self.engine.Floor(40, 20, 2)
        finally:
            self.engine.random.setstate(state)
        p = self.engine.Player(0, 0, 'Wizard')
        p.depth, p.max_depth_reached = 2, 2
        p.x, p.y = floor.entrance
        p.hp, p.xp, p.gold = 11, 10, 6
        occupied = {(item.x, item.y) for item in floor.items}
        occupied.update((m.x, m.y) for m in floor.monsters if m.alive)
        occupied.add((p.x, p.y))
        candidates = [(x, y) for y, row in enumerate(floor.game_map)
                      for x, tile in enumerate(row) if tile.symbol == '.'
                      and (x, y) not in occupied]
        for name, symbol, fraction in [('Goblin', 'g', 3), ('Skeleton', 's', 2)]:
            x, y = candidates[len(candidates) // fraction]
            monster = self.engine.Monster(x, y, name, symbol, 10, 3, 10, (3, 8),
                                         undead=(name == 'Skeleton'))
            floor.monsters.append(monster)
        self.capture_map(floor.game_map, p, floor.monsters, floor.items)
        self.history.extend(['You cast Magic Missile!', 'The goblin takes 4 damage!',
                             'The goblin is defeated!'])
        self.text_buffer = ''
        self.draw_scene()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--screenshot', type=Path, help='Save a demonstration screen and exit.')
    args = parser.parse_args()
    if args.screenshot:
        os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
        os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
    app = DungeonFace(load_engine(), screenshot=bool(args.screenshot))
    if args.screenshot:
        try:
            app.preview()
            args.screenshot.parent.mkdir(parents=True, exist_ok=True)
            pygame.image.save(app.canvas, str(args.screenshot))
        finally:
            pygame.quit()
    else:
        app.run()


if __name__ == '__main__':
    main()
