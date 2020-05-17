"""
Configuration.
"""

import json
import logging
from pathlib import Path

import appdirs
import pkg_resources

import bibtex_dblp.dblp_api as api
from bibtex_dblp.formats import BIB_FORMATS, CONDENSED

# Application settings
APP_NAME = "bibtex-dblp"
VERSION = pkg_resources.require(APP_NAME)[0].version
DEFAULT_CONFIG_DIR = Path(appdirs.user_config_dir(APP_NAME))
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.json"

## Default values (in case they're missing in the .json file)
DEFAULT_CONFIG = {
    "format": CONDENSED,
    "max_search_results": 30,
    "providers": api.PROVIDERS,
}

## Allowed values for each field, or function to verify whether allowed. None means no restrictions.
ALLOWED_VALUES = {
    "format": BIB_FORMATS,
    "providers": api.PROVIDERS,
}


def _is_valid_key(key, where=""):
    if key in DEFAULT_CONFIG.keys():
        return True
    else:
        logging.error(
            f"{where}Configuration key '{key}' is unknown.\nKnown keys are {', '.join(DEFAULT_CONFIG.keys())}"
        )
        return False


def _is_valid_key_value(key, value, where=""):
    if not _is_valid_key(key, where=where) or not isinstance(
        value, type(DEFAULT_CONFIG[key])
    ):
        return False
    elif key not in ALLOWED_VALUES:
        return True
    else:
        allowed = (
            type(value) == list and set(value).issubset(set(ALLOWED_VALUES[key]))
        ) or value in ALLOWED_VALUES[key]
        if allowed:
            return True
        else:
            logging.error(
                f"{where}Configuration key '{key}' has value '{value}'.\n However, only these values are allowed: {', '.join(ALLOWED_VALUES[key])}."
            )
            return False


def _is_valid(cfg, config_file):
    """Checks whether the given cfg is a valid config"""
    for key in cfg.keys():
        if not _is_valid_key_value(key, cfg[key], where=f"In {config_file}\n"):
            return False
    return True


def _convert_types(cfg):
    """Converts types from string to whatever type the value in DEFAULT_CONFIG has"""
    for key in cfg.keys():
        if type(DEFAULT_CONFIG[key]) == int:
            cfg[key] = int(cfg[key])
        if type(DEFAULT_CONFIG[key]) == list:
            assert type(cfg[key]) == list
            t = type(DEFAULT_CONFIG[key][0])
            cfg[key] = [t(x) for x in cfg[key]]


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
            else:
                exit(1)
    except FileNotFoundError:
        pass
    return {}


class Config:
    config_file = DEFAULT_CONFIG_FILE
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
            return DEFAULT_CONFIG[key], "default setting"
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
