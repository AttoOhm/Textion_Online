# Textion Online MMORPG — New Player Guide

Welcome to the Textion Online MMORPG! This guide covers every game mechanic currently implemented. The game world is rich with NPCs, quests, combat, crafting, and exploration — but many of these systems are **not yet explained in-game**. Read this guide carefully before you start playing.

---

## TABLE OF CONTENTS

1. [Getting Started](#1-getting-started)
2. [Movement — Exploring the World](#2-movement--exploring-the-world)
3. [Entering and Exiting Locations](#3-entering-and-exiting-locations)
4. [Talking to NPCs](#4-talking-to-npcs)
5. [NPC Shops — Buying Items](#5-npc-shops--buying-items)
6. [Quests](#6-quests)
7. [Getting Information from NPCs](#7-getting-information-from-npcs)
8. [Combat — Fighting Enemies](#8-combat--fighting-enemies)
9. [Combat Techniques](#9-combat-techniques)
10. [Crafting](#10-crafting)
11. [Inventory & Equipment](#11-inventory--equipment)
12. [Full Command Reference](#12-full-command-reference)

---

## 1. Getting Started

The game is played entirely through **text commands** typed into the chat/terminal. There is no graphical interface.

**Basic flow:**
1. Start the game server
2. You begin in Oakhaven Village 
3. Type commands to move, talk to NPCs, attack enemies, craft items, inventory, ...

---

## 2. Movement — Exploring the World

The world is divided into **maps** (Overworld, Village, Goblin Camp, Dungeon). Each map contains **nodes** (locations). You move between nodes within a map.

### Command: `move <direction>`

```
move north
move to the forest edge
move eastern field
```

**How it works:**
- At any location, you can see available exits by looking around
- Each exit has a descriptive direction label (e.g., "northern field", "to the forest edge", "further in forest")
- Use `move` followed by the direction label to travel there
- The game will tell you what you discover at your new location

**Example:**
```
> move northern field
You travel north through the open fields...
You arrive at Farmlands. The golden wheat sways in the breeze.
```

### Key Locations

| Map | Notable Locations |
|-----|-------------------|
| **Overworld** | Oakhaven Gates, Forest Edge, Deep Forest, Farmlands, Open Hills, Dungeon Exterior, Goblin Camp Entrance |
| **Village** | Oakhaven (safe zone with NPCs, shops, quests) |
| **Goblin Camp** | Forest Path, various camp nodes (enemy territory) |

**Tip:** The world is large. Explore carefully and remember where key locations are.

---

## 3. Entering and Exiting Locations

Some special locations (villages, dungeons, camps) are **entrances** between maps. You cannot simply walk into them — you must use the `enter` or `exit` commands.

### Command: `enter`

Used to go **into** a village, dungeon, or camp from the Overworld.

```
enter village
enter goblin camp
enter dungeon
```

**Example:**
```
> enter village
You pass through the massive wooden gates of Oakhaven...
```

### Command: `exit` (or `exit to`)

Used to **leave** a village, dungeon, or camp back to the Overworld.

```
exit
exit to overworld
```

**Example:**
```
> exit
You walk through the gates and back out into the wilderness...
```

### Entrance Locations in the Overworld:

| Entrance | Found At | Leads To |
|----------|----------|----------|
| Oakhaven Main Gate | Oakhaven village entrance (Overworld) | Village |
| Goblin Camp | Deep Forest (node deep_forest_29) | Goblin Camp |
| Dungeon Entrance | Dungeon Exterior (Overworld) | Dungeon |

**Important:** Be prepared before entering dungeons or the goblin camp — they contain enemies!

---

## 4. Talking to NPCs

Talking to NPCs is one of the most important things you can do. NPCs offer quests, sell items, share information, and sometimes train you.

### Command: `talk to <npc name>`

```
talk to aldric
talk to merchant
talk to grim
```

**How it works:**
1. Type `talk to <npc>` to start a conversation
2. Speak **naturally** — the game understands natural language via an AI system
3. You can ask about topics, request quests, browse shops, or just chat
4. To end a conversation, say goodbye

### What You Can Do in Conversations:

| Intent | How to Say It |
|--------|---------------|
| Greet | "Hello", "Hi", "Greetings" |
| Browse shop | "What do you sell?", "Show me your wares", "I'd like to browse" |
| Buy something | "I'll buy the iron sword", "I want to purchase the healing potion" |
| Ask about price | "How much is X?", "What's the price of Y?" |
| Ask for quests | "Do you have any work?", "Any quests for me?", "What needs doing?" |
| Ask for information | "Tell me about X", "What do you know about Y?", "Who is Z?" |
| Complete a quest | Talk about the quest topic to the right NPC |
| Ask for training | "Can you train me?", "Teach me techniques" |
| Ask for healing | "Can you heal me?", "I need treatment" |
| Say farewell | "Goodbye", "Farewell", "I'll be going" |

**Example Conversation:**
```
> talk to aldric
You approach Aldric the Swordmaster.
Aldric: "Hail, traveler. Looking to learn the blade?"

> what do you sell?
Aldric shows you his wares: [list of items with prices]

> i'll buy the iron sword
You purchase the Iron Sword for 50 gold.

> any quests for me?
Aldric: "I could use some help. Goblins have been raiding the outskirts..."
```

**Important Tips:**
- NPCs have **limited knowledge** — not every NPC knows everything
- NPCs have **personalities** — some are friendly, some are gruff
- The conversation system uses an AI, so be patient with responses
- Some NPCs offer training in techniques (combat abilities)

---

## 5. NPC Shops — Buying Items

Many NPCs are merchants who sell items. You interact with shops through conversation.

### Browsing a Shop

In conversation with a merchant NPC:

```
browse
what do you have for sale?
show me your wares
```

The NPC will list their items with prices.

### Buying Items

```
i'll buy <item name>
i want to buy <item name>
i'll take <item name>
```

The game checks if you have enough gold and processes the purchase.

### Asking About Prices

```
how much is <item name>?
what's the price of <item name>?
```

### Current Shop Limitations:
- NPCs do **not** buy items from you
- Each NPC has a fixed inventory
- Prices are fixed

---

## 6. Quests

Quests are tasks given by NPCs. They are a core progression system.

### Getting a Quest

Talk to an NPC and ask about quests or work:

```
any quests for me?
do you have any work?
what needs doing?
```

The NPC will offer available quests. You can accept or decline.

### Accepting a Quest

When offered a quest, say:

```
yes, i'll do it
i accept
i'll help
```

### Checking Your Quests

```
quests
```

Shows your active quests.

### Completing a Quest

Quests are completed by **talking to the right NPC about the right topic**.

- Check the quest description for clues
- Go to the NPC mentioned in the quest
- Talk to them about the quest's main topic

Example: If a quest says "Talk to Aldric about the goblin threat", you would:
```
> talk to aldric
> I have information about the goblin threat
```

### Quest Rewards

Completed quests grant rewards (gold, items, experience).

### Quest Prerequisites

Some quests require **completing other quests first** before they become available.

---

## 7. Getting Information from NPCs

NPCs have knowledge about the world. You can ask them questions.

### Command: `ask about <topic>` (during conversation)

Simply ask naturally during conversation:

```
tell me about the goblins
what do you know about the dungeon?
who is the village elder?
where can I find iron ore?
```

Topics NPCs might know about:
- Locations (dungeon, forest, goblin camp, etc.)
- People (other NPCs, enemies)
- Creatures (wolves, goblins, etc.)
- Items and materials
- History and lore
- Quests and rumors

**Tip:** If an NPC doesn't know something, try asking a different NPC.

---

## 8. Combat — Fighting Enemies

Combat is turn-based and uses the **attack** command. Attacks take 1 tick (moment of time) to execute.

### Command: `attack <target>`

```
attack goblin
attack wolf
attack bandit
```

**How combat works:**
1. You type `attack <target>` to start an attack
2. The attack takes 1 tick to resolve
3. The result depends on your weapon, attributes, and the target's defenses
4. Damage types include: slashing, piercing, bludgeoning, heat, cold, and more

### Weapon Attack Profiles

| Weapon | Base Damage | Damage Type | Attributes Used |
|--------|-------------|-------------|-----------------|
| Unarmed | 3 | Bludgeoning | Strength (100%) |
| Sword | 6 | Slashing | Strength (60%), Dexterity (40%) |
| Dagger | More | Piercing | Dexterity (mostly) |
| Axe | More | Slashing | Strength (mostly) |
| Hammer | More | Bludgeoning | Strength (mostly) |
| Bow | Ranged | Piercing | Dexterity |
| (and more) | | | |

### HP and States

- **Default HP:** 100
- **Downed:** When HP reaches 0, you are downed
- **Dead:** When HP falls below -50, you die
- **HP States:** Unharmed, Scratched, Wounded, Severely Wounded, Near Death, Downed, Dead

### Combat Effects

Some attacks and techniques apply effects:
- **Stunned** — Cannot attack while stunned
- **Death Mark** — Marked for increased damage
- **Taunt** — Forced to focus on the taunter

### Combat Groups (Engagement Graph)

Combat in this game uses an **Engagement Graph** system. When you melee-attack an enemy, both of you become **engaged** — linked together in a combat group. This system creates strategic depth in multi-enemy fights.

**How combat groups work:**
- Attacking an enemy with a **melee** attack creates an engagement link between you and that enemy
- All actors connected through engagement links form a single **combat group**
- Ranged attacks (bows) **cannot** target members of your own combat group — you can't shoot someone you're engaged with in melee
- Being in a combat group means you are actively fighting and cannot simply walk away without consequences

### Commands for Combat Groups

| Command | Description |
|---------|-------------|
| `join <group>` | Join an existing combat group (engage with an ongoing fight) |
| `leave` | Leave your current combat group (disengage from combat) |
| `hide` | Attempt to hide — removes you from engagement, making you undetected by enemies |

**Strategic implications:**
- **Melee fighters** build engagement links, locking themselves in combat
- **Ranged fighters** can attack from outside the group but cannot shoot into their own engaged melee
- If you're outnumbered, you can **disengage** by leaving the group, but enemies may pursue
- The `hide` command lets you break engagement and escape from enemies who were fighting you

### Important Combat Notes:
- You cannot attack while **stunned**
- You cannot attack while **downed** (HP ≤ 0)
- You cannot attack a target that is already downed
- Your equipped weapon determines your attack profile
- Each time you are targeted by an attack, your **attack pressure** increases (tracks how many times you've been attacked)

---

## 9. Combat Techniques

Techniques are **special combat abilities** that go beyond basic attacks. They are learned from NPC trainers.

### Available Technique Disciplines

| Discipline | Focus | Example Techniques |
|------------|-------|-------------------|
| **Sword Art** | Melee sword combat | Draw Cut, Riposte, Sword Dance, Perfect Cut, Whirlwind |
| **Hunter** | Ranged/tracking | Death Mark, Track Prey, Bear Trap, Silent Step, Loot |
| **Warrior** | Defense/shields | Shield Bash, Power Strike, Alert |
| **Light God's Art** | Holy magic | Bless, Purify, Divine Shield, Holy Light, Resurrection |
| **Dark God's Art** | Dark magic | (various dark techniques) |
| **Arcane Art** | Arcane magic | (Arcane Sight, Mana Shield) |

### Creature Techniques

Enemies have their own techniques:
- **Goblins:** Short Bow Shot, Melee Attack, Crunch, Double Attack
- **Wolves:** Bite, Claw, Howl

### Using Techniques

```
use <technique> on <target>
```

Example:
```
use shield_bash on goblin
use riposte on wolf
```

### Learning Techniques

Talk to NPC trainers and ask about training:
```
can you train me?
teach me techniques
```

Different NPCs teach different disciplines. For example, Aldric the Swordmaster teaches Sword Art techniques.

---

## 10. Crafting

Crafting allows you to create items from raw materials. It is **deterministic** — if you have the right materials and a suitable station, it always succeeds.

### Crafting Stations

Different recipes require different stations:

| Station | Purpose |
|---------|---------|
| **Furnace** | Smelting ores into ingots |
| **Anvil** | Forging metal items (weapons, armor) |
| **Workbench** | Woodworking, general crafting |
| **Saw Table** | Cutting wood into planks |
| **Mortar & Pestle** | Grinding materials, alchemy |
| **Cauldron** | Brewing potions |

### Resource Gathering

Resource nodes are found in the world:
- **Iron Deposits** — Mined for iron ore
- **Copper Deposits** — Mined for copper ore
- **Oak Trees** — Cut for wood
- **Berry Bushes** — Picked for berries
- **(and more depending on location)**

```
gather <resource>     (if this command is available)
```

Resource nodes have limited quantity and **respawn** after a set number of ticks.

### Crafting Process

1. **Learn a recipe** — Recipes can be bought from NPCs or learned
2. **Get materials** — Gather or buy the required materials
3. **Find the right station** — Go to a node that has the station you need
4. **Craft the item** — Use the `craft` command (or similar)

### Material Familiarity

As you craft finished items from a specific material, you gain **familiarity** with that material. (This system is tracked but not yet used for quality bonuses — this is a future feature.)

---

## 11. Inventory & Equipment

### Checking Inventory

```
inventory
```

Shows all items you are carrying, including gold.

### Equipment

```
equip <item>          — Equip a weapon, armor, or accessory
unequip <item>        — Unequip an item
```

Equipping weapons changes your attack profile in combat.

### Item Management

| Command | Purpose |
|---------|---------|
| `take <item>` | Pick up an item from the ground |
| `drop <item>` | Drop an item from your inventory |
| `give <item> to <npc>` | Give an item to an NPC (sometimes used for quests) |
| `use <item>` | Use a consumable item (potions, etc.) |
| `drink <potion>` | Drink a potion |
| `inspect <item>` | Examine an item closely |
| `put <item> in <container>` | Store items in containers |
| `reload quiver` | Reload your quiver with arrows |

### Gold

Gold/coins are your currency. Earn them from quests or other activities. Spend them at NPC shops.

---

## 12. Full Command Reference

### Movement & Exploration

| Command | Description |
|---------|-------------|
| `move <direction>` | Travel to an adjacent node in the current map |
| `enter <location>` | Enter a village, dungeon, or camp |
| `exit` or `exit to <place>` | Leave a location and return to the overworld |
| `look` | Look at your surroundings |
| `inspect <target>` | Inspect an object, NPC, or location |

### NPC Interaction

| Command | Description |
|---------|-------------|
| `talk to <npc>` | Start a conversation with an NPC |
| *(during conversation)* `ask about <topic>` | Ask an NPC for information |
| *(during conversation)* `browse` | Browse an NPC's shop |
| *(during conversation)* `buy <item>` | Purchase an item from an NPC |

### Combat

| Command | Description |
|---------|-------------|
| `attack <target>` | Attack an enemy (takes 1 tick) |
| `use <technique> on <target>` | Use a learned combat technique |
| `join <group>` | Join a combat group (engage in an ongoing fight) |
| `leave` | Leave your current combat group (disengage) |
| `hide` | Attempt to hide — break engagement and become undetected |

### Inventory & Items

| Command | Description |
|---------|-------------|
| `inventory` | Check your inventory |
| `equip <item>` | Equip a weapon or armor |
| `unequip <item>` | Unequip an item |
| `take <item>` | Pick up an item |
| `drop <item>` | Drop an item |
| `give <item> to <npc>` | Give an item to an NPC |
| `use <item>` | Use a consumable item |
| `drink <potion>` | Drink a potion |
| `reload quiver` | Reload ranged ammo |
| `put <item> in <container>` | Store an item |

### Systems

| Commands | Description |
|----------|-------------|
| `quests` | Check your active quests |
| `craft` | Craft items (if at a station with materials) |
| `gather` | Gather from resource nodes (if implemented as direct command) |

---

## Quick Tips for New Players

1. **Talk to everyone** — NPCs are your main source of quests, information, and gear
2. **Start in Oakhaven Village** — The village is safe and has multiple NPCs to interact with
3. **Be prepared before exploring** — The Overworld has wolves and other dangers
4. **Save your gold** — Better equipment costs more, and some recipes must be bought
5. **Complete quests** — Quests give rewards and unlock more quests
6. **Equip weapons** — Your unarmed attack is weak; find or buy a weapon
7. **Learn techniques** — Trainers can teach you powerful combat abilities
8. **Watch your HP** — If you get downed (HP ≤ 0), you need healing
9. **Use natural language** — The conversation AI understands plain English; speak naturally
10. **Explore carefully** — The goblin camp and dungeon are dangerous; don't rush in

Good luck, adventurer!
