#activity_monitor.py
import win32con
import win32gui
import win32api
import win32ts
from win32gui import PumpMessages
from database.queries import log_sleep_event
import threading
import pythoncom
import wmi
import time

WTS_SESSION_LOCK = 0x7
WTS_SESSION_UNLOCK = 0x8
WM_WTSSESSION_CHANGE = 0x02B1
NOTIFY_FOR_THIS_SESSION = 0

def activity_window_proc(account_id, session_id):
    def wndProc(hWnd, msg, wParam, lParam):
        if msg == win32con.WM_POWERBROADCAST:
            if wParam == win32con.PBT_APMSUSPEND:
                log_sleep_event(account_id, session_id, 'sleep', source='system')
            elif wParam == win32con.PBT_APMRESUMEAUTOMATIC:
                log_sleep_event(account_id, session_id, 'resume', source='system')

        elif msg == WM_WTSSESSION_CHANGE:
            if wParam == WTS_SESSION_LOCK:
                log_sleep_event(account_id, session_id, 'sleep', source='user')
            elif wParam == WTS_SESSION_UNLOCK:
                log_sleep_event(account_id, session_id, 'resume', source='user')

        return win32gui.DefWindowProc(hWnd, msg, wParam, lParam)

    return wndProc


def monitor_sleep_resume(account_id, session_id):
    pythoncom.CoInitialize()
    c = wmi.WMI()
    watcher = c.Win32_PowerManagementEvent.watch_for()
    while True:
        try:
            event = watcher()
            if event.Type == 4:  # Suspend
                log_sleep_event(account_id, session_id, 'sleep')
            elif event.Type == 7:  # Resume
                log_sleep_event(account_id, session_id, 'resume')
        except Exception as e:
            print("WMI Sleep/Resume Monitor Error:", e)
            time.sleep(1)

def start_activity_monitor(account_id, session_id):
    threading.Thread(target=monitor_sleep_resume, args=(account_id, session_id), daemon=True).start()

    hInstance = win32api.GetModuleHandle()
    className = "ActivityMonitorWindow"

    wndClass = win32gui.WNDCLASS()
    wndClass.lpfnWndProc = activity_window_proc(account_id, session_id)
    wndClass.hInstance = hInstance
    wndClass.lpszClassName = className
    win32gui.RegisterClass(wndClass)

    hWnd = win32gui.CreateWindow(className, className, 0, 0, 0, 0, 0, 0, 0, hInstance, None)
    win32ts.WTSRegisterSessionNotification(hWnd, NOTIFY_FOR_THIS_SESSION)

    PumpMessages()
