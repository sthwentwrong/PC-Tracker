import threading
import time

import win32api
import win32con
import win32gui
import win32ui

# Virtual screen: covers all monitors (including extended displays)
screen_left = win32api.GetSystemMetrics(win32con.SM_XVIRTUALSCREEN)
screen_top = win32api.GetSystemMetrics(win32con.SM_YVIRTUALSCREEN)
screen_width = win32api.GetSystemMetrics(win32con.SM_CXVIRTUALSCREEN)
screen_height = win32api.GetSystemMetrics(win32con.SM_CYVIRTUALSCREEN)
screen_size = (screen_width, screen_height)


def get_monitor_region(x, y):
    """Return (left, top, width, height) of the monitor containing (x, y)."""
    hmon = win32api.MonitorFromPoint((x, y), win32con.MONITOR_DEFAULTTONEAREST)
    info = win32api.GetMonitorInfo(hmon)
    left, top, right, bottom = info["Monitor"]
    return (left, top, right - left, bottom - top)


class ScreenCapturer:
    def __init__(self):
        self.hwindow = win32gui.GetDesktopWindow()

    def capture(self, region=None):
        """Capture screen.
        region: (left, top, width, height) for a single monitor, or None for all screens.
        """
        if region is None:
            cap_left, cap_top = screen_left, screen_top
            cap_width, cap_height = screen_width, screen_height
        else:
            cap_left, cap_top, cap_width, cap_height = region

        # dc: device context
        window_dc = win32gui.GetWindowDC(self.hwindow)
        img_dc = win32ui.CreateDCFromHandle(window_dc)
        mem_dc = img_dc.CreateCompatibleDC()
        # Create a bitmap object
        screenshot = win32ui.CreateBitmap()
        # Create a bitmap compatible with the device context and set its width and height
        screenshot.CreateCompatibleBitmap(img_dc, cap_width, cap_height)
        # Select the bitmap into the memory device context
        mem_dc.SelectObject(screenshot)
        # Perform a bit block transfer from the target region origin
        mem_dc.BitBlt(
            (0, 0), (cap_width, cap_height),
            img_dc, (cap_left, cap_top), win32con.SRCCOPY
        )
        # screenshot: bitmap byte stream
        bits = screenshot.GetBitmapBits(True)
        # Release resources
        mem_dc.DeleteDC()
        win32gui.ReleaseDC(self.hwindow, window_dc)
        win32gui.DeleteObject(screenshot.GetHandle())
        return bits


capturer = ScreenCapturer()


class RecentScreen:
    def __init__(self, capture_interval=0.1, region=None):
        self.region = region
        if region is not None:
            self.capture_size = (region[2], region[3])
            self.capture_origin = (region[0], region[1])
        else:
            self.capture_size = screen_size
            self.capture_origin = (screen_left, screen_top)
        self.screenshot = capturer.capture(region)
        self.capture_interval = capture_interval
        self.lock = threading.Lock()
        self.refresh_thread = threading.Thread(target=self.refreshing)
        self.refresh_thread.daemon = True
        self.refresh_thread.start()

    def refreshing(self):
        while True:
            screenshot = capturer.capture(self.region)
            with self.lock:
                self.screenshot = screenshot
            time.sleep(self.capture_interval)

    def get(self):
        with self.lock:
            return self.screenshot
