#!/usr/bin/env bash
set -euo pipefail

desktop_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
work_dir="$desktop_dir/.engine"
bin_dir="$desktop_dir/src-tauri/bin"
version=9.0.2
archive="ffmpeg-$version.tar.xz"

mkdir -p "$work_dir" "$bin_dir"
cd "$work_dir"
if [[ ! -f "$archive" ]]; then
  curl --fail --silent --show-error --location "https://ffmpeg.org/releases/$archive" --output "$archive"
fi
echo "8c3850283eb25fa026482078a04051e0be17347b09ef81a0849bec15a96e002e  $archive" | sha256sum --check -
tar -xf "$archive"
cd "ffmpeg-$version"

./configure \
  --disable-autodetect --disable-doc --disable-debug --disable-network \
  --disable-ffplay --disable-ffprobe --disable-shared --enable-static \
  --enable-mediafoundation --extra-ldflags=-static
make -j "${NUMBER_OF_PROCESSORS:-2}" ffmpeg.exe
cp ffmpeg.exe "$bin_dir/deface-ffmpeg-x86_64-pc-windows-msvc.exe"
cp COPYING.LGPLv2.1 "$bin_dir/FFmpeg-LICENSE.txt"
