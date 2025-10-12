# entities.py
import random
from . import config


# A simple class for 2D vectors/coordinates
class Vec:
    def __init__(self, x, y):
        self.x = x
        self.y = y


# ===================================================================================
# BASE ENTITY CLASS
# ===================================================================================
class Entity:
    """The base class for all objects in the game world."""

    def __init__(self, x, y, entity_id):
        self.x = x
        self.y = y
        self.id = entity_id

        # --- State Properties ---
        self.is_moving = False
        self.is_pushing = False
        self.face_dir = config.Direction.DOWN
        self.just_moved = False
        self.removal_timer = -1  # Corresponds to gets_removed_in

        # --- Gameplay Attributes ---
        self.can_push = False
        self.pushable = False
        self.consumable = False
        self.is_small = False  # Affects movement and visibility rules

        # --- Visuals ---
        self.moving_offset = Vec(0, 0)  # Visual offset for smooth tweening
        self.fine_offset_x = 0  # Static X offset for sprite centering
        self.fine_offset_y = 0  # Static Y offset for sprite centering
        self.animation_frame = -1  # Current image ID to display
        self.anim_index = 0  # The 0-3 index of the current animation frame

    def update(self, game):
        """
        Handles the continuous logic for an entity, like visual movement and timers.
        This is called every game tick.
        """
        # 1. Handle visual movement tweening
        if self.is_moving:
            if self.face_dir == config.Direction.UP:
                self.moving_offset.y -= game.move_speed
            elif self.face_dir == config.Direction.DOWN:
                self.moving_offset.y += game.move_speed
            elif self.face_dir == config.Direction.LEFT:
                self.moving_offset.x -= game.move_speed
            elif self.face_dir == config.Direction.RIGHT:
                self.moving_offset.x += game.move_speed

            # Check if movement to the next tile is complete
            if (
                abs(self.moving_offset.x) >= config.TILE_SIZE
                or abs(self.moving_offset.y) >= config.TILE_SIZE
            ):
                game.completed_moves.append(self)
                self.just_moved = True
        # 2. Handle entity removal timer (for doors)
        if self.removal_timer == 0:
            if self.is_moving:
                dest_pos = game.dir_to_coords(self.x, self.y, self.face_dir)
                game.level_array[dest_pos.x][dest_pos.y] = Empty(
                    dest_pos.x, dest_pos.y
                )
            game.level_array[self.x][self.y] = Empty(self.x, self.y)

        elif self.removal_timer > 0:
            self.removal_timer -= 1


# ===================================================================================
# CHARACTER SUBCLASSES (PLAYER AND MONSTERS)
# ===================================================================================


class Character(Entity):
    """A base class for movable characters like the player and monsters."""

    def __init__(self, x, y, entity_id):
        super().__init__(x, y, entity_id)
        self.is_small = True  # Players and monsters are "small" entities


class Player(Character):
    """The player-controlled character."""

    def __init__(self, x, y, berti_id):
        super().__init__(x, y, config.Entity.PLAYER_BERTI)
        self.berti_id = berti_id
        self.can_push = True

    def handle_input(self, game, input_handler, single_step_mode):
        """Checks for keyboard/touch input and initiates movement based on the game mode."""
        if self.is_moving:
            return

        # Get the appropriate direction based on whether single-step is on
        pressed_dir = input_handler.get_direction(single_step_mode)

        if pressed_dir != config.Direction.NONE and game.is_walkable(
            self.x, self.y, pressed_dir
        ):
            game.start_move(self.x, self.y, pressed_dir)

    def check_enemy_proximity(self, game):
        """Checks adjacent and diagonal tiles for monsters."""
        if self.moving_offset.x != 0 or self.moving_offset.y != 0:
            return

        for tile_pos in game.get_adjacent_tiles(
            self.x, self.y, include_diagonals=True
        ):
            entity = game.level_array[tile_pos.x][tile_pos.y]
            if isinstance(entity, Monster) and not entity.is_moving:
                is_diagonal = (
                    abs(self.x - tile_pos.x) == 1
                    and abs(self.y - tile_pos.y) == 1
                )
                if is_diagonal:
                    obstacle1 = not isinstance(
                        game.level_array[tile_pos.x][self.y], (Empty, Dummy)
                    )
                    obstacle2 = not isinstance(
                        game.level_array[self.x][tile_pos.y], (Empty, Dummy)
                    )
                    if obstacle1 or obstacle2:
                        continue
                game.end_level(caught=True)
                return


class Monster(Character):
    """A base class for enemy AI characters."""

    def __init__(self, x, y, entity_id):
        super().__init__(x, y, entity_id)
        self.sees_berti = False
        self.time_since_noise = 100

    def update_ai(self, game):
        """The main AI logic loop for the monster."""
        if not self.is_moving:
            self.chase_berti(game)

    def move_randomly(self, game):
        """Makes the monster wander aimlessly if it cannot see the player."""
        if self.is_moving:
            return

        possibilities = [
            config.Direction.UP,
            config.Direction.DOWN,
            config.Direction.LEFT,
            config.Direction.RIGHT,
        ]
        random.shuffle(possibilities)  # Shuffle to make it random

        if random.random() < 0.80 and game.is_walkable(
            self.x, self.y, self.face_dir
        ):
            game.start_move(self.x, self.y, self.face_dir)
            return

        for direction in possibilities:
            if game.is_walkable(self.x, self.y, direction):
                game.start_move(self.x, self.y, direction)
                return

    def chase_berti(self, game):
        """Finds and moves towards the player if visible."""
        if self.is_moving:
            return

        self.time_since_noise += 1
        closest_berti_pos = None
        min_dist = float('inf')

        for berti_pos in game.berti_positions:
            is_in_front = (
                (self.face_dir == config.Direction.DOWN and berti_pos.y >= self.y) or
                (self.face_dir == config.Direction.UP and berti_pos.y <= self.y) or
                (self.face_dir == config.Direction.LEFT and berti_pos.x <= self.x) or
                (self.face_dir == config.Direction.RIGHT and berti_pos.x >= self.x)
            )
            
            if is_in_front and game.can_see_tile(self.x, self.y, berti_pos.x, berti_pos.y):
                dist = abs(berti_pos.x - self.x) + abs(berti_pos.y - self.y)
                if dist < min_dist:
                    min_dist = dist
                    closest_berti_pos = berti_pos

        if closest_berti_pos is None or random.random() < 0.02:
            self.sees_berti = False
            self.move_randomly(game)
            return
       
        # Get the actual player object the monster is chasing.
        player_entity = game.level_array[closest_berti_pos.x][closest_berti_pos.y]

        # Check if the player is currently in the middle of a move.
        if player_entity.is_moving:
            # Calculate where the player will end up after their move.
            player_dest = game.dir_to_coords(player_entity.x, player_entity.y, player_entity.face_dir)
            
            # Check if that destination is adjacent (including diagonals) to the monster's current position.
            is_orthogonally_adjacent = abs(player_dest.x - self.x) + abs(player_dest.y - self.y) == 1
            
            if is_orthogonally_adjacent:
                return

        if not self.sees_berti:
            self.sees_berti = True
            if self.time_since_noise > random.randint(3, 13):
                self.time_since_noise = 0
                if self.id == config.Entity.PURPLE_MONSTER: game.audio_manager.play_sound('monster_spot_purple')
                elif self.id == config.Entity.GREEN_MONSTER: game.audio_manager.play_sound('monster_spot_green')

        diff_x = closest_berti_pos.x - self.x
        diff_y = closest_berti_pos.y - self.y

        dir1, dir2 = None, None
        if abs(diff_x) > abs(diff_y):
            dir1 = config.Direction.RIGHT if diff_x > 0 else config.Direction.LEFT
            dir2 = config.Direction.DOWN if diff_y > 0 else config.Direction.UP
        else:
            dir1 = config.Direction.DOWN if diff_y > 0 else config.Direction.UP
            dir2 = config.Direction.RIGHT if diff_x > 0 else config.Direction.LEFT
        
        if diff_y == 0: dir2 = None
        if diff_x == 0: dir2 = None

        if game.is_walkable(self.x, self.y, dir1): game.start_move(self.x, self.y, dir1)
        elif dir2 and game.is_walkable(self.x, self.y, dir2): game.start_move(self.x, self.y, dir2)
        else: self.move_randomly(game)

    def check_player_capture(self, game):
        """Checks adjacent and diagonal tiles for a player to capture."""
        for tile_pos in game.get_adjacent_tiles(self.x, self.y, include_diagonals=True):
            entity = game.level_array[tile_pos.x][tile_pos.y]
            if isinstance(entity, Player):
                is_diagonal = abs(self.x - tile_pos.x) == 1 and abs(self.y - tile_pos.y) == 1
                if is_diagonal:
                    obstacle1 = not isinstance(game.level_array[tile_pos.x][self.y], (Empty, Dummy))
                    obstacle2 = not isinstance(game.level_array[self.x][tile_pos.y], (Empty, Dummy))
                    if obstacle1 or obstacle2: continue
                game.end_level(caught=True)
                return
class PurpleMonster(Monster):
    def __init__(self, x, y):
        super().__init__(x, y, config.Entity.PURPLE_MONSTER)
        self.can_push = True


class GreenMonster(Monster):
    def __init__(self, x, y):
        super().__init__(x, y, config.Entity.GREEN_MONSTER)


class Block(Entity):
    def __init__(self, x, y, entity_id):
        super().__init__(x, y, entity_id)
        self.pushable = True


class LightBlock(Block):
    def __init__(self, x, y):
        super().__init__(x, y, config.Entity.LIGHT_BLOCK)
        self.can_push = True


class HeavyBlock(Block):
    def __init__(self, x, y):
        super().__init__(x, y, config.Entity.HEAVY_BLOCK)


class PinnedBlock(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, config.Entity.PINNED_BLOCK)


class Item(Entity):
    def __init__(self, x, y, entity_id):
        super().__init__(x, y, entity_id)
        self.consumable = True

    def consume(self, game):
        raise NotImplementedError("Subclass must implement abstract method")


class Banana(Item):
    def __init__(self, x, y):
        super().__init__(x, y, config.Entity.BANANA_PEEL)

    def consume(self, game):
        # The only job of consume is to play a sound and remove the item from the grid.
        # The game logic (decrementing bananas_remaining) is handled in the engine.
        game.audio_manager.play_sound("collect_banana")
        game.remove_entity(self)


class Key(Item):
    def __init__(self, x, y, key_type):
        super().__init__(x, y, config.Entity.KEY_1 + key_type - 1)
        self.key_type = key_type

    def consume(self, game):
        # --- NEW LOGIC: FIND AND OPEN ALL MATCHING DOORS ---
        for x in range(config.LEV_DIMENSION_X):
            for y in range(config.LEV_DIMENSION_Y):
                entity = game.level_array[x][y]
                # If we find a door and its type matches this key's type...
                if (
                    isinstance(entity, Door)
                    and entity.door_type == self.key_type
                ):
                    entity.start_opening(game)

        # Original logic: play sound and remove the key itself
        game.audio_manager.play_sound("pickup_key")
        game.remove_entity(self)


class Door(Entity):
    def __init__(self, x, y, door_type):
        entity_id = config.Entity.DOOR_1 + door_type - 1
        super().__init__(x, y, entity_id)
        self.door_type = door_type
        self.state = "CLOSED"  # States: CLOSED, OPENING, FADING
        self.animation_timer = 0
        self.pushable = False

    def start_opening(self, game):
        """Begins the door opening sequence if it's currently closed."""
        if self.state == "CLOSED":
            self.state = "OPENING"
            self.animation_timer = config.ANIMATION_DURATION * 2
            game.audio_manager.play_sound("opendoor")

    def update(self, game):
        """Handles the animation state transitions for the door."""
        super().update(game)

        if self.state != "CLOSED":
            self.animation_timer -= 1

            opening_duration = config.ANIMATION_DURATION
            if self.animation_timer > opening_duration:
                self.state = "OPENING"
                self.animation_frame = (
                    config.ImageID.DOOR_1_OPENING + (self.door_type - 1) * 3
                )
            elif self.animation_timer > 0:
                self.state = "FADING"
                self.animation_frame = (
                    config.ImageID.DOOR_1_FADING + (self.door_type - 1) * 3
                )
            else:
                game.remove_entity(self)


class Empty(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, config.Entity.EMPTY)


class Dummy(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, config.Entity.DUMMY)
