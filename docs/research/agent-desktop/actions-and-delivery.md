---
okf_version: "0.2"
type: "report"
title: "agent-desktop ref actions and delivery tracking"
description: "Action chains, read-back verification and what delivered_verified proves, from source."
resource: "https://github.com/vercel-labs/agent-desktop"
version: "1.1.0"
timestamp: "2026-11-03T22:00:00Z"
status: "draft"
stale_after: "2026-12-03T00:00:00Z"
tags: [agent-desktop, macos, accessibility, clion, jetbrains, mcp]
---

# agent-desktop: ref actions, delivery tracking, headless vs headed

> **Status: source reading before the live trials (2026-11-03).** Where this page predicts live behaviour, [results](results.md) wins. In particular: headless `press --app` is blind and is not to be used; the frontmost need comes from `DaemonCodeAnalyzerImpl.isInActiveProject` when two or more projects are open.

Source: vercel-labs/agent-desktop, main 6660fba (installed binary is v1.1.0 = d3dc190; main = v1.1.0 + 5 commits).
Paths are relative to the repo root. Tags: [code] read in source, [inferred] reasoning from code, [docs] not checked in this pass (docs pages, probes, FINDINGS were NOT read). No live commands were run; `agent-desktop --help` via the mise shim fails here ("No version is set for shim"), so CLI flag text is unverified.

## 1. Version differences (v1.1.0 vs main)
- `git diff v1.1.0 HEAD -- crates/macos/src/actions` touches only ax_perform.rs, chain/activate_descendant.rs, select/container_select.rs (commit 8b7fa26f, #503, "select list rows that only their container can select"). It also adds tree/properties/selection_owner.rs and selection_verdicts.rs and edits action_list.rs [code].
- Consequence: the container-selection logic (a row advertises Click when a container within 2 ancestors owns settable AXSelectedRows/Children/Cells) is main-only. The v1.1.0 binary may advertise Click on tree rows differently, and its select_within_container is the older version [inferred; v1.1.0 side not read]. Re-test on a main build before concluding.
- `mcp` command (6660fba) is new on main and not in v1.1.0; not read.

## 2. Flow of one ref action
1. CLI builds an Action; `CommandContext::request(action, base)` joins `Action::base_interaction_policy` (crates/core/src/actions/action.rs ~166: PressKey = focus_fallback, everything else headless) with the `--headed` option policy (context/mod.rs ~108-130, 215-233) [code].
2. Actionability gates (crates/core/src/actionability/gates.rs:150-203) [code]:
   - Click/RightClick pass only with a directly advertised Click/RightClick, or a headed policy; else PolicyDenied.
   - DoubleClick/TripleClick need headed.
   - Other actions need the capability from capability.rs (Select = Select|Click; Toggle/Check/Uncheck = Toggle|Click; SetValue/Clear = SetValue; Expand/Collapse/Scroll/ScrollTo/TypeText/PressKey map 1:1). Missing capability gives ActionNotSupported ("X is not available"). Focus fallback is allowed only for TypeText and PressKey.
3. Pointer delivery (actionability/requirements.rs:41-56, pointer_delivery.rs): NotApplicable / Physical (headed + cursor action) / Semantic (Click or RightClick on an element advertising exactly Click/RightClick) / otherwise Physical. ref_action/mod.rs:123-128 resets the policy to headless when delivery is Semantic [code].
4. Headed focus: ref_action_single.rs:26-38 calls `headed_focus::focus_entry_window` (adapter.focus_window, exact window id + process instance) first when the request has a HeadedRequirement. Keyboard actions skip it if `!adapter.keyboard_needs_window_activation()` (default true) [code].
5. Preflight (ref_action/mod.rs:62-167): resolve saved ref, stable preflight, may scroll the ref into view and retry, attach verified point, run cursor-overlay hooks [code].
6. macOS dispatch `perform_action` (crates/macos/src/actions/dispatch.rs:16-203) routes per Action to a chain or helper (section 4) [code].
7. Core post-state check `execute_verified_action` (crates/core/src/actions/post_action.rs:7-139), only for SetValue, Clear, TypeText, Check, Uncheck, Toggle, Expand, Collapse: poll live element up to 400 ms (50 ms settle) for the postcondition; verified -> `verification_scope`; unverifiable -> `verification_reason` (insufficient_evidence/secure_field/postcondition_mismatch); mismatch -> error "Post-action state does not match the requested change". Click, Select, Scroll, Focus get NO core readback [code].

HeadedRequirement (headed_requirement.rs): FocusedWindowAndCursor = Click, DoubleClick, RightClick, TripleClick, Scroll, Hover, Drag. FocusedWindow = SetValue, SetFocus, Expand, Collapse, Select, Toggle, Check, Uncheck, ScrollTo, PressKey, KeyDown, KeyUp, TypeText, Clear. `ActionRequest::headed_requirement()` is None unless the policy is headed [code].

## 3. Delivery vocabulary
- Chain `DeliveryOutcome` (chain/chain_delivery.rs): NotDelivered, SatisfiedNoDelivery, DeliveredUnverified, DeliveredWithoutEffect, DeliveredVerified. Only NotDelivered and DeliveredWithoutEffect let the chain continue to the next step [code].
- Result-level `DeliverySemantics` (core delivery_semantics.rs): Unknown, NotDelivered (retry safe), DeliveryUncertain, DeliveredUnverified, DeliveredVerified (unsafe to retry). `DeliveryTracker` upgrades NotDelivered/Unknown errors to delivered_unverified once any unit was delivered [code].
- Chain engine (chain/mod.rs:17-137): iterates steps, skips ones not allowed by policy (CGClick and FocusThenClearByKeyboard need `is_headed()`), stops at the first terminating outcome. Exhaustion = ActionFailed "All chain steps exhausted" plus the chain's suggestion; disposition delivered_unverified if any step succeeded, else not_delivered [code].
- AX perform (actions/ax_perform.rs:16-61): if `advertises_action(el,name) == Some(false)` returns NotDelivered WITHOUT performing (unadvertised actions are never tried). Else snapshots `activation_effect::focus_state`, calls AXUIElementPerformAction, classifies the code (ax_mutation.rs:28-104): Success -> delivered; ActionUnsupported/NotImplemented -> NotDelivered; AttributeUnsupported/NoValue -> uninformative (settle poll 40 ms step, 400 ms budget, else DeliveryUncertain); Failure/CannotComplete -> uncertain error; APIDisabled -> PermDenied; InvalidUIElement -> StaleRef. Success becomes `from_delivery(true, changed_now(before, el))`: DeliveredVerified only if an effect is seen, else DeliveredUnverified [code].
- Effect definition (activation_effect.rs): app AXFocusedUIElement moved to the target (walks up to 3 AXParents), OR target AXSelected went false->true, OR menu_open false->true for menu roles, OR focus/focused value changed within the target window [code].

## 4. Per-action chains (order matters)
| Action | Headless order | Added/changed when headed |
|---|---|---|
| click | Role probe only when headed (AXMenuBarItem non-status-item -> AXPress only). CLICK_CHAIN (chain_defs.rs:12-35): (1 CGClick, headed only) 2 `press_or_report_no_effect` = AXPress; 3 AXOpen; 4 `activate_descendant` (up to 4 AXChildren, AXPress/AXOpen/AXConfirm each; skipped when `selects_only_through_container`); 5 `select_within_container`; 6 AXConfirm. Each AX action is skipped if not advertised. | CGClick first: click_via_bounds -> window raised, hit test, CGEvent at element centre. DeliveredUnverified. |
| double/triple click | Not possible (policy-gated). | Physical only (`click_via_bounds`, chain_defs.rs:158-195). |
| right-click | RIGHT_CLICK_CHAIN (continue_after_unverified_delivery): show_menu (AXShowMenu), select_then_show_menu, selected_items_menu, child_show_menu, ancestor_show_menu (chain_menu_steps.rs, not read in detail) | CGClick right button first. |
| expand / collapse | Single step `set_disclosure` (chain_disclosure_steps.rs:22-67): read state AXExpanded -> AXDisclosing -> AXValue (disclosure triangle only); already desired -> SatisfiedNoDelivery. Then AXExpand/AXCollapse (if advertised) + verify 200 ms; then set AXExpanded (if settable) + verify; then AXPress only if the state is KNOWN to be the opposite. Else NotDelivered -> ActionFailed "Target a control with a readable expandable state". | No difference. A unit test (chain_defs.rs:197-213) asserts there is no physical fallback for expand/collapse. |
| set-value | SET_VALUE_CHAIN: SetDynamic AXValue (settable check, `set_dynamic_verified`; value coerced to number/bool/string by current type, ax_helpers.rs:123-189), then IncrementToDynamic (AXIncrement/AXDecrement). Core readback follows. | Same. |
| clear | CLEAR_CHAIN: FocusThenClearByKeyboard (headed only) then SetDynamic AXValue "" | Cmd+A, Delete first (press_sequence). |
| focus (SetFocus) | FOCUS_CHAIN: SetBool AXFocused=true; if AXFocused not settable -> NotDelivered, exhausted ("Target an element whose AXFocused attribute is settable"). Verified readback. | Same. |
| select | extras.rs `select_value`: combobox: write AXValue if settable (600 ms verify) else `select_from_menu`; popupbutton/menubutton: `select_from_menu`; list/table/outline: `select_collection_item` (select_menu.rs/select_name.rs, not read); other roles: ActionNotSupported. | Same. |
| toggle/check/uncheck | toggle_state.rs, toggle_state_radio.rs (not read) | - |
| scroll | scroll.rs:9-50 headless: find scroll area (<=5 ancestors); (1) AXVerticalScrollBar/AXHorizontalScrollBar AXIncrement/AXDecrement x amount (bar must advertise); (2) AXValue += 0.1*amount, clamped, readback; (3) AXPress on AXIncrementPage/Arrow subrole children; (4) AXScrollDownByPage etc. on target; (5) ActionNotSupported kind `scroll_advertised_but_inert`. Max amount 1000. | Physical wheel (`physical_wheel`), unverified. |
| scroll-to | SCROLL_TO_CHAIN: AXScrollToVisible (scroll_into_view.rs, not read) | - |
| type | role must be AXTextField/TextArea/SecureTextField/ComboBox; write AXSelectedText via `set_ax_string_or_err`, unverified by adapter; core compares resulting value. | `physical_keyboard::type_text`: PID-targeted unicode keys. |
| press (on ref) | physical_keyboard `prepare_target` requires allow_focus_steal; checks window AXMain and app AXFrontmost (`verify_app_focused` only checks, does not raise); sets AXFocused on element, waits <=500 ms; `synthesize_key(combo, Some(pid))`. | - |
| press (top level, `commands/press.rs`) | With --app/--window-id and headed: focus window first, then keys. Else `press_key_for_app`/`press_key_for_window`. macOS `press_for_app` (system/key_dispatch.rs:22-66): (a) if allow_focus_steal and modifiers: try menu-bar shortcut via AXPress on menu item; (b) bare return/enter -> AXConfirm, escape -> AXCancel on the focused element if advertised; (c) else requires a focused element (AXFocusedUIElement, 500 ms) and posts CGEventPostToPid; `verify_app_focused` only when allow_focus_steal. No app: global `synthesize_key(None)`. | - |
| hover, drag, key-down/up | Return ActionNotSupported "requires adapter-level handling" from dispatch.rs; handled elsewhere. | - |

How availability is computed (macos/src/tree/properties/action_list.rs:40-123) [code]: AXPress/AXOpen/AXConfirm -> Click; toggle roles -> Toggle; row/treeitem/cell/listitem/option/tab with settable own AXSelected, or a container (<=2 ancestors, selection_owner.rs) with settable AXSelectedRows/Children/Cells -> Click (main only); AXShowMenu -> RightClick; AXScrollToVisible -> ScrollTo; any AXScroll*ByPage or `has_scrollbars` -> Scroll; settable AXValue or AXIncrement/Decrement -> SetValue; settable AXFocused -> SetFocus; textfield/combobox with settable AXSelectedText -> TypeText; settable AXExpanded (or AXPress on an expandable role) -> Expand/Collapse.

## 5. Headless vs headed decision
- Per action, from policy only: `--headed` sets focus-steal + cursor-move true (`with_headed`); otherwise headless. PressKey alone defaults to focus_fallback (focus true, cursor false) [code].
- Headed makes cursor actions Physical (CGEvent at element centre after hit test and a window raise); headless forces semantic AX delivery. A Click on an element that advertises Click is Semantic and the policy is reset to headless even if --headed was passed ONLY when the pointer-delivery gate selects Semantic; in the gate order, headed + cursor-requiring action yields Physical first (requirements.rs:41-56) [code; read the gate once more before relying on this].
- Physical click requires AXFrontmost app and AXMain window (`PreparedPhysicalTarget::prepare` verify_focus), aborts when the hit test shows an occluder (physical_click.rs, physical_target.rs). `focus_window_impl` (system/focus.rs) sets AXFrontmost=true, raises the window, verifies: this is the ~0.6 s `focus-window` [code].
- Expand/collapse, set-focus, set-value, select, toggle are "FocusedWindow" actions when headed: the window is raised first, but their semantic chains are unchanged (no physical fallback) [code].

## 6. Why delivered_verified with no visible effect
1. `press_or_report_no_effect` (chain/press_selection.rs:12-79): after a DeliveredUnverified AXPress on a selection role, it reads AXSelected (poll <=300 ms, 25 ms) and returns immediately when the value is not false. Some(true) -> DeliveredVerified. There is no comparison with the pre-press state. A row that already reports AXSelected=true is "verified" whatever the press did [code]. The observed "every tree item reports selected" matches exactly [inferred link].
2. `select_within_container` (container_select.rs:70-124): writes AXSelected (own) or the container's AXSelectedRows/Children/Cells and reads back "contains member". Re-selecting an already selected item is trivially verified; and it changes the AX model, not necessarily the Swing action handler [code + inferred].
3. `perform_observed_action`: the effect test counts AXFocusedUIElement/AXSelected changes, which says nothing about app-level work such as CLion starting analysis [code].
4. Click has no core-level readback (section 2.7). The label "verified" means "the AX selection/focus read-back looked right", not "the app did the thing" [code].
5. The result `steps` array names which step ran; that tells whether path 1 or 2 produced the verdict. Not observed yet.

## 7. Limits
- Headless semantic paths only reach what the app's AX bridge implements. Java Swing on JetBrains Runtime: scroll bars exist but AXIncrement/AXValue/ByPage do not move content (hence scroll_advertised_but_inert); AXExpand/settable AXExpanded likely absent on tree rows [inferred, matches observed ACTION_FAILED].
- Unadvertised AX actions are never attempted (ax_perform.rs), so there is no brute-force fallback in headless mode.
- Expand/collapse have no physical fallback even with --headed (chain_defs.rs:197-213). To expand a tree row physically you need click --headed on the disclosure control or a key press (Right arrow) with the row focused.
- No action in the tool wakes an app's frontmost-gated logic by itself; focus is stolen only through --headed or focus-window.
- Nothing here sets an app "active" without raising it: `focus_app` sets AXFrontmost (system/focus.rs) which IS a visible raise.
- Not read: chain_value_write.rs, chain_menu_steps.rs, toggle_state*.rs, select_menu/select_name.rs, scroll_into_view.rs, post_state.rs, input/keyboard and mouse, docs/probes/CHANGELOG/builtin skills. [docs] claims therefore absent.

## 8. Avenues for the CLion problem
See the structured summary. In short, in order of source-predicted usefulness:
1. `agent-desktop focus-window ...` then act: known to work (~0.6 s); visible focus steal.
2. `click --headed <ref>`: real CGEvent click on frontmost CLion; cursor moves and focus is stolen; only avenue that bypasses the AX bridge. Does it trigger the 1 s analysis path: unknown.
3. Headless `press` with `--window-id`: refused for a background window (live: `STALE_REF`). Without `--window-id`: **Rejected after live tests (see [results](results.md)): keys land in whichever window and field had focus last, unverified. Don't use this.** Source reading: AXConfirm/AXCancel or CGEventPostToPid to the focused element; does not raise the window; whether CLion processes it while not frontmost is untested.
4. `focus @ref` (SetFocus): works only if AXFocused is settable; no raise; probably ACTION_FAILED.
5. `expand`/`scroll`/`set-value`/`select` headless: all source-predicted to fail on Swing as already observed.

## 9. Open questions
- Which step name appears in the `steps` array of the headless tree-item click (AXPress vs select_within_container)?
- Does the installed v1.1.0 binary behave like main for row click (main-only #503)?
- Does `press` with --app headless deliver keys to a non-frontmost CLion and does the MCP get_file_problems then answer fast?
- Does a headed click on a tree row, or `focus-window` once, leave CLion in a state where the fast path persists after the user's app is frontmost again?
