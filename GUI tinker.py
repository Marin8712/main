import tkinter as tk
from tkinter import messagebox
import math


def krijo_kalkulator():
    dritarja = tk.Tk()
    dritarja.title("Kalkulator i Plote")
    dritarja.geometry("430x620")
    dritarja.minsize(380, 560)
    dritarja.configure(bg="#111111")

    variabla_shprehjes = tk.StringVar()
    rezultati_fundit = tk.StringVar(value="0")

    ekrani = tk.Entry(
        dritarja,
        textvariable=variabla_shprehjes,
        font=("Segoe UI", 24),
        bg="#f3f6f8",
        justify="right",
        bd=6,
        relief="flat",
    )
    ekrani.grid(row=0, column=0, columnspan=5, padx=10, pady=12, sticky="nsew")

    for kolona in range(5):
        dritarja.grid_columnconfigure(kolona, weight=1)
    for rreshti in range(1, 8):
        dritarja.grid_rowconfigure(rreshti, weight=1)

    funksione_lejuara = {
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "sqrt": math.sqrt,
        "log": math.log10,
        "ln": math.log,
        "abs": abs,
        "pi": math.pi,
        "e": math.e,
    }

    def shto_tekst(teksti):
        ekrani.insert(tk.END, teksti)

    def pastro_gjithcka():
        variabla_shprehjes.set("")

    def fshi_karakterin_fundit():
        aktuale = variabla_shprehjes.get()
        if aktuale:
            variabla_shprehjes.set(aktuale[:-1])

    def perqindje():
        try:
            vl = vlereso_shprehjen(variabla_shprehjes.get())
            variabla_shprehjes.set(str(vl / 100))
        except Exception:
            messagebox.showerror("Gabim", "Nuk u llogarit dot perqindja.")

    def ndrysho_shenjen():
        try:
            tekst = variabla_shprehjes.get().strip()
            if not tekst:
                return
            vl = vlereso_shprehjen(tekst)
            variabla_shprehjes.set(str(-vl))
        except Exception:
            messagebox.showerror("Gabim", "Nuk u ndryshua dot shenja.")

    def shto_ans():
        shto_tekst(rezultati_fundit.get())

    def vlereso_shprehjen(shprehja):
        shprehja = shprehja.replace("^", "**")
        shprehja = shprehja.replace("×", "*").replace("÷", "/")
        rezultat = eval(shprehja, {"__builtins__": {}}, funksione_lejuara)
        if isinstance(rezultat, float):
            return round(rezultat, 12)
        return rezultat

    def llogarit_rezultatin():
        try:
            shprehja = variabla_shprehjes.get().strip()
            if not shprehja:
                return
            rezultat = vlereso_shprehjen(shprehja)
            rezultati_fundit.set(str(rezultat))
            variabla_shprehjes.set(str(rezultat))
        except ZeroDivisionError:
            messagebox.showerror("Gabim", "Ndarje me zero nuk lejohet.")
            variabla_shprehjes.set("")
        except Exception:
            messagebox.showerror("Gabim", "Shprehje e pavlefshme.")

    butonat = [
        [("C", "danger", pastro_gjithcka), ("DEL", "danger", fshi_karakterin_fundit), ("(", "op", lambda: shto_tekst("(")), (")", "op", lambda: shto_tekst(")")), ("/", "op", lambda: shto_tekst("/"))],
        [("sin", "func", lambda: shto_tekst("sin(")), ("cos", "func", lambda: shto_tekst("cos(")), ("tan", "func", lambda: shto_tekst("tan(")), ("sqrt", "func", lambda: shto_tekst("sqrt(")), ("*", "op", lambda: shto_tekst("*"))],
        [("log", "func", lambda: shto_tekst("log(")), ("ln", "func", lambda: shto_tekst("ln(")), ("pi", "func", lambda: shto_tekst("pi")), ("e", "func", lambda: shto_tekst("e")), ("-", "op", lambda: shto_tekst("-"))],
        [("7", "num", lambda: shto_tekst("7")), ("8", "num", lambda: shto_tekst("8")), ("9", "num", lambda: shto_tekst("9")), ("^", "op", lambda: shto_tekst("^")), ("+", "op", lambda: shto_tekst("+"))],
        [("4", "num", lambda: shto_tekst("4")), ("5", "num", lambda: shto_tekst("5")), ("6", "num", lambda: shto_tekst("6")), ("%", "func", perqindje), ("x^2", "func", lambda: shto_tekst("**2"))],
        [("1", "num", lambda: shto_tekst("1")), ("2", "num", lambda: shto_tekst("2")), ("3", "num", lambda: shto_tekst("3")), ("abs", "func", lambda: shto_tekst("abs(")), (".", "num", lambda: shto_tekst("."))],
        [("0", "num", lambda: shto_tekst("0")), ("00", "num", lambda: shto_tekst("00")), ("Ans", "func", shto_ans), ("+/-", "func", ndrysho_shenjen), ("=", "equal", llogarit_rezultatin)],
    ]

    ngjyra = {
        "num": {"bg": "#2d3436", "fg": "#f5f6fa"},
        "op": {"bg": "#0984e3", "fg": "white"},
        "func": {"bg": "#e17055", "fg": "white"},
        "equal": {"bg": "#00b894", "fg": "white"},
        "danger": {"bg": "#d63031", "fg": "white"},
    }

    for rreshti, lista_butonash in enumerate(butonat, start=1):
        for kolona, (etiketa, tipi, komanda) in enumerate(lista_butonash):
            stil = ngjyra.get(tipi, ngjyra["num"])
            tk.Button(
                dritarja,
                text=etiketa,
                font=("Segoe UI", 14, "bold"),
                bg=stil["bg"],
                fg=stil["fg"],
                relief="flat",
                activebackground="#3f3f3f",
                activeforeground="white",
                command=komanda,
            ).grid(row=rreshti, column=kolona, sticky="nsew", padx=2, pady=2)

    ekrani.focus_set()
    dritarja.bind("<Return>", lambda _: llogarit_rezultatin())
    dritarja.bind("<Escape>", lambda _: pastro_gjithcka())

    dritarja.mainloop()


krijo_kalkulator()
