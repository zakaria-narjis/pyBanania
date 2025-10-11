# Banania - Pygame Edition

A faithful recreation of the 1992 Windows 3.x game "Banania", remade in Python with Pygame.

## What is Banania

Banania is a video game for Windows 3.x that was released in 1992. It was created by the programmer Rüdiger Appel and the comics artist Markuß Golschinski.

The game was published by Data Becker, a German company that went out of business in 2014. Because of that, the original Pascal source code is most likely lost.

## About This Project

This project is a port of Banania to Python and Pygame. It is heavily based on the fantastic JavaScript recreation by **Benjamin Richner**.

Special thanks to him for reverse-engineering the original game's sprites, sounds, and logic, and for making his work available. This Pygame version would not have been possible without his efforts.

You can find his original JavaScript version here: **[https://github.com/BenjaminRi/Banania](https://github.com/BenjaminRi/Banania)**.

## How to Run

To run the game locally, you will need Python and Pygame installed.

1.  Clone this repository to your local machine.
2.  Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Run the game:
    ```bash
    python run_game.py
    ```

## How to Play

Use the **arrow keys** to move Berti. To complete a level, you must collect all the banana peels while avoiding the green and purple monsters.

* **Keys** unlock doors with the corresponding number.
* **Light blue blocks** can be pushed in unlimited numbers.
* **Dark blue diamond blocks** can only be pushed one at a time.
* **Grey blocks** cannot be moved.

## Creating an Executable

You can create a standalone Windows executable using PyInstaller. First, make sure you have an icon file at the specified path (`assets/berti.ico`). Then, run the following command from the project's root directory:

```bash
pyinstaller --onefile --windowed --add-data "assets;assets" --name "Banania" --icon="assets/berti.ico" main.py
```