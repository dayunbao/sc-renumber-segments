import logging
from pathlib import Path
from typing import List, Optional

import attr

from sutta_processor.application.domain_models.base import (
    BaseFileAggregate,
    BaseRootAggregate,
    BaseVerses,
)
from sutta_processor.application.value_objects import RawVerse

log = logging.getLogger(__name__)


@attr.s(frozen=True, auto_attribs=True)
class Verses(BaseVerses):
    raw_verse: RawVerse = attr.ib(converter=RawVerse, init=False)

    def __attrs_post_init__(self):
        super().__attrs_post_init__()
        object.__setattr__(self, "raw_verse", RawVerse(self.verse))


@attr.s(frozen=True, auto_attribs=True)
class FileAggregate(BaseFileAggregate):
    verses_class = Verses

    @classmethod
    def from_dict(cls, in_dto: dict, f_pth: Path) -> "FileAggregate":
        index, errors = cls._from_dict(in_dto=in_dto)
        return cls(index=index, f_pth=f_pth, errors=errors)


@attr.s(frozen=True, auto_attribs=True, str=False)
class BilaraRootAggregate(BaseRootAggregate):
    @classmethod
    def from_path(cls, exclude_dirs: List[str], root_pth: Path, root_langs: List[str]=None) -> "BilaraRootAggregate":
        file_aggregates, index, errors = cls._from_path(
            exclude_dirs=exclude_dirs,
            root_pth=root_pth,
            file_aggregate_cls=FileAggregate,
            root_langs=root_langs,
        )
        log.info(cls._LOAD_INFO, cls.__name__, len(index))
        return cls(file_aggregates=tuple(file_aggregates), index=index)

    @classmethod
    def from_file_paths(cls, exclude_dirs: List[str], file_paths: List[Path], root_langs: List[str] = None) -> "BilaraRootAggregate":
        """A version of the from_path function that works on a list of files as a pathlib.Path obect."""
        file_aggregates, index, errors = cls._from_file_paths(
            exclude_dirs=exclude_dirs,
            file_paths=file_paths,
            file_aggregate_cls=FileAggregate,
            root_langs=root_langs,
        )
        log.info(cls._LOAD_INFO, cls.__name__, len(index))
        return cls(file_aggregates=tuple(file_aggregates), index=index)
