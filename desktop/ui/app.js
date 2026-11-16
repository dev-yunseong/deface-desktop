const { core, webview } = window.__TAURI__;
const source = document.querySelector("#source");
const filename = document.querySelector("#filename");
const sourceDetail = document.querySelector("#source-detail");
const mask = document.querySelector("#mask");
const audio = document.querySelector("#audio");
const exportButton = document.querySelector("#export");
const updateButton = document.querySelector("#update");
const progress = document.querySelector("#progress");
const status = document.querySelector("#status");
const result = document.querySelector("#result");
const preview = document.querySelector("#preview");
const output = document.querySelector("#output");
const errorDetails = document.querySelector("#error");
const errorText = document.querySelector("#error-text");
const videoExtensions = ["mp4", "mov", "mkv", "avi", "webm", "m4v", "mpg", "mpeg", "mts", "m2ts", "wmv"];
let inputPath = "";
let busy = false;

function setBusy(value) {
  busy = value;
  source.disabled = value;
  mask.disabled = value;
  audio.disabled = value;
  updateButton.disabled = value;
  exportButton.disabled = value || !inputPath;
}

function setStatus(message, error) {
  status.textContent = message;
  errorDetails.hidden = !error;
  errorDetails.open = false;
  errorText.textContent = error ? String(error) : "";
}

function hideResult() {
  result.hidden = true;
  preview.removeAttribute("src");
  preview.load();
}

function useSource(path) {
  if (!path) return;
  inputPath = path;
  filename.textContent = path.split(/[\\/]/).pop();
  sourceDetail.textContent = path;
  hideResult();
  setStatus("");
  setBusy(false);
}

source.addEventListener("click", async () => {
  setBusy(true);
  try {
    useSource(await core.invoke("choose_video", { extensions: videoExtensions }));
  } catch (error) {
    setStatus("영상 선택 창을 열 수 없습니다.", error);
  } finally {
    setBusy(false);
  }
});

webview.getCurrentWebview().onDragDropEvent(({ payload }) => {
  source.classList.toggle("dragging", !busy && (payload.type === "enter" || payload.type === "over"));
  if (busy || payload.type !== "drop") return;
  const [path] = payload.paths;
  if (payload.paths.length !== 1 || !videoExtensions.includes(path.split(".").pop().toLowerCase())) {
    setStatus("지원하는 영상 파일 한 개를 놓아 주세요.");
    return;
  }
  useSource(path);
}).catch((error) => setStatus("파일 끌어놓기를 사용할 수 없습니다.", error));

exportButton.addEventListener("click", async () => {
  setBusy(true);
  try {
    const outputPath = await core.invoke("choose_output", { input: inputPath });
    if (!outputPath) return;
    hideResult();
    progress.hidden = false;
    setStatus("영상을 여는 중…");
    const frames = new core.Channel();
    frames.onmessage = (count) => setStatus(count.toLocaleString("ko-KR") + " 프레임 처리");
    await core.invoke("anonymize", {
      input: inputPath, output: outputPath, mask: mask.value, keepAudio: audio.checked, progress: frames,
    });
    preview.src = core.convertFileSrc(outputPath);
    output.textContent = outputPath;
    result.hidden = false;
    setStatus("저장 완료");
  } catch (error) {
    setStatus("영상을 저장하지 못했습니다.", error);
  } finally {
    progress.hidden = true;
    setBusy(false);
  }
});

updateButton.addEventListener("click", async () => {
  setBusy(true);
  setStatus("업데이트 확인 중…");
  try {
    const version = await core.invoke("check_update");
    if (!version) {
      setStatus("최신 버전을 사용하고 있습니다.");
      return;
    }
    if (!window.confirm(version + " 버전을 설치하시겠습니까?")) {
      setStatus(version + " 버전을 설치할 수 있습니다.");
      return;
    }
    setStatus("업데이트를 다운로드하고 설치하는 중…");
    await core.invoke("install_update", { version });
    setStatus("업데이트를 설치했습니다. 앱을 다시 열어 주세요.");
  } catch (error) {
    setStatus("업데이트를 진행할 수 없습니다.", error);
  } finally {
    setBusy(false);
  }
});
