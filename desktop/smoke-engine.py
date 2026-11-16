"""Exercise the packaged engine with a five-frame clip and an audio track."""

import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

import imageio.v2 as imageio
import numpy as np
from deface.deface import draw_det

DESKTOP = Path(__file__).resolve().parent
ENGINE = DESKTOP / "src-tauri/bin/deface-engine-x86_64-pc-windows-msvc.exe"
FFMPEG = DESKTOP / "src-tauri/bin/deface-ffmpeg-x86_64-pc-windows-msvc.exe"
SAMPLE = DESKTOP.parent / "examples/city.jpg"


def verify_mosaic_styles():
    original = np.indices((32, 32)).sum(axis=0).astype(np.uint8)
    original = np.repeat(original[..., None], 3, axis=2)
    rectangle = original.copy()
    ellipse = original.copy()
    larger_blocks = original.copy()
    draw_det(rectangle, 1, 0, 0, 0, 31, 31, replacewith="mosaic", mosaicsize=4)
    draw_det(ellipse, 1, 0, 0, 0, 31, 31, replacewith="mosaic", mosaicsize=4, mosaic_ellipse=True)
    draw_det(larger_blocks, 1, 0, 0, 0, 31, 31, replacewith="mosaic", mosaicsize=8)
    assert np.array_equal(ellipse[1, 1], original[1, 1])
    assert not np.array_equal(rectangle[1, 1], original[1, 1])
    assert np.array_equal(ellipse[17, 17], rectangle[17, 17])
    assert not np.array_equal(ellipse[17, 17], original[17, 17])
    assert not np.array_equal(larger_blocks[5, 5], rectangle[5, 5])


def main():
    verify_mosaic_styles()
    os.environ["IMAGEIO_FFMPEG_EXE"] = str(FFMPEG)
    with TemporaryDirectory() as directory:
        source = Path(directory) / "원본.mp4"
        result = Path(directory) / "결과.mp4"
        mosaic = Path(directory) / "모자이크.mp4"
        subprocess.run(
            [
                FFMPEG, "-v", "error", "-loop", "1",
                "-i", str(SAMPLE), "-f", "lavfi", "-i", "sine=frequency=440",
                "-vf", "scale=640:-2", "-t", "1", "-r", "5",
                "-c:v", "h264_mf", "-pix_fmt", "yuv420p", "-c:a", "aac", str(source),
            ],
            check=True,
        )
        subprocess.run([ENGINE, source, result, "solid", "--ffmpeg", FFMPEG, "--keep-audio"], check=True)
        with imageio.get_reader(source) as original, imageio.get_reader(result) as exported:
            assert exported.count_frames() == original.count_frames() == 5
            assert exported.get_meta_data().get("audio_codec")
            for index in range(5):
                before = original.get_data(index)
                after = exported.get_data(index)
                masked = (after.max(axis=2) < 12) & (before.min(axis=2) > 48)
                assert np.count_nonzero(masked) > 100, f"No face mask in frame {index + 1}"
        print("Verified face masks on all five frames and audio in the packaged export.")
        subprocess.run(
            [ENGINE, source, mosaic, "mosaic", "--ffmpeg", FFMPEG,
             "--mosaic-size", "12", "--mosaic-ellipse"],
            check=True,
        )
        with imageio.get_reader(mosaic) as exported:
            assert exported.count_frames() == 5
        print("Verified mosaic block sizes and shapes, and exported five frames with elliptical mosaics.")


if __name__ == "__main__":
    main()
