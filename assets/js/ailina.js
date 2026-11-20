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
    styleScores();
    styleMeta();
  });
})();
