"""Shared home navigation; use each screen's normal safe close handler."""
import tkinter as tk
from tkinter import ttk


HOME_LABEL = 'Voltar ao início'


def add_home_button(app, window, close, *, parent=None):
    """Register a screen and place its home button before its content."""
    screens = vars(app).setdefault('_home_screens', [])
    app.root.withdraw()
    for previous, _ in screens:
        if previous.winfo_exists():
            previous.withdraw()
    entry = (window, close)
    screens.append(entry)

    def forget(event):
        if event.widget is window and entry in screens:
            screens.remove(entry)
            if not vars(app).get('_returning_home', False):
                remaining = [screen for screen, _ in screens if screen.winfo_exists()]
                previous = remaining[-1] if remaining else app.root
                try:
                    previous.deiconify()
                    previous.lift()
                except tk.TclError:
                    pass  # The entire application may be shutting down.

    window.bind('<Destroy>', forget, add='+')

    def go_home():
        if app.busy:
            return
        center = vars(app).get('settings_home')
        if center is None:
            from settings_home import SettingsHome
            center = SettingsHome(app)
        center.show_home()

    bar = parent
    if bar is None:
        bar = ttk.Frame(window, padding=(12, 8))
        bar.pack(side='top', fill='x')
    button = ttk.Button(bar, text=HOME_LABEL, command=go_home)
    button.pack(side='right' if parent is not None else 'left')
    return button
