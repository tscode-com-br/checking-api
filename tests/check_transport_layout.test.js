const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const checkCss = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/check/styles.css'),
  'utf8'
);

test('transport scheduling screen card fills the available viewport height within the dialog padding', () => {
  assert.match(
    checkCss,
    /\.transport-screen\s*\{[\s\S]*--transport-screen-card-height:\s*calc\(var\(--app-viewport-height\) - \(2 \* var\(--page-padding-block\)\)\);/
  );
  assert.match(
    checkCss,
    /\.transport-screen-card\s*\{[\s\S]*min-height:\s*var\(--transport-screen-card-height\);[\s\S]*height:\s*var\(--transport-screen-card-height\);[\s\S]*max-height:\s*var\(--transport-screen-card-height\);/
  );
});

test('transport request history grows into the remaining transport screen space', () => {
  assert.match(
    checkCss,
    /\.transport-request-history-section\s*\{[\s\S]*display:\s*flex;[\s\S]*flex:\s*0 0 auto;[\s\S]*min-height:\s*auto;/
  );
  assert.match(
    checkCss,
    /\.transport-request-history-list\s*\{[\s\S]*display:\s*grid;[\s\S]*grid-template-columns:\s*minmax\(0, 1fr\);[\s\S]*overflow:\s*visible;/
  );
  assert.match(
    checkCss,
    /\.transport-request-summary-card\s*\{[\s\S]*display:\s*grid;[\s\S]*min-height:\s*116px;[\s\S]*border-left:\s*4px solid transparent;/
  );
});

test('transport shell keeps the instruction and option buttons compact and side by side', () => {
  assert.match(
    checkCss,
    /\.transport-option-instruction\s*\{[\s\S]*width:\s*min\(100%, 420px\);[\s\S]*margin:\s*0 auto;[\s\S]*text-align:\s*center;/
  );
  assert.match(
    checkCss,
    /\.transport-option-buttons\s*\{[\s\S]*grid-template-columns:\s*repeat\(3, minmax\(0, 1fr\)\);[\s\S]*gap:\s*clamp\(8px, 2\.5vw, 12px\);[\s\S]*width:\s*min\(100%, 420px\);/
  );
  assert.match(
    checkCss,
    /\.transport-option-button\s*\{[\s\S]*min-height:\s*clamp\(62px, 13vw, 72px\);[\s\S]*padding:\s*10px 8px;[\s\S]*font-size:\s*0\.76rem;/
  );
  assert.match(
    checkCss,
    /\.transport-option-button-label\s*\{[\s\S]*display:\s*block;[\s\S]*max-width:\s*8ch;[\s\S]*text-align:\s*center;/
  );
});