(() => {
  const $ = (s) => document.querySelector(s);
  const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));

  /* Live clock in the eyebrow */
  const clock = $("#clock");
  const setClock = () => {
    clock.textContent = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  };
  setClock();
  setInterval(setClock, 15000);

  /* Ticker of closed cases, duplicated for a seamless loop */
  const closed = [
    "Blocked toilet unblocked · Willowmere Rd",
    "Hedge trimmed · Copperfield Walk",
    "Checkout clean booked and invoiced",
    "Dishwasher door fixed",
    "Front door lock replaced",
    "Oven repaired before Sunday lunch",
    "Shower tap stopped dripping",
    "Washing machine replaced",
    "Bedroom window handle fixed",
    "Solar panel readings collected",
    "Spare keys cut and delivered",
    "Shed door rehung",
  ];
  const track = $("#tickerTrack");
  const itemsHtml = closed
    .map((t) => `<span class="ticker-item"><span class="tick">✓</span>${t}</span>`)
    .join("");
  track.innerHTML = itemsHtml;
  const clone = track.cloneNode(true);
  clone.removeAttribute("id");
  clone.setAttribute("aria-hidden", "true");
  track.after(clone);

  /* Mascot eyes */
  const mascot = $("#mascot");
  const eyes = $("#eyes");
  const REST = { x: -40, y: -12 }; // glancing up-left at the speech bubble
  let mouse = null;
  let lastMouseAt = 0;
  let glanceUntil = 0;

  const setEyes = (x, y) => { eyes.style.transform = `translate(${x}px, ${y}px)`; };

  const eyeOffset = (svg, px, py) => {
    const r = svg.getBoundingClientRect();
    const dx = px - (r.left + r.width * 0.55);
    const dy = py - (r.top + r.height * 0.5);
    const dist = Math.hypot(dx, dy) || 1;
    const k = Math.min(dist / 260, 1);
    // Logo eyes already sit right of centre, so they travel further left than right.
    return [-22 + (dx / dist) * 32 * k, (dy / dist) * 18 * k];
  };

  const lookAt = (px, py) => setEyes(...eyeOffset(mascot, px, py));

  const lookAtEl = (el) => {
    const r = el.getBoundingClientRect();
    lookAt(r.left + r.width / 2, r.top + r.height / 2);
  };

  const settle = () => {
    if (mouse && Date.now() - lastMouseAt < 3000) lookAt(mouse.x, mouse.y);
    else setEyes(REST.x, REST.y);
  };

  /* Every other little house on the page (team, footer peek) watches the cursor too */
  const otherEyes = [...document.querySelectorAll("svg[data-eyes] .eyes")];
  let othersFrame = 0;
  const aimOthers = () => {
    othersFrame = 0;
    for (const el of otherEyes) {
      const svg = el.ownerSVGElement;
      const r = svg.getBoundingClientRect();
      if (r.bottom < 0 || r.top > innerHeight) continue;
      const [x, y] = eyeOffset(svg, mouse.x, mouse.y);
      el.style.transform = `translate(${x}px, ${y}px)`;
    }
  };

  window.addEventListener("pointermove", (e) => {
    if (e.pointerType !== "mouse") return;
    mouse = { x: e.clientX, y: e.clientY };
    lastMouseAt = Date.now();
    if (Date.now() > glanceUntil) lookAt(mouse.x, mouse.y);
    if (!othersFrame) othersFrame = requestAnimationFrame(aimOthers);
  }, { passive: true });
  setInterval(() => { if (Date.now() > glanceUntil) settle(); }, 1200);

  const glance = (el, ms = 1100) => {
    glanceUntil = Date.now() + ms;
    lookAtEl(el);
    setTimeout(() => { if (Date.now() >= glanceUntil) settle(); }, ms);
  };

  /* Blinking */
  const blink = async () => {
    eyes.classList.add("blink");
    await wait(110);
    eyes.classList.remove("blink");
  };
  const blinkLoop = async () => {
    await wait(2200 + Math.random() * 3200);
    await blink();
    if (Math.random() < 0.25) { await wait(160); await blink(); }
    blinkLoop();
  };
  if (!reduceMotion) blinkLoop();

  const blinkOthers = async () => {
    await wait(900 + Math.random() * 1800);
    const el = otherEyes[Math.floor(Math.random() * otherEyes.length)];
    el.classList.add("blink");
    await wait(110);
    el.classList.remove("blink");
    blinkOthers();
  };
  if (!reduceMotion && otherEyes.length) blinkOthers();

  /* Body animations */
  const play = (el, cls) => {
    el.classList.remove(cls);
    void el.getBoundingClientRect();
    el.classList.add(cls);
  };

  /* Click the mascot for a quip */
  const quip = $("#quip");
  const quips = [
    "Boop! I'm on shift.",
    "Careful, I'm load-bearing.",
    "Windows? I know a guy.",
    "No hard hat needed. I am the house.",
    "Rent's in. Kettle's on.",
  ];
  let quipIndex = 0;
  let quipTimer;
  const say = (text) => {
    quip.textContent = text;
    quip.classList.add("show");
    clearTimeout(quipTimer);
    quipTimer = setTimeout(() => quip.classList.remove("show"), 2000);
  };
  mascot.addEventListener("click", () => {
    play(mascot, "squish");
    say(quips[quipIndex++ % quips.length]);
  });

  /* Speech bubble: Properly narrating its day */
  const messages = [
    { ch: "call",   meta: "02:14 · Flat 3, Willowmere Rd", text: "Leak under the sink at 2am. Calmed everyone down and booked a plumber for 8." },
    { ch: "email",  meta: "07:02 · 38 new emails",          text: "Inbox zero before your alarm went off. You're welcome." },
    { ch: "repair", meta: "09:30 · Copperfield Walk",       text: "Got quotes for the hedge. Picked the gardener who actually turns up." },
    { ch: "books",  meta: "12:00 · Month end",              text: "Rent's reconciled and the books balance. Obviously." },
    { ch: "call",   meta: "14:47 · Call from the landlord", text: "Told Rowan the boiler's fixed. Sent photos as proof." },
    { ch: "repair", meta: "16:20 · Flat 12 checkout",       text: "Checkout clean booked. Deposit return drafted and ready for you." },
    { ch: "email",  meta: "18:05 · Tenant question",        text: "Explained the bin schedule. For the fourth time. Kindly." },
    { ch: "books",  meta: "23:59 · Late rent",              text: "Sent a friendly nudge about late rent. Two have paid already." },
  ];

  const bubble = $("#bubble");
  const bubbleMeta = $("#bubbleMeta");
  const bubbleText = $("#bubbleText");
  const bubbleIcon = $("#bubbleIcon use");
  const tally = $("#tally");
  const chips = Object.fromEntries(
    [...document.querySelectorAll(".chip-pos")].map((el) => [el.dataset.ch, el])
  );
  let handled = 0;

  const type = async (text) => {
    bubbleText.textContent = "";
    if (reduceMotion) { bubbleText.textContent = text; return; }
    for (const ch of text) {
      bubbleText.textContent += ch;
      await wait(/[.,!?]/.test(ch) ? 160 : 22 + Math.random() * 20);
    }
  };

  const runMessage = async (m) => {
    const chip = chips[m.ch];
    chip.classList.add("active");
    glance(chip, 1000);
    await wait(650);

    bubbleIcon.setAttribute("href", `#i-${m.ch}`);
    bubbleMeta.textContent = m.meta;
    play(bubble, "pop");
    await type(m.text);

    chip.classList.remove("active");
    play(chip, "done");
    play(mascot, "hop");
    tally.textContent = ++handled;
    play(tally, "bump");
    await wait(2600);
  };

  const loop = async () => {
    await wait(reduceMotion ? 0 : 2300); // let the entrance finish
    for (let i = 0; ; i++) await runMessage(messages[i % messages.length]);
  };
  loop();

  /* Signup: posts to the landing server, which saves it and pings the team chat */
  const form = $("#signup");
  const input = $("#email");
  const fields = [$("#signup-name"), $("#signup-company"), input];
  const button = form.querySelector("button");
  const burst = () => {
    if (reduceMotion) return;
    const colors = ["#ffe45c", "#ff6f59", "#f5f5f5", "#8dbee3"];
    const r = button.getBoundingClientRect();
    const f = form.getBoundingClientRect();
    for (let i = 0; i < 18; i++) {
      const c = document.createElement("span");
      c.className = "confetti";
      const angle = (Math.PI * 2 * i) / 18 + Math.random() * 0.4;
      const dist = 70 + Math.random() * 70;
      c.style.left = `${r.left - f.left + r.width / 2}px`;
      c.style.top = `${r.top - f.top + r.height / 2}px`;
      c.style.setProperty("--c", colors[i % colors.length]);
      c.style.setProperty("--tx", `${Math.cos(angle) * dist}px`);
      c.style.setProperty("--ty", `${Math.sin(angle) * dist - 30}px`);
      c.style.setProperty("--rot", `${Math.random() * 540 - 270}deg`);
      if (i % 2) c.style.borderRadius = "50%";
      form.appendChild(c);
      setTimeout(() => c.remove(), 950);
    }
  };
  const status = $("#signupStatus");
  const fail = (message, field = input) => {
    play(form, "shake");
    field.focus();
    glance(field, 1400);
    status.textContent = message;
  };

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (button.disabled) return;
    const empty = fields.find((field) => !field.value.trim());
    if (empty && empty !== input) {
      fail(`Pop in your ${empty.name} and we'll say hello.`, empty);
      return;
    }
    if (!input.checkValidity() || !input.value) {
      input.placeholder = "Need an email to say hello";
      fail("Pop in a valid email address and we'll say hello.");
      return;
    }

    button.disabled = true;
    button.textContent = "Saving…";
    status.textContent = "";
    let result;
    try {
      const res = await fetch("/api/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: fields[0].value, company: fields[1].value, email: input.value, website: form.elements.website.value,
        }),
      });
      result = { ok: res.ok, ...(await res.json().catch(() => ({}))) };
    } catch {
      result = { ok: false };
    }
    button.disabled = false;

    if (!result.ok) {
      button.textContent = "Hire Properly";
      fail(result.error ?? "That didn't save. Check your connection and try again.");
      return;
    }
    form.classList.add("is-done");
    fields.forEach((field) => { field.value = ""; });
    input.placeholder = "We'll be in touch very soon";
    play(mascot, "hop");
    glance(button, 1400);
    if (result.duplicate) {
      button.textContent = "Already on the list!";
      status.textContent = "You're already on the list. We haven't forgotten you.";
      say("Back again? You're already in.");
      return;
    }
    button.textContent = "You're on the list!";
    status.textContent = "Thanks! We'll be in touch soon.";
    burst();
    say("A new landlord! Kettle's on.");
  });

  document.querySelectorAll('a[href="#signup"]').forEach((a) => {
    a.addEventListener("click", (e) => {
      e.preventDefault();
      form.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "center" });
      setTimeout(() => fields[0].focus({ preventScroll: true }), reduceMotion ? 0 : 700);
    });
  });

  /* Scroll reveals */
  const revealer = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      entry.target.classList.add("in");
      revealer.unobserve(entry.target);
    }
  }, { threshold: 0.15, rootMargin: "0px 0px -40px 0px" });
  document.querySelectorAll(".reveal, .peek").forEach((el) => revealer.observe(el));

  /* How it works: the little house walks the track, one step at a time */
  const stepsEl = $("#steps");
  const steps = [...stepsEl.querySelectorAll(".step")];
  const walker = $("#walker");
  const walkerEyes = walker.querySelector(".eyes");
  let current = 0;
  let paused = false;
  let howVisible = false;

  const goTo = (i) => {
    if (i === current) return;
    walkerEyes.style.transform = `translate(${i > current ? 10 : -52}px, 0px)`;
    current = i;
    steps.forEach((s, j) => s.classList.toggle("active", j === i));
    stepsEl.style.setProperty("--step", i);
    play(walker, "hop");
  };

  steps.forEach((s, j) => s.addEventListener("mouseenter", () => { paused = true; goTo(j); }));
  stepsEl.addEventListener("mouseleave", () => { paused = false; });
  new IntersectionObserver(([entry]) => { howVisible = entry.isIntersecting; }, { threshold: 0.3 }).observe(stepsEl);
  setInterval(() => {
    if (howVisible && !paused && !reduceMotion) goTo((current + 1) % steps.length);
  }, 2600);
})();
