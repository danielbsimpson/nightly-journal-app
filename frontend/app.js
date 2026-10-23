(() => {
  const recordButton = document.querySelector("#record-button");
  const recordButtonLabel = document.querySelector("#record-button-label");
  const recordingHint = document.querySelector("#recording-hint");
  const recordingStatus = document.querySelector("#recording-status");
  const recordingTimer = document.querySelector("#recording-timer");
  const waveformFrame = document.querySelector("#waveform-frame");
  const waveformCanvas = document.querySelector("#waveform");
  const reviewPanel = document.querySelector("#review-panel");
  const preview = document.querySelector("#recording-preview");
  const retakeButton = document.querySelector("#retake-button");
  const transcribeButton = document.querySelector("#transcribe-button");
  const transcriptPanel = document.querySelector("#transcript-panel");
  const transcriptText = document.querySelector("#transcript-text");
  const measuredDuration = document.querySelector("#measured-duration");
  const transcriptDuration = document.querySelector("#transcript-duration");
  const actionMessage = document.querySelector("#action-message");
  const healthMessage = document.querySelector("#health-message");
  const transcriptionIndicator = document.querySelector("#transcription-indicator");
  const processingIndicator = document.querySelector("#processing-indicator");
  const transcriptionReadiness = document.querySelector("#transcription-readiness");
  const processingReadiness = document.querySelector("#processing-readiness");
  const dateLabel = document.querySelector("#today-label");
  const canvasContext = waveformCanvas.getContext("2d");

  let transcriptionReady = false;
  let processingReady = false;
  let mediaRecorder = null;
  let audioStream = null;
  let audioContext = null;
  let animationFrame = null;
  let timerInterval = null;
  let recordingStartedAt = null;
  let recordingBlob = null;
  let recordingUrl = null;
  let audioChunks = [];

  dateLabel.textContent = new Intl.DateTimeFormat(undefined, {
    weekday: "long",
    month: "long",
    day: "numeric",
  }).format(new Date());

  function setReadiness(indicator, label, ready, detail) {
    indicator.dataset.ready = String(ready);
    label.textContent = detail || (ready ? "Ready" : "Unavailable");
  }

  function setActionMessage(message, isError = false) {
    actionMessage.textContent = message;
    actionMessage.dataset.error = String(isError);
  }

  function setHealthMessage(message, isError = false) {
    healthMessage.textContent = message;
    healthMessage.dataset.error = String(isError);
  }

  function updateControls() {
    const isRecording = mediaRecorder?.state === "recording";
    recordButton.disabled = !isRecording && (!transcriptionReady || Boolean(recordingBlob));
    recordButton.setAttribute("aria-pressed", String(isRecording));
    recordButtonLabel.textContent = isRecording ? "Stop recording" : "Start recording";
    transcribeButton.disabled = !recordingBlob || !transcriptionReady || isRecording;
    retakeButton.disabled = !recordingBlob || !transcriptionReady;
  }

  function formatTime(totalSeconds) {
    const minutes = Math.floor(totalSeconds / 60).toString().padStart(2, "0");
    const seconds = Math.floor(totalSeconds % 60).toString().padStart(2, "0");
    return `${minutes}:${seconds}`;
  }

  function formatMeasuredDuration(seconds) {
    const roundedSeconds = Math.round(seconds);
    const minutes = Math.floor(roundedSeconds / 60);
    const remainingSeconds = roundedSeconds % 60;
    return minutes > 0
      ? `Server-measured duration: ${minutes} min ${remainingSeconds} sec`
      : `Server-measured duration: ${remainingSeconds} sec`;
  }

  function updateTimer() {
    if (recordingStartedAt === null) {
      return;
    }

    recordingTimer.textContent = formatTime((performance.now() - recordingStartedAt) / 1000);
  }

  function stopTimer() {
    if (timerInterval !== null) {
      window.clearInterval(timerInterval);
      timerInterval = null;
    }
    updateTimer();
    recordingStartedAt = null;
  }

  function resizeWaveform() {
    const { width, height } = waveformCanvas.getBoundingClientRect();
    const scale = window.devicePixelRatio || 1;
    waveformCanvas.width = Math.max(1, Math.floor(width * scale));
    waveformCanvas.height = Math.max(1, Math.floor(height * scale));
    canvasContext.setTransform(scale, 0, 0, scale, 0, 0);
    drawIdleWaveform();
  }

  function drawIdleWaveform() {
    const { width, height } = waveformCanvas.getBoundingClientRect();
    canvasContext.clearRect(0, 0, width, height);
    canvasContext.fillStyle = "rgba(217, 166, 135, 0.38)";
    const barWidth = 3;
    const gap = 5;
    const count = Math.floor(width / (barWidth + gap));

    for (let index = 0; index < count; index += 1) {
      const variation = Math.abs(Math.sin(index * 0.42) * Math.cos(index * 0.13));
      const barHeight = 4 + variation * (height * 0.28);
      const x = index * (barWidth + gap);
      canvasContext.fillRect(x, (height - barHeight) / 2, barWidth, barHeight);
    }
  }

  function drawLiveWaveform(analyser) {
    const samples = new Uint8Array(analyser.fftSize);

    function draw() {
      const { width, height } = waveformCanvas.getBoundingClientRect();
      analyser.getByteTimeDomainData(samples);
      canvasContext.clearRect(0, 0, width, height);
      canvasContext.fillStyle = "rgba(239, 189, 157, 0.8)";
      const barWidth = 3;
      const gap = 5;
      const count = Math.floor(width / (barWidth + gap));
      const sampleStep = Math.max(1, Math.floor(samples.length / count));

      for (let index = 0; index < count; index += 1) {
        const amplitude = Math.abs(samples[index * sampleStep] - 128) / 128;
        const barHeight = Math.max(4, amplitude * height * 1.5);
        canvasContext.fillRect(
          index * (barWidth + gap),
          (height - barHeight) / 2,
          barWidth,
          barHeight,
        );
      }

      animationFrame = window.requestAnimationFrame(draw);
    }

    draw();
  }

  function stopWaveform() {
    if (animationFrame !== null) {
      window.cancelAnimationFrame(animationFrame);
      animationFrame = null;
    }
    if (audioContext) {
      const context = audioContext;
      audioContext = null;
      context.close().catch((error) => {
        console.error("Unable to close audio visualization context.", error);
      });
    }
    resizeWaveform();
  }

  function stopTracks() {
    if (!audioStream) {
      return;
    }
    audioStream.getTracks().forEach((track) => track.stop());
    audioStream = null;
  }

  function releaseRecordingUrl() {
    if (recordingUrl) {
      URL.revokeObjectURL(recordingUrl);
      recordingUrl = null;
    }
  }

  function clearRecording() {
    stopTracks();
    stopTimer();
    stopWaveform();
    releaseRecordingUrl();
    recordingBlob = null;
    audioChunks = [];
    mediaRecorder = null;
    preview.removeAttribute("src");
    preview.load();
    reviewPanel.hidden = true;
    transcriptPanel.hidden = true;
    transcriptText.value = "";
    measuredDuration.textContent = "";
    transcriptDuration.textContent = "";
    recordingTimer.textContent = "00:00";
    waveformFrame.dataset.recording = "false";
    recordingStatus.textContent = "Ready when you are";
    recordingHint.textContent = "Allow microphone access when your browser asks.";
    setActionMessage("");
    updateControls();
  }

  function chooseMimeType() {
    if (typeof MediaRecorder.isTypeSupported !== "function") {
      return "";
    }

    return [
      "audio/webm;codecs=opus",
      "audio/webm",
      "audio/mp4",
      "audio/ogg;codecs=opus",
    ].find((type) => MediaRecorder.isTypeSupported(type)) || "";
  }

  function extensionForMimeType(mimeType) {
    if (mimeType.includes("mp4")) {
      return "mp4";
    }
    if (mimeType.includes("ogg")) {
      return "ogg";
    }
    return "webm";
  }

  async function startRecording() {
    if (!transcriptionReady || recordingBlob) {
      return;
    }

    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      setActionMessage("This browser does not support microphone recording.", true);
      return;
    }

    setActionMessage("");
    recordingHint.textContent = "Requesting microphone access…";

    try {
      audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (audioStream.getAudioTracks().length === 0) {
        stopTracks();
        throw new Error("No microphone audio track was provided.");
      }

      const mimeType = chooseMimeType();
      mediaRecorder = mimeType
        ? new MediaRecorder(audioStream, { mimeType })
        : new MediaRecorder(audioStream);
      audioChunks = [];

      mediaRecorder.addEventListener("dataavailable", (event) => {
        if (event.data.size > 0) {
          audioChunks.push(event.data);
        }
      });

      mediaRecorder.addEventListener("error", (event) => {
        const detail = event.error?.message || "The browser could not record audio.";
        setActionMessage(detail, true);
        recordingStatus.textContent = "Recording failed";
      });

      mediaRecorder.addEventListener("stop", () => {
        stopTimer();
        stopTracks();
        stopWaveform();
        waveformFrame.dataset.recording = "false";

        if (audioChunks.length === 0) {
          recordingStatus.textContent = "No audio was captured";
          setActionMessage("No audio was captured. Check your microphone and try again.", true);
          mediaRecorder = null;
          updateControls();
          return;
        }

        const actualMimeType = mediaRecorder.mimeType || audioChunks[0].type || mimeType;
        recordingBlob = new Blob(audioChunks, { type: actualMimeType || "audio/webm" });
        recordingUrl = URL.createObjectURL(recordingBlob);
        preview.src = recordingUrl;
        reviewPanel.hidden = false;
        recordingStatus.textContent = "Recording ready to review";
        recordingHint.textContent = "Listen back, then transcribe when you’re ready.";
        updateControls();
      });

      mediaRecorder.start();
      recordingStartedAt = performance.now();
      recordingTimer.textContent = "00:00";
      timerInterval = window.setInterval(updateTimer, 250);
      waveformFrame.dataset.recording = "true";
      recordingStatus.textContent = "Listening…";
      recordingHint.textContent = "Your audio is only held in memory on this device.";

      try {
        audioContext = new AudioContext();
        const source = audioContext.createMediaStreamSource(audioStream);
        const analyser = audioContext.createAnalyser();
        analyser.fftSize = 256;
        source.connect(analyser);
        drawLiveWaveform(analyser);
      } catch (error) {
        stopWaveform();
        console.warn("Live waveform is unavailable in this browser.", error);
      }

      updateControls();
    } catch (error) {
      stopTracks();
      stopTimer();
      stopWaveform();
      mediaRecorder = null;
      waveformFrame.dataset.recording = "false";
      recordingStatus.textContent = "Ready when you are";
      recordingHint.textContent = "Allow microphone access when your browser asks.";
      const detail = error.name === "NotAllowedError"
        ? "Microphone access was denied. Allow access in your browser settings and try again."
        : error.name === "NotFoundError"
          ? "No microphone was found. Connect a microphone and try again."
          : `Could not start recording: ${error.message || "the browser could not access a microphone."}`;
      setActionMessage(detail, true);
      updateControls();
    }
  }

  function stopRecording() {
    if (mediaRecorder?.state === "recording") {
      mediaRecorder.stop();
      recordingStatus.textContent = "Preparing your recording…";
      updateControls();
    }
  }

  async function transcribeRecording() {
    if (!recordingBlob || !transcriptionReady) {
      return;
    }

    const mimeType = recordingBlob.type || "audio/webm";
    const filename = `recording.${extensionForMimeType(mimeType)}`;
    const formData = new FormData();
    formData.append("audio", recordingBlob, filename);
    transcribeButton.disabled = true;
    setActionMessage("Transcribing on your device…");

    try {
      const response = await fetch("/transcribe", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Transcription failed (HTTP ${response.status}).`);
      }

      const result = await response.json();
      if (typeof result.transcript !== "string" || result.transcript.trim() === "") {
        throw new Error("The transcription service returned an empty transcript.");
      }

      transcriptText.value = result.transcript;
      transcriptPanel.hidden = false;
      transcriptPanel.scrollIntoView({ behavior: "smooth", block: "nearest" });
      const duration = result.audio_duration_seconds;
      const durationText = Number.isFinite(duration) && duration >= 0
        ? formatMeasuredDuration(duration)
        : "";
      measuredDuration.textContent = durationText;
      transcriptDuration.textContent = durationText;
      setActionMessage("Transcription complete. Review your words below.");
    } catch (error) {
      setActionMessage(error.message || "Transcription failed. Please try again.", true);
    } finally {
      updateControls();
    }
  }

  async function loadHealth() {
    try {
      const response = await fetch("/health", { headers: { Accept: "application/json" } });
      if (!response.ok) {
        throw new Error(`Health check failed (HTTP ${response.status}).`);
      }

      const health = await response.json();
      const transcriptionState = health.transcription?.ready;
      const processingState = health.processing?.ready;
      if (typeof transcriptionState !== "boolean" || typeof processingState !== "boolean") {
        throw new Error("Health check returned an invalid readiness response.");
      }

      transcriptionReady = transcriptionState;
      processingReady = processingState;
      const transcriptionDetail = transcriptionReady && health.transcription.device
        ? `Ready · ${health.transcription.device}`
        : transcriptionReady
          ? "Ready"
          : "Unavailable";
      setReadiness(transcriptionIndicator, transcriptionReadiness, transcriptionReady, transcriptionDetail);
      setReadiness(
        processingIndicator,
        processingReadiness,
        processingReady,
        processingReady ? "Ready" : "Unavailable",
      );
      setHealthMessage(
        health.status === "degraded"
          ? "Some local services are unavailable. Recording and transcription follow transcription readiness."
          : "Connected to your local journal.",
      );
    } catch (error) {
      transcriptionReady = false;
      processingReady = false;
      setReadiness(transcriptionIndicator, transcriptionReadiness, false, "Unavailable");
      setReadiness(processingIndicator, processingReadiness, false, "Unavailable");
      setHealthMessage(error.message || "Could not connect to the local journal.", true);
    }

    updateControls();
  }

  recordButton.addEventListener("click", () => {
    if (mediaRecorder?.state === "recording") {
      stopRecording();
    } else {
      startRecording();
    }
  });

  retakeButton.addEventListener("click", async () => {
    clearRecording();
    await startRecording();
  });

  transcribeButton.addEventListener("click", transcribeRecording);
  window.addEventListener("resize", resizeWaveform);
  window.addEventListener("beforeunload", () => {
    stopTimer();
    stopWaveform();
    stopTracks();
    releaseRecordingUrl();
  });

  resizeWaveform();
  updateControls();
  loadHealth();
})();
