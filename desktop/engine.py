"""Video worker for the desktop app. Stdout carries processed frame counts."""

import argparse
import os

import imageio.v2 as imageio

from deface.centerface import CenterFace
from deface.deface import anonymize_frame


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("output")
    parser.add_argument("mask", choices=("blur", "mosaic", "solid"))
    parser.add_argument("--ffmpeg", required=True)
    parser.add_argument("--keep-audio", action="store_true")
    args = parser.parse_args()
    os.environ["IMAGEIO_FFMPEG_EXE"] = args.ffmpeg

    detector = CenterFace(backend="opencv")
    frames = 0
    with imageio.get_reader(
        args.input, format="FFMPEG", output_params=["-fps_mode", "passthrough"]
    ) as reader:
        metadata = reader.get_meta_data()
        options = {
            "fps": metadata["fps"],
            "codec": "h264_mf",
            "macro_block_size": 1,
            "output_params": ["-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2"],
        }
        if args.keep_audio and metadata.get("audio_codec"):
            options.update(audio_path=args.input, audio_codec="aac")

        with imageio.get_writer(args.output, format="FFMPEG", **options) as writer:
            for frames, frame in enumerate(reader, start=1):
                faces, _ = detector(frame, threshold=0.2)
                anonymize_frame(faces, frame, 1.3, args.mask, False, False, None, 20)
                writer.append_data(frame)
                if frames == 1 or frames % 10 == 0:
                    print(frames, flush=True)

    if frames == 0:
        raise RuntimeError("No video frames were decoded.")
    with imageio.get_reader(args.output, format="FFMPEG") as result:
        if result.count_frames() != frames:
            raise RuntimeError("The export did not contain every processed frame.")
        if args.keep_audio and metadata.get("audio_codec") and not result.get_meta_data().get("audio_codec"):
            raise RuntimeError("The export did not contain the source audio.")
    print(frames, flush=True)


if __name__ == "__main__":
    main()
