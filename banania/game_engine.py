import random
import json
import os
from .entities import (
    Player,
    PurpleMonster,
    GreenMonster,
    LightBlock,
    HeavyBlock,
    PinnedBlock,
    Banana,
    Key,
    Door,
    Empty,
    Dummy,
    Vec,
    Monster,
    Block,
    Character,
)
from . import config
from .config import ErrorCode, ImageID  # Import ErrorCode and ImageID

# Create a directory for saves if it doesn't exist
SAVE_DIR = "saves"
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)


class SaveGameManager:
    def __init__(self):
        self.save_name = None
        self.reached_level = 1
        self.arr_steps = {i: 0 for i in range(1, 51)}
        self.progressed = (
            False  # This flag indicates if there's new progress to save
        )

    def get_save_path(self, save_name):
        """Constructs the full path for a save file."""
        # Sanitize filename to prevent directory traversal issues
        safe_filename = "".join(
            c for c in save_name if c.isalnum() or c in (" ", "_", "-")
        ).rstrip()
        return os.path.join(SAVE_DIR, f"{safe_filename}.json")

    def save_game(self, save_name):
        """Saves the current game state to a JSON file, overwriting if it exists."""
        if not save_name:
            return False

        self.save_name = save_name

        data = {
            "save_name": self.save_name,
            "reached_level": self.reached_level,
            "arr_steps": self.arr_steps,
        }

        filepath = self.get_save_path(save_name)
        try:
            with open(filepath, "w") as f:
                json.dump(data, f, indent=4)
            self.progressed = False
            return True
        except IOError as e:
            return False

    def load_game(self, save_name):
        """Loads game state from a JSON file."""
        if not save_name:
            return False

        filepath = self.get_save_path(save_name)
        try:
            with open(filepath, "r") as f:
                data = json.load(f)

            self.save_name = data.get("save_name", save_name)
            self.reached_level = data.get("reached_level", 1)
            self.arr_steps = {
                int(k): v for k, v in data.get("arr_steps", {}).items()
            }
            return True
        except FileNotFoundError:
            return False
        except (json.JSONDecodeError, KeyError) as e:
            return False


class Game:
    """
    Manages the core game logic, state, and entity interactions.
    This is the Python equivalent of the JavaScript `CLASS_game`.
    """

    def __init__(self, level_data, audio_manager):
        # --- Game State ---
        self.is_paused = False
        self.is_initialized = False
        self.wait_timer = config.INTRO_DURATION * config.UPS
        self.mode = 0  # CHANGED: Was 'entry'. 0=Title, 1=Game, 2=End
        self.level_ended = 0  # 0: ongoing, 1: won, 2: lost

        # --- Level Data ---
        self.external_level_data = level_data  # From EXTERNAL_LEVELS
        self.level_number = 1
        self.level_array = []  # The 2D grid of entity objects
        self.berti_positions = []  # Quick access to player objects it has only one element which is the player object

        # --- Player & Level Stats ---
        self.steps_taken = 0
        self.num_bananas = 0
        self.bananas_remaining = 0

        # --- Input & Timing ---
        self.single_steps = False
        self.last_dir_pressed = config.Direction.NONE
        self.update_tick = 0
        self.move_speed = round(1 * 60 / config.UPS)
        self.door_removal_delay = round(8 * config.UPS / 60)

        # --- Systems ---
        self.audio_manager = audio_manager
        self.save_manager = SaveGameManager()
        self.completed_moves = []

        # --- Turn-Based Mode ---
        self.turn_based = False
        self.tb_state = "WAITING_PLAYER"  # WAITING_PLAYER | ANIMATING_PLAYER | ANIMATING_MONSTER
        self.tb_current_monster_index = 0
        self.tb_monsters = []  # Ordered list of monster references for current round
        self.tb_turn_orders = {}  # Maps id(entity) -> turn order number

    def update(self, input_handler):
        """
        The main logic update, called once per frame from your main game loop.
        Equivalent to the global `update` and `update_entities` functions in JS.
        """
        if (
            self.mode != 1
        ):  # Mode 1 is the active game mode. 0 is Title, 2 is End.
            return
        if self.is_paused:
            return

        if self.wait_timer > 0:
            self.wait_timer -= 1
            return

        if self.turn_based:
            self.update_turn_based(input_handler)
            return

        if self.level_ended != 0:
            if self.level_ended == 1:  # Won
                self.next_level()
            elif self.level_ended == 2:  # Lost
                self.reset_level()
            return

        self.update_tick += 1

        synced_move = (self.update_tick * 60 / config.UPS) % (
            12 / self.move_speed
        ) == 0

        # --- Handle Inputs and AI Decisions FIRST ---
        stale_positions = []
        for berti_pos in self.berti_positions:
            entity = self.level_array[berti_pos.x][berti_pos.y]
            if isinstance(entity, Player):
                entity.handle_input(self, input_handler, self.single_steps)
            else:
                stale_positions.append(berti_pos)

        if stale_positions:
            self.berti_positions = [
                p for p in self.berti_positions if p not in stale_positions
            ]

        for y in range(config.LEV_DIMENSION_Y):
            for x in range(config.LEV_DIMENSION_X):
                entity = self.level_array[x][y]
                if synced_move and isinstance(
                    entity, (PurpleMonster, GreenMonster)
                ):
                    entity.update_ai(self)

        # --- THEN, update ALL entity states and COLLECT completed moves ---
        self.completed_moves.clear()
        for y in range(config.LEV_DIMENSION_Y):
            for x in range(config.LEV_DIMENSION_X):
                entity = self.level_array[x][y]
                entity.just_moved = False
                entity.update(self)

        # --- NOW, process all collected moves at once ---
        if self.completed_moves:
            # Create a copy of the list, as the original will be cleared on the next tick.
            entities_that_just_moved = self.completed_moves[:]

            # First, finalize the completed moves in the grid.
            # This sets their is_moving flag to False.
            self._process_completed_moves(entities_that_just_moved)

            if self.level_ended != 0:
                return

            # NOW, immediately re-evaluate the entities that just finished moving.
            # This allows them to start a new move in the same tick, preventing a flicker.
            for entity in entities_that_just_moved:
                # Sanity check: ensure the entity is still where it should be.
                if self.level_array[entity.x][entity.y] != entity:
                    continue

                # If it's a player, handle input again.
                if isinstance(entity, Player) and not self.single_steps:
                    entity.handle_input(self, input_handler, self.single_steps)
                
                # If it's a monster, run its AI again.
                elif isinstance(entity, (PurpleMonster, GreenMonster)):
                    entity.update_ai(self)

        # --- FINALLY, check for game over conditions ---
        for berti_pos in self.berti_positions:
            player = self.level_array[berti_pos.x][berti_pos.y]
            if isinstance(player, Player):
                player.check_enemy_proximity(self)

    def update_turn_based(self, input_handler):
        """
        Turn-based update loop. Called from update() when turn_based is True.
        Uses a state machine: WAITING_PLAYER -> ANIMATING_PLAYER -> ANIMATING_MONSTER -> WAITING_PLAYER
        """
        if self.level_ended != 0:
            if self.level_ended == 1:
                self.next_level()
            elif self.level_ended == 2:
                self.reset_level()
            return

        # Tick all entity visual tweens every frame regardless of state
        self.completed_moves.clear()
        for y in range(config.LEV_DIMENSION_Y):
            for x in range(config.LEV_DIMENSION_X):
                entity = self.level_array[x][y]
                entity.just_moved = False
                entity.update(self)

        # Process any moves that completed this tick
        if self.completed_moves:
            entities_that_just_moved = self.completed_moves[:]
            self._process_completed_moves(entities_that_just_moved)
            if self.level_ended != 0:
                return

            if self.tb_state == "ANIMATING_PLAYER":
                # Player animation done — check proximity then start monster turns
                for berti_pos in self.berti_positions:
                    player = self.level_array[berti_pos.x][berti_pos.y]
                    if isinstance(player, Player):
                        player.check_enemy_proximity(self)
                if self.level_ended != 0:
                    return
                if self.tb_monsters:
                    self.tb_state = "ANIMATING_MONSTER"
                    self.tb_current_monster_index = 0
                    self._tb_trigger_next_monster()
                else:
                    self.tb_state = "WAITING_PLAYER"

            elif self.tb_state == "ANIMATING_MONSTER":
                # Current monster animation done — advance to next monster
                if self.level_ended != 0:
                    return
                self.tb_current_monster_index += 1
                if self.tb_current_monster_index < len(self.tb_monsters):
                    self._tb_trigger_next_monster()
                else:
                    self.tb_state = "WAITING_PLAYER"
            return

        # No animations in progress — handle state logic
        if self.tb_state == "WAITING_PLAYER":
            # Poll for a single keypress from the player
            for berti_pos in self.berti_positions:
                entity = self.level_array[berti_pos.x][berti_pos.y]
                if isinstance(entity, Player) and not entity.is_moving:
                    pressed_dir = input_handler.get_direction(True)  # always single-step
                    if pressed_dir != config.Direction.NONE and self.is_walkable(
                        entity.x, entity.y, pressed_dir
                    ):
                        self.start_move(entity.x, entity.y, pressed_dir)
                        self.tb_state = "ANIMATING_PLAYER"
                        self._tb_build_monster_list()

        elif self.tb_state == "ANIMATING_MONSTER":
            # Monster had no move available — skip it and advance
            self.tb_current_monster_index += 1
            if self.tb_current_monster_index < len(self.tb_monsters):
                self._tb_trigger_next_monster()
            else:
                self.tb_state = "WAITING_PLAYER"

    def _tb_build_monster_list(self):
        """Scans the grid and builds the ordered monster list for this round (row-major order)."""
        self.tb_monsters = []
        for y in range(config.LEV_DIMENSION_Y):
            for x in range(config.LEV_DIMENSION_X):
                entity = self.level_array[x][y]
                if isinstance(entity, (PurpleMonster, GreenMonster)):
                    self.tb_monsters.append(entity)
        self.tb_current_monster_index = 0

    def _tb_trigger_next_monster(self):
        """Triggers the AI for the current monster, skipping any that are stuck or removed."""
        while self.tb_current_monster_index < len(self.tb_monsters):
            monster = self.tb_monsters[self.tb_current_monster_index]
            # Verify the monster is still alive and at its expected position
            if self.level_array[monster.x][monster.y] is monster:
                monster.update_ai(self)
                if monster.is_moving:
                    return  # Animation started — wait for it to complete
                # Monster couldn't move; try the next one
            self.tb_current_monster_index += 1
        # All monsters processed
        self.tb_state = "WAITING_PLAYER"

    def _tb_assign_turn_orders(self):
        """Assigns turn order numbers to all character entities after a level load."""
        self.tb_turn_orders = {}
        turn = 1
        # Player is always turn 1 (scan for player first)
        for y in range(config.LEV_DIMENSION_Y):
            for x in range(config.LEV_DIMENSION_X):
                entity = self.level_array[x][y]
                if isinstance(entity, Player):
                    self.tb_turn_orders[id(entity)] = turn
                    turn += 1
        # Monsters get turns 2, 3, 4... in row-major scan order
        for y in range(config.LEV_DIMENSION_Y):
            for x in range(config.LEV_DIMENSION_X):
                entity = self.level_array[x][y]
                if isinstance(entity, (PurpleMonster, GreenMonster)):
                    self.tb_turn_orders[id(entity)] = turn
                    turn += 1

    def toggle_turn_based(self):
        """Toggles turn-based mode on/off and resets the current level."""
        self.turn_based = not self.turn_based
        self.reset_level()

    ## 2. Level Handling Methods
    # =================================================================================
    def load_level(self, level_num):
        """
        Initializes the game board from level data.
        Equivalent to `load_level` in JS.
        """
        self.level_number = level_num
        self.mode = 1
        self.level_array = [
            [Empty(x, y) for y in range(config.LEV_DIMENSION_Y)]
            for x in range(config.LEV_DIMENSION_X)
        ]
        self.berti_positions = []
        self.steps_taken = 0
        self.num_bananas = 0
        self.level_ended = 0
        self.audio_manager.play_sound("newplane")
        self.wait_timer = config.LEV_START_DELAY * config.UPS

        berti_counter = 0
        if level_num >= len(self.external_level_data):
            level_map = [
                [config.Entity.EMPTY for _ in range(config.LEV_DIMENSION_Y)]
                for _ in range(config.LEV_DIMENSION_X)
            ]
        else:
            level_map = self.external_level_data[level_num]

        for y in range(config.LEV_DIMENSION_Y):
            for x in range(config.LEV_DIMENSION_X):
                entity_id = level_map[x][y]

                if entity_id == config.Entity.PLAYER_BERTI:
                    self.level_array[x][y] = Player(x, y, berti_counter)
                    self.berti_positions.append(Vec(x, y))
                    berti_counter += 1
                elif entity_id == config.Entity.AUTO_BERTI:
                    self.level_array[x][y] = PurpleMonster(x, y)
                elif entity_id == config.Entity.BANANA_PEEL:
                    self.level_array[x][y] = Banana(x, y)
                    self.num_bananas += 1
                elif entity_id == config.Entity.PURPLE_MONSTER:
                    self.level_array[x][y] = PurpleMonster(x, y)
                elif entity_id == config.Entity.GREEN_MONSTER:
                    self.level_array[x][y] = GreenMonster(x, y)
                elif entity_id == config.Entity.PINNED_BLOCK:
                    self.level_array[x][y] = PinnedBlock(x, y)
                elif entity_id == config.Entity.LIGHT_BLOCK:
                    self.level_array[x][y] = LightBlock(x, y)
                elif entity_id == config.Entity.HEAVY_BLOCK:
                    self.level_array[x][y] = HeavyBlock(x, y)
                elif config.Entity.KEY_1 <= entity_id <= config.Entity.KEY_6:
                    key_type = entity_id - config.Entity.KEY_1 + 1
                    self.level_array[x][y] = Key(x, y, key_type)
                elif config.Entity.DOOR_1 <= entity_id <= config.Entity.DOOR_6:
                    door_type = entity_id - config.Entity.DOOR_1 + 1
                    self.level_array[x][y] = Door(x, y, door_type)
                else:
                    self.level_array[x][y] = Empty(x, y)

        self.bananas_remaining = self.num_bananas

        self._initialize_entity_animations()

        if self.turn_based:
            self._tb_assign_turn_orders()
            self.tb_state = "WAITING_PLAYER"
            self.tb_current_monster_index = 0
            self.tb_monsters = []

    def _initialize_entity_animations(self):
        """
        Sets the initial animation_frame for all entities after level load.
        This is the Python port of the 'init_animation' function from the JS source.
        """
        offset_key_x, offset_key_y = 3, 4
        offset_banana_x, offset_banana_y = 4, 4

        for y in range(config.LEV_DIMENSION_Y):
            for x in range(config.LEV_DIMENSION_X):
                entity = self.level_array[x][y]

                if isinstance(entity, Player):
                    entity.animation_frame = ImageID.BERTI_IDLE
                elif isinstance(entity, PinnedBlock):
                    entity.animation_frame = ImageID.BLOCK_PINNED
                elif isinstance(entity, Banana):
                    entity.animation_frame = ImageID.BANANA_PEEL
                    entity.fine_offset_x = offset_banana_x
                    entity.fine_offset_y = offset_banana_y
                elif isinstance(entity, LightBlock):
                    entity.animation_frame = ImageID.BLOCK_LIGHT
                elif isinstance(entity, HeavyBlock):
                    entity.animation_frame = ImageID.BLOCK_HEAVY
                elif isinstance(entity, PurpleMonster):
                    entity.animation_frame = ImageID.PURPMON_STUCK_0
                elif isinstance(entity, GreenMonster):
                    entity.animation_frame = ImageID.GREENMON_STUCK_0
                elif isinstance(entity, Key):
                    entity.animation_frame = (
                        ImageID.KEY_1 + entity.key_type - 1
                    )
                    entity.fine_offset_x = offset_key_x
                    entity.fine_offset_y = offset_key_y
                elif isinstance(entity, Door):
                    entity.animation_frame = (
                        ImageID.DOOR_1_CLOSED + (entity.door_type - 1) * 3
                    )

    def next_level(self):
        """Loads the next level, if unlocked."""
        next_lvl = self.level_number + 1
        if next_lvl > self.save_manager.reached_level and next_lvl <= 50:
            return

        if self.level_number >= 50:
            self.mode = 2
            return
        self.load_level(next_lvl)

    def previous_level(self):
        """Loads the previous level."""
        if self.level_number <= 1:
            return
        self.load_level(self.level_number - 1)

    def reset_level(self):
        """Reloads the current level."""
        self.load_level(self.level_number)

    def end_level(self, won=False, caught=False):
        """Ends the current level with a win or loss condition."""
        if won:
            self.level_ended = 1
            self.win_type = random.choice(["wow", "yeah"])
            self.audio_manager.play_sound(self.win_type)
            # Update reached level if a new level is completed
            if self.level_number == self.save_manager.reached_level:
                self.save_manager.reached_level += 1
                self.save_manager.progressed = (
                    True  # Mark that there is progress to save
                )
        elif caught:
            self.level_ended = 2
            self.audio_manager.play_sound("player_caught")
        self.wait_timer = config.LEV_STOP_DELAY * config.UPS

    ## 3. Movement and Interaction Logic
    # =================================================================================

    def is_walkable(self, x, y, direction):
        """
        Checks if an entity at (x, y) can move in a given direction.
        This is the definitive gatekeeper for all movement.
        args: 
            x, y: Current coordinates of the entity.
            direction: Direction to move (config.Direction).
        """
        dest = self.dir_to_coords(x, y, direction)
        
        # Rule 0: Cannot move out of bounds.
        if not self.is_in_bounds(dest.x, dest.y):
            return False

        entity_at_src = self.level_array[x][y]
        entity_at_dest = self.level_array[dest.x][dest.y]
        
        # Rule 1: A tile claimed by a Dummy is ALWAYS unwalkable.
        if isinstance(entity_at_dest, Dummy):
            return False
        # Rule 2: An empty tile is always walkable.
        if isinstance(entity_at_dest, Empty):
            return True
        if isinstance(entity_at_dest, PinnedBlock):
            return False
        # Rule 3: The player can always move onto a consumable item.
        if isinstance(entity_at_src, Player) and entity_at_dest.consumable:
            return True  
        # Rule 4: A pushable entity can be moved if it is not already moving and
        # the space behind it is walkable.
        if entity_at_dest.pushable and entity_at_src.can_push and not entity_at_dest.is_moving:
            # Recursive call to check the tile behind the pushable object.
            if dest.x == x+1 and dest.y == y:
                return self.is_walkable(dest.x, dest.y, config.Direction.RIGHT)
            if dest.x == x-1 and dest.y == y:
                return self.is_walkable(dest.x, dest.y, config.Direction.LEFT)
            if dest.x == x and dest.y == y+1:
                return self.is_walkable(dest.x, dest.y, config.Direction.DOWN)
            if dest.x == x and dest.y == y-1:
                return self.is_walkable(dest.x, dest.y, config.Direction.UP)
        # Rule 5: An entity that is already moving cannot be pushed.
        if entity_at_dest.pushable and entity_at_dest.is_moving:
            return False
        # Rule 6: A tile with a moving entity is walkable, ONLY if it's not a direct swap and no other entity is moving there.
        if entity_at_dest.is_moving and isinstance(entity_at_src, Character):         
            their_destination = self.dir_to_coords(entity_at_dest.x, entity_at_dest.y, entity_at_dest.face_dir)
            # check if their destination is our source tile
            if their_destination.x == x and their_destination.y == y:
                return False
            if their_destination.x == dest.x and their_destination.y == dest.y:
                return False
            return True
        # Rule 7: Any other entity (idle monster, static block) makes the tile unwalkable.
        return False

    def start_move(self, x, y, direction):
        """
        Initiates the visual movement of an entity.
        """
        # SAFETY CHECK: Verify the move is actually walkable
        if not self.is_walkable(x, y, direction):
            return  # Abort the move if it's not valid
        
        entity = self.level_array[x][y]
        dest = self.dir_to_coords(x, y, direction)

        entity.is_moving = True
        entity.face_dir = direction
        
        if isinstance(entity, Player):
            self.steps_taken += 1
            self.save_manager.progressed = True # Mark progress on move

        dest_entity = self.level_array[dest.x][dest.y]
        
        if isinstance(dest_entity, Empty):
            self.level_array[dest.x][dest.y] = Dummy(dest.x, dest.y)
        elif dest_entity.consumable:
            pass 
        elif not dest_entity.is_moving:
            entity.is_pushing = True
            self.start_move(dest.x, dest.y, direction)

    ## 4. AI and Utility Methods
    # =================================================================================
    def is_in_bounds(self, x, y):
        return (
            0 <= x < config.LEV_DIMENSION_X and 0 <= y < config.LEV_DIMENSION_Y
        )

    def dir_to_coords(self, x, y, direction):
        if direction == config.Direction.UP:
            return Vec(x, y - 1)
        if direction == config.Direction.DOWN:
            return Vec(x, y + 1)
        if direction == config.Direction.LEFT:
            return Vec(x - 1, y)
        if direction == config.Direction.RIGHT:
            return Vec(x + 1, y)
        return Vec(x, y)

    def can_see_tile(self, eye_x, eye_y, tile_x, tile_y):
        diff_x = tile_x - eye_x
        diff_y = tile_y - eye_y

        if diff_x == 0 and diff_y == 0:
            return True

        walk1_x, walk1_y, walk2_x, walk2_y = 0, 0, 0, 0

        if diff_x == 0:
            walk1_x, walk2_x = 0, 0
            walk1_y, walk2_y = 1 if diff_y > 0 else -1, 1 if diff_y > 0 else -1
        elif diff_x > 0:
            if diff_y == 0:
                walk1_x, walk2_x, walk1_y, walk2_y = 1, 1, 0, 0
            elif diff_y > 0:
                if diff_y > diff_x:
                    walk1_x, walk1_y, walk2_x, walk2_y = 0, 1, 1, 1
                elif diff_y == diff_x:
                    walk1_x, walk1_y, walk2_x, walk2_y = 1, 1, 1, 1
                else:
                    walk1_x, walk1_y, walk2_x, walk2_y = 1, 0, 1, 1
            else:
                if abs(diff_y) > diff_x:
                    walk1_x, walk1_y, walk2_x, walk2_y = 0, -1, 1, -1
                elif abs(diff_y) == diff_x:
                    walk1_x, walk1_y, walk2_x, walk2_y = 1, -1, 1, -1
                else:
                    walk1_x, walk1_y, walk2_x, walk2_y = 1, 0, 1, -1
        else:
            if diff_y == 0:
                walk1_x, walk1_y, walk2_x, walk2_y = -1, 0, -1, 0
            elif diff_y > 0:
                if diff_y > abs(diff_x):
                    walk1_x, walk1_y, walk2_x, walk2_y = 0, 1, -1, 1
                elif diff_y == abs(diff_x):
                    walk1_x, walk1_y, walk2_x, walk2_y = -1, 1, -1, 1
                else:
                    walk1_x, walk1_y, walk2_x, walk2_y = -1, 0, -1, 1
            else:
                if diff_y > diff_x:
                    walk1_x, walk1_y, walk2_x, walk2_y = -1, 0, -1, -1
                elif diff_y == diff_x:
                    walk1_x, walk1_y, walk2_x, walk2_y = -1, -1, -1, -1
                else:
                    walk1_x, walk1_y, walk2_x, walk2_y = 0, -1, -1, -1

        x_offset, y_offset = 0, 0
        max_iterations = abs(diff_x) + abs(diff_y) + 1

        while max_iterations > 0:
            max_iterations -= 1
            x_ratio1 = (x_offset + walk1_x) / diff_x if diff_x != 0 else 1
            x_ratio2 = (x_offset + walk2_x) / diff_x if diff_x != 0 else 1
            y_ratio1 = (y_offset + walk1_y) / diff_y if diff_y != 0 else 1
            y_ratio2 = (y_offset + walk2_y) / diff_y if diff_y != 0 else 1

            if abs(x_ratio1 - y_ratio1) <= abs(x_ratio2 - y_ratio2):
                x_offset, y_offset = x_offset + walk1_x, y_offset + walk1_y
            else:
                x_offset, y_offset = x_offset + walk2_x, y_offset + walk2_y

            if x_offset == diff_x and y_offset == diff_y:
                return True

            current_entity = self.level_array[eye_x + x_offset][
                eye_y + y_offset
            ]
            if (
                not isinstance(current_entity, (Empty, Dummy))
                and not current_entity.is_small
            ):
                return False

        return False  # Exceeded iteration limit — treat as blocked

    def get_adjacent_tiles(self, x, y, include_diagonals=False):
        adj = []
        for j in range(-1, 2):
            for i in range(-1, 2):
                if i == 0 and j == 0:
                    continue
                if not include_diagonals and i != 0 and j != 0:
                    continue

                check_x, check_y = x + i, y + j
                if self.is_in_bounds(check_x, check_y):
                    adj.append(Vec(check_x, check_y))
        return adj

    ## 5. UI Callback Methods
    # =================================================================================
    def get_state(self, key):
        if key == "has_storage":
            return True
        if key == "can_save":
            return self.save_manager.progressed
        if key == "is_logged_in":
            return self.save_manager.save_name is not None
        if key == "username":
            return self.save_manager.save_name
        return None

    def get_full_state(self):
        return {
            "paused": self.is_paused,
            "sound_on": self.audio_manager.sound_enabled,
            "volume": self.audio_manager.volume,
            "single_steps": self.single_steps,
            "turn_based": self.turn_based,
            "buttons_activated": [
                self.level_number > 1,
                True,
                self.level_number < self.save_manager.reached_level,
            ],
        }

    def get_charts_data(self):
        """
        Scans all save files, collects all completed level scores, sorts them,
        and returns the data for the charts dialog.
        """
        all_scores = []

        # Check if the save directory exists
        if not os.path.exists(SAVE_DIR):
            return []

        # Iterate through all files in the save directory
        for filename in os.listdir(SAVE_DIR):
            if filename.endswith(".json"):
                filepath = os.path.join(SAVE_DIR, filename)
                try:
                    with open(filepath, "r") as f:
                        data = json.load(f)

                    # Ensure the save file has the required data
                    save_name = data.get("save_name")
                    arr_steps = data.get("arr_steps")

                    if save_name and arr_steps:
                        # arr_steps keys are strings from JSON, convert to int
                        for level_str, steps in arr_steps.items():
                            if (
                                steps > 0
                            ):  # A score of 0 means the level hasn't been completed
                                all_scores.append(
                                    {
                                        "name": save_name,
                                        "level": int(level_str),
                                        "steps": steps,
                                    }
                                )
                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    continue  # Skip corrupted or malformed files

        # Sort the scores. The best scores are those with the fewest steps.
        # A secondary sort by level number is good for tie-breaking.
        all_scores.sort(key=lambda x: (x["steps"], x["level"]))

        return all_scores

    def save_game_action(self, save_name):
        """UI callback for saving the game. Returns an ErrorCode."""
        if not save_name:
            return ErrorCode.EMPTYNAME

        self.save_manager.arr_steps[self.level_number] = self.steps_taken

        if self.save_manager.save_game(save_name):
            return ErrorCode.SUCCESS
        else:
            return ErrorCode.SAVEFAIL

    def load_game_action(self, save_name):
        """UI callback for loading a game. Returns an ErrorCode."""
        if not save_name:
            return ErrorCode.EMPTYNAME

        if self.save_manager.load_game(save_name):
            self.load_level(self.save_manager.reached_level)
            return ErrorCode.SUCCESS
        else:
            return ErrorCode.NOTFOUND

    def change_password_action(self, old_pass, new_pass):
        """(Obsolete) UI callback for changing password. Does nothing."""
        return ErrorCode.SUCCESS

    def new_game_action(self):
        """UI callback for starting a new game."""
        self.save_manager = SaveGameManager()
        self.load_level(1)

    def save_and_new_game_action(self):
        """UI callback for the 'Yes' button in the 'New Game' confirmation."""
        pass

    def toggle_single_steps(self):
        self.single_steps = not self.single_steps

    def toggle_pause(self):
        self.is_paused = not self.is_paused

    def toggle_sound(self):
        self.audio_manager.toggle_sound()

    def _process_completed_moves(self, moves_to_process):
        # Pass 1: clear all source cells so push chains don't block placements.
        for entity in moves_to_process:
            if self.level_array[entity.x][entity.y] == entity:
                self.level_array[entity.x][entity.y] = Empty(entity.x, entity.y)

        # Pass 2: place all entities at their destinations.
        monsters_to_check = []
        for entity in moves_to_process:
            dest_pos = self.dir_to_coords(entity.x, entity.y, entity.face_dir)
            target_tile_entity = self.level_array[dest_pos.x][dest_pos.y]

            if isinstance(entity, Player) and target_tile_entity.consumable:
                if isinstance(target_tile_entity, Banana):
                    self.bananas_remaining -= 1
                target_tile_entity.consume(self)
                if self.bananas_remaining <= 0:
                    self.end_level(won=True)

            if isinstance(self.level_array[dest_pos.x][dest_pos.y], (Empty, Dummy)):
                self.level_array[dest_pos.x][dest_pos.y] = entity

            entity.x, entity.y = dest_pos.x, dest_pos.y
            entity.is_moving = False
            entity.moving_offset = Vec(0, 0)
            entity.is_pushing = False

            if isinstance(entity, Player):
                self.berti_positions[entity.berti_id] = dest_pos

            if isinstance(entity, Monster):
                monsters_to_check.append(entity)

        # Pass 3: check captures only after ALL entities are placed.
        # Deferring this prevents the early-return from leaving entities stranded.
        for monster in monsters_to_check:
            monster.check_player_capture(self)
            if self.level_ended != 0:
                return
    def remove_entity(self, entity_to_remove):
        if (
            self.level_array[entity_to_remove.x][entity_to_remove.y]
            == entity_to_remove
        ):
            self.level_array[entity_to_remove.x][entity_to_remove.y] = Empty(
                entity_to_remove.x, entity_to_remove.y
            )
