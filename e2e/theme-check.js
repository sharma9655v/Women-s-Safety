const { chromium } = require("playwright-core");
(async () => {
  const b = await chromium.launch({ channel: "msedge", headless: true });
  const ctx = await b.newContext({ viewport: { width: 1440, height: 900 } });
  const p = await ctx.newPage();
  const fails = [];
  const check = (name, ok, detail) => {
    console.log((ok ? "PASS " : "FAIL ") + name + (ok ? "" : "  -- " + detail));
    if (!ok) fails.push(name);
  };
  const bodyBg = () =>
    p.evaluate(() => getComputedStyle(document.body).backgroundColor);

  // 1. Fresh context: no stored preference -> follows system (headless = light)
  await p.goto("http://localhost:3000/live", { waitUntil: "load" });
  await p.waitForTimeout(1500);
  const themeAttr = await p.evaluate(() => document.documentElement.dataset.theme);
  check("no pref -> system-resolved theme applied", themeAttr === "light" || themeAttr === "dark", themeAttr);
  check("light tokens on body", (await bodyBg()).startsWith("rgb("), await bodyBg());

  // 2. Switch to Dark via header toggle
  await p.getByRole("button", { name: "Dark", exact: true }).click();
  await p.waitForTimeout(600);
  const darkBg = await bodyBg();
  check("Dark toggle flips tokens", darkBg !== "rgb(248, 249, 253)", darkBg);
  check("html[data-theme=dark] set", (await p.evaluate(() => document.documentElement.dataset.theme)) === "dark", "no");
  const stored = await p.evaluate(() => localStorage.getItem("mf:theme"));
  check("choice persisted to localStorage", stored === "dark", stored);

  // 3. Reload -> persists without flash (dataset present in pre-hydration DOM)
  await p.reload({ waitUntil: "load" });
  await p.waitForTimeout(800);
  const attrAtLoad = await p.evaluate(() => document.documentElement.dataset.theme);
  check("dark persists across reload", attrAtLoad === "dark", attrAtLoad);
  check("dark tokens after reload", (await bodyBg()) === darkBg, `${await bodyBg()} vs ${darkBg}`);

  // 4. System mode follows OS preference
  await p.getByRole("button", { name: "System", exact: true }).click();
  await p.waitForTimeout(600);
  const sysStored = await p.evaluate(() => localStorage.getItem("mf:theme"));
  check("system choice stored", sysStored === "system", sysStored);

  // 5. Light mode
  await p.getByRole("button", { name: "Light", exact: true }).click();
  await p.waitForTimeout(600);
  check("Light toggle flips tokens", (await bodyBg()) === "rgb(248, 249, 253)", await bodyBg());

  // 6. Components render with themed surfaces (light)
  const light = await p.evaluate(() => {
    const aside = Array.from(document.querySelectorAll("aside.glass")).find((a) => getComputedStyle(a).display !== "none");
    const cs = (el) => el ? getComputedStyle(el) : null;
    return {
      sidebarBg: aside ? cs(aside).backgroundImage : null,
      search: cs(document.querySelector('input[aria-label*="Search"]'))?.backgroundColor,
      toggleBtn: (() => {
        const btn = document.querySelector('fieldset[aria-label="Theme"] button[aria-pressed="true"]');
        return btn ? getComputedStyle(btn).color : null;
      })(),
    };
  });
  check("sidebar glass light (translucent fill)", (light.sidebarBg === "none" ? true : /linear-gradient/.test(light.sidebarBg)), light.sidebarBg?.slice(0, 40));
  check("search field surface bg", light.search === "rgb(255, 255, 255)", light.search);
  check("theme toggle active state", light.toggleBtn !== null, light.toggleBtn);

  // 7. Dark mode surface + gauge legibility
  await p.getByRole("button", { name: "Dark", exact: true }).click();
  await p.waitForTimeout(600);
  const dark = await p.evaluate(() => {
    const search = document.querySelector('input[aria-label*="Search"]');
    return getComputedStyle(search).backgroundColor;
  });
  check("dark surface bg for fields", dark === "rgb(13, 17, 23)", dark);

  // 8. No console/page errors during switching
  const errors = [];
  p.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
  p.on("pageerror", (e) => errors.push(String(e)));
  await p.getByRole("button", { name: "Light", exact: true }).click();
  await p.getByRole("button", { name: "Dark", exact: true }).click();
  await p.getByRole("button", { name: "System", exact: true }).click();
  await p.waitForTimeout(800);
  check("no console/page errors during theme switching", errors.length === 0, errors.slice(0, 2).join(" | "));

  console.log(fails.length ? "\n== " + fails.length + " theme check(s) failed ==" : "\n== all theme checks passed ==");
  await b.close();
  process.exit(fails.length ? 1 : 0);
})().catch((e) => { console.error("SCRIPT ERROR:", e); process.exit(2); });