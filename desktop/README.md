# Deface Desktop

[GitHub Releases](https://github.com/dev-yunseong/deface-desktop/releases)에서 Windows x64 설치 파일을 받습니다. 영상 파일을 선택하거나 끌어다 놓고 얼굴을 가릴 방식과 오디오 유지 여부를 선택한 뒤 MP4로 저장합니다. 저장한 영상은 앱에서 재생할 수 있습니다.

Rust/Tauri 앱이 설치 파일에 포함된 deface 엔진을 실행합니다. 엔진은 영상을 로컬에서 디코딩하고 모든 프레임에서 CenterFace로 얼굴을 검출합니다. 출력 파일을 검증한 후 선택한 이름으로 저장하며, 이름이 같은 파일이 있으면 다른 이름을 선택해야 합니다. 출력 MP4는 고정 프레임률이므로 가변 프레임률 영상은 재생 시간이 달라질 수 있습니다. 영상 공유 전에 얼굴이 가려졌는지 확인하세요.

## 개발

Windows x64에서 Rust, Visual Studio C++ Build Tools, WebView2, Python 3.12, Node.js, Media Foundation이 필요합니다. 먼저 MSYS2 UCRT64 셸에서 `pacman -S make diffutils mingw-w64-ucrt-x86_64-gcc mingw-w64-ucrt-x86_64-nasm`으로 컴파일 도구를 설치하고 저장소 루트에서 `bash desktop/build-ffmpeg.sh`를 실행합니다. 나머지 명령은 저장소 루트의 PowerShell에서 실행합니다.

```powershell
python -m pip install -e . "pyinstaller>=6,<7"
./desktop/build-engine.ps1
python desktop/smoke-engine.py
cd desktop
npm ci
npm run tauri -- dev
```

## 릴리스

1. `package.json`, `package-lock.json`, `src-tauri/Cargo.toml`, `src-tauri/Cargo.lock`, `src-tauri/tauri.conf.json`의 앱 버전을 맞춥니다.
2. 커밋을 포크에 푸시하고 앱 버전에 맞는 `desktop-v0.1.0` 형식의 Git 태그를 푸시합니다.
3. Actions가 Windows 엔진을 빌드하고 테스트합니다. 설치 파일과 서명, 업데이트 매니페스트가 준비되면 GitHub Release를 공개합니다.
4. 설치된 앱의 **업데이트 확인**에서 새 버전을 찾아 설치합니다.

릴리스 워크플로는 `TAURI_SIGNING_PRIVATE_KEY` 시크릿을 사용합니다. 현재 설치본이 다음 릴리스의 서명을 검증할 수 있도록 동일 키를 사용하고 개인 키 백업을 보관하세요. 다른 저장소에서 배포할 경우 updater 공개 키와 매니페스트 URL을 해당 저장소에 맞게 지정합니다. 태그 없이 Actions에서 수동으로 실행하면 검증용 설치 파일을 워크플로 아티팩트로 받을 수 있습니다.

영상 입출력에 사용하는 FFmpeg의 소스 아카이브는 설치 파일과 같은 릴리스에서 받을 수 있습니다. [빌드 스크립트](build-ffmpeg.sh)에 컴파일 옵션이 있으며, FFmpeg 라이선스와 엔진 라이브러리 고지는 설치 파일에 포함됩니다.
