from __future__ import annotations

import json
import re
from functools import partial
from pathlib import Path
from shutil import rmtree
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    Iterator,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    cast,
    get_type_hints,
)

import attr

from .utils.formats import format_json, to_unix

T = TypeVar("T")


_NAME_RE = re.compile(r"[\w_-]+$")


def verify_name(name: str) -> None:
    if not _NAME_RE.match(name):
        raise Exception(
            f"Item names must only contain "
            f"only alphanumeric characters and '_' and '-': '{name}'"
        )


@attr.s(auto_attribs=True)
class JsonFile:
    _file: Path

    def write_json(self, data: Dict[Any, Any]) -> None:
        if data is not None:
            self._file.write_text(format_json(data), encoding="utf-8")
        elif self._file.exists():
            self._file.unlink()

    def read_json(self) -> Optional[Dict[Any, Any]]:
        if self._file.is_file():
            return cast(
                Dict[Any, Any], json.loads(self._file.read_text(encoding="utf-8"))
            )
        else:
            return None


@attr.s(auto_attribs=True)
class TextFile:
    _file: Path

    def write_text(self, data: str) -> None:
        if data:
            self._file.write_text(to_unix(data), encoding="utf-8")
        elif self._file.exists():
            self._file.unlink()

    def read_text(self) -> str:
        if self._file.is_file():
            return self._file.read_text(encoding="utf-8")
        else:
            return ""


@attr.s(auto_attribs=True)
class UnpackedIndex(Generic[T]):
    _path: Path
    _child_type: Callable[[Path], T]

    def __class_getitem__(
        cls, child_type: Type[T]
    ) -> Callable[[Path], UnpackedIndex[T]]:
        return partial(cls, child_type=child_type)

    @property
    def _index(self) -> TextFile:
        return TextFile(self._path.joinpath("index.list"))

    def exists(self) -> bool:
        return self._path.is_dir()

    def child(self, name: str, *, create: bool = False) -> T:
        # Check that the name is a reasonable file path
        verify_name(name)

        path = self._path.joinpath(name)
        if create:
            path.mkdir(parents=True, exist_ok=True)
        elif not path.is_dir():
            raise Exception("Objects must be directories")
        return self._child_type(path)

    def children(self) -> Iterator[Tuple[str, T]]:
        if not self.exists():
            return
        entries = self._index.read_text().splitlines()
        for entry in entries:
            verify_name(entry)
            yield (entry, self.child(entry))

    def write_index(self, entries: List[str]) -> None:
        for entry in entries:
            verify_name(entry)
        self._index.write_text("\n".join(entries) + "\n")
        for child in self._path.iterdir():
            if child.name not in entries and child.name != "index.list":
                if child.is_dir():
                    rmtree(str(child))
                else:
                    child.unlink()


def _get_child(self: Any, *, path: Path, make: Callable[..., T]) -> T:
    return make(self._path.joinpath(path))


def _unpacked_layout(cls: type) -> type:
    new_cls = attr.make_class(cls.__name__, {"_path": attr.ib(type=Path)})
    hints = get_type_hints(cls, None, {cls.__name__: new_cls})
    for name, attr_type in hints.items():
        p = partial(_get_child, path=getattr(cls, name), make=attr_type)
        setattr(new_cls, name, property(p))
    return new_cls


@_unpacked_layout
class UnpackedObject:
    object: JsonFile = Path("object.json")
    script: TextFile = Path("script.lua")
    script_state: JsonFile = Path("script-state.json")
    xml_ui: TextFile = Path("ui.xml")
    contained: UnpackedIndex[UnpackedObject] = Path("contained")


@_unpacked_layout
class UnpackedSavegame:
    savegame: JsonFile = Path("savegame.json")
    script: TextFile = Path("script.lua")
    script_state: JsonFile = Path("script-state.json")
    note: TextFile = Path("note.txt")
    xml_ui: TextFile = Path("ui.xml")
    objects: UnpackedIndex[UnpackedObject] = Path("objects")
