"""
Thin API entry point for the MMORPG server.
Creates Flask app and imports all routes.
"""

from flask import Flask, request, render_template
from flask_cors import CORS
from flask_socketio import SocketIO

# Create Flask app
app = Flask(__name__, template_folder='../templates')
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Set app and socketio in state module so routes can access them
from server.state import set_app, set_socketio
set_app(app)
set_socketio(socketio)

# Import all routes to register their Socket.IO handlers
from server.routes import (
    players, movement, inventory, equipment, combat,
    crafting, quests, world, discovery, reputation,
    entities, chat, admin
)

# Load world data
from server.routes.world import load_world_data
from server.state import load_all_npcs, load_all_quests, load_items_db
from engine.items import load_items as load_engine_items
load_world_data()
load_all_npcs()
load_all_quests()
load_items_db()
load_engine_items()

# Load resource nodes from map data
from server.state import resource_node_manager, WORLD_MAPS
from engine.crafting import create_resource_node
for map_id, map_data in WORLD_MAPS.items():
    for node_id, node in map_data.get('nodes', {}).items():
        for ent in node.get('entities', []):
            # Register resource nodes for gathering
            if ent in ('oak_tree', 'ash_tree', 'yew_tree', 'iron_deposit', 'copper_deposit', 'coal_deposit', 'resin_deposit', 'sap_deposit', 'spirit_bark_deposit'):
                rn = create_resource_node(
                    node_id=f"{ent}_{map_id}_{node_id}",
                    node_type=ent,
                    name=ent.replace('_', ' ').title(),
                    quantity=50,
                    respawn_time=100,
                    map_id=map_id,
                    node_location=node_id,
                )
                resource_node_manager.add_node(rn)
                print(f"[RESOURCE] Loaded {ent} at {map_id}/{node_id}")

# Initialize chronicle
from server.state import initialize_chronicle
initialize_chronicle()

# Import and start tick loop
from server.ticker import start_tick_loop
start_tick_loop()


@app.route('/')
def index():
    return render_template('index.html')


if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000)