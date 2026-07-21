# Changelog

## 1.1 — 2026-07-21

- **Today is highlighted.** The Today section sits in a warm amber band with
  brighter text and a labeled header, so it reads as the focus rather than one
  group among four.
- **Apple Reminders sync (opt-in, two-way).** Link one list with
  `today sync list "NAME"`; the widget then syncs every minute. Creation,
  completion, renaming, rescheduling, and deletion all propagate. Notes and links
  stay local to the widget.
- Sync safety: an exclusive file lock stops the manual and automatic syncs from
  racing each other, titles are matched so an existing reminder is adopted rather
  than duplicated, and an empty answer from Reminders.app is re-checked before
  it's believed (it returns nothing while busy, which previously caused duplicate
  reminders).

## 1.0 — 2026-07-21

First shareable version.

- Wallpaper-embedded design ("The Spine"): a hairline vertical rule with tasks as
  stations on it, light ink over a feathered wash, one amber accent. No panel, no
  border, no shadow — it reads as part of the desktop picture.
- Date sections: Carried over (with age), Today, Upcoming (grouped by day), Done
  (with completion times). Unfinished work keeps its original date at rollover
  instead of silently becoming today's.
- Per-task note drawers with free text, auto-detected link chips (Notion aware)
  that open in the browser, and Today / Tomorrow / +1 week reschedule buttons.
- Click-through: the window ignores the mouse except over rows, the header, and
  open drawers, so desktop icons underneath stay clickable.
- Lives on the desktop layer by default so it never blocks apps; ★ temporarily
  floats it above everything.
- `today` CLI for terminal and AI-assistant control, with live sync to the widget
  (the app watches the data file).
- Inline editing, drag-to-reorder, confetti when the day is cleared, dark-mode-safe
  palette, resizable and movable with position remembered.
