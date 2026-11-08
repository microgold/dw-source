#!/usr/bin/env python3
"""Book Two, Chapter 8 - Learn and cast Magic Missile and Sleep."""

import random
import time
from copy import copy
import os
import sys
from colorama import Fore, Style, init

init()

TILE_COLORS = {
    '#': Fore.BLACK,
    '.': Fore.YELLOW,
    '>': Fore.CYAN,
}

ENTITY_COLORS = {
    '@': Style.BRIGHT + Fore.GREEN,
    'r': Style.BRIGHT + Fore.RED,
    'g': Style.BRIGHT + Fore.RED,
    's': Style.BRIGHT + Fore.MAGENTA,
    '!': Style.BRIGHT + Fore.BLUE,
    '/': Style.BRIGHT + Fore.BLUE,
    '*': Style.BRIGHT + Fore.CYAN,
    ')': Fore.CYAN,
    '[': Fore.BLUE,
    'o': Fore.BLUE,
    '?': Style.BRIGHT + Fore.MAGENTA,
}

if os.name == 'nt':
    import msvcrt

    def get_key():
        key = msvcrt.getch()
        if key in (b'\x00', b'\xe0'):
            msvcrt.getch()
            return ''
        return key.decode('utf-8', errors='ignore').lower()
else:
    import tty
    import termios

    def get_key():
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            return sys.stdin.read(1).lower()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


WIDTH = 40
HEIGHT = 20
SCORE_FILE = os.path.join(os.path.dirname(__file__), "high_scores.txt")
INVENTORY_CAPACITY = 9
ANIMATE_SPELLS = True
MISSILE_FRAME_SECONDS = 0.15
MISSILE_IMPACT_SECONDS = 0.35
STAT_POTION_CHANCE = 0.03
STAT_CAP = 18
STAT_NAMES = ('constitution', 'strength', 'dexterity', 'intelligence')


SPELLS = {
    'Magic Missile': {'mana': 2, 'range': 6,
                      'description': 'Automatically hits for 1d6 + 2 damage.'},
    'Sleep': {'mana': 3, 'range': 5,
              'description': 'One living target skips its next three actions.'},
}


CLASS_STATS = {
    'Warrior': {'constitution': 12, 'strength': 13,
                'dexterity': 10, 'intelligence': 9},
    'Rogue': {'constitution': 10, 'strength': 11,
              'dexterity': 13, 'intelligence': 10},
    'Wizard': {'constitution': 10, 'strength': 8,
               'dexterity': 11, 'intelligence': 15},
}


def stat_modifier(score):
    return score - 10


class Tile:
    def __init__(self, symbol, walkable):
        self.symbol = symbol
        self.walkable = walkable


WALL = Tile('#', walkable=False)
FLOOR = Tile('.', walkable=True)
STAIRS_DOWN = Tile('>', walkable=True)


def create_empty_map(width, height):
    return [[WALL for _ in range(width)] for _ in range(height)]


def attacker_name(entity):
    return "You" if isinstance(entity, Player) else entity.name


def defender_name(entity):
    return "you" if isinstance(entity, Player) else entity.name


def apply_damage(attacker, defender, damage, message):
    if not defender.alive:
        return "That fight is already over.", None
    if getattr(defender, 'sleep_turns', 0) > 0:
        defender.sleep_turns = 0
        message += f" {defender.name} wakes from the damage!"
    defender.hp = max(0, defender.hp - damage)
    killed = None
    if defender.hp == 0:
        defender.alive = False
        killed = defender
        message += f" {defender_name(defender)} falls."
        if isinstance(defender, Player):
            defender.killer = attacker.name
    return message, killed


def reward_kill(player, monster, messages):
    if monster is None or monster.alive or monster.rewards_claimed:
        return
    monster.rewards_claimed = True
    gold = random.randint(*monster.gold_range)
    player.gold += gold
    player.xp += monster.xp
    messages.append(f"You find {gold} gold. (Total: {player.gold}) +{monster.xp} XP.")
    check_level_up(player, messages)


def attack(attacker, defender):
    if not attacker.alive or not defender.alive:
        return "That fight is already over.", None
    roll = random.randint(1, 20)
    total = roll + attacker.attack_bonus
    hit = roll == 20 or (roll != 1 and total >= defender.armor_class)
    name = attacker_name(attacker)
    verb = 'hit' if isinstance(attacker, Player) else 'hits'
    roll_text = (
        f"(roll {roll} {attacker.attack_bonus:+d} = {total} "
        f"vs AC {defender.armor_class})"
    )
    if not hit:
        miss_verb = 'miss' if isinstance(attacker, Player) else 'misses'
        return f"{name} {miss_verb} {defender_name(defender)}. {roll_text}", None

    damage = max(
        1, random.randint(1, attacker.weapon_damage) + attacker.damage_bonus
    )
    message = (
        f"{name} {verb} {defender_name(defender)} "
        f"for {damage} damage. {roll_text}"
    )
    return apply_damage(attacker, defender, damage, message)


def heal_effect(player, amount):
    def apply(player):
        if player.hp >= player.max_hp:
            return False, "You are already at full health."
        healed = min(amount, player.max_hp - player.hp)
        player.hp += healed
        return True, f"You feel better. Healed {healed} HP."
    return apply


def mana_effect(amount=6):
    def apply(player):
        if player.mana >= player.max_mana:
            return False, "Your mana is already full."
        restored = min(amount, player.max_mana - player.mana)
        player.mana += restored
        return True, f"You recover {restored} mana."
    return apply


def attack_boost_effect(player, amount):
    def apply(player):
        weapon = player.equipment['weapon']
        if weapon is None:
            return False, "Equip a weapon before using a whetstone."
        weapon.enhancement += amount
        return True, (
            f"You sharpen {weapon.name}. Its maximum damage roll "
            f"increases by {amount}."
        )
    return apply


def stat_boost_effect(stat_name):
    def apply(player):
        increased, message = increase_stat(player, stat_name)
        if not increased:
            return False, message + " The potion is not consumed."
        return True, message + " The increase lasts for this run."
    return apply


def learn_spell_effect(spell_name):
    def apply(player):
        if spell_name in player.spells:
            return False, f"You already know {spell_name}. The scroll is kept."
        player.spells.append(spell_name)
        return True, f"You learn {spell_name}! Press c to cast."
    return apply


def invisibility_effect(turns=10):
    def apply(player):
        if player.invisible_turns >= turns:
            return False, "Your invisibility is already at full duration."
        player.invisible_turns = turns
        return True, f"You fade from sight. ({turns} turns remaining)"
    return apply


def save_score(depth, gold):
    with open(SCORE_FILE, "a") as f:
        f.write(f"{depth},{gold}\n")


def load_high_score():
    if not os.path.exists(SCORE_FILE):
        return 0, 0

    best_depth = 0
    best_gold = 0

    with open(SCORE_FILE) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(',')
            if len(parts) == 2:
                depth, gold = int(parts[0]), int(parts[1])
            else:
                depth, gold = int(parts[0]), 0
            if depth > best_depth:
                best_depth = depth
                best_gold = gold

    return best_depth, best_gold


def render_map(game_map, player, monsters, items=None, projectile=None):
    if items is None:
        items = []
    monster_positions = {(m.x, m.y): m.symbol for m in monsters if m.alive}
    item_positions = {(i.x, i.y): i.symbol for i in items}

    for y, row in enumerate(game_map):
        line = ''
        for x, tile in enumerate(row):
            if x == player.x and y == player.y:
                symbol = '@'
                color = Style.DIM + \
                    Fore.GREEN if player.is_invisible else ENTITY_COLORS.get(
                        '@', Fore.WHITE)
            elif (x, y) == projectile:
                symbol = '*'
                color = Style.BRIGHT + Fore.CYAN
            elif (x, y) in monster_positions:
                symbol = monster_positions[(x, y)]
                color = ENTITY_COLORS.get(symbol, Fore.WHITE)
            elif (x, y) in item_positions:
                symbol = item_positions[(x, y)]
                color = ENTITY_COLORS.get(symbol, Fore.WHITE)
            else:
                symbol = tile.symbol
                color = TILE_COLORS.get(symbol, Fore.WHITE)
            line += color + symbol + Style.RESET_ALL
        print(line)


def carve_room(game_map, x1, y1, x2, y2):
    for y in range(y1, y2):
        for x in range(x1, x2):
            game_map[y][x] = FLOOR


class Room:
    def __init__(self, x, y, width, height):
        self.x1 = x
        self.y1 = y
        self.x2 = x + width
        self.y2 = y + height

    def center(self):
        center_x = (self.x1 + self.x2) // 2
        center_y = (self.y1 + self.y2) // 2
        return center_x, center_y

    def intersects(self, other):
        return (
            self.x1 <= other.x2 and self.x2 >= other.x1 and
            self.y1 <= other.y2 and self.y2 >= other.y1
        )


XP_THRESHOLDS = [0, 50, 120, 220, 350, 520, 750]


def xp_for_next_level(level):
    if level < len(XP_THRESHOLDS):
        return XP_THRESHOLDS[level]
    return XP_THRESHOLDS[-1] + (level - len(XP_THRESHOLDS) + 1) * 300


def increase_stat(player, stat_name):
    """Increase one score, preserving wounds and previously spent mana."""
    if stat_name not in STAT_NAMES:
        return False, "That is not a character stat."
    score = getattr(player, stat_name)
    if score >= STAT_CAP:
        return False, f"{stat_name.title()} is already at the cap of {STAT_CAP}."
    old_max_hp = player.max_hp
    old_max_mana = player.max_mana
    setattr(player, stat_name, score + 1)
    player.hp += player.max_hp - old_max_hp
    player.mana += player.max_mana - old_max_mana
    return True, f"{stat_name.title()} increases from {score} to {score + 1}."


def choose_level_stat(player, messages):
    selected = None
    detail = "Choose a stat to preview its effect."
    while True:
        clear_screen()
        print(f"LEVEL {player.level}: CHOOSE YOUR INCREASE")
        for message in messages[-4:]:
            print(message)
        print()
        print("Current character:")
        show_character_stats(player)
        print()
        for number, stat_name in enumerate(STAT_NAMES, start=1):
            score = getattr(player, stat_name)
            change = 'at cap' if score >= STAT_CAP else f'{score} -> {score + 1}'
            print(f"{number}. {stat_name.title()}: {change}")
        print("1-4: preview  Enter: confirm  Escape: clear selection")
        print("The dungeon waits. Choose one increase to continue.")
        print(detail)
        if selected is not None:
            preview = copy(player)
            increase_stat(preview, selected)
            print()
            print("After your selected increase:")
            show_character_stats(preview)
        key = get_key()
        if key == '\x1b':
            selected = None
            detail = "Selection cleared. Your point has not been spent."
        elif len(key) == 1 and key in '1234':
            stat_name = STAT_NAMES[int(key) - 1]
            if getattr(player, stat_name) >= STAT_CAP:
                selected = None
                detail = f"{stat_name.title()} is at its cap; choose another stat."
            else:
                selected = stat_name
                detail = f"Previewing {stat_name.title()}. Enter confirms."
        elif key in ('\r', '\n') and selected is not None:
            increased, message = increase_stat(player, selected)
            if increased:
                messages.append(message)
                return


def check_level_up(player, messages):
    if not player.alive:
        return
    while player.xp >= xp_for_next_level(player.level):
        hp_gain = player.hp_per_level
        player.level += 1
        player.level_hp_gained += hp_gain
        player.hp = min(player.max_hp, player.hp + hp_gain)
        messages.append(
            f"You reached level {player.level}! "
            f"You gain {hp_gain} maximum and current HP "
            f"(CON {player.constitution}); maximum HP is now {player.max_hp}."
        )
        if (player.class_name == 'Wizard' and player.level == 2
                and 'Sleep' not in player.spells):
            player.spells.append('Sleep')
            messages.append("Your studies bear fruit: you learn Sleep! Press c to cast.")
        if any(getattr(player, name) < STAT_CAP for name in STAT_NAMES):
            choose_level_stat(player, messages)
        else:
            messages.append(
                "All stats are at 18. You gain the level's HP, but no stat point."
            )


class Player:
    def __init__(self, x, y, class_name='Warrior'):
        stats = CLASS_STATS[class_name]
        self.x = x
        self.y = y
        self.class_name = class_name
        self.spells = ['Magic Missile'] if class_name == 'Wizard' else []
        self.constitution = stats['constitution']
        self.strength = stats['strength']
        self.dexterity = stats['dexterity']
        self.intelligence = stats['intelligence']
        self.level = 1
        self.level_hp_gained = 0
        self.equipment = {'weapon': None, 'armor': None, 'shield': None}
        self.hp = self.max_hp
        self.mana = self.max_mana
        self.alive = True
        self.depth = 1
        self.invisible_turns = 0
        self.killer = None
        self.gold = 0
        self.xp = 0
        starter = create_item('Short Sword')
        self.inventory = [starter]
        self.equipment['weapon'] = starter

    @property
    def max_hp(self):
        return 20 + self.level_hp_gained + 2 * stat_modifier(self.constitution)

    @property
    def hp_per_level(self):
        return 5 + stat_modifier(self.constitution) // 2

    @property
    def max_mana(self):
        return 6 + 2 * stat_modifier(self.intelligence)

    @property
    def attack_bonus(self):
        weapon = self.equipment['weapon']
        magic = weapon.magic_bonus if weapon is not None else 0
        return stat_modifier(self.dexterity) + magic

    @property
    def damage_bonus(self):
        weapon = self.equipment['weapon']
        magic = weapon.magic_bonus if weapon is not None else 0
        return stat_modifier(self.strength) + magic

    @property
    def weapon_damage(self):
        weapon = self.equipment['weapon']
        if weapon is None:
            return 1
        return weapon.weapon_damage + weapon.enhancement

    @property
    def armor_bonus(self):
        return sum(
            item.armor_bonus + item.magic_bonus
            for slot, item in self.equipment.items()
            if slot in ('armor', 'shield') and item is not None
        )

    @property
    def armor_class(self):
        return 10 + stat_modifier(self.dexterity) // 2 + self.armor_bonus

    @property
    def is_invisible(self):
        return self.invisible_turns > 0


def show_character_stats(player):
    print(
        f"{player.class_name}  CON {player.constitution}  "
        f"STR {player.strength}  DEX {player.dexterity}  "
        f"INT {player.intelligence}"
    )
    low = max(1, 1 + player.damage_bonus)
    high = max(1, player.weapon_damage + player.damage_bonus)
    print(
        f"HP: {player.hp}/{player.max_hp}  "
        f"Mana: {player.mana}/{player.max_mana}"
    )
    print(
        f"Damage: {low}-{high}  "
        f"To hit: {player.attack_bonus:+d}  AC: {player.armor_class}"
    )
    print(
        f"HP at next level: +{player.hp_per_level} "
        "(before that level\'s stat choice)"
    )
    gear = '  '.join(
        f"{slot.title()}: {item.name if item is not None else 'none'}"
        for slot, item in player.equipment.items()
    )
    print(gear)
    print("Spells: " + (", ".join(player.spells) if player.spells else "none yet"))


def choose_character():
    names = list(CLASS_STATS)
    selected = None
    while True:
        clear_screen()
        print("CHOOSE YOUR ADVENTURER")
        for number, name in enumerate(names, start=1):
            print(f"{number}. {name}")
        print("Choose 1-3 to preview. Enter confirms. Escape quits.")
        if selected is not None:
            print()
            show_character_stats(selected)
            print("All classes can use items and learn spells.")
            print("Wizards start with Magic Missile and learn Sleep at level 2.")
        key = get_key()
        if key == '\x1b':
            return None
        if len(key) == 1 and key in '123':
            selected = Player(0, 0, names[int(key) - 1])
        elif key in ('\r', '\n') and selected is not None:
            return selected


class Monster:
    def __init__(self, x, y, name, symbol, hp, attack, xp, gold_range,
                 attack_bonus=0, armor_class=10, sleep_immune=False):
        self.x = x
        self.y = y
        self.name = name
        self.symbol = symbol
        self.hp = hp
        self.max_hp = hp
        self.weapon_damage = attack
        self.damage_bonus = 0
        self.attack_bonus = attack_bonus
        self.armor_class = armor_class
        self.alive = True
        self.xp = xp
        self.gold_range = gold_range
        self.sleep_turns = 0
        self.sleep_immune = sleep_immune
        self.rewards_claimed = False


class Item:
    def __init__(self, x, y, name, symbol, effect=None, slot=None,
                 weapon_damage=0, armor_bonus=0, magic_bonus=0):
        self.x = x
        self.y = y
        self.base_name = name
        self.symbol = symbol
        self.effect = effect
        self.slot = slot
        self.weapon_damage = weapon_damage
        self.armor_bonus = armor_bonus
        self.enhancement = 0
        self.magic_bonus = magic_bonus

    @property
    def name(self):
        if self.magic_bonus:
            return f"{self.base_name} +{self.magic_bonus}"
        return self.base_name


def create_item(name, x=None, y=None, magic_bonus=0):
    template = next(t for t in ITEM_TYPES if t['name'] == name)
    return Item(
        x, y, name, template['symbol'], template.get('effect'),
        template.get('slot'), template.get('weapon_damage', 0),
        template.get('armor_bonus', 0), magic_bonus,
    )


DUNGEON_ADJECTIVES = [
    "Sunken", "Forgotten", "Cursed", "Ancient", "Blighted",
    "Hollow", "Forsaken", "Rotting", "Silent", "Endless"
]

DUNGEON_NOUNS = [
    "Tomb", "Vaults", "Warrens", "Crypts", "Halls",
    "Passages", "Caverns", "Depths", "Tunnels", "Ruins"
]


def generate_dungeon_name():
    adj = random.choice(DUNGEON_ADJECTIVES)
    noun = random.choice(DUNGEON_NOUNS)
    return f"The {adj} {noun}"


DEATH_MESSAGES = {
    'Giant Rat': [
        "Killed by a giant rat. This is not how you imagined it ending.",
        "A giant rat. You were done in by a giant rat.",
        "The rat wins. The rat always wins.",
    ],
    'Goblin': [
        "A goblin cackles over your body. It sounds genuinely delighted.",
        "The goblin didn't even break a sweat.",
        "Slain by a goblin. You had such potential.",
    ],
    'Skeleton': [
        "The skeleton regards your corpse with empty eyes. You were not its first.",
        "The bones win. The bones always win, in the end.",
        "Killed by something that is already dead. A new low.",
    ],
}

DEFAULT_DEATH_MESSAGES = [
    "You have died.",
    "The dungeon claims another adventurer.",
    "Darkness takes you.",
]


def get_death_message(killer_name):
    options = DEATH_MESSAGES.get(killer_name, DEFAULT_DEATH_MESSAGES)
    return random.choice(options)


MONSTER_TYPES = [
    {'name': 'Giant Rat', 'symbol': 'r', 'hp': 6,
        'attack': 2, 'xp': 5,  'gold': (1, 4), 'attack_bonus': 0, 'armor_class': 10},
    {'name': 'Goblin',    'symbol': 'g', 'hp': 10,
        'attack': 3, 'xp': 10, 'gold': (3, 8), 'attack_bonus': 1, 'armor_class': 11},
    {'name': 'Skeleton',  'symbol': 's', 'hp': 14,
        'attack': 4, 'xp': 15, 'gold': (5, 12), 'attack_bonus': 2, 'armor_class': 12, 'sleep_immune': True},
]

ITEM_TYPES = [
    {'name': 'Health Potion', 'symbol': '!',
     'effect': lambda: heal_effect(None, 8)},
    {'name': 'Mana Potion', 'symbol': '!',
     'effect': lambda: mana_effect(6)},
    {'name': 'Scroll of Magic Missile', 'symbol': '?',
     'effect': lambda: learn_spell_effect('Magic Missile')},
    {'name': 'Scroll of Sleep', 'symbol': '?',
     'effect': lambda: learn_spell_effect('Sleep')},
    {'name': 'Whetstone', 'symbol': '/',
     'effect': lambda: attack_boost_effect(None, 1)},
    {'name': 'Shadow Cloak', 'symbol': '*',
     'effect': lambda: invisibility_effect(10)},
    {'name': 'Short Sword', 'symbol': ')', 'slot': 'weapon', 'weapon_damage': 4},
    {'name': 'Long Sword', 'symbol': ')', 'slot': 'weapon', 'weapon_damage': 6},
    {'name': 'Battle Axe', 'symbol': ')', 'slot': 'weapon', 'weapon_damage': 8},
    {'name': 'Leather Armor', 'symbol': '[', 'slot': 'armor', 'armor_bonus': 1},
    {'name': 'Chain Armor', 'symbol': '[', 'slot': 'armor', 'armor_bonus': 2},
    {'name': 'Iron Shield', 'symbol': 'o', 'slot': 'shield', 'armor_bonus': 1},
    {'name': 'Potion of Constitution', 'symbol': '!', 'rare_stat_potion': True,
     'effect': lambda: stat_boost_effect('constitution')},
    {'name': 'Potion of Strength', 'symbol': '!', 'rare_stat_potion': True,
     'effect': lambda: stat_boost_effect('strength')},
    {'name': 'Potion of Dexterity', 'symbol': '!', 'rare_stat_potion': True,
     'effect': lambda: stat_boost_effect('dexterity')},
    {'name': 'Potion of Intelligence', 'symbol': '!', 'rare_stat_potion': True,
     'effect': lambda: stat_boost_effect('intelligence')},
]


def generate_rooms(game_map, max_rooms, room_min_size, room_max_size, map_width, map_height):
    rooms = []

    for _ in range(max_rooms):
        width = random.randint(room_min_size, room_max_size)
        height = random.randint(room_min_size, room_max_size)
        x = random.randint(1, map_width - width - 1)
        y = random.randint(1, map_height - height - 1)

        new_room = Room(x, y, width, height)

        if any(new_room.intersects(other) for other in rooms):
            continue

        carve_room(game_map, new_room.x1, new_room.y1,
                   new_room.x2, new_room.y2)
        rooms.append(new_room)

    return rooms


def carve_horizontal_corridor(game_map, x1, x2, y):
    for x in range(min(x1, x2), max(x1, x2) + 1):
        game_map[y][x] = FLOOR


def carve_vertical_corridor(game_map, y1, y2, x):
    for y in range(min(y1, y2), max(y1, y2) + 1):
        game_map[y][x] = FLOOR


def connect_rooms(game_map, rooms):
    for i in range(1, len(rooms)):
        prev_x, prev_y = rooms[i - 1].center()
        curr_x, curr_y = rooms[i].center()

        if random.random() < 0.5:
            carve_horizontal_corridor(game_map, prev_x, curr_x, prev_y)
            carve_vertical_corridor(game_map, prev_y, curr_y, curr_x)
        else:
            carve_vertical_corridor(game_map, prev_y, curr_y, prev_x)
            carve_horizontal_corridor(game_map, prev_x, curr_x, curr_y)


def spawn_monsters(rooms, player_start_room, spawn_chance, depth=1):
    monsters = []

    for room in rooms:
        if room is player_start_room:
            continue

        if random.random() < spawn_chance:
            template = random.choice(MONSTER_TYPES)
            x, y = room.center()
            scaled_hp = template['hp'] + (depth - 1) * 2
            scaled_attack = template['attack'] + (depth - 1) // 2
            monster = Monster(x, y, template['name'], template['symbol'],
                              scaled_hp, scaled_attack,
                              template['xp'], template['gold'],
                              template['attack_bonus'], template['armor_class'],
                              template.get('sleep_immune', False))
            monsters.append(monster)

    return monsters


def magic_item_chance(depth):
    """Chance to upgrade a spawned piece of gear, not every floor tile."""
    return min(max(1, depth), 10) / 100


def choose_item_template():
    # Roll for the rare category first, so adding four potion types does not
    # make them four equally common entries in the ordinary loot pool.
    rare = random.random() < STAT_POTION_CHANCE
    pool = [template for template in ITEM_TYPES
            if template.get('rare_stat_potion', False) == rare]
    return random.choice(pool)


def spawn_items(rooms, player_start_room, spawn_chance=0.5, depth=1):
    items = []

    for room in rooms:
        if room is player_start_room:
            continue

        if random.random() < spawn_chance:
            template = choose_item_template()
            x, y = room.center()
            x += random.randint(-1, 1)
            y += random.randint(-1, 1)
            item = create_item(template['name'], x, y)
            if item.slot is not None and random.random() < magic_item_chance(depth):
                item.magic_bonus = 1
            items.append(item)

    return items


def place_stairs(game_map, rooms):
    last_room = rooms[-1]
    x, y = last_room.center()
    game_map[y][x] = STAIRS_DOWN
    return x, y


def generate_floor(width, height, depth):
    game_map = create_empty_map(width, height)
    rooms = generate_rooms(game_map, max_rooms=10, room_min_size=4, room_max_size=8,
                           map_width=width, map_height=height)
    connect_rooms(game_map, rooms)

    monsters = spawn_monsters(rooms, rooms[0], spawn_chance=min(
        0.5 + depth * 0.05, 0.9), depth=depth)
    items = spawn_items(rooms, rooms[0], depth=depth)
    stairs_x, stairs_y = place_stairs(game_map, rooms)

    return game_map, rooms, monsters, items, (stairs_x, stairs_y)


def find_available_player_spawn(game_map, rooms):
    x, y = rooms[0].center()
    return x, y


def monster_take_turn(monster, player, game_map, monsters, messages):
    if not monster.alive or not player.alive:
        return
    if monster.sleep_turns > 0:
        monster.sleep_turns -= 1
        if monster.sleep_turns == 0:
            messages.append(f"{monster.name} wakes up. It can act next turn.")
        return
    if player.is_invisible:
        return

    distance_x = player.x - monster.x
    distance_y = player.y - monster.y
    distance = abs(distance_x) + abs(distance_y)

    if distance == 1:
        message, _ = attack(monster, player)
        messages.append(message)
        return

    if distance > 8:
        return

    dx = (distance_x > 0) - (distance_x < 0)
    dy = (distance_y > 0) - (distance_y < 0)

    if dx != 0 and dy != 0:
        if random.random() < 0.5:
            dx = 0
        else:
            dy = 0

    new_x = monster.x + dx
    new_y = monster.y + dy
    occupied = any(
        other.alive and other is not monster
        and (other.x, other.y) == (new_x, new_y)
        for other in monsters
    )
    if (is_walkable(game_map, new_x, new_y)
            and not occupied
            and (new_x, new_y) != (player.x, player.y)):
        monster.x = new_x
        monster.y = new_y



def is_walkable(game_map, x, y):
    return (
        0 <= y < len(game_map)
        and 0 <= x < len(game_map[y])
        and game_map[y][x].walkable
    )


def pick_up_item(player, items, messages, report_empty=False):
    item = next(
        (item for item in items
         if (item.x, item.y) == (player.x, player.y)),
        None,
    )
    if item is None:
        if report_empty:
            messages.append("There is nothing here to pick up.")
        return False
    if len(player.inventory) >= INVENTORY_CAPACITY:
        messages.append(
            f"Your backpack is full. {item.name} stays on the floor."
        )
        return False
    items.remove(item)
    item.x = None
    item.y = None
    player.inventory.append(item)
    messages.append(f"You pick up {item.name}.")
    return True


ITEM_DESCRIPTIONS = {
    'Scroll of Magic Missile': 'Learn a 2-mana, range-6 damage spell. Kept if known.',
    'Scroll of Sleep': 'Learn a 3-mana, range-5 control spell. Undead are immune.',
    'Health Potion': 'Restores health when used.',
    'Mana Potion': 'Restores up to 6 mana, capped at maximum. Kept if mana is full.',
    'Potion of Constitution': (
        '+1 constitution for this run (cap 18). +2 current and maximum HP; '
        'may improve future level HP. Earlier level gains stay unchanged.'
    ),
    'Potion of Strength': '+1 strength for this run (cap 18): +1 melee damage.',
    'Potion of Dexterity': (
        '+1 dexterity for this run (cap 18): +1 to hit; '
        'AC increases only at each two-point boundary above 10.'
    ),
    'Potion of Intelligence': (
        '+1 intelligence for this run (cap 18). '
        '+2 current and maximum mana, preserving spent mana.'
    ),
    'Whetstone': 'Sharpens your weapon when used.',
    'Iron Shield': 'Equip for +1 AC. Only one shield can be equipped.',
    'Shadow Cloak': 'Grants temporary invisibility when used.',
}


def equip_item(player, index, messages):
    if not 0 <= index < len(player.inventory):
        messages.append("That slot is empty.")
        return False
    item = player.inventory[index]
    if item.slot not in player.equipment:
        messages.append("That item cannot be equipped.")
        return False
    previous = player.equipment[item.slot]
    if previous is item:
        messages.append(f"{item.name} is already equipped.")
        return False
    player.equipment[item.slot] = item
    message = f"You equip {item.name}."
    if previous is not None:
        message += f" {previous.name} stays in your backpack."
    messages.append(message)
    return True


def unequip_item(player, index, messages):
    if not 0 <= index < len(player.inventory):
        messages.append("That slot is empty.")
        return False
    item = player.inventory[index]
    if item.slot not in player.equipment or player.equipment[item.slot] is not item:
        messages.append("That item is not equipped.")
        return False
    player.equipment[item.slot] = None
    messages.append(f"You remove {item.name}. It stays in your backpack.")
    return True


def describe_item(player, item):
    if item.slot == 'weapon':
        maximum = item.weapon_damage + item.enhancement
        damage_bonus = stat_modifier(player.strength) + item.magic_bonus
        low = max(1, 1 + damage_bonus)
        high = max(1, maximum + damage_bonus)
        accuracy = stat_modifier(player.dexterity) + item.magic_bonus
        old_low = max(1, 1 + player.damage_bonus)
        old_high = max(1, player.weapon_damage + player.damage_bonus)
        return (
            f"{item.name}: weapon roll 1-{maximum}; magic "
            f"+{item.magic_bonus} to hit and damage. "
            f"Equipping: damage {old_low}-{old_high} -> {low}-{high}; "
            f"to hit {player.attack_bonus:+d} -> {accuracy:+d}."
        )
    if item.slot in ('armor', 'shield'):
        current = player.equipment[item.slot]
        old_bonus = (current.armor_bonus + current.magic_bonus
                     if current is not None else 0)
        bonus = item.armor_bonus + item.magic_bonus
        new_ac = player.armor_class - old_bonus + bonus
        return (
            f"{item.name}: {item.slot} +{bonus} AC "
            f"(base {item.armor_bonus}, magic {item.magic_bonus}); "
            f"equipping changes AC {player.armor_class} -> {new_ac}."
        )
    return f"{item.name}: " + ITEM_DESCRIPTIONS.get(item.name, 'An item you can carry.')


def use_item(player, index, messages):
    if not 0 <= index < len(player.inventory):
        messages.append("That slot is empty.")
        return False
    item = player.inventory[index]
    if item.slot is not None:
        return equip_item(player, index, messages)
    if item.effect is None:
        messages.append("That item cannot be used.")
        return False
    apply_effect = item.effect()
    used, message = apply_effect(player)
    messages.append(message)
    if not used:
        return False
    player.inventory.pop(index)
    messages.append(f"You use {item.name}.")
    return True


def drop_item(player, index, items, messages):
    if not 0 <= index < len(player.inventory):
        messages.append("That slot is empty.")
        return False
    item = player.inventory.pop(index)
    if item.slot in player.equipment and player.equipment[item.slot] is item:
        player.equipment[item.slot] = None
        messages.append(f"You unequip {item.name}.")
    item.x, item.y = player.x, player.y
    items.append(item)
    messages.append(f"You drop {item.name}.")
    return True


def show_inventory(player, items, messages):
    selected = None
    detail = "Choose 1-9 to inspect. Escape returns to the dungeon."
    while True:
        clear_screen()
        print(f"BACKPACK ({len(player.inventory)}/{INVENTORY_CAPACITY})")
        print()
        for index in range(INVENTORY_CAPACITY):
            name = (player.inventory[index].name
                    if index < len(player.inventory) else '[empty]')
            if index < len(player.inventory):
                item = player.inventory[index]
                if item.slot in player.equipment and player.equipment[item.slot] is item:
                    name += f" [equipped: {item.slot}]"
            marker = '>' if index == selected else ' ' 
            print(f"{marker} {index + 1}. {name}")
        print()
        print(detail)
        if selected is not None:
            print("u: use/equip  r: remove equipment  d: drop")
        print("Using, equipping, removing, or dropping takes a turn on success.")
        key = get_key()
        if key == '\x1b':
            return False
        if key in '123456789' and len(key) == 1:
            index = int(key) - 1
            if index < len(player.inventory):
                selected = index
                item = player.inventory[index]
                detail = describe_item(player, item)
            else:
                selected = None
                detail = f"Slot {key} is empty."
        elif key in ('u', 'r', 'd'):
            if selected is None:
                detail = "Choose an occupied slot first."
                continue
            if key == 'u':
                spent_turn = use_item(player, selected, messages)
            elif key == 'r':
                spent_turn = unequip_item(player, selected, messages)
            else:
                spent_turn = drop_item(player, selected, items, messages)
            if spent_turn:
                return True
            detail = messages[-1]


def try_move(player, game_map, monsters, items, dx, dy, messages):
    if dx == 0 and dy == 0:
        return False
    new_x = player.x + dx
    new_y = player.y + dy

    target = next((m for m in monsters if m.alive and m.x ==
                  new_x and m.y == new_y), None)
    if target:
        message, killed = attack(player, target)
        messages.append(message)
        reward_kill(player, killed, messages)
        return True

    if is_walkable(game_map, new_x, new_y):
        player.x = new_x
        player.y = new_y
        pick_up_item(player, items, messages)
        return True

    messages.append("You bump into a wall.")

    return False


def get_player_input():
    directions = {
        'w': (0, -1),
        's': (0, 1),
        'a': (-1, 0),
        'd': (1, 0),
    }

    move = get_key()

    if move == 'q':
        return 'quit'
    if move == 'i':
        return 'inventory'
    if move == '.':
        return 'wait'
    if move == 'g':
        return 'pickup'
    if move == 'c':
        return 'cast'

    return directions.get(move, (0, 0))


def missile_path(start, end):
    """Return crossed tile centers, including the source and destination."""
    x, y = start
    target_x, target_y = end
    distance_x = abs(target_x - x)
    distance_y = abs(target_y - y)
    step_x = (target_x > x) - (target_x < x)
    step_y = (target_y > y) - (target_y < y)
    crossed_x = crossed_y = 0
    path = [(x, y)]
    while crossed_x < distance_x or crossed_y < distance_y:
        horizontal = (1 + 2 * crossed_x) * distance_y
        vertical = (1 + 2 * crossed_y) * distance_x
        if horizontal == vertical:
            x += step_x
            y += step_y
            crossed_x += 1
            crossed_y += 1
        elif horizontal < vertical:
            x += step_x
            crossed_x += 1
        else:
            y += step_y
            crossed_y += 1
        path.append((x, y))
    return path


def has_line_of_sight(game_map, start, end):
    """Use the projectile route, rejecting walls and blocked corners."""
    if not is_walkable(game_map, *start) or not is_walkable(game_map, *end):
        return False
    path = missile_path(start, end)
    for previous, current in zip(path, path[1:]):
        x, y = previous
        new_x, new_y = current
        if new_x != x and new_y != y:
            if (not is_walkable(game_map, new_x, y)
                    or not is_walkable(game_map, x, new_y)):
                return False
        if not is_walkable(game_map, new_x, new_y):
            return False
    return True


def animate_magic_missile(player, target, game_map, monsters, items):
    # Skip animation in redirected output and automated/non-terminal runs.
    if not ANIMATE_SPELLS or not sys.stdout.isatty():
        return
    path = missile_path((player.x, player.y), (target.x, target.y))
    for position in path[1:]:
        clear_screen()
        render_map(game_map, player, monsters, items, projectile=position)
        print(f"Magic Missile -> {target.name}  Mana: {player.mana}/{player.max_mana}")
        sys.stdout.flush()
        delay = (MISSILE_IMPACT_SECONDS if position == path[-1]
                 else MISSILE_FRAME_SECONDS)
        time.sleep(delay)


def spell_target_error(player, spell_name, target, game_map, monsters):
    if not player.alive:
        return "You cannot cast after the run has ended."
    if spell_name not in SPELLS or spell_name not in player.spells:
        return "You have not learned that spell."
    spell = SPELLS[spell_name]
    if player.mana < spell['mana']:
        return f"Not enough mana for {spell_name}."
    if target not in monsters or not target.alive or target.hp <= 0:
        return "Choose a living monster on this floor."
    distance = abs(target.x - player.x) + abs(target.y - player.y)
    if distance > spell['range']:
        return f"{target.name} is out of range ({distance}/{spell['range']})."
    if not has_line_of_sight(game_map, (player.x, player.y), (target.x, target.y)):
        return "A wall blocks the spell's line of sight."
    if spell_name == 'Sleep':
        if target.sleep_immune:
            return f"{target.name} is immune to Sleep."
        if target.sleep_turns >= 3:
            return f"{target.name} is already asleep for the full duration."
    return None


def cast_spell(player, spell_name, target, game_map, monsters, messages,
               animate=None):
    error = spell_target_error(player, spell_name, target, game_map, monsters)
    if error is not None:
        messages.append(error)
        return False
    player.mana -= SPELLS[spell_name]['mana']
    if spell_name == 'Magic Missile':
        if animate is not None:
            animate(target)
        damage = random.randint(1, 6) + 2
        message, killed = apply_damage(
            player, target, damage,
            f"Your Magic Missile hits {target.name} for {damage} damage.",
        )
        messages.append(message)
        reward_kill(player, killed, messages)
    else:
        target.sleep_turns = 3
        messages.append(f"{target.name} falls asleep for its next three actions.")
    return True


def show_cast_menu(player, game_map, monsters, messages, animate=None):
    if not player.spells:
        messages.append("Your spellbook is empty. Use a spell scroll to learn.")
        return False
    while True:
        clear_screen()
        print(f"SPELLBOOK - Mana {player.mana}/{player.max_mana}")
        for number, name in enumerate(player.spells, start=1):
            spell = SPELLS[name]
            print(f"{number}. {name}: {spell['mana']} mana, range {spell['range']}")
            print(f"   {spell['description']}")
        print("Choose a spell. A sole target is automatic; otherwise choose a target. Escape cancels.")
        key = get_key()
        if key == '\x1b':
            return False
        if len(key) != 1 or key not in '123456789':
            continue
        index = int(key) - 1
        if index >= len(player.spells):
            continue
        spell_name = player.spells[index]
        if player.mana < SPELLS[spell_name]['mana']:
            messages.append(f"Not enough mana for {spell_name}.")
            return False
        return show_spell_targets(
            player, spell_name, game_map, monsters, messages, animate
        )


def show_spell_targets(player, spell_name, game_map, monsters, messages,
                       animate=None):
    targets = sorted(
        (monster for monster in monsters
         if monster.alive and monster.hp > 0
         and (spell_name != 'Magic Missile'
              or abs(monster.x - player.x) + abs(monster.y - player.y)
              <= SPELLS[spell_name]['range'])),
        key=lambda monster: (abs(monster.x - player.x) + abs(monster.y - player.y),
                             monster.y, monster.x),
    )
    if not targets:
        if spell_name == 'Magic Missile':
            messages.append("No living monsters are within Magic Missile range (6 tiles).")
        else:
            messages.append("There are no living targets on this floor.")
        return False
    if len(targets) == 1:
        return cast_spell(player, spell_name, targets[0], game_map, monsters,
                          messages, animate)
    page = 0
    detail = "Choose a target to cast. Escape cancels. n/p: next/previous page."
    while True:
        clear_screen()
        render_map(game_map, player, monsters)
        print(f"{spell_name} - Mana {player.mana}/{player.max_mana}")
        print(f"Target page {page + 1}/{(len(targets) + 8) // 9}")
        visible = targets[page * 9:page * 9 + 9]
        for number, target in enumerate(visible, start=1):
            error = spell_target_error(player, spell_name, target, game_map, monsters)
            status = error if error is not None else 'ready'
            print(f"{number}. {target.name} ({target.x}, {target.y}) "
                  f"HP {target.hp}/{target.max_hp}: {status}")
        print(detail)
        key = get_key()
        if key == '\x1b':
            return False
        if key == 'n' and (page + 1) * 9 < len(targets):
            page += 1
        elif key == 'p' and page > 0:
            page -= 1
        elif len(key) == 1 and key in '123456789':
            index = int(key) - 1
            if index < len(visible):
                if cast_spell(player, spell_name, visible[index], game_map, monsters,
                              messages, animate):
                    return True
                detail = messages[-1]


def player_death_check(player):
    if player.hp <= 0:
        player.alive = False
        previous_best_depth, previous_best_gold = load_high_score()
        save_score(player.depth, player.gold)

        print(get_death_message(player.killer))
        print(
            f"You reached depth {player.depth}, level {player.level}, carrying {player.gold} gold.")

        if player.depth > previous_best_depth:
            print("That's a new personal best!")
        else:
            print(
                f"Your best run reached depth {previous_best_depth} with {previous_best_gold} gold.")

        return True
    return False


def game_loop(player, width, height):
    game_map, rooms, monsters, items, stairs = generate_floor(
        width, height, player.depth)
    player.x, player.y = find_available_player_spawn(game_map, rooms)
    messages = []

    while player.alive:
        clear_screen()
        render_map(game_map, player, monsters, items)
        show_character_stats(player)
        print(
            f"Level: {player.level}  "
            f"XP: {player.xp}/{xp_for_next_level(player.level)}"
        )
        print(f"Depth: {player.depth}  Gold: {player.gold}")
        print(f"Backpack: {len(player.inventory)}/{INVENTORY_CAPACITY}")
        print("w/a/s/d: move  i: inventory  c: cast  g: pick up  .: wait  q: quit")
        floor_count = sum(
            (item.x, item.y) == (player.x, player.y) for item in items
        )
        if floor_count:
            print(f"Items here: {floor_count}. Press g to pick up one.")
        for msg in messages:
            print(msg)
        messages = []

        move = get_player_input()

        if move == 'quit':
            print("You retreat from the dungeon. Coward.")
            break

        if move == 'inventory':
            spent_turn = show_inventory(player, items, messages)
        elif move == 'cast':
            spent_turn = show_cast_menu(
                player, game_map, monsters, messages,
                animate=lambda target: animate_magic_missile(
                    player, target, game_map, monsters, items
                ),
            )
        elif move == 'pickup':
            spent_turn = pick_up_item(
                player, items, messages, report_empty=True
            )
        elif move == 'wait':
            spent_turn = True
        else:
            dx, dy = move
            spent_turn = try_move(
                player, game_map, monsters, items, dx, dy, messages
            )
        if not spent_turn:
            continue

        if player_death_check(player):
            break

        for monster in monsters:
            if monster.alive:
                monster_take_turn(
                    monster, player, game_map, monsters, messages
                )
                if not player.alive:
                    break

        if player_death_check(player):
            break

        if player.invisible_turns > 0:
            player.invisible_turns -= 1
            if player.invisible_turns == 0:
                messages.append("You reappear. The monsters notice.")

        if (player.x, player.y) == stairs:
            player.depth += 1
            name = generate_dungeon_name()
            messages.append(
                f"You descend into {name} (depth {player.depth})...")
            game_map, rooms, monsters, items, stairs = generate_floor(
                width, height, player.depth)
            player.x, player.y = find_available_player_spawn(game_map, rooms)


def show_title_screen():
    print(Fore.GREEN + "=" * 40)
    print("           THE DEEPER DOWN")
    print("        A Python Roguelike")
    print("=" * 40)
    print()
    print("Move with w/a/s/d. Walk into monsters to fight them.")
    print("Find the > to descend. Death is permanent.")
    print("i: inventory; 1-9: select; u: use/equip; r: remove; d: drop.")
    print("g: pick up one item here. .: wait.")
    print("Gear stays in the nine-slot backpack. Escape closes inventory.")
    print("Each level: constitution-based HP and one stat choice (maximum score 18).")
    print("Rare stat potions grant +1 for this run, also capped at 18.")
    print("c: cast; select a spell, then a numbered target. Escape cancels.")
    print()
    input("Press Enter to descend into the dungeon..." + Style.RESET_ALL)


def main():
    clear_screen()
    show_title_screen()
    player = choose_character()
    if player is not None:
        game_loop(player, WIDTH, HEIGHT)


if __name__ == "__main__":
    main()
