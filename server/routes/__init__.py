"""
Route registration for the MMORPG server.
Import all route modules to register their Socket.IO handlers.
"""

from server.state import socketio

# Import all route modules to register their handlers
from server.routes import players
from server.routes import movement
from server.routes import inventory
from server.routes import equipment
from server.routes import combat
from server.routes import crafting
from server.routes import quests
from server.routes import world
from server.routes import discovery
from server.routes import reputation
from server.routes import entities
from server.routes import chat
from server.routes import admin
from server.routes import auth