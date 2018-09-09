#!/usr/bin/env python

import sys
import argparse
import re
from msi_perkeyrgb.config import load_config, ConfigError, UnknownModelError
from msi_perkeyrgb.msi_keyboard import MSI_Keyboard, AVAILABLE_MSI_KEYMAPS
from msi_perkeyrgb.hidapi_wrapping import HIDLibraryError, HIDNotFoundError, HIDOpenError

VERSION = "1.0"
DEFAULT_ID = "1038:1122"


def main():
    parser = argparse.ArgumentParser(description='Tool to control per-key RGB keyboard backlighting on MSI laptops. https://github.com/Askannz/msi-perkeyrgb')
    parser.add_argument('-v', '--version', action='store_true', help='Prints version and exits.')
    parser.add_argument('-c', '--config', action='store', metavar='FILEPATH', help='Loads the configuration file located at FILEPATH. Refer to the README for syntax.')
    parser.add_argument('--id', action='store', metavar='VENDOR_ID:PRODUCT_ID', help='This argument allows you to specify the vendor/product id of your keyboard. You should not have to use this unless opening the keyboard fails with the default value. IDs are in hexadecimal format (example :  1038:1122)')

    args = parser.parse_args()

    if args.version:
        print("Version : %s" % VERSION)
    else:
        if not args.config:
            print("Please specify a config file to load. Refer to the README for syntax.")
        else:
            if args.id:
                id_str = args.id
                if not re.fullmatch("^[0-9a-f]{4}:[0-9a-f]{4}$", id_str):
                    print("Invalid syntax for vendor/product ID.")
                    sys.exit(1)
            else:
                id_str = DEFAULT_ID

            try:
                msi_keymap, colors_map, warnings = load_config(args.config)
            except UnknownModelError as e:
                print("Error parsing laptop model : unknown model %s" % str(e))
                print("Known models are :")
                for msi_models, _ in AVAILABLE_MSI_KEYMAPS:
                    for model in msi_models:
                        print(model)
                print("\nIf your laptop is not in this list, use the closest one (with a keyboard layout as similar as possible). This tool will only work with per-key RGB models.")
            except ConfigError as e:
                print("Error reading config file : %s" % str(e))
            else:

                # Printings config parse warnings
                for w in warnings:
                    print("Warning :", w)

                try:
                    kb = MSI_Keyboard(id_str, msi_keymap)
                except HIDLibraryError as e:
                    print("Cannot open HIDAPI library : %s. Make sure you have installed libhidapi on your system, then try running \"sudo ldconfig\" to regenerate library cache." % str(e))
                except HIDNotFoundError:
                    if not args.id:
                        print("No MSI keyboards with a known product/vendor IDs were found. However, if you think your keyboard should work with this program, you can try overriding the ID by adding the option \"--id VENDOR_ID:PRODUCT_ID\"")
                    else:
                        print("No USB device with ID %s found." % id_str)
                except HIDOpenError:
                    print("Cannot open keyboard. Possible causes :\n- You don't have permissions to open the HID device. Run this program as root, or give yourself read/write permissions to the corresponding /dev/hidraw*.\n- USB device with id %s is not a HID device." % id_str)
                else:
                    kb.set_color_all([0, 0, 0])
                    kb.set_colors(colors_map)
                    kb.refresh()


if __name__ == '__main__':
    main()