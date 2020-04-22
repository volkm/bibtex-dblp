"""
Configuration.
"""

import json
import logging
from pathlib import Path

import appdirs

from bibtex_dblp.dblp_api import BIB_FORMATS, CONDENSED

# Application settings
APP_NAME = "bibtex-dblp"
CONFIG_DIR = Path(appdirs.user_config_dir(APP_NAME))
CONFIG_FILE = CONFIG_DIR / "config.json"

## Default values (in case they're missing in the .json file)
DEFAULT_CONFIG = {
    "format": CONDENSED,
    "max_search_results": 30,
}

## Allowed values for each field. None means everything is allowed.
ALLOWED_VALUES = {"format": BIB_FORMATS}


def _is_valid(cfg, config_file):
    """Checks whether the given cfg is a valid config"""
    allowed_keys = DEFAULT_CONFIG.keys()
    for key in cfg.keys():
        if key not in allowed_keys:
            logging.error(
                f"{config_file}:\nConfiguration key {key} is unknown.\nKnown keys are {', '.join(allowed_keys)}"
            )
            if key in ALLOWED_VALUES and cfg[key] not in ALLOWED_VALUES[key]:
                logging.error(
                    f"{config_file}:\nConfiguration key {key} has value {cfg[key]}.\n However, only these values are known: {', '.join(ALLOWED_VALUES[key])}."
                )
                return False
    return True


def _convert_types(cfg):
    """Converts types from string to whatever type the value in DEFAULT_CONFIG has"""
    for key in cfg.keys():
        if type(DEFAULT_CONFIG[key]) == int:
            cfg[key] = int(cfg[key])


def load(config_file):
    """Load the configuration file and return its contents as a dict."""
    logging.debug(f"Loading {config_file}...")
    try:
        with open(config_file, "r") as f:
            cfg = json.load(f)
            logging.debug(f"Loaded configuration: {cfg}")
            if _is_valid(cfg, config_file):
                _convert_types(cfg)
                return cfg
    except FileNotFoundError:
        pass
    return {}


class Config:
    config_file = CONFIG_FILE
    config = {}
    cmd_line_options = {}

    def __init__(self, file):
        if file:
            self.config_file = Path(file)
        self.config = load(self.config_file)

    def get(self, key):
        v, _ = self.get_with_source(key)
        return v

    def get_with_source(self, key):
        if (
            self.cmd_line_options
            and key in self.cmd_line_options
            and self.cmd_line_options[key] is not None
        ):
            return self.cmd_line_options[key], "command line"
        elif self.config and key in self.config:
            return self.config[key], f"config file {self.config_file}"
        elif key in DEFAULT_CONFIG:
            return DEFAULT_CONFIG[key], f"default setting"
        else:
            logging.error(f"{key} is not a valid configuration key.")
            exit(1)

    def unset(self, key):
        if self.config and key in self.config:
            del self.config[key]

    def set(self, key, value):
        self.config[key] = value

    def set_cmd_line(self, key, value):
        self.cmd_line_options[key] = value

    def save(self):
        """Save the configuration in json format to the config file."""
        config_dir = self.config_file.parent
        config_dir.mkdir(parents=True, exist_ok=True)
        j = json.dumps(self.config, ensure_ascii=False, indent=2)
        with open(self.config_file, "w", encoding="utf-8") as f:
            f.write(j)
        logging.info(f"Successfully wrote configuration to {self.config_file}")
