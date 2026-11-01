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
const askModeInput = document.querySelector("#ask-mode");
const pdfCopyForm = document.querySelector("#pdf-copy-form");
const copyPdfInput = document.querySelector("#copy-pdf-input");
const copyPagesInput = document.querySelector("#copy-pages-input");
const copyTextButton = document.querySelector("#copy-text-button");
const copyTextStatus = document.querySelector("#copy-text-status");
const copyTextResults = document.querySelector("#copy-text-results");
pdfCopyForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const file = copyPdfInput.files[0];
  const pages = copyPagesInput.value.trim();
  if (!file || !pages) return;

  copyTextButton.disabled = true;
  copyTextButton.textContent = "Reading pages…";
  copyTextStatus.textContent = "Extracting text locally. Scanned pages may take a little longer…";
  copyTextResults.replaceChildren();
  const formData = new FormData();
  formData.append("file", file, file.name);
  formData.append("pages", pages);
  try {
    const response = await fetch("/extract-text", { method: "POST", body: formData });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "Could not extract text.");
    copyTextStatus.textContent = `Extracted ${payload.pages.length} ${payload.pages.length === 1 ? "page" : "pages"} from a ${payload.total_pages}-page PDF.`;
    for (const page of payload.pages) {
      const card = document.createElement("article");
      card.className = "ocr-page-card";
      const heading = document.createElement("div");
      heading.className = "ocr-page-heading";
      const title = document.createElement("strong");
      title.textContent = `Page ${page.page_number}`;
      const copyButton = document.createElement("button");
      copyButton.className = "quiet-button";
      copyButton.type = "button";
      copyButton.textContent = "Copy text";
      const textArea = document.createElement("textarea");
      textArea.className = "ocr-page-text";
      textArea.setAttribute("aria-label", `Extracted text from page ${page.page_number}`);
      textArea.readOnly = true;
      textArea.value = page.text;
      copyButton.disabled = !page.text;
      copyButton.addEventListener("click", async () => {
        try {
          await navigator.clipboard.writeText(textArea.value);
          copyButton.textContent = "Copied";
          window.setTimeout(() => { copyButton.textContent = "Copy text"; }, 1500);
        } catch {
          textArea.focus();
          textArea.select();
          copyTextStatus.textContent = "Clipboard access was blocked. The page text is selected; press Ctrl+C to copy.";
        }
      });
      heading.append(title, copyButton);
      card.append(heading, textArea);
      copyTextResults.append(card);
    }
  } catch (error) {
    copyTextStatus.textContent = error.message;
  } finally {
    copyTextButton.disabled = false;
    copyTextButton.textContent = "Extract text";
  }
});

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
  const imageAllowed = /\.(pdf|png|jpe?g|bmp|tiff?)$/i;
  const textAllowed = /\.(md|txt)$/i;
  for (let index = 0; index < files.length; index += 1) {
    const file = files[index];
    if (!imageAllowed.test(file.name) && !textAllowed.test(file.name)) {
      showUploadError(`${file.name}: choose a PDF, PNG, JPG, BMP, TIFF, Markdown, or TXT file.`);
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

function renderResults(results, append = false) {
  if (!append) searchResults.replaceChildren();
  results.forEach((result, index) => {
    const card = document.createElement("article");
    card.className = "result-card";
    card.dataset.sourceIndex = String(index + 1);
    const topLine = document.createElement("div");
    topLine.className = "result-topline";

    const source = document.createElement("div");
    source.className = "result-source";
    source.innerHTML = '<svg viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M3.5 2.5h5l4 4v7h-9v-11Z" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round"/><path d="M8.5 2.5v4h4" stroke="currentColor" stroke-width="1.2"/></svg>';
    const citation = document.createElement("span");
    citation.textContent = `[${index + 1}] ${result.filename} · page ${result.page_number}`;
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
  });
}

function highlightSource(index) {
  const source = searchResults.querySelector(`[data-source-index="${index}"]`);
  if (!source) return;
  source.scrollIntoView({ behavior: "smooth", block: "center" });
  source.classList.add("source-highlight");
  window.setTimeout(() => source.classList.remove("source-highlight"), 1800);
}

function renderAnswer(payload) {
  searchResults.replaceChildren();
  const answerCard = document.createElement("article");
  answerCard.className = "answer-card";
  const heading = document.createElement("h3");
  heading.className = "answer-heading";
  heading.textContent = "Answer";
  const answerText = document.createElement("p");
  answerText.className = "answer-text";

  const citationPattern = /\[(\d+)\]/g;
  let previous = 0;
  for (const match of payload.answer.matchAll(citationPattern)) {
    const start = match.index;
    const end = start + match[0].length;
    answerText.append(document.createTextNode(payload.answer.slice(previous, start)));
    const sourceIndex = Number(match[1]);
    if (sourceIndex > 0 && sourceIndex <= payload.sources.length) {
      const citation = document.createElement("button");
      citation.className = "answer-citation";
      citation.type = "button";
      citation.textContent = match[0];
      citation.setAttribute("aria-label", `Show source ${sourceIndex}`);
      citation.addEventListener("click", () => highlightSource(sourceIndex));
      answerText.append(citation);
    } else {
      answerText.append(document.createTextNode(match[0]));
    }
    previous = end;
  }
  answerText.append(document.createTextNode(payload.answer.slice(previous)));
  answerCard.append(heading, answerText);
  searchResults.append(answerCard);

  if (payload.sources.length) {
    const sourcesHeading = document.createElement("h3");
    sourcesHeading.className = "sources-heading";
    sourcesHeading.textContent = "Sources";
    searchResults.append(sourcesHeading);
    renderResults(payload.sources, true);
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
  searchStatus.textContent = askModeInput.checked ? "Preparing a grounded answer…" : "Searching your passages…";
  searchResults.replaceChildren();
  const useLlm = askModeInput.checked;
  try {
    const response = await fetch(useLlm ? "/ask" : "/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, top_k: Number(topKInput.value), use_llm: useLlm }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "Search failed.");
    if (useLlm) {
      renderAnswer(payload);
      searchStatus.textContent = payload.refused
        ? "No relevant passage found in the indexed documents."
        : `Answer generated from ${payload.sources.length} ${payload.sources.length === 1 ? "source" : "sources"}${payload.model_name ? ` · ${payload.model_name}` : ""}.`;
    } else if (payload.no_relevant_passage) {
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
