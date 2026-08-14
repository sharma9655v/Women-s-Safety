const { chromium } = require("playwright-core");
const errors = [];
const results = [];
function log(ok, name, detail = "") {
  results.push({ ok: !!ok, name });
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail ? ` - ${detail}` : ""}`);
}
(async () => {
  const b = await chromium.launch({ channel: "msedge", headless: true });
  const p = await (await b.newContext({ viewport: { width: 1440, height: 900 } })).newPage();
  p.on("pageerror", (e) => errors.push(String(e)));
  p.on("console", (m) => { if (m.type() === "error" && !/404|Failed to load resource/.test(m.text())) errors.push(m.text()); });

  await p.goto("http://localhost:3000/live", { waitUntil: "load" });
  await p.waitForTimeout(2500);

  // ---- map 3D machinery: wrapper present, default 2D, no tilt ----
  const wrapper = await p.locator(".map3d-perspective").count();
  log(wrapper > 0, "map3d-perspective wrapper present");
  const is3dDefault = await p.locator(".map3d-perspective").evaluate((el) => el.classList.contains("is-3d")).catch(() => true);
  const paneTransform = await p.locator(".leaflet-map-pane").evaluate((el) => getComputedStyle(el).transform).catch(() => "");
  log(!is3dDefault && (paneTransform === "none" || paneTransform === "matrix(1, 0, 0, 1, 0, 0)"), "2D default state (no tilt transform)");

  // ---- SOS flow: sidebar Emergency -> contacts dialog -> cancel ----
  await p.getByRole("button", { name: "Emergency", exact: true }).click();
  const dialog = p.locator('[role="dialog"][aria-label="Emergency"]');
  await dialog.waitFor({ timeout: 5000 }).catch(() => {});
  log((await dialog.count()) > 0, "SOS dialog opens from sidebar Emergency");
  const helpline = await dialog.locator('a[href^="tel:"]').count().catch(() => 0);
  log(helpline >= 3, "Emergency contacts shown", `${helpline} tel: links`);
  const telText = await dialog.innerText().catch(() => "");
  log(/Women Helpline/.test(telText) && /181/.test(telText) && /Police/.test(telText), "Helpline / Police contacts listed");
  await p.getByRole("button", { name: /Cancel/ }).click();
  await p.waitForTimeout(400);
  log((await dialog.count()) === 0, "SOS dialog closes on Cancel, nothing fired");

  // ---- mobile SOS entry still present on live ----
  const mpage = await b.newPage();
  await mpage.setViewportSize({ width: 390, height: 844 });
  await mpage.goto("http://localhost:3000/live", { waitUntil: "load" });
  await mpage.waitForTimeout(1500);
  const sosFab = await mpage.locator("a[aria-label*='SOS'], button[aria-label*='SOS']").count();
  log(sosFab > 0, "Mobile SOS entry present", `${sosFab} element(s)`);
  await mpage.close();

  log(errors.length === 0 ? true : false, "no console/page errors in map+SOS flows", errors.join(" | ").slice(0, 300));
  await b.close();
  const failed = results.filter((r) => !r.ok);
  console.log(`\n===== ${results.length - failed.length}/${results.length} passed =====`);
  failed.forEach((f) => console.log(`  FAILED: ${f.name}`));
  process.exit(failed.length > 0 ? 1 : 0);
})().catch((e) => { console.error("SCRIPT ERROR:", e); process.exit(2); });