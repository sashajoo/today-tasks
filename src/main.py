#!/usr/bin/env python3
"""Today Tasks — translucent floating task widget for macOS."""

import datetime
import json
import os

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


class AppDelegate(NSObject):
    def applicationDidFinishLaunching_(self, note):
        self.state = load_state()
        self.file_mtime = self.currentMtime()
        self.zones = None
        self.click_through = False

        mask = (
            NSWindowStyleMaskBorderless
            | NSWindowStyleMaskResizable
            | NSWindowStyleMaskFullSizeContentView
        )
        self.window = (
            PanelWindow.alloc().initWithContentRect_styleMask_backing_defer_(
                NSMakeRect(0, 0, 320, 700), mask, NSBackingStoreBuffered, False
            )
        )
        w = self.window
        w.setOpaque_(False)
        w.setBackgroundColor_(NSColor.clearColor())
        w.setHasShadow_(False)  # embedded-in-wallpaper look: no card shadow
        w.setMovableByWindowBackground_(True)
        w.setCollectionBehavior_(
            NSWindowCollectionBehaviorCanJoinAllSpaces
            | NSWindowCollectionBehaviorFullScreenAuxiliary
        )
        # New autosave name: resets the frame to the right-dock default once,
        # then keeps remembering her manual moves/resizes as before.
        w.setFrameAutosaveName_("TodayTasksPanelSpine")
        w.setMinSize_((260, 400))

        # Default: docked to the right edge, full visible height (resizable).
        if w.frame().origin.x == 0 and w.frame().origin.y == 0:
            screen = NSScreen.mainScreen()
            if screen:
                sf = screen.visibleFrame()
                w.setFrame_display_(
                    NSMakeRect(
                        sf.origin.x + sf.size.width - 330,
                        sf.origin.y + 10,
                        320,
                        sf.size.height - 20,
                    ),
                    True,
                )

        # No frosted card: the transparent web view renders straight onto
        # the wallpaper (its CSS provides a feathered wash for legibility).
        config = WKWebViewConfiguration.alloc().init()
        ucc = config.userContentController()
        for name in ("save", "pin", "hide", "drag", "open", "zones"):
            ucc.addScriptMessageHandler_name_(self, name)
        self.webview = WKWebView.alloc().initWithFrame_configuration_(
            w.contentView().bounds(), config
        )
        self.webview.setAutoresizingMask_(18)  # width + height sizable
        self.webview.setValue_forKey_(False, "drawsBackground")
        self.webview.setNavigationDelegate_(self)
        w.setContentView_(self.webview)

        url = NSURL.fileURLWithPath_(HTML_FILE)
        self.webview.loadFileURL_allowingReadAccessToURL_(
            url, url.URLByDeletingLastPathComponent()
        )

        self.applyPinned()

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

        # Click-through: pass clicks to the desktop unless the cursor is over
        # an actual row/header/drawer.
        self.hitTimer = (
            NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                0.06, self, "updateClickThrough:", None, True
            )
        )

        w.makeKeyAndOrderFront_(None)
        NSApp.activateIgnoringOtherApps_(True)

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
        elif name == "pin":
            self.state["pinned"] = not self.state.get("pinned", False)
            self.persist()
            self.applyPinned()
            self.pushState()
        elif name == "hide":
            self.window.orderOut_(None)
        elif name == "open":
            url = NSURL.URLWithString_(str(message.body()))
            if url is not None:
                NSWorkspace.sharedWorkspace().openURL_(url)
        elif name == "zones":
            try:
                self.zones = json.loads(str(message.body()))
            except Exception:
                pass
        elif name == "drag":
            event = NSApp.currentEvent()
            if event is not None:
                self.window.performWindowDragWithEvent_(event)

    # -- Python -> JS -------------------------------------------------------

    def webView_didFinishNavigation_(self, webview, nav):
        self.pushState()

    def pushState(self):
        payload = json.dumps(
            {"tasks": self.state["tasks"], "pinned": self.state.get("pinned", False)}
        )
        self.webview.evaluateJavaScript_completionHandler_(
            "window.setState(%s)" % payload, None
        )

    # -- Click-through ------------------------------------------------------

    def updateClickThrough_(self, timer):
        """Ignore the mouse except over reported hot zones, so desktop icons
        under the empty parts of the widget stay clickable."""
        if not self.window.isVisible() or not self.zones:
            return
        # Never swallow clicks while pinned-and-focused editing? Editing still
        # works because hot zones cover every interactive row.
        p = NSEvent.mouseLocation()  # screen coords, origin bottom-left
        f = self.window.frame()
        inside_window = (
            f.origin.x <= p.x <= f.origin.x + f.size.width
            and f.origin.y <= p.y <= f.origin.y + f.size.height
        )
        hot = False
        if inside_window:
            # Convert to web-view coords (origin top-left, CSS px).
            sx = self.zones.get("w", f.size.width) / max(f.size.width, 1)
            sy = self.zones.get("h", f.size.height) / max(f.size.height, 1)
            x = (p.x - f.origin.x) * sx
            y = (f.origin.y + f.size.height - p.y) * sy
            for rx, ry, rw, rh in self.zones.get("rects", []):
                if rx <= x <= rx + rw and ry <= y <= ry + rh:
                    hot = True
                    break
        if hot == self.click_through:
            return
        self.click_through = hot
        self.window.setIgnoresMouseEvents_(not hot)

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
        self.window.setLevel_(
            NSFloatingWindowLevel
            if self.state.get("pinned", False)
            else DESKTOP_LEVEL
        )

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
        if self.window.isVisible():
            self.window.orderOut_(None)
        else:
            self.showPanel()

    def showPanel(self):
        self.rolloverIfNeeded()
        self.window.makeKeyAndOrderFront_(None)
        NSApp.activateIgnoringOtherApps_(True)

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
