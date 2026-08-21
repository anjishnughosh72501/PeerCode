import puppeteer from "puppeteer-core";

const EDGE = "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const URL = "http://127.0.0.1:7432/";

const browser = await puppeteer.launch({
  executablePath: EDGE,
  headless: "new",
  args: ["--no-first-run", "--disable-gpu"],
});

const page = await browser.newPage();
await page.setViewport({ width: 1366, height: 850 });

page.on("pageerror", (e) => console.log("PAGEERROR:", e.message));
page.on("console", (m) => {
  if (["error", "warning"].includes(m.type())) console.log("CONSOLE:", m.type(), m.text());
});

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

await page.goto(URL, { waitUntil: "networkidle2" });
console.log("loaded launcher");

// click Host Session card
await page.evaluate(() => {
  const el = [...document.querySelectorAll("h2")].find((h) => h.textContent.includes("Host Session"));
  el.closest("[class*='cursor-pointer'], .glass").click();
});
await sleep(800);

// fill form
await page.type("input[placeholder='Host']", "AutoHost");
const pathInput = await page.$("input[placeholder^='C:']");
await pathInput.type(process.env.DEMO_DIR || "C:\\nonexistent-demo");

// click Start Hosting
await page.evaluate(() => {
  const btn = [...document.querySelectorAll("button")].find((b) => b.textContent.includes("Start Hosting"));
  btn.click();
});
await sleep(2500);

let text = await page.evaluate(() => document.body.innerText.slice(0, 300));
console.log("AFTER HOSTING BODY:", JSON.stringify(text.slice(0, 150)));

// switch to Files section and open a file
await page.evaluate(() => {
  const nav = document.querySelector("button[title='Files']");
  nav?.click();
});
await sleep(800);
const clicked = await page.evaluate(() => {
  const rows = [...document.querySelectorAll("button")];
  const file = rows.find((b) => b.textContent.trim() === "hello.py" || b.textContent.trim() === "untitled.py");
  if (file) { file.click(); return file.textContent.trim(); }
  return null;
});
console.log("clicked file:", clicked);
await sleep(2000);

text = await page.evaluate(() => document.body.innerText.slice(0, 400));
console.log("AFTER FILE OPEN BODY:", JSON.stringify(text.slice(0, 250)));
console.log("editor value:", await page.evaluate(() => document.querySelector("textarea")?.value));
console.log("root children:", await page.evaluate(() => document.getElementById("root").children.length));

await browser.close();
