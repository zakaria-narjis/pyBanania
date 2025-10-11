# input_handler.py
import pygame
from .config import Direction


class InputHandler:
    """
    Processes raw Pygame events into a game-relevant state. It handles quitting,
    delegates UI events, and interprets keyboard input for player movement
    in both single-step and continuous modes.
    """

    def __init__(self):
        self.quit_requested = False

        # Captures a one-time direction event, reset every frame.
        # Used for 'single_steps' mode.
        self.direction_event = Direction.NONE

        # Tracks the last directional key pressed to resolve diagonal movement conflicts.
        self._last_dir_pressed_map = Direction.NONE

    def process_events(self, ui_manager):
        """
        Iterates through the Pygame event queue each frame. It resets single-press
        events, delegates all events to the UIManager, and then processes key
        presses for game logic.
        """
        # Reset one-time events at the start of each frame's input processing.
        self.direction_event = Direction.NONE

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit_requested = True
                return  # Exit immediately if quit is requested

            # --- 1. Delegate to UI Manager First ---
            # The UI manager handles its own events (clicks, typing, etc.) and can
            # effectively "consume" them, preventing them from affecting the game.
            if ui_manager:
                ui_manager.handle_event(event)

            # --- 2. Process Game-World Input ---
            if event.type == pygame.KEYDOWN:
                # This block captures a single key press event for single-step mode
                # and updates the map for resolving diagonal movement.
                if event.key in (pygame.K_UP, pygame.K_w):
                    self.direction_event = Direction.UP
                    self._last_dir_pressed_map = Direction.UP
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    self.direction_event = Direction.DOWN
                    self._last_dir_pressed_map = Direction.DOWN
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    self.direction_event = Direction.LEFT
                    self._last_dir_pressed_map = Direction.LEFT
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    self.direction_event = Direction.RIGHT
                    self._last_dir_pressed_map = Direction.RIGHT

    def get_continuous_direction(self):
        """
        Gets the current direction from the keyboard's continuous state (keys being held down).
        This mirrors the original JS logic to prioritize the last-pressed axis for diagonals.
        """
        keys = pygame.key.get_pressed()

        # Determine horizontal and vertical components separately to handle opposing keys
        dir_h = Direction.NONE
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dir_h = Direction.LEFT
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            # If both left and right are pressed, cancel horizontal movement
            dir_h = (
                Direction.NONE if dir_h == Direction.LEFT else Direction.RIGHT
            )

        dir_v = Direction.NONE
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            dir_v = Direction.UP
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            # If both up and down are pressed, cancel vertical movement
            dir_v = Direction.NONE if dir_v == Direction.UP else Direction.DOWN

        # No movement if no keys are pressed or opposing keys cancel each other out
        if dir_h == Direction.NONE and dir_v == Direction.NONE:
            return Direction.NONE

        # If only one axis is active, return that direction
        if dir_h == Direction.NONE:
            return dir_v
        if dir_v == Direction.NONE:
            return dir_h

        # If both axes are active (diagonal), prioritize based on the last key physically pressed
        if self._last_dir_pressed_map in (Direction.UP, Direction.DOWN):
            return dir_v  # Prioritize vertical
        else:
            return dir_h  # Prioritize horizontal

    def get_direction(self, single_step_mode: bool):
        """
        A convenience method that returns the correct direction type based on the
        game's current movement mode.
        """
        if single_step_mode:
            return self.direction_event
        else:
            return self.get_continuous_direction()
