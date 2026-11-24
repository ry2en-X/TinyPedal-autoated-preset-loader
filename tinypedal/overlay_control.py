#  TinyPedal is an open-source overlay application for racing simulation.
#  Copyright (C) 2022-2026 TinyPedal developers, see contributors.md file
#
#  This file is part of TinyPedal.
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
Overlay Control
"""

import json
import logging
import os
import threading
from time import sleep

from . import api, app_signal, cfg, overlay_signal, realtime_state

logger = logging.getLogger(__name__)


class OverlayToggle:
    """Overlay state toggle"""

    __slots__ = ()

    def vr(self):
        """Toggle VR state"""
        self.__toggle_option("vr_compatibility")
        overlay_signal.iconify.emit(cfg.overlay["vr_compatibility"])

    def lock(self):
        """Toggle lock state"""
        self.__toggle_option("fixed_position")
        overlay_signal.locked.emit(cfg.overlay["fixed_position"])

    def hide(self):
        """Toggle hide state"""
        self.__toggle_option("auto_hide")

    def grid(self):
        """Toggle grid move state"""
        self.__toggle_option("enable_grid_move")

    @staticmethod
    def __toggle_option(option_name: str):
        """Toggle option"""
        cfg.overlay[option_name] = not cfg.overlay[option_name]
        cfg.save()


class OverlayControl:
    """Overlay control"""

    __slots__ = (
        "_event",
        "_last_active_state",
        "_last_hide_state",
        "_last_vehicle_name",
        "_last_vehicle_model",
        "_stopped",
        "toggle",
    )

    def __init__(self):
        self.toggle = OverlayToggle()
        self._stopped = True
        self._event = threading.Event()

        self._last_active_state = None
        self._last_hide_state = None
        self._last_vehicle_name = ""
        self._last_vehicle_model = ""

    def enable(self):
        """Enable overlay control"""
        if self._stopped:
            self._stopped = False
            self._event.clear()
            threading.Thread(target=self.__updating, daemon=True).start()
            logger.info("ENABLED: overlay control")

    def disable(self):
        """Disable overlay control"""
        self._event.set()
        while not self._stopped:
            sleep(0.01)

    def __updating(self):
        """Update global state"""
        _event_wait = self._event.wait

        while not _event_wait(0.2):
            # Read state
            active = api.read.state.active()
            paused = api.read.state.paused()
            resets = api.read.state.resets()
            hidden = cfg.overlay["auto_hide"] and not active

            # Update state
            realtime_state.active = active
            realtime_state.paused = paused
            realtime_state.resets = resets

            # Auto hide state check
            if self._last_hide_state != hidden:
                self._last_hide_state = hidden
                realtime_state.hidden = hidden
                overlay_signal.hidden.emit(hidden)

            # Active state check
            if self._last_active_state != active:
                self._last_active_state = active

                # Update auto load state when player enters track
                if active and cfg.application["enable_auto_load_preset"]:
                    current_vehicle_name = api.read.vehicle.team_name()
                    current_vehicle_model = api.read.vehicle.vehicle_model()
                    self._last_vehicle_name = current_vehicle_name
                    self._last_vehicle_model = current_vehicle_model

                    logger.info(
                        "VEHICLE DETECTED: name = %s | model = %s",
                        api.read.vehicle.team_name(),
                        api.read.vehicle.vehicle_model(),
                    )

                    self.__check_preset_class()

                # Set overlay timer state
                overlay_signal.paused.emit(not active)

            # Vehicle change check while already on track
            if active and cfg.application["enable_auto_load_preset"]:
                current_vehicle_name = api.read.vehicle.team_name()
                current_vehicle_model = api.read.vehicle.vehicle_model()

                if (
                    current_vehicle_name != self._last_vehicle_name
                    or (
                        current_vehicle_model
                        and current_vehicle_model != self._last_vehicle_model
                    )
                ):
                    self._last_vehicle_name = current_vehicle_name
                    self._last_vehicle_model = current_vehicle_model

                    logger.info(
                        "VEHICLE CHANGE: %s",
                        current_vehicle_name,
                    )

                    self.__check_preset_class()

            else:
                self._last_vehicle_name = ""
                self._last_vehicle_model = ""

        self._stopped = True
        logger.info("DISABLED: overlay control")

    def __check_preset_class(self) -> bool:
        """Check vehicle model-specific preset first, then fall back to class preset."""

        vehicle_name = api.read.vehicle.team_name()
        vehicle_model = api.read.vehicle.vehicle_model()

        if not vehicle_model:
            logger.warning(
                "AUTOLOADING: could not determine vehicle model for %s",
                vehicle_name,
                )
            return self.__check_preset_class_fallback()

        logger.info(
            "AUTOLOADING: vehicle model detected: %s",
            vehicle_model,
        )

        # Load vehicle preset mapping
        application_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        mapping_file = os.path.join(
            application_root,
            "settings",
            "vehicle_presets.json",
        )

        try:
            with open(mapping_file, "r", encoding="utf-8") as file:
                vehicle_mapping = json.load(file)

        except FileNotFoundError:
            logger.warning(
                "AUTOLOADING: vehicle_presets.json not found: %s",
                mapping_file,
            )
            return self.__check_preset_class_fallback()

        except (OSError, json.JSONDecodeError) as error:
            logger.error(
                "AUTOLOADING: could not read vehicle_presets.json: %s",
                error,
            )
            return self.__check_preset_class_fallback()

        # Search all vehicle classes
        for class_name, vehicles in vehicle_mapping.items():

            if not isinstance(vehicles, dict):
                continue

            for mapped_model, preset_path in vehicles.items():

                # Exact model comparison
                if mapped_model.casefold() != vehicle_model.casefold():
                    continue

                # Convert JSON path to Windows-compatible path
                preset_path = preset_path.replace("/", os.sep)

                full_preset_path = os.path.join(
                    os.path.dirname(mapping_file),
                    preset_path,
                )

                if not os.path.isfile(full_preset_path):
                    logger.warning(
                        "AUTOLOADING: vehicle model %s matched %s, "
                        "but preset does not exist: %s",
                        vehicle_model,
                        mapped_model,
                        full_preset_path,
                    )
                    return False

                logger.info(
                    "AUTOLOADING: MATCH: %s -> %s",
                    vehicle_model,
                    preset_path,
                )

                preset_filename = os.path.relpath(
                    full_preset_path,
                    cfg.path.settings,
                )
                self.__auto_load_preset(vehicle_model, preset_filename)

                return True

        # No vehicle mapping found
        logger.info(
            "AUTOLOADING: no vehicle preset mapping found for model %s",
            vehicle_model,
        )

        return self.__check_preset_class_fallback()


    def __check_preset_class_fallback(self) -> bool:
        """Fallback to TinyPedal's original class-based preset loading."""

        class_name = api.read.vehicle.class_name()
        class_data = cfg.user.classes.get(class_name)

        if class_data is None:
            return False

        class_preset_name = class_data["preset"]

        if class_preset_name == "":
            return False

        preset_name = cfg.get_primary_preset_name(class_preset_name)

        self.__auto_load_preset(class_name, preset_name)

        return True

    def __auto_load_preset(self, target_name, preset_name):
        """Auto load preset."""

        logger.info(
            "AUTOLOADING: %s detected, attempt loading %s",
            target_name,
            preset_name,
        )

        # Abort if preset file does not exist
        if preset_name == "":
            logger.info(
                "AUTOLOADING: %s not found, abort auto loading",
                preset_name,
            )
            return

        # Check if already loaded
        if cfg.is_loaded(preset_name):
            logger.info(
                "AUTOLOADING: %s already loaded",
                preset_name,
            )
            return

        # Update preset name & signal reload
        cfg.set_next_to_load(preset_name)
        app_signal.reload.emit(True)
