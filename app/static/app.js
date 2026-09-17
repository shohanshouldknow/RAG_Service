"use strict";

const MAX_UPLOAD_BYTES = 5 * 1024 * 1024;
const SUPPORTED_EXTENSIONS = [".md", ".txt"];

const elements = {
  documentStatus: document.querySelector("#documentStatus"),
  documentStatusText: document.querySelector("#documentStatusText"),
  uploadForm: document.querySelector("#uploadForm"),
  dropZone: document.querySelector("#dropZone"),
  fileInput: document.querySelector("#documentFile"),
  browseButton: document.querySelector("#browseButton"),
  selectedFile: document.querySelector("#selectedFile"),
  selectedFileName: document.querySelector("#selectedFileName"),
  selectedFileSize: document.querySelector("#selectedFileSize"),
  fileType: document.querySelector("#fileType"),
  removeFileButton: document.querySelector("#removeFileButton"),
  uploadButton: document.querySelector("#uploadButton"),
  uploadMessage: document.querySelector("#uploadMessage"),
  indexSummary: document.querySelector("#indexSummary"),
  indexedFilename: document.querySelector("#indexedFilename"),
  indexedChunkCount: document.querySelector("#indexedChunkCount"),
  questionForm: document.querySelector("#questionForm"),
  questionInput: document.querySelector("#questionInput"),
  askButton: document.querySelector("#askButton"),
  queryMessage: document.querySelector("#queryMessage"),
  emptyAnswer: document.querySelector("#emptyAnswer"),
  answerPanel: document.querySelector("#answerPanel"),
  answerState: document.querySelector("#answerState"),
  answerTitle: document.querySelector("#answerTitle"),
  answerText: document.querySelector("#answerText"),
  sourceCount: document.querySelector("#sourceCount"),
  tokenCount: document.querySelector("#tokenCount"),
  sourcesSection: document.querySelector("#sourcesSection"),
  sourceList: document.querySelector("#sourceList"),
};

const state = {
  selectedFile: null,
  documentReady: false,
  indexing: false,
  asking: false,
};

function extensionOf(filename) {
  const dotIndex = filename.lastIndexOf(".");
  return dotIndex >= 0 ? filename.slice(dotIndex).toLowerCase() : "";
}

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function setMessage(element, message = "", status = "") {
  element.textContent = message;
  if (status) {
    element.dataset.state = status;
  } else {
    delete element.dataset.state;
  }
}

function setDocumentStatus(status, label) {
  elements.documentStatus.dataset.state = status;
  elements.documentStatusText.textContent = label;
}

function updateControls() {
  elements.uploadButton.disabled = !state.selectedFile || state.indexing || state.asking;
  elements.fileInput.disabled = state.indexing || state.asking;
  elements.browseButton.disabled = state.indexing || state.asking;
  elements.removeFileButton.disabled = state.indexing || state.asking;
  elements.dropZone.dataset.disabled = String(state.indexing || state.asking);
  elements.dropZone.setAttribute("aria-disabled", String(state.indexing || state.asking));
  elements.questionInput.disabled = !state.documentReady || state.indexing || state.asking;
  elements.askButton.disabled = !state.documentReady || state.indexing || state.asking;
}

function chooseFile(file) {
  setMessage(elements.uploadMessage);

  if (!file) {
    clearSelectedFile();
    return;
  }

  const extension = extensionOf(file.name);
  if (!SUPPORTED_EXTENSIONS.includes(extension)) {
    clearSelectedFile();
    setMessage(elements.uploadMessage, "Choose a Markdown (.md) or text (.txt) file.", "error");
    return;
  }
  if (file.size === 0) {
    clearSelectedFile();
    setMessage(elements.uploadMessage, "The selected file is empty.", "error");
    return;
  }
  if (file.size > MAX_UPLOAD_BYTES) {
    clearSelectedFile();
    setMessage(elements.uploadMessage, "The selected file exceeds the 5 MB limit.", "error");
    return;
  }

  state.selectedFile = file;
  elements.selectedFileName.textContent = file.name;
  elements.selectedFileSize.textContent = formatBytes(file.size);
  elements.fileType.textContent = extension.slice(1).toUpperCase();
  elements.selectedFile.hidden = false;
  updateControls();
}

function clearSelectedFile() {
  state.selectedFile = null;
  elements.fileInput.value = "";
  elements.selectedFile.hidden = true;
  elements.selectedFileName.textContent = "";
  elements.selectedFileSize.textContent = "";
  updateControls();
}

function setIndexing(isIndexing) {
  state.indexing = isIndexing;
  elements.uploadButton.classList.toggle("is-loading", isIndexing);
  elements.uploadButton.querySelector(".button-label").textContent = isIndexing
    ? "Indexing document"
    : "Upload & index";
  elements.uploadForm.setAttribute("aria-busy", String(isIndexing));
  updateControls();
}

function setAsking(isAsking) {
  state.asking = isAsking;
  elements.askButton.classList.toggle("is-loading", isAsking);
  elements.askButton.querySelector(".button-label").textContent = isAsking
    ? "Finding evidence"
    : "Ask DocuSense";
  elements.questionForm.setAttribute("aria-busy", String(isAsking));
  updateControls();
}

async function responseError(response) {
  try {
    const payload = await response.json();
    if (typeof payload.detail === "string") return payload.detail;
    if (Array.isArray(payload.detail)) return "The submitted data was not valid.";
  } catch (_error) {
    // A safe status-based message is returned below.
  }
  return `The request failed with status ${response.status}.`;
}

async function uploadDocument(event) {
  event.preventDefault();
  if (!state.selectedFile || state.indexing || state.asking) return;

  const wasReady = state.documentReady;
  setIndexing(true);
  setDocumentStatus("loading", "Indexing document…");
  setMessage(elements.uploadMessage, "Creating embeddings and replacing the active index…");

  const formData = new FormData();
  formData.append("file", state.selectedFile, state.selectedFile.name);

  try {
    const response = await fetch("/api/documents", {
      method: "POST",
      body: formData,
    });
    if (!response.ok) throw new Error(await responseError(response));

    const result = await response.json();
    state.documentReady = true;
    setDocumentStatus("ready", "Document ready");
    setMessage(
      elements.uploadMessage,
      `${result.chunks_indexed} chunks indexed successfully.`,
      "success",
    );
    elements.indexedFilename.textContent = result.filename;
    elements.indexedChunkCount.textContent = String(result.chunks_indexed);
    elements.indexSummary.hidden = false;
    elements.questionInput.placeholder = "Ask a question supported by the active document…";
    elements.emptyAnswer.hidden = false;
    elements.answerPanel.hidden = true;
    setMessage(elements.queryMessage);
    clearSelectedFile();
    window.setTimeout(() => elements.questionInput.focus(), 0);
  } catch (error) {
    state.documentReady = wasReady;
    setDocumentStatus(wasReady ? "ready" : "empty", wasReady ? "Document ready" : "No document indexed");
    setMessage(elements.uploadMessage, error.message || "The document could not be indexed.", "error");
  } finally {
    setIndexing(false);
  }
}

function sourceCard(source, index) {
  const details = document.createElement("details");
  details.className = "source-card";
  if (index === 0) details.open = true;

  const summary = document.createElement("summary");
  const chunkId = document.createElement("span");
  chunkId.className = "source-id";
  chunkId.textContent = source.chunk_id;

  const score = document.createElement("span");
  score.className = "source-score";
  const numericScore = Number(source.similarity_score);
  score.textContent = Number.isFinite(numericScore)
    ? `similarity ${numericScore.toFixed(3)}`
    : "similarity unavailable";

  const text = document.createElement("p");
  text.className = "source-text";
  text.textContent = source.text_snippet;

  summary.append(chunkId, score);
  details.append(summary, text);
  return details;
}

function renderAnswer(result) {
  const sources = Array.isArray(result.sources) ? result.sources : [];
  const insufficient = sources.length === 0;

  elements.emptyAnswer.hidden = true;
  elements.answerPanel.hidden = false;
  elements.answerPanel.dataset.state = insufficient ? "insufficient" : "grounded";
  elements.answerState.textContent = insufficient ? "Insufficient evidence" : "Grounded answer";
  elements.answerTitle.textContent = insufficient ? "The document cannot support this answer" : "Answer";
  elements.answerText.textContent = result.answer;
  elements.sourceCount.textContent = String(sources.length);
  elements.tokenCount.textContent = String(result.tokens_used ?? 0);
  elements.sourceList.replaceChildren(...sources.map(sourceCard));
  elements.sourcesSection.hidden = insufficient;
}

function renderQueryError(message) {
  elements.emptyAnswer.hidden = true;
  elements.answerPanel.hidden = false;
  elements.answerPanel.dataset.state = "error";
  elements.answerState.textContent = "Technical error";
  elements.answerTitle.textContent = "Unable to answer";
  elements.answerText.textContent = message;
  elements.sourceCount.textContent = "0";
  elements.tokenCount.textContent = "0";
  elements.sourceList.replaceChildren();
  elements.sourcesSection.hidden = true;
}

async function askQuestion(event) {
  event.preventDefault();
  const question = elements.questionInput.value.trim();
  if (!question || !state.documentReady || state.indexing || state.asking) {
    if (!question) setMessage(elements.queryMessage, "Enter a question first.", "error");
    return;
  }

  setAsking(true);
  setMessage(elements.queryMessage, "Retrieving qualifying evidence and generating a grounded answer…");

  try {
    const response = await fetch("/api/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    if (!response.ok) throw new Error(await responseError(response));

    renderAnswer(await response.json());
    setMessage(elements.queryMessage);
    elements.answerPanel.scrollIntoView({ block: "nearest" });
  } catch (error) {
    const message = error.message || "The question could not be processed.";
    setMessage(elements.queryMessage, message, "error");
    renderQueryError(message);
  } finally {
    setAsking(false);
  }
}

elements.browseButton.addEventListener("click", (event) => {
  event.stopPropagation();
  elements.fileInput.click();
});

elements.dropZone.addEventListener("click", (event) => {
  if (
    event.target !== elements.browseButton
    && event.target !== elements.fileInput
    && !state.indexing
    && !state.asking
  ) {
    elements.fileInput.click();
  }
});

for (const eventName of ["dragenter", "dragover"]) {
  elements.dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    if (!state.indexing && !state.asking) elements.dropZone.dataset.dragging = "true";
  });
}

for (const eventName of ["dragleave", "drop"]) {
  elements.dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    delete elements.dropZone.dataset.dragging;
  });
}

elements.dropZone.addEventListener("drop", (event) => {
  if (!state.indexing && !state.asking) chooseFile(event.dataTransfer.files[0]);
});

elements.fileInput.addEventListener("change", () => chooseFile(elements.fileInput.files[0]));
elements.removeFileButton.addEventListener("click", clearSelectedFile);
elements.uploadForm.addEventListener("submit", uploadDocument);
elements.questionForm.addEventListener("submit", askQuestion);
elements.questionInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
    event.preventDefault();
    elements.questionForm.requestSubmit();
  }
});

updateControls();
