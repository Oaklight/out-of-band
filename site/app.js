(() => {
  "use strict";

  const state = {
    lang: detectLang(),
    scenario: 0,
    step: 0,
  };

  function detectLang() {
    const asked = new URLSearchParams(location.search).get("lang");
    if (asked === "en" || asked === "zh") return asked;
    try {
      const saved = localStorage.getItem("outboard-lang");
      if (saved === "en" || saved === "zh") return saved;
    } catch (_) {
      /* storage can be unavailable; fall through */
    }
    // English is the default. Chinese is offered when it is the visitor's
    // first preference, or when they pick it with the toggle.
    const preferred =
      (navigator.languages && navigator.languages[0]) || navigator.language || "en";
    return preferred.toLowerCase().startsWith("zh") ? "zh" : "en";
  }

  function saveLang() {
    try {
      localStorage.setItem("outboard-lang", state.lang);
    } catch (_) {
      /* a private window will just forget it */
    }
  }

  const L = (value) => (value && typeof value === "object" ? value[state.lang] : value);

  function node(tag, cls, text) {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined) n.textContent = text;
    return n;
  }

  function html(tag, cls, markup) {
    const n = node(tag, cls);
    n.innerHTML = markup;
    return n;
  }

  function currentScenario() {
    return SCENARIOS[state.scenario];
  }

  function currentStep() {
    return currentScenario().steps[state.step];
  }

  /* ---------- static sections ---------- */

  function renderStatic() {
    document.documentElement.lang = state.lang;
    document.querySelectorAll("[data-i18n]").forEach((n) => {
      const key = n.getAttribute("data-i18n");
      if (UI[state.lang][key] !== undefined) n.textContent = UI[state.lang][key];
    });
    document.title =
      state.lang === "zh" ? "outboard — 带外回执导览" : "outboard — a guided tour";

    const langBtn = document.getElementById("lang");
    langBtn.textContent = state.lang === "zh" ? "English" : "中文";
    langBtn.setAttribute("aria-label", state.lang === "zh" ? "Switch to English" : "切换到中文");

    renderActors();
    renderTabs();
    renderLimits();
    renderFaq();
    renderVariants();
    renderStates();
    renderAdopt();
  }

  function renderActors() {
    const host = document.getElementById("actors");
    host.replaceChildren();
    UI[state.lang].actors.forEach((actor, i) => {
      const side = ["github-side", "operator-side", "target-side"][i];
      const card = node("div", `actor ${side}`);
      card.appendChild(node("span", "tag", actor.tag));
      card.appendChild(node("h3", "", actor.title));
      const ul = node("ul");
      actor.items.forEach((item) => ul.appendChild(node("li", "", item)));
      card.appendChild(ul);
      card.appendChild(node("div", "flow", actor.flow));
      host.appendChild(card);
    });
  }

  function renderTabs() {
    const host = document.getElementById("scenario-tabs");
    host.replaceChildren();
    SCENARIOS.forEach((scenario, i) => {
      const b = node("button", "tab", L(scenario.label));
      b.type = "button";
      b.setAttribute("role", "tab");
      b.setAttribute("aria-selected", String(i === state.scenario));
      b.addEventListener("click", () => {
        state.scenario = i;
        state.step = 0;
        renderTabs();
        renderStep(true);
      });
      host.appendChild(b);
    });
  }

  function renderLimits() {
    const host = document.getElementById("limits-list");
    host.replaceChildren();
    UI[state.lang].limits.forEach((item) => {
      const li = node("li", "limit");
      li.appendChild(node("strong", "", item.title));
      li.appendChild(node("p", "", item.text));
      host.appendChild(li);
    });
  }

  function renderFaq() {
    const host = document.getElementById("faq-list");
    host.replaceChildren();
    UI[state.lang].faq.forEach((item, i) => {
      const d = node("details", "faq-item");
      if (i === 0) d.open = true;
      const summary = node("summary", "", item.q);
      d.appendChild(summary);
      d.appendChild(node("p", "", item.a));
      host.appendChild(d);
    });
  }

  function renderVariants() {
    const host = document.getElementById("variants");
    host.replaceChildren();
    VARIANTS.forEach((variant) => {
      const card = node("article", "card");
      card.appendChild(node("h3", "", L(variant.title)));
      card.appendChild(node("p", "", L(variant.text)));
      const a = node("a", "", UI[state.lang].openGuide);
      a.href = state.lang === "zh" ? variant.hrefZh : variant.href;
      card.appendChild(a);
      host.appendChild(card);
    });
  }

  function renderStates() {
    const host = document.getElementById("state-grid");
    host.replaceChildren();
    STATES.forEach((s) => {
      const card = node("article", `state-card ${s.key}`);
      card.appendChild(node("h3", "", s.title));
      card.appendChild(node("p", "", L(s.text)));
      host.appendChild(card);
    });
  }

  function renderAdopt() {
    const host = document.getElementById("adopt");
    host.replaceChildren();
    ADOPT.forEach((item) => {
      const li = node("li");
      li.appendChild(node("strong", "", L(item.title)));
      const span = html("span", "", L(item.text));
      li.appendChild(span);
      host.appendChild(li);
    });
  }

  /* ---------- tour ---------- */

  function renderStepper() {
    const host = document.getElementById("stepper");
    host.replaceChildren();
    currentScenario().steps.forEach((step, i) => {
      const b = node("button", "step-dot");
      b.type = "button";
      b.setAttribute("role", "tab");
      b.setAttribute("aria-selected", String(i === state.step));
      b.appendChild(node("span", "n", String(i + 1)));
      b.appendChild(node("span", "lbl", L(step.nav)));
      b.addEventListener("click", () => {
        state.step = i;
        renderStep(true);
      });
      host.appendChild(b);
    });
  }

  function renderControls() {
    const total = currentScenario().steps.length;
    document.getElementById("prev").textContent = UI[state.lang].prev;
    document.getElementById("next").textContent = UI[state.lang].next;
    document.getElementById("prev").disabled = state.step === 0;
    document.getElementById("next").disabled = state.step === total - 1;
    document.getElementById("counter").textContent = UI[state.lang].counter
      .replace("{n}", String(state.step + 1))
      .replace("{m}", String(total));
    document.getElementById("progress").style.width = `${((state.step + 1) / total) * 100}%`;
  }

  function renderStep(animate) {
    renderStepper();
    renderControls();

    const step = currentStep();
    const gh = document.getElementById("github-pane");
    const mc = document.getElementById("machine-pane");
    gh.replaceChildren();
    mc.replaceChildren();

    renderBlocks(step.github, gh, "github");
    renderBlocks(step.machine, mc, "machine");

    document.getElementById("step-title").textContent = L(step.title);
    document.getElementById("step-body").innerHTML = L(step.body);

    if (animate) {
      [gh, mc].forEach((pane) => {
        pane.classList.remove("swap");
        void pane.offsetWidth;
        pane.classList.add("swap");
      });
    }
  }

  function emptyPane(which) {
    const text =
      which === "github"
        ? state.lang === "zh"
          ? "暂时什么都没有。"
          : "Nothing here yet."
        : state.lang === "zh"
          ? "这一步机器上不需要做什么。"
          : "Nothing to do on the machine for this step.";
    return node("p", "note", text);
  }

  function renderBlocks(blocks, host, side) {
    if (!blocks || blocks.length === 0) {
      host.appendChild(emptyPane(side));
      return;
    }
    blocks.forEach((block) => host.appendChild(renderBlock(block, side)));
  }

  function renderBlock(block, side) {
    switch (block.t) {
      case "event":
        return node("div", "event", L(block.text));
      case "pr": {
        const wrap = node("div");
        wrap.appendChild(node("h3", "pr-title", L(block.title)));
        wrap.appendChild(node("p", "pr-meta", L(block.meta)));
        return wrap;
      }
      case "files": {
        const wrap = node("div", "files");
        block.items.forEach((f) => {
          const row = node("div", "file");
          row.appendChild(node("span", "", f.path));
          const stat = node("span", "stat");
          if (f.add) stat.appendChild(node("span", "add", f.add));
          if (f.del) stat.appendChild(node("span", "del", f.del));
          row.appendChild(stat);
          wrap.appendChild(row);
        });
        return wrap;
      }
      case "checks": {
        const wrap = node("div", "checks");
        block.items.forEach((c) => {
          const row = node("div", `check ${c.state}`);
          row.appendChild(node("span", "ind"));
          row.appendChild(node("span", "", c.name));
          row.appendChild(node("span", "state", L(c.text)));
          wrap.appendChild(row);
        });
        return wrap;
      }
      case "comment": {
        const wrap = node("div", "comment");
        const head = node("div", "comment-head");
        head.appendChild(node("strong", "", block.author));
        head.appendChild(node("span", "", L(block.time)));
        wrap.appendChild(head);
        const body = node("div", "comment-body");
        const pre = node("pre", "code small", block.body);
        body.appendChild(pre);
        wrap.appendChild(body);
        return wrap;
      }
      case "code": {
        const pre = node("pre", "code", block.text);
        if (block.text.split("\n").length > 16) pre.classList.add("small");
        return pre;
      }
      case "note":
        return html("p", "note", L(block.text));
      case "jobs": {
        const wrap = node("div", "jobs");
        block.items.forEach((j) => {
          const row = node("div", "job");
          row.appendChild(node("span", "ind"));
          row.appendChild(node("span", "", j.name));
          if (j.time) row.appendChild(node("span", "time", j.time));
          wrap.appendChild(row);
        });
        return wrap;
      }
      case "summary": {
        const wrap = node("div", "summary");
        wrap.appendChild(node("h4", "", block.title));
        wrap.appendChild(node("pre", "", block.body));
        if (block.transcript) {
          const d = node("details");
          d.appendChild(node("summary", "", L(block.details)));
          d.appendChild(node("pre", "", block.transcript));
          wrap.appendChild(d);
        }
        return wrap;
      }
      case "artifact":
        return node("div", "file", L(block.text));
      case "term": {
        const wrap = node("div");
        if (block.title) wrap.appendChild(node("p", "term-title", L(block.title)));
        const term = node("div", "term");
        block.lines.forEach((line) => {
          const span = node("span", line.k || "out", `${line.text}\n`);
          term.appendChild(span);
        });
        wrap.appendChild(term);
        return wrap;
      }
      case "receipt": {
        const wrap = node("div", "receipt");
        const head = node("div", "receipt-head");
        head.appendChild(node("span", "", L(block.label)));
        wrap.appendChild(head);
        wrap.appendChild(node("pre", "", block.text));
        return wrap;
      }
      case "kv": {
        const dl = node("dl", "kv");
        block.items.forEach((item) => {
          dl.appendChild(node("dt", "", item.k));
          dl.appendChild(html("dd", "", L(item.v)));
        });
        return dl;
      }
      case "checklist": {
        const wrap = node("ul", "checklist");
        block.items.forEach((item) => {
          const li = node("li");
          li.appendChild(node("span", "tick", "✓"));
          li.appendChild(node("span", "", L(item)));
          wrap.appendChild(li);
        });
        return wrap;
      }
      case "chips": {
        const wrap = node("div", "chips");
        block.items.forEach((c) => wrap.appendChild(node("span", "chip ok", L(c))));
        return wrap;
      }
      default:
        return node("p", "note", JSON.stringify(block));
    }
  }

  /* ---------- wiring ---------- */

  function go(delta) {
    const total = currentScenario().steps.length;
    const next = Math.min(total - 1, Math.max(0, state.step + delta));
    if (next !== state.step) {
      state.step = next;
      renderStep(true);
    }
  }

  function bind() {
    document.getElementById("prev").addEventListener("click", () => go(-1));
    document.getElementById("next").addEventListener("click", () => go(1));
    document.getElementById("lang").addEventListener("click", () => {
      state.lang = state.lang === "zh" ? "en" : "zh";
      saveLang();
      renderStatic();
      renderStep(false);
    });
    document.addEventListener("keydown", (e) => {
      if (e.target instanceof HTMLElement && /input|textarea|select/i.test(e.target.tagName)) return;
      if (e.key === "ArrowRight") go(1);
      if (e.key === "ArrowLeft") go(-1);
    });
  }

  renderStatic();
  renderStep(false);
  bind();
})();
