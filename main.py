import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server.api import app, socketio

def main():
    """Main entry point for the MMORPG game"""
    print("=" * 50)
    print("    Welcome to the Medieval Fantasy MMORPG")
    print("=" * 50)
    print()
    print("Game systems initialized.")
    print("Starting game server...")
    print()
    print("Server will run on http://localhost:5000")
    print("Press Ctrl+C to stop the server")
    print()
    
    try:
        socketio.run(app, debug=True, port=5000, allow_unsafe_werkzeug=True)
    except KeyboardInterrupt:
        print("\nShutting down...")
        sys.exit(0)

if __name__ == "__main__":
    main()