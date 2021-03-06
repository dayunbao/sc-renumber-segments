import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Dict

import attr

from sutta_processor.application.domain_models.base import (
    BaseFileAggregate,
    BaseRootAggregate,
    BaseVerses,
)
from sutta_processor.application.value_objects import (
    UID,
    BaseTextKey,
    PtsPli,
    ReferencesConcordance,
    ScID,
    Verse,
)

log = logging.getLogger(__name__)


@attr.s(frozen=True, auto_attribs=True)
class ConcordanceVerses(BaseVerses):
    uid: UID = attr.ib(init=False)
    verse: Verse

    references: ReferencesConcordance = attr.ib(init=False)

    def __attrs_post_init__(self):
        object.__setattr__(self, "uid", UID(self.raw_uid))
        object.__setattr__(
            self, "references", ReferencesConcordance(self.verse, uid=self.uid)
        )
        object.__setattr__(self, "verse", Verse(self.verse))


@attr.s(frozen=True, auto_attribs=True)
class ConcordanceFileAggregate(BaseFileAggregate):
    index: Dict[UID, ConcordanceVerses]
    verses_class = ConcordanceVerses

    @classmethod
    def from_dict(cls, in_dto: dict, f_pth: Path) -> "ConcordanceFileAggregate":
        index, errors = cls._from_dict(in_dto=in_dto)
        return cls(index=index, errors=errors, f_pth=f_pth)

    @classmethod
    def from_file(cls, f_pth: Path) -> "BaseFileAggregate":
        with open(f_pth) as f:
            data = json.load(f)
        return cls.from_dict(in_dto=data, f_pth=f_pth)

    @property
    def data(self) -> Dict[str, str]:
        verses = (vers for vers in self.index.values())
        return {v.uid: v.references.data for v in verses}


@attr.s(frozen=True, auto_attribs=True, str=False)
class ConcordanceAggregate(BaseRootAggregate):
    # cs are counted from the first paragraph, but are not unique through whole texts,
    # that's wy we need BaseTextKey to see which sutta it is.
    ref_index: Dict[BaseTextKey, Dict[ScID, ReferencesConcordance]]
    index: Dict[UID, ConcordanceVerses]

    @classmethod
    def from_path(cls, root_pth: Path) -> "ConcordanceAggregate":
        f_aggregate = ConcordanceFileAggregate.from_file(root_pth)
        index = f_aggregate.index
        log.info(cls._LOAD_INFO, cls.__name__, len(index))

        ref_index = defaultdict(dict)
        for uid, verses in index.items():  # type: UID, ConcordanceVerses
            if verses.references.sc_id:
                ref_index[uid.key.key][verses.references.sc_id] = verses.references
            elif verses.references.pts_pli:
                ref_index[uid.key.key.head][
                    verses.references.pts_pli
                ] = verses.references
        return cls(
            file_aggregates=(f_aggregate,), index=index, ref_index=dict(ref_index),
        )
