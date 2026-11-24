(function () {
  "use strict";

  function isHeading(el) {
    return el && /^(H2|H3|HR)$/.test(el.tagName);
  }

  function groupStories() {
    const content = document.querySelector(".content-panel.is-issue");
    if (!content) return;

    const headings = Array.from(content.querySelectorAll(":scope > h3"));
    headings.forEach(function (heading) {
      const card = document.createElement("article");
      card.className = "story-card";
      const parent = heading.parentNode;
      parent.insertBefore(card, heading);
      let node = heading;
      while (node && (node === heading || !isHeading(node))) {
        const next = node.nextSibling;
        card.appendChild(node);
        node = next;
      }
      if (node && node.tagName === "HR") node.remove();
    });

    /* Main markdown contains a plain summary list; keep it lightweight. */
    const toc = content.querySelector(":scope > ol");
    if (toc) toc.setAttribute("aria-label", "Темы выпуска");
  }

  function addStoryPreviews() {
    document.querySelectorAll(".story-card .ailina-preview-data").forEach(function (marker) {
      const card = marker.closest(".story-card");
      const heading = card.querySelector("h3");
      const title = heading ? heading.textContent.toLowerCase() : "";
      const label = /промпт|prompt/.test(title) ? "ПРАКТИКА" :
        /исследован|arxiv|research|benchmark/.test(title) ? "НАУКА" :
        /робот|гаджет|устройств|robot|hardware/.test(title) ? "УСТРОЙСТВА" :
        /модел|llm|model|claude|gemini|gpt/.test(title) ? "МОДЕЛИ" : "ИИ-РАДАР";
      const preview = document.createElement("figure");
      preview.className = "story-preview";
      const fallback = document.createElement("span");
      fallback.className = "story-preview-fallback";
      fallback.setAttribute("aria-hidden", "true");
      const motif = document.createElement("span");
      motif.className = "story-preview-motif";
      motif.textContent = "✳";
      const caption = document.createElement("span");
      caption.className = "story-preview-label";
      caption.textContent = label;
      fallback.append(motif, caption);
      preview.append(fallback);
      const url = marker.dataset.image || "";
      if (/^https:\/\//i.test(url)) {
        const img = document.createElement("img");
        img.alt = "Превью из источника новости";
        img.loading = "lazy";
        img.decoding = "async";
        img.referrerPolicy = "no-referrer";
        img.addEventListener("load", function () {
          if (img.naturalWidth >= 100 && img.naturalHeight >= 60) {
            preview.classList.add("has-image");
          } else {
            img.remove();
          }
        });
        img.addEventListener("error", function () { img.remove(); });
        img.src = url;
        preview.append(img);
      }
      marker.replaceWith(preview);
      card.classList.add("with-preview");
    });
  }

  function styleScores() {
    const scoreRegex = /⭐️\s*(\d+(?:\.\d+)?)\/10/;
    document.querySelectorAll(".content-panel h3, .content-panel ol li").forEach(function (el) {
      const match = el.innerHTML.match(scoreRegex);
      if (!match) return;
      const score = Number(match[1]);
      const tier = score >= 9 ? "high" : score >= 7 ? "good" : score >= 5 ? "mid" : "low";
      el.innerHTML = el.innerHTML.replace(
        scoreRegex,
        '<span class="score-badge" data-tier="' + tier + '" aria-label="Оценка значимости ' + match[1] + ' из 10">' + match[1] + '/10</span>'
      );
    });
  }

  function styleMeta() {
    document.querySelectorAll(".content-panel .story-card p").forEach(function (p) {
      const text = (p.textContent || "").trim();
      if (/^(rss|telegram|reddit|github|hackernews|hn)\s*·/i.test(text)) {
        p.classList.add("source-line");
      } else if (/^Практичность\s*:/.test(text)) {
        p.classList.add("practicality-line");
      } else if (/^(Темы|Tags|标签)\s*:/.test(text)) {
        p.classList.add("tag-line");
      }
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    groupStories();
    addStoryPreviews();
    styleScores();
    styleMeta();
  });
})();
