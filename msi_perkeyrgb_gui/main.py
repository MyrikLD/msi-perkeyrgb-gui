#!/usr/bin/env python

import argparse
import logging
import os
import sys

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")

from .config import load_steady, ConfigError
from .gui_handlers import SetupHandler, ConfigHandler
from .msikeyboard import MSIKeyboard, UnknownModelError
from .parsing import (
    parse_usb_id,
    parse_preset,
    UnknownIdError,
    UnknownPresetError,
)

from gi.repository import Gtk

__version__ = "3.0"
DEFAULT_ID = "1038:1122"
DEFAULT_MODEL = "GP75"  # Default laptop model if nothing specified

logging.basicConfig()
logging.getLogger().setLevel(logging.INFO)
log = logging.getLogger(__name__)


def run_gui(model, colors_filename, usb_id, setup=False):
    builder = Gtk.Builder()

    builder.add_from_file(os.path.join(os.path.dirname(__file__), "ui.glade"))
    kb_image = builder.get_object("kb_image")
    color_selector = builder.get_object("color_selector")

    if setup:
        h = SetupHandler(model, kb_image)
    else:
        h = ConfigHandler(
            model,
            kb_image,
            color_selector,
            colors_filename,
            usb_id,
        )
    builder.connect_signals(h)

    window = builder.get_object("GtkWindow")
    window.set_title(f"{model} Keyboard {__version__}")
    window.show_all()

    Gtk.main()


def main():
    parser = argparse.ArgumentParser(
        description="Tool to control per-key RGB keyboard backlighting on MSI laptops. https://github.com/Askannz/msi-perkeyrgb"
    )
    parser.add_argument(
        "-v", "--version", action="store_true", help="Prints version and exits."
    )
    parser.add_argument(
        "-c",
        "--config",
        action="store",
        metavar="FILEPATH",
        help='Loads the configuration file located at FILEPATH. Refer to the README for syntax. If set to "-", '
        "the configuration file is read from the standard input (stdin) instead.",
        default="config.msic",
    )
    parser.add_argument(
        "-d", "--disable", action="store_true", help="Disable RGB lighting."
    )
    parser.add_argument(
        "--id",
        action="store",
        metavar="VENDOR_ID:PRODUCT_ID",
        help="This argument allows you to specify the vendor/product id of your keyboard. "
        "You should not have to use this unless opening the keyboard fails with the default value. "
        "IDs are in hexadecimal format (example :  1038:1122)",
    )
    parser.add_argument(
        "--list-presets",
        action="store_true",
        help="List available presets for the given laptop model.",
    )
    parser.add_argument(
        "-p", "--preset", action="store", help="Use vendor preset (see --list-presets)."
    )
    parser.add_argument(
        "-m",
        "--model",
        action="store",
        help="Set laptop model (see --list-models). If not specified, will use %s as default."
        % DEFAULT_MODEL,
    )
    parser.add_argument(
        "--list-models", action="store_true", help="List available laptop models."
    )
    parser.add_argument("--setup", action="store_true", help="Open app in setup mode.")
    parser.add_argument(
        "-s",
        "--steady",
        action="store",
        metavar="HEXCOLOR",
        help="Set all of the keyboard to a steady html color. ex. 00ff00 for green",
    )

    args = parser.parse_args()

    if args.version:
        print("Version: %s" % __version__)
        sys.exit(1)

    if args.list_models:
        print("Available laptop models are :")
        for msi_models, _ in MSIKeyboard.available_msi_keymaps:
            for model in msi_models:
                print(model)
        print(
            "\nIf your laptop is not in this list, use the closest one "
            "(with a keyboard layout as similar as possible). "
            "This tool will only work with per-key RGB models."
        )
        sys.exit(1)

    # Parse laptop model
    if not args.model:
        print("No laptop model specified, using %s as default." % DEFAULT_MODEL)
        msi_model = DEFAULT_MODEL
    else:
        try:
            msi_model = MSIKeyboard.parse_model(args.model)
        except UnknownModelError:
            print("Unknown MSI model : %s" % args.model)
            sys.exit(1)

    # Parse USB vendor/product ID
    if not args.id:
        usb_id = parse_usb_id(DEFAULT_ID)
    else:
        try:
            usb_id = parse_usb_id(args.id)
        except UnknownIdError:
            print("Unknown vendor/product ID : %s" % args.id)
            sys.exit(1)

    # Loading presets
    msi_presets = MSIKeyboard.get_model_presets(msi_model)

    if args.list_presets:
        if msi_presets == {}:
            print("No presets available for %s." % msi_model)
        else:
            print("Available presets for %s:" % msi_model)
            for preset in msi_presets.keys():
                print("\t- %s" % preset)
        sys.exit(1)

    # Loading keymap
    msi_keymap = MSIKeyboard.get_model_keymap(msi_model)

    # Loading keyboard
    kb = MSIKeyboard.get(usb_id, msi_keymap, msi_presets)
    if not kb:
        sys.exit(1)

    # If user has requested disabling
    if args.disable:
        kb.set_color_all([0, 0, 0])
        kb.refresh()
        sys.exit(1)

    # If user has requested a preset
    elif args.preset:
        try:
            preset = parse_preset(args.preset, msi_presets)
        except UnknownPresetError:
            print(
                f"Preset {args.preset} not found for model {msi_model}. "
                f"Use --list-presets for available options"
            )
            sys.exit(1)

        kb.set_preset(preset)
        kb.refresh()
        sys.exit(1)

    # If user has requested to display a steady color
    elif args.steady:
        try:
            colors_map, warnings = load_steady(args.steady, msi_keymap)
        except ConfigError as e:
            print("Error preparing steady color : %s" % str(e))
            sys.exit(1)
        kb.set_colors(colors_map)
        kb.refresh()
        sys.exit(1)

    # If user has not requested anything
    else:
        if not os.path.isfile(args.config):
            with open(args.config, "w") as i:
                with open(
                    os.path.join(os.path.dirname(__file__), "configs", "default.msic")
                ) as o:
                    print(
                        f"Config file {args.config} not found, new created from default"
                    )
                    i.write(o.read())
        run_gui(msi_model, args.config, usb_id, args.setup)


if __name__ == "__main__":
    main()
