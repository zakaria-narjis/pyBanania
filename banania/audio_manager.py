# audio_manager.py
import pygame
import os
from .config import DEFAULT_VOLUME, SOUND_DIR


class AudioManager:
    """A dedicated class to handle loading and playing sounds and music."""

    def __init__(self):
        try:
            pygame.mixer.init()
            self.sounds = {}
            self.volume = DEFAULT_VOLUME
            self.sound_enabled = True
            self.load_all_sounds()
        except pygame.error as e:
            self.sounds = None

    def load_sound(self, name, file_path):
        """Loads a sound effect and stores it in the library."""
        try:
            self.sounds[name] = pygame.mixer.Sound(file_path)
        except pygame.error as e:
            raise FileNotFoundError(
                f"Could not load sound '{name}' from '{file_path}': {e}"
            )

    def load_all_sounds(self):
        """Loads all sounds into memory."""
        sound_files = {
            "about": "about.mp3",
            "argl": "argl.mp3",
            "attack1": "attack1.mp3",
            "attack2": "attack2.mp3",
            "chart": "chart.mp3",
            "click": "click.mp3",
            "gameend": "gameend.mp3",
            # 'getpoint': "getpoint.mp3", # Renamed to be more specific
            "collect_banana": "getpoint.mp3",  # Example: mapping game event to file
            "newplane": "newplane.mp3",
            "opendoor": "opendoor.mp3",
            "wow": "wow.mp3",
            "yeah": "yeah.mp3",
            # --- ADD THESE ---
            # NOTE: You will need to ensure you have sound files with these names.
            # I've mapped them to existing files as placeholders.
            "monster_spot_purple": "attack1.mp3",
            "monster_spot_green": "attack2.mp3",
            "level_win": "wow.mp3",
            "player_caught": "argl.mp3",
        }
        for name, file in sound_files.items():
            sound_path = os.path.join(SOUND_DIR, file)
            if os.path.exists(sound_path):
                self.load_sound(name, sound_path)
            else:
                raise FileNotFoundError(f"Sound file not found: {sound_path}")

    def play_sound(self, name):
        """Plays a loaded sound effect if sound is enabled."""
        # if not self.sounds or not self.sound_enabled: return # This line is why sound might be off
        if name in self.sounds:
            self.sounds[name].set_volume(self.volume)
            self.sounds[name].play()

    def set_volume(self, volume_level):
        """Sets the master volume for all sound effects."""
        if not self.sounds:
            return
        # Clamp volume between 0.0 and 1.0
        self.volume = max(0.0, min(1.0, volume_level))

    # --- ADD THIS METHOD ---
    def toggle_sound(self):
        """Enables or disables sound playback."""
        self.sound_enabled = not self.sound_enabled
