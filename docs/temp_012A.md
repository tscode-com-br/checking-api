# Executable Prompt Pack for Implementing the Samsung S21 Checking Web Fix

## How to use this document

This file turns the plan in `docs/temp_012.md` into a sequence of implementation prompts for another AI agent.

Execution rules:

1. Run the phases in order.
2. Do not skip the diagnosis phase.
3. Treat the Samsung vertical scroll failure as the highest-priority symptom until disproven.
4. Do not assume the `max-width: 360px` breakpoint is the only root cause.
5. Do not use device-specific hacks, user-agent detection, or browser-specific branching unless there is hard evidence that a standards-based fix is impossible.
6. Preserve the approved iPhone 14 Pro behavior.
7. Prefer the smallest correct change that solves the problem at the root.
8. After each implementation phase, run the narrowest validation available before widening scope.
9. If a hypothesis fails, step one layer closer to the code that directly controls the behavior instead of reopening broad exploration.
10. For every phase, provide: files inspected, hypothesis, code changes, validation performed, result, and rollback note.

Primary implementation surface:

- `sistema/app/static/check/index.html`
- `sistema/app/static/check/styles.css`
- `sistema/app/static/check/app.js`

Likely supporting test surface:

- `tests/check_responsive_layout.test.js`
- `tests/check_transport_layout.test.js`
- `tests/check_auth_transport_ui.test.js`
- `tests/check_automatic_activities_layout.test.js`
- `tests/check_user_location_ui.test.js`
- `tests/check_history_latest_activity_ui.test.js`
- `tests/check_registration_widget.test.js`
- `tests/check_portrait_lock.test.js`

Baseline problem statement:

The `Checking Web` screen looks correct on iPhone 14 Pro but behaves differently on Samsung Galaxy S21 Chrome. Two symptoms must be investigated separately:

1. The Samsung layout appears to fall into a more stacked mobile variant.
2. The more severe issue is that the Samsung user reportedly could not scroll vertically to reach the rest of the screen.

The agent must first prove whether the root problem is scroll lock, an overly aggressive `360px` responsive breakpoint, or both.

## Phase 0 - Baseline Reproduction and Root-Cause Separation

### Phase context

Goal: establish whether the Samsung problem is primarily a scroll failure, a responsive breakpoint variant, or a combination of both.

Completion criteria: there is a concrete evidence-based answer about what is actually broken and where it is controlled.

Rollback criteria: not applicable, because this phase should be investigation-first and should not make functional changes unless a tiny reversible probe is necessary.

### Prompt 0.1 - Compare the screenshots against the current responsive contract

You are the agent responsible for separating visual variance from functional failure in the `Checking Web` UI. Work in `sistema/app/static/check/index.html`, `sistema/app/static/check/styles.css`, and `sistema/app/static/check/app.js`. Treat the attached iPhone screenshot as the approved baseline and the Samsung Galaxy S21 screenshot as the problematic case.

Your first task is diagnostic only. Do not change code yet unless you need a tiny reversible probe to expose the controlling behavior.

You must:

1. Compare the two screenshots and list the concrete differences visible above the fold.
2. Distinguish which differences could be explained by responsive layout and which could be explained by stateful UI behavior.
3. Inspect the `@media (max-width: 480px)` and `@media (max-width: 360px)` sections in `styles.css` and identify which selectors directly change the Samsung-visible composition.
4. Inspect `app.js` to determine whether `Projeto`, `Local`, `Informe`, or `Atividades Automáticas` can be hidden because of application state rather than viewport width.
5. Produce a compact matrix in this format:
   - `symptom -> screenshot evidence -> likely controlling selector/function -> confidence`
6. State one falsifiable local hypothesis for the visual variance.
7. State one separate falsifiable local hypothesis for the reported vertical scroll failure.

Do not propose browser setting changes. Do not conclude that the `360px` breakpoint is the entire root cause unless you can also explain the scroll report.

Expected output:

1. A bullet list of concrete screenshot differences.
2. A bullet list separating `state-driven differences` from `layout-driven differences`.
3. A short `primary visual hypothesis`.
4. A short `primary scroll hypothesis`.

### Prompt 0.2 - Reproduce viewport metrics and scroll contract behavior

You are the agent responsible for reproducing the Samsung/iPhone responsive and scroll behavior with concrete viewport evidence. Work from the same `Checking Web` implementation surface and gather only the evidence needed to determine what controls the defect.

Your job is to inspect the root scroll contract and responsive conditions before any substantive edit.

You must collect, for at least these simulated viewports, the live DOM and computed-style evidence if the route can be loaded locally, or static code evidence if not:

- `360 x 800` or equivalent for Samsung Galaxy S21 portrait
- `393 x 852` or equivalent for iPhone 14 Pro portrait
- `320 x 700` or equivalent for truly narrow fallback

For each viewport, inspect or infer:

1. `window.innerWidth`
2. `window.innerHeight`
3. `visualViewport.width`
4. `visualViewport.height`
5. `document.documentElement.scrollHeight`
6. `document.documentElement.clientHeight`
7. `document.body.scrollHeight`
8. `document.body.clientHeight`
9. computed `overflow-x` and `overflow-y` for `html`, `body`, `.check-shell`, and `.check-card`
10. computed `touch-action` for `body` and the main interactive surfaces
11. computed `overscroll-behavior` for `html` and `body`
12. whether the Samsung-equivalent viewport actually falls into the `max-width: 360px` rules

If the issue cannot be faithfully reproduced in desktop emulation, say so explicitly and keep the result framed as `partial evidence` rather than certainty.

Expected output:

1. A table of viewport metrics.
2. A table of computed scroll/overflow/touch contract values.
3. A clear answer to: `Is the root page structurally scrollable according to the current contract?`
4. A clear answer to: `Does the Samsung-equivalent viewport enter the 360px stacked layout variant?`

## Phase 1 - Fix the Vertical Scroll Failure First

### Phase context

Goal: make sure the main `/user` screen can always scroll vertically when content extends below the visible fold.

Completion criteria: the main page is no longer perceived as locked and the user can reach all lower controls on Samsung-equivalent portrait viewports.

Rollback criteria: revert only the scroll-contract change if it introduces a new blocker such as horizontal overflow, broken overlays, or iPhone regression.

### Prompt 1.1 - Implement the smallest root-cause fix for the main page scroll contract

You are the agent responsible for fixing the vertical scroll problem in the `Checking Web` main screen. Your highest priority is to restore reliable vertical scrolling in the root page without regressing the approved iPhone behavior.

Work primarily in:

- `sistema/app/static/check/styles.css`
- `sistema/app/static/check/app.js`

Use the evidence from Phase 0. Do not broaden scope unnecessarily. Do not redesign the page. Do not start by changing the `360px` breakpoint unless the evidence proves that the scroll defect is actually caused by that breakpoint.

Investigate and correct, in the smallest defensible way, the scroll contract across:

1. `html`
2. `body`
3. `.check-shell`
4. `.check-card`
5. any invisible backdrop or fixed overlay that might still capture pointer interaction after closing
6. any root-level `touch-action` or `overscroll-behavior` choice that may interfere with Android Chrome scroll behavior
7. the viewport-height/header-height CSS variable contract if the measured height is producing a false full-screen layout that prevents natural page scrolling

Constraints:

1. Keep the fix standards-based and device-agnostic.
2. Do not introduce user-agent detection.
3. Do not remove dynamic viewport synchronization unless it is directly implicated and you can replace it with a safer contract.
4. Preserve dialog and transport overlay behavior.
5. Preserve horizontal containment.

Required implementation behavior:

1. The root page must scroll vertically when content exceeds the visible viewport.
2. The fix must not leave hidden overlays or backdrops intercepting scroll.
3. The fix must not turn the page into a horizontally scrollable layout.

After your first substantive edit, immediately run the narrowest validation available for the touched slice.

Expected output:

1. The root-cause explanation of the scroll defect.
2. The exact files and rules changed.
3. The first focused validation result.
4. A short rollback note.

### Prompt 1.2 - Validate that the scroll fix works without reopening scope

You are the agent responsible for validating the just-applied `Checking Web` scroll fix before any visual refinement work begins.

Do not widen scope yet. Validate only whether the main page now scrolls correctly and whether the fix caused immediate regressions.

You must verify, at minimum:

1. the root page remains vertically scrollable in a Samsung-equivalent viewport
2. the root page does not gain horizontal overflow
3. dialogs can still open and close normally
4. the transport overlay can still open and close normally
5. the viewport/header CSS-variable synchronization still updates when the viewport changes

Prefer the narrowest executable validation available. If no live route is available, use the tightest test or DOM contract validation you can run from the repo.

Expected output:

1. `validated behavior`
2. `remaining ambiguity`
3. `go/no-go for visual refinement phase`

## Phase 2 - Refine the 360px Visual Variant Only If Still Needed

### Phase context

Goal: only after scroll is correct, decide whether the Samsung `360px` presentation still needs responsive refinement.

Completion criteria: the Samsung-equivalent viewport is visually acceptable without regressing iPhone or very narrow fallback behavior.

Rollback criteria: revert only the responsive visual adjustments if they degrade iPhone, narrow mobile fallback, or form usability.

### Prompt 2.1 - Decide whether the visual variant still requires code changes

You are the agent responsible for deciding whether the Samsung visual variance still needs a responsive CSS change after the scroll fix has been validated.

Do not assume that a different composition at `360px` is automatically a bug. Compare the post-fix Samsung-equivalent viewport against the product baseline and determine whether the remaining difference is:

1. acceptable compact mobile behavior
2. a still-problematic overly aggressive stacked variant
3. partially acceptable but worth refining

Your decision must explicitly evaluate:

1. `.history-grid`
2. `.auth-credentials-row`
3. `.choice-grid.two-columns`
4. spacing and compactness above the fold
5. whether users can see enough meaningful controls before scrolling

Expected output:

1. `visual verdict after scroll fix`
2. `selectors still worth refining, if any`
3. `whether the 360px breakpoint should remain unchanged, be softened, or be split into subranges`

### Prompt 2.2 - Implement the smallest safe responsive refinement for the Samsung-equivalent width range

You are the agent responsible for making a minimal responsive refinement only if Phase 2.1 concluded that the Samsung-equivalent `360px` layout is still too aggressive.

Work in `sistema/app/static/check/styles.css` first. Only touch JavaScript if there is hard evidence that CSS alone cannot express the needed behavior.

Your task is to reduce unnecessary structural collapse in the `360px` range while preserving:

1. the approved iPhone 14 Pro layout
2. the newly fixed vertical scrolling behavior
3. safe fallback for truly narrow widths such as `320px`

Potential targets include, but are not limited to:

1. keeping `.history-grid` in two columns when still legible
2. keeping `.auth-credentials-row` compact without fully collapsing to one column
3. delaying the full one-column collapse to a narrower threshold only if validation supports that move
4. reducing gaps and paddings before collapsing structure

Constraints:

1. no device-specific targeting
2. no iPhone regression
3. no desktop redesign
4. no unrelated visual changes

After the first substantive edit, immediately run a narrow validation for the touched responsive slice.

Expected output:

1. The exact responsive rule change made.
2. Why that change is safer than a broader redesign.
3. Validation result for `360px`, `393px`, and a narrower fallback viewport.

## Phase 3 - Audit Adjacent Surfaces for Regressions

### Phase context

Goal: ensure that the scroll fix and any responsive refinements do not break neighboring mobile surfaces.

Completion criteria: dialogs, transport overlay, landscape layout, keyboard behavior, and containment rules remain correct.

Rollback criteria: revert only the regression-causing subset if any of these adjacent surfaces break.

### Prompt 3.1 - Harden adjacent mobile surfaces after the main-page fix

You are the agent responsible for auditing nearby mobile surfaces after the `Checking Web` main-page fix. Focus on preventing hidden regressions, not on widening product scope.

Inspect and validate, at minimum:

1. password dialog open/close behavior
2. registration dialog open/close behavior
3. transport overlay open/close behavior
4. low-height landscape responsive block
5. keyboard focus behavior on `Chave` and `Senha`
6. horizontal overflow prevention in the root page and transport lists
7. any overlay residual state after close

Files to inspect first:

- `sistema/app/static/check/styles.css`
- `sistema/app/static/check/app.js`
- `tests/check_transport_layout.test.js`
- `tests/check_auth_transport_ui.test.js`
- `tests/check_registration_widget.test.js`
- `tests/check_portrait_lock.test.js`

If you find a regression directly caused by the scroll or responsive fix, repair that same slice immediately and revalidate before continuing.

Expected output:

1. `adjacent surface audit findings`
2. `repairs made, if any`
3. `revalidation results`

## Phase 4 - Update and Strengthen the Automated Tests

### Phase context

Goal: make the Samsung bug reproducible as a regression in the automated suite so the fix does not silently decay.

Completion criteria: the suite protects both the root scroll contract and any accepted responsive breakpoint changes.

Rollback criteria: revert only brittle or incorrect new assertions if they prove unstable, while keeping meaningful regression coverage.

### Prompt 4.1 - Add regression coverage for the root page scroll contract

You are the agent responsible for updating the automated tests so that the Samsung root-page scroll defect cannot be reintroduced silently.

Start with `tests/check_responsive_layout.test.js`, then inspect whether related assertions belong in adjacent `Checking Web` UI tests.

Your new or updated tests must cover, at minimum:

1. `html` still declares vertical scrolling support
2. `body` still declares vertical scrolling support
3. `.check-shell` is not turned into a fixed scroll blocker
4. no new global JavaScript scroll lock contract was introduced in `app.js`
5. the dynamic viewport/header-height contract remains present

If the final fix adjusted `touch-action` or `overscroll-behavior`, encode that intended contract in the tests as well.

Do not add vague tests. Add assertions that are directly tied to the implemented contract.

Expected output:

1. Which test files changed.
2. What new contract each test now protects.
3. The narrow test command run and its result.

### Prompt 4.2 - Add regression coverage for any accepted 360px responsive refinement

You are the agent responsible for protecting the final accepted responsive behavior for the Samsung-equivalent width range.

Only run this prompt if the implementation actually changed the `360px` visual behavior.

Update the tests so that:

1. the accepted Samsung-equivalent layout behavior is captured explicitly
2. the iPhone-approved higher-width mobile behavior remains protected
3. truly narrow fallback behavior can still collapse if that remains the intended design

Be precise. If the solution introduced a new structural breakpoint threshold, encode that threshold in the tests so future edits cannot accidentally revert the Samsung fix.

Expected output:

1. The new responsive contract encoded in tests.
2. The test command run.
3. Test results.

## Phase 5 - Manual Validation and Evidence Capture

### Phase context

Goal: validate the fix against the original Samsung complaint and confirm that the iPhone baseline remains intact.

Completion criteria: there is concrete evidence that the user can scroll the Samsung-equivalent screen and that the visual result is acceptable without iPhone regression.

Rollback criteria: if manual validation contradicts the implementation hypothesis, stop broad edits, document the contradiction, and step back to the nearest controlling layer.

### Prompt 5.1 - Perform focused manual validation of the final behavior

You are the agent responsible for the final manual validation of the `Checking Web` Samsung fix.

Validate the final result against three viewports or device classes:

1. Samsung Galaxy S21-equivalent portrait
2. iPhone 14 Pro-equivalent portrait
3. a truly narrow mobile fallback around `320px`

You must confirm, at minimum:

1. vertical scrolling works on the Samsung-equivalent screen
2. the user can reach lower controls such as `Atividades Automáticas`, `Registro`, action buttons, and the submit area
3. there is no invisible layer blocking touch or scroll
4. there is no horizontal overflow
5. the `Chave / Senha / button` row is visually coherent for the available width
6. the `Registrar` button remains visible, legible, and usable
7. keyboard interaction does not break the viewport contract
8. dialogs and transport overlay still behave correctly
9. the iPhone-equivalent layout remains aligned with the approved baseline

If you cannot validate on a real Android device in this environment, explicitly mark the result as `desktop/emulation validation only` and list the exact open questions that still require real-device confirmation.

Expected output:

1. A final validation checklist with pass/fail per item.
2. A short note on any remaining real-device uncertainty.
3. A concise recommendation: `ready`, `ready with caution`, or `not ready`.

## Phase 6 - Final Consolidation and Handoff

### Phase context

Goal: leave the implementation in a state that is easy to review, validate, and execute phase by phase.

Completion criteria: all code changes, tests, and validation notes are summarized clearly enough for review or rollout.

Rollback criteria: not applicable beyond the rollback notes already captured in each phase.

### Prompt 6.1 - Produce the final implementation report

You are the agent responsible for the final implementation report for the `Checking Web` Samsung fix.

Produce a concise but technically explicit report containing:

1. root cause found
2. whether the actual defect was scroll lock, aggressive breakpoint behavior, or both
3. exact files changed
4. exact tests changed
5. validation commands run
6. validation results
7. residual risks, if any
8. whether further real-device Samsung confirmation is still required

The report must make it easy for a reviewer to answer these questions quickly:

1. What was actually wrong?
2. Why is this the smallest correct fix?
3. Why does it not regress iPhone?
4. What protects this from regressing again?

Expected output:

1. Final implementation summary.
2. Final validation summary.
3. Residual risk summary.

## Final acceptance rule for the whole prompt pack

Do not declare this work complete unless all of the following are true:

1. There is evidence-based clarity on whether the Samsung defect was scroll lock, overly aggressive responsive collapse, or both.
2. The Samsung-equivalent viewport no longer traps the user above the fold.
3. The iPhone-equivalent viewport remains aligned with the approved layout.
4. Truly narrow fallback behavior still exists when necessary.
5. Dialogs, transport overlay, landscape behavior, and dynamic viewport handling still work.
6. Automated tests now protect the accepted contract.
7. Manual or emulated validation was documented with explicit limitations.