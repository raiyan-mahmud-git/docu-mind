"use strict";

const fileInput = document.querySelector("#file-input");
const dropZone = document.querySelector("#drop-zone");
const uploadStatus = document.querySelector("#upload-status");
const uploadMessage = document.querySelector("#upload-message");
const uploadPercent = document.querySelector("#upload-percent");
const uploadProgress = document.querySelector("#upload-progress");
const uploadError = document.querySelector("#upload-error");
const documentList = document.querySelector("#document-list");
const documentCount = document.querySelector("#document-count");
const searchForm = document.querySelector("#search-form");
const queryInput = document.querySelector("#query-input");
const topKInput = document.querySelector("#top-k");
const searchButton = document.querySelector("#search-button");
const searchStatus = document.querySelector("#search-status");
const searchResults = document.querySelector("#search-results");

function showUploadError(message) {
  uploadError.textContent = message;
  uploadError.hidden = !message;
}

function setProgress(percent, message) {
  const bounded = Math.max(0, Math.min(100, Math.round(percent)));
  uploadStatus.hidden = false;
  uploadMessage.textContent = message;
  uploadPercent.textContent = `${bounded}%`;
  uploadProgress.style.width = `${bounded}%`;
}

function uploadFile(file) {
  return new Promise((resolve, reject) => {
    const formData = new FormData();
    formData.append("file", file, file.name);
    const request = new XMLHttpRequest();
    request.open("POST", "/documents");
    request.upload.addEventListener("progress", (event) => {
      if (event.lengthComputable) {
        setProgress((event.loaded / event.total) * 100, `Uploading ${file.name}`);
      }
    });
    request.upload.addEventListener("load", () => {
      setProgress(100, `Indexing ${file.name}…`);
    });
    request.addEventListener("load", () => {
      let payload = {};
      try {
        payload = JSON.parse(request.responseText);
      } catch {
        // A missing JSON body is reported below with the HTTP status.
      }
      if (request.status >= 200 && request.status < 300) {
        resolve(payload);
      } else {
        reject(new Error(payload.detail || `Upload failed (${request.status})`));
      }
    });
    request.addEventListener("error", () => reject(new Error("Could not reach the DocuMind API.")));
    request.addEventListener("abort", () => reject(new Error("Upload was cancelled.")));
    setProgress(0, `Preparing ${file.name}`);
    request.send(formData);
  });
}

async function handleFiles(fileCollection) {
  const files = Array.from(fileCollection || []);
  if (!files.length) return;

  showUploadError("");
  const allowed = /\.(pdf|md|txt)$/i;
  for (let index = 0; index < files.length; index += 1) {
    const file = files[index];
    if (!allowed.test(file.name)) {
      showUploadError(`${file.name}: choose a PDF, Markdown, or TXT file.`);
      continue;
    }
    try {
      await uploadFile(file);
      if (index < files.length - 1) {
        uploadMessage.textContent = `Added ${file.name}. Preparing the next file…`;
      } else {
        uploadMessage.textContent = `Added ${file.name} to your library.`;
      }
    } catch (error) {
      showUploadError(`${file.name}: ${error.message}`);
    }
  }
  fileInput.value = "";
  await refreshDocuments();
}

fileInput.addEventListener("change", (event) => handleFiles(event.target.files));
dropZone.addEventListener("click", () => fileInput.click());
for (const eventName of ["dragenter", "dragover"]) {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.add("is-dragging");
  });
}
for (const eventName of ["dragleave", "drop"]) {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.remove("is-dragging");
  });
}
dropZone.addEventListener("drop", (event) => handleFiles(event.dataTransfer.files));

function makeFileIcon(filename) {
  const icon = document.createElement("span");
  icon.className = "file-icon";
  icon.setAttribute("aria-hidden", "true");
  icon.textContent = filename.split(".").pop().slice(0, 4).toUpperCase();
  return icon;
}

function renderDocuments(documents) {
  documentCount.textContent = String(documents.length);
  documentList.replaceChildren();
  if (!documents.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = "Your library is ready when you are. Add a document above to begin.";
    documentList.append(empty);
    return;
  }

  for (const item of documents) {
    const row = document.createElement("article");
    row.className = "document-row";
    row.append(makeFileIcon(item.filename));

    const info = document.createElement("div");
    info.className = "document-info";
    const name = document.createElement("div");
    name.className = "document-name";
    name.textContent = item.filename;
    const meta = document.createElement("div");
    meta.className = "document-meta";
    meta.textContent = `${item.pages} ${item.pages === 1 ? "page" : "pages"} · ${item.chunk_count} passages · ${item.sha256.slice(0, 10)}`;
    info.append(name, meta);

    const remove = document.createElement("button");
    remove.className = "delete-button";
    remove.type = "button";
    remove.setAttribute("aria-label", `Delete ${item.filename}`);
    remove.title = `Delete ${item.filename}`;
    remove.innerHTML = '<svg viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="M4.5 6h11m-9.5 0 .6 10h7.8L15 6M8 6V4h4v2m-3 3v4m2-4v4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>';
    remove.addEventListener("click", () => removeDocument(item, remove));
    row.append(info, remove);
    documentList.append(row);
  }
}

async function refreshDocuments() {
  try {
    const response = await fetch("/documents");
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "Could not load documents.");
    renderDocuments(payload);
  } catch (error) {
    documentList.replaceChildren();
    const message = document.createElement("div");
    message.className = "empty-state";
    message.textContent = error.message;
    documentList.append(message);
  }
}

async function removeDocument(item, button) {
  if (button) button.disabled = true;
  try {
    const response = await fetch(`/documents/${encodeURIComponent(item.id)}`, { method: "DELETE" });
    if (!response.ok) {
      const payload = await response.json();
      throw new Error(payload.detail || "Could not delete document.");
    }
    await refreshDocuments();
  } catch (error) {
    if (button) button.disabled = false;
    showUploadError(error.message);
  }
}

document.querySelector("#refresh-button").addEventListener("click", refreshDocuments);

function renderResults(results) {
  searchResults.replaceChildren();
  for (const result of results) {
    const card = document.createElement("article");
    card.className = "result-card";
    const topLine = document.createElement("div");
    topLine.className = "result-topline";

    const source = document.createElement("div");
    source.className = "result-source";
    source.innerHTML = '<svg viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M3.5 2.5h5l4 4v7h-9v-11Z" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round"/><path d="M8.5 2.5v4h4" stroke="currentColor" stroke-width="1.2"/></svg>';
    const citation = document.createElement("span");
    citation.textContent = `${result.filename} · page ${result.page_number}`;
    source.append(citation);

    const score = document.createElement("span");
    score.className = "result-score";
    score.textContent = `Match ${Math.round(result.score * 100)}% · result ${result.rank}`;
    topLine.append(source, score);

    const passage = document.createElement("p");
    passage.className = "result-text";
    passage.textContent = result.text;
    card.append(topLine, passage);
    searchResults.append(card);
  }
}

searchForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const query = queryInput.value.trim();
  if (!query) {
    queryInput.focus();
    return;
  }

  searchButton.disabled = true;
  searchStatus.textContent = "Searching your passages…";
  searchResults.replaceChildren();
  try {
    const response = await fetch("/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, top_k: Number(topKInput.value) }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "Search failed.");
    if (payload.no_relevant_passage) {
      searchStatus.textContent = "";
      const empty = document.createElement("div");
      empty.className = "no-results";
      empty.textContent = "No relevant passage found. Try another question or add more documents to your library.";
      searchResults.append(empty);
    } else {
      renderResults(payload.results);
      searchStatus.textContent = `${payload.results.length} ${payload.results.length === 1 ? "passage" : "passages"} found in your documents.`;
    }
  } catch (error) {
    searchStatus.textContent = error.message;
  } finally {
    searchButton.disabled = false;
  }
});

refreshDocuments();


