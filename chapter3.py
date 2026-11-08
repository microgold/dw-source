#!/usr/bin/env python3
"""Book Two, Chapter 3 - Choose when to use, drop, and collect items."""

import random
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


def attack(attacker, defender):
    hit_roll = random.randint(1, 20)

    if hit_roll <= 2:
        return f"{attacker_name(attacker)} swings and completely misses.", None

    damage = max(1, random.randint(1, attacker.attack) - defender.defense)
    defender.hp -= damage

    message = f"{attacker_name(attacker)} hits {defender_name(defender)} for {damage} damage."
    killed = None

    if defender.hp <= 0:
        defender.alive = False
        message += f" {defender_name(defender)} falls."
        killed = defender
        if isinstance(defender, Player):
            defender.killer = attacker.name if hasattr(
                attacker, 'name') else None

    return message, killed


def heal_effect(player, amount):
    def apply(player):
        if player.hp >= player.max_hp:
            return False, "You are already at full health."
        healed = min(amount, player.max_hp - player.hp)
        player.hp += healed
        return True, f"You feel better. Healed {healed} HP."
    return apply


def armor_effect(amount):
    def apply(player):
        gained = min(amount, 3 - player.defense)
        if gained <= 0:
            return False, "Your defense is already at its limit."
        player.defense += gained
        return True, f"Defense increased by {gained}."
    return apply


def attack_boost_effect(player, amount):
    def apply(player):
        player.attack += amount
        return True, f"Your weapon feels sharper. Attack increased by {amount}."
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


def render_map(game_map, player, monsters, items=None):
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


def check_level_up(player, messages):
    if player.xp >= xp_for_next_level(player.level):
        player.level += 1
        player.max_hp += 5
        player.hp = player.max_hp
        player.attack += 1
        messages.append(
            f"You reached level {player.level}! Max HP up to {player.max_hp}, Attack up to {player.attack}."
        )


class Player:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.hp = 20
        self.max_hp = 20
        self.attack = 4
        self.alive = True
        self.depth = 1
        self.invisible_turns = 0
        self.killer = None
        self.gold = 0
        self.xp = 0
        self.level = 1
        self.defense = 0
        self.inventory = []

    @property
    def is_invisible(self):
        return self.invisible_turns > 0


class Monster:
    def __init__(self, x, y, name, symbol, hp, attack, xp, gold_range):
        self.x = x
        self.y = y
        self.name = name
        self.symbol = symbol
        self.hp = hp
        self.max_hp = hp
        self.attack = attack
        self.defense = 0
        self.alive = True
        self.xp = xp
        self.gold_range = gold_range


class Item:
    def __init__(self, x, y, name, symbol, effect):
        self.x = x
        self.y = y
        self.name = name
        self.symbol = symbol
        self.effect = effect


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
        'attack': 2, 'xp': 5,  'gold': (1, 4)},
    {'name': 'Goblin',    'symbol': 'g', 'hp': 10,
        'attack': 3, 'xp': 10, 'gold': (3, 8)},
    {'name': 'Skeleton',  'symbol': 's', 'hp': 14,
        'attack': 4, 'xp': 15, 'gold': (5, 12)},
]

ITEM_TYPES = [
    {'name': 'Health Potion', 'symbol': '!',
        'effect': lambda: heal_effect(None, 8)},
    {'name': 'Whetstone', 'symbol': '/',
        'effect': lambda: attack_boost_effect(None, 1)},
    {'name': 'Iron Shield', 'symbol': 'o', 'effect': lambda: armor_effect(1)},
    {'name': 'Shadow Cloak', 'symbol': '*',
        'effect': lambda: invisibility_effect(10)},
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
                              template['xp'], template['gold'])
            monsters.append(monster)

    return monsters


def spawn_items(rooms, player_start_room, spawn_chance=0.5):
    items = []

    for room in rooms:
        if room is player_start_room:
            continue

        if random.random() < spawn_chance:
            template = random.choice(ITEM_TYPES)
            x, y = room.center()
            x += random.randint(-1, 1)
            y += random.randint(-1, 1)
            item = Item(x, y, template['name'],
                        template['symbol'], template['effect'])
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
    items = spawn_items(rooms, rooms[0])
    stairs_x, stairs_y = place_stairs(game_map, rooms)

    return game_map, rooms, monsters, items, (stairs_x, stairs_y)


def find_available_player_spawn(game_map, rooms):
    x, y = rooms[0].center()
    return x, y


def monster_take_turn(monster, player, game_map, monsters, messages):
    if not monster.alive or not player.alive or player.is_invisible:
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
    'Health Potion': 'Restores health when used.',
    'Whetstone': 'Sharpens your weapon when used.',
    'Iron Shield': 'Offers protection when used.',
    'Shadow Cloak': 'Grants temporary invisibility when used.',
}


def use_item(player, index, messages):
    if not 0 <= index < len(player.inventory):
        messages.append("That slot is empty.")
        return False
    item = player.inventory[index]
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
            marker = '>' if index == selected else ' '
            print(f"{marker} {index + 1}. {name}")
        print()
        print(detail)
        if selected is not None:
            print("u: use selected item  d: drop selected item")
        print("A successful use or drop takes a turn and closes the backpack.")
        key = get_key()
        if key == '\x1b':
            return False
        if key in '123456789' and len(key) == 1:
            index = int(key) - 1
            if index < len(player.inventory):
                selected = index
                item = player.inventory[index]
                description = ITEM_DESCRIPTIONS.get(
                    item.name, 'An item you can carry.'
                )
                detail = f"{item.name}: {description}"
            else:
                selected = None
                detail = f"Slot {key} is empty."
        elif key in ('u', 'd'):
            if selected is None:
                detail = "Choose an occupied slot first."
                continue
            if key == 'u':
                spent_turn = use_item(player, selected, messages)
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
        if killed:
            gold_dropped = random.randint(*killed.gold_range)
            player.gold += gold_dropped
            player.xp += killed.xp
            messages.append(
                f"You find {gold_dropped} gold. (Total: {player.gold})  +{killed.xp} XP.")
            check_level_up(player, messages)
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

    return directions.get(move, (0, 0))


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
        print(
            f"HP: {player.hp}/{player.max_hp}  Level: {player.level}  XP: {player.xp}/{xp_for_next_level(player.level)}")
        print(f"Depth: {player.depth}  Gold: {player.gold}")
        print(f"Backpack: {len(player.inventory)}/{INVENTORY_CAPACITY}")
        print("w/a/s/d: move  i: inventory  g: pick up  .: wait  q: quit")
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
    print("i: inventory; 1-9: select; u: use; d: drop; Escape: return.")
    print("g: pick up one item here. .: wait.")
    print("Using, dropping, and picking up items each take a turn.")
    print()
    input("Press Enter to descend into the dungeon..." + Style.RESET_ALL)


def main():
    clear_screen()
    show_title_screen()
    player = Player(0, 0)
    game_loop(player, WIDTH, HEIGHT)


if __name__ == "__main__":
    main()
