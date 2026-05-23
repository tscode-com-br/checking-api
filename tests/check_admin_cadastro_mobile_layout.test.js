const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const adminHtml = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/admin2/index.html'),
  'utf8'
);

const adminCss = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/admin2/styles.css'),
  'utf8'
);

const adminJs = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/admin2/app.js'),
  'utf8'
);

test('cadastro tab groups each maintenance surface into explicit subsection panels', () => {
  assert.match(adminHtml, /<section id="tab-cadastro" class="tab cadastro-tab">/);
  assert.match(adminHtml, /data-cadastro-section="pendencias"/);
  assert.match(adminHtml, /data-cadastro-section="acidentes"/);
  assert.match(adminHtml, /data-cadastro-section="localizacoes"/);
  assert.match(adminHtml, /data-cadastro-section="administradores"/);
  assert.match(adminHtml, /data-cadastro-section="projetos"/);
  assert.match(adminHtml, /data-cadastro-section="usuarios"/);
  assert.match(adminHtml, /data-cadastro-section="endpoints"/);
});

test('cadastro runtime converts top-level section titles into accessible collapse toggles', () => {
  assert.match(adminJs, /function setCadastroSectionCollapsed\(section, toggle, content, collapsed\) \{[\s\S]*section\.dataset\.cadastroCollapsed = collapsed \? "true" : "false";[\s\S]*toggle\.setAttribute\("aria-expanded", collapsed \? "false" : "true"\);[\s\S]*content\.hidden = collapsed;[\s\S]*content\.classList\.toggle\("hidden", collapsed\);[\s\S]*\}/);
  assert.match(adminJs, /function initializeCadastroSection\(section, index\) \{[\s\S]*toggle\.className = "cadastro-section-toggle";[\s\S]*toggle\.dataset\.cadastroToggle = sectionKey;[\s\S]*child\.setAttribute\("data-cadastro-header-action", ""\);[\s\S]*content\.className = "cadastro-section-content";[\s\S]*content\.dataset\.cadastroContent = sectionKey;[\s\S]*toggle\.setAttribute\("aria-controls", content\.id\);[\s\S]*setCadastroSectionCollapsed\(section, toggle, content, true\);[\s\S]*\}/);
  assert.match(adminJs, /function setupCadastroSectionPanels\(\) \{[\s\S]*document\.getElementById\("tab-cadastro"\)[\s\S]*initializeCadastroSection\(section, index\)[\s\S]*\}/);
  assert.match(adminJs, /function bindActions\(\) \{[\s\S]*setupCadastroSectionPanels\(\);/);
});

test('cadastro mobile layout replaces the generic compressed table stack with padded section cards', () => {
  assert.match(adminCss, /\.cadastro-tab \{[\s\S]*gap: 18px;/);
  assert.match(adminCss, /\.cadastro-tab\.active \{[\s\S]*display: grid;/);
  assert.match(adminCss, /\.cadastro-section-panel \{[\s\S]*display: grid;[\s\S]*gap: 14px;/);
  assert.match(adminCss, /\.cadastro-section-toggle \{[\s\S]*display: inline-flex;[\s\S]*justify-content: space-between;[\s\S]*width: 100%;[\s\S]*background: transparent;[\s\S]*font-weight: 700;/);
  assert.match(adminCss, /\.cadastro-section-content \{[\s\S]*display: grid;[\s\S]*gap: 12px;/);
  assert.match(adminCss, /\.cadastro-section-panel\[data-cadastro-collapsed="true"\] \[data-cadastro-header-action\] \{[\s\S]*display: none;/);
  assert.match(adminCss, /@media \(max-width: 800px\) \{[\s\S]*\.cadastro-section-panel \{[\s\S]*padding: 14px;[\s\S]*border-radius: 16px;[\s\S]*background: linear-gradient\(180deg, #ffffff 0%, #f8fafc 100%\);/);
  assert.match(adminCss, /@media \(max-width: 800px\) \{[\s\S]*\.cadastro-section-panel \.project-editor-panel \{[\s\S]*padding: 0;[\s\S]*border: 0;[\s\S]*background: transparent;[\s\S]*box-shadow: none;/);
});

test('cadastro mobile tables show labels above content and expand maintenance actions to full width', () => {
  assert.match(adminCss, /@media \(max-width: 800px\) \{[\s\S]*\.cadastro-table td \{[\s\S]*display: grid;[\s\S]*gap: 6px;[\s\S]*padding: 12px;[\s\S]*text-align: left;/);
  assert.match(adminCss, /@media \(max-width: 800px\) \{[\s\S]*\.cadastro-table td::before \{[\s\S]*position: static;[\s\S]*display: block;[\s\S]*text-transform: uppercase;/);
  assert.match(adminCss, /@media \(max-width: 800px\) \{[\s\S]*\.cadastro-table \.pending-actions \{[\s\S]*display: grid;[\s\S]*grid-template-columns: 1fr;[\s\S]*width: 100%;/);
  assert.match(adminCss, /@media \(max-width: 800px\) \{[\s\S]*\.cadastro-table \.pending-actions button,[\s\S]*\.cadastro-users-table \.user-actions button,[\s\S]*\.location-actions button,[\s\S]*\.project-editor-actions button,[\s\S]*\.locations-settings-actions button \{[\s\S]*width: 100%;[\s\S]*min-height: 44px;/);
  assert.match(adminCss, /@media \(max-width: 800px\) \{[\s\S]*\.cadastro-users-table \.user-actions \{[\s\S]*grid-template-columns: 1fr;/);
  assert.match(adminCss, /@media \(max-width: 800px\) \{[\s\S]*\.membership-projects-button \{[\s\S]*width: 100%;/);
  assert.match(adminCss, /@media \(max-width: 800px\) \{[\s\S]*\.membership-projects-panel \{[\s\S]*max-height: none;/);
  assert.match(adminCss, /@media \(max-width: 800px\) \{[\s\S]*\.membership-projects-panel-footer \{[\s\S]*display: grid;[\s\S]*grid-template-columns: 1fr;/);
  assert.match(adminCss, /@media \(max-width: 800px\) \{[\s\S]*\.membership-projects-panel-footer button \{[\s\S]*width: 100%;[\s\S]*min-height: 44px;/);
  assert.match(adminCss, /@media \(max-width: 800px\) \{[\s\S]*\.admin-projects-panel \{[\s\S]*grid-template-columns: 1fr;[\s\S]*max-height: none;/);
  assert.match(adminCss, /@media \(max-width: 800px\) \{[\s\S]*\.location-projects-panel \{[\s\S]*max-height: none;/);
});