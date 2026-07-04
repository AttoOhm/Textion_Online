"""
Recipe Manager (Phase 7A)

Manages recipe knowledge for all actors.

This is the runtime store of which recipes each actor knows.
No content is pre-loaded. Content will be added in Phase 7C.

Reuses existing systems:
- Disciplines (engine/disciplines.py)
"""

import time
from typing import Optional, Dict, List, Any, Set

# ============ CONSTANTS ============

# Crafting event types
EVENT_RECIPE_LEARNED = "recipe_learned"
EVENT_RECIPE_FORGOTTEN = "recipe_forgotten"

# Station types (shared with crafting.py)
STATION_FURNACE = "furnace"
STATION_SAW_TABLE = "saw_table"
STATION_MORTAR = "mortar"
STATION_ANVIL = "anvil"
STATION_WORKBENCH = "workbench"
STATION_CAULDRON = "cauldron"

VALID_STATION_TYPES = [
    STATION_FURNACE,
    STATION_SAW_TABLE,
    STATION_MORTAR,
    STATION_ANVIL,
    STATION_WORKBENCH,
    STATION_CAULDRON,
]

# Default values
DEFAULT_RECIPE_DURATION_TICKS = 5


# ============ RECIPE KNOWLEDGE ============


def create_recipe_knowledge(
    recipe_id: str,
    name: str = "",
    station_required: str = "",
    technique_required: str = "",
    inputs: Optional[List[Dict[str, Any]]] = None,
    outputs: Optional[List[Dict[str, Any]]] = None,
    duration_ticks: int = DEFAULT_RECIPE_DURATION_TICKS,
) -> Dict[str, Any]:
    """Create a canonical recipe knowledge entry.

    Args:
        recipe_id: Unique identifier for the recipe
        name: Human-readable recipe name
        station_required: Station type required (e.g., "furnace")
        technique_required: Discipline technique required (e.g., "smelting")
        inputs: List of input requirements [{"item_id": str, "quantity": int}, ...]
        outputs: List of output results [{"item_id": str, "quantity": int}, ...]
        duration_ticks: Base duration in ticks

    Returns:
        Dict representing the recipe definition
    """
    return {
        "recipe_id": recipe_id,
        "name": name or recipe_id,
        "station_required": station_required,
        "technique_required": technique_required,
        "inputs": inputs or [],
        "outputs": outputs or [],
        "duration_ticks": duration_ticks,
    }


def validate_recipe_knowledge(recipe: Dict[str, Any]) -> List[str]:
    """Validate a recipe knowledge entry. Returns list of errors (empty = valid)."""
    errors = []
    required = ["recipe_id", "name", "station_required", "technique_required", "inputs", "outputs", "duration_ticks"]
    for field in required:
        if field not in recipe:
            errors.append(f"Missing required field: {field}")

    if recipe.get("duration_ticks", 0) < 1:
        errors.append("duration_ticks must be >= 1")

    if recipe.get("station_required") and recipe["station_required"] not in VALID_STATION_TYPES:
        errors.append(f"Unknown station type: {recipe['station_required']}")

    return errors


class RecipeManager:
    """Manages recipe knowledge for all actors.

    This is the runtime store of which recipes each actor knows.
    No content is pre-loaded. Content will be added in Phase 7C.
    """

    def __init__(self):
        # recipe_id -> recipe definition
        self._recipe_definitions: Dict[str, Dict[str, Any]] = {}
        # actor_id -> set of recipe_ids
        self._actor_known_recipes: Dict[str, Set[str]] = {}
        self._events: List[Dict[str, Any]] = []

    # ============ DEFINITION MANAGEMENT ============

    def register_recipe(self, recipe: Dict[str, Any]) -> bool:
        """Register a recipe definition.

        Args:
            recipe: Recipe knowledge dict

        Returns:
            True if registered, False if validation fails
        """
        errors = validate_recipe_knowledge(recipe)
        if errors:
            return False

        self._recipe_definitions[recipe["recipe_id"]] = recipe
        return True

    def get_recipe_definition(self, recipe_id: str) -> Optional[Dict[str, Any]]:
        """Get a recipe definition by ID.

        Args:
            recipe_id: Recipe identifier

        Returns:
            Recipe definition dict or None
        """
        return self._recipe_definitions.get(recipe_id)
    
    def get_recipe(self, recipe_id: str) -> Optional[Dict[str, Any]]:
        """Get a recipe definition by ID (alias for get_recipe_definition).

        Args:
            recipe_id: Recipe identifier

        Returns:
            Recipe definition dict or None
        """
        return self.get_recipe_definition(recipe_id)

    def has_recipe_definition(self, recipe_id: str) -> bool:
        """Check if a recipe definition exists.

        Args:
            recipe_id: Recipe identifier

        Returns:
            True if recipe is registered
        """
        return recipe_id in self._recipe_definitions

    def get_all_recipe_definitions(self) -> List[Dict[str, Any]]:
        """Get all registered recipe definitions.

        Returns:
            List of recipe definition dicts
        """
        return list(self._recipe_definitions.values())

    # ============ ACTOR KNOWLEDGE ============

    def learn_recipe(self, actor_id: str, recipe_id: str) -> bool:
        """Teach an actor a recipe.

        Args:
            actor_id: Actor to teach
            recipe_id: Recipe to learn

        Returns:
            True if learned, False if recipe does not exist or already known
        """
        if recipe_id not in self._recipe_definitions:
            return False

        if actor_id not in self._actor_known_recipes:
            self._actor_known_recipes[actor_id] = set()

        if recipe_id in self._actor_known_recipes[actor_id]:
            return False  # Already known

        self._actor_known_recipes[actor_id].add(recipe_id)
        self._generate_event(EVENT_RECIPE_LEARNED, actor_id, recipe_id)
        return True

    def forget_recipe(self, actor_id: str, recipe_id: str) -> bool:
        """Make an actor forget a recipe.

        Args:
            actor_id: Actor to modify
            recipe_id: Recipe to forget

        Returns:
            True if forgotten, False if not known
        """
        if actor_id not in self._actor_known_recipes:
            return False

        if recipe_id not in self._actor_known_recipes[actor_id]:
            return False

        self._actor_known_recipes[actor_id].discard(recipe_id)
        self._generate_event(EVENT_RECIPE_FORGOTTEN, actor_id, recipe_id)
        return True

    def knows_recipe(self, actor_id: str, recipe_id: str) -> bool:
        """Check if an actor knows a recipe.

        Args:
            actor_id: Actor to check
            recipe_id: Recipe to check

        Returns:
            True if actor knows the recipe
        """
        if actor_id not in self._actor_known_recipes:
            return False
        return recipe_id in self._actor_known_recipes[actor_id]

    def get_known_recipes(self, actor_id: str) -> List[Dict[str, Any]]:
        """Get all recipes an actor knows.

        Args:
            actor_id: Actor to query

        Returns:
            List of recipe definition dicts known by the actor
        """
        known_ids = self._actor_known_recipes.get(actor_id, set())
        return [self._recipe_definitions[rid] for rid in known_ids if rid in self._recipe_definitions]

    def get_known_recipe_ids(self, actor_id: str) -> Set[str]:
        """Get the set of recipe IDs an actor knows.

        Args:
            actor_id: Actor to query

        Returns:
            Set of recipe IDs
        """
        return self._actor_known_recipes.get(actor_id, set())

    # ============ EVENTS ============

    def get_events(self) -> List[Dict[str, Any]]:
        """Get all generated events."""
        return list(self._events)

    def clear_events(self):
        """Clear all events."""
        self._events.clear()

    def _generate_event(self, event_type: str, actor_id: str, recipe_id: str):
        """Generate an event for a recipe knowledge change."""
        event = {
            "event_type": event_type,
            "actor_id": actor_id,
            "recipe_id": recipe_id,
            "timestamp": time.time(),
        }
        self._events.append(event)