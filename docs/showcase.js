"use strict";

const samples = [
  {
    keys: ["coral", "bleach", "reef", "heat"],
    pages: [4, 5, 6],
    passages: [
      "Coral bleaching happens when heat stress causes corals to expel the algae living in their tissues. Without these algae, corals lose much of their color and their main energy source.",
      "Marine heatwaves can keep water temperatures above the usual summer maximum for weeks. The longer the heat stress lasts, the harder it is for a reef to recover.",
      "Bleached coral is not necessarily dead. If conditions improve, corals may regain their algae, although repeated bleaching leaves reefs more vulnerable.",
    ],
  },
  {
    keys: ["forest", "tree", "carbon"],
    pages: [8, 9, 10],
    passages: [
      "Forests remove carbon dioxide from the air through photosynthesis and store carbon in trunks, branches, roots, and leaves.",
      "Soils hold carbon from fallen leaves and dead roots. Disturbing forest soil can release some of that stored carbon back into the atmosphere.",
      "Older forests can continue to absorb carbon while also supporting habitats and helping regulate local water cycles.",
    ],
  },
  {
    keys: ["sea", "level", "ocean", "rise", "coast"],
    pages: [2, 3, 11],
    passages: [
      "Sea level rises as warming ocean water expands and melting land ice adds water to the ocean. Both processes contribute to the global average.",
      "Higher average sea levels allow storm surges to reach farther inland, increasing flood risk for some coastal communities.",
      "Local sea-level change varies with land movement, ocean currents, and regional patterns of warming.",
    ],
  },
];

function renderSample(sample) {
  const results = document.querySelector("#results");
  results.replaceChildren();
  sample.passages.forEach((text, index) => {
    const card = document.createElement("article");
    card.className = "result-card";
    const metadata = document.createElement("div");
    metadata.className = "result-meta";
    const citation = document.createElement("strong");
    citation.textContent = `[${index + 1}] climate_notes.pdf · page ${sample.pages[index]}`;
    const label = document.createElement("span");
    label.textContent = "Sample match";
    metadata.append(citation, label);
    const passage = document.createElement("p");
    passage.textContent = text;
    card.append(metadata, passage);
    results.append(card);
  });
  document.querySelector("#result-count").textContent = `${sample.passages.length} sample passages`;
}

document.querySelector("#demo-search").addEventListener("submit", (event) => {
  event.preventDefault();
  const query = document.querySelector("#query").value.toLocaleLowerCase();
  const sample = samples.find((item) => item.keys.some((key) => query.includes(key))) || samples[0];
  renderSample(sample);
});

document.querySelectorAll("[data-query]").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelector("#query").value = button.dataset.query;
    document.querySelector("#demo-search").requestSubmit();
  });
});

const pathParts = window.location.pathname.split("/").filter(Boolean);
const owner = window.location.hostname.split(".")[0];
const repository = pathParts[0];
if (owner && repository && window.location.hostname.endsWith("github.io")) {
  document.querySelector("#source-link").href = `https://github.com/${owner}/${repository}`;
} else {
  document.querySelector("#source-link").hidden = true;
}
