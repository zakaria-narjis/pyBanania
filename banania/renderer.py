# renderer.py
import pygame
import os

from .config import (
    LEV_OFFSET_X,
    LEV_OFFSET_Y,
    LEV_DIMENSION_X,
    LEV_DIMENSION_Y,
    Entity,
    ImageID,
    IMAGE_DIR,
    IMG_DIGIT_LOOKUP,
)

# Constants for rendering logic, mirroring the JS implementation
TILE_SIZE = 24  # The JS version uses 24x24 tiles
ANIMATION_DURATION_MS = 100  # Time in ms for one animation frame


class Renderer:
    """
    Handles all drawing to the screen. This class is a Python/Pygame port
    of the rendering logic found in the original rendering_and_others.js,
    including CLASS_visual, render_field, and render_block functions.
    """

    def __init__(self):
        # A dictionary to hold all loaded images (Pygame surfaces)
        self.images = {}
        # Pygame fonts for any HUD/debug text
        self.font_big = pygame.font.SysFont("Tahoma", 24)
        self.font_small = pygame.font.SysFont("Tahoma", 12)

        # Animation sequence lengths (in frames)
        self.ANIM_LENGTH = 4

        # Offsets for pop-up images
        self.offset_wow_x = -20
        self.offset_wow_y = -44
        self.offset_yeah_x = -20
        self.offset_yeah_y = -44
        self.offset_argl_x = -20
        self.offset_argl_y = -44

        # --- Animation State Lookups ---
        # These lists map Direction enum to the starting ImageID for an animation.
        # This replaces the faulty logic in the original _get_animation_start_frame.
        # Order must match the Direction enum: UP(0), LEFT(1), DOWN(2), RIGHT(3)
        self.BERTI_WALK_STARTS = [
            ImageID.BERTI_WALK_UP_0,
            ImageID.BERTI_WALK_LEFT_0,
            ImageID.BERTI_WALK_DOWN_0,
            ImageID.BERTI_WALK_RIGHT_0,
        ]
        self.BERTI_PUSH_STARTS = [
            ImageID.BERTI_PUSH_UP_0,
            ImageID.BERTI_PUSH_LEFT_0,
            ImageID.BERTI_PUSH_DOWN_0,
            ImageID.BERTI_PUSH_RIGHT_0,
        ]
        self.PURPLE_MONSTER_WALK_STARTS = [
            ImageID.PURPMON_WALK_UP_0,
            ImageID.PURPMON_WALK_LEFT_0,
            ImageID.PURPMON_WALK_DOWN_0,
            ImageID.PURPMON_WALK_RIGHT_0,
        ]
        self.PURPLE_MONSTER_PUSH_STARTS = [
            ImageID.PURPMON_PUSH_UP_0,
            ImageID.PURPMON_PUSH_LEFT_0,
            ImageID.PURPMON_PUSH_DOWN_0,
            ImageID.PURPMON_PUSH_RIGHT_0,
        ]
        self.GREEN_MONSTER_WALK_STARTS = [
            ImageID.GREENMON_WALK_UP_0,
            ImageID.GREENMON_WALK_LEFT_0,
            ImageID.GREENMON_WALK_DOWN_0,
            ImageID.GREENMON_WALK_RIGHT_0,
        ]

        # --- Asset Loading ---
        self.load_assets()

    def _load_image(self, filename):
        """Loads a single Pygame image surface, handling transparency."""
        try:
            path = os.path.join(IMAGE_DIR, filename)
            return pygame.image.load(path).convert_alpha()
        except pygame.error as e:
            error_surface = pygame.Surface((TILE_SIZE, TILE_SIZE))
            error_surface.fill((255, 0, 255))  # Magenta for missing textures
            return error_surface

    def load_assets(self):
        """
        Loads all game images, matching the complete asset list from the JS source.
        This includes game entities, UI elements, items, and dialog boxes.
        The ImageID enum in config.py must be updated to match these additions.
        """
        simple_assets = {
            ImageID.BACKGROUND: "background.png",
            ImageID.TITLESCREEN: "entry.png",
            ImageID.ENDSCREEN: "exit.png",
            # REMOVED: ImageID.FOOTSTEPS and ImageID.LADDER are loaded in the loop below
            ImageID.ARGL: "argl.png",
            ImageID.WOW: "wow.png",
            ImageID.YEAH: "yeah.png",
            ImageID.CHECKBOX_CHECKED: "check_b.png",  # Renamed from CHECK_B
            ImageID.CHECKBOX_UNCHECKED: "check_w.png",  # Renamed from CHECK_W
            ImageID.DIALOGBOX_CONFIRM: "dbx_confirm.png",
            ImageID.DIALOGBOX_SAVELOAD: "dbx_saveload.png",
            ImageID.DIALOGBOX_LOADLVL: "dbx_loadlvl.png",
            ImageID.DIALOGBOX_CHARTS: "dbx_charts.png",
            ImageID.BTN_CANCEL_UP: "btn_c-up.png",
            ImageID.BTN_CANCEL_DOWN: "btn_c-down.png",
            ImageID.BTN_NO_UP: "btn_n-up.png",
            ImageID.BTN_NO_DOWN: "btn_n-down.png",
            ImageID.BTN_OK_UP: "btn_o-up.png",
            ImageID.BTN_OK_DOWN: "btn_o-down.png",
            ImageID.BTN_YES_UP: "btn_y-up.png",
            ImageID.BTN_YES_DOWN: "btn_y-down.png",
            ImageID.BTN_PREV_UP: "userbutton_0-1.png",
            ImageID.BTN_PREV_DOWN: "userbutton_1-1.png",
            ImageID.BTN_PREV_DISABLED: "userbutton_2-1.png",
            ImageID.BTN_BERTI_UP: "userbutton_0-0.png",
            ImageID.BTN_BERTI_DOWN: "userbutton_1-0.png",
            ImageID.BTN_BERTI_BLINK_UP: "userbutton_2-0.png",
            ImageID.BTN_NEXT_UP: "userbutton_0-2.png",
            ImageID.BTN_NEXT_DOWN: "userbutton_1-2.png",
            ImageID.BTN_NEXT_DISABLED: "userbutton_2-2.png",
        }
        for img_id, filename in simple_assets.items():
            self.images[img_id] = self._load_image(filename)

        for i in range(9):
            image_id = ImageID(i + 2)
            self.images[image_id] = self._load_image(f"garbage_{i}.png")

        for i in range(9):
            image_id = ImageID(i + 31)
            self.images[image_id] = self._load_image(f"stone_{i}.png")

        for i in range(11):
            self.images[ImageID.DIGIT_0 + i] = self._load_image(
                f"digits_{i}.png"
            )

        door_types, door_frames = 6, 3
        for i in range(door_types):
            for j in range(door_frames):
                self.images[ImageID.DOOR_1_CLOSED + (i * door_frames) + j] = (
                    self._load_image(f"doors_{j}-{i}.png")
                )

        player_anim_types, directions = 13, 4
        for i in range(player_anim_types):
            for j in range(directions):
                key = ImageID.BERTI_IDLE + (i * directions) + j
                self.images[key] = self._load_image(f"player_{j}-{i}.png")

        monster1_anim_types, directions = 9, 4
        for i in range(monster1_anim_types):
            for j in range(directions):
                key = ImageID.PURPMON_STUCK_0 + (i * directions) + j
                self.images[key] = self._load_image(f"monster1_{j}-{i}.png")

        monster2_anim_types, directions = 5, 4
        for i in range(monster2_anim_types):
            for j in range(directions):
                key = ImageID.GREENMON_STUCK_0 + (i * directions) + j
                self.images[key] = self._load_image(f"monster2_{j}-{i}.png")

    def _get_animation_start_frame(self, block):
        """Helper to determine the base frame ID for an entity's current state."""
        # Player Animation Logic
        if block.id == Entity.PLAYER_BERTI:
            if block.is_moving:
                base_list = (
                    self.BERTI_PUSH_STARTS
                    if block.is_pushing
                    else self.BERTI_WALK_STARTS
                )
                return base_list[block.face_dir]
            else:
                # Player idle state is not animated
                return ImageID.BERTI_IDLE

        # Purple Monster Animation Logic
        elif block.id == Entity.PURPLE_MONSTER:
            if block.is_moving:
                base_list = (
                    self.PURPLE_MONSTER_PUSH_STARTS
                    if block.is_pushing
                    else self.PURPLE_MONSTER_WALK_STARTS
                )
                return base_list[block.face_dir]
            else:
                # Monster idle ("stuck") state is a 4-frame animation
                return ImageID.PURPMON_STUCK_0

        # Green Monster Animation Logic
        elif block.id == Entity.GREEN_MONSTER:
            if block.is_moving:
                # Green monster does not have a push animation
                return self.GREEN_MONSTER_WALK_STARTS[block.face_dir]
            else:
                # Monster idle ("stuck") state is a 4-frame animation
                return ImageID.GREENMON_STUCK_0

        return -1

    def update_animation(self, game, x, y):
        """Updates the animation frame for a single entity based on its state."""
        block = game.level_array[x][y]

        # Handle static states (win/loss) first for the player
        if block.id == Entity.PLAYER_BERTI:
            if game.level_ended == 1:
                block.animation_frame = ImageID.BERTI_CELEBRATING
                return
            elif game.level_ended == 2:
                block.animation_frame = ImageID.BERTI_DEAD
                return

        # Determine the correct animation strip for the entity's current state
        start_id = self._get_animation_start_frame(block)

        # Exit if not an animated character or in a non-animated state (like Berti's idle)
        if start_id == -1 or (
            block.id == Entity.PLAYER_BERTI and not block.is_moving
        ):
            block.animation_frame = (
                start_id if start_id != -1 else block.animation_frame
            )
            return

        # Determine if it's time to advance the animation frame
        advance_frame = False
        current_time_ms = pygame.time.get_ticks()
        if not hasattr(block, "last_anim_time"):
            block.last_anim_time = 0

        if current_time_ms - block.last_anim_time > ANIMATION_DURATION_MS:
            advance_frame = True
            block.last_anim_time = current_time_ms

        # If the character's state has changed, reset the animation to the new strip
        if (
            not hasattr(block, "anim_index")
            or block.animation_frame < start_id
            or block.animation_frame >= start_id + self.ANIM_LENGTH
        ):
            block.animation_frame = start_id
            block.anim_index = 0
        # Otherwise, advance the frame if it's time
        elif advance_frame:
            block.anim_index = (block.anim_index + 1) % self.ANIM_LENGTH
            block.animation_frame = start_id + block.anim_index

    def update_all_animations(self, game):
        """Iterates through all entities and updates their animations."""
        # ADD THIS CHECK: If we are not in the main game mode, do nothing.
        if game.mode != 1:
            return
        for y in range(LEV_DIMENSION_Y):
            for x in range(LEV_DIMENSION_X):
                # Ensure the block is an entity that needs animation updates
                if hasattr(game.level_array[x][y], "id"):
                    self.update_animation(game, x, y)

    def draw_block(self, surface, block, x_grid, y_grid):
        """Draws a single game entity."""
        # Ensure block has an animation frame to draw
        if not hasattr(block, "animation_frame"):
            return

        image = self.images.get(block.animation_frame)
        if not image:
            return

        # Get visual offsets for smooth movement and static adjustments
        offset_x = block.moving_offset.x + block.fine_offset_x
        offset_y = block.moving_offset.y + block.fine_offset_y
        x_pos = LEV_OFFSET_X + x_grid * TILE_SIZE + offset_x
        y_pos = LEV_OFFSET_Y + y_grid * TILE_SIZE + offset_y

        surface.blit(image, (x_pos, y_pos))

    def draw_level_entities(self, surface, game):
        """Draws the game entities, with clipping to keep them within the game board area."""

        # 1. Define the clipping rectangle for the game board.
        clip_rect = pygame.Rect(
            LEV_OFFSET_X,
            LEV_OFFSET_Y,
            LEV_DIMENSION_X * TILE_SIZE,
            LEV_DIMENSION_Y * TILE_SIZE,
        )

        # --- Draw the game board entities with clipping enabled ---
        try:
            # 2. Apply the clipping rectangle.
            surface.set_clip(clip_rect)

            # To achieve the correct 2.5D perspective, we collect all drawable objects
            # and sort them in every frame based on their visual position.

            # Step A: Collect all drawable entities into a single list.
            drawable_entities = []
            for y in range(LEV_DIMENSION_Y):
                for x in range(LEV_DIMENSION_X):
                    block = game.level_array[x][y]
                    # A block is drawable if it has a valid image assigned.
                    if (
                        hasattr(block, "animation_frame")
                        and block.animation_frame != -1
                    ):
                        drawable_entities.append(block)

            # Step B: Define the sorting key for column-by-column rendering.
            def sort_key(entity):
                # Main sort key: The visual X position. This ensures a strict
                # column-by-column draw order from left to right.
                visual_x = entity.x * TILE_SIZE + entity.moving_offset.x

                # Secondary sort key: The visual Y position. For entities
                # in the same column, this draws them from top to bottom.
                visual_y = entity.y * TILE_SIZE + entity.moving_offset.y

                # Tertiary sort key (Priority): A final tie-breaker.
                # priority = 0 if hasattr(entity, 'id') and entity.id == Entity.PINNED_BLOCK else 1

                return visual_x + visual_y

            # Step C: Sort the list of entities using our final key.
            drawable_entities.sort(key=sort_key)

            # Step D: Draw the entities in their newly sorted back-to-front order.
            for block in drawable_entities:
                self.draw_block(surface, block, block.x, block.y)

        finally:
            # 3. IMPORTANT: Reset the clip so popups and UI can draw outside the board.
            surface.set_clip(None)

        # --- Draw Popups on top (e.g., "WOW!", "ARGL!") without clipping ---
        if game.level_ended > 0 and game.berti_positions:
            for p_pos in game.berti_positions:
                player_block = game.level_array[p_pos.x][p_pos.y]
                x_pos = (
                    LEV_OFFSET_X
                    + p_pos.x * TILE_SIZE
                    + player_block.moving_offset.x
                )
                y_pos = (
                    LEV_OFFSET_Y
                    + p_pos.y * TILE_SIZE
                    + player_block.moving_offset.y
                )

                popup_img, offset_x, offset_y = None, 0, 0

                if game.level_ended == 1:  # Won
                    if game.win_type == "wow":
                        popup_id = ImageID.WOW
                        offset_x, offset_y = (
                            self.offset_wow_x,
                            self.offset_wow_y,
                        )
                    else:
                        popup_id = ImageID.YEAH
                        offset_x, offset_y = (
                            self.offset_yeah_x,
                            self.offset_yeah_y,
                        )
                    popup_img = self.images.get(popup_id)

                elif game.level_ended == 2:  # Died
                    popup_img = self.images.get(ImageID.ARGL)
                    offset_x, offset_y = self.offset_argl_x, self.offset_argl_y

                if popup_img:
                    surface.blit(
                        popup_img, (x_pos + offset_x, y_pos + offset_y)
                    )

    def draw(self, surface, game):
        """The main drawing function, called every frame."""
        # Always draw the base background
        surface.blit(self.images.get(ImageID.BACKGROUND), (0, 0))

        # Mode 0: Title Screen
        if game.mode == 0:
            title_img = self.images.get(ImageID.TITLESCREEN)
            if title_img:
                # Center the title image within the level area
                x = (
                    LEV_OFFSET_X
                    + (TILE_SIZE * LEV_DIMENSION_X - title_img.get_width()) / 2
                )
                y = (
                    LEV_OFFSET_Y
                    + (TILE_SIZE * LEV_DIMENSION_Y - title_img.get_height())
                    / 2
                )
                surface.blit(title_img, (x, y))

        # Mode 1: Main Game
        elif game.mode == 1:
            # Draw static UI elements like footsteps and ladder
            surface.blit(self.images.get(ImageID.FOOTSTEPS), (22, 41))
            self.draw_number(surface, game.steps_taken, 101, 41, 4)
            surface.blit(self.images.get(ImageID.LADDER), (427, 41))
            self.draw_number(surface, game.level_number, 506, 41, 2)

            # Draw all the dynamic game entities
            self.draw_level_entities(surface, game)

            # NOTE: HUD elements like score, buttons, etc., would be drawn here

        # Mode 2: End Screen
        elif game.mode == 2:
            end_img = self.images.get(ImageID.ENDSCREEN)
            if end_img:
                x = (
                    LEV_OFFSET_X
                    + (TILE_SIZE * LEV_DIMENSION_X - end_img.get_width()) / 2
                )
                y = (
                    LEV_OFFSET_Y
                    + (TILE_SIZE * LEV_DIMENSION_Y - end_img.get_height()) / 2
                )
                surface.blit(end_img, (x, y))

    def get_image(self, image_id):
        """Helper to allow other managers to access loaded images."""
        return self.images.get(image_id)

    def draw_number(self, surface, number, x_right_align, y, total_digits):
        """
        Draws a number right-aligned at a specific location, inspired by the JS logic.
        Pads the left with an empty digit sprite instead of zeros.

        Args:
            surface: The pygame surface to draw on.
            number: The integer to display.
            x_right_align: The x-coordinate for the RIGHT edge of the rightmost digit.
            y: The y-coordinate for the top of the digits.
            total_digits: The total width of the display area in digits.
        """
        # Get the width of a single digit from the pre-loaded images.
        digit_img = self.images.get(ImageID.DIGIT_0)
        if not digit_img:
            return  # Failsafe if images aren't loaded
        digit_width = digit_img.get_width()

        number_str = str(number)

        # 1. Draw the actual digits of the number, starting from the right.
        # We iterate through the number string in reverse.
        for i, digit_char in enumerate(reversed(number_str)):
            # This check ensures we only process valid number characters.
            if "0" <= digit_char <= "9":
                digit_value = int(digit_char)

                # Use the lookup table from config.py to get the correct ImageID.
                image_id = IMG_DIGIT_LOOKUP[digit_value]

                # Retrieve the pre-loaded image from the self.images dictionary.
                image_to_draw = self.images.get(image_id)

                # The x position is calculated from the right edge.
                # i=0 is the rightmost digit, drawn at x_right_align.
                # i=1 is the next digit to the left, and so on.
                x_pos = x_right_align - (i * digit_width)

                if image_to_draw:
                    surface.blit(image_to_draw, (x_pos, y))

        # 2. Draw the empty placeholder digits for the remaining space on the left.
        # This replicates the second loop in the provided JavaScript.
        empty_image = self.images.get(ImageID.DIGIT_EMPTY)
        if empty_image:
            # Start drawing empty digits to the left of the number we just drew.
            # The loop starts at the number of digits already drawn.
            for i in range(len(number_str), total_digits):
                x_pos = x_right_align - (i * digit_width)
                surface.blit(empty_image, (x_pos, y))
