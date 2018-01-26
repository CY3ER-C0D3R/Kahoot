from Tkinter import *
import ttk
import tkMessageBox


class Dialog(Toplevel):
    def __init__(self, parent, title=None, parm=False, text1=None, text2=None, opt=False):
        if __name__ == "__main__" or parm:
            self.parm = True

            Toplevel.__init__(self, parent)
            self.transient(parent)

            if title:
                self.title(title)

            self.parent = parent

            self.result = None

            body = Frame(self)
            self.initial_focus = self.body(body, text1, text2, opt)
            body.pack(padx=5, pady=5)

            self.buttonbox()

            self.grab_set()

            if not self.initial_focus:
                self.initial_focus = self

            self.protocol("WM_DELETE_WINDOW", self.cancel)

            self.geometry("+%d+%d" % (parent.winfo_rootx()+50,
                                      parent.winfo_rooty()+50))

            self.initial_focus.focus_set()

            self.wait_window(self)

    def body(self, master, text1, text2, opt):
        if __name__ == "__main__" or self.parm:

            ttk.Label(master, text=text1).grid(row=0)
            ttk.Label(master, text=text2).grid(row=1)

            self.e1 = ttk.Entry(master)
            self.e2 = ttk.Entry(master)
            if opt:
                self.e2.configure(show="*")

            self.e1.grid(row=0, column=1)
            self.e2.grid(row=1, column=1)
            return self.e1  # initial focus

    def buttonbox(self):
        if __name__ == "__main__" or self.parm:
            # add standard button box. override if you don't want the
            # standard buttons

            box = Frame(self)

            w = ttk.Button(box, text="OK", width=10, command=self.ok, default=ACTIVE)
            w.pack(side=LEFT, padx=5, pady=5)
            w = ttk.Button(box, text="Cancel", width=10, command=self.cancel)
            w.pack(side=LEFT, padx=5, pady=5)

            self.bind("<Return>", self.ok)
            self.bind("<Escape>", self.cancel)

            box.pack()

    def ok(self, event=None):
        if __name__ == "__main__" or self.parm:
            self.withdraw()
            self.update_idletasks()

            self.apply()

            self.cancel()

    def cancel(self, event=None):
        if __name__ == "__main__" or self.parm:
            if not self.result:
                self.result = "cancelled"
            # put focus back to the parent window
            self.parent.focus_set()
            self.destroy()

    def apply(self):
        if __name__ == "__main__" or self.parm:
            try:
                first = str(self.e1.get())
                second = str(self.e2.get())
                self.result = (first, second)
            except ValueError:
                tkMessageBox.showwarning(
                    "Bad input",
                    "Illegal values, please try again")