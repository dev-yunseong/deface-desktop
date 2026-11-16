from pathlib import Path
from importlib.metadata import distribution

root = Path(SPECPATH).resolve().parent
engine = Analysis(
    [str(root / "desktop/engine.py")],
    pathex=[str(root)],
    datas=[(str(root / "deface/centerface.onnx"), "deface")],
    excludes=["onnx", "onnxruntime"],
)

# Use the separately built FFmpeg CLI for all video I/O.
def keep(entry):
    name = entry[0].replace("\\", "/").lower()
    return not (
        name.startswith("imageio_ffmpeg/binaries/")
        or "opencv_videoio_ffmpeg" in name
    )

engine.binaries = [entry for entry in engine.binaries if keep(entry)]
engine.datas = [entry for entry in engine.datas if keep(entry)]

notices = []
for package in (
    "imageio", "imageio-ffmpeg", "numpy", "scipy", "opencv-python",
    "scikit-image", "pillow", "lazy-loader", "networkx", "packaging",
    "tifffile", "tqdm", "colorama", "pyinstaller",
):
    dist = distribution(package)
    for path in dist.files or ():
        if ".dist-info/" in path.as_posix() and (
            "/licenses/" in path.as_posix() or path.name.upper().startswith(("LICENSE", "COPYING", "NOTICE"))
        ):
            notice = Path(dist.locate_file(path)).read_text(encoding="utf-8", errors="replace")
            notices.append(f"{package} {dist.version} | {path.name}\n\n{notice}")
(root / "desktop/src-tauri/bin/engine-notices.txt").write_text("\n\n".join(notices), encoding="utf-8")

EXE(
    PYZ(engine.pure),
    engine.scripts,
    engine.binaries,
    engine.datas,
    name="deface-engine-x86_64-pc-windows-msvc",
    console=True,
    upx=False,
)
