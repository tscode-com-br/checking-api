const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const transportScreen = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/check/transport-screen.js'),
  'utf8'
);

const checkApp = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/check/app.js'),
  'utf8'
);

const checkHtml = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/check/index.html'),
  'utf8'
);

const checkCss = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/check/styles.css'),
  'utf8'
);

test('transport request state still persists local realized ids by chave for the fixed projection', () => {
  assert.match(checkApp, /checking\.web\.transport\.local-state\.by-chave/);
  assert.match(checkApp, /realized_request_ids/);
  assert.match(checkApp, /function persistTransportRequestLocalState\(chave\)/);
});

test('transport request state still normalizes API realized status back to confirmed for local handling', () => {
  assert.match(checkApp, /function normalizeTransportRequestStatusValue\(value\)/);
  assert.match(checkApp, /return normalizedStatus === 'realized' \? 'confirmed' : normalizedStatus;/);
});

test('transport request state still treats inactive requests as cancelled in the webapp UI', () => {
  assert.match(checkApp, /if \(!isActive && normalizedStatus !== 'realized'\) \{[\s\S]*normalizedStatus = 'cancelled';[\s\S]*\}/);
});

test('transport screen projects the latest request per modality instead of rendering the old history list', () => {
  assert.match(transportScreen, /const transportRequestProjectionKinds = \['regular', 'weekend', 'extra'\];/);
  assert.match(transportScreen, /function getLatestTransportRequestByKind\(requestKind\)/);
  assert.match(transportScreen, /function renderTransportRequestSummaries\(\)/);
  assert.match(transportScreen, /createTransportRequestSummaryCard\(requestKind, requestItem\)/);
});

test('transport screen removes the old detail overlay markup and keeps actions inside fixed modality summaries', () => {
  assert.match(checkHtml, /Última solicitação por modalidade/);
  assert.doesNotMatch(checkHtml, /id="transportRequestDetailWidget"/);
  assert.match(transportScreen, /realizedButton\.dataset\.transportRequestRealized = 'true'/);
  assert.match(transportScreen, /cancelButton\.dataset\.transportRequestCancel = 'true'/);
  assert.match(checkCss, /\.transport-request-summary-card/);
  assert.match(checkCss, /\.transport-request-summary-action\.is-realized/);
  assert.match(checkCss, /\.transport-request-summary-action\.is-cancel/);
});

test('transport webapp fetches transport state and actions with same-origin credentials', () => {
  assert.match(checkApp, /fetch\(`\$\{transportStateEndpoint\}\?chave=\$\{encodeURIComponent\(chave\)\}`, \{[\s\S]*credentials: 'same-origin'/);
  assert.match(checkApp, /async function postTransportPayload\(url, payload\) \{[\s\S]*credentials: 'same-origin'/);
});