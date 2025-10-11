# main.py
import pygame
import sys
import json
from banania.config import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    UPS,
    LEVELS_PATH,
    ErrorCode,
)
from banania.game_engine import Game
from banania.renderer import Renderer
from banania.input_handler import InputHandler
from banania.audio_manager import AudioManager
from banania.ui_manager import UIManager


def load_all_levels(path):
    """Loads the level data from the specified JSON file."""
    try:
        with open(path, "r") as f:
            data = json.load(f)
            return data["levels"]
    except FileNotFoundError:
        sys.exit()
    except (json.JSONDecodeError, KeyError):
        sys.exit()


def main():
    """The main function to run the game."""
    pygame.init()

    # Setup the display
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Berti - Python Edition")
    clock = pygame.time.Clock()

    # --- Initialize all game components ---

    # CORRECTED ORDER: Game logic must be created before the UI that needs to call it.

    renderer = Renderer()
    audio_manager = AudioManager()

    all_levels = load_all_levels(LEVELS_PATH)

    # 1. Create the Game instance FIRST
    game = Game(all_levels, audio_manager)

    # 2. Create the dictionary of callbacks for the UI Manager
    # This acts as a bridge, allowing the UI to safely interact with the game engine.
    game_logic_callbacks = {
        # State getters
        "get_state": game.get_state,
        "get_full_state": game.get_full_state,
        "get_charts_data": game.get_charts_data,
        # Action performers
        "new": game.new_game_action,
        "save": game.save_game_action,
        "load": game.load_game_action,
        "change_password": game.change_password_action,  # Obsolete, but kept for safety
        "toggle_pause": game.toggle_pause,
        "toggle_sound": game.toggle_sound,
        "toggle_single_steps": game.toggle_single_steps,
        # --- ADD THESE THREE LINES ---
        "previous_level": game.previous_level,
        "reset_level": game.reset_level,
        "next_level": game.next_level,
        # -----------------------------
        "save_and_new": None,
        "set_volume": audio_manager.set_volume,
    }

    # 3. Create the UI Manager, passing in the callbacks
    ui_manager = UIManager(renderer, game_logic_callbacks)

    # Now, define the save_and_new callback which needs a reference to ui_manager
    def save_and_new_flow():
        # Define what happens when the save dialog's "OK" is successful
        # --- ADAPT THIS FUNCTION ---
        def on_save_success(save_name):  # Password argument removed
            result = game.save_game_action(save_name)  # Pass only save_name
            if result == ErrorCode.SUCCESS:
                game.new_game_action()
            return result

        # -------------------------
        # Show the save dialog and pass our custom success handler to it
        ui_manager.active_dialog = UIManager.SaveLoadDialog(
            renderer, ui_manager, "Save game", on_save_success
        )

    # Assign the fully defined flow to the callback dictionary
    game_logic_callbacks["save_and_new"] = save_and_new_flow

    # Load initial level and create input handler
    input_handler = InputHandler()
    game.is_initialized = True

    # --- Main Game Loop ---
    is_running = True
    while is_running:
        # 1. Process Input
        # We now get the state directly from the game object via the callback
        _ = game.get_full_state()

        input_handler.process_events(ui_manager)
        if input_handler.quit_requested:
            is_running = False

        # 2. Update Game Logic and Animations
        if ui_manager.active_dialog is None:
            game.update(input_handler)
            renderer.update_all_animations(game)

        # Pass delta time (in ms) to UI for animations like blinking cursors
        ui_manager.update(clock.get_time())

        # 3. Render Graphics
        renderer.draw(screen, game)
        ui_manager.draw_all(screen)

        # 4. Update display and control framerate
        pygame.display.flip()
        clock.tick(UPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
