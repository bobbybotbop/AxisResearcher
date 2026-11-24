# Desktop browser tool (`mcp__desktop_browser__run`)

Read this before driving the built-in browser (e.g. investigating 3D-file sites
through the UI). The schema is strict: unknown keys are rejected, and a wrong
`condition` shape fails every time.

## `page.wait_for` conditions

Exactly three shapes, copy-paste from here:

```jsonc
// text on the page — state is required: "present" | "absent"
{"kind": "text", "text": "Just a moment", "match": "contains", "state": "absent"}

// element by role — state: "visible" | "hidden" | "enabled"
{"kind": "element", "locator": {"role": "button", "name": "Sign in"}, "state": "visible"}

// URL — match: "exact" | "prefix"
{"kind": "url", "value": "https://www.thingiverse.com/", "match": "prefix"}
```

Each shape accepts only the keys shown. Adding a key from another shape (e.g.
`value` on a text condition) is a validation error, not a merge.

## `page.visual.snapshot` right after navigation

A snapshot taken immediately after navigate/input can fail with
`PAGE_NOT_READY` ("page changed while capturing"). Capture again — it is a
transient race, not a broken page. If it persists, `page.wait_for` on text or
an element first, then snapshot.
