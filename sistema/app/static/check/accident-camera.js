(function () {
  "use strict";

  const RecordingState = { stream: null, recorder: null, chunks: [], dialog: null };

  // i18n helper — uses window.CheckingWebI18n.t when available; otherwise
  // returns the pt-BR fallback text (which is the canonical wording required
  // by item 5.2 of docs/temp002_alteracoes.txt — do not change these strings
  // without explicit authorization).
  function tt(key, fallback) {
    const i18n = window.CheckingWebI18n;
    if (i18n && typeof i18n.t === "function") {
      try {
        const result = i18n.t(key);
        if (typeof result === "string" && result && result !== key) return result;
      } catch (_) {
        // fall through to fallback
      }
    }
    return fallback;
  }

  function getMimeType() {
    const candidates = ["video/webm;codecs=vp9,opus", "video/webm", "video/mp4"];
    for (const m of candidates) {
      if (window.MediaRecorder && MediaRecorder.isTypeSupported(m)) return m;
    }
    return "";
  }

  async function startRecording(chave) {
    try {
      RecordingState.stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" } },
        audio: true,
      });
    } catch (err) {
      alert("Sem permissão para câmera/microfone. Habilite em Ajustes → Permitir Audio & Video.");
      return false;
    }
    showRecordingDialog();
    RecordingState.chunks = [];
    const mime = getMimeType();
    try {
      RecordingState.recorder = new MediaRecorder(
        RecordingState.stream,
        mime ? { mimeType: mime } : {}
      );
    } catch (err) {
      cleanup();
      alert("Seu dispositivo não suporta gravação de vídeo.");
      return false;
    }
    RecordingState.recorder.ondataavailable = (e) => {
      if (e.data && e.data.size) RecordingState.chunks.push(e.data);
    };
    RecordingState.recorder.onstop = () => uploadRecording(chave, mime);
    RecordingState.recorder.start();
    return true;
  }

  function stopRecording() {
    if (RecordingState.recorder && RecordingState.recorder.state !== "inactive") {
      RecordingState.recorder.stop();
    }
  }

  async function uploadRecording(chave, mime) {
    const blob = new Blob(RecordingState.chunks, { type: mime || "video/webm" });
    const fd = new FormData();
    fd.append("chave", chave);
    fd.append(
      "idempotency_key",
      crypto.randomUUID
        ? crypto.randomUUID()
        : Date.now().toString(36) + Math.random().toString(36).slice(2)
    );
    fd.append("video", blob, `recording.${mime.includes("mp4") ? "mp4" : "webm"}`);
    // Item 5.2 spec: these three texts are the user-visible contract for the
    // video upload feedback. Do not change them without explicit authorization.
    const sendingText = tt("accident.video.sending", "Enviando o registro...");
    const sentText = tt("accident.video.sent", "Registro enviado com sucesso.");
    const errorText = tt("accident.video.error", "Erro: registro não enviado.");
    setStatus(sendingText);
    setExternalStatus(sendingText);
    try {
      const resp = await fetch("/api/web/check/accident/video", {
        method: "POST",
        body: fd,
        credentials: "include",
      });
      if (!resp.ok) throw new Error("upload failed");
      setStatus(sentText);
      setExternalStatus(sentText);
    } catch (err) {
      setStatus(errorText);
      setExternalStatus(errorText);
    } finally {
      cleanup();
    }
  }

  function showRecordingDialog() {
    if (RecordingState.dialog) return;

    const backdrop = document.createElement("div");
    backdrop.className = "accident-camera-backdrop";

    const card = document.createElement("div");
    card.className = "accident-camera-card";

    const video = document.createElement("video");
    video.className = "accident-camera-preview";
    video.autoplay = true;
    video.muted = true;
    video.playsInline = true;
    video.srcObject = RecordingState.stream;

    const statusEl = document.createElement("p");
    statusEl.className = "accident-camera-status";
    statusEl.textContent = "Gravando…";

    const stopBtn = document.createElement("button");
    stopBtn.type = "button";
    stopBtn.className = "accident-camera-stop-button";
    stopBtn.textContent = "Encerrar";
    stopBtn.addEventListener("click", stopRecording);

    card.appendChild(video);
    card.appendChild(statusEl);
    card.appendChild(stopBtn);
    backdrop.appendChild(card);
    document.body.appendChild(backdrop);

    RecordingState.dialog = { backdrop, statusEl };
  }

  function setStatus(msg) {
    if (RecordingState.dialog) {
      RecordingState.dialog.statusEl.textContent = msg;
    }
  }

  function setExternalStatus(msg) {
    const el = document.getElementById("notificationLineSecondary");
    if (el) el.textContent = msg;
  }

  function cleanup() {
    if (RecordingState.stream) {
      RecordingState.stream.getTracks().forEach((t) => t.stop());
    }
    RecordingState.stream = null;
    RecordingState.recorder = null;
    RecordingState.chunks = [];
    hideRecordingDialog();
  }

  function hideRecordingDialog() {
    if (RecordingState.dialog) {
      RecordingState.dialog.backdrop.remove();
      RecordingState.dialog = null;
    }
  }

  window.AccidentCamera = { startRecording, stopRecording };
})();
