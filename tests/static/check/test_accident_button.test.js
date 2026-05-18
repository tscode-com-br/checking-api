const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const staticDir = path.join(__dirname, "../../../sistema/app/static/check");

const html = fs.readFileSync(path.join(staticDir, "index.html"), "utf8");
const accidentJs = fs.readFileSync(path.join(staticDir, "accident.js"), "utf8");
const appJs = fs.readFileSync(path.join(staticDir, "app.js"), "utf8");

test("test_button_renders_after_login", () => {
  // Button exists in HTML
  assert.match(html, /id="accidentReportButton"/);
  assert.match(html, /accident-report-button-label/);
  // JS reveals it after login (onLogin triggers refreshState which calls updateReportButton)
  assert.match(accidentJs, /updateReportButton/);
  assert.match(accidentJs, /btn\.hidden = false/);
  // app.js calls onLogin after authenticated load
  assert.match(appJs, /window\.AccidentMode.*onLogin/);
});

test("test_wizard_opens_when_inactive", () => {
  assert.match(accidentJs, /if \(state\.isActive\) openAccidentActionsDialog/);
  assert.match(accidentJs, /else openAccidentWizard/);
  assert.match(accidentJs, /async function openAccidentWizard/);
  assert.match(accidentJs, /\/api\/web\/check\/accident\/wizard\/projects/);
  assert.match(accidentJs, /\/api\/web\/check\/accident\/open/);
});

test("test_dialog_opens_when_active", () => {
  assert.match(accidentJs, /function openAccidentActionsDialog/);
  assert.match(html, /id="accidentActionsDialog"/);
  assert.match(html, /id="accidentActionsVideoButton"/);
  assert.match(accidentJs, /accidentActionsVideoButton/);
  assert.match(accidentJs, /window\.AccidentCamera/);
});

test("test_sse_message_triggers_refresh", () => {
  assert.match(accidentJs, /new EventSource/);
  assert.match(accidentJs, /data\.reason.*startsWith\("accident_"\)/);
  assert.match(accidentJs, /scheduleRefresh/);
  assert.match(accidentJs, /function scheduleRefresh/);
  assert.match(accidentJs, /setTimeout/);
  assert.match(accidentJs, /250/);
});

test("test_confirm_submits_report", () => {
  assert.match(accidentJs, /function askConfirm/);
  assert.match(accidentJs, /\/api\/web\/check\/accident\/report/);
  assert.match(accidentJs, /method: "POST"/);
  assert.match(accidentJs, /chave: getCurrentChave\(\).*zone.*status/s);
});

test("test_zone_accident_changes_button_labels", () => {
  assert.match(accidentJs, /zoneAccidentBtn\.addEventListener/);
  assert.match(accidentJs, /Preciso de Ajuda/);
  assert.match(accidentJs, /Estou bem\./);
  assert.match(accidentJs, /Sua Situa/);
});

test("test_audio_video_permission_button_in_settings", () => {
  assert.match(html, /id="settingsAudioVideoPermissionButton"/);
  assert.match(accidentJs, /settingsAudioVideoPermissionButton/);
  assert.match(accidentJs, /navigator\.mediaDevices\.getUserMedia/);
  assert.match(accidentJs, /Audio.*Video.*permitido/);
});
