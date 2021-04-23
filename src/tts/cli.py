# -*- coding: utf-8 -*-

from pathlib import Path
from typing import Optional

from .utils.cli import CLI
from .utils.formats import format_json, parse_json

app = CLI("Interact with Tabletop Simulator mods")


@app.command("unpack", help="Unpack a tts mod.")
@app.argument(metavar="savegame", dest="savegame_file", type=Path, nargs="?")
@app.argument("--fileid", type=int, help="Workshop file id to unpack.")
def unpack_cmd(*, savegame_file: Optional[Path], fileid: Optional[int]) -> None:
    from .config import CONFIG_NAME, Config
    from .savegame import UnpackedSavegame
    from .unpack import unpack
    from .workshop import get_workshop_mod

    if savegame_file and fileid:
        raise Exception("Can't specify both a savegame file and a workshop file id.")
    elif savegame_file:
        savegame = parse_json(savegame_file.read_text(encoding="utf-8"))
    elif fileid:
        savegame = get_workshop_mod(fileid)
    else:
        raise Exception("Must specify a savegame file or workshop fileid.")

    savegame_dir = Path.cwd()
    config = Config.load(savegame_dir.joinpath(CONFIG_NAME))

    unpack(savegame=savegame, unpacked_savegame=UnpackedSavegame(savegame_dir, config))


@app.command("repack", help="Repack a tts mod.")
@app.argument(
    metavar="savegame",
    dest="savegame_file",
    type=Path,
    nargs="?",
    default="build/packed-savegame.json",
)
def repack_cmd(*, savegame_file: Path) -> None:
    from .config import CONFIG_NAME, Config
    from .repack import repack
    from .savegame import UnpackedSavegame

    if not savegame_file.parent.exists():
        savegame_file.parent.mkdir(parents=True)

    savegame_dir = Path.cwd()
    config = Config.load(savegame_dir.joinpath(CONFIG_NAME))

    savegame = repack(unpacked_savegame=UnpackedSavegame(savegame_dir, config))

    savegame_file.write_text(format_json(savegame, config=config), encoding="utf-8")


@app.command("workshop-download", help="Download a mod from the steam workshop.")
@app.argument("fileid", type=int)
@app.argument(
    "-o", type=Path, dest="output", help="File to write mod (default: <fileid>.json)"
)
def download_cmd(*, fileid: int, output: Optional[Path]) -> None:
    from .config import Config
    from .workshop import get_workshop_mod

    if output is None:
        output = Path(f"{fileid}.json")

    mod = get_workshop_mod(fileid)
    output.write_text(format_json(mod, config=Config()), encoding="utf-8")


@app.command(
    "fmt",
    help="Normalize the unpacked savegame, as if it was freshly unpacked.",
    description="In particular, this will apply any configured quantization.",
)
def fmt_cmd() -> None:
    from .config import CONFIG_NAME, Config
    from .repack import repack
    from .savegame import UnpackedSavegame
    from .unpack import unpack

    savegame_dir = Path.cwd()
    config = Config.load(savegame_dir.joinpath(CONFIG_NAME))

    savegame = repack(unpacked_savegame=UnpackedSavegame(savegame_dir, config))
    unpack(savegame=savegame, unpacked_savegame=UnpackedSavegame(savegame_dir, config))


main = app.main
