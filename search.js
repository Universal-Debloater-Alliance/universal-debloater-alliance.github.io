(() => {
  const siteRoot = new URL(".", document.currentScript.src);
  const content = document.querySelector("#content");
  const search = document.querySelector(".docs-search");
  const input = search.querySelector("input");
  const panel = search.querySelector(".search-results");
  const status = search.querySelector(".search-status");
  const announcement = search.querySelector(".search-announcement");
  const results = panel.querySelector("ul");
  let index;
  let revision = 0;

  function revealFragment(scroll = false) {
    let anchor;
    try {
      anchor = decodeURIComponent(location.hash.slice(1));
    } catch {
      return;
    }
    const target = document.getElementById(anchor);
    if (!target || !content.contains(target)) return;

    for (
      let details = target.closest("details");
      details;
      details = details.parentElement.closest("details")
    ) {
      if (!details.open) {
        details.open = true;
        scroll = true;
      }
    }
    if (scroll) target.scrollIntoView();
  }

  function loadIndex() {
    index ??= fetch(new URL("search-index.json", siteRoot))
      .then((response) => {
        if (!response.ok) throw new Error("Search index unavailable");
        return response.json();
      })
      .then((pages) =>
        pages.flatMap((page) =>
          page.sections.map((section) => {
            const title = section.title || page.title;
            return {
              title,
              page: section.title ? page.title : "",
              url: section.anchor ? `${page.url}#${encodeURIComponent(section.anchor)}` : page.url,
              text: section.text,
              heading: title.toLowerCase(),
              body: section.text.toLowerCase(),
            };
          }),
        ),
      )
      .catch((error) => {
        index = undefined;
        throw error;
      });
    return index;
  }

  function rank(entry, query, terms) {
    const { heading, body } = entry;
    if (heading === query) return 5;
    if (heading.includes(query)) return 4;
    if (terms.every((term) => heading.includes(term))) return 3;
    if (body.includes(query)) return 2;
    return terms.every((term) => heading.includes(term) || body.includes(term)) ? 1 : 0;
  }

  function snippet(entry, query, terms) {
    let at = entry.body.indexOf(query);
    if (at < 0) at = terms.map((term) => entry.body.indexOf(term)).find((at) => at >= 0) ?? 0;
    const start = Math.max(0, at - 40);
    const end = start + 140;
    return `${start ? "…" : ""}${entry.text.slice(start, end).trim()}${end < entry.text.length ? "…" : ""}`;
  }

  function showStatus(message, announceOnly = false) {
    announcement.textContent = message;
    status.textContent = announceOnly ? "" : message;
    status.hidden = announceOnly || !message;
  }

  function dismiss() {
    revision++;
    panel.hidden = true;
    results.replaceChildren();
    showStatus("");
  }

  async function update() {
    const query = input.value.trim().toLowerCase().replace(/\s+/g, " ");
    if (!query) {
      dismiss();
      return;
    }

    const current = ++revision;
    panel.hidden = false;
    if (!index) showStatus("Loading search…");
    try {
      const entries = await loadIndex();
      if (current !== revision) return;
      const terms = query.split(" ");
      const matches = entries
        .map((entry) => ({ entry, score: rank(entry, query, terms) }))
        .filter(({ score }) => score)
        .sort((a, b) => b.score - a.score);

      const items = matches.slice(0, 8).map(({ entry }) => {
        const item = document.createElement("li");
        const link = document.createElement("a");
        link.href = new URL(entry.url, siteRoot);
        link.textContent = entry.title;
        if (entry.page) {
          const page = document.createElement("small");
          page.textContent = entry.page;
          link.append(page);
        }
        if (entry.text) {
          const excerpt = document.createElement("small");
          excerpt.textContent = snippet(entry, query, terms);
          link.append(excerpt);
        }
        item.append(link);
        return item;
      });
      results.replaceChildren(...items);
      panel.scrollTop = 0;
      if (items.length) {
        showStatus(`${items.length} ${items.length === 1 ? "result" : "results"} shown`, true);
      } else {
        showStatus("No results found.");
      }
    } catch {
      if (current === revision) showStatus("Search couldn’t load. Try again.");
    }
  }

  input.addEventListener("input", update);
  input.addEventListener("focus", () => {
    if (panel.hidden) update();
  });
  search.addEventListener("keydown", (event) => {
    if (event.isComposing) return;
    if (event.key === "Escape" && !panel.hidden) {
      event.preventDefault();
      input.focus();
      dismiss();
    } else if (event.key === "Enter" && event.target === input) {
      if (panel.hidden || !results.firstElementChild) {
        update();
      } else {
        results.querySelector("a").click();
      }
    }
  });
  results.addEventListener("click", (event) => {
    const link = event.target.closest("a");
    if (
      !link ||
      event.button !== 0 ||
      event.ctrlKey ||
      event.metaKey ||
      event.shiftKey ||
      event.altKey
    )
      return;
    if (link.href === location.href && location.hash) revealFragment(true);
    setTimeout(dismiss, 0);
  });
  search.addEventListener("focusout", (event) => {
    if (event.relatedTarget && !search.contains(event.relatedTarget)) dismiss();
  });
  document.addEventListener("click", (event) => {
    if (!search.contains(event.target) && !panel.hidden) dismiss();
  });
  window.addEventListener("hashchange", () => revealFragment());
  revealFragment();
  search.hidden = false;
})();
