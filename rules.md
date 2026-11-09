# Book Two Rules

These are proposed teaching values, not playtested balance. Keep them consistent across prose and code, then revise them together after playing.

### Stats

At character creation, choose a class with fixed starting scores:

| Class | Constitution | Strength | Dexterity | Intelligence | Total |
| --- | ---: | ---: | ---: | ---: | ---: |
| Warrior | 12 | 13 | 10 | 9 | 44 |
| Rogue | 10 | 11 | 13 | 10 | 44 |
| Wizard | 10 | 8 | 11 | 15 | 44 |

Ten is the baseline, not a minimum. A stat's modifier is its score minus 10: strength 13 gives +3 damage, while strength 8 gives -2. Scores initially cap at 18, including increases from leveling and potions. Each class has the same point total, but equal totals do not guarantee equal effectiveness; playtest their different combat and resource advantages.

Show the class scores and derived values before confirmation. No dungeon turns pass during selection. Calculate starting maximum HP and mana from the confirmed scores, then fill both pools. The class sets starting strengths only: all classes can improve any stat, equip the same items, and learn spells. Leveling and potions do not change the class label or restrict growth.

| Class | Starting HP | Maximum mana | Melee damage | Attack bonus | AC without armor |
| --- | ---: | ---: | --- | ---: | ---: |
| Warrior | 24 | 4 | 4–7 | +0 | 10 |
| Rogue | 20 | 6 | 2–5 | +3 | 11 |
| Wizard | 20 | 16 | 1–2 | +1 | 10 |

These damage ranges use the same starting weapon with a four-sided damage roll. Minimum damage remains 1. Once Magic Missile is implemented, start the Wizard with that spell learned so its main advantage is usable from the first floor; other classes can learn it from scrolls. Until the casting chapters, explicitly present classes as a system still being built, with the Wizard's mana reserved for the coming spells. Sleep becomes learnable when its chapter is implemented.

| Stat | Effect of each point above 10 |
| --- | --- |
| Constitution | +2 maximum HP |
| Intelligence | +2 maximum mana |
| Strength | +1 melee damage on a successful hit |
| Dexterity | +1 to physical attack rolls; +1 AC per two points above 10 |

Starting maximum HP is `20 + 2 * (constitution - 10)`. From Chapter 5 onward, maximum HP is `20 + level_hp_gained + 2 * (constitution - 10)`, where `level_hp_gained` stores the sum of HP actually earned at previous level-ups. A constitution increase adds the same HP to current and maximum HP, preserving the amount of damage already suffered. It does not fully heal the player.

Maximum mana is `6 + 2 * (intelligence - 10)`. Once spellcasting is introduced, the player starts a run with full mana. An intelligence increase adds the same amount to current and maximum mana, preserving mana already spent rather than refilling the pool. Until then, the character sheet explains that intelligence reserves mana for spells introduced later.

A level adds `5 + (constitution - 10) // 2` current and maximum HP and awards one stat point. Calculate and record the HP gain before that level's stat choice. Never recalculate previous level gains after constitution changes. Choosing constitution adds its own HP increase as well. Remove book one's automatic attack increase and full heal; do not apply both progression systems. Keep XP cumulative and process every threshold crossed. If all stats reach the cap, future levels still add HP but award no unusable stat points.

### Chapter 4 checkpoint

`chapter4.py` adds class selection with `1`–`3` to preview, Enter to confirm, and Escape to quit before generating a floor. The status display includes scores, damage range, attack bonus, AC, and reserved mana. Spellcasting is not implemented yet.

Until Chapter 5 adds stat choices, levels grant only 5 current and maximum HP, preserving damage already suffered. They no longer increase attack or fully heal the player. Multiple XP thresholds are processed in one award.

Until Chapter 6 adds equipment, using an Iron Shield still consumes it but now adds 1 AC, capped at +3 AC from shields. This replaces damage reduction rather than stacking with it. Whetstones raise maximum weapon damage by 1. Chapter 3's original defense behavior remains in that earlier checkpoint.

Initial monster combat values: Giant Rat attack bonus +0/AC 10; Goblin +1/AC 11; Skeleton +2/AC 12. Existing depth scaling still affects their HP and maximum damage. These values need playtesting against all three classes.

### Chapter 5 checkpoint

`chapter5.py` awards one stat increase for each level, after adding the constitution-based HP gain to current HP and the stored `level_hp_gained` total. The gain uses constitution before that level's choice: CON 10–11 grants 5, 12–13 grants 6, 14–15 grants 7, 16–17 grants 8, and 18 grants 9. The status display and selection preview show the HP gain at the next level. Choose `1`–`4` to preview constitution, strength, dexterity, or intelligence. Enter confirms; Escape clears the preview without forfeiting the point. The dungeon waits until a valid choice is confirmed. Previewing never mutates the real character.

Choosing constitution adds 2 current and maximum HP immediately and can improve future level gains, without changing previously earned HP; intelligence adds 2 current and maximum mana, preserving wounds and spent mana. Strength improves melee damage. Dexterity always adds 1 accuracy but raises AC only when its half-modifier increases. All scores cap at 18. If every score is capped, further levels grant HP and no unusable point. Each crossed cumulative XP threshold gets its own choice before surviving monsters take their normal phase. No extra turn or effect countdown is charged for level choices.

### Chapter 6 checkpoint

`chapter6.py` has weapon, armor, and shield slots, each referencing one carried item. Equipped items still count toward the nine-slot backpack. Every class starts with a carried, equipped Short Sword (weapon roll 1–4). Unarmed attacks use a 1-point base roll plus strength, minimum 1 damage.

In the backpack, select `1`–`9`, then `u` to use a consumable or equip gear, `r` to remove equipped gear while keeping it carried, or `d` to drop. Successful equip, removal, and drop each cost one turn and close the backpack. Equipping an already equipped item, removing unequipped gear, and canceled actions cost no turn. Dropping equipped gear clears its slot immediately. Pickup does not auto-equip.

Replacing gear leaves the previous item in the backpack, and works even when full. Only the current item in each slot contributes. Short Sword, Long Sword, and Battle Axe have maximum weapon rolls of 4, 6, and 8. Leather Armor adds 1 AC, Chain Armor adds 2, and Iron Shield adds 1 in its separate shield slot. Dexterity's half-modifier still contributes to AC; armor types do not impose additional dexterity caps in this simple implementation. All classes can equip all current gear.

Shields are no longer consumed or permanently stacked. Whetstones are consumed to increase the equipped weapon's maximum damage roll by 1; its enhancement follows that individual item through swaps, drops, and pickup. Without an equipped weapon, use is refused and the whetstone remains carried. Descriptions compare weapon rolls or the resulting AC before equipping, and inventory rows mark equipped items.

### Chapter 6 magical gear extension

Each item has a separate `magic_bonus`, initially 0. A +1 weapon adds 1 to physical attack rolls and 1 to every successful damage roll while equipped. It does not enlarge the weapon die. A +1 armor piece or shield adds 1 AC beyond its normal bonus. Carried duplicates contribute nothing. Replacing gear removes the old contribution, and dropping or removing it clears its magic bonus from the character. Displayed names include the suffix, such as Long Sword +1.

Whetstone enhancement still increases only that weapon's maximum damage roll. Magic and sharpening persist independently on the same item. Inventory comparisons show resulting accuracy and damage for weapons, and replacement AC for armor and shields.

When a piece of gear spawns, it has a depth-based chance to become +1: 1% at depth 1, 5% at depth 5, and a maximum of 10% at depth 10 onward. Thus 90–99% of spawned gear remains ordinary, and consumables never receive the upgrade. This is conditional on gear spawning, not the chance per room or floor. The starting Short Sword remains nonmagical. No +2/+3 items or special magical effects are generated yet.

### Chapter 7 checkpoint

Mana Potions are ordinary loot in Chapter 7. They restore up to 6 current mana, limited to the missing amount, and report the amount actually restored. Full-mana use is refused without consumption or a turn. They use the ordinary inventory selection/use path and do not change maximum mana or intelligence.

`chapter7.py` adds Potions of Constitution, Strength, Dexterity, and Intelligence. Each is a one-use +1 increase for this run, using the same `increase_stat` helper as leveling. They consume no XP or level choice. Constitution adds 2 current and maximum HP and can improve future level growth without recalculating historical gains. Intelligence adds 2 current and maximum mana, preserving spent mana. Strength adds melee damage; dexterity adds accuracy and only adds AC when crossing its two-point boundary. Stat increases combine normally with equipped magic bonuses without modifying the gear itself.

All four potions share a 3% category chance when an item spawns, independent of depth. Each is equally likely inside that category (0.75% per spawned item). The other 97% uses the ten ordinary item templates (including Mana Potion); magical gear is still rolled separately only for eligible equipment, using its existing depth-based rates. Stat potions are clearly named and never receive equipment magic bonuses.

Use through `i`, select `1`–`9`, then `u`. Success consumes the potion and spends one turn. At the stat cap of 18, use is refused: the potion stays carried, the menu remains open, and no turn or timer tick is charged. Carrying, inspecting, dropping, or picking up a potion does not increase a stat. A new character starts from its class template again.

### Combat and equipment

Roll `d20 + attack_bonus` against the defender's armor class; equal or higher hits. A natural 1 misses and a natural 20 hits, without extra critical damage initially. The player's attack bonus is `dexterity - 10`; armor class is `10 + (dexterity - 10) // 2 + armor_bonus`.

On a melee hit, player damage is `max(1, randint(1, weapon_damage) + strength - 10)`. The starting weapon has `weapon_damage = 4`, preserving book one's initial damage range at strength 10; class modifiers then change the final damage. Monsters have explicit attack bonuses, armor classes, and damage ranges; they do not need ability scores yet.

Armor class makes attacks less likely to land. It replaces the appendix's damage reduction when this rule is introduced. An equipped shield or armor piece contributes its listed AC bonus; picking it up does not permanently increase defense. Whetstones can later improve the equipped weapon rather than adding to a player attribute that leveling also changes.

### Items and turns

Walking onto an item attempts automatic pickup into a nine-slot backpack. Pickup is part of that movement action. If the backpack is full, the item stays on the floor and movement still succeeds. Gold goes directly to the gold total and uses no slot. Press `i` to open the backpack, `1`–`9` to inspect a numbered slot, and Escape to return. Empty slots are shown explicitly. Chapter 2 supports carrying and inspection. In Chapter 3, select a slot, then press `u` to use or `d` to drop it. A successful use or drop closes the backpack and spends one turn; a refused action keeps the item and menu open. Slots renumber after removal. Press `g` in the dungeon to pick up one item at the current position; success spends one turn, while an empty tile or full backpack costs none. Movement pickup remains part of the movement turn. Multiple floor items share a tile without merging; `g` collects them one at a time in floor-list order.

Opening menus, inspecting, canceling, invalid commands, blocked movement, and failed actions cost no turn. Moving, melee attacks (including misses), waiting, successfully using an item, dropping an item, and changing equipment cost one turn. An unusable potion stays in the backpack. Healing at full HP, a shield at the current defense cap of 3, and a cloak whose invisibility already has at least ten turns remaining all refuse use. Refreshing a shorter cloak effect resets it to ten turns rather than stacking durations. Healing messages report actual HP restored. The shield retains the appendix consumable behavior until equipment is introduced in Chapter 6. Dropped items remain at the player's position, and an explicit pickup command lets the player collect them without having to move away and back.

For a committed action: resolve the player's effect, resolve any required level choices, check deaths, run each surviving monster's action until the player dies, then finish status bookkeeping. Menus never advance counters. Define player buffs in terms of protected monster phases: a newly used ten-turn cloak protects the next ten phases, including the phase immediately after activation.

### Chapter 8 checkpoint

`chapter8.py` combines the casting foundation, Magic Missile, and Sleep in one playable checkpoint. The Wizard starts knowing Magic Missile and automatically learns Sleep upon reaching level 2, before that level's stat choice. A Wizard who already knows Sleep gets no duplicate. This grants the spell without costing a scroll, mana, or an additional turn; it does not refill mana. Other classes start with empty spellbooks and can learn either spell from scrolls. Scrolls of Magic Missile and Sleep are added to the ordinary loot pool, now twelve templates. Use a scroll through the inventory to learn its spell for the run; learning costs one turn and consumes it. Already-known scrolls are kept without spending a turn. Stat-potion rarity remains a separate 3% category and magical gear rarity is unchanged.

Press `c`, select a learned spell by number, then select a numbered target to cast immediately if more than one candidate remains. A sole target is attempted automatically, with all normal validation still required. Magic Missile filters its list to living, positive-HP monsters within its six-tile Manhattan range; if none remain, it reports that and costs nothing. Targets show names, coordinates, HP, and validation feedback. More than nine targets use `n`/`p` pages. Escape at either screen cancels the whole action. Browsing, invalid choices, insufficient mana, obstructed targets, and immunity consume no mana or turn. A successful cast consumes the listed mana and one turn. The game still has no fog of war. Magic Missile lists only in-range candidates, including wall-blocked ones with feedback; Sleep lists living targets with range and immunity feedback.

Line of sight traces between tile centers. Walls block; a diagonal corner is blocked if either adjacent side tile is a wall. Monsters do not block the ray. Range remains Manhattan distance. Magic Missile automatically hits for 1d6 + 2, ignoring AC and physical weapon bonuses. Sleep costs 3 mana and makes a susceptible target skip three monster actions, including the immediate post-cast phase. The last skipped action wakes the target, which can act on its next turn. Damage wakes it immediately; missed attacks do not. Sleep cannot affect skeletons. Recasting at the full three-action duration is refused; refreshing a shorter duration sets it to three rather than stacking.

Melee and spells use shared damage/death handling and a shared kill-reward function. Dead enemies never act or grant rewards twice. A spell kill can open the level-choice screen before the normal surviving-monster phase. Sleep counters advance during monster phases even if the player is invisible; menus never tick them. Mana Potions now restore mana actually spent on spells.

The game loop supplies a Magic Missile animation callback: after validation and mana payment, a bright cyan `*` follows the same tile route used for line of sight, then damage resolves and the normal monster phase runs once. Frames never tick effects, move actors, or consume additional turns. Scrolls render as bright magenta `?` symbols. Missile delay is 0.15 seconds per crossed tile, with a 0.35-second impact frame; `ANIMATE_SPELLS = False` disables it, and redirected/non-terminal output skips it automatically. Projectile rendering is an overlay and never changes map tiles or items. Sleep has no projectile animation.

### Spells

Intelligence 10 gives 6 maximum mana; each additional point adds 2 maximum mana. Intelligence 11 therefore allows four Magic Missiles or two Sleeps from a full pool, with 2 mana left after the Sleeps. Add mana potions; avoid unlimited safe regeneration through waiting. Intelligence changes how much the player can cast; spell costs, damage, and duration stay fixed initially. Leveling does not refill mana; only choosing intelligence adds its 2-point increase to current mana.

| Spell | Mana | Range | Initial effect |
| --- | --- | --- | --- |
| Magic Missile | 2 | 6 tiles | Automatically hits a valid target for `1d6 + 2` damage; ignores AC |
| Sleep | 3 | 5 tiles | One living target skips its next three monster actions; damage wakes it immediately |

Range uses Manhattan distance, matching four-direction movement. Both spells require an unobstructed line of sight and a living target. Magic Missile can affect undead; Sleep cannot affect skeletons. Target validation includes immunity. Canceling, insufficient mana, and invalid targets consume neither mana nor time. A successful cast costs one turn. Sleep applied during the player's action prevents the target's action in that same monster phase, which counts as the first of three skipped actions.

Use one shared damage/death/reward path for melee and spells. A dead monster cannot act or award XP and gold a second time. Leveling, potions, equipment, and spells must preserve these rules as they are added.

### Chapter 9 checkpoint: A Little More Magic

`chapter9.py` adds six spells to the existing Magic Missile and Sleep. All eight have learnable scrolls in the ordinary loot pool. Wizards also unlock Sleep at level 2, Strength at 3, Fireball at 4, Summon Ally at 5, Teleport at 6, Charm Monster at 7, and Turn Undead at 8. Already-known spells do not duplicate. No automatic mana refill is added. Stat potions remain a separate 3% loot category; the ordinary pool now has eighteen entries, so each ordinary template is less frequent than in Chapter 8. Equipment magic rarity is unchanged.

| Spell | Mana | Range / duration | Effect |
| --- | ---: | --- | --- |
| Magic Missile | 2 | Range 6 | Existing 1d6 + 2 damage, no attack roll |
| Sleep | 3 | Range 5 / 3 actions | Existing sleep; damage wakes |
| Fireball | 5 | Range 6 / radius 1 | Shared 2d6 damage roll against all actors in the blast, including player and allies |
| Summon Ally | 5 | Adjacent spawn / 6 actions | One guardian with 12 HP, 1d6 damage, +2 to hit, AC 12 |
| Teleport | 4 | Anywhere in the floor interior | Random destination excludes actors and current tile, but includes walls; wall landing is fatal |
| Strength | 3 | Self / 10 monster phases | +3 melee damage, without changing permanent strength |
| Charm Monster | 4 | Range 5 / 5 actions | A susceptible living enemy fights for the player; player-inflicted damage breaks it |
| Turn Undead | 3 | Visible hostiles within range 6 / 4 actions | Undead flee; cornered undead lose the action rather than attack; no XP merely for turning |

Fireball uses a Manhattan-radius-one cross centered on an in-range hostile target. Walls exclude blast tiles through the shared visibility rules. The confirmation highlights affected tiles red and lists every victim; `y` commits, any other key cancels without cost. Fireball can kill its caster; resolve all blast damage before awarding rewards, and do not award XP or open level choices after the player dies. Spell damage never critically hits or fumbles.

Teleport always requires explicit `y` confirmation. Its prompt calculates and displays the exact percentage of eligible destinations that are walls. It can teleport through walls to another open area or kill the player inside stone; this risk is intentional. A fatal landing uses the normal death/score path and stops before monsters act. No occupied destination or current tile is chosen.

Strength refreshes a shorter duration to ten and refuses use at full duration. It adds damage, including to critical melee damage, but changes neither base stats nor gear. The counter ticks once after each committed action's monster phase, including activation, and the bonus disappears completely at expiry.

Summoning requires an empty cardinally adjacent floor tile and refuses a second living guardian. Guardians and charmed monsters use shared friendly AI, choose visible hostiles within eight tiles, and otherwise follow the player without sharing tiles. Hostiles can attack nearby allies. Allies act in the same monster phase as their creation; their action counters tick after their opportunity to act, including skipped sleeping actions. A guardian fades after its sixth opportunity and awards no treasure or XP. Charm ends after its fifth opportunity and the creature becomes hostile for its next action. Undead and sleep-immune targets resist charm. Player damage, including Fireball, immediately breaks charm; normal bump movement refuses to attack an ally. Allies remain on the current floor and are left behind upon descent.

Turn Undead affects hostile undead in range and line of sight, uses the explicit `undead` monster flag, and resets fear to four actions. It does not damage, kill, or award XP. Friendly/charmed actors are excluded from targeted spell menus; all targeted spells now filter to their own range and keep the single-target shortcut. Self spells skip target selection, while Fireball and Teleport still require their risk confirmation.

Monster XP is `base_xp + 2 * (depth - 1)`. HP, damage scaling, gold, and monster AC/accuracy otherwise retain existing values. Ally kills credit the player through the shared exactly-once reward path. Critical natural 20s double final physical melee damage, including strength, Strength-spell bonus, and weapon magic, for player and monsters. A natural 1 automatically misses and has a 50% chance to drop the player's equipped weapon during normal movement combat; no weapon is broken. Its sharpening and magic persist, its slot clears, and recovery and re-equipping cost their normal actions. This is part of the failed attack turn, not an additional drop turn. Monsters have no player-style equipment drops.

### Chapter 10 checkpoint: The Dungeon Store

`chapter10.py` builds on Chapter 9. A `Store` instance is created only on floors 1 and 5; floor 3 has no store. Breadth-first traversal from the starting room finds a connected, unoccupied walkable tile, excluding spawn, stairs, monsters, and loose items. Its tile is `$`, bright yellow, and remains walkable and transparent to spells. Store state is returned with the floor and persists until descent; reopening does not regenerate stock.

Walk onto the store tile to enter automatically after that movement turn's normal monster phase. Browsing and leaving are free. Press `b` while standing on the store to reopen it; pressing `b` elsewhere is a free refused action. Select `1`–`9` to inspect, Enter to buy, `n`/`p` for stock pages, and Escape to leave. Changing pages clears selection. One successful purchase closes the shop and commits one turn; surviving monsters and effect counters advance normally. The store is not a safe zone, and a player killed during entry never opens it.

Health Potions (8 gold) and Mana Potions (10) have unlimited purchase stock but still cost money and a free backpack slot. Each purchase creates a fresh carried item; it neither uses nor equips it. Floor 1 also offers three whetstones (12 each), one Iron Shield (20), one Long Sword (45), one Chain Armor (60), and one each of Magic Missile (30), Sleep (35), and Strength (45) scrolls.

Floor 5 has the same basic stock plus one each: Long Sword +1 (140), Battle Axe +1 (200), Chain Armor +1 (160), Iron Shield +1 (100), Fireball scroll (70), Summon Ally scroll (75), Potion of Constitution (120), and Potion of Intelligence (120). All finite quantities remain depleted after buying. Prices are initial playtesting values; there is no selling, credit, free starting gold, or free recovery.

Validate the offer index, remaining stock, affordability, and nine-slot inventory capacity before creating a purchase or deducting gold. Failures leave stock, gold, and inventory unchanged and cost no turn. Equipped gear continues to count toward capacity. Purchasing does not change class stats, spell knowledge, HP, or mana until the item is later used or equipped through the normal controls. Earlier checkpoints retain their original five-value floor result; Chapter 10 returns the Store as a sixth value.

### Deferred Appendix Ideas

- Difficulty settings: Easy, Medium, Hard and separate score comparisons. No implementation in the main chapters for now; these may move to book three.
- Occasional monster treasure drops: magical items and weapons can be part of a defeated monster's treasure. Preserve item ownership, sensible placement, rarity, and exactly-once rewards.
- Floor-five ranged guardian and relic: the guardian protects a wearable relic granting +3 AC specifically against attacks from undead. It is conditional protection, not +3 universal AC. Add a relic/accessory slot when implementing it and define which enemies count as undead. This encounter and optional recovery/escape objective belong in the appendix rather than Chapter 9.

### Chapter 9 Wizard spell growth

`spell_details` derives effects from a fresh copy of each spell definition. Wizard growth is `max(0, level - 1)`; other classes use zero. Magic Missile adds growth to its existing 1d6 + 2 damage and Fireball adds growth to 2d6. Sleep lasts `3 + growth // 2` actions, summons `6 + growth`, charm `5 + growth // 2`, and fear `4 + growth // 2`. Strength gives `3 + growth // 3` melee damage for `10 + growth` phases. Mana costs, range, guardian stats, and Teleport risk do not scale.

Spellbook descriptions, Fireball previews, validation, and casting use these derived values. Active durations and the Strength bonus are recorded at casting; later level-ups do not alter existing effects. Recasting uses current level and refreshes rather than stacks. Guardian status includes HP and remaining actions. HP death says "Your guardian is slain!"; duration expiry says "Your guardian's summoning expires."

Chapter 9 movement tie-break correction: choose randomly among equally good legal cardinal steps when chasing or fleeing. This restores the earlier horizontal/vertical variation lost in the first shared-AI refactor. It does not add diagonal steps or random hesitation; equal-speed pursuit can still maintain distance. The optional appendix behavior ideas remain separate.

### Chapter 9 intelligence-based mana growth

From chapter9.py onward, every class gains `max(1, 2 + (intelligence - 10) // 2)` current and maximum mana per earned level. INT 8–9 grants 1, 10–11 grants 2, 12–13 grants 3, 14–15 grants 4, 16–17 grants 5, and 18 grants 6. Calculate the gain before that level's stat choice and add it to the stored `level_mana_gained` total. Maximum mana is `6 + level_mana_gained + 2 * (intelligence - 10)`; current mana gains the same amount without refilling previous expenditure. Later intelligence increases do not recalculate past gains. Choosing intelligence or using its potion still adds 2 current and maximum mana immediately. The status and stat previews display next-level mana growth. Earlier chapter checkpoints retain their original mana rules.

### Chapter 11 checkpoint: Remembering Previous Levels

`chapter11.py` adds Floor and Dungeon classes. The manager lazily generates one Floor per depth and reuses it within the run. A Floor owns its name, map, rooms, surviving/dead monsters, loose items, entrance/upstairs and downstairs positions, and Store. Map changes, wounds, claimed rewards, item enhancements, collected/dropped loot, and limited shop stock remain on revisit. Memory is per run, not a disk save.

Use Enter while on `>` to descend or `<` to ascend. Walking onto stairs does not travel. Floor 1 has a reserved entry floor tile and no upstairs exit; deeper floors place `<` at their entry. Descending lands at the destination entry; ascending lands on the preceding floor's downstairs. One-room maps get distinct endpoints. Stair/entry tiles are player-walkable and spell-transparent. Initially spawned creatures and items on a landing are relocated to the nearest free ordinary floor tile, preserving their objects and rolled values rather than deleting them. Monster movement and summon placement exclude landings. Deliberately dropped items may stay there. Store tiles remain separate from arrivals and stairs.

Travel commits one destination-floor monster phase, not one on each floor. Noncurrent floors pause all creature positions, HP, and effect durations. Allies remain on their source floor with durations frozen until revisit. Player inventory, resources, and effects travel with the adventurer; player timers tick once after the active phase. No resource refill, enemy respawn, loot reroll, or finite-stock replenishment occurs on travel. Stores remain on floors 1 and 5 and keep their own state. The deepest depth is tracked separately and used in scores even after returning upstairs.

### Chapter 12 presentation

The graphical adapter is a main-book chapter: `chapter12.py` loads an isolated instance of `chapter11.py`, captures its printed menus into Pygame overlays, draws state in fixed panels, and supplies graphical input and missile animation. Chapter 11's source and turn rules remain unchanged. The earlier `dungeon_face.py` command is a compatibility launcher, and tests live in `test_chapter12.py`. The existing gold-frame preview and quick-start guide remain available. Chapter 14 is the closing essay and has no separate game script.


### Chapter 13 save-and-resume

`chapter13.py` reuses Chapter 11’s engine and optionally Chapter 12’s interface (`--graphics`). It writes versioned JSON to `saved_run.json` beside the script; `--save PATH` selects a different file. Both interfaces share a save. Run only one instance per save file. Earlier chapter launchers remain earlier checkpoints without disk persistence.

Save the initial state and every completed turn before the next dungeon prompt. Preserve all player fields, learned spells, current resources, recorded level gains, inventory, equipment references, enhancements, active effects, explored maps, rooms, creatures and timers, loot, stair positions, store stock, pending messages/shop entry, and random generator state. Derived combat and maximum resource properties are recomputed from their saved inputs. Inactive floors and closed programs do not advance effect timers.

Quit with `q` or close the graphical window to retain the most recent completed-turn checkpoint. Closing during an unfinished action restores its preceding completed state. Failed writes report an error and prevent a normal quit; forced closing can retain only the previous successful save. Use a temporary file and atomic replacement so a failed replacement preserves the previous save.

On startup, `c` continues a valid save; `n`, then `y`, requests replacement, which occurs after a new character is confirmed and reaches its first checkpoint. Canceling leaves the previous file unchanged. Invalid or incompatible saves are reported and left untouched. Reconstruct known item templates and preserve equipment identity using inventory indexes. Never load executable saved code.

Death deletes the resumable save before the usual death message and score handling, including fatal Teleport. Dead players cannot be saved. High scores remain separate. This supports normal permadeath but does not prevent manual file editing or copying.


### Room-generation retry budget

From Chapter 11 onward, `generate_rooms` treats `max_rooms` as a target number of accepted rooms. It permits up to `max_rooms * 50` placement attempts and stops when the target is reached. Overlapping candidates are rejected without reducing the target. The normal target remains ten rooms; crowded layouts may contain fewer. This changes newly generated floors, not saved or cached layouts. Per-room monster and item spawn chances remain unchanged.
