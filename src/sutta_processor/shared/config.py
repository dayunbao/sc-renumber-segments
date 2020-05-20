import argparse
import logging
from logging.config import dictConfig
from pathlib import Path
from typing import Union

import attr
from ruamel import yaml

log = logging.getLogger(__name__)

HERE = Path(__file__).parent
SRC_ROOT = HERE.parent


NULL_PTH = Path("/dev/null")


def create_dir(pth: Union[str, Path]) -> Path:
    if not pth or pth == NULL_PTH:
        return NULL_PTH
    pth = Path(pth).expanduser().resolve()
    pth.mkdir(exist_ok=True, parents=True)
    return pth


def touch_file(pth: Union[str, Path]) -> Path:
    pth = Path(pth)
    pth.parent.mkdir(exist_ok=True, parents=True)
    pth.touch()
    if not pth.is_file() and not pth.is_char_device():  # is_char_device for /dev/null
        raise RuntimeError(f"Path should be a file: '{pth}'")
    return pth


def use_case_present(_inst, _attr, uc_name: str):
    from sutta_processor.application import use_cases

    if not getattr(use_cases, uc_name, None):
        choices = use_cases.__all__
        raise NameError(
            f"Module {uc_name} was not found, choices: {choices}. "
            "Check `exec_module` config key."
        )


@attr.s(frozen=True, auto_attribs=True)
class Config:
    exec_module: str = attr.ib(validator=use_case_present)

    bilara_root_path: Path = attr.ib(converter=create_dir)
    pali_canon_path: Path = attr.ib(converter=create_dir)
    ms_yuttadhammo_path: Path = attr.ib(converter=create_dir, default=NULL_PTH)
    bilara_html_path: Path = attr.ib(converter=create_dir, default=NULL_PTH)
    bilara_comment_path: Path = attr.ib(converter=create_dir, default=NULL_PTH)
    bilara_variant_path: Path = attr.ib(converter=create_dir, default=NULL_PTH)
    bilara_translation_path: Path = attr.ib(converter=create_dir, default=NULL_PTH)
    pali_concordance_filepath: Path = attr.ib(default=NULL_PTH)
    reference_root_path: Path = attr.ib(converter=create_dir, default=NULL_PTH)

    debug_dir: Path = attr.ib(converter=create_dir, default=NULL_PTH)
    log_level: int = attr.ib(default=logging.INFO)

    repo: "FileRepository" = attr.ib(init=False)
    check: "CheckService" = attr.ib(init=False)

    def __attrs_post_init__(self):
        from sutta_processor.infrastructure.repository.repo import FileRepository

        from sutta_processor.application.check_service import CheckService

        object.__setattr__(self, "check", CheckService(cfg=self))
        object.__setattr__(self, "repo", FileRepository(cfg=self))

    @classmethod
    def from_yaml(cls, f_pth: Union[str, Path] = None) -> "Config":
        """
        Keys in the yaml file will override corresponding settings if found.
        """
        kwargs = cls._get_yaml_kwargs(f_pth=f_pth)
        return cls(**kwargs)

    @classmethod
    def _get_yaml_kwargs(cls, f_pth: Union[str, Path] = None) -> dict:
        log.info("Loading config: '%s'", f_pth)
        with open(f_pth) as f:
            file_setts = yaml.safe_load(stream=f) or {}
        Logging.setup(
            debug_dir=file_setts.get("debug_dir"),
            log_level=file_setts.get("log_level"),
        )

        setts_names = [field.name for field in attr.fields(cls)]
        log.debug("Loaded setts from file: %s, values: %s", f_pth, file_setts)
        kwargs = {k: v for k, v in file_setts.items() if k in setts_names}
        return kwargs


class Logging:
    APP_LOG_FILENAME = "app.log"
    REPORT_LOG_FILENAME = "report.log"

    FORMATTERS = {
        "verbose": {
            "format": (
                "%(asctime)s [%(levelname)7s] %(funcName)20s:%(lineno)d: %(message)s"
            ),
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "simple": {"format": "%(message)s",},
    }

    @classmethod
    def setup(cls, debug_dir: str = "", log_level=None):
        """
        WARNING: Information about the discrepancy in the data, should be fixed when
                 errors are corrected.
        ERROR: Error found in the processed data. Should give some ids to check and fix.
        """
        log_level = log_level or logging.INFO
        cls.add_trace_level()
        handlers = {
            **cls.get_console_conf(log_level=log_level),
            **cls.get_file_handlers(debug_dir=debug_dir, log_level=log_level),
        }

        root_handler = ["console", "file", "file_report"] if debug_dir else ["console"]

        log_conf = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": cls.FORMATTERS,
            "handlers": handlers,
            "loggers": {
                "": {
                    "level": logging._levelToName.get(log_level, "INFO"),
                    "handlers": root_handler,
                },
                "root": {
                    "level": logging._levelToName.get(log_level, "INFO"),
                    "handlers": root_handler,
                },
            },
        }
        dictConfig(log_conf)

    @classmethod
    def get_file_handlers(cls, debug_dir: str, log_level: int) -> dict:
        if not debug_dir:
            return {}

        debug_dir = Path(debug_dir).expanduser().resolve()
        debug_dir.mkdir(exist_ok=True, parents=True)
        handlers = {
            "file": {
                "class": "logging.FileHandler",
                "filename": str(debug_dir / cls.APP_LOG_FILENAME),
                "formatter": "verbose",
                "level": logging._levelToName.get(log_level, "TRACE"),
                "mode": "w",
            },
            "file_report": {
                "class": "logging.FileHandler",
                "filename": str(debug_dir / cls.REPORT_LOG_FILENAME),
                "formatter": "simple",
                "level": "ERROR",
                "mode": "w",
            },
        }
        return handlers

    @classmethod
    def get_console_conf(cls, log_level) -> dict:
        console = {
            "level": logging._levelToName.get(log_level, "DEBUG"),
            "class": "logging.StreamHandler",
            "formatter": "simple",
        }
        return {"console": console}

    @classmethod
    def add_trace_level(cls, trace_lvl=9):
        logging.addLevelName(trace_lvl, "TRACE")

        def trace(self, message, *args, **kws):
            if self.isEnabledFor(trace_lvl):
                self._log(trace_lvl, message, args, **kws)

        logging.Logger.trace = trace


def configure_argparse() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Tool to help with suttas texts", add_help=False
    )
    parser.add_argument(
        "-c",
        "--config",
        help="Path to config file",
        metavar="CONFIG_PATH",
        required=True,
        type=str,
    )
    parser.add_argument(
        "-h",
        "--help",
        action="help",
        default=argparse.SUPPRESS,
        help="Print this help text and exit",
    )

    return parser.parse_args()
