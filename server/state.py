"""
Shared game state for the MMORPG server.
All global state lives here so routes can import it.
Pure state declarations and simple getters only.
Complex logic lives in server/npc_conversation.py, server/ticker.py, etc.
"""

import os
import json

# World data
WORLD_MAPS = {}
WORLD_ENTITIES = {}
WORLD_ENTRANCES = {}

# Canonical actor positions: exactly one {map_id, node_id} per actor
ACTOR_POSITIONS = {}

# Creature spawn system
CREATURE_TEMPLATES = {}      # template_id (e.g. "wolf") -> template data from data/actors/
CREATURE_INSTANCES = {}      # instance_id (e.g. "wolf_alpha") -> {template_id, spawn, ...}
CREATURE_RESPAWN_QUEUE = {}  # instance_id -> tick_number when respawn should occur
CREATURE_SPAWN_CONFIGS = {} # group_name -> list of spawn configs

# Player session management
player_sessions = {}  # sid -> player_id
player_states = {}    # player_id -> player state

# Game time
GAME_TIME_START_HOUR = 8
game_minutes = 0
tick_number = 0

# Command queues
pending_commands = {}  # player_id -> list of commands
conversation_memories = {}  # player_id -> {npc_id -> memory}

# Corpse/Loot System
corpses = {}  # actor_id -> {map_id, node_id, loot_table, display_name}

# Inspect System - track who is inspecting what
inspect_state = {}  # player_id -> {target_id: target_data}

# Creature death/respawn tracking
creature_death_times = {}  # instance_id -> tick_number when died

# Empty corpse cleanup tracking
empty_corpse_times = {}  # corpse_id -> tick_number when became empty

# Long Action Queue - manages gathering/crafting actions
from engine.long_action import ActionQueue, process_tick
long_action_queue = ActionQueue()

# NPC data cache
_npc_cache = {}

# Quest data cache
_quest_cache = {}

# Items database
_items_db = {}
_items_by_id = {}

# Resource Node Manager - single instance for the entire server
from engine.crafting import ResourceNodeManager, create_resource_node, create_station
resource_node_manager = ResourceNodeManager()

# Technique Manager - single instance for the entire server
from engine.technique_manager import TechniqueManager
technique_manager = TechniqueManager()
disciplines_engine = technique_manager  # alias for compatibility with command handlers

# Inventory Engine - single instance for the entire server
from engine.inventory import InventoryEngine
inventory_engine = InventoryEngine()

# Equipment Engine - single instance for the entire server
from engine.equipment import EquipmentEngine
equipment_engine = EquipmentEngine()

# Recipe Manager - single instance for the entire server
from engine.recipe_manager import RecipeManager
recipe_manager = RecipeManager()

# Material Familiarity Tracker - single instance for the entire server
from engine.crafting import MaterialFamiliarityTracker
familiarity_engine = MaterialFamiliarityTracker()

# Load recipe definitions from data/recipes/finished_crafting.json
def load_recipes():
    """Load all recipe definitions from the recipes directory."""
    recipes_dir = os.path.join('data', 'recipes')
    if os.path.exists(recipes_dir):
        for filename in os.listdir(recipes_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(recipes_dir, filename)
                with open(filepath, 'r') as f:
                    try:
                        data = json.load(f)
                        if isinstance(data, dict):
                            for category, category_data in data.items():
                                if not isinstance(category_data, dict):
                                    continue
                                # Handle nested structure: category -> {technique, station, recipes: {...}}
                                recipes_dict = category_data.get('recipes', category_data)
                                if isinstance(recipes_dict, dict):
                                    for recipe_id, recipe_data in recipes_dict.items():
                                        if isinstance(recipe_data, dict) and 'inputs' in recipe_data:
                                            # Normalize recipe data to canonical schema
                                            normalized = {
                                                "recipe_id": recipe_id,
                                                "name": recipe_data.get('name', recipe_id),
                                                "station_required": category_data.get('station', recipe_data.get('station', recipe_data.get('station_required', ''))),
                                                "technique_required": category_data.get('technique', recipe_data.get('technique', recipe_data.get('technique_required', 'crafting'))),
                                                "inputs": recipe_data.get('inputs', []),
                                                "outputs": recipe_data.get('outputs', []),
                                                "duration_ticks": recipe_data.get('duration_ticks', 5),
                                            }
                                            recipe_manager.register_recipe(normalized)
                    except Exception as e:
                        print(f"[RECIPES] Warning: Failed to load {filepath}: {e}")

load_recipes()

# AI components
from ai.npc_intent_detector import Layer1Interpreter
from ai.npc_response_generator import NPCResponseGenerator
intent_detector = Layer1Interpreter()
response_generator = NPCResponseGenerator()

# Flask app and SocketIO (will be set by api.py)
app = None
socketio = None


def set_app(flask_app):
    """Set the Flask app instance."""
    global app
    app = flask_app


def set_socketio(sio):
    """Set the SocketIO instance."""
    global socketio
    socketio = sio


def save_player_state(player_id):
    """Save player state to disk (data/players/<name>.json)."""
    import os, json
    global player_states, player_sessions
    state = player_states.get(player_id)
    if not state:
        return False
    # Strip legacy 'stats' field (game uses 'attributes' only)
    state.pop('stats', None)
    # Try to get the real character name from the session, not the session-based player_id
    char_name = state.get('name', player_id)
    # If name looks like a session ID (player_xxxxx), look up the character name from sessions
    if char_name.startswith('player_') or not char_name:
        for sid, sess in player_sessions.items():
            sess_pid = sess.get('player_id') if isinstance(sess, dict) else sess
            if sess_pid == player_id and isinstance(sess, dict):
                char_name = sess.get('character_name', char_name)
                break
    safe_name = char_name.lower().replace(' ', '_')
    filepath = os.path.join('data', 'players', f"{safe_name}.json")
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2)
        print(f"[SAVE] Player {char_name} saved to {filepath}")
        return True
    except Exception as e:
        print(f"[SAVE] Failed to save player {char_name}: {e}")
        return False


def get_player_state(player_id):
    """Get or create player state."""
    global player_states
    if player_id not in player_states:
        player_states[player_id] = {
            'name': player_id,  # Will be overwritten by character data on login
            'position': {'map_id': 'village', 'node_id': 'village_center'},
            'hp': 100, 'max_hp': 100, 'coins': 100,
            'inventory': [], 'equipment': {'weapon': None, 'armor': None, 'accessory': None},
            'skills': {}, 'quests': [], 'quest_notes': {}, 'journal': [], 'completed_quests': [],
            'discovery': {
                'visited_nodes': [],
                'known_actors': [],
                'known_entities': [],
                'known_locations': [],
                'location_positions': [],
            },
            'attributes': create_default_attributes(),
            'disciplines': {},
            'techniques': {},
            'reputation': {'actors': {}, 'factions': {}},
            'in_combat': False,
            'combat_target': None,
            'race': 'player'  # Add race for AI relationship checks
        }
    return player_states[player_id]


def get_game_time():
    """Get current game time string."""
    total_minutes = game_minutes
    hours = (GAME_TIME_START_HOUR + total_minutes // 60) % 24
    mins = total_minutes % 60
    return f"{hours:02d}:{mins:02d}"


def get_game_hour():
    """Get current game hour."""
    return (GAME_TIME_START_HOUR + game_minutes // 60) % 24


def get_time_of_day():
    """Get time of day string."""
    hour = get_game_hour()
    if 6 <= hour < 12:
        return "morning"
    elif 12 <= hour < 18:
        return "afternoon"
    elif 18 <= hour < 22:
        return "evening"
    else:
        return "night"


def get_node(map_id, node_id):
    """Get a node dict from WORLD_MAPS, or None."""
    if map_id in WORLD_MAPS and node_id in WORLD_MAPS[map_id].get('nodes', {}):
        return WORLD_MAPS[map_id]['nodes'][node_id]
    return None


def get_actors_at_position(map_id, node_id):
    """Get all actors at a specific map node."""
    alive_actors = []
    for actor_id, pos in ACTOR_POSITIONS.items():
        if pos['map_id'] == map_id and pos['node_id'] == node_id:
            if actor_id in creature_death_times:
                continue
            alive_actors.append(actor_id)
    return alive_actors


def get_actor_position(actor_id):
    """Get an actor's canonical {map_id, node_id} or None."""
    return ACTOR_POSITIONS.get(actor_id)


def move_actor_to(actor_id, map_id, node_id):
    """Move an actor to a new position."""
    if map_id not in WORLD_MAPS:
        return False, f"Unknown map: {map_id}"
    if node_id not in WORLD_MAPS[map_id]['nodes']:
        return False, f"Unknown node: {node_id}"
    ACTOR_POSITIONS[actor_id] = {'map_id': map_id, 'node_id': node_id}
    return True, "OK"


def _ensure_world_quests(npc_data):
    """Synthesize world.available_quests from quests.starts if missing."""
    quests = npc_data.get('quests', {})
    starts = quests.get('starts', [])
    world = npc_data.get('world', {})

    if not starts or 'available_quests' in world:
        return

    available = []
    for quest_id in starts:
        qd = get_quest_data(quest_id)
        if qd:
            q = {
                "id": qd.get('id', quest_id),
                "name": qd.get('title', 'Unknown Quest'),
                "description": qd.get('description', ''),
                "giver": qd.get('giver', ''),
                "prerequisites": qd.get('prerequisites', []),
                "steps": qd.get('steps', []),
                "completion_npc": qd.get('completion_npc', ''),
                "completion_topic": qd.get('completion_topic', ''),
                "keywords": qd.get('keywords', []),
                "rewards": qd.get('rewards', {})
            }
            available.append(q)

    if available:
        world['available_quests'] = available
        npc_data['world'] = world


def get_npc_data(npc_id_or_name):
    """Get NPC/actor data by ID or name."""
    global _npc_cache
    if not _npc_cache:
        load_all_npcs()
    key = npc_id_or_name.lower()
    for file_id, data in _npc_cache.items():
        if file_id.lower() == key or data.get('name', '').lower() == key:
            _ensure_world_quests(data)
            return data
    for instance_id, data in CREATURE_INSTANCES.items():
        if instance_id.lower() == key or data.get('name', '').lower() == key:
            _ensure_world_quests(data)
            return data
    return None


def get_quest_data(quest_id):
    """Get quest definition by ID."""
    global _quest_cache
    if not _quest_cache:
        load_all_quests()
    return _quest_cache.get(quest_id)


def is_actor_known(state, actor_id):
    """Check if player knows this actor's identity."""
    return actor_id in state['discovery']['known_actors']


def get_creature_display_name(actor_id, state):
    """Get display name for a creature."""
    if is_actor_known(state, actor_id):
        actor_data = get_npc_data(actor_id)
        return actor_data.get('name', actor_id) if actor_data else actor_id
    
    # Check CREATURE_INSTANCES first (new actor system)
    if actor_id in CREATURE_INSTANCES:
        instance_data = CREATURE_INSTANCES[actor_id]
        # Use the name directly from actor data (already formatted)
        return instance_data.get('name', actor_id.replace('_', ' ').title())
    
    actor_data = get_npc_data(actor_id)
    if not actor_data:
        return f"a stranger"
    
    species = actor_data.get('species', '').lower()
    conv = actor_data.get('conversation') or {}
    job = conv.get('job', '').lower()
    creature_type = species or job
    descriptor = actor_data.get('descriptor', '').lower()
    
    CREATURE_DESCRIPTOR_DISPLAY = {
        'wolf': {
            'feral': 'Feral Wolf', 'scarred': 'Scarred Wolf', 'young': 'Young Wolf',
            'old_grey': 'Old Grey Wolf', 'large_black': 'Large Black Wolf',
            'gray': 'Grey Wolf', 'white': 'White Wolf', 'black': 'Black Wolf',
            'scared': 'Scared Wolf', 'enraged': 'Enraged Wolf'
        },
        'goblin': {
            'one_eyed': 'One-Eyed Goblin', 'red_capped': 'Red-Capped Goblin',
            'crooked_nose': 'Crooked-Nose Goblin', 'snarling': 'Snarling Goblin',
            'chief': 'Goblin Chief', 'warrior': 'Goblin Warrior', 'scout': 'Goblin Scout'
        },
        'bear': {'massive_brown': 'Massive Brown Bear', 'scarred': 'Scarred Bear', 'young': 'Young Bear', 'shaggy': 'Shaggy Bear'},
    }
    
    if creature_type in CREATURE_DESCRIPTOR_DISPLAY and descriptor in CREATURE_DESCRIPTOR_DISPLAY[creature_type]:
        return CREATURE_DESCRIPTOR_DISPLAY[creature_type][descriptor]
    
    if species:
        return f"a {species}"
    if job:
        return f"a {job}"
    return f"a {actor_data.get('name', 'stranger').lower()}"


def get_actor_display_name(actor_id, state):
    """Get display name for an actor based on discovery status."""
    if is_actor_known(state, actor_id):
        actor_data = get_npc_data(actor_id)
        return actor_data.get('name', actor_id) if actor_data else actor_id
    else:
        actor_data = get_npc_data(actor_id)
        if actor_data:
            appearance = actor_data.get('appearance') or {}
            unknown_name = appearance.get('unknown_name', '')
            if unknown_name:
                return unknown_name
            world = actor_data.get('world') or {}
            job = world.get('job', '')
            if job:
                return f"a {job}"
            conv = actor_data.get('conversation') or {}
            job = conv.get('job', '')
            if job:
                return f"a {job}"
            species = actor_data.get('species', '')
            if species:
                return f"a {species}"
            return f"a {actor_data.get('name', 'stranger').lower()}"
        return f"a stranger"


def reveal_actor_identity(state, actor_id):
    """Explicitly reveal an actor's identity."""
    disc = state['discovery']
    if actor_id not in disc['known_actors']:
        disc['known_actors'].append(actor_id)
        return True
    return False


def discover_node(state, node_id):
    """Track node discovery."""
    disc = state['discovery']
    if node_id not in disc['visited_nodes']:
        disc['visited_nodes'].append(node_id)
        return True
    return False


def discover_actor(state, actor_id):
    """Track actor identity discovery."""
    disc = state['discovery']
    if actor_id not in disc['known_actors']:
        disc['known_actors'].append(actor_id)
        return True
    return False


def discover_entity(state, entity_id):
    """Track world entity discovery."""
    disc = state['discovery']
    if entity_id not in disc['known_entities']:
        disc['known_entities'].append(entity_id)
        return True
    return False


def discover_location(state, location_id):
    """Track location discovery."""
    disc = state['discovery']
    if location_id not in disc['known_locations']:
        disc['known_locations'].append(location_id)
        return True
    return False


def get_actor_reputation(player_state, actor_id):
    """Get reputation with an actor."""
    return player_state.get('reputation', {}).get('actors', {}).get(actor_id, 0)


def modify_actor_reputation(player_state, actor_id, amount):
    """Modify reputation with an actor."""
    if 'reputation' not in player_state:
        player_state['reputation'] = {'actors': {}, 'factions': {}}
    if 'actors' not in player_state['reputation']:
        player_state['reputation']['actors'] = {}
    player_state['reputation']['actors'][actor_id] = player_state['reputation']['actors'].get(actor_id, 0) + amount


def get_faction_reputation(player_state, faction_id):
    """Get reputation with a faction."""
    return player_state.get('reputation', {}).get('factions', {}).get(faction_id, 0)


def modify_faction_reputation(player_state, faction_id, amount):
    """Modify reputation with a faction."""
    if 'reputation' not in player_state:
        player_state['reputation'] = {'actors': {}, 'factions': {}}
    if 'factions' not in player_state['reputation']:
        player_state['reputation']['factions'] = {}
    player_state['reputation']['factions'][faction_id] = player_state['reputation']['factions'].get(faction_id, 0) + amount


def get_reputation_label(rep_value):
    """Get reputation label from value."""
    if rep_value >= 100:
        return "Allied"
    elif rep_value >= 50:
        return "Friendly"
    elif rep_value >= 10:
        return "Neutral"
    elif rep_value >= -10:
        return "Indifferent"
    elif rep_value >= -50:
        return "Unfriendly"
    else:
        return "Hostile"


def create_event(event_type, map_id, node_id, actors, data=None):
    """Create a game event."""
    pass


def get_events():
    """Get pending events."""
    return []


def process_new_events(events):
    """Process events through chronicle."""
    return 0


def get_chronicle_count():
    """Get total chronicle count."""
    return 0


def initialize_chronicle():
    """Initialize the chronicle system."""
    pass


def log_movement(map_id, node_id, player_id, from_map_id=None, from_node_id=None):
    """Log movement event."""
    pass


def log_quest_accept(map_id, node_id, player_id, quest_id, quest_name):
    """Log quest acceptance."""
    pass


def log_quest_complete(map_id, node_id, player_id, quest_id, quest_name):
    """Log quest completion."""
    pass


def log_conversation(map_id, node_id, player_id, npc_id, summary=''):
    """Log conversation event."""
    pass


def create_default_attributes():
    """Create default attributes dict."""
    return {
        "strength": 10, "dexterity": 10, "observation": 10, "constitution": 10,
        "willpower": 10, "reactiveness": 10, "arcana": 10, "knowledge": 10
    }


def get_full_item_details(item_name_or_shop_item):
    """Get full item details."""
    if isinstance(item_name_or_shop_item, dict):
        name = item_name_or_shop_item.get('name', '').lower()
    else:
        name = item_name_or_shop_item.lower()

    db_item = _items_db.get(name)
    if not db_item:
        for key, item in _items_db.items():
            if isinstance(item, dict) and item.get('name', '').lower() == name:
                db_item = item
                break

    if db_item:
        return db_item
    return item_name_or_shop_item


def load_items_db():
    """Load items database."""
    global _items_db, _items_by_id
    _items_db = {}
    _items_by_id = {}

    objects_dir = os.path.join('data', 'objects')
    if os.path.exists(objects_dir):
        for filename in os.listdir(objects_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(objects_dir, filename)
                with open(filepath, 'r') as f:
                    try:
                        data = json.load(f)
                        if isinstance(data, dict):
                            for category, items in data.items():
                                if isinstance(items, list):
                                    for item in items:
                                        if 'id' in item:
                                            _items_db[item['id']] = item
                                            _items_by_id[item['id']] = item
                                        if 'name' in item:
                                            _items_db[item['name'].lower()] = item
                    except Exception as e:
                        print(f"[ITEMS DB] Warning: Failed to load {filepath}: {e}")


def load_all_npcs():
    """Load all NPC/actor data."""
    global _npc_cache, CREATURE_INSTANCES, CREATURE_TEMPLATES, CREATURE_SPAWN_CONFIGS, ACTOR_POSITIONS

    _npc_cache = {}
    
    # Load from new data/world/actors/ directory (unified actor system)
    actors_dir = os.path.join('data', 'world', 'actors')
    if os.path.exists(actors_dir):
        for filename in os.listdir(actors_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(actors_dir, filename)
                with open(filepath, 'r') as f:
                    try:
                        actor_data_map = json.load(f)
                        actors_list = actor_data_map.get('actors', [])
                        for actor in actors_list:
                            instance_id = actor.get('id')
                            if not instance_id:
                                continue
                            
                            # Add to NPC cache
                            _npc_cache[instance_id] = actor
                            
                            # Add to CREATURE_INSTANCES for combat/respawn system
                            CREATURE_INSTANCES[instance_id] = actor
                            
                            # Handle schedule-based positioning (for NPCs with schedules)
                            schedule = actor.get('schedule', [])
                            current_hour = get_game_hour()
                            
                            # For max_distance: 0 NPCs, use first schedule entry as fixed position
                            if actor.get('max_distance', 3) == 0 and schedule:
                                first_schedule = schedule[0]
                                node_id = first_schedule.get('node_id')
                                map_id = first_schedule.get('map_id')
                                if node_id and map_id:
                                    ACTOR_POSITIONS[instance_id] = {'map_id': map_id, 'node_id': node_id}
                            elif schedule:
                                # Normal schedule-based movement for NPCs with max_distance > 0
                                for schedule_item in schedule:
                                    from_hour = schedule_item.get('from', 0)
                                    to_hour = schedule_item.get('to', 24)
                                    node_id = schedule_item.get('node_id')
                                    map_id = schedule_item.get('map_id')
                                    
                                    if from_hour < to_hour:
                                        in_schedule = from_hour <= current_hour < to_hour
                                    else:
                                        in_schedule = current_hour >= from_hour or current_hour < to_hour
                                    
                                    if in_schedule and node_id and map_id:
                                        ACTOR_POSITIONS[instance_id] = {'map_id': map_id, 'node_id': node_id}
                                        break
                            
                            # If no schedule matched, use spawn location
                            if instance_id not in ACTOR_POSITIONS:
                                spawn = actor.get('spawn', {})
                                spawn_map = spawn.get('map_id')
                                spawn_node = spawn.get('node_id')
                                if spawn_map and spawn_node:
                                    ACTOR_POSITIONS[instance_id] = {'map_id': spawn_map, 'node_id': spawn_node}
                                elif schedule:
                                    # Fallback: use first valid schedule position
                                    for sched_item in schedule:
                                        sched_node = sched_item.get('node_id')
                                        sched_map = sched_item.get('map_id')
                                        if sched_node and sched_map:
                                            ACTOR_POSITIONS[instance_id] = {'map_id': sched_map, 'node_id': sched_node}
                                            print(f"[POSITION] {instance_id} placed at {sched_map}/{sched_node} (schedule fallback)")
                                            break
                                elif schedule:
                                    # Fallback: use first valid schedule position
                                    for sched_item in schedule:
                                        sched_node = sched_item.get('node_id')
                                        sched_map = sched_item.get('map_id')
                                        if sched_node and sched_map:
                                            ACTOR_POSITIONS[instance_id] = {'map_id': sched_map, 'node_id': sched_node}
                                            print(f"[POSITION] {instance_id} placed at {sched_map}/{sched_node} (schedule fallback)")
                                            break
                            
                            # Inherit from template if specified
                            template_id = actor.get('template')
                            if template_id:
                                # Load template data
                                template_path = os.path.join('data', 'actors', f'{template_id}.json')
                                if os.path.exists(template_path):
                                    with open(template_path, 'r') as tf:
                                        try:
                                            template_data = json.load(tf)
                                            # Inherit from template only if not set or empty in actor
                                            for field in ['hp', 'max_hp', 'damage', 'loot', 'type', 'species', 'relationships', 'behaviors', 'attributes', 'techniques', 'world']:
                                                actor_has_field = field in actor
                                                actor_field_value = actor.get(field)
                                                field_is_empty = not actor_field_value if actor_has_field else True
                                                if actor_has_field and actor_field_value:
                                                    continue
                                                if field in template_data:
                                                    actor[field] = template_data[field]
                                        except Exception as e:
                                            print(f"[TEMPLATE] Warning: Failed to load template {template_path}: {e}")
                            
                            # Register creature techniques in technique manager (after template inheritance)
                            creature_techniques = actor.get('techniques', [])
                            if creature_techniques:
                                for tech_id in creature_techniques:
                                    if not technique_manager.has_technique(instance_id, tech_id):
                                        technique_manager.learn_technique(
                                            actor_id=instance_id,
                                            technique_id=tech_id,
                                            name=tech_id.replace('_', ' ').title(),
                                            discipline='creature_combat',
                                            lvl=1,
                                            tier='minor',
                                            category='active',
                                            description=f'Creature technique: {tech_id}',
                                            current_tick=0
                                        )
                    except Exception as e:
                        print(f"[NPC] Failed to load {filepath}: {e}")
    
    print(f"[NPC] Loaded {len(_npc_cache)} actors from data/world/actors/")


def load_all_quests():
    """Load all quest definitions (including subdirectories)."""
    global _quest_cache
    _quest_cache = {}
    quests_dir = os.path.join('data', 'quests')
    if os.path.exists(quests_dir):
        for root, dirs, files in os.walk(quests_dir):
            for filename in files:
                if filename.endswith('.json'):
                    filepath = os.path.join(root, filename)
                    with open(filepath, 'r') as f:
                        try:
                            data = json.load(f)
                            quest_id = data.get('id', filename.replace('.json', '').lower())
                            _quest_cache[quest_id] = data
                        except:
                            pass


def apply_quest_reputation_rewards(player_state, quest_data):
    """Apply reputation rewards from quest completion."""
    pass


def _update_quest_kill_progress(player_state, killed_actor_id, actor_data):
    """Update quest progress when creature is killed."""
    if not player_state:
        return

    killed_template = actor_data.get('spawn_template', killed_actor_id)
    killed_type = actor_data.get('type', '')
    killed_species = actor_data.get('species', '')

    kill_targets = [killed_template, killed_actor_id, killed_species]

    active_quests = player_state.get('quests', [])
    for quest in active_quests:
        if quest.get('status') != 'active':
            continue

        steps = quest.get('steps', [])
        for step in steps:
            if step.get('type') != 'kill':
                continue

            step_target = step.get('target', '').lower()
            step_count = step.get('count', 1)
            current_count = step.get('current', 0)

            target_matched = False
            for kill_target in kill_targets:
                if kill_target and kill_target.lower() == step_target:
                    target_matched = True
                    break

            if target_matched:
                step['current'] = current_count + 1
                print(f"[QUEST] Kill progress: {quest.get('name', '')} - {step.get('description', 'Kill')} ({step['current']}/{step_count})")