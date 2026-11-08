# Dungeon Crawl Chapter Project

This repository contains a progression of standalone Python dungeon-crawl prototypes built chapter by chapter. Each script is a self-contained milestone in a larger roguelike design, with the mechanics and balance rules tracked in [rules.md](rules.md).

The project starts from a Book One reference implementation and then advances through Book Two mechanics such as inventory management, classes, leveling, weapons and armor, magic, shops, and persistent saves.

## Project goals

- Build a playable roguelike in small, testable steps
- Explore progression systems for classes, stats, combat, and loot
- Add magic and dungeon features gradually rather than all at once
- Keep each chapter runnable on its own

## Requirements

- Python 3.9+
- `colorama`

Install dependencies:

```bash
pip install colorama
```

## Running the game

Most chapters are run directly as scripts.

```bash
python chapter2.py
python chapter4.py
python chapter8.py
python chapter13.py
```

A few files are reference or compatibility variants rather than the main chapter flow:

```bash
python rogue_final.py
python rogue2_final.py
python dungeon_face.py
```

Some scripts accept optional command-line flags. For example, chapter 13 supports a graphics mode:

```bash
python chapter13.py --graphics
```

## Chapter overview

| File                | Description                                                                          |
| ------------------- | ------------------------------------------------------------------------------------ |
| `rogue_final.py`  | Book One reference implementation with corrected monster movement and death handling |
| `chapter2.py`     | Nine-slot inventory system built on the earlier prototype                            |
| `chapter3.py`     | Use, drop, and collection flow for items                                             |
| `chapter4.py`     | Class selection and ability-score-based combat basics                                |
| `chapter5.py`     | Leveling and stat-improvement choices                                                |
| `chapter6.py`     | Weapon, armor, and shield equipment system                                           |
| `chapter7.py`     | Rare stat-boosting potions                                                           |
| `chapter8.py`     | Magic missile and sleep spellcasting                                                 |
| `chapter9.py`     | Expanded magic, allied summons, and combat twists                                    |
| `chapter10.py`    | Store/merchant flow with gold spending on specific floors                            |
| `chapter11.py`    | Floor memory and return paths to earlier shop access                                 |
| `rogue2_final.py` | Alternate Book Two final reference for the chapter 13 gameplay state                |
| `chapter12.py`    | Pygame-based face for the chapter 11 game                                            |
| `chapter13.py`    | Save and resume support with run persistence and death cleanup                       |
| `dungeon_face.py` | Compatibility launcher for the graphical implementation                              |

## Rules and design notes

The project includes detailed design rules in [rules.md](rules.md). That file documents the intended class stats, level progression, combat balances, equipment behavior, and chapter-by-chapter checkpoint goals.

The rules file is especially useful when comparing chapter files side by side, because the mechanics evolve over time as the game is redesigned and expanded.

## Typical workflow

1. Pick a chapter to run.
2. Review the matching rules in [rules.md](rules.md).
3. Play the chapter to test the feature it introduces.
4. Compare behavior with the rules and adjust balancing or implementation in that chapter.

## Notes

- Each chapter is designed to be runnable independently.
- The project is best understood as a learning progression rather than a single polished game.
- Final gameplay state can be exercised through the chapter files and the saved-run logic in chapter 13.
