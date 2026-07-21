#!/usr/bin/env python3
"""Today Tasks — translucent floating task widget for macOS."""

import datetime
import json
import os
import shutil
import subprocess

import objc
from AppKit import (
    NSApp,
    NSApplication,
    NSApplicationActivationPolicyAccessory,
    NSBackingStoreBuffered,
    NSColor,
    NSEvent,
    NSFloatingWindowLevel,
    NSImage,
    NSEqualRects,
    NSMakeRect,
    NSMenu,
    NSMenuItem,
    NSNormalWindowLevel,
    NSObject,
    NSScreen,
    NSStatusBar,
    NSVisualEffectBlendingModeBehindWindow,
    NSVisualEffectMaterialPopover,
    NSVisualEffectStateActive,
    NSVisualEffectView,
    NSWindow,
    NSWindowCollectionBehaviorCanJoinAllSpaces,
    NSWindowCollectionBehaviorFullScreenAuxiliary,
    NSWindowStyleMaskBorderless,
    NSWindowStyleMaskFullSizeContentView,
    NSWindowStyleMaskResizable,
    NSWorkspace,
)
from Foundation import NSURL, NSNotificationCenter, NSTimer
from Quartz import CGWindowLevelForKey, kCGDesktopIconWindowLevelKey

# Just above the desktop icons, below every app window.
DESKTOP_LEVEL = CGWindowLevelForKey(kCGDesktopIconWindowLevelKey) + 1
from PyObjCTools import AppHelper
from WebKit import WKWebView, WKWebViewConfiguration

SQUARE_LENGTH = -2  # NSSquareStatusItemLength

DATA_DIR = os.path.expanduser("~/Library/Application Support/TodayTasks")
DATA_FILE = os.path.join(DATA_DIR, "tasks.json")
HTML_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")


def today_str():
    return datetime.date.today().isoformat()


def load_state():
    try:
        with open(DATA_FILE) as f:
            state = json.load(f)
    except Exception:
        state = {"date": today_str(), "tasks": [], "pinned": True}
    if state.get("date") != today_str():
        # New day: drop finished tasks. Unfinished ones keep their original
        # due date, so they surface under "Carried over".
        state["tasks"] = [t for t in state.get("tasks", []) if not t.get("done")]
        state["date"] = today_str()
        save_state(state)
    state.setdefault("tasks", [])
    state.setdefault("pinned", False)
    for t in state["tasks"]:
        t.setdefault("due", state.get("date", today_str()))
    return state


def save_state(state):
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, DATA_FILE)


class PanelWindow(NSWindow):
    def canBecomeKeyWindow(self):
        return True

    def canBecomeMainWindow(self):
        return True

    def constrainFrameRect_toScreen_(self, rect, screen):
        # macOS otherwise pulls these borderless windows back onto the main
        # display, which would stack every panel on one screen.
        return rect


class AppDelegate(NSObject):
    # -- Panels (one per display) -------------------------------------------

    def buildPanels(self):
        """Create a panel on every screen, reusing saved frames per display."""
        for p in self.panels:
            p["window"].orderOut_(None)
            p["window"].setContentView_(None)
        self.panels = []

        mask = (
            NSWindowStyleMaskBorderless
            | NSWindowStyleMaskResizable
            | NSWindowStyleMaskFullSizeContentView
        )
        url = NSURL.fileURLWithPath_(HTML_FILE)

        for i, screen in enumerate(NSScreen.screens()):
            sf = screen.visibleFrame()
            w = PanelWindow.alloc().initWithContentRect_styleMask_backing_defer_(
                NSMakeRect(0, 0, 320, 700), mask, NSBackingStoreBuffered, False
            )
            w.setOpaque_(False)
            w.setBackgroundColor_(NSColor.clearColor())
            w.setHasShadow_(False)  # embedded-in-wallpaper look
            w.setMovableByWindowBackground_(True)
            w.setCollectionBehavior_(
                NSWindowCollectionBehaviorCanJoinAllSpaces
                | NSWindowCollectionBehaviorFullScreenAuxiliary
            )
            w.setMinSize_((260, 400))

            # Per-display saved frame, keyed by the screen's own geometry so a
            # given monitor keeps its position when others come and go.
            key = "TodayTasksSpineL3-%dx%d@%d,%d" % (
                int(sf.size.width), int(sf.size.height),
                int(sf.origin.x), int(sf.origin.y),
            )
            w.setFrameAutosaveName_(key)
            if not w.setFrameUsingName_(key):
                # Default: flush against the LEFT edge of this display, full height.
                w.setFrame_display_(
                    NSMakeRect(
                        sf.origin.x,
                        sf.origin.y,
                        320,
                        sf.size.height,
                    ),
                    True,
                )

            config = WKWebViewConfiguration.alloc().init()
            ucc = config.userContentController()
            for name in ("save", "pin", "hide", "drag", "open", "zones", "width"):
                ucc.addScriptMessageHandler_name_(self, name)
            wv = WKWebView.alloc().initWithFrame_configuration_(
                w.contentView().bounds(), config
            )
            wv.setAutoresizingMask_(18)  # width + height sizable
            wv.setValue_forKey_(False, "drawsBackground")
            wv.setNavigationDelegate_(self)
            w.setContentView_(wv)
            wv.loadFileURL_allowingReadAccessToURL_(
                url, url.URLByDeletingLastPathComponent()
            )

            self.panels.append({"window": w, "webview": wv, "zones": None,
                                "ct": False, "index": i, "want": w.frame(),
                                "screenFrame": screen.frame(),
                                "visibleFrame": sf})

        self.applyPinned()
        if not self.hidden:
            for p in self.panels:
                p["window"].orderFront_(None)
            # Ordering a window front can nudge its frame; put each panel back
            # on its own display afterwards.
            for p in self.panels:
                if not NSEqualRects(p["window"].frame(), p["want"]):
                    p["window"].setFrame_display_(p["want"], True)

    def fitWidth_(self, needed):
        """Widen or narrow every panel so the longest task fits on one line,
        within sane bounds and never past a third of the display."""
        for p in self.panels:
            f = p["window"].frame()
            sf = p["visibleFrame"]
            limit = min(520, int(sf.size.width * 0.34))
            target = max(300, min(int(needed), limit))
            if abs(target - f.size.width) <= 4:
                continue
            p["want"] = NSMakeRect(f.origin.x, f.origin.y, target, f.size.height)
            p["window"].setFrame_display_(p["want"], True)
        self.enforceScreens_(None)

    def enforceScreens_(self, timer):
        """Each panel belongs to one display. macOS keeps yanking borderless
        windows back onto the main screen (on resize, on wake, on space
        changes), so put any stray panel back where it belongs."""
        for p in self.panels:
            win = p["window"]
            if not win.isVisible():
                continue
            f = win.frame()
            sf, vf = p["screenFrame"], p["visibleFrame"]
            cx = f.origin.x + f.size.width / 2.0
            cy = f.origin.y + f.size.height / 2.0
            on_its_screen = (
                sf.origin.x <= cx <= sf.origin.x + sf.size.width
                and sf.origin.y <= cy <= sf.origin.y + sf.size.height
            )
            if on_its_screen:
                p["want"] = f  # she may have dragged it; respect that
                continue
            h = min(f.size.height, vf.size.height)
            back = NSMakeRect(vf.origin.x, vf.origin.y, f.size.width, h)
            p["want"] = back
            win.setFrame_display_(back, True)

    def panelForWebView_(self, webview):
        for p in self.panels:
            if p["webview"] is webview:
                return p
        return None

    def screensChanged_(self, note):
        self.buildPanels()

    def applicationDidFinishLaunching_(self, note):
        self.state = load_state()
        self.file_mtime = self.currentMtime()
        self.panels = []   # one per display: {window, webview, zones, ct}
        self.hidden = False

        self.buildPanels()

        # Rebuild when displays are plugged in, unplugged, or rearranged.
        NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(
            self, "screensChanged:",
            "NSApplicationDidChangeScreenParametersNotification", None
        )

        # Menu-bar icon: the way back after hiding the panel.
        self.statusItem = NSStatusBar.systemStatusBar().statusItemWithLength_(
            SQUARE_LENGTH
        )
        icon = NSImage.imageWithSystemSymbolName_accessibilityDescription_(
            "checklist", "Today Tasks"
        )
        if icon is not None:
            self.statusItem.button().setImage_(icon)
        else:
            self.statusItem.button().setTitle_("✓")
        menu = NSMenu.alloc().init()
        item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Show / Hide Panel", "togglePanel:", ""
        )
        item.setTarget_(self)
        menu.addItem_(item)
        menu.addItem_(NSMenuItem.separatorItem())
        quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Quit Today Tasks", "terminate:", "q"
        )
        menu.addItem_(quit_item)
        self.statusItem.setMenu_(menu)

        NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(
            self, "dayChanged:", "NSCalendarDayChanged", None
        )

        # Watch the data file so external edits (CLI / Claude) show up live.
        self.watchTimer = (
            NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                1.5, self, "checkFileChange:", None, True
            )
        )

        # Keep each panel pinned to its own display.
        self.screenTimer = (
            NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                1.0, self, "enforceScreens:", None, True
            )
        )

        # Click-through: pass clicks to the desktop unless the cursor is over
        # an actual row/header/drawer.
        self.hitTimer = (
            NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                0.06, self, "updateClickThrough:", None, True
            )
        )

        # Apple Reminders sync, if she linked a list (runs out-of-process so a
        # slow AppleScript can never stall the UI; results arrive via the
        # file watcher above).
        self.syncProc = None
        self.syncTimer = (
            NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                60.0, self, "runReminderSync:", None, True
            )
        )
        self.runReminderSync_(None)

    # -- JS -> Python bridge ------------------------------------------------

    def userContentController_didReceiveScriptMessage_(self, ucc, message):
        name = message.name()
        if name == "save":
            try:
                tasks = json.loads(str(message.body()))
            except Exception:
                return
            self.state["tasks"] = tasks
            self.state["date"] = today_str()
            self.persist()
            # Mirror the edit onto the other displays (not the one being typed
            # in, which would reset the caret).
            self.pushStateExcept_(message.webView())
        elif name == "pin":
            self.state["pinned"] = not self.state.get("pinned", False)
            self.persist()
            self.applyPinned()
            self.pushState()
        elif name == "hide":
            self.hidePanel()
        elif name == "open":
            url = NSURL.URLWithString_(str(message.body()))
            if url is not None:
                NSWorkspace.sharedWorkspace().openURL_(url)
        elif name == "zones":
            panel = self.panelForWebView_(message.webView())
            if panel is not None:
                try:
                    panel["zones"] = json.loads(str(message.body()))
                except Exception:
                    pass
        elif name == "width":
            try:
                self.fitWidth_(int(float(str(message.body()))))
            except Exception:
                pass
        elif name == "drag":
            panel = self.panelForWebView_(message.webView())
            event = NSApp.currentEvent()
            if panel is not None and event is not None:
                panel["window"].performWindowDragWithEvent_(event)

    # -- Python -> JS -------------------------------------------------------

    def webView_didFinishNavigation_(self, webview, nav):
        self.pushStateTo_(webview)

    def stateJS(self):
        payload = json.dumps(
            {"tasks": self.state["tasks"], "pinned": self.state.get("pinned", False)}
        )
        return "window.setState(%s)" % payload

    def pushState(self):
        js = self.stateJS()
        for p in self.panels:
            p["webview"].evaluateJavaScript_completionHandler_(js, None)

    def pushStateTo_(self, webview):
        webview.evaluateJavaScript_completionHandler_(self.stateJS(), None)

    def pushStateExcept_(self, webview):
        js = self.stateJS()
        for p in self.panels:
            if p["webview"] is not webview:
                p["webview"].evaluateJavaScript_completionHandler_(js, None)

    # -- Apple Reminders ----------------------------------------------------

    def todayCLI(self):
        found = shutil.which("today")
        if found:
            return found
        for p in ("/opt/homebrew/bin/today", "/usr/local/bin/today",
                  os.path.expanduser("~/.local/bin/today")):
            if os.path.exists(p):
                return p
        return None

    def runReminderSync_(self, timer):
        if not self.state.get("syncOn") or not self.state.get("remindersList"):
            return
        if self.syncProc is not None and self.syncProc.poll() is None:
            return  # previous sync still running
        cli = self.todayCLI()
        if not cli:
            return
        try:
            self.syncProc = subprocess.Popen(
                [cli, "sync"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        except Exception:
            self.syncProc = None

    # -- Click-through ------------------------------------------------------

    def updateClickThrough_(self, timer):
        """Ignore the mouse except over reported hot zones, so desktop icons
        under the empty parts of the widget stay clickable."""
        cursor = NSEvent.mouseLocation()  # screen coords, origin bottom-left
        for panel in self.panels:
            win, zones = panel["window"], panel["zones"]
            if not win.isVisible() or not zones:
                continue
            f = win.frame()
            hot = False
            if (f.origin.x <= cursor.x <= f.origin.x + f.size.width
                    and f.origin.y <= cursor.y <= f.origin.y + f.size.height):
                # Convert to web-view coords (origin top-left, CSS px).
                sx = zones.get("w", f.size.width) / max(f.size.width, 1)
                sy = zones.get("h", f.size.height) / max(f.size.height, 1)
                x = (cursor.x - f.origin.x) * sx
                y = (f.origin.y + f.size.height - cursor.y) * sy
                for rx, ry, rw, rh in zones.get("rects", []):
                    if rx <= x <= rx + rw and ry <= y <= ry + rh:
                        hot = True
                        break
            if hot != panel["ct"]:
                panel["ct"] = hot
                win.setIgnoresMouseEvents_(not hot)

    # -- External-edit watching --------------------------------------------

    def currentMtime(self):
        try:
            return os.stat(DATA_FILE).st_mtime
        except OSError:
            return 0

    def persist(self):
        save_state(self.state)
        self.file_mtime = self.currentMtime()

    def checkFileChange_(self, timer):
        m = self.currentMtime()
        if m != self.file_mtime:
            self.file_mtime = m
            self.state = load_state()
            self.applyPinned()
            self.pushState()

    # -- Panel management ---------------------------------------------------

    def applyPinned(self):
        # Default: desktop-widget level (never blocks apps, visible with the
        # wallpaper). Pinned (star ON): floats above everything temporarily.
        level = (
            NSFloatingWindowLevel
            if self.state.get("pinned", False)
            else DESKTOP_LEVEL
        )
        for p in self.panels:
            p["window"].setLevel_(level)

    def rolloverIfNeeded(self):
        if self.state.get("date") != today_str():
            self.state["tasks"] = [
                t for t in self.state["tasks"] if not t.get("done")
            ]
            self.state["date"] = today_str()
            self.persist()
            self.pushState()

    def dayChanged_(self, note):
        AppHelper.callAfter(self.rolloverIfNeeded)

    def togglePanel_(self, sender):
        if self.hidden:
            self.showPanel()
        else:
            self.hidePanel()

    def hidePanel(self):
        self.hidden = True
        for p in self.panels:
            p["window"].orderOut_(None)

    def showPanel(self):
        self.hidden = False
        self.rolloverIfNeeded()
        for p in self.panels:
            p["window"].orderFront_(None)

    def applicationShouldHandleReopen_hasVisibleWindows_(self, app, flag):
        self.showPanel()
        return True


def main():
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    delegate = AppDelegate.alloc().init()
    app.setDelegate_(delegate)
    AppHelper.runEventLoop()


if __name__ == "__main__":
    main()
