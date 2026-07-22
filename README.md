# Today Tasks

A translucent to-do widget that lives on your macOS wallpaper. It sits behind your
app windows, so it never blocks your work, and clicks pass through the empty parts
so your desktop icons stay usable.

Built by Sasha Zhu.

```
  Today  Tue, Jul 21              2 of 7 done   ★  –
  ▮▮▮▮▮▮▮▮▮▮▮▮·································  33%   <- LED meter
  ─────────────────────────────────────────────────
  CARRIED OVER · 1 ────────────────────────────────
   2d  ○  Submit to SUO                         ▶
  ╭───────────────────────────────────────────────╮
  │ TODAY ─────────────────────────────────────── │  <- highlighted band
  │      ○  Thaw T cells                          │
  │      ○  Thaw KDM1A KO cells                   │
  │      ○  Prepare ELISA samples              ▶  │
  │      +  Add a task…                           │
  ╰───────────────────────────────────────────────╯
  UPCOMING · 2 ────────────────────────────────────
  WED 22
       ⚬  Draft SUO abstract figures
  DONE · 2 ────────────────────────────────────────
  10:04 ✓  Email the draft
```

---

## Install

**Requirements:** macOS (Apple Silicon or Intel), Python 3.9+ (the one Apple ships is fine).
No Xcode, no admin password needed.

1. Download or clone this folder.
2. Open Terminal, go into the folder, and run:

   ```
   ./install.sh
   ```

That's it. The installer puts **Today Tasks.app** in your `~/Applications`,
installs the `today` command line tool, and launches the widget.

To have it start automatically when you log in:
**System Settings → General → Login Items → +** and pick `Today Tasks` from `~/Applications`.

---

## Using it

The widget appears on the left edge of **every** display you have, showing the
same list on each. Everything is editable by clicking; nothing needs the terminal.

| What you want | How |
| --- | --- |
| Add a task | Click the `+` line at the bottom of the Today section, type, press Return |
| Check something off | Click the circle next to it |
| Edit wording | Click the text and type |
| Delete | Hover the row, click the ✕ on the right |
| Reorder | Hover, then drag the `⋮` handle |
| Add notes or a link | Hover the row, click `▶` to open its drawer |
| Open a saved link | Click the amber 🔗 chip in the drawer |
| Reschedule | In the drawer, click **Today**, **Tomorrow**, or **+1 week** |
| Move the widget | Drag it by the "Today" header (each display remembers its own spot) |
| Resize | Drag any edge or corner |
| Bring it in front of apps | Click the ★ (click again to send it back to the wallpaper) |
| Hide it | Click the `–`, or use the ✓ menu bar icon |
| Quit | ✓ menu bar icon → Quit Today Tasks |

### Sizing

The panels widen and narrow on their own to fit your longest task, within
sensible limits (never past about a third of the display). Anything longer than
that wraps onto extra lines instead of being cut off, and the row grows to hold
it. You can still drag an edge to size a panel yourself.

### Multiple displays

Every screen gets its own copy, all showing the same tasks. Edit or check
something off on one and the others update immediately. Each display remembers
where you put its panel and how big you made it, and plugging or unplugging a
monitor rebuilds them automatically — no restart needed.

### The sections

Tasks are grouped by date, not by priority:

- **Carried over** — unfinished work from previous days, labeled with its age
  ("yest", "3d"). It keeps its original date instead of quietly becoming today's
  problem, so nothing disappears into the pile.
- **Today** — what's on for today.
- **Upcoming** — scheduled for later, dimmed, grouped by day.
- **Done** — checked-off items, stamped with the time you finished them.

At midnight, finished tasks clear out and unfinished ones move to "Carried over."

**Today is highlighted** with a warm band and brighter text, so the thing you're
actually working on stands out from what's carried over or coming up.

**The LED meter** under the header is a dot-matrix progress display showing how
much of today is finished. It sweeps up whenever you check something off.

### Notes and links

Every task has a drawer (the `▶`) for free text: reagent details, sample counts,
reminders, whatever. Any URL you paste is detected automatically and shown as a
clickable chip below the note. Notion links (`notion.so` or `notion://`) are
labeled "Notion"; others show the site name. Clicking a chip opens it in your
default browser.

---

## Controlling it from the terminal (or from Claude)

The widget watches its data file, so anything the command line changes appears
within about two seconds. This is also how you get an AI assistant to manage your
list: ask it to run these commands.

```
today                                list everything, grouped by section
today add "Thaw T cells"             add to today
today add "Order primers" --when tomorrow
today add "Passage PDOs" --when +3   3 days out (also accepts 2026-07-30)
today done 2                         check off task 2 (numbers come from `today`)
today undo 2                         un-check it
today rm 4                           delete task 4
today clear                          remove all checked-off tasks
today when 3 tomorrow                reschedule task 3
today note 5 "24h + 48h timepoints"  set a note (URLs allowed)
today note+ 5 "https://notion.so/…"  append a line to the note
today note- 5                        clear the note
```

---

## Apple Reminders sync (optional)

You can link the widget to one Reminders list. It syncs both ways, so tasks you
add on your iPhone show up on the desktop, and anything you check off in either
place is done in both.

```
today sync list "Tasks"     link a list and sync immediately
today sync                  sync now
today sync status           show what's linked
today sync off              stop automatic syncing (today sync on resumes it)
```

Once linked, the widget syncs by itself every minute.

The first time it runs, macOS asks for permission to control Reminders — say yes.
If you miss the prompt, enable it in **System Settings → Privacy & Security →
Automation**.

**What syncs**

| Change | Result |
| --- | --- |
| New task in the widget | New reminder in the list |
| New reminder in Reminders | New task in the widget |
| Checked off in either place | Marked done in both |
| Renamed or rescheduled in the widget | Reminder updated to match |
| Reminder deleted in Reminders.app | Task disappears from the widget |

Notes and links stay in the widget only; Reminders doesn't get them.

**Pick the list carefully** — if you share a list with someone (a household or
partner list), everything on your widget will appear in their Reminders too. Use a
personal list unless you want that.

---

## Sharing a list with a coworker (Notion)

Apple Reminders sharing ties two personal iCloud accounts together, which is
awkward for a coworker. Instead the widget can sync a **shared list** to a Notion
database that you both connect to. Everyone linked to it sees the same shared
tasks — in the widget's teal **Shared** section — while your personal tasks stay
private to you.

**One-time setup (needs a Notion integration token in `~/.notion_token`).**

Owner (creates the list):

```
today share new "Lab shared"     # creates the Notion database + links you
```

It prints the database URL and its ID. In Notion, open that page and **share it
with your coworker** (and, if you're in different workspaces, share it to their
integration too). Then send them the database ID.

Coworker (joins the existing list):

```
echo 'secret_theirtoken' > ~/.notion_token   # their own Notion integration
today share join <DATABASE_ID> "Lab shared"  # links their widget to the same list
```

Now you both have the widget's Shared section backed by the same tasks.

**Putting tasks on the shared list**

| Action | How |
| --- | --- |
| Add straight to shared | `today add "Restock tips" --shared`, or the input then the `→ Share` button in a task's drawer |
| Move an existing task in | open its `▶` drawer → **→ Share with <list>** |
| Move it back to private | drawer → **← Make private** |
| See who added a task | the small name chip on each shared row (your own show "you") |

Completion, edits, due dates, and deletions sync both ways every ~45 seconds, and
each side can check off or edit any shared task. Personal notes stay on the shared
Notion page too (unlike Reminders). To manage from the terminal:

```
today share status      # what's linked
today share sync        # sync now
today share off         # pause shared syncing
today unshare N         # move task N back to private
```

**Which store, and privacy.** Only tasks you explicitly share go to Notion; your
personal list never leaves your Mac. Anyone with access to that Notion database
sees everything on the shared list, so keep it to the shared work.

---

## Where your data lives

| What | Where |
| --- | --- |
| Your tasks | `~/Library/Application Support/TodayTasks/tasks.json` |
| The app | `~/Applications/Today Tasks.app` |
| The CLI | `today` (in `/opt/homebrew/bin`, `/usr/local/bin`, or `~/.local/bin`) |
| Window position/size | remembered automatically |
| Error log | `~/Library/Logs/TodayTasks.log` |

Everything is local. Nothing is uploaded anywhere.

Your task file is plain JSON, so it is easy to back up or edit by hand:

```json
{
  "date": "2026-07-21",
  "pinned": false,
  "tasks": [
    { "id": "a1b2", "text": "Thaw T cells", "done": false, "due": "2026-07-21",
      "note": "P4 vial, box 2\nhttps://notion.so/..." }
  ]
}
```

---

## Troubleshooting

**The widget isn't visible.** It lives on the wallpaper layer, behind your apps.
Show the desktop (spread four fingers on the trackpad, or F11), or click the ✓ menu
bar icon → Show / Hide Panel. To keep it above your windows, click the ★.

**It's covering desktop icons I need.** Clicks pass through the empty areas, so
icons there still work. For icons sitting directly behind a task row, drag the
widget by its header until it clears them, or make it narrower by dragging an edge.

**Nothing happens when I click a task.** Make sure you're clicking the row itself.
The click-through logic only makes rows, the header, and open drawers interactive.

**The `today` command isn't found.** Its folder isn't on your PATH. Run
`~/.local/bin/today` directly, or add that folder to your PATH in `~/.zshrc`.

**It didn't start.** Check `~/Library/Logs/TodayTasks.log` for the error, and
confirm PyObjC installed: `python3 -c "import AppKit, WebKit, Quartz"`.

---

## Colors

The accent color is picked automatically from your **wallpaper** — the widget
reads each display's desktop picture, finds its most prominent color, and uses
that for the checkmarks, links, progress meter, and Today highlight. The shared
section uses the complementary color so it stays distinct. Change your wallpaper
and the widget re-colors itself within about 20 seconds, and each display matches
its own wallpaper.

Grayscale or very muted wallpaper falls back to a warm amber.

If you'd rather pin a fixed color, set `--amber` (and friends) in the `:root`
block at the top of `src/index.html` and it will override the auto-detected one:

```css
--ink:   #f7f1e8;   /* main text (light, sits over a dark wash) */
--amber: #f7b06a;   /* accent: checkmarks, links, the +, the meter */
--stale: #e08a6a;   /* carried-over items */
--teal:  #5ed3c4;   /* the shared section */
```

---

## How it works

A small Python app using PyObjC. A borderless, transparent window sits just above
the desktop-icon layer and hosts a WebKit view that renders the interface as
HTML/CSS/JS. A timer polls the cursor position and toggles the window's
mouse-ignoring flag, which is what produces the click-through. Another timer
watches the JSON file so external edits (the CLI, an AI assistant) show up live.

```
src/main.py     the macOS window, click-through, file watching, link opening
src/index.html  the entire interface and its behavior
bin/today       the command line tool
install.sh      builds the .app bundle and installs both
```
