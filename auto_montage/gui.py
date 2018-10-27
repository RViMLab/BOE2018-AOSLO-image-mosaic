import tkinter as tk
from tkinter.filedialog import askdirectory, askopenfilename
from tkinter import messagebox

from . import auto_montage
import queue
from threading import Thread, Event


class GUI:
    def __init__(self):
        self.root = tk.Tk()
        self.frame = tk.Frame(self.root)
        self.frame.pack()
        self.welcome_window()

    def restart_frame(self):
        self.frame.destroy()
        self.frame = tk.Frame(self.root)
        self.frame.pack()
        new_frame = tk.Frame(self.frame)
        new_frame.pack()
        return new_frame

    def welcome_window(self):
        welcome_frame = self.restart_frame()


        directory_var = tk.StringVar()
        photoshop_var = tk.StringVar()
        nominal_var = tk.StringVar()

        def get_directory():
            options = {'title': 'Choose directory'}
            directory_var.set(askdirectory(**options))

        def get_nominal():
            options = {'title': 'Choose nominal pos'}
            nominal_var.set(askopenfilename(**options))

        def get_photoshop():
            options = {'title': 'Choose directory'}
            photoshop_var.set(askdirectory(**options))

        choose_directory_label = tk.Label(welcome_frame, text='Choose image folder')
        choose_directory_label.grid(row=0, column=0, sticky=(tk.W,))
        choose_directory = tk.Button(welcome_frame, text='Choose', command=get_directory)
        choose_directory.grid(row=0, column=1, sticky=(tk.N, tk.S, tk.E, tk.W))

        choose_nominal_label = tk.Label(welcome_frame, text='Choose nominal positions')
        choose_nominal_label.grid(row=1, column=0, sticky=(tk.W,))
        choose_nominal = tk.Button(welcome_frame, text='Choose', command=get_nominal)
        choose_nominal.grid(row=1, column=1, sticky=(tk.N, tk.S, tk.E, tk.W))

        eye = tk.StringVar()
        eye.set('None')
        eye_label = tk.Label(welcome_frame, text='Choose eye')
        eye_label.grid(row=2, column=0, sticky=(tk.W,))
        eye_menu = tk.OptionMenu(welcome_frame, eye, *['OD', 'OS'])
        eye_menu.grid(row=2, column=1, sticky=(tk.N, tk.S, tk.E, tk.W))

        conf_var = tk.StringVar()
        conf_var.set('confocal')
        conf_label = tk.Label(welcome_frame, text='confocal naming')
        conf_label.grid(row=3, column=0, sticky=(tk.W,))
        conf_entry = tk.Entry(welcome_frame, textvariable=conf_var)
        conf_entry.grid(row=3, column=1, sticky=(tk.N, tk.S, tk.E, tk.W))

        split_var = tk.StringVar()
        split_var.set('split_det')
        split_label = tk.Label(welcome_frame, text='split naming')
        split_label.grid(row=4, column=0, sticky=(tk.W,))
        split_entry = tk.Entry(welcome_frame, textvariable=split_var)
        split_entry.grid(row=4, column=1, sticky=(tk.N, tk.S, tk.E, tk.W))

        avg_var = tk.StringVar()
        avg_var.set('avg')
        avg_label = tk.Label(welcome_frame, text='average naming')
        avg_label.grid(row=5, column=0, sticky=(tk.W,))
        avg_entry = tk.Entry(welcome_frame, textvariable=avg_var)
        avg_entry.grid(row=5, column=1, sticky=(tk.N, tk.S, tk.E, tk.W))

        photo_label = tk.Label(welcome_frame, text='Choose output photoshop script folder')
        photo_label.grid(row=6, column=0, sticky=(tk.W,))
        photo = tk.Button(welcome_frame, text='Choose', command=get_photoshop)
        photo.grid(row=6, column=1, sticky=(tk.N, tk.S, tk.E, tk.W))

        def go():
            naming = {
                'confocal':conf_var.get(),
                'split':split_var.get(),
                'avg':avg_var.get()
            }
            self.start_montage(
                directory_var.get(),
                nominal_var.get(),
                eye.get(),
                naming,
                photoshop_var.get()
            )
        go = tk.Button(welcome_frame, text='Montage', command=go)
        go.grid(row=7, column=0, columnspan=2, sticky=(tk.N, tk.S, tk.E, tk.W))

    def start_montage(self, directory, nominal, eye, naming, photoshop_directory):
        q = queue.Queue()
        e = Event()
        t = Thread(target=auto_montage.montage, args=(directory, nominal, eye, naming, photoshop_directory, q, e))
        t.start()

        self.monitor_montage(q, e)

    def monitor_montage(self, q, e):
        monitor_frame = self.restart_frame()
        label = tk.Label(monitor_frame, text='Collecting images, can take a minute, gui hasnt frozen!')
        label.grid(row=0, column=0)
        label = tk.Label(monitor_frame, text='Number images montaged will appear below:')
        label.grid(row=1, column=0)

        def update_vars():
            try:
                done, total, fov_id, fov_name = q.get(block=False)
                label = tk.Label(monitor_frame, text='{} fov: {}/{}'.format(fov_name, done, total))
                label.grid(row=2 + fov_id, column=1)
            except queue.Empty:
                pass
            repeat_process()

        def repeat_process():
            if e.is_set():
                messagebox.showinfo(
                    "Finished",
                    "Finished montaging",
                    icon='warning')
                self.welcome_window()
            else:
                self.root.after(500, update_vars)

        update_vars()
