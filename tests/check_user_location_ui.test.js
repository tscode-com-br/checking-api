const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const checkHtml = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/check/index.html'),
  'utf8'
);

const checkScript = fs.readFileSync(
  path.join(__dirname, '../sistema/app/static/check/app.js'),
  'utf8'
);

const checkAutomaticActivities = require('../sistema/app/static/check/automatic-activities.js');

function extractObjectFreezeConstant(sourceText, constantName) {
  const pattern = new RegExp(`const ${constantName} = Object\\.freeze\\((\\{[\\s\\S]*?\\})\\);`);
  const match = sourceText.match(pattern);
  assert.ok(match, `Expected ${constantName} to be declared in app.js`);
  return `const ${constantName} = Object.freeze(${match[1]});`;
}

function extractConstSource(sourceText, constantName) {
  const startToken = `const ${constantName} = `;
  const startIndex = sourceText.indexOf(startToken);
  assert.notEqual(startIndex, -1, `Expected ${constantName} to be declared in app.js`);

  let index = startIndex + startToken.length;
  let parenDepth = 0;
  let braceDepth = 0;
  let bracketDepth = 0;
  let quote = null;
  let inLineComment = false;
  let inBlockComment = false;
  let escapeNext = false;

  for (; index < sourceText.length; index += 1) {
    const char = sourceText[index];
    const nextChar = sourceText[index + 1];

    if (inLineComment) {
      if (char === '\n') {
        inLineComment = false;
      }
      continue;
    }

    if (inBlockComment) {
      if (char === '*' && nextChar === '/') {
        inBlockComment = false;
        index += 1;
      }
      continue;
    }

    if (quote) {
      if (escapeNext) {
        escapeNext = false;
        continue;
      }
      if (char === '\\') {
        escapeNext = true;
        continue;
      }
      if (char === quote) {
        quote = null;
      }
      continue;
    }

    if (char === '/' && nextChar === '/') {
      inLineComment = true;
      index += 1;
      continue;
    }
    if (char === '/' && nextChar === '*') {
      inBlockComment = true;
      index += 1;
      continue;
    }

    if (char === '\'' || char === '"' || char === '`') {
      quote = char;
      continue;
    }

    if (char === '(') {
      parenDepth += 1;
      continue;
    }
    if (char === ')') {
      parenDepth -= 1;
      continue;
    }
    if (char === '{') {
      braceDepth += 1;
      continue;
    }
    if (char === '}') {
      braceDepth -= 1;
      continue;
    }
    if (char === '[') {
      bracketDepth += 1;
      continue;
    }
    if (char === ']') {
      bracketDepth -= 1;
      continue;
    }

    if (char === ';' && parenDepth === 0 && braceDepth === 0 && bracketDepth === 0) {
      return sourceText.slice(startIndex, index + 1);
    }
  }

  throw new Error(`Could not extract ${constantName} from app.js`);
}

function findMatchingBrace(sourceText, openBraceIndex) {
  let index = openBraceIndex + 1;
  let depth = 1;
  let quote = null;
  let inLineComment = false;
  let inBlockComment = false;
  let escapeNext = false;

  for (; index < sourceText.length; index += 1) {
    const char = sourceText[index];
    const nextChar = sourceText[index + 1];

    if (inLineComment) {
      if (char === '\n') {
        inLineComment = false;
      }
      continue;
    }

    if (inBlockComment) {
      if (char === '*' && nextChar === '/') {
        inBlockComment = false;
        index += 1;
      }
      continue;
    }

    if (quote) {
      if (escapeNext) {
        escapeNext = false;
        continue;
      }
      if (char === '\\') {
        escapeNext = true;
        continue;
      }
      if (char === quote) {
        quote = null;
      }
      continue;
    }

    if (char === '/' && nextChar === '/') {
      inLineComment = true;
      index += 1;
      continue;
    }
    if (char === '/' && nextChar === '*') {
      inBlockComment = true;
      index += 1;
      continue;
    }

    if (char === '\'' || char === '"' || char === '`') {
      quote = char;
      continue;
    }

    if (char === '{') {
      depth += 1;
      continue;
    }

    if (char === '}') {
      depth -= 1;
      if (depth === 0) {
        return index;
      }
    }
  }

  throw new Error('Could not find the matching closing brace in app.js');
}

function extractFunctionSource(sourceText, functionName) {
  const functionToken = `function ${functionName}(`;
  const startIndex = sourceText.indexOf(functionToken);
  assert.notEqual(startIndex, -1, `Expected ${functionName} to be declared in app.js`);

  const openBraceIndex = sourceText.indexOf('{', startIndex);
  assert.notEqual(openBraceIndex, -1, `Expected ${functionName} to contain a block body`);

  const closeBraceIndex = findMatchingBrace(sourceText, openBraceIndex);
  return sourceText.slice(startIndex, closeBraceIndex + 1);
}

function createLocationHelperHarness(overrides = {}) {
  const context = {
    Object,
    Math,
    Number,
    Date: overrides.Date || Date,
    Promise,
    Error,
    JSON,
    navigator: overrides.navigator || { geolocation: {} },
    window: overrides.window || {
      setTimeout,
      clearTimeout,
    },
    setLocationPresentation: overrides.setLocationPresentation || (() => {}),
    recordLocationMeasurementEvent: overrides.recordLocationMeasurementEvent || (() => {}),
    recordLocationMeasurementSample: overrides.recordLocationMeasurementSample || (() => {}),
    requestCurrentPosition: overrides.requestCurrentPosition || (() => Promise.resolve(null)),
  };

  const moduleSource = [
    'let locationAccuracyThresholdMeters = null;',
    extractConstSource(checkScript, 'geolocationOptions'),
    extractObjectFreezeConstant(checkScript, 'lifecycleLocationCapturePlan'),
    extractObjectFreezeConstant(checkScript, 'enforcedLocationCapturePlan'),
    extractObjectFreezeConstant(checkScript, 'locationCapturePlansByTrigger'),
    extractFunctionSource(checkScript, 'hasFiniteCoordinate'),
    extractFunctionSource(checkScript, 'readPositionAccuracyMeters'),
    extractFunctionSource(checkScript, 'isLocationSampleBetter'),
    extractFunctionSource(checkScript, 'getLocationMeasurementTrigger'),
    extractFunctionSource(checkScript, 'buildLocationCapturePlan'),
    extractFunctionSource(checkScript, 'shouldStopLocationWatch'),
    extractFunctionSource(checkScript, 'buildWatchGeolocationOptions'),
    extractFunctionSource(checkScript, 'buildLocationWatchTimeoutError'),
    extractFunctionSource(checkScript, 'formatMeters'),
    extractFunctionSource(checkScript, 'buildAccuracyText'),
    extractFunctionSource(checkScript, 'buildLocationCaptureProgressAccuracyText'),
    extractFunctionSource(checkScript, 'updateLocationCaptureProgress'),
    extractFunctionSource(checkScript, 'requestWatchedCurrentPosition'),
    extractFunctionSource(checkScript, 'requestCurrentPositionForPlan'),
    `globalThis.__locationTestExports = {
      geolocationOptions,
      lifecycleLocationCapturePlan,
      enforcedLocationCapturePlan,
      locationCapturePlansByTrigger,
      setLocationAccuracyThresholdMeters(value) {
        locationAccuracyThresholdMeters = value;
      },
      buildLocationCapturePlan,
      shouldStopLocationWatch,
      buildWatchGeolocationOptions,
      buildAccuracyText,
      buildLocationCaptureProgressAccuracyText,
      updateLocationCaptureProgress,
      requestWatchedCurrentPosition,
      requestCurrentPositionForPlan,
    };`,
  ].join('\n\n');

  vm.runInNewContext(moduleSource, context, { filename: 'check-location-helpers.vm.js' });
  return {
    helpers: context.__locationTestExports,
    context,
  };
}

function createManualLocationFallbackHarness() {
  const context = {
    Boolean,
    syncProjectVisibility: () => {},
  };

  const moduleSource = [
    'let gpsLocationPermissionGranted = false;',
    'let currentLocationMatch = null;',
    'let currentLocationResolutionStatus = null;',
    extractFunctionSource(checkScript, 'isAccuracyTooLowManualFallbackActive'),
    extractFunctionSource(checkScript, 'shouldAllowManualLocationSelection'),
    extractFunctionSource(checkScript, 'setResolvedLocation'),
    `globalThis.__manualLocationFallbackTestExports = {
      isAccuracyTooLowManualFallbackActive,
      shouldAllowManualLocationSelection,
      setGpsLocationPermissionGranted(value) {
        gpsLocationPermissionGranted = Boolean(value);
      },
      setResolvedLocation,
      getState() {
        return {
          gpsLocationPermissionGranted,
          currentLocationMatch,
          currentLocationResolutionStatus,
        };
      },
    };`,
  ].join('\n\n');

  vm.runInNewContext(moduleSource, context, { filename: 'check-manual-location-fallback.vm.js' });
  return {
    helpers: context.__manualLocationFallbackTestExports,
    context,
  };
}

function createManualOverrideUiHarness() {
  function createElement() {
    const classes = new Set();
    return {
      disabled: false,
      textContent: '',
      value: '',
      attributes: {},
      classList: {
        toggle(name, force) {
          const shouldAdd = force === undefined ? !classes.has(name) : Boolean(force);
          if (shouldAdd) {
            classes.add(name);
            return;
          }
          classes.delete(name);
        },
        contains(name) {
          return classes.has(name);
        },
      },
      setAttribute(name, value) {
        this.attributes[name] = String(value);
      },
      getAttribute(name) {
        return this.attributes[name];
      },
    };
  }

  const context = {
    Array,
    Boolean,
    Object,
    __createElement: createElement,
    __selectedValues: [],
    isUserInteractionLocked: () => false,
    syncAuthenticationFieldHighlights: () => {},
    isPasswordActionBusy: () => false,
    isAnyDialogOpen: () => false,
    isApplicationUnlocked: () => true,
    resolvePasswordActionButtonLabel: () => 'Senha',
    isPasswordActionAssistanceModeActive: () => false,
    getActiveChave: () => 'AB12',
    isMissingUserRegistrationState: () => false,
    isMissingPasswordRegistrationState: () => false,
    canSubmitPasswordDialog: () => false,
    isPasswordRegistrationDialogMode: () => false,
    setSelectedValue(name, value) {
      context.__selectedValues.push({ name, value });
    },
  };

  const moduleSource = [
    'let gpsLocationPermissionGranted = false;',
    'let currentLocationResolutionStatus = null;',
    'let transportStateLoading = false;',
    'let transportAddressSaveInProgress = false;',
    'let transportRequestInProgress = false;',
    'let transportCancelInProgress = false;',
    'let submitInProgress = false;',
    'let passwordRegisterInProgress = false;',
    'let passwordChangeInProgress = false;',
    'let userSelfRegistrationInProgress = false;',
    'let projectCatalogLoading = false;',
    'let projectUpdateInProgress = false;',
    'let locationRefreshLoading = false;',
    'let passwordLoginInProgress = false;',
    'let availableLocations = ["Portaria"];',
    'let allowedProjectValues = ["Projeto A"];',
    'const automaticActivitiesToggle = { checked: false };',
    'const projectSelect = globalThis.__createElement();',
    'const manualLocationSelect = globalThis.__createElement();',
    'const refreshLocationButton = globalThis.__createElement();',
    'const submitButton = globalThis.__createElement();',
    'const projectField = globalThis.__createElement();',
    'const locationSelectField = globalThis.__createElement();',
    'const informeField = globalThis.__createElement();',
    'const form = globalThis.__createElement();',
    'const actionInputs = [globalThis.__createElement(), globalThis.__createElement()];',
    'const processControls = [actionInputs[0], actionInputs[1], manualLocationSelect, refreshLocationButton, submitButton];',
    'const authControls = [];',
    'const passwordDialogControls = [];',
    'const registrationDialogControls = [];',
    'const transportScreenControls = [];',
    'const transportUiState = {};',
    'const transportButton = null;',
    'const transportScreen = null;',
    'const passwordDialog = null;',
    'const registrationDialog = null;',
    extractConstSource(checkScript, 'defaultManualLocationLabel'),
    extractConstSource(checkScript, 'accuracyFallbackManualLocationLabel'),
    extractFunctionSource(checkScript, 'isAccuracyTooLowManualFallbackActive'),
    extractFunctionSource(checkScript, 'shouldAllowManualLocationSelection'),
    extractFunctionSource(checkScript, 'resolveManualLocationOptions'),
    extractFunctionSource(checkScript, 'isAutomaticActivitiesEnabled'),
    extractFunctionSource(checkScript, 'syncFormControlStates'),
    extractFunctionSource(checkScript, 'syncProjectVisibility'),
    `globalThis.__manualOverrideUiTestExports = {
      syncFormControlStates,
      syncProjectVisibility,
      setAutomaticActivitiesEnabled(value) {
        automaticActivitiesToggle.checked = Boolean(value);
      },
      setGpsLocationPermissionGranted(value) {
        gpsLocationPermissionGranted = Boolean(value);
      },
      setCurrentLocationResolutionStatus(value) {
        currentLocationResolutionStatus = value;
      },
      setAvailableLocations(values) {
        availableLocations = Array.from(values || []);
      },
      getSnapshot() {
        return {
          projectHidden: projectField.classList.contains('is-hidden'),
          locationHidden: locationSelectField.classList.contains('is-hidden'),
          informeHidden: informeField.classList.contains('is-hidden'),
          projectDisabled: projectSelect.disabled,
          manualLocationDisabled: manualLocationSelect.disabled,
          actionDisabled: actionInputs.map((control) => control.disabled),
          submitDisabled: submitButton.disabled,
          selectedValues: globalThis.__selectedValues.slice(),
        };
      },
    };`,
  ].join('\n\n');

  vm.runInNewContext(moduleSource, context, { filename: 'check-manual-override-ui.vm.js' });
  return {
    helpers: context.__manualOverrideUiTestExports,
    context,
  };
}

function createManualLocationSelectHarness() {
  function createSelectElement() {
    return {
      value: '',
      options: [],
      replaceChildren() {
        this.options = [];
      },
      append(option) {
        this.options.push({
          value: option.value,
          textContent: option.textContent,
        });
      },
    };
  }

  const context = {
    Array,
    Boolean,
    Object,
    __createSelectElement: createSelectElement,
    document: {
      createElement() {
        return {
          value: '',
          textContent: '',
        };
      },
    },
    syncFormControlStates: () => {},
  };

  const moduleSource = [
    'let gpsLocationPermissionGranted = false;',
    'let currentLocationResolutionStatus = null;',
    'let availableLocations = [];',
    'const manualLocationSelect = globalThis.__createSelectElement();',
    'const locationValue = { textContent: "" };',
    extractConstSource(checkScript, 'defaultManualLocationLabel'),
    extractConstSource(checkScript, 'accuracyFallbackManualLocationLabel'),
    extractFunctionSource(checkScript, 'isAccuracyTooLowManualFallbackActive'),
    extractFunctionSource(checkScript, 'shouldAllowManualLocationSelection'),
    extractFunctionSource(checkScript, 'resolveManualLocationOptions'),
    extractFunctionSource(checkScript, 'resolveManualLocationDefaultForCurrentProject'),
    extractFunctionSource(checkScript, 'getDefaultManualLocation'),
    extractFunctionSource(checkScript, 'setLocationSelectOptions'),
    extractFunctionSource(checkScript, 'syncManualLocationControl'),
    `globalThis.__manualLocationSelectTestExports = {
      syncManualLocationControl,
      resolveManualLocationOptions,
      resolveManualLocationDefaultForCurrentProject,
      setGpsLocationPermissionGranted(value) {
        gpsLocationPermissionGranted = Boolean(value);
      },
      setCurrentLocationResolutionStatus(value) {
        currentLocationResolutionStatus = value;
      },
      setAvailableLocations(values) {
        availableLocations = Array.from(values || []);
      },
      setDisplayedLocation(value) {
        locationValue.textContent = String(value || '');
      },
      setManualLocationValue(value) {
        manualLocationSelect.value = String(value || '');
      },
      getSnapshot() {
        return {
          options: manualLocationSelect.options.map((option) => option.value),
          selectedValue: manualLocationSelect.value,
          resolvedDefault: resolveManualLocationDefaultForCurrentProject(),
        };
      },
    };`,
  ].join('\n\n');

  vm.runInNewContext(moduleSource, context, { filename: 'check-manual-location-select.vm.js' });
  return {
    helpers: context.__manualLocationSelectTestExports,
    context,
  };
}

function createSubmittedLocationHarness() {
  const context = {
    Boolean,
  };

  const moduleSource = [
    'let gpsLocationPermissionGranted = false;',
    'let currentLocationResolutionStatus = null;',
    'let currentLocationMatch = null;',
    'const manualLocationSelect = { value: "" };',
    extractFunctionSource(checkScript, 'isAccuracyTooLowManualFallbackActive'),
    extractFunctionSource(checkScript, 'shouldAllowManualLocationSelection'),
    extractFunctionSource(checkScript, 'resolveSubmittedLocationValue'),
    `globalThis.__submittedLocationTestExports = {
      resolveSubmittedLocationValue,
      setGpsLocationPermissionGranted(value) {
        gpsLocationPermissionGranted = Boolean(value);
      },
      setCurrentLocationResolutionStatus(value) {
        currentLocationResolutionStatus = value;
      },
      setCurrentLocationMatch(value) {
        currentLocationMatch = value;
      },
      setManualLocationValue(value) {
        manualLocationSelect.value = String(value || '');
      },
    };`,
  ].join('\n\n');

  vm.runInNewContext(moduleSource, context, { filename: 'check-submitted-location.vm.js' });
  return {
    helpers: context.__submittedLocationTestExports,
    context,
  };
}

function createProjectSelectionHarness() {
  const context = {
    Boolean,
    Promise,
    Error,
    JSON,
    __calls: {
      fetches: [],
      loadManualLocations: 0,
      persistCurrentUserSettings: 0,
      syncFormControlStates: 0,
      syncProjectSelectOptions: [],
      statuses: [],
    },
    fetch: async (url, options) => {
      context.__calls.fetches.push({
        url,
        body: JSON.parse(options.body),
      });
      return {
        ok: true,
        json: async () => ({
          project: JSON.parse(options.body).projeto,
          message: 'Projeto atualizado com sucesso.',
        }),
      };
    },
    getActiveChave: () => 'AB12',
    normalizeKnownProjectValue: (value, fallback) => String(value || fallback || ''),
    syncProjectSelectOptions: (settings) => {
      context.__calls.syncProjectSelectOptions.push(settings);
    },
    isApplicationUnlocked: () => true,
    persistCurrentUserSettings: () => {
      context.__calls.persistCurrentUserSettings += 1;
    },
    syncFormControlStates: () => {
      context.__calls.syncFormControlStates += 1;
    },
    buildProtectedRequestError: () => new Error('request failed'),
    loadManualLocations: async () => {
      context.__calls.loadManualLocations += 1;
    },
    setStatus: (message, tone) => {
      context.__calls.statuses.push({ message, tone });
    },
  };

  const moduleSource = [
    'let gpsLocationPermissionGranted = false;',
    'let currentLocationResolutionStatus = null;',
    'let projectUpdateInProgress = false;',
    'let lastCommittedProjectValue = "Projeto A";',
    'let latestHistoryState = { projeto: "Projeto A" };',
    'const defaultProjectValue = "Projeto A";',
    'const projectUpdateEndpoint = "/api/web/project";',
    'const projectSelect = { value: "Projeto B" };',
    'const automaticActivitiesToggle = { checked: false };',
    extractFunctionSource(checkScript, 'isAccuracyTooLowManualFallbackActive'),
    extractFunctionSource(checkScript, 'isAutomaticActivitiesEnabled'),
    `async ${extractFunctionSource(checkScript, 'updateCurrentUserProjectSelection')}`,
    `globalThis.__projectSelectionTestExports = {
      async updateCurrentUserProjectSelection() {
        return updateCurrentUserProjectSelection();
      },
      setAutomaticActivitiesEnabled(value) {
        automaticActivitiesToggle.checked = Boolean(value);
      },
      setGpsLocationPermissionGranted(value) {
        gpsLocationPermissionGranted = Boolean(value);
      },
      setCurrentLocationResolutionStatus(value) {
        currentLocationResolutionStatus = value;
      },
      setProjectValue(value) {
        projectSelect.value = String(value || '');
      },
      getSnapshot() {
        return {
          fetches: globalThis.__calls.fetches.slice(),
          loadManualLocations: globalThis.__calls.loadManualLocations,
          persistCurrentUserSettings: globalThis.__calls.persistCurrentUserSettings,
          syncFormControlStates: globalThis.__calls.syncFormControlStates,
          syncProjectSelectOptions: globalThis.__calls.syncProjectSelectOptions.slice(),
          statuses: globalThis.__calls.statuses.slice(),
          lastCommittedProjectValue,
          latestHistoryProject: latestHistoryState ? latestHistoryState.projeto : null,
          projectUpdateInProgress,
        };
      },
    };`,
  ].join('\n\n');

  vm.runInNewContext(moduleSource, context, { filename: 'check-project-selection.vm.js' });
  return {
    helpers: context.__projectSelectionTestExports,
    context,
  };
}

function createLocationCatalogSettingsHarness() {
  const context = {
    Array,
    Number,
    Math,
    Promise,
    Set,
    JSON,
    __calls: {
      fetch: [],
      syncManualLocationControl: 0,
    },
    __applicationUnlocked: true,
    __payload: {
      items: [],
      location_accuracy_threshold_meters: 30,
      mixed_zone_interval_minutes: 20,
    },
    __fetchFailure: false,
    isApplicationUnlocked: () => context.__applicationUnlocked,
    fetch: async (url, options) => {
      context.__calls.fetch.push({ url, options });
      if (context.__fetchFailure) {
        throw new Error('network failure');
      }
      return {
        ok: true,
        json: async () => context.__payload,
      };
    },
    buildProtectedRequestError: () => new Error('request failed'),
    syncManualLocationControl: () => {
      context.__calls.syncManualLocationControl += 1;
    },
  };

  const moduleSource = [
    'let availableLocations = [];',
    'let locationAccuracyThresholdMeters = null;',
    'let mixedZoneIntervalMinutes = null;',
    'const locationsEndpoint = "/api/web/check/locations";',
    extractConstSource(checkScript, 'DEFAULT_MIXED_ZONE_INTERVAL_MINUTES'),
    extractFunctionSource(checkScript, 'setLocationAccuracyThresholdMeters'),
    extractFunctionSource(checkScript, 'setMixedZoneIntervalMinutes'),
    `async ${extractFunctionSource(checkScript, 'loadManualLocations')}`,
    `globalThis.__locationCatalogSettingsTestExports = {
      async loadManualLocations() {
        return loadManualLocations();
      },
      setApplicationUnlocked(value) {
        globalThis.__applicationUnlocked = Boolean(value);
      },
      setPayload(value) {
        globalThis.__payload = value;
      },
      setFetchFailure(value) {
        globalThis.__fetchFailure = Boolean(value);
      },
      getSnapshot() {
        return {
          availableLocations: availableLocations.slice(),
          locationAccuracyThresholdMeters,
          mixedZoneIntervalMinutes,
          fetchCalls: globalThis.__calls.fetch.slice(),
          syncManualLocationControl: globalThis.__calls.syncManualLocationControl,
        };
      },
    };`,
  ].join('\n\n');

  vm.runInNewContext(moduleSource, context, { filename: 'check-location-catalog-settings.vm.js' });
  return {
    helpers: context.__locationCatalogSettingsTestExports,
    context,
  };
}

function createAuthenticatedApplicationHarness() {
  const context = {
    Promise,
    Boolean,
    String,
    __calls: [],
    chaveInput: { value: '' },
    sanitizeChave: (value) => String(value || '').trim().toUpperCase(),
    isApplicationUnlocked: () => true,
    loadProjectCatalog: async (options) => {
      context.__calls.push({ step: 'loadProjectCatalog', options });
    },
    restorePersistedUserSettingsForChave: (chave) => {
      context.__calls.push({ step: 'restorePersistedUserSettingsForChave', chave });
    },
    loadManualLocations: async () => {
      context.__calls.push({ step: 'loadManualLocations' });
    },
    setStatus: (message, tone) => {
      context.__calls.push({ step: 'setStatus', message, tone });
    },
    runLifecycleUpdateSequence: async (options) => {
      context.__calls.push({ step: 'runLifecycleUpdateSequence', options });
      return true;
    },
  };

  const moduleSource = [
    'let authenticatedApplicationLoadPromise = null;',
    'let authenticatedApplicationLoadFingerprint = "";',
    'let authenticatedApplicationReadyFingerprint = "";',
    'let lastVerifiedPassword = "persisted-secret";',
    'const passwordInput = { value: "persisted-secret" };',
    extractFunctionSource(checkScript, 'buildPasswordVerificationFingerprint'),
    `async ${extractFunctionSource(checkScript, 'loadAuthenticatedApplication')}`,
    `globalThis.__authenticatedApplicationTestExports = {
      async loadAuthenticatedApplication(chave, options) {
        return loadAuthenticatedApplication(chave, options);
      },
      getSnapshot() {
        return globalThis.__calls.slice();
      },
    };`,
  ].join('\n\n');

  vm.runInNewContext(moduleSource, context, { filename: 'check-authenticated-application.vm.js' });
  return {
    helpers: context.__authenticatedApplicationTestExports,
    context,
  };
}

function createPasswordInputAuthenticationHarness() {
  const context = {
    Boolean,
    Promise,
    String,
    __calls: {
      applyAuthenticationLockedState: [],
      logoutWebSession: [],
      schedulePasswordVerification: [],
      clearPasswordVerificationTimer: 0,
      setAuthenticationPrompt: [],
    },
    __authState: {
      found: true,
      hasPassword: true,
      authenticated: false,
      passwordVerified: false,
      statusResolved: true,
    },
    __chaveInput: { value: 'AB12' },
    __passwordInput: { value: '' },
    getActiveChave: () => 'AB12',
    isApplicationUnlocked: () => false,
    applyAuthenticationLockedState: (options) => {
      context.__calls.applyAuthenticationLockedState.push(options);
    },
    logoutWebSession: (options) => {
      context.__calls.logoutWebSession.push(options);
      return Promise.resolve();
    },
    schedulePasswordVerification: (options) => {
      context.__calls.schedulePasswordVerification.push(options);
    },
    clearPasswordVerificationTimer: () => {
      context.__calls.clearPasswordVerificationTimer += 1;
    },
    setAuthenticationPrompt: (message) => {
      context.__calls.setAuthenticationPrompt.push(message);
    },
    syncFormControlStates: () => {},
    clientState: {
      isPasswordLengthValid(password) {
        const rawPassword = String(password ?? '');
        return rawPassword.length >= 3 && rawPassword.length <= 10 && rawPassword.trim().length > 0;
      },
    },
  };

  const moduleSource = [
    'const authState = globalThis.__authState;',
    'const chaveInput = globalThis.__chaveInput;',
    'const passwordInput = globalThis.__passwordInput;',
    'let lastObservedPasswordFieldValue = "";',
    'let lastVerifiedPassword = "";',
    extractFunctionSource(checkScript, 'syncPasswordInputState'),
    `globalThis.__passwordInputAuthenticationTestExports = {
      syncPasswordInputState(options) {
        return syncPasswordInputState(options);
      },
      setPasswordValue(value) {
        passwordInput.value = value;
      },
      resetCalls() {
        globalThis.__calls.applyAuthenticationLockedState = [];
        globalThis.__calls.logoutWebSession = [];
        globalThis.__calls.schedulePasswordVerification = [];
        globalThis.__calls.clearPasswordVerificationTimer = 0;
        globalThis.__calls.setAuthenticationPrompt = [];
      },
      getSnapshot() {
        return {
          schedulePasswordVerification: globalThis.__calls.schedulePasswordVerification.slice(),
          clearPasswordVerificationTimer: globalThis.__calls.clearPasswordVerificationTimer,
          setAuthenticationPrompt: globalThis.__calls.setAuthenticationPrompt.slice(),
        };
      },
    };`,
  ].join('\n\n');

  vm.runInNewContext(moduleSource, context, { filename: 'check-password-input-authentication.vm.js' });
  return {
    helpers: context.__passwordInputAuthenticationTestExports,
    context,
  };
}

function createAuthenticationStatusHarness() {
  const context = {
    AbortController,
    Promise,
    Boolean,
    String,
    __fetchPayload: { found: true, has_password: true },
    __persistedPasswordMap: {},
    __calls: {
      applyAuthenticationStatusPayload: [],
      schedulePasswordVerification: [],
      schedulePasswordAutofillSync: 0,
      persistPasswordForChave: [],
      clearTypedPasswordAuthentication: 0,
      applyAuthenticationLockedState: [],
    },
    __authState: {
      chave: '',
      found: false,
      hasPassword: false,
      authenticated: false,
      passwordVerified: false,
      statusResolved: false,
      statusLoading: false,
      statusErrored: false,
    },
    __passwordInput: { value: '' },
    sanitizeChave: (value) => String(value || '').trim().toUpperCase(),
    fetchAuthenticationStatus: async () => context.__fetchPayload,
    applyAuthenticationStatusPayload: (payload) => {
      context.__calls.applyAuthenticationStatusPayload.push(payload);
      context.__authState.hasPassword = Boolean(payload && payload.has_password);
    },
    schedulePasswordVerification: (options) => {
      context.__calls.schedulePasswordVerification.push(options);
    },
    schedulePasswordAutofillSync: () => {
      context.__calls.schedulePasswordAutofillSync += 1;
    },
    persistPasswordForChave: (chave, password) => {
      context.__calls.persistPasswordForChave.push({ chave, password });
    },
    clearTypedPasswordAuthentication: () => {
      context.__calls.clearTypedPasswordAuthentication += 1;
      context.__authState.authenticated = false;
      context.__authState.passwordVerified = false;
    },
    syncFormControlStates: () => {},
    clearProtectedClientState: () => {},
    setAuthenticationPrompt: () => {},
    applyAuthenticationLockedState: (options) => {
      context.__calls.applyAuthenticationLockedState.push(options);
    },
    clientState: {
      isPasswordLengthValid(password) {
        const rawPassword = String(password ?? '');
        return rawPassword.length >= 3 && rawPassword.length <= 10 && rawPassword.trim().length > 0;
      },
      resolvePersistedPassword(passwordMap, chave) {
        const normalizedChave = String(chave || '').trim().toUpperCase();
        return passwordMap[normalizedChave] || '';
      },
    },
    readPersistedUserPasswordMap: () => context.__persistedPasswordMap,
  };

  const moduleSource = [
    'let authStatusRequestToken = 0;',
    'let authStatusAbortController = null;',
    'const authState = globalThis.__authState;',
    'const passwordInput = globalThis.__passwordInput;',
    extractFunctionSource(checkScript, 'resolvePersistedPasswordForChave'),
    `async ${extractFunctionSource(checkScript, 'refreshAuthenticationStatus')}`,
    `globalThis.__authenticationStatusTestExports = {
      async refreshAuthenticationStatus(chave, options) {
        return refreshAuthenticationStatus(chave, options);
      },
      setPasswordValue(value) {
        passwordInput.value = value;
      },
      setPersistedPasswordMap(value) {
        globalThis.__persistedPasswordMap = value;
      },
      setFetchPayload(value) {
        globalThis.__fetchPayload = value;
      },
      resetCalls() {
        globalThis.__calls.applyAuthenticationStatusPayload = [];
        globalThis.__calls.schedulePasswordVerification = [];
        globalThis.__calls.schedulePasswordAutofillSync = 0;
        globalThis.__calls.persistPasswordForChave = [];
        globalThis.__calls.clearTypedPasswordAuthentication = 0;
        globalThis.__calls.applyAuthenticationLockedState = [];
      },
      getSnapshot() {
        return {
          schedulePasswordVerification: globalThis.__calls.schedulePasswordVerification.slice(),
          schedulePasswordAutofillSync: globalThis.__calls.schedulePasswordAutofillSync,
          clearTypedPasswordAuthentication: globalThis.__calls.clearTypedPasswordAuthentication,
          applyAuthenticationLockedState: globalThis.__calls.applyAuthenticationLockedState.slice(),
        };
      },
    };`,
  ].join('\n\n');

  vm.runInNewContext(moduleSource, context, { filename: 'check-authentication-status.vm.js' });
  return {
    helpers: context.__authenticationStatusTestExports,
    context,
  };
}

function createAutomaticLocationDecisionHarness() {
  const context = {
    __calls: [],
    automaticActivities: {
      shouldAttemptAutomaticLocationEvent(locationPayload, remoteState, settings) {
        context.__calls.push({ locationPayload, remoteState, settings });
        return true;
      },
    },
  };

  const moduleSource = [
    'let mixedZoneIntervalMinutes = 35;',
    extractFunctionSource(checkScript, 'shouldAttemptAutomaticLocationEvent'),
    `globalThis.__automaticLocationDecisionTestExports = {
      shouldAttemptAutomaticLocationEvent(locationPayload, remoteState, options) {
        return shouldAttemptAutomaticLocationEvent(locationPayload, remoteState, options);
      },
      getSnapshot() {
        return globalThis.__calls.slice();
      },
    };`,
  ].join('\n\n');

  vm.runInNewContext(moduleSource, context, { filename: 'check-automatic-location-decision.vm.js' });
  return {
    helpers: context.__automaticLocationDecisionTestExports,
    context,
  };
}

function createManualRefreshSequenceHarness(overrides = {}) {
  const context = {
    Boolean,
    Promise,
    __calls: {
      runWithLockedUserInteraction: 0,
      resolveCurrentLocation: [],
      runAutomaticActivitiesIfNeeded: [],
    },
    __locationPayload: null,
    isUserInteractionLocked: overrides.isUserInteractionLocked || (() => false),
    isApplicationUnlocked: overrides.isApplicationUnlocked || (() => true),
    runWithLockedUserInteraction: overrides.runWithLockedUserInteraction || (async (callback) => {
      context.__calls.runWithLockedUserInteraction += 1;
      return callback();
    }),
    resolveCurrentLocation: overrides.resolveCurrentLocation || (async (options) => {
      context.__calls.resolveCurrentLocation.push(options);
      return context.__locationPayload;
    }),
    runAutomaticActivitiesIfNeeded: overrides.runAutomaticActivitiesIfNeeded || (async (locationPayload, options) => {
      context.__calls.runAutomaticActivitiesIfNeeded.push({ locationPayload, options });
      return { performed: false, action: null, local: null };
    }),
  };

  const moduleSource = [
    `async ${extractFunctionSource(checkScript, 'runManualLocationRefreshSequence')}`,
    `globalThis.__manualRefreshSequenceTestExports = {
      async runManualLocationRefreshSequence() {
        return runManualLocationRefreshSequence();
      },
      setLocationPayload(value) {
        globalThis.__locationPayload = value;
      },
      getSnapshot() {
        return {
          runWithLockedUserInteraction: globalThis.__calls.runWithLockedUserInteraction,
          resolveCurrentLocation: globalThis.__calls.resolveCurrentLocation.slice(),
          runAutomaticActivitiesIfNeeded: globalThis.__calls.runAutomaticActivitiesIfNeeded.slice(),
        };
      },
    };`,
  ].join('\n\n');

  vm.runInNewContext(moduleSource, context, { filename: 'check-manual-refresh-sequence.vm.js' });
  return {
    helpers: context.__manualRefreshSequenceTestExports,
    context,
  };
}

function createManualRefreshAutomaticActivityHarness(overrides = {}) {
  const shouldAttemptAutomaticLocationEventImpl = overrides.shouldAttemptAutomaticLocationEvent
    || ((locationPayload, remoteState, settings) => (
      checkAutomaticActivities.shouldAttemptAutomaticLocationEvent(locationPayload, remoteState, settings)
    ));
  const context = {
    Boolean,
    Promise,
    automaticCheckoutLocation: checkAutomaticActivities.AUTOMATIC_CHECKOUT_LOCATION,
    automaticActivities: checkAutomaticActivities,
    gpsLocationPermissionGranted: overrides.gpsLocationPermissionGranted !== undefined
      ? Boolean(overrides.gpsLocationPermissionGranted)
      : true,
    latestHistoryState: null,
    mixedZoneIntervalMinutes: overrides.mixedZoneIntervalMinutes !== undefined
      ? overrides.mixedZoneIntervalMinutes
      : 35,
    chaveInput: { value: overrides.chave || 'A123' },
    __calls: {
      runWithLockedUserInteraction: 0,
      resolveCurrentLocation: [],
      fetchWebState: [],
      applyHistoryState: [],
      shouldAttemptAutomaticLocationEvent: [],
      submitAutomaticActivity: [],
    },
    __locationPayload: null,
    __remoteState: overrides.remoteState || {
      current_action: 'checkout',
      current_local: 'Zona de CheckOut',
      last_checkin_at: '2026-04-16T08:00:00',
      last_checkout_at: '2026-04-16T09:00:00',
    },
    isUserInteractionLocked: overrides.isUserInteractionLocked || (() => false),
    isApplicationUnlocked: overrides.isApplicationUnlocked || (() => true),
    isAutomaticActivitiesEnabled: overrides.isAutomaticActivitiesEnabled || (() => true),
    sanitizeChave: overrides.sanitizeChave || ((value) => String(value || '').trim().toUpperCase()),
    runWithLockedUserInteraction: overrides.runWithLockedUserInteraction || (async (callback) => {
      context.__calls.runWithLockedUserInteraction += 1;
      return callback();
    }),
    resolveCurrentLocation: overrides.resolveCurrentLocation || (async (options) => {
      context.__calls.resolveCurrentLocation.push(options);
      return context.__locationPayload;
    }),
    fetchWebState: overrides.fetchWebState || (async (chave) => {
      context.__calls.fetchWebState.push(chave);
      return context.__remoteState;
    }),
    applyHistoryState: overrides.applyHistoryState || ((remoteState) => {
      context.__calls.applyHistoryState.push(remoteState);
    }),
    shouldAttemptAutomaticLocationEvent: (locationPayload, remoteState, settings) => {
      context.__calls.shouldAttemptAutomaticLocationEvent.push({ locationPayload, remoteState, settings });
      return shouldAttemptAutomaticLocationEventImpl(locationPayload, remoteState, settings);
    },
    shouldAttemptAutomaticOutOfRangeCheckout:
      overrides.shouldAttemptAutomaticOutOfRangeCheckout
      || ((locationPayload, remoteState) => (
        checkAutomaticActivities.shouldAttemptAutomaticOutOfRangeCheckout(locationPayload, remoteState)
      )),
    shouldAttemptAutomaticNearbyWorkplaceCheckIn:
      overrides.shouldAttemptAutomaticNearbyWorkplaceCheckIn
      || ((locationPayload, remoteState) => (
        checkAutomaticActivities.shouldAttemptAutomaticNearbyWorkplaceCheckIn(locationPayload, remoteState)
      )),
    resolveAutomaticCheckInLocation:
      overrides.resolveAutomaticCheckInLocation
      || ((locationPayload) => checkAutomaticActivities.resolveAutomaticCheckInLocation(locationPayload)),
    isCheckoutZoneLocationName:
      overrides.isCheckoutZoneLocationName
      || ((value) => checkAutomaticActivities.isCheckoutZoneLocationName(value)),
    submitAutomaticActivity: overrides.submitAutomaticActivity || (async ({ action, local, suppressStatus }) => {
      context.__calls.submitAutomaticActivity.push({ action, local, suppressStatus });
      return {
        state: {
          current_action: action,
          current_local: local,
        },
      };
    }),
  };

  const moduleSource = [
    extractFunctionSource(checkScript, 'resolveAutomaticLocationAction'),
    `async ${extractFunctionSource(checkScript, 'runAutomaticActivitiesIfNeeded')}`,
    `async ${extractFunctionSource(checkScript, 'runManualLocationRefreshSequence')}`,
    `globalThis.__manualRefreshAutomaticActivityTestExports = {
      async runAutomaticActivitiesIfNeeded(locationPayload, options) {
        return runAutomaticActivitiesIfNeeded(locationPayload, options);
      },
      async runManualLocationRefreshSequence() {
        return runManualLocationRefreshSequence();
      },
      setLocationPayload(value) {
        globalThis.__locationPayload = value;
      },
      setRemoteState(value) {
        globalThis.__remoteState = value;
      },
      getSnapshot() {
        return {
          runWithLockedUserInteraction: globalThis.__calls.runWithLockedUserInteraction,
          resolveCurrentLocation: globalThis.__calls.resolveCurrentLocation.slice(),
          fetchWebState: globalThis.__calls.fetchWebState.slice(),
          applyHistoryState: globalThis.__calls.applyHistoryState.slice(),
          shouldAttemptAutomaticLocationEvent: globalThis.__calls.shouldAttemptAutomaticLocationEvent.slice(),
          submitAutomaticActivity: globalThis.__calls.submitAutomaticActivity.slice(),
          latestHistoryState: globalThis.latestHistoryState,
        };
      },
    };`,
  ].join('\n\n');

  vm.runInNewContext(moduleSource, context, { filename: 'check-manual-refresh-automatic-activity.vm.js' });
  return {
    helpers: context.__manualRefreshAutomaticActivityTestExports,
    context,
  };
}

function createLifecycleAutomaticActivityHarness(overrides = {}) {
  const shouldAttemptAutomaticLocationEventImpl = overrides.shouldAttemptAutomaticLocationEvent
    || ((locationPayload, remoteState, settings) => (
      checkAutomaticActivities.shouldAttemptAutomaticLocationEvent(locationPayload, remoteState, settings)
    ));
  const context = {
    Boolean,
    Promise,
    Date: overrides.Date || {
      now: () => 10_000,
    },
    automaticCheckoutLocation: checkAutomaticActivities.AUTOMATIC_CHECKOUT_LOCATION,
    gpsLocationPermissionGranted: overrides.gpsLocationPermissionGranted !== undefined
      ? Boolean(overrides.gpsLocationPermissionGranted)
      : true,
    latestHistoryState: null,
    mixedZoneIntervalMinutes: overrides.mixedZoneIntervalMinutes !== undefined
      ? overrides.mixedZoneIntervalMinutes
      : 35,
    chaveInput: { value: overrides.chave || 'A123' },
    lifecycleTriggerCooldownMs: overrides.lifecycleTriggerCooldownMs !== undefined
      ? overrides.lifecycleTriggerCooldownMs
      : 5000,
    lastLifecycleTriggerAt: overrides.lastLifecycleTriggerAt !== undefined
      ? overrides.lastLifecycleTriggerAt
      : 0,
    lifecycleRefreshInProgress: false,
    __locationPayload: null,
    __remoteState: overrides.remoteState || {
      current_action: 'checkout',
      current_local: 'Zona de CheckOut',
      last_checkin_at: '2026-04-16T08:00:00',
      last_checkout_at: '2026-04-16T09:00:00',
    },
    __calls: {
      refreshHistory: [],
      updateLocationForLifecycleSequence: [],
      fetchWebState: [],
      applyHistoryState: [],
      shouldAttemptAutomaticLocationEvent: [],
      setSequenceStatus: [],
      restorePersistedUserSettingsForChave: [],
      setNotificationMessage: [],
      setStatus: [],
      submitAutomaticActivity: [],
    },
    isUserInteractionLocked: overrides.isUserInteractionLocked || (() => false),
    sanitizeChave: overrides.sanitizeChave || ((value) => String(value || '').trim().toUpperCase()),
    isApplicationUnlocked: overrides.isApplicationUnlocked || (() => true),
    refreshHistory: overrides.refreshHistory || (async (chave, options) => {
      context.__calls.refreshHistory.push({ chave, options });
      return context.__remoteState;
    }),
    updateLocationForLifecycleSequence: overrides.updateLocationForLifecycleSequence || (async (options) => {
      context.__calls.updateLocationForLifecycleSequence.push(options);
      return context.__locationPayload;
    }),
    isAutomaticActivitiesEnabled: overrides.isAutomaticActivitiesEnabled || (() => true),
    fetchWebState: overrides.fetchWebState || (async (chave) => {
      context.__calls.fetchWebState.push(chave);
      return context.__remoteState;
    }),
    applyHistoryState: overrides.applyHistoryState || ((remoteState) => {
      context.__calls.applyHistoryState.push(remoteState);
    }),
    shouldAttemptAutomaticLocationEvent: (locationPayload, remoteState, settings) => {
      context.__calls.shouldAttemptAutomaticLocationEvent.push({ locationPayload, remoteState, settings });
      return shouldAttemptAutomaticLocationEventImpl(locationPayload, remoteState, settings);
    },
    shouldAttemptAutomaticOutOfRangeCheckout:
      overrides.shouldAttemptAutomaticOutOfRangeCheckout || (() => false),
    shouldAttemptAutomaticNearbyWorkplaceCheckIn:
      overrides.shouldAttemptAutomaticNearbyWorkplaceCheckIn || (() => false),
    resolveAutomaticCheckInLocation:
      overrides.resolveAutomaticCheckInLocation
      || ((locationPayload) => checkAutomaticActivities.resolveAutomaticCheckInLocation(locationPayload)),
    isCheckoutZoneLocationName:
      overrides.isCheckoutZoneLocationName
      || ((value) => checkAutomaticActivities.isCheckoutZoneLocationName(value)),
    submitAutomaticActivity: overrides.submitAutomaticActivity || (async ({ action, local, suppressStatus }) => {
      context.__calls.submitAutomaticActivity.push({ action, local, suppressStatus });
      return {
        state: {
          current_action: action,
          current_local: local,
        },
      };
    }),
    setSequenceStatus: (message) => {
      context.__calls.setSequenceStatus.push(message);
    },
    restorePersistedUserSettingsForChave: (chave) => {
      context.__calls.restorePersistedUserSettingsForChave.push(chave);
    },
    setNotificationMessage: (channel, message, tone) => {
      context.__calls.setNotificationMessage.push({ channel, message, tone });
    },
    setStatus: (message, tone) => {
      context.__calls.setStatus.push({ message, tone });
    },
  };

  const moduleSource = [
    'const lifecycleDataReuseWindowMs = 5000;',
    extractFunctionSource(checkScript, 'resolveAutomaticLocationAction'),
    `async ${extractFunctionSource(checkScript, 'runAutomaticActivitiesIfNeeded')}`,
    `async ${extractFunctionSource(checkScript, 'runLifecycleUpdateSequence')}`,
    `globalThis.__lifecycleAutomaticActivityTestExports = {
      async runLifecycleUpdateSequence(options) {
        return runLifecycleUpdateSequence(options);
      },
      setLocationPayload(value) {
        globalThis.__locationPayload = value;
      },
      getSnapshot() {
        return {
          refreshHistory: globalThis.__calls.refreshHistory.slice(),
          updateLocationForLifecycleSequence: globalThis.__calls.updateLocationForLifecycleSequence.slice(),
          fetchWebState: globalThis.__calls.fetchWebState.slice(),
          applyHistoryState: globalThis.__calls.applyHistoryState.slice(),
          shouldAttemptAutomaticLocationEvent: globalThis.__calls.shouldAttemptAutomaticLocationEvent.slice(),
          setSequenceStatus: globalThis.__calls.setSequenceStatus.slice(),
          restorePersistedUserSettingsForChave: globalThis.__calls.restorePersistedUserSettingsForChave.slice(),
          setNotificationMessage: globalThis.__calls.setNotificationMessage.slice(),
          setStatus: globalThis.__calls.setStatus.slice(),
          submitAutomaticActivity: globalThis.__calls.submitAutomaticActivity.slice(),
        };
      },
    };`,
  ].join('\n\n');

  vm.runInNewContext(moduleSource, context, { filename: 'check-lifecycle-automatic-activity.vm.js' });
  return {
    helpers: context.__lifecycleAutomaticActivityTestExports,
    context,
  };
}

function createHistoryRefreshHarness(overrides = {}) {
  let currentNow = overrides.now !== undefined ? overrides.now : 10_000;
  const context = {
    AbortController,
    Promise,
    Boolean,
    Date: {
      now: () => currentNow,
    },
    __payload: overrides.payload || {
      found: true,
      last_checkin_at: '2026-04-16T08:00:00',
      last_checkout_at: '2026-04-16T09:00:00',
      projeto: 'BASE',
    },
    __calls: {
      fetch: [],
      setHistoryMessage: [],
      applyHistoryState: [],
      resetHistory: [],
    },
    sanitizeChave: overrides.sanitizeChave || ((value) => String(value || '').trim().toUpperCase()),
    isApplicationUnlocked: overrides.isApplicationUnlocked || (() => true),
    buildProtectedRequestError: overrides.buildProtectedRequestError || (() => new Error('request failed')),
    fetch: overrides.fetch || (async (url, options) => {
      context.__calls.fetch.push({ url, options });
      return {
        ok: true,
        json: async () => context.__payload,
      };
    }),
    setHistoryMessage: (message, tone) => {
      context.__calls.setHistoryMessage.push({ message, tone });
    },
  };

  const moduleSource = [
    'const stateEndpoint = "/api/web/check/state";',
    'let latestHistoryState = null;',
    'let historyRequestToken = 0;',
    'let historyAbortController = null;',
    'let historyRequestPromise = null;',
    'let historyRequestPromiseChave = "";',
    'let lastHistoryStateAppliedAt = 0;',
    'let lastHistoryStateAppliedChave = "";',
    'function getActiveChave() { return "A123"; }',
    `function applyHistoryState(state) {
      latestHistoryState = state;
      if (state) {
        lastHistoryStateAppliedAt = Date.now();
        lastHistoryStateAppliedChave = getActiveChave();
      } else {
        lastHistoryStateAppliedAt = 0;
        lastHistoryStateAppliedChave = '';
      }
      globalThis.__calls.applyHistoryState.push(state);
    }`,
    `function resetHistory(message) {
      applyHistoryState(null);
      globalThis.__calls.resetHistory.push(message || null);
      if (message) {
        setHistoryMessage(message);
      }
    }`,
    extractFunctionSource(checkScript, 'readRecentHistoryState'),
    `async ${extractFunctionSource(checkScript, 'refreshHistory')}`,
    `globalThis.__historyRefreshTestExports = {
      async refreshHistory(chave, options) {
        return refreshHistory(chave, options);
      },
      advanceTime(ms) {
        globalThis.__advanceTime(ms);
      },
      getSnapshot() {
        return {
          fetch: globalThis.__calls.fetch.slice(),
          setHistoryMessage: globalThis.__calls.setHistoryMessage.slice(),
          applyHistoryState: globalThis.__calls.applyHistoryState.slice(),
          resetHistory: globalThis.__calls.resetHistory.slice(),
        };
      },
    };`,
  ].join('\n\n');

  context.__advanceTime = (ms) => {
    currentNow += Number(ms) || 0;
  };

  vm.runInNewContext(moduleSource, context, { filename: 'check-history-refresh.vm.js' });
  return {
    helpers: context.__historyRefreshTestExports,
    context,
  };
}

function createSubmitGuardLocationHarness(overrides = {}) {
  let currentNow = overrides.now !== undefined ? overrides.now : 10_000;
  const context = {
    Promise,
    Boolean,
    Date: {
      now: () => currentNow,
    },
    __calls: {
      queryLocationPermissionState: 0,
      captureAndResolveLocation: [],
    },
    isApplicationUnlocked: overrides.isApplicationUnlocked || (() => true),
    getActiveChave: overrides.getActiveChave || (() => 'A123'),
    sanitizeChave: overrides.sanitizeChave || ((value) => String(value || '').trim().toUpperCase()),
    queryLocationPermissionState: overrides.queryLocationPermissionState || (async () => {
      context.__calls.queryLocationPermissionState += 1;
      return 'granted';
    }),
    readStorageFlag: overrides.readStorageFlag || (() => true),
    clientState: {
      shouldAttemptSilentLocationLookup: overrides.shouldAttemptSilentLocationLookup || (() => true),
    },
    captureAndResolveLocation: overrides.captureAndResolveLocation || (async (options) => {
      context.__calls.captureAndResolveLocation.push(options);
      return { status: 'matched', resolved_local: 'Portaria' };
    }),
  };

  const moduleSource = [
    'const lifecycleDataReuseWindowMs = 5000;',
    'const locationPermissionGrantedKey = "checking.web.user.location.permission-granted";',
    'let locationRequestPromise = null;',
    'let recentLocationResolutionPayload = null;',
    'let recentLocationResolutionAt = 0;',
    'let recentLocationResolutionChave = "";',
    extractFunctionSource(checkScript, 'readRecentLocationResolution'),
    `async ${extractFunctionSource(checkScript, 'ensureLocationReadyForSubmit')}`,
    `globalThis.__submitGuardLocationTestExports = {
      async ensureLocationReadyForSubmit() {
        return ensureLocationReadyForSubmit();
      },
      setRecentLocationResolution(payload, ageMs) {
        recentLocationResolutionPayload = payload;
        recentLocationResolutionAt = Date.now() - (Number(ageMs) || 0);
        recentLocationResolutionChave = 'A123';
      },
      clearRecentLocationResolution() {
        recentLocationResolutionPayload = null;
        recentLocationResolutionAt = 0;
        recentLocationResolutionChave = '';
      },
      getSnapshot() {
        return {
          queryLocationPermissionState: globalThis.__calls.queryLocationPermissionState,
          captureAndResolveLocation: globalThis.__calls.captureAndResolveLocation.slice(),
        };
      },
    };`,
  ].join('\n\n');

  vm.runInNewContext(moduleSource, context, { filename: 'check-submit-guard-location.vm.js' });
  return {
    helpers: context.__submitGuardLocationTestExports,
    context,
  };
}

function toPlainValue(value) {
  return JSON.parse(JSON.stringify(value));
}

test('check controller source parses as valid JavaScript', () => {
  assert.doesNotThrow(() => {
    new vm.Script(checkScript);
  });
});

test('check page keeps Projeto, Local and Informe controls addressable for toggle-driven visibility', () => {
  assert.doesNotMatch(checkHtml, /<title>\s*Checking Mobile Web\s*<\/title>/);
  assert.match(checkHtml, /<span class="header-logo-text">\s*Checking Web\s*<\/span>/);
  assert.match(checkHtml, /id="automaticActivitiesToggle"/);
  assert.match(checkHtml, /id="projectField"/);
  assert.match(checkHtml, /id="locationSelectField"/);
  assert.match(checkHtml, /id="informeField"/);
  assert.match(checkHtml, /id="submitButton"[\s\S]*>Registrar</);
});

test('check controller keeps automatic mode blocked outside the accuracy fallback override and reruns lifecycle updates when GPS is available', () => {
  const { helpers } = createManualOverrideUiHarness();

  helpers.setAutomaticActivitiesEnabled(true);
  helpers.setGpsLocationPermissionGranted(true);
  helpers.setCurrentLocationResolutionStatus('matched');
  helpers.syncProjectVisibility();
  helpers.syncFormControlStates();

  const matchedSnapshot = toPlainValue(helpers.getSnapshot());
  assert.equal(matchedSnapshot.projectHidden, true);
  assert.equal(matchedSnapshot.locationHidden, true);
  assert.equal(matchedSnapshot.informeHidden, true);
  assert.equal(matchedSnapshot.projectDisabled, true);
  assert.equal(matchedSnapshot.manualLocationDisabled, true);
  assert.deepStrictEqual(matchedSnapshot.actionDisabled, [true, true]);
  assert.equal(matchedSnapshot.submitDisabled, true);

  helpers.setGpsLocationPermissionGranted(false);
  helpers.setCurrentLocationResolutionStatus(null);
  helpers.syncProjectVisibility();
  helpers.syncFormControlStates();

  const noPermissionSnapshot = toPlainValue(helpers.getSnapshot());
  assert.equal(noPermissionSnapshot.projectHidden, true);
  assert.equal(noPermissionSnapshot.locationHidden, true);
  assert.equal(noPermissionSnapshot.projectDisabled, true);
  assert.equal(noPermissionSnapshot.submitDisabled, true);

  assert.match(checkScript, /control === manualLocationSelect[\s\S]*!shouldAllowManualLocationSelection\(\)/);
  assert.match(checkScript, /if \(shouldAllowManualLocationSelection\(\) && !manualLocationSelect\.value\) \{/);
  assert.match(checkScript, /function resolveSubmittedLocationValue\(\) \{[\s\S]*shouldAllowManualLocationSelection\(\)[\s\S]*manualLocationSelect\.value \|\| null[\s\S]*currentLocationMatch \? currentLocationMatch\.resolved_local : null/);
  assert.match(checkScript, /local: resolveSubmittedLocationValue\(\)/);
  assert.match(checkScript, /setGpsLocationPermissionGranted\(value\) \{[\s\S]*syncProjectVisibility\(\);/);
  assert.match(checkScript, /automaticActivitiesToggle\.addEventListener\('change', \(\) => \{[\s\S]*syncProjectVisibility\(\);[\s\S]*syncManualLocationControl\(\);/);
  assert.match(checkScript, /if \(gpsLocationPermissionGranted && isApplicationUnlocked\(\)\) \{[\s\S]*runLifecycleUpdateSequence\(\{[\s\S]*ignoreCooldown: true,[\s\S]*triggerSource: 'automatic_activities_disable',[\s\S]*\}\);/);
  assert.match(checkScript, /if \(isAutomaticActivitiesEnabled\(\) && !isAccuracyTooLowManualFallbackActive\(\)\) \{[\s\S]*Desative Atividades Automáticas para registrar manualmente\./);
});

test('check controller preserves manual override across automatic toggle changes only while accuracy_too_low remains active', () => {
  const { helpers } = createManualOverrideUiHarness();

  helpers.setGpsLocationPermissionGranted(true);
  helpers.setCurrentLocationResolutionStatus('accuracy_too_low');
  helpers.setAvailableLocations(['Portaria']);

  helpers.setAutomaticActivitiesEnabled(false);
  helpers.syncProjectVisibility();
  helpers.syncFormControlStates();
  const manualModeSnapshot = toPlainValue(helpers.getSnapshot());
  assert.equal(manualModeSnapshot.projectHidden, false);
  assert.equal(manualModeSnapshot.projectDisabled, false);
  assert.equal(manualModeSnapshot.manualLocationDisabled, false);

  helpers.setAutomaticActivitiesEnabled(true);
  helpers.syncProjectVisibility();
  helpers.syncFormControlStates();
  const automaticModeSnapshot = toPlainValue(helpers.getSnapshot());
  assert.equal(automaticModeSnapshot.projectHidden, false);
  assert.equal(automaticModeSnapshot.projectDisabled, false);
  assert.equal(automaticModeSnapshot.manualLocationDisabled, false);

  helpers.setCurrentLocationResolutionStatus('matched');
  helpers.syncProjectVisibility();
  helpers.syncFormControlStates();
  const recoveredSnapshot = toPlainValue(helpers.getSnapshot());
  assert.equal(recoveredSnapshot.projectHidden, true);
  assert.equal(recoveredSnapshot.projectDisabled, true);
  assert.equal(recoveredSnapshot.manualLocationDisabled, true);
});

test('check controller unlocks manual override controls during accuracy_too_low even with automatic mode enabled', () => {
  const { helpers } = createManualOverrideUiHarness();

  helpers.setAutomaticActivitiesEnabled(true);
  helpers.setGpsLocationPermissionGranted(true);
  helpers.setCurrentLocationResolutionStatus('accuracy_too_low');
  helpers.setAvailableLocations(['Portaria']);
  helpers.syncProjectVisibility();
  helpers.syncFormControlStates();

  const snapshot = toPlainValue(helpers.getSnapshot());
  assert.equal(snapshot.projectHidden, false);
  assert.equal(snapshot.locationHidden, false);
  assert.equal(snapshot.informeHidden, true);
  assert.equal(snapshot.projectDisabled, false);
  assert.equal(snapshot.manualLocationDisabled, false);
  assert.deepStrictEqual(snapshot.actionDisabled, [false, false]);
  assert.equal(snapshot.submitDisabled, false);

  helpers.setAvailableLocations([]);
  helpers.syncFormControlStates();
  const syntheticOnlySnapshot = toPlainValue(helpers.getSnapshot());
  assert.equal(syntheticOnlySnapshot.manualLocationDisabled, false);
});

test('check controller prefers Escritório Principal and falls back to Precisao Insuficiente only during accuracy_too_low', () => {
  const { helpers } = createManualLocationSelectHarness();

  helpers.setGpsLocationPermissionGranted(true);
  helpers.setCurrentLocationResolutionStatus('accuracy_too_low');
  helpers.setAvailableLocations(['Portaria', 'Escritório Principal']);
  helpers.syncManualLocationControl();

  const preferredDefaultSnapshot = toPlainValue(helpers.getSnapshot());
  assert.deepStrictEqual(preferredDefaultSnapshot.options, ['Portaria', 'Escritório Principal']);
  assert.equal(preferredDefaultSnapshot.selectedValue, 'Escritório Principal');
  assert.equal(preferredDefaultSnapshot.resolvedDefault, 'Escritório Principal');

  helpers.setAvailableLocations(['Portaria']);
  helpers.setManualLocationValue('');
  helpers.syncManualLocationControl();

  const syntheticFallbackSnapshot = toPlainValue(helpers.getSnapshot());
  assert.deepStrictEqual(syntheticFallbackSnapshot.options, ['Precisao Insuficiente', 'Portaria']);
  assert.equal(syntheticFallbackSnapshot.selectedValue, 'Precisao Insuficiente');
  assert.equal(syntheticFallbackSnapshot.resolvedDefault, 'Precisao Insuficiente');
});

test('check controller keeps the no-permission manual flow limited to API-provided locations', () => {
  const { helpers } = createManualLocationSelectHarness();

  helpers.setGpsLocationPermissionGranted(false);
  helpers.setCurrentLocationResolutionStatus(null);
  helpers.setAvailableLocations(['Portaria']);
  helpers.syncManualLocationControl();

  const snapshot = toPlainValue(helpers.getSnapshot());
  assert.deepStrictEqual(snapshot.options, ['Portaria']);
  assert.equal(snapshot.selectedValue, 'Portaria');
  assert.equal(snapshot.resolvedDefault, 'Portaria');
});

test('check controller recalculates manual location defaults when project options change during accuracy_too_low', () => {
  const { helpers } = createManualLocationSelectHarness();

  helpers.setGpsLocationPermissionGranted(true);
  helpers.setCurrentLocationResolutionStatus('accuracy_too_low');
  helpers.setAvailableLocations(['Portaria']);
  helpers.syncManualLocationControl();

  const firstProjectSnapshot = toPlainValue(helpers.getSnapshot());
  assert.deepStrictEqual(firstProjectSnapshot.options, ['Precisao Insuficiente', 'Portaria']);
  assert.equal(firstProjectSnapshot.selectedValue, 'Precisao Insuficiente');

  helpers.setAvailableLocations(['Escritório Principal', 'Almoxarifado']);
  helpers.setManualLocationValue('Precisao Insuficiente');
  helpers.syncManualLocationControl();

  const secondProjectSnapshot = toPlainValue(helpers.getSnapshot());
  assert.deepStrictEqual(secondProjectSnapshot.options, ['Escritório Principal', 'Almoxarifado']);
  assert.equal(secondProjectSnapshot.selectedValue, 'Escritório Principal');
  assert.equal(secondProjectSnapshot.resolvedDefault, 'Escritório Principal');
});

test('check controller removes the synthetic fallback option after leaving accuracy_too_low', () => {
  const { helpers } = createManualLocationSelectHarness();

  helpers.setGpsLocationPermissionGranted(true);
  helpers.setCurrentLocationResolutionStatus('accuracy_too_low');
  helpers.setAvailableLocations(['Portaria']);
  helpers.syncManualLocationControl();
  assert.deepStrictEqual(toPlainValue(helpers.getSnapshot()).options, ['Precisao Insuficiente', 'Portaria']);

  helpers.setCurrentLocationResolutionStatus('matched');
  helpers.syncManualLocationControl();

  const recoveredSnapshot = toPlainValue(helpers.getSnapshot());
  assert.deepStrictEqual(recoveredSnapshot.options, ['Portaria']);
  assert.equal(recoveredSnapshot.selectedValue, 'Portaria');
  assert.equal(recoveredSnapshot.resolvedDefault, 'Portaria');
});

test('check controller resolves the submitted local from manual fallback and matched GPS states', () => {
  const { helpers } = createSubmittedLocationHarness();

  helpers.setGpsLocationPermissionGranted(true);
  helpers.setCurrentLocationResolutionStatus('accuracy_too_low');
  helpers.setManualLocationValue('Precisao Insuficiente');
  helpers.setCurrentLocationMatch(null);
  assert.equal(helpers.resolveSubmittedLocationValue(), 'Precisao Insuficiente');

  helpers.setGpsLocationPermissionGranted(false);
  helpers.setCurrentLocationResolutionStatus(null);
  helpers.setManualLocationValue('Portaria');
  assert.equal(helpers.resolveSubmittedLocationValue(), 'Portaria');

  helpers.setGpsLocationPermissionGranted(true);
  helpers.setCurrentLocationResolutionStatus('matched');
  helpers.setCurrentLocationMatch({ resolved_local: 'Guarita' });
  helpers.setManualLocationValue('Ignorado');
  assert.equal(helpers.resolveSubmittedLocationValue(), 'Guarita');
});

test('check controller reloads project locations during accuracy_too_low even when automatic mode is enabled', async () => {
  const { helpers } = createProjectSelectionHarness();

  helpers.setAutomaticActivitiesEnabled(true);
  helpers.setGpsLocationPermissionGranted(true);
  helpers.setCurrentLocationResolutionStatus('matched');
  let result = await helpers.updateCurrentUserProjectSelection();
  let snapshot = toPlainValue(helpers.getSnapshot());

  assert.equal(result, false);
  assert.equal(snapshot.fetches.length, 0);
  assert.equal(snapshot.loadManualLocations, 0);

  helpers.setCurrentLocationResolutionStatus('accuracy_too_low');
  result = await helpers.updateCurrentUserProjectSelection();
  snapshot = toPlainValue(helpers.getSnapshot());

  assert.equal(result, true);
  assert.equal(snapshot.fetches.length, 1);
  assert.deepStrictEqual(snapshot.fetches[0].body, {
    chave: 'AB12',
    projeto: 'Projeto B',
  });
  assert.equal(snapshot.loadManualLocations, 1);
  assert.equal(snapshot.lastCommittedProjectValue, 'Projeto B');
  assert.equal(snapshot.latestHistoryProject, 'Projeto B');
});

test('check controller stores mixed zone interval from the web locations catalog, falls back during partial rollout, and clears it on reset paths', async () => {
  const { helpers } = createLocationCatalogSettingsHarness();

  helpers.setPayload({
    items: ['Portaria', 'Portaria', 'Zona Mista'],
    location_accuracy_threshold_meters: 25,
    mixed_zone_interval_minutes: 35,
  });
  await helpers.loadManualLocations();

  let snapshot = toPlainValue(helpers.getSnapshot());
  assert.deepStrictEqual(snapshot.availableLocations, ['Portaria', 'Zona Mista']);
  assert.equal(snapshot.locationAccuracyThresholdMeters, 25);
  assert.equal(snapshot.mixedZoneIntervalMinutes, 35);

  helpers.setPayload({
    items: ['Portaria'],
    location_accuracy_threshold_meters: 30,
  });
  await helpers.loadManualLocations();

  snapshot = toPlainValue(helpers.getSnapshot());
  assert.equal(snapshot.locationAccuracyThresholdMeters, 30);
  assert.equal(snapshot.mixedZoneIntervalMinutes, 20);

  helpers.setApplicationUnlocked(false);
  await helpers.loadManualLocations();

  snapshot = toPlainValue(helpers.getSnapshot());
  assert.deepStrictEqual(snapshot.availableLocations, []);
  assert.equal(snapshot.locationAccuracyThresholdMeters, null);
  assert.equal(snapshot.mixedZoneIntervalMinutes, null);
});

test('check controller keeps loading the locations catalog before the startup lifecycle refresh', async () => {
  const { helpers } = createAuthenticatedApplicationHarness();

  const result = await helpers.loadAuthenticatedApplication('ab12', { showReadyMessage: true });
  const snapshot = toPlainValue(helpers.getSnapshot());

  assert.equal(result, true);
  assert.deepStrictEqual(snapshot, [
    { step: 'loadProjectCatalog', options: { showError: false } },
    { step: 'restorePersistedUserSettingsForChave', chave: 'AB12' },
    { step: 'loadManualLocations' },
    { step: 'setStatus', message: 'Autenticação concluída. Atualizando a aplicação...', tone: 'info' },
    { step: 'runLifecycleUpdateSequence', options: { ignoreCooldown: true, triggerSource: 'startup' } },
  ]);
});

test('check controller does not auto-verify while the user is still typing the password', () => {
  const { helpers } = createPasswordInputAuthenticationHarness();

  helpers.setPasswordValue('abc');
  helpers.syncPasswordInputState({ showReadyMessage: true });

  let snapshot = toPlainValue(helpers.getSnapshot());
  assert.deepStrictEqual(snapshot.schedulePasswordVerification, []);
  assert.equal(snapshot.clearPasswordVerificationTimer, 1);

  helpers.resetCalls();
  helpers.syncPasswordInputState({
    showReadyMessage: true,
    allowAutomaticVerification: true,
    requirePersistedPasswordMatch: false,
  });

  snapshot = toPlainValue(helpers.getSnapshot());
  assert.deepStrictEqual(snapshot.schedulePasswordVerification, [{
    showReadyMessage: true,
    requirePersistedPasswordMatch: false,
  }]);
});

test('check controller only auto-verifies after auth status when the restored password matches the persisted value', async () => {
  const { helpers } = createAuthenticationStatusHarness();

  helpers.setPersistedPasswordMap({ AB12: 'segredo' });
  helpers.setPasswordValue('segredo');
  await helpers.refreshAuthenticationStatus('ab12', { schedulePasswordVerification: true });

  let snapshot = toPlainValue(helpers.getSnapshot());
  assert.deepStrictEqual(snapshot.schedulePasswordVerification, [{ showReadyMessage: true }]);
  assert.equal(snapshot.schedulePasswordAutofillSync, 1);

  helpers.resetCalls();
  helpers.setPasswordValue('digitando');
  await helpers.refreshAuthenticationStatus('ab12', { schedulePasswordVerification: true });

  snapshot = toPlainValue(helpers.getSnapshot());
  assert.deepStrictEqual(snapshot.schedulePasswordVerification, []);
  assert.equal(snapshot.schedulePasswordAutofillSync, 1);
});

test('check controller does not replay the authenticated bootstrap for the same verified session', async () => {
  const { helpers } = createAuthenticatedApplicationHarness();

  const firstResult = await helpers.loadAuthenticatedApplication('ab12', { showReadyMessage: true });
  const secondResult = await helpers.loadAuthenticatedApplication('ab12', { showReadyMessage: true });
  const snapshot = toPlainValue(helpers.getSnapshot());

  assert.equal(firstResult, true);
  assert.equal(secondResult, true);
  assert.deepStrictEqual(snapshot, [
    { step: 'loadProjectCatalog', options: { showError: false } },
    { step: 'restorePersistedUserSettingsForChave', chave: 'AB12' },
    { step: 'loadManualLocations' },
    { step: 'setStatus', message: 'Autenticação concluída. Atualizando a aplicação...', tone: 'info' },
    { step: 'runLifecycleUpdateSequence', options: { ignoreCooldown: true, triggerSource: 'startup' } },
  ]);
});

test('check controller forwards the loaded mixed zone interval into the automatic location decision engine', () => {
  const { helpers } = createAutomaticLocationDecisionHarness();

  helpers.shouldAttemptAutomaticLocationEvent(
    { resolved_local: 'Zona Mista' },
    { current_action: 'checkout', current_local: 'Zona Mista' },
    { referenceTime: '2026-04-16T09:20:00' }
  );

  assert.deepStrictEqual(toPlainValue(helpers.getSnapshot()), [
    {
      locationPayload: { resolved_local: 'Zona Mista' },
      remoteState: { current_action: 'checkout', current_local: 'Zona Mista' },
      settings: {
        mixedZoneIntervalMinutes: 35,
        referenceTime: '2026-04-16T09:20:00',
      },
    },
  ]);
});

test('check controller injects the mixed zone interval into runtime automatic activity decisions', async () => {
  const { helpers } = createManualRefreshAutomaticActivityHarness({
    shouldAttemptAutomaticLocationEvent: () => false,
  });

  await helpers.runAutomaticActivitiesIfNeeded(
    { matched: true, resolved_local: 'Zona Mista', status: 'matched' },
    { suppressStatus: true }
  );

  const snapshot = toPlainValue(helpers.getSnapshot());
  assert.deepStrictEqual(snapshot.shouldAttemptAutomaticLocationEvent, [{
    locationPayload: { matched: true, resolved_local: 'Zona Mista', status: 'matched' },
    remoteState: {
      current_action: 'checkout',
      current_local: 'Zona de CheckOut',
      last_checkin_at: '2026-04-16T08:00:00',
      last_checkout_at: '2026-04-16T09:00:00',
    },
    settings: {
      mixedZoneIntervalMinutes: 35,
    },
  }]);
  assert.deepStrictEqual(snapshot.submitAutomaticActivity, []);
});

test('check lifecycle sequence forwards the stored mixed zone interval into the automatic engine', async () => {
  const { helpers } = createLifecycleAutomaticActivityHarness({
    shouldAttemptAutomaticLocationEvent: () => false,
  });

  helpers.setLocationPayload({
    matched: true,
    resolved_local: 'Zona Mista',
    status: 'matched',
  });

  const result = await helpers.runLifecycleUpdateSequence({ triggerSource: 'visibility' });
  const snapshot = toPlainValue(helpers.getSnapshot());

  assert.equal(result, true);
  assert.deepStrictEqual(snapshot.refreshHistory, [{
    chave: 'A123',
    options: {
      showLoadingMessage: false,
      silentSuccessMessage: true,
      suppressMessages: true,
      rethrowErrors: true,
      cacheWindowMs: 5000,
    },
  }]);
  assert.deepStrictEqual(snapshot.updateLocationForLifecycleSequence, [{
    triggerSource: 'visibility',
    cacheWindowMs: 5000,
  }]);
  assert.deepStrictEqual(snapshot.fetchWebState, []);
  assert.deepStrictEqual(snapshot.shouldAttemptAutomaticLocationEvent, [{
    locationPayload: {
      matched: true,
      resolved_local: 'Zona Mista',
      status: 'matched',
    },
    remoteState: {
      current_action: 'checkout',
      current_local: 'Zona de CheckOut',
      last_checkin_at: '2026-04-16T08:00:00',
      last_checkout_at: '2026-04-16T09:00:00',
    },
    settings: {
      mixedZoneIntervalMinutes: 35,
    },
  }]);
  assert.deepStrictEqual(snapshot.setSequenceStatus, [
    'Atualizando as atividades.....',
    'Atualizando a localização.....',
    'Realizando check-in ou check-out, se aplicável.....',
  ]);
  assert.deepStrictEqual(snapshot.restorePersistedUserSettingsForChave, ['A123']);
  assert.deepStrictEqual(snapshot.setStatus, [{
    message: 'Aplicação atualizada com sucesso.',
    tone: 'success',
  }]);
  assert.deepStrictEqual(snapshot.submitAutomaticActivity, []);
});

test('check controller reuses recent history state during lifecycle refreshes inside the cache window', async () => {
  const { helpers } = createHistoryRefreshHarness();

  await helpers.refreshHistory('a123', {
    suppressMessages: true,
    cacheWindowMs: 5000,
  });
  await helpers.refreshHistory('a123', {
    suppressMessages: true,
    cacheWindowMs: 5000,
  });

  let snapshot = toPlainValue(helpers.getSnapshot());
  assert.equal(snapshot.fetch.length, 1);
  assert.equal(snapshot.applyHistoryState.length, 1);

  helpers.advanceTime(6000);
  await helpers.refreshHistory('a123', {
    suppressMessages: true,
    cacheWindowMs: 5000,
  });

  snapshot = toPlainValue(helpers.getSnapshot());
  assert.equal(snapshot.fetch.length, 2);
  assert.equal(snapshot.applyHistoryState.length, 2);
});

test('check controller reuses a recent lifecycle location for the submit guard instead of recapturing immediately', async () => {
  const { helpers } = createSubmitGuardLocationHarness();

  helpers.setRecentLocationResolution({
    matched: true,
    resolved_local: 'Portaria',
    status: 'matched',
  }, 1500);

  await helpers.ensureLocationReadyForSubmit();

  let snapshot = toPlainValue(helpers.getSnapshot());
  assert.equal(snapshot.queryLocationPermissionState, 0);
  assert.deepStrictEqual(snapshot.captureAndResolveLocation, []);

  helpers.clearRecentLocationResolution();
  await helpers.ensureLocationReadyForSubmit();

  snapshot = toPlainValue(helpers.getSnapshot());
  assert.equal(snapshot.queryLocationPermissionState, 1);
  assert.deepStrictEqual(snapshot.captureAndResolveLocation, [{
    interactive: false,
    forceRefresh: true,
    measurementTrigger: 'submit_guard',
  }]);
});

test('check controller submits automatic checkout when Zona Mista is reached after a remote check-in', async () => {
  const { helpers } = createManualRefreshAutomaticActivityHarness({
    remoteState: {
      current_action: 'checkin',
      current_local: 'Recepção',
      last_checkin_at: '2026-04-16T09:00:00',
      last_checkout_at: '2026-04-16T08:00:00',
    },
  });

  await helpers.runAutomaticActivitiesIfNeeded({
    matched: true,
    resolved_local: 'Zona Mista',
    status: 'matched',
  });

  const snapshot = toPlainValue(helpers.getSnapshot());
  assert.deepStrictEqual(snapshot.submitAutomaticActivity, [{
    action: 'checkout',
    local: 'Zona Mista',
  }]);
});

test('check controller keeps checkout zone forcing automatic checkout after a mixed-zone check-in', async () => {
  const { helpers } = createManualRefreshAutomaticActivityHarness({
    remoteState: {
      current_action: 'checkin',
      current_local: 'Zona Mista',
      last_checkin_at: '2026-04-16T09:00:00',
      last_checkout_at: '2026-04-16T08:00:00',
    },
  });

  await helpers.runAutomaticActivitiesIfNeeded({
    matched: true,
    resolved_local: 'Zona de CheckOut',
    status: 'matched',
  }, {
    suppressStatus: true,
    referenceTime: '2026-04-16T09:10:00',
  });

  const snapshot = toPlainValue(helpers.getSnapshot());
  assert.deepStrictEqual(snapshot.submitAutomaticActivity, [{
    action: 'checkout',
    local: 'Zona de CheckOut',
    suppressStatus: true,
  }]);
});

test('check controller keeps outside_workplace forcing automatic checkout after a mixed-zone check-in', async () => {
  const { helpers } = createManualRefreshAutomaticActivityHarness({
    remoteState: {
      current_action: 'checkin',
      current_local: 'Zona Mista',
      last_checkin_at: '2026-04-16T09:00:00',
      last_checkout_at: '2026-04-16T08:00:00',
    },
  });

  await helpers.runAutomaticActivitiesIfNeeded({
    matched: false,
    status: 'outside_workplace',
    minimum_checkout_distance_meters: 2500,
  }, {
    suppressStatus: true,
    referenceTime: '2026-04-16T09:10:00',
  });

  const snapshot = toPlainValue(helpers.getSnapshot());
  assert.deepStrictEqual(snapshot.submitAutomaticActivity, [{
    action: 'checkout',
    local: 'Fora do Local de Trabalho',
    suppressStatus: true,
  }]);
});

test('check controller keeps automatic check-in immediate when leaving mixed zone for a known location after checkout', async () => {
  const { helpers } = createManualRefreshAutomaticActivityHarness({
    remoteState: {
      current_action: 'checkout',
      current_local: 'Zona Mista',
      last_checkin_at: '2026-04-16T08:00:00',
      last_checkout_at: '2026-04-16T09:00:00',
    },
  });

  await helpers.runAutomaticActivitiesIfNeeded({
    matched: true,
    resolved_local: 'Escritório Principal',
    status: 'matched',
  }, {
    suppressStatus: true,
    referenceTime: '2026-04-16T09:10:00',
  });

  const snapshot = toPlainValue(helpers.getSnapshot());
  assert.deepStrictEqual(snapshot.submitAutomaticActivity, [{
    action: 'checkin',
    local: 'Escritório Principal',
    suppressStatus: true,
  }]);
});

test('check controller keeps automatic check-in immediate when leaving mixed zone for a nearby eligible unregistered location', async () => {
  const { helpers } = createManualRefreshAutomaticActivityHarness({
    remoteState: {
      current_action: 'checkout',
      current_local: 'Zona Mista',
      last_checkin_at: '2026-04-16T08:00:00',
      last_checkout_at: '2026-04-16T09:00:00',
    },
  });

  await helpers.runAutomaticActivitiesIfNeeded({
    matched: false,
    status: 'not_in_known_location',
    label: 'Localização não Cadastrada',
    nearest_workplace_distance_meters: 180,
  }, {
    suppressStatus: true,
    referenceTime: '2026-04-16T09:10:00',
  });

  const snapshot = toPlainValue(helpers.getSnapshot());
  assert.deepStrictEqual(snapshot.submitAutomaticActivity, [{
    action: 'checkin',
    local: 'Localização não Cadastrada',
    suppressStatus: true,
  }]);
});

test('check controller re-enables manual local fallback when GPS ends below the required accuracy', () => {
  const { helpers } = createManualLocationFallbackHarness();

  assert.equal(helpers.isAccuracyTooLowManualFallbackActive(), false);
  assert.equal(helpers.shouldAllowManualLocationSelection(), true);

  helpers.setGpsLocationPermissionGranted(true);
  helpers.setResolvedLocation({
    matched: true,
    status: 'matched',
    resolved_local: 'Portaria',
  });
  assert.equal(helpers.isAccuracyTooLowManualFallbackActive(), false);
  assert.equal(helpers.shouldAllowManualLocationSelection(), false);

  helpers.setResolvedLocation({
    matched: false,
    status: 'accuracy_too_low',
    label: 'Precisao insuficiente',
    resolved_local: null,
  });
  assert.equal(helpers.isAccuracyTooLowManualFallbackActive(), true);
  assert.equal(helpers.shouldAllowManualLocationSelection(), true);
  assert.deepStrictEqual(toPlainValue(helpers.getState()), {
    gpsLocationPermissionGranted: true,
    currentLocationMatch: null,
    currentLocationResolutionStatus: 'accuracy_too_low',
  });

  helpers.setResolvedLocation({
    matched: false,
    status: 'outside_workplace',
    resolved_local: null,
  });
  assert.equal(helpers.isAccuracyTooLowManualFallbackActive(), false);
  assert.equal(helpers.shouldAllowManualLocationSelection(), false);
});

test('check controller exposes opt-in local measurement support for baseline GPS sessions', () => {
  assert.match(checkScript, /const locationMeasurementStorageKey = 'checking\.web\.location\.measurement\.enabled';/);
  assert.match(checkScript, /window\.CheckingWebLocationMeasurement = Object\.freeze\(\{[\s\S]*enable\(\)[\s\S]*getSessions\(\)[\s\S]*getLatestSession\(\)[\s\S]*summarize\(\)[\s\S]*summarizeByTrigger\(\)[\s\S]*buildReport\(metadata\)[\s\S]*printReport\(metadata\)/);
  assert.match(checkScript, /measurementTrigger: 'manual_refresh'/);
  assert.match(checkScript, /measurementTrigger: 'automatic_activities_enable'/);
});

test('check location helpers map lifecycle triggers to the 0s to 5s watch window and preserve enforced triggers elsewhere', () => {
  const { helpers } = createLocationHelperHarness();
  helpers.setLocationAccuracyThresholdMeters(30);

  assert.deepStrictEqual(toPlainValue(helpers.buildLocationCapturePlan({ measurementTrigger: 'startup' })), {
    trigger: 'startup',
    strategy: 'watch_window',
    minimumWindowMs: 0,
    maxWindowMs: 5000,
    targetAccuracyMeters: 30,
  });
  assert.deepStrictEqual(toPlainValue(helpers.buildLocationCapturePlan({ measurementTrigger: 'visibility' })), {
    trigger: 'visibility',
    strategy: 'watch_window',
    minimumWindowMs: 0,
    maxWindowMs: 5000,
    targetAccuracyMeters: 30,
  });
  assert.deepStrictEqual(toPlainValue(helpers.buildLocationCapturePlan({ measurementTrigger: 'pageshow' })), {
    trigger: 'pageshow',
    strategy: 'watch_window',
    minimumWindowMs: 0,
    maxWindowMs: 5000,
    targetAccuracyMeters: 30,
  });
  assert.deepStrictEqual(toPlainValue(helpers.buildLocationCapturePlan({ measurementTrigger: 'manual_refresh' })), {
    trigger: 'manual_refresh',
    strategy: 'watch_window',
    minimumWindowMs: 3000,
    maxWindowMs: 7000,
    targetAccuracyMeters: 30,
  });
  assert.deepStrictEqual(toPlainValue(helpers.buildLocationCapturePlan({ measurementTrigger: 'submit_guard' })), {
    trigger: 'submit_guard',
    strategy: 'watch_window',
    minimumWindowMs: 3000,
    maxWindowMs: 7000,
    targetAccuracyMeters: 30,
  });
  assert.deepStrictEqual(toPlainValue(helpers.buildLocationCapturePlan({ interactive: true })), {
    trigger: 'interactive',
    strategy: 'single_attempt',
    minimumWindowMs: 0,
    maxWindowMs: 0,
    targetAccuracyMeters: 30,
  });
});

test('check location helpers stop lifecycle watches immediately when the configured accuracy is met and keep the enforced minimum window elsewhere', () => {
  let nowMs = 5000;
  const { helpers } = createLocationHelperHarness({
    Date: {
      now: () => nowMs,
    },
  });
  const bestPosition = {
    coords: {
      accuracy: 18,
    },
  };

  assert.equal(helpers.shouldStopLocationWatch(bestPosition, {
    minimumWindowMs: 0,
    targetAccuracyMeters: 20,
  }, 5000), true);
  assert.equal(helpers.shouldStopLocationWatch(bestPosition, {
    minimumWindowMs: 3000,
    targetAccuracyMeters: 20,
  }, 5000), false);

  nowMs = 8000;
  assert.equal(helpers.shouldStopLocationWatch(bestPosition, {
    minimumWindowMs: 3000,
    targetAccuracyMeters: 20,
  }, 5000), true);
  assert.equal(helpers.shouldStopLocationWatch(bestPosition, {
    minimumWindowMs: 0,
    targetAccuracyMeters: null,
  }, 5000), false);
});

test('check location progress shows the current accuracy text and ignores invalid progress samples', () => {
  const presentationCalls = [];
  const { helpers } = createLocationHelperHarness({
    setLocationPresentation: (...args) => presentationCalls.push(args),
  });

  assert.equal(
    helpers.buildLocationCaptureProgressAccuracyText(18.2, { targetAccuracyMeters: 30 }),
    'Precisão atual 18 m / Limite 30 m'
  );
  assert.equal(
    helpers.buildLocationCaptureProgressAccuracyText(18.2, { targetAccuracyMeters: null }),
    'Precisão atual 18 m'
  );

  helpers.updateLocationCaptureProgress(
    {
      coords: {
        accuracy: 18.2,
      },
    },
    { targetAccuracyMeters: 30 },
    { showDetectingState: true }
  );

  assert.deepStrictEqual(toPlainValue(presentationCalls), [[
    'Buscando precisão suficiente...',
    '',
    'info',
    'Precisão atual 18 m / Limite 30 m',
    { suppressNotification: true },
  ]]);

  helpers.updateLocationCaptureProgress(
    {
      coords: {
        accuracy: null,
      },
    },
    { targetAccuracyMeters: 30 },
    { showDetectingState: true }
  );
  helpers.updateLocationCaptureProgress(
    {
      coords: {
        accuracy: 12,
      },
    },
    { targetAccuracyMeters: 30 },
    { showDetectingState: false }
  );

  assert.equal(presentationCalls.length, 1);
});

test('check watched GPS acquisition refreshes progress for each valid sample while keeping the best sample as the timeout fallback', async () => {
  let watchSuccess = null;
  let watchOptions = null;
  let clearedWatchId = null;
  let clearedTimeoutId = null;
  let timeoutCallback = null;
  const presentationCalls = [];
  const measurementEvents = [];
  const measurementSamples = [];
  const { helpers } = createLocationHelperHarness({
    navigator: {
      geolocation: {
        watchPosition(success, _error, options) {
          watchSuccess = success;
          watchOptions = options;
          return 77;
        },
        clearWatch(watchId) {
          clearedWatchId = watchId;
        },
      },
    },
    window: {
      setTimeout(callback, _delayMs) {
        timeoutCallback = callback;
        return 13;
      },
      clearTimeout(timeoutId) {
        clearedTimeoutId = timeoutId;
      },
    },
    setLocationPresentation: (...args) => presentationCalls.push(args),
    recordLocationMeasurementEvent: (_session, eventName, eventPayload) => {
      measurementEvents.push({ eventName, eventPayload });
    },
    recordLocationMeasurementSample: (_session, position) => {
      measurementSamples.push(position);
    },
  });

  const bestPosition = {
    coords: {
      latitude: -23.55,
      longitude: -46.63,
      accuracy: 18,
    },
    timestamp: 100,
  };
  const worsePosition = {
    coords: {
      latitude: -23.55,
      longitude: -46.63,
      accuracy: 42,
    },
    timestamp: 200,
  };
  const pendingPosition = helpers.requestWatchedCurrentPosition(
    {
      minimumWindowMs: 0,
      maxWindowMs: 5000,
      targetAccuracyMeters: 10,
    },
    { session_id: 'phase-3-watch-window' },
    { showDetectingState: true }
  );

  assert.equal(typeof watchSuccess, 'function');
  assert.equal(typeof timeoutCallback, 'function');
  assert.equal(watchOptions.timeout, 5000);

  watchSuccess(bestPosition);
  watchSuccess(worsePosition);

  assert.equal(measurementSamples.length, 2);
  assert.deepStrictEqual(presentationCalls.map((call) => call[3]), [
    'Precisão atual 18 m / Limite 10 m',
    'Precisão atual 42 m / Limite 10 m',
  ]);

  timeoutCallback();
  const resolvedPosition = await pendingPosition;

  assert.equal(resolvedPosition, bestPosition);
  assert.equal(clearedWatchId, 77);
  assert.equal(clearedTimeoutId, 13);
  assert.deepStrictEqual(measurementEvents.map((entry) => entry.eventName), [
    'watch_window_started',
    'watch_window_completed',
  ]);
  assert.deepStrictEqual(toPlainValue(measurementEvents[0].eventPayload), {
    max_window_ms: 5000,
    minimum_window_ms: 0,
    target_accuracy_meters: 10,
  });
  assert.deepStrictEqual(toPlainValue(measurementEvents[1].eventPayload), {
    termination_reason: 'acquisition_window_elapsed',
    best_accuracy_meters: 18,
  });
});

test('check controller keeps lifecycle GPS acquisition wired through the expected settings handoff', () => {
  assert.match(checkScript, /function requestCurrentPositionForPlan\(capturePlan, measurementSession, options\) \{[\s\S]*capturePlan\.strategy !== 'watch_window'[\s\S]*navigator\.geolocation\.watchPosition/);
  assert.match(checkScript, /async function updateLocationForLifecycleSequence\(options\) \{[\s\S]*showDetectingState: settings\.showDetectingState !== false,[\s\S]*\}/);
  assert.match(checkScript, /const locationPayload = await updateLocationForLifecycleSequence\(\{[\s\S]*cacheWindowMs: settings\.locationCacheWindowMs \?\? lifecycleDataReuseWindowMs,[\s\S]*\}\);/);
  assert.match(checkScript, /const position = await requestCurrentPositionForPlan\(capturePlan, measurementSession, \{[\s\S]*showDetectingState: settings\.showDetectingState,[\s\S]*\}\);/);
});

test('check controller keeps visibility, focus and pageshow routed through the shared lifecycle update sequence', () => {
  assert.match(checkScript, /function requestLifecycleUpdateFromUi\(triggerSource\) \{[\s\S]*window\.setTimeout\([\s\S]*runLifecycleUpdateSequence\(\{ triggerSource: nextTriggerSource \}\);/);
  assert.match(checkScript, /document\.addEventListener\('visibilitychange', \(\) => \{[\s\S]*requestLifecycleUpdateFromUi\('visibility'\);/);
  assert.match(checkScript, /window\.addEventListener\('focus', \(\) => \{[\s\S]*requestLifecycleUpdateFromUi\('focus'\);/);
  assert.match(checkScript, /window\.addEventListener\('pageshow', \(\) => \{[\s\S]*requestLifecycleUpdateFromUi\('pageshow'\);/);
});

test('manual refresh should evaluate automatic activities after a changed location during an active check-in', async () => {
  const { helpers } = createManualRefreshSequenceHarness();

  helpers.setLocationPayload({
    matched: true,
    resolved_local: 'Almoxarifado',
    status: 'matched',
  });

  await helpers.runManualLocationRefreshSequence();

  const snapshot = toPlainValue(helpers.getSnapshot());
  assert.equal(snapshot.runWithLockedUserInteraction, 1);
  assert.deepStrictEqual(snapshot.resolveCurrentLocation, [{
    interactive: true,
    forceRefresh: true,
    measurementTrigger: 'manual_refresh',
    showDetectingState: true,
    showCompletionStatus: true,
    suppressNotification: false,
  }]);
  assert.deepStrictEqual(snapshot.runAutomaticActivitiesIfNeeded, [{
    locationPayload: {
      matched: true,
      resolved_local: 'Almoxarifado',
      status: 'matched',
    },
  }]);
});

test('manual refresh forwards the stored mixed zone interval into the automatic engine', async () => {
  const { helpers } = createManualRefreshAutomaticActivityHarness({
    shouldAttemptAutomaticLocationEvent: () => false,
  });

  helpers.setLocationPayload({
    matched: true,
    resolved_local: 'Zona Mista',
    status: 'matched',
  });

  await helpers.runManualLocationRefreshSequence();

  const snapshot = toPlainValue(helpers.getSnapshot());
  assert.equal(snapshot.runWithLockedUserInteraction, 1);
  assert.deepStrictEqual(snapshot.resolveCurrentLocation, [{
    interactive: true,
    forceRefresh: true,
    measurementTrigger: 'manual_refresh',
    showDetectingState: true,
    showCompletionStatus: true,
    suppressNotification: false,
  }]);
  assert.deepStrictEqual(snapshot.fetchWebState, ['A123']);
  assert.deepStrictEqual(snapshot.shouldAttemptAutomaticLocationEvent, [{
    locationPayload: {
      matched: true,
      resolved_local: 'Zona Mista',
      status: 'matched',
    },
    remoteState: {
      current_action: 'checkout',
      current_local: 'Zona de CheckOut',
      last_checkin_at: '2026-04-16T08:00:00',
      last_checkout_at: '2026-04-16T09:00:00',
    },
    settings: {
      mixedZoneIntervalMinutes: 35,
    },
  }]);
  assert.deepStrictEqual(snapshot.submitAutomaticActivity, []);
});

test('manual refresh should submit an automatic location update after an active check-in moves to another known location', async () => {
  const { helpers } = createManualRefreshAutomaticActivityHarness({
    remoteState: {
      current_action: 'checkin',
      current_local: 'Recepção',
      last_checkin_at: '2026-04-16T09:00:00',
      last_checkout_at: '2026-04-16T08:00:00',
    },
  });

  helpers.setLocationPayload({
    matched: true,
    resolved_local: 'Almoxarifado',
    status: 'matched',
  });

  await helpers.runManualLocationRefreshSequence();

  const snapshot = toPlainValue(helpers.getSnapshot());
  assert.equal(snapshot.runWithLockedUserInteraction, 1);
  assert.deepStrictEqual(snapshot.fetchWebState, ['A123']);
  assert.deepStrictEqual(snapshot.submitAutomaticActivity, [{
    action: 'checkin',
    local: 'Almoxarifado',
  }]);
});

test('manual refresh should submit automatic check-in after checkout when leaving checkout zone for a known location', async () => {
  const { helpers } = createManualRefreshAutomaticActivityHarness();

  helpers.setLocationPayload({
    matched: true,
    resolved_local: 'Escritório Principal',
    status: 'matched',
  });

  await helpers.runManualLocationRefreshSequence();

  const snapshot = toPlainValue(helpers.getSnapshot());
  assert.equal(snapshot.runWithLockedUserInteraction, 1);
  assert.deepStrictEqual(snapshot.fetchWebState, ['A123']);
  assert.deepStrictEqual(snapshot.submitAutomaticActivity, [{
    action: 'checkin',
    local: 'Escritório Principal',
  }]);
});

test('manual refresh should submit automatic check-in after checkout when leaving checkout zone for a nearby unregistered location', async () => {
  const { helpers } = createManualRefreshAutomaticActivityHarness();

  helpers.setLocationPayload({
    matched: false,
    status: 'not_in_known_location',
    label: 'Localização não Cadastrada',
    nearest_workplace_distance_meters: 180,
  });

  await helpers.runManualLocationRefreshSequence();

  const snapshot = toPlainValue(helpers.getSnapshot());
  assert.equal(snapshot.runWithLockedUserInteraction, 1);
  assert.deepStrictEqual(snapshot.submitAutomaticActivity, [{
    action: 'checkin',
    local: 'Localização não Cadastrada',
  }]);
});

test('manual refresh should not submit automatic activity after checkout when the location remains checkout zone', async () => {
  const { helpers } = createManualRefreshAutomaticActivityHarness();

  helpers.setLocationPayload({
    matched: true,
    resolved_local: 'Zona de CheckOut',
    status: 'matched',
  });

  await helpers.runManualLocationRefreshSequence();

  const snapshot = toPlainValue(helpers.getSnapshot());
  assert.equal(snapshot.runWithLockedUserInteraction, 1);
  assert.deepStrictEqual(snapshot.submitAutomaticActivity, []);
});

test('manual refresh should not start a refresh sequence when the application is locked', async () => {
  const { helpers } = createManualRefreshSequenceHarness({
    isApplicationUnlocked: () => false,
  });

  helpers.setLocationPayload({
    matched: true,
    resolved_local: 'Escritório Principal',
    status: 'matched',
  });

  await helpers.runManualLocationRefreshSequence();

  const snapshot = toPlainValue(helpers.getSnapshot());
  assert.equal(snapshot.runWithLockedUserInteraction, 0);
  assert.deepStrictEqual(snapshot.resolveCurrentLocation, []);
  assert.deepStrictEqual(snapshot.runAutomaticActivitiesIfNeeded, []);
});

test('manual refresh should not submit automatic activity when automatic activities are disabled', async () => {
  const { helpers } = createManualRefreshAutomaticActivityHarness({
    isAutomaticActivitiesEnabled: () => false,
  });

  helpers.setLocationPayload({
    matched: true,
    resolved_local: 'Escritório Principal',
    status: 'matched',
  });

  await helpers.runManualLocationRefreshSequence();

  const snapshot = toPlainValue(helpers.getSnapshot());
  assert.equal(snapshot.runWithLockedUserInteraction, 1);
  assert.equal(snapshot.resolveCurrentLocation.length, 1);
  assert.deepStrictEqual(snapshot.fetchWebState, []);
  assert.deepStrictEqual(snapshot.submitAutomaticActivity, []);
});

test('manual refresh should not submit automatic activity when the key is invalid', async () => {
  const { helpers } = createManualRefreshAutomaticActivityHarness({
    chave: 'A1',
  });

  helpers.setLocationPayload({
    matched: true,
    resolved_local: 'Escritório Principal',
    status: 'matched',
  });

  await helpers.runManualLocationRefreshSequence();

  const snapshot = toPlainValue(helpers.getSnapshot());
  assert.equal(snapshot.runWithLockedUserInteraction, 1);
  assert.equal(snapshot.resolveCurrentLocation.length, 1);
  assert.deepStrictEqual(snapshot.fetchWebState, []);
  assert.deepStrictEqual(snapshot.submitAutomaticActivity, []);
});

test('manual refresh should not submit automatic activity after checkout when backend reports outside workplace', async () => {
  const { helpers } = createManualRefreshAutomaticActivityHarness();

  helpers.setLocationPayload({
    matched: false,
    status: 'outside_workplace',
    minimum_checkout_distance_meters: 2500,
  });

  await helpers.runManualLocationRefreshSequence();

  const snapshot = toPlainValue(helpers.getSnapshot());
  assert.equal(snapshot.runWithLockedUserInteraction, 1);
  assert.deepStrictEqual(snapshot.submitAutomaticActivity, []);
});