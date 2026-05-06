const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const checkCss = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/check/styles.css'),
  'utf8'
);
const checkHtml = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/check/index.html'),
  'utf8'
);
const checkAppScript = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/check/app.js'),
  'utf8'
);

function extractAtRuleBlock(source, atRule) {
  const startIndex = source.indexOf(atRule);
  assert.notEqual(startIndex, -1, `Expected to find at-rule: ${atRule}`);

  const blockStartIndex = source.indexOf('{', startIndex);
  assert.notEqual(blockStartIndex, -1, `Expected opening brace for at-rule: ${atRule}`);

  let depth = 0;
  for (let index = blockStartIndex; index < source.length; index += 1) {
    const character = source[index];
    if (character === '{') {
      depth += 1;
    } else if (character === '}') {
      depth -= 1;
      if (depth === 0) {
        return source.slice(blockStartIndex + 1, index);
      }
    }
  }

  assert.fail(`Expected closing brace for at-rule: ${atRule}`);
}

function extractRuleBlock(source, selector) {
  const startIndex = source.indexOf(selector);
  assert.notEqual(startIndex, -1, `Expected to find selector: ${selector}`);

  const blockStartIndex = source.indexOf('{', startIndex);
  assert.notEqual(blockStartIndex, -1, `Expected opening brace for selector: ${selector}`);

  let depth = 0;
  for (let index = blockStartIndex; index < source.length; index += 1) {
    const character = source[index];
    if (character === '{') {
      depth += 1;
    } else if (character === '}') {
      depth -= 1;
      if (depth === 0) {
        return source.slice(blockStartIndex + 1, index);
      }
    }
  }

  assert.fail(`Expected closing brace for selector: ${selector}`);
}

test('main check shell uses dynamic viewport and measured header height to fit the device', () => {
  assert.match(
    checkCss,
    /:root\s*\{[\s\S]*--app-viewport-width:\s*100vw;[\s\S]*--app-viewport-height:\s*100vh;[\s\S]*--app-viewport-height:\s*100svh;[\s\S]*--app-viewport-height:\s*100dvh;[\s\S]*--app-header-height:/
  );
  assert.match(
    checkCss,
    /\.check-shell\s*\{[\s\S]*width:\s*100%;[\s\S]*min-height:\s*calc\(var\(--app-viewport-height\) - var\(--app-header-height\)\);[\s\S]*align-items:\s*stretch;/
  );
  assert.match(
    checkCss,
    /\.check-card\s*\{[\s\S]*margin:\s*0 auto;/
  );
});

test('root page preserves vertical scrolling support without reintroducing global scroll locks', () => {
  const htmlBlock = extractRuleBlock(checkCss, 'html {');
  const bodyBlock = extractRuleBlock(checkCss, 'body {');
  const shellBlock = extractRuleBlock(checkCss, '.check-shell {');

  assert.match(
    htmlBlock,
    /overflow-x:\s*hidden;[\s\S]*overflow-y:\s*auto;[\s\S]*overscroll-behavior-x:\s*none;[\s\S]*overscroll-behavior-y:\s*auto;/
  );
  assert.match(
    bodyBlock,
    /min-height:\s*var\(--app-viewport-height\);[\s\S]*overflow-x:\s*hidden;[\s\S]*overflow-y:\s*auto;[\s\S]*overscroll-behavior-x:\s*none;[\s\S]*overscroll-behavior-y:\s*auto;/
  );
  assert.match(
    shellBlock,
    /position:\s*relative;[\s\S]*min-height:\s*calc\(var\(--app-viewport-height\) - var\(--app-header-height\)\);[\s\S]*overflow:\s*visible;/
  );
  assert.match(
    checkCss,
    /\.check-field input,[\s\S]*\.check-field select,[\s\S]*\.submit-button,[\s\S]*\.location-refresh-button,[\s\S]*\.choice-card,[\s\S]*\.choice-card input,[\s\S]*\.choice-card-static\s*\{[\s\S]*touch-action:\s*manipulation;/
  );
  assert.doesNotMatch(bodyBlock, /touch-action:\s*manipulation;/);

  assert.match(
    checkAppScript,
    /function syncViewportLayoutMetrics\(\)\s*\{[\s\S]*const rootStyle = document\.documentElement\.style;[\s\S]*setProperty\('--app-viewport-width', `\$\{metrics\.viewportWidth\}px`\);[\s\S]*setProperty\('--app-viewport-height', `\$\{metrics\.viewportHeight\}px`\);[\s\S]*setProperty\('--app-header-height', `\$\{metrics\.headerHeight\}px`\);/
  );
  assert.doesNotMatch(checkAppScript, /addEventListener\('touchmove'/);
  assert.doesNotMatch(checkAppScript, /addEventListener\('wheel'/);
  assert.doesNotMatch(checkAppScript, /document\.body\.style\.(overflow|overflowY|position)/);
  assert.doesNotMatch(checkAppScript, /document\.documentElement\.style\.(overflow|overflowY|position)/);
});

test('main check card expands more on larger screens without losing mobile full-width behavior', () => {
  assert.match(
    checkCss,
    /:root\s*\{[\s\S]*--card-max-width:\s*680px;/
  );
  assert.match(
    checkCss,
    /@media \(min-width: 640px\)\s*\{[\s\S]*\.check-card\s*\{[\s\S]*--card-max-width:\s*760px;/
  );
  assert.match(
    checkCss,
    /@media \(min-width: 1024px\)\s*\{[\s\S]*\.check-card\s*\{[\s\S]*--card-max-width:\s*1040px;/
  );
  assert.match(
    checkCss,
    /@media \(min-width: 1180px\)\s*\{[\s\S]*\.check-card\s*\{[\s\S]*--card-max-width:\s*1160px;/
  );
});

test('wider mobile keeps the approved grid contract, 360px only compacts controls, and 340px handles the true narrow fallback', () => {
  const wideMobile480Block = extractAtRuleBlock(checkCss, '@media (max-width: 480px)');
  const compact360Block = extractAtRuleBlock(checkCss, '@media (max-width: 360px)');
  const narrow340Block = extractAtRuleBlock(checkCss, '@media (max-width: 340px)');
  const historyGridBlock = extractRuleBlock(checkCss, '.history-grid {');
  const authCredentialsBlock = extractRuleBlock(checkCss, '.auth-credentials-row {');
  const twoColumnChoiceBlock = extractRuleBlock(checkCss, '.choice-grid.two-columns {');

  assert.match(
    historyGridBlock,
    /grid-template-columns:\s*repeat\(2, minmax\(0, 1fr\)\);/
  );
  assert.match(
    authCredentialsBlock,
    /grid-template-columns:\s*repeat\(3, minmax\(0, 1fr\)\);[\s\S]*gap:\s*8px;/
  );
  assert.match(
    twoColumnChoiceBlock,
    /grid-template-columns:\s*repeat\(2, minmax\(0, 1fr\)\);/
  );

  assert.match(
    wideMobile480Block,
    /\.check-field input,[\s\S]*\.check-field select,[\s\S]*\.auth-action-button,[\s\S]*\.submit-button,[\s\S]*\.secondary-button,[\s\S]*\.choice-card\s*\{[\s\S]*font-size:\s*16px;/
  );
  assert.doesNotMatch(wideMobile480Block, /\.history-grid\s*\{/);
  assert.doesNotMatch(wideMobile480Block, /\.choice-grid\.two-columns\s*\{/);
  assert.doesNotMatch(wideMobile480Block, /\.auth-credentials-row\s*\{/);

  assert.match(
    compact360Block,
    /:root\s*\{[\s\S]*--page-padding-inline:\s*10px;[\s\S]*--card-padding:\s*12px;[\s\S]*--section-gap:\s*9px;[\s\S]*--control-height:\s*40px;/
  );
  assert.match(
    compact360Block,
    /\.auth-action-button,[\s\S]*\.check-field input,[\s\S]*\.check-field select,[\s\S]*\.submit-button,[\s\S]*\.secondary-button\s*\{[\s\S]*font-size:\s*0\.8rem;/
  );
  assert.doesNotMatch(compact360Block, /\.history-grid\s*\{/);
  assert.doesNotMatch(compact360Block, /\.choice-grid\.two-columns\s*\{/);
  assert.doesNotMatch(compact360Block, /\.auth-credentials-row\s*\{/);
  assert.doesNotMatch(compact360Block, /\.auth-field-button\s*\{/);

  assert.match(
    narrow340Block,
    /\.history-grid\s*\{[\s\S]*grid-template-columns:\s*1fr;/
  );
  assert.match(
    narrow340Block,
    /\.choice-grid\.two-columns\s*\{[\s\S]*grid-template-columns:\s*1fr;/
  );
  assert.match(
    narrow340Block,
    /\.auth-credentials-row\s*\{[\s\S]*grid-template-columns:\s*1fr;[\s\S]*gap:\s*5px;/
  );
  assert.match(
    narrow340Block,
    /\.auth-field-button\s*\{[\s\S]*grid-column:\s*auto;/
  );
});

test('web app script synchronizes viewport css variables during mobile viewport changes', () => {
  assert.match(
    checkAppScript,
    /function syncViewportLayoutMetrics\(\)\s*\{[\s\S]*setProperty\('--app-viewport-width', `\$\{metrics\.viewportWidth\}px`\);[\s\S]*setProperty\('--app-viewport-height', `\$\{metrics\.viewportHeight\}px`\);[\s\S]*setProperty\('--app-header-height', `\$\{metrics\.headerHeight\}px`\);/
  );
  assert.match(
    checkAppScript,
    /window\.addEventListener\('resize', scheduleViewportLayoutMetricsSync\);/
  );
  assert.match(
    checkAppScript,
    /window\.addEventListener\('orientationchange', \(\) => \{[\s\S]*scheduleViewportLayoutMetricsSync\(\);[\s\S]*realignViewport\(\);[\s\S]*\}\);/
  );
  assert.match(
    checkAppScript,
    /window\.visualViewport\.addEventListener\('resize', scheduleViewportLayoutMetricsSync\);/
  );
});

test('low-height landscape layout reorganizes the main form without reintroducing scroll blockers', () => {
  assert.match(checkHtml, /<fieldset id="registrationField" class="check-group">/);
  assert.match(
    checkCss,
    /@media \(orientation: landscape\) and \(max-height: 540px\)\s*\{[\s\S]*\.check-card\s*\{[\s\S]*width:\s*min\(100%, 960px\);[\s\S]*align-self:\s*start;[\s\S]*\}[\s\S]*\.check-form\s*\{[\s\S]*grid-template-columns:\s*minmax\(220px, 0\.92fr\) minmax\(0, 1\.08fr\);[\s\S]*grid-template-areas:[\s\S]*"history auth"[\s\S]*"location submit";[\s\S]*align-items:\s*start;/
  );
  assert.match(
    checkCss,
    /@media \(orientation: landscape\) and \(max-height: 540px\)\s*\{[\s\S]*\.check-form > \*\s*\{[\s\S]*min-width:\s*0;[\s\S]*\}[\s\S]*\.check-form > #registrationField\s*\{[\s\S]*grid-area:\s*registration;/
  );
  assert.match(
    checkCss,
    /@media \(orientation: landscape\) and \(max-height: 540px\)\s*\{[\s\S]*\.password-dialog,[\s\S]*\.transport-screen\s*\{[\s\S]*align-items:\s*flex-start;[\s\S]*padding-top:\s*max\(10px, env\(safe-area-inset-top\)\);/
  );
});

test('desktop layout keeps the shell contained while reorganizing form and transport surfaces', () => {
  assert.match(
    checkCss,
    /@media \(min-width: 1024px\)\s*\{[\s\S]*\.transport-screen-card\s*\{[\s\S]*width:\s*min\(100%, 900px\);[\s\S]*min-height:\s*auto;[\s\S]*height:\s*auto;[\s\S]*gap:\s*14px;[\s\S]*\}[\s\S]*\.transport-option-buttons\s*\{[\s\S]*grid-template-columns:\s*repeat\(3, minmax\(0, 1fr\)\);/
  );
  assert.match(
    checkCss,
    /@media \(min-width: 1180px\)\s*\{[\s\S]*\.check-form\s*\{[\s\S]*grid-template-columns:\s*minmax\(300px, 0\.88fr\) minmax\(0, 1\.12fr\);[\s\S]*grid-template-areas:[\s\S]*"history auth"[\s\S]*"location submit";[\s\S]*align-items:\s*start;/
  );
  assert.match(
    checkCss,
    /@media \(min-width: 1180px\)\s*\{[\s\S]*\.check-field-compact\s*\{[\s\S]*flex:\s*0 0 148px;[\s\S]*width:\s*148px;[\s\S]*min-width:\s*148px;/
  );
  assert.match(
    checkCss,
    /@media \(min-width: 1180px\)\s*\{[\s\S]*\.transport-request-history-list\s*\{[\s\S]*grid-template-columns:\s*repeat\(3, minmax\(0, 1fr\)\);[\s\S]*align-content:\s*start;/
  );
  assert.match(
    checkCss,
    /@media \(min-width: 1180px\)\s*\{[\s\S]*\.transport-request-summary-card\s*\{[\s\S]*min-height:\s*132px;/
  );
});