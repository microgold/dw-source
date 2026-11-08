"""Chapter 13: save completed turns, resume a run, and delete it on death.

Terminal: python chapter13.py
Graphical: python chapter13.py --graphics
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import random
import tempfile

ROOT = Path(__file__).resolve().parent
SAVE_FILE = ROOT / 'saved_run.json'
SAVE_VERSION = 1


def load_engine():
    spec = importlib.util.spec_from_file_location('persistent_dungeon_engine', ROOT / 'chapter11.py')
    if spec is None or spec.loader is None:
        raise RuntimeError('Keep chapter11.py beside chapter13.py.')
    engine = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(engine)
    return engine


game = load_engine()
_original_death_check = game.player_death_check
PLAYER_FIELDS = ('x', 'y', 'class_name', 'spells', 'constitution', 'strength',
                 'dexterity', 'intelligence', 'level', 'level_hp_gained',
                 'level_mana_gained', 'hp', 'mana', 'alive', 'depth',
                 'max_depth_reached', 'invisible_turns', 'strength_turns',
                 'strength_bonus', 'killer', 'gold', 'xp')
MONSTER_FIELDS = ('x', 'y', 'name', 'symbol', 'hp', 'max_hp', 'weapon_damage',
                  'damage_bonus', 'attack_bonus', 'armor_class', 'alive', 'xp',
                  'gold_range', 'sleep_turns', 'sleep_immune', 'undead',
                  'rewards_claimed', 'charm_turns', 'fear_turns',
                  'summon_turns', 'summoned')


class SaveError(Exception):
    """A save could not be read, validated, or written."""


class Run:
    def __init__(self, player, dungeon, messages=None, shop_pending=False, rng_state=None):
        self.player = player
        self.dungeon = dungeon
        self.messages = [] if messages is None else messages
        self.shop_pending = shop_pending
        self.rng_state = rng_state


def item_to_data(item):
    return {'name': item.base_name, 'x': item.x, 'y': item.y,
            'magic_bonus': item.magic_bonus, 'enhancement': item.enhancement}


def item_from_data(data):
    known = {entry['name'] for entry in game.ITEM_TYPES}
    if data['name'] not in known:
        raise SaveError('The save contains an unknown item template.')
    for key in ('magic_bonus', 'enhancement'):
        if type(data[key]) is not int or data[key] < 0:
            raise SaveError('Invalid item bonus.')
    item = game.create_item(data['name'], data['x'], data['y'], data['magic_bonus'])
    item.enhancement = data['enhancement']
    return item


def run_to_data(run):
    player = run.player
    if not player.alive or player.hp <= 0:
        raise SaveError('A dead character cannot be saved.')
    equipment = {}
    for slot, equipped in player.equipment.items():
        if equipped is None:
            equipment[slot] = None
        else:
            equipment[slot] = next(index for index, item in enumerate(player.inventory)
                                   if item is equipped)
    floors = []
    for depth, floor in sorted(run.dungeon.floors.items()):
        floors.append({
            'depth': depth, 'name': floor.name,
            'tiles': [[{'symbol': tile.symbol, 'walkable': tile.walkable,
                        'monster_walkable': tile.monster_walkable}
                       for tile in row] for row in floor.game_map],
            'rooms': [[room.x1, room.y1, room.x2 - room.x1, room.y2 - room.y1]
                      for room in floor.rooms],
            'monsters': [{name: getattr(monster, name) for name in MONSTER_FIELDS}
                         for monster in floor.monsters],
            'items': [item_to_data(item) for item in floor.items],
            'entrance': floor.entrance, 'upstairs': floor.upstairs,
            'downstairs': floor.downstairs,
            'store': (None if floor.store is None else
                      {'x': floor.store.x, 'y': floor.store.y, 'depth': floor.store.depth,
                       'name': floor.store.name, 'stock': floor.store.stock}),
        })
    return {
        'version': SAVE_VERSION,
        'player': {'state': {name: getattr(player, name) for name in PLAYER_FIELDS},
                   'inventory': [item_to_data(item) for item in player.inventory],
                   'equipment': equipment},
        'dungeon': {'width': run.dungeon.width, 'height': run.dungeon.height, 'floors': floors},
        'messages': list(run.messages), 'shop_pending': run.shop_pending,
        'random_state': game.random.getstate(),
    }


def require(condition, message):
    if not condition:
        raise SaveError(message)


def integer(value, minimum=None):
    return type(value) is int and (minimum is None or value >= minimum)


def coordinate(value, width, height):
    require(isinstance(value, (list, tuple)) and len(value) == 2,
            'Invalid floor coordinate.')
    x, y = value
    require(integer(x, 0) and integer(y, 0) and x < width and y < height,
            'Coordinate is outside the floor.')
    return x, y


def tuples(value):
    return tuple(tuples(item) for item in value) if isinstance(value, list) else value


def run_from_data(data):
    """Reconstruct known classes and item factories; never execute saved code."""
    try:
        require(data['version'] == SAVE_VERSION, 'Unsupported save version.')
        dimensions = data['dungeon']
        width, height = dimensions['width'], dimensions['height']
        require(integer(width, 1) and integer(height, 1), 'Invalid map dimensions.')
        raw_player = data['player']
        state = raw_player['state']
        require(state['class_name'] in game.CLASS_STATS, 'Unknown character class.')
        require(state['alive'] is True and integer(state['hp'], 1), 'This character is dead.')
        for name in PLAYER_FIELDS:
            if name not in ('class_name', 'spells', 'alive', 'killer'):
                require(integer(state[name], 0), f'Invalid player field: {name}.')
        require(state['level'] >= 1 and state['depth'] >= 1, 'Invalid character level or floor.')
        require(state['max_depth_reached'] >= state['depth'], 'Invalid deepest floor.')
        require(state['killer'] is None or isinstance(state['killer'], str), 'Invalid killer name.')
        require(isinstance(state['spells'], list) and all(name in game.SPELLS for name in state['spells'])
                and len(set(state['spells'])) == len(state['spells']), 'Invalid spellbook.')
        player = game.Player(0, 0, state['class_name'])
        for name in PLAYER_FIELDS:
            setattr(player, name, state[name])
        player.inventory = [item_from_data(item) for item in raw_player['inventory']]
        require(len(player.inventory) <= game.INVENTORY_CAPACITY, 'Backpack is too large.')
        require(all(item.x is None and item.y is None for item in player.inventory),
                'Carried items cannot occupy floor tiles.')
        require(set(raw_player['equipment']) == {'weapon', 'armor', 'shield'}, 'Invalid equipment slots.')
        player.equipment = {}
        for slot, index in raw_player['equipment'].items():
            require(index is None or (integer(index, 0) and index < len(player.inventory)),
                    'Invalid equipped item reference.')
            item = player.inventory[index] if index is not None else None
            require(item is None or item.slot == slot, 'Equipment is in the wrong slot.')
            player.equipment[slot] = item
        require(0 < player.hp <= player.max_hp and 0 <= player.mana <= player.max_mana,
                'Character resources exceed their limits.')
        dungeon = game.Dungeon(width, height)
        for raw_floor in dimensions['floors']:
            depth = raw_floor['depth']
            require(integer(depth, 1) and depth not in dungeon.floors, 'Invalid or duplicate floor.')
            floor = game.Floor.__new__(game.Floor)
            floor.depth, floor.name = depth, raw_floor['name']
            require(isinstance(floor.name, str), 'Invalid floor name.')
            tiles = raw_floor['tiles']
            require(len(tiles) == height and all(len(row) == width for row in tiles), 'Map dimensions changed.')
            floor.game_map = []
            for row in tiles:
                restored = []
                for tile in row:
                    require(isinstance(tile['symbol'], str) and len(tile['symbol']) == 1
                            and type(tile['walkable']) is bool and type(tile['monster_walkable']) is bool,
                            'Invalid tile.')
                    restored.append(game.Tile(tile['symbol'], tile['walkable'], tile['monster_walkable']))
                floor.game_map.append(restored)
            floor.rooms = [game.Room(*room) for room in raw_floor['rooms']]
            floor.entrance = coordinate(raw_floor['entrance'], width, height)
            floor.upstairs = (None if raw_floor['upstairs'] is None else
                              coordinate(raw_floor['upstairs'], width, height))
            floor.downstairs = coordinate(raw_floor['downstairs'], width, height)
            require(floor.entrance != floor.downstairs, 'Stair landings overlap.')
            require(floor.upstairs == (floor.entrance if depth > 1 else None), 'Invalid upstairs connection.')
            for x, y in [floor.entrance, floor.downstairs]:
                require(game.is_walkable(floor.game_map, x, y)
                        and not game.is_monster_walkable(floor.game_map, x, y), 'Invalid reserved landing.')
            floor.monsters = []
            occupied = set()
            for raw in raw_floor['monsters']:
                for name in MONSTER_FIELDS:
                    require(name in raw, f'Missing creature field: {name}.')
                for name in ('alive', 'sleep_immune', 'undead', 'rewards_claimed', 'summoned'):
                    require(type(raw[name]) is bool, 'Invalid creature flag.')
                for name in MONSTER_FIELDS:
                    if name not in ('name', 'symbol', 'gold_range', 'alive', 'sleep_immune',
                                    'undead', 'rewards_claimed', 'summoned'):
                        require(integer(raw[name]), 'Invalid creature stat.')
                point = coordinate((raw['x'], raw['y']), width, height)
                require(isinstance(raw['name'], str) and isinstance(raw['symbol'], str)
                        and len(raw['symbol']) == 1 and raw['max_hp'] > 0
                        and 0 <= raw['hp'] <= raw['max_hp'] and raw['weapon_damage'] >= 1,
                        'Invalid creature data.')
                gold = raw['gold_range']
                require(len(gold) == 2 and all(integer(n, 0) for n in gold) and gold[0] <= gold[1],
                        'Invalid creature treasure.')
                monster = game.Monster(raw['x'], raw['y'], raw['name'], raw['symbol'], raw['max_hp'],
                                       raw['weapon_damage'], raw['xp'], tuple(gold),
                                       raw['attack_bonus'], raw['armor_class'], raw['sleep_immune'], raw['undead'])
                for name in MONSTER_FIELDS:
                    setattr(monster, name, tuple(raw[name]) if name == 'gold_range' else raw[name])
                if monster.alive:
                    require(monster.hp > 0 and point not in occupied
                            and game.is_monster_walkable(floor.game_map, *point), 'Invalid creature position.')
                    occupied.add(point)
                floor.monsters.append(monster)
            floor.items = [item_from_data(item) for item in raw_floor['items']]
            for item in floor.items:
                coordinate((item.x, item.y), width, height)
                require(game.is_walkable(floor.game_map, item.x, item.y), 'Item is inside a wall.')
            raw_store = raw_floor['store']
            floor.store = None
            if raw_store is not None:
                x, y = coordinate((raw_store['x'], raw_store['y']), width, height)
                require(raw_store['depth'] == depth and depth in (1, 5), 'Invalid store floor.')
                require(floor.game_map[y][x].symbol == '$', 'Store tile is missing.')
                store = game.Store(x, y, depth)
                store.name = raw_store['name']
                require(isinstance(store.name, str), 'Invalid store name.')
                for entry in raw_store['stock']:
                    require(entry['name'] in {t['name'] for t in game.ITEM_TYPES}
                            and integer(entry['price'], 0) and integer(entry['magic_bonus'], 0)
                            and (entry['quantity'] is None or integer(entry['quantity'], 0)), 'Invalid shop offer.')
                store.stock = raw_store['stock']
                floor.store = store
            dungeon.floors[depth] = floor
        require(player.depth in dungeon.floors, 'Current floor is missing.')
        current = dungeon.floors[player.depth]
        position = coordinate((player.x, player.y), width, height)
        require(game.is_walkable(current.game_map, *position)
                and all(not m.alive or (m.x, m.y) != position for m in current.monsters), 'Player landing is blocked.')
        require(type(data['shop_pending']) is bool and isinstance(data['messages'], list)
                and all(isinstance(message, str) for message in data['messages']), 'Invalid pending messages.')
        rng_state = tuples(data['random_state'])
        random.Random().setstate(rng_state)  # Validate without changing the live RNG.
        return Run(player, dungeon, data['messages'], data['shop_pending'], rng_state)
    except SaveError:
        raise
    except (KeyError, TypeError, ValueError, AttributeError, IndexError, StopIteration) as exc:
        raise SaveError(f'The save is incomplete or invalid: {exc}') from exc


def save_run(run, path=None):
    path = SAVE_FILE if path is None else Path(path)
    temporary = None
    try:
        data = run_to_data(run)
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent,
                                         prefix='.saved_run-', suffix='.tmp', delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(data, handle, indent=2, allow_nan=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except (OSError, TypeError, ValueError, StopIteration) as exc:
        raise SaveError(f'Could not save the run: {exc}') from exc
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def load_run(path=None):
    path = SAVE_FILE if path is None else Path(path)
    try:
        return run_from_data(json.loads(path.read_text(encoding='utf-8')))
    except (OSError, ValueError) as exc:
        raise SaveError(f'Could not read the saved run: {exc}') from exc


def delete_save(path=None):
    path = SAVE_FILE if path is None else Path(path)
    path.unlink(missing_ok=True)


def persistent_death_check(player):
    if not player.alive or player.hp <= 0:
        delete_save()
        return _original_death_check(player)
    return False


def new_run(player, width=None, height=None):
    dungeon = game.Dungeon(width or game.WIDTH, height or game.HEIGHT)
    floor = dungeon.get_floor(player.depth)
    player.x, player.y = floor.entrance
    player.max_depth_reached = max(player.max_depth_reached, player.depth)
    return Run(player, dungeon)


active_run = None


def game_loop(run):
    player = run.player
    dungeon = run.dungeon
    current = dungeon.get_floor(player.depth)
    game_map, monsters, items, store = (current.game_map, current.monsters, current.items, current.store)
    messages = run.messages
    shop_pending = run.shop_pending
    while player.alive:
        run.messages = messages
        run.shop_pending = shop_pending
        try:
            save_run(run)
            saved = True
        except SaveError as exc:
            saved = False
            messages.append(str(exc))
        game.clear_screen()
        game.render_map(game_map, player, monsters, items)
        game.show_character_stats(player)
        print(f'Level: {player.level}  XP: {player.xp}/{game.xp_for_next_level(player.level)}')
        print(f'Floor: {player.depth}  Deepest: {player.max_depth_reached}  Gold: {player.gold}')
        print(f'Backpack: {len(player.inventory)}/{game.INVENTORY_CAPACITY}')
        allies = [m for m in monsters if m.alive and m.friendly]
        if allies:
            print('Allies: ' + ', '.join((f'{m.name} HP {m.hp}/{m.max_hp} ({(m.summon_turns if m.summoned else m.charm_turns)} actions left)' for m in allies)))
        print('w/a/s/d: move  i: inventory  c: cast  g: pick up  b: shop  Enter: stairs  .: wait  q: quit')
        if store is not None and (player.x, player.y) == (store.x, store.y):
            print('You are at the store. Press b to browse again.')
        if (player.x, player.y) == current.downstairs:
            print('> Press Enter to descend. Walking onto stairs does not travel.')
        elif current.upstairs is not None and (player.x, player.y) == current.upstairs:
            print('< Press Enter to return upstairs. Visited floors are remembered.')
        floor_count = sum(((item.x, item.y) == (player.x, player.y) for item in items))
        if floor_count:
            print(f'Items here: {floor_count}. Press g to pick up one.')
        for msg in messages:
            print(msg)
        messages = []
        if shop_pending:
            move = 'shop'
            shop_pending = False
        else:
            move = game.get_player_input()
        previous_position = (player.x, player.y)
        if move == 'quit':
            if not saved:
                messages.append('Save failed. The run is still open; quit again after fixing the save location.')
                continue
            print('Your run is saved. Choose Continue next time to resume here.')
            break
        if move == 'stairs':
            destination = dungeon.travel(player, current, messages)
            if destination is None:
                continue
            current = destination
            game_map, monsters, items, store = (current.game_map, current.monsters, current.items, current.store)
            shop_pending = False
            previous_position = (player.x, player.y)
            spent_turn = True
        elif move == 'shop':
            if store is None or (player.x, player.y) != (store.x, store.y):
                messages.append('There is no store here. Look for $ on floors 1 and 5.')
                continue
            spent_turn = store.browse(player, messages)
        elif move == 'inventory':
            spent_turn = game.show_inventory(player, items, messages)
        elif move == 'cast':
            spent_turn = game.show_cast_menu(player, game_map, monsters, messages, animate=lambda target: game.animate_magic_missile(player, target, game_map, monsters, items))
        elif move == 'pickup':
            spent_turn = game.pick_up_item(player, items, messages, report_empty=True)
        elif move == 'wait':
            spent_turn = True
        else:
            dx, dy = move
            spent_turn = game.try_move(player, game_map, monsters, items, dx, dy, messages)
        if not spent_turn:
            continue
        if game.player_death_check(player):
            break
        for monster in list(monsters):
            if monster.alive:
                game.monster_take_turn(monster, player, game_map, monsters, messages)
                if not player.alive:
                    break
        if game.player_death_check(player):
            break
        if player.strength_turns > 0:
            player.strength_turns -= 1
            if player.strength_turns == 0:
                messages.append('Your magical strength fades.')
        if player.invisible_turns > 0:
            player.invisible_turns -= 1
            if player.invisible_turns == 0:
                messages.append('You reappear. The monsters notice.')
        if store is not None and previous_position != (player.x, player.y) and ((player.x, player.y) == (store.x, store.y)):
            shop_pending = True


def choose_run():
    """Do not replace an existing run unless a new character is confirmed."""
    if not SAVE_FILE.exists():
        player = game.choose_character()
        return new_run(player) if player is not None else None
    detail = ''
    while True:
        game.clear_screen()
        print('CONTINUE YOUR DESCENT')
        loaded = None
        try:
            loaded = load_run()
            player = loaded.player
            print(f'{player.class_name}, level {player.level}, floor {player.depth}')
            print(f'HP {player.hp}/{player.max_hp}  Mana {player.mana}/{player.max_mana}')
            print(f'Gold {player.gold}  Visited floors: {len(loaded.dungeon.floors)}')
            print('c: Continue the saved run')
        except SaveError as exc:
            print(str(exc))
            print('The existing file has been left untouched. It cannot be continued.')
        print('n: New run (replaces the saved run only after confirmation)')
        print('Escape: leave')
        if detail:
            print(detail)
        key = game.get_key()
        if key == '\x1b':
            return None
        if key == 'c' and loaded is not None:
            game.random.setstate(loaded.rng_state)
            return loaded
        if key == 'n':
            print('Start a new character and replace this save? y confirms; any other key cancels.')
            if game.get_key() == 'y':
                player = game.choose_character()
                if player is not None:
                    return new_run(player)
                detail = 'Character selection canceled; the previous save is unchanged.'


def run_game():
    global active_run
    active_run = None
    game.clear_screen()
    game.show_title_screen()
    active_run = choose_run()
    if active_run is not None:
        game_loop(active_run)


def main(argv=None):
    global SAVE_FILE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--graphics', action='store_true', help='Use the Chapter 12 Pygame interface.')
    parser.add_argument('--save', type=Path, default=SAVE_FILE, help='Save location (default: saved_run.json beside this script).')
    args = parser.parse_args(argv)
    SAVE_FILE = args.save.resolve()
    game.player_death_check = persistent_death_check
    game.main = run_game
    if args.graphics:
        from chapter12 import DungeonFace
        DungeonFace(game).run()
    else:
        run_game()


if __name__ == '__main__':
    main()
