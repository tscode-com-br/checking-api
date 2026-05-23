const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const adminJs = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/admin2/app.js'),
  'utf8'
);

test('admin locations require positive tolerance in the UI', () => {
  assert.match(adminJs, /function normalizeTolerance\(value\) \{[\s\S]*tolerance < 1 \|\| tolerance > 9999[\s\S]*inteiro entre 1 e 9999 metros\./);
  assert.match(adminJs, /class="inline location-tolerance" type="number" min="1" max="9999" inputmode="numeric"/);
});

test('admin location settings support keyboard save and clear stale pending status', () => {
  assert.match(adminJs, /const LOCATION_SETTINGS_PENDING_STATUS = "Alterações pendentes nas configurações de localização\. Clique em Salvar para registrar\.";/);
  assert.match(adminJs, /function renderLocationSettings\(\) \{[\s\S]*locationAccuracyThresholdMeters[\s\S]*locationSettingsDirty = false;/);
  assert.match(adminJs, /function haveLocationSettingsChanged\(\) \{[\s\S]*normalizeLocationAccuracyThreshold\(accuracyInput\.value\)/);
  assert.match(adminJs, /function handleLocationSettingsInputChange\(\) \{[\s\S]*setStatus\(LOCATION_SETTINGS_PENDING_STATUS, true\);[\s\S]*if \(statusLine\.textContent === LOCATION_SETTINGS_PENDING_STATUS\) \{[\s\S]*clearStatus\(\);[\s\S]*\}/);
  assert.match(adminJs, /function handleLocationSettingsInputKeydown\(event\) \{[\s\S]*event\.key === "Escape"[\s\S]*discardLocationSettingsDraft\(\);[\s\S]*event\.key !== "Enter"[\s\S]*refreshLocationSettingsDirtyState\(\);[\s\S]*if \(!locationSettingsDirty\) \{[\s\S]*return;[\s\S]*\}[\s\S]*saveLocationSettings\(\)\.catch\(\(error\) => setStatus\(error\.message, false\)\);[\s\S]*\}/);
  assert.match(adminJs, /const response = await postJson\("\/api\/admin\/locations\/settings", \{[\s\S]*location_accuracy_threshold_meters: Number\(normalizedAccuracy\),[\s\S]*\}\);/);
  assert.match(adminJs, /locationAccuracyThresholdMeters = response\.location_accuracy_threshold_meters;/);
  assert.match(adminJs, /locationAccuracyThresholdMeters = locationsResponse\.location_accuracy_threshold_meters;/);
  assert.match(adminJs, /input\.addEventListener\("keydown", handleLocationSettingsInputKeydown\);/);
  assert.match(adminJs, /bindLocationSettingsInput\("locationAccuracyThresholdMeters"\);/);
});