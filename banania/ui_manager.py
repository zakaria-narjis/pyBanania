# ui_manager.py
import pygame
from .config import (
    ImageID,
    DialogBox as DialogBoxType,
    ErrorCode,
)


# --- UI Colors ---
class Colors:
    """Defines colors used in the UI, matching the JS version."""

    BLACK = (0, 0, 0)
    DARK_GREY = (64, 64, 64)
    MED_GREY = (128, 128, 128)
    LIGHT_GREY = (212, 208, 200)
    WHITE = (255, 255, 255)
    BLUE = (10, 36, 106)
    RED = (255, 0, 0)
    GREEN = (0, 255, 0)
    DISABLED_GREY = (50, 50, 50)
    INPUT_BG = (255, 255, 255)
    INPUT_BORDER = (128, 128, 128)
    TITLE_TEXT = (255, 255, 255)


# --- UI Component Helper Classes ---


class Button:
    """A simple UI button that uses images for its states."""

    def __init__(
        self, rect, img_up_id, img_down_id, callback, resource_manager
    ):
        self.rect = pygame.Rect(rect)
        self.img_up = resource_manager.get_image(img_up_id)
        self.img_down = resource_manager.get_image(img_down_id)
        self.image = self.img_up
        self.callback = callback
        self.pressed = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.pressed = True
                self.image = self.img_down
                return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.pressed:
                if self.rect.collidepoint(event.pos) and self.callback:
                    self.callback()
                self.pressed = False
                self.image = self.img_up
                return True
        return False

    def draw(self, surface):
        surface.blit(self.image, self.rect.topleft)


class Label:
    """A simple text label."""

    def __init__(self, text, pos, font, color=Colors.BLACK, align="left"):
        self.text = text
        self.pos = pos
        self.font = font
        self.color = color
        self.align = align
        self.surface = self.font.render(self.text, True, self.color)

    def draw(self, surface):
        if self.align == "left":
            surface.blit(self.surface, self.pos)
        elif self.align == "right":
            surface.blit(
                self.surface,
                (self.pos[0] - self.surface.get_width(), self.pos[1]),
            )


class InputField:
    """A text input field for dialog boxes."""

    def __init__(self, rect, font, is_password=False):
        self.rect = pygame.Rect(rect)
        self.font = font
        self.is_password = is_password
        self.text = ""
        self.active = False
        self.cursor_visible = True
        self.cursor_timer = 0

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)

        if self.active and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key == pygame.K_RETURN:
                self.active = False
            else:
                self.text += event.unicode
            return True
        return False

    def update(self, dt):
        if self.active:
            self.cursor_timer += dt
            if self.cursor_timer >= 500:
                self.cursor_timer = 0
                self.cursor_visible = not self.cursor_visible

    def draw(self, surface):
        pygame.draw.rect(surface, Colors.INPUT_BG, self.rect)
        pygame.draw.rect(surface, Colors.INPUT_BORDER, self.rect, 1)
        text_surf = self.font.render(self.text, True, Colors.BLACK)
        surface.blit(text_surf, (self.rect.x + 5, self.rect.y + 5))

        if self.active and self.cursor_visible:
            cursor_pos = self.rect.x + 5 + text_surf.get_width()
            pygame.draw.line(
                surface,
                Colors.BLACK,
                (cursor_pos, self.rect.y + 5),
                (cursor_pos, self.rect.y + self.rect.height - 5),
            )

    def get_value(self):
        return self.text


# --- Base Dialog Box Class ---


class DialogBox:
    """Base class for all modal dialog boxes."""

    def __init__(self, rect, title, bg_image_id, resource_manager, uimanager):
        # ... (init method remains the same) ...
        self.rect = pygame.Rect(rect)
        screen_rect = pygame.display.get_surface().get_rect()
        self.rect.center = screen_rect.center

        self.title = title
        self.res = resource_manager
        self.ui_manager = uimanager
        self.bg_image = (
            self.res.get_image(bg_image_id)
            if bg_image_id is not None
            else None
        )

        self.title_font = pygame.font.SysFont("Tahoma", 14, bold=True)
        self.font = pygame.font.SysFont("Tahoma", 12)
        self.components = []

        self.dragging = False
        self.drag_offset = (0, 0)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                is_on_component = False
                relative_pos = (
                    event.pos[0] - self.rect.x,
                    event.pos[1] - self.rect.y,
                )
                for component in self.components:
                    if hasattr(
                        component, "rect"
                    ) and component.rect.collidepoint(relative_pos):
                        is_on_component = True
                        break
                if not is_on_component:
                    self.dragging = True
                    self.drag_offset = (
                        self.rect.x - event.pos[0],
                        self.rect.y - event.pos[1],
                    )

        elif event.type == pygame.MOUSEMOTION:
            if self.dragging:
                self.rect.x = event.pos[0] + self.drag_offset[0]
                self.rect.y = event.pos[1] + self.drag_offset[1]

                # --- FIX: Constrain the dialog to the screen boundaries ---
                self.rect.clamp_ip(pygame.display.get_surface().get_rect())
                # -----------------------------------------------------------

                return True  # Consume motion event while dragging

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False

        if self.dragging:
            return True

        is_mouse_event = event.type in (
            pygame.MOUSEBUTTONDOWN,
            pygame.MOUSEBUTTONUP,
            pygame.MOUSEMOTION,
        )
        if is_mouse_event and not self.rect.collidepoint(event.pos):
            return True

        relative_event = pygame.event.Event(event.type, event.dict)
        if is_mouse_event:
            relative_event.pos = (
                event.pos[0] - self.rect.x,
                event.pos[1] - self.rect.y,
            )

        for component in self.components:
            if hasattr(component, "handle_event") and component.handle_event(
                relative_event
            ):
                break
        return True

    def update(self, dt):
        for component in self.components:
            if hasattr(component, "update"):
                component.update(dt)

    def draw(self, surface):
        if self.bg_image:
            surface.blit(self.bg_image, self.rect.topleft)
        else:
            pygame.draw.rect(surface, Colors.LIGHT_GREY, self.rect)
            pygame.draw.rect(surface, Colors.DARK_GREY, self.rect, 2)

        # The title is drawn relative to the main surface, outside the dialog's top border.
        title_surf = self.title_font.render(
            self.title, True, Colors.TITLE_TEXT
        )
        surface.blit(title_surf, (self.rect.x + 5, self.rect.y + 2))

        # Components are drawn on a subsurface relative to the dialog's rect.
        dialog_surface = surface.subsurface(self.rect)
        for component in self.components:
            component.draw(dialog_surface)

    def close(self):
        self.ui_manager.active_dialog = None


# --- Specific Dialog Box Implementations ---


class ConfirmDialog(DialogBox):
    def __init__(self, resource_manager, uimanager, yes_callback, no_callback):
        super().__init__(
            (0, 0, 256, 154),
            "Confirm",
            ImageID.DIALOGBOX_CONFIRM,
            resource_manager,
            uimanager,
        )
        self.components.append(
            Label("Do you want to save the game?", (40, 35), self.font)
        )
        self.components.extend(
            [
                Button(
                    (20, 100, 65, 25),
                    ImageID.BTN_YES_UP,
                    ImageID.BTN_YES_DOWN,
                    yes_callback,
                    self.res,
                ),
                Button(
                    (100, 100, 65, 25),
                    ImageID.BTN_NO_UP,
                    ImageID.BTN_NO_DOWN,
                    no_callback,
                    self.res,
                ),
                Button(
                    (180, 100, 65, 25),
                    ImageID.BTN_CANCEL_UP,
                    ImageID.BTN_CANCEL_DOWN,
                    self.close,
                    self.res,
                ),
            ]
        )


class SaveLoadDialog(DialogBox):
    """Dialog for saving or loading with just a name field."""

    def __init__(self, resource_manager, uimanager, title, ok_callback):
        super().__init__(
            (0, 0, 256, 213),
            title,
            ImageID.DIALOGBOX_SAVELOAD,
            resource_manager,
            uimanager,
        )

        self.ok_callback = ok_callback
        # Adjusted component positions for better vertical alignment.
        self.components.append(Label("Save name:", (20, 60), self.font))
        self.name_input = InputField((100, 60, 120, 22), self.font)
        self.error_label = Label("", (20, 95), self.font, color=Colors.RED)

        self.components.extend([self.name_input, self.error_label])

        # Adjusted button Y-position to 160 to match the original.
        self.components.extend(
            [
                Button(
                    (40, 160, 65, 25),
                    ImageID.BTN_OK_UP,
                    ImageID.BTN_OK_DOWN,
                    self._on_ok,
                    self.res,
                ),
                Button(
                    (160, 160, 65, 25),
                    ImageID.BTN_CANCEL_UP,
                    ImageID.BTN_CANCEL_DOWN,
                    self.close,
                    self.res,
                ),
            ]
        )

    def _on_ok(self):
        result = self.ok_callback(self.name_input.get_value())
        if result == ErrorCode.SUCCESS:
            self.close()
        else:
            self.set_error(result)

    def set_error(self, code):
        error_messages = {
            ErrorCode.NOSAVE: "Error - there are no savegames to load!",
            ErrorCode.NOTFOUND: "Error - this save name couldn't be found.",
            ErrorCode.EMPTYNAME: "Error - please enter a save name.",
        }
        self.error_label.text = error_messages.get(code, "Unknown error")
        self.error_label.surface = self.font.render(
            self.error_label.text, True, self.error_label.color
        )


class LoadLevelDialog(DialogBox):
    def __init__(self, resource_manager, uimanager, game_state_accessor):
        super().__init__(
            (0, 0, 197, 273),
            "Load level",
            ImageID.DIALOGBOX_LOADLVL,
            resource_manager,
            uimanager,
        )

        username = game_state_accessor("username") or "- none -"
        self.components.append(Label("Player name:", (20, 30), self.font))
        self.components.append(Label(username, (100, 30), self.font))
        self.components.append(Label("Level, steps:", (20, 50), self.font))
        self.components.append(
            Label(
                "Level list component\nnot yet implemented.",
                (20, 80),
                self.font,
            )
        )
        self.components.extend(
            [
                Button(
                    (25, 220, 65, 25),
                    ImageID.BTN_OK_UP,
                    ImageID.BTN_OK_DOWN,
                    self.close,
                    self.res,
                ),
                Button(
                    (105, 220, 65, 25),
                    ImageID.BTN_CANCEL_UP,
                    ImageID.BTN_CANCEL_DOWN,
                    self.close,
                    self.res,
                ),
            ]
        )


class ChartsDialog(DialogBox):
    def __init__(self, resource_manager, uimanager, chart_data):
        super().__init__(
            (0, 0, 322, 346),
            "Charts",
            ImageID.DIALOGBOX_CHARTS,
            resource_manager,
            uimanager,
        )
        headers = [("rank", 21), ("level", 57), ("steps", 100), ("name", 150)]
        for text, x_pos in headers:
            self.components.append(Label(text, (x_pos, 47), self.font))

        for i, entry in enumerate(chart_data[:10]):
            y_pos = 68 + 18 * i
            self.components.extend(
                [
                    Label(str(i + 1), (41, y_pos), self.font, align="right"),
                    Label(
                        str(entry["level"]),
                        (87, y_pos),
                        self.font,
                        align="right",
                    ),
                    Label(
                        str(entry["steps"]),
                        (140, y_pos),
                        self.font,
                        align="right",
                    ),
                    Label(entry["name"], (155, y_pos), self.font),
                ]
            )
        self.components.append(
            Button(
                (125, 300, 65, 25),
                ImageID.BTN_OK_UP,
                ImageID.BTN_OK_DOWN,
                self.close,
                self.res,
            )
        )


# --- Menu Data Structures ---


class SubMenu:
    def __init__(self, width, dd_width, name, options):
        self.width = width
        self.offset_line = 9
        self.offset_text = 17
        self.dd_width = dd_width
        self.dd_height = 6 + sum(
            self.offset_line if opt["line"] else self.offset_text
            for opt in options
        )
        self.name = name
        self.options = options


class Menu:
    def __init__(self, offset_x, offset_y, height, submenus):
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.height = height
        self.width = sum(sm.width for sm in submenus)
        self.submenus = submenus


# --- Main UI Manager Class ---


class UIManager:
    def __init__(self, resource_manager, game_logic_callbacks):
        self.res = resource_manager
        self.game_callbacks = game_logic_callbacks
        self.active_dialog = None

        self.main_buttons_pressed = [False, False, False]
        self.berti_blink_time = 103

        self.menu_font = pygame.font.SysFont("Tahoma", 11)
        self.selected_menu_item = -1
        self._init_menus()

        self.hotkey_map = {pygame.K_F2: 0, pygame.K_F5: 4}

    def _init_menus(self):
        def can_always():
            return True

        def has_storage():
            return self.game_callbacks["get_state"]("has_storage")

        def can_save():
            return self.game_callbacks["get_state"]("can_save")

        arr_options1 = [
            {
                "name": "New",
                "effect_id": 0,
                "on": can_always,
                "hotkey": "F2",
                "check": 0,
                "line": False,
            },
            {
                "name": "Load Game...",
                "effect_id": 1,
                "on": has_storage,
                "hotkey": "",
                "check": 0,
                "line": False,
            },
            {
                "name": "Save",
                "effect_id": 2,
                "on": can_save,
                "hotkey": "",
                "check": 0,
                "line": False,
            },
            {
                "name": "Pause",
                "effect_id": 3,
                "on": can_always,
                "hotkey": "",
                "check": 1,
                "line": False,
            },
        ]
        arr_options2 = [
            {
                "name": "Single steps",
                "effect_id": 4,
                "on": can_always,
                "hotkey": "F5",
                "check": 1,
                "line": False,
            },
            {
                "name": "Sound",
                "effect_id": 5,
                "on": can_always,
                "hotkey": "",
                "check": 1,
                "line": False,
            },
            {
                "name": "",
                "effect_id": -1,
                "on": can_always,
                "hotkey": "",
                "check": 0,
                "line": True,
            },
            {
                "name": "Load Level",
                "effect_id": 6,
                "on": has_storage,
                "hotkey": "",
                "check": 0,
                "line": False,
            },
            {
                "name": "Charts",
                "effect_id": 8,
                "on": has_storage,
                "hotkey": "",
                "check": 0,
                "line": False,
            },
        ]

        self.main_menu = Menu(
            1,
            2,
            17,
            [
                SubMenu(43, 100, "Game", arr_options1),
                SubMenu(55, 120, "Options", arr_options2),
            ],
        )

    def _trigger_menu_effect(self, effect_id):
        if effect_id == 0:
            if self.game_callbacks["get_state"]("can_save"):
                self.show_dialog(
                    DialogBoxType.CONFIRM,
                    yes_callback=self.game_callbacks["save_and_new"],
                    no_callback=lambda: (
                        self.game_callbacks["new"](),
                        self.active_dialog.close(),
                    ),
                )
            else:
                self.game_callbacks["new"]()
        elif effect_id == 1:
            self.show_dialog(DialogBoxType.LOAD)
        elif effect_id == 2:
            self.show_dialog(DialogBoxType.SAVE)
        elif effect_id == 3:
            self.game_callbacks["toggle_pause"]()
        elif effect_id == 4:
            self.game_callbacks["toggle_single_steps"]()
        elif effect_id == 5:
            self.game_callbacks["toggle_sound"]()
        elif effect_id == 6:
            self.show_dialog(DialogBoxType.LOADLVL)
        elif effect_id == 8:
            self.show_dialog(DialogBoxType.CHARTS)

        self.selected_menu_item = -1

    def handle_event(self, event):
        if self.active_dialog:
            self.active_dialog.handle_event(event)
            return

        if event.type == pygame.KEYDOWN and event.key in self.hotkey_map:
            self._trigger_menu_effect(self.hotkey_map[event.key])
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # --- MODIFICATION START ---
            # Check for volume bar click first. If it returns True, the event is handled.
            if self._handle_volume_click(event.pos):
                return
            # --- MODIFICATION END ---
            self._handle_menu_click(event.pos)
            self._handle_main_buttons_click(event.pos)

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.main_buttons_pressed = [False, False, False]

    def update(self, dt):
        if self.active_dialog:
            self.active_dialog.update(dt)

    # --- NEW METHOD START ---
    def _handle_volume_click(self, mouse_pos):
        """Checks for clicks on the volume bar and updates the volume."""
        vb_rect = pygame.Rect(400, 2, 100, 17)
        if vb_rect.collidepoint(mouse_pos):
            # Calculate volume (0.0 to 1.0) based on the horizontal click position
            relative_x = mouse_pos[0] - vb_rect.x
            new_volume = relative_x / vb_rect.width

            # Clamp the value between 0.0 and 1.0 to be safe
            new_volume = max(0.0, min(1.0, new_volume))

            # Use the callback to set the volume in the audio manager
            set_volume_callback = self.game_callbacks.get("set_volume")
            if set_volume_callback:
                set_volume_callback(new_volume)

            return True  # Indicate that the event has been handled
        return False  # The click was not on the volume bar

    # --- NEW METHOD END ---

    def _handle_main_buttons_click(self, mouse_pos):
        button_rects = [
            pygame.Rect(219, 35, 30, 30),
            pygame.Rect(253, 35, 30, 30),
            pygame.Rect(287, 35, 30, 30),
        ]
        for i, rect in enumerate(button_rects):
            if rect.collidepoint(mouse_pos):
                self.main_buttons_pressed[i] = True
                if i == 0:
                    self.game_callbacks.get("previous_level", lambda: None)()
                elif i == 1:
                    self.game_callbacks.get("reset_level", lambda: None)()
                elif i == 2:
                    self.game_callbacks.get("next_level", lambda: None)()
                break

    def _handle_menu_click(self, mouse_pos):
        menu = self.main_menu
        x_offset = menu.offset_x

        for i, submenu in enumerate(menu.submenus):
            if pygame.Rect(
                x_offset, menu.offset_y, submenu.width, menu.height
            ).collidepoint(mouse_pos):
                self.selected_menu_item = (
                    -1 if self.selected_menu_item == i else i
                )
                return
            x_offset += submenu.width

        if self.selected_menu_item != -1:
            submenu = menu.submenus[self.selected_menu_item]
            x_offset = menu.offset_x + sum(
                sm.width for sm in menu.submenus[: self.selected_menu_item]
            )
            dd_rect = pygame.Rect(
                x_offset,
                menu.offset_y + menu.height,
                submenu.dd_width,
                submenu.dd_height,
            )

            if not dd_rect.collidepoint(mouse_pos):
                self.selected_menu_item = -1
                return

            y_offset = menu.offset_y + menu.height + 4
            for option in submenu.options:
                item_height = (
                    submenu.offset_line
                    if option["line"]
                    else submenu.offset_text
                )
                if not option["line"]:
                    opt_rect = pygame.Rect(
                        x_offset, y_offset, submenu.dd_width, item_height
                    )
                    if opt_rect.collidepoint(mouse_pos) and option["on"]():
                        self._trigger_menu_effect(option["effect_id"])
                        return
                y_offset += item_height

    def show_dialog(self, dialog_type, **kwargs):
        if dialog_type == DialogBoxType.CONFIRM:
            self.active_dialog = ConfirmDialog(
                self.res, self, kwargs["yes_callback"], kwargs["no_callback"]
            )
        elif dialog_type == DialogBoxType.SAVE:
            self.active_dialog = SaveLoadDialog(
                self.res, self, "Save game", self.game_callbacks["save"]
            )
        elif dialog_type == DialogBoxType.LOAD:
            self.active_dialog = SaveLoadDialog(
                self.res, self, "Load game", self.game_callbacks["load"]
            )
        elif dialog_type == DialogBoxType.LOADLVL:
            self.active_dialog = LoadLevelDialog(
                self.res, self, self.game_callbacks["get_state"]
            )
        elif dialog_type == DialogBoxType.CHARTS:
            chart_data = self.game_callbacks["get_charts_data"]()
            self.active_dialog = ChartsDialog(self.res, self, chart_data)

        self.selected_menu_item = -1

    def draw_all(self, surface):
        game_state = self.game_callbacks["get_full_state"]()
        self.draw_volume_bar(
            surface, game_state["volume"], game_state["sound_on"]
        )
        self.draw_main_buttons(surface, game_state["buttons_activated"])
        self.draw_menu(surface, game_state)
        if self.active_dialog:
            self.active_dialog.draw(surface)

    def draw_main_buttons(self, surface, activated_buttons):
        if not activated_buttons[0]:
            surface.blit(
                self.res.get_image(ImageID.BTN_PREV_DISABLED), (219, 35)
            )
        else:
            img = (
                ImageID.BTN_PREV_DOWN
                if self.main_buttons_pressed[0]
                else ImageID.BTN_PREV_UP
            )
            surface.blit(self.res.get_image(img), (219, 35))

        if self.main_buttons_pressed[1]:
            surface.blit(self.res.get_image(ImageID.BTN_BERTI_DOWN), (253, 35))
        else:
            if self.berti_blink_time >= 100:
                surface.blit(
                    self.res.get_image(ImageID.BTN_BERTI_BLINK_UP), (253, 35)
                )
                self.berti_blink_time -= 1
                if self.berti_blink_time < 100:
                    self.berti_blink_time = 95
            else:
                surface.blit(
                    self.res.get_image(ImageID.BTN_BERTI_UP), (253, 35)
                )
                self.berti_blink_time -= 1
                if self.berti_blink_time < 0:
                    self.berti_blink_time = 103

        if not activated_buttons[2]:
            surface.blit(
                self.res.get_image(ImageID.BTN_NEXT_DISABLED), (287, 35)
            )
        else:
            img = (
                ImageID.BTN_NEXT_DOWN
                if self.main_buttons_pressed[2]
                else ImageID.BTN_NEXT_UP
            )
            surface.blit(self.res.get_image(img), (287, 35))

    def draw_menu(self, surface, game_state):
        menu = self.main_menu
        mouse_pos = pygame.mouse.get_pos()

        submenu_offset = 0
        for sm in menu.submenus:
            text_surf = self.menu_font.render(sm.name, True, Colors.BLACK)
            surface.blit(
                text_surf,
                (menu.offset_x + submenu_offset + 6, menu.offset_y + 3),
            )
            submenu_offset += sm.width

        if self.selected_menu_item != -1:
            submenu = menu.submenus[self.selected_menu_item]
            x_pos = menu.offset_x + sum(
                sm.width for sm in menu.submenus[: self.selected_menu_item]
            )
            dd_rect = pygame.Rect(
                x_pos,
                menu.offset_y + menu.height + 1,
                submenu.dd_width,
                submenu.dd_height,
            )

            pygame.draw.rect(surface, Colors.LIGHT_GREY, dd_rect)
            pygame.draw.line(
                surface, Colors.WHITE, dd_rect.topleft, dd_rect.topright
            )
            pygame.draw.line(
                surface, Colors.WHITE, dd_rect.topleft, dd_rect.bottomleft
            )
            pygame.draw.line(
                surface,
                Colors.DARK_GREY,
                (dd_rect.right - 1, dd_rect.top),
                (dd_rect.right - 1, dd_rect.bottom),
            )
            pygame.draw.line(
                surface,
                Colors.DARK_GREY,
                (dd_rect.left, dd_rect.bottom - 1),
                (dd_rect.right, dd_rect.bottom - 1),
            )

            y_offset = dd_rect.top + 4
            for option in submenu.options:
                if option["line"]:
                    pygame.draw.line(
                        surface,
                        Colors.MED_GREY,
                        (dd_rect.left + 3, y_offset + 3),
                        (dd_rect.right - 3, y_offset + 3),
                    )
                    pygame.draw.line(
                        surface,
                        Colors.WHITE,
                        (dd_rect.left + 3, y_offset + 4),
                        (dd_rect.right - 3, y_offset + 4),
                    )
                    y_offset += submenu.offset_line
                else:
                    opt_rect = pygame.Rect(
                        dd_rect.left,
                        y_offset,
                        submenu.dd_width,
                        submenu.offset_text,
                    )
                    is_hovered = opt_rect.collidepoint(mouse_pos)
                    is_enabled = option["on"]()

                    if is_hovered and is_enabled:
                        pygame.draw.rect(
                            surface,
                            Colors.BLUE,
                            (
                                dd_rect.left + 3,
                                y_offset,
                                submenu.dd_width - 6,
                                submenu.offset_text,
                            ),
                        )

                    text_color = (
                        Colors.MED_GREY
                        if not is_enabled
                        else (Colors.WHITE if is_hovered else Colors.BLACK)
                    )
                    text_surf = self.menu_font.render(
                        option["name"], True, text_color
                    )
                    surface.blit(text_surf, (dd_rect.left + 20, y_offset + 1))

                    is_checked = (
                        (option["effect_id"] == 3 and game_state["paused"])
                        or (
                            option["effect_id"] == 5 and game_state["sound_on"]
                        )
                        or (
                            option["effect_id"] == 4
                            and game_state["single_steps"]
                        )
                    )

                    if option["check"] != 0 and is_checked:
                        surface.blit(
                            self.res.get_image(ImageID.CHECKBOX_CHECKED),
                            (dd_rect.left + 6, y_offset + 4),
                        )
                    y_offset += submenu.offset_text

    def draw_volume_bar(self, surface, volume, sound_enabled):
        vb_rect = pygame.Rect(400, 2, 100, 17)
        for i in range(0, vb_rect.width, 2):
            ratio = i / vb_rect.width
            line_height = round(vb_rect.height * ratio)

            if i < volume * vb_rect.width:
                if sound_enabled:
                    color = (
                        int(
                            Colors.GREEN[0] * (1 - ratio)
                            + Colors.RED[0] * ratio
                        ),
                        int(
                            Colors.GREEN[1] * (1 - ratio)
                            + Colors.RED[1] * ratio
                        ),
                        int(
                            Colors.GREEN[2] * (1 - ratio)
                            + Colors.RED[2] * ratio
                        ),
                    )
                else:
                    color = Colors.DISABLED_GREY
            else:
                color = Colors.WHITE

            pygame.draw.line(
                surface,
                color,
                (vb_rect.x + i, vb_rect.bottom),
                (vb_rect.x + i, vb_rect.bottom - line_height),
            )
