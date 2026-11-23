"""The window: choose the mods folder and the game file, make the trackers, run the Archipelago console bridge."""
import queue
import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from ootr_tracker import __version__, actions, settings
from ootr_tracker.companion import Options
from ootr_tracker.seedfolder import SeedError, mods_folder_of, read_seed, seed_folders

TITLE = 'OoTRr in-game tracker'
MOZ_URL = 'https://github.com/Mozencaz/OotrR'
MOZ_RELEASES_URL = MOZ_URL + '/releases'
INTRO = ("Use this with Moz's version of the randomizer ({url}). It gives each seed you installed with it a tracker "
         'you open in the game with R + right stick up.')
POLL_MILLISECONDS = 100
PADDING = 8
PASSWORD_MASK = '*'
PATH_WIDTH = 60
GAME_FILES = [('Game file', '*.nup'), ('All files', '*.*')]


class Window:
    def __init__(self, root):
        self.root = root
        root.title(f'{TITLE} {__version__}')
        self.saved = settings.load()
        self.messages = queue.Queue()
        self.bridge = None
        self.mods = tk.StringVar(value=self.saved['mods_folder'])
        self.game = tk.StringVar(value=self.saved['game_file'])
        self.module = tk.BooleanVar(value=self.saved['module'])
        self._build()
        self.refresh_seeds()
        root.protocol('WM_DELETE_WINDOW', self.close)
        root.after(POLL_MILLISECONDS, self._drain)

    # ----------------------------------------------------------------- layout
    def _build(self):
        frame = ttk.Frame(self.root, padding=PADDING)
        frame.grid(sticky='nsew')
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(5, weight=1)
        ttk.Label(frame, text=INTRO.format(url=MOZ_URL), wraplength=480, justify='left').grid(
            row=0, column=0, columnspan=2, sticky='w')
        links = ttk.Frame(frame)
        links.grid(row=0, column=2, sticky='e')
        for column, (text, url) in enumerate((("Moz's randomizer", MOZ_URL), ('Releases', MOZ_RELEASES_URL))):
            link = ttk.Label(links, text=text, foreground='#1a5fb4', cursor='hand2')
            link.grid(row=0, column=column, padx=PADDING)
            link.bind('<Button-1>', lambda event, url=url: webbrowser.open(url))
        self._path_row(frame, 1, "Mods folder (the emulator's load folder for the game)", self.mods, self.pick_mods)
        self._path_row(frame, 2, 'Game file (.nup), for the icons and Y (optional)', self.game, self.pick_game)
        options = ttk.Frame(frame)
        options.grid(row=3, column=0, columnspan=3, sticky='w')
        ttk.Checkbutton(options, text='Put the module in (turn off if your emulator provides it)',
                        variable=self.module).grid(row=0, column=0, sticky='w')
        self.tabs = ttk.Notebook(frame)
        self.tabs.grid(row=4, column=0, columnspan=3, sticky='ew', pady=PADDING)
        self._tracker_tab()
        self._console_tab()
        self.output = tk.Text(frame, height=12, width=80, wrap='word', state='disabled')
        self.output.grid(row=5, column=0, columnspan=3, sticky='nsew')

    def _path_row(self, frame, row, label, variable, command):
        ttk.Label(frame, text=label).grid(row=row, column=0, sticky='w')
        ttk.Entry(frame, textvariable=variable, width=PATH_WIDTH).grid(row=row, column=1, sticky='ew', padx=PADDING)
        ttk.Button(frame, text='Choose...', command=command).grid(row=row, column=2)

    def _tracker_tab(self):
        tab = ttk.Frame(self.tabs, padding=PADDING)
        self.tabs.add(tab, text='Tracker')
        ttk.Button(tab, text='Create tracker', command=self.create).grid(row=0, column=0, sticky='w')
        ttk.Button(tab, text='Remove leftovers', command=self.clean).grid(row=0, column=1, padx=PADDING)
        ttk.Button(tab, text='List', command=self.show_list).grid(row=0, column=2)
        ttk.Label(tab, text='Enable the tracker folder in the emulator together with its seed. Without the game '
                            'file the items show as letters and Y is off.', wraplength=560).grid(
            row=1, column=0, columnspan=3, sticky='w', pady=PADDING)

    def _console_tab(self):
        tab = ttk.Frame(self.tabs, padding=PADDING)
        self.tabs.add(tab, text='Archipelago console')
        self.seed = tk.StringVar()
        self.server = tk.StringVar(value=self.saved['server'])
        self.slot = tk.StringVar()
        self.password = tk.StringVar()
        self.emulators = tk.StringVar(value=self.saved['extra_emulators'])
        tab.columnconfigure(1, weight=1)
        rows = (('Seed', None), ('Server', self.server), ('Slot', self.slot), ('Password', self.password),
                ('Emulator program (only if unknown)', self.emulators))
        for row, (label, variable) in enumerate(rows):
            ttk.Label(tab, text=label).grid(row=row, column=0, sticky='w')
            if variable is None:
                widget = ttk.Combobox(tab, textvariable=self.seed, state='readonly')
                widget.bind('<<ComboboxSelected>>', self._seed_chosen)
                self.seed_box = widget
            else:
                widget = ttk.Entry(tab, textvariable=variable, show=PASSWORD_MASK if label == 'Password' else '')
            widget.grid(row=row, column=1, sticky='ew', padx=PADDING)
        buttons = ttk.Frame(tab)
        buttons.grid(row=len(rows), column=0, columnspan=2, sticky='w', pady=PADDING)
        self.start_button = ttk.Button(buttons, text='Start console', command=self.start_console)
        self.start_button.grid(row=0, column=0)
        self.stop_button = ttk.Button(buttons, text='Stop', command=self.stop_console, state='disabled')
        self.stop_button.grid(row=0, column=1, padx=PADDING)
        ttk.Label(tab, wraplength=560, text=(
            'This is a second, text-only connection to your slot, beside the randomizer\'s own: it asks for no '
            'items and sends no checks. It writes the room\'s messages into the running game (needs the emulator on '
            'this computer). The password is not saved.')).grid(row=len(rows) + 1, column=0, columnspan=2, sticky='w')

    # ---------------------------------------------------------------- helpers
    def say(self, lines):
        self.messages.put(('say', lines))

    def _drain(self):
        while not self.messages.empty():
            kind, payload = self.messages.get()
            if kind == 'say':
                self.output.configure(state='normal')
                self.output.insert('end', '\n'.join(payload) + '\n')
                self.output.see('end')
                self.output.configure(state='disabled')
            elif kind == 'idle':
                self.start_button.configure(state='normal' if self.bridge is None else 'disabled')
                self.stop_button.configure(state='disabled' if self.bridge is None else 'normal')
        self.root.after(POLL_MILLISECONDS, self._drain)

    def _options(self):
        game = self.game.get().strip()
        return Options(module=self.module.get(), game_file=Path(game) if game else None)

    def _remember(self):
        settings.save({'mods_folder': self.mods.get(), 'game_file': self.game.get(),
                       'module': self.module.get(),
                       'server': self.server.get(), 'extra_emulators': self.emulators.get()})

    def _in_background(self, work):
        """Run ``work`` (which returns lines) off the window's thread, so the window stays alive."""
        self._remember()
        threading.Thread(target=lambda: self.say(work()), daemon=True).start()

    def _mods_path(self):
        return mods_folder_of(self.mods.get().strip() or '.')

    # ---------------------------------------------------------------- actions
    def pick_mods(self):
        folder = filedialog.askdirectory(title="The game's mods folder")
        if folder:
            self.mods.set(folder)
            self.refresh_seeds()

    def pick_game(self):
        path = filedialog.askopenfilename(title='Your game file', filetypes=GAME_FILES)
        if path:
            self.game.set(path)

    def create(self):
        path, options = self.mods.get().strip(), self._options()
        self.say(['Working...'])
        self._in_background(lambda: actions.create_trackers(path, options).lines)
        self.root.after(2000, self.refresh_seeds)

    def show_list(self):
        self.say(actions.list_trackers(self.mods.get().strip() or '.'))

    def clean(self):
        path = self.mods.get().strip() or '.'
        planned = actions.clean(path)
        if planned == ['Nothing to remove.']:
            self.say(planned)
        elif messagebox.askyesno(TITLE, '\n'.join(planned[1:]) + '\n\nRemove these tracker folders?'):
            self.say(actions.clean(path, apply=True))

    def refresh_seeds(self):
        folders = seed_folders(self._mods_path()) if self.mods.get().strip() else []
        self.seeds = {folder.name: folder for folder in folders}
        self.seed_box.configure(values=list(self.seeds))
        if self.seeds and self.seed.get() not in self.seeds:
            self.seed.set(next(iter(self.seeds)))
            self._seed_chosen()

    def _seed_chosen(self, event=None):
        try:
            self.slot.set(read_seed(self.seeds[self.seed.get()]).slot_name)
        except (KeyError, SeedError):
            self.slot.set('')

    def start_console(self):
        from ootr_tracker.console.bridge import Bridge
        from ootr_tracker.console.memory import set_extra_emulators
        try:
            seed = read_seed(self.seeds[self.seed.get()])
        except (KeyError, SeedError) as error:
            messagebox.showerror(TITLE, f'Choose a seed first ({error}).')
            return
        self._remember()
        set_extra_emulators(self.emulators.get())
        self.bridge = Bridge(seed.short_id, self.server.get(), self.slot.get() or seed.slot_name,
                             self.password.get(), on_status=lambda text: self.say([text]))
        self.say(['Second, text-only connection to the room. It stops when you press Stop or close the window.'])
        self.bridge.start()
        self.messages.put(('idle', None))

    def stop_console(self):
        if self.bridge is not None:
            self.bridge.stop()
            self.bridge = None
        self.messages.put(('idle', None))

    def close(self):
        self.stop_console()
        self._remember()
        self.root.destroy()


def run():
    """Open the window (returns when it is closed)."""
    root = tk.Tk()
    Window(root)
    root.mainloop()
    return 0
