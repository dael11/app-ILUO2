import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
import json, os, unicodedata
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt

# ── ARCHIVOS ────────────────────────────────────────────────────────
ARCH_EMP = "empleados.json"
ARCH_REL = "relaciones.json"
ARCH_CAT = "catalogo.json"

def cargar(ruta, default):
    if os.path.exists(ruta):
        with open(ruta, "r", encoding="utf-8") as f:
            return json.load(f)
    return default

def guardar(ruta, data):
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

TRABAJADORES = cargar(ARCH_EMP, [])
RELACIONES   = cargar(ARCH_REL, [])
_cat_def     = {"maquinas": [], "prs": ["PR-001 Ensamble A","PR-002 Soldadura B","PR-003 Inspeccion C"]}
CATALOGO     = cargar(ARCH_CAT, _cat_def)
if "maquinas" not in CATALOGO: CATALOGO["maquinas"] = []
if "prs"      not in CATALOGO: CATALOGO["prs"]      = _cat_def["prs"]
guardar(ARCH_CAT, CATALOGO)

def _norm(txt):
    return unicodedata.normalize("NFD", txt).encode("ascii","ignore").decode().lower().strip()

LETRAS_ILUO  = ["I","L","U","O"]
NOMBRES_ILUO = ["Instruido","Listo","Unico","Operador"]
COLORES_ILUO = ["#00c853","#2962ff","#ffa726","#d50000"]

def porcentaje(iluo): return sum(iluo)*25

# ── TEMAS ───────────────────────────────────────────────────────────
TEMAS = {
    "Oscuro": {
        "bg_dark":  "#12131f", "bg_panel": "#1a1c2e", "bg_card":  "#22243a",
        "accent1":  "#5c6bc0", "accent2":  "#26c6da", "danger":   "#ef5350",
        "success":  "#66bb6a", "warning":  "#ffa726", "purple":   "#ab47bc",
        "text":     "#e8eaf6", "subtext":  "#9fa8da", "sep":      "#333755",
        "entry_fg": "#e8eaf6", "lista_bg": "#22243a", "lista_fg": "#e8eaf6",
        "fig_bg":   "#1a1c2e",
    },
    "Claro": {
        "bg_dark":  "#f0f2f5", "bg_panel": "#ffffff", "bg_card":  "#e8edf2",
        "accent1":  "#3949ab", "accent2":  "#0097a7", "danger":   "#e53935",
        "success":  "#43a047", "warning":  "#f57c00", "purple":   "#8e24aa",
        "text":     "#1a1a2e", "subtext":  "#455a64", "sep":      "#b0bec5",
        "entry_fg": "#1a1a2e", "lista_bg": "#e8edf2", "lista_fg": "#1a1a2e",
        "fig_bg":   "#ffffff",
    },
}
TEMA_ACTUAL = "Oscuro"
C = dict(TEMAS[TEMA_ACTUAL])

def boton(parent, texto, comando, color, ancho=18):
    return tk.Button(parent, text=texto, command=comando,
        bg=color, fg="white", font=("Segoe UI", 11, "bold"),
        padx=12, pady=8, bd=0, cursor="hand2",
        activebackground=color, activeforeground="white",
        width=ancho, relief="flat")

def sep(parent, pady=5):
    f = tk.Frame(parent, bg=C["sep"], height=1)
    f.pack(fill="x", pady=pady)
    return f


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Dashboard Operador")
        self.geometry("1280x720")
        self.configure(bg=C["bg_dark"])
        self.resizable(True, True)
        self.var_buscar  = tk.StringVar()
        self.var_nomina  = tk.StringVar()
        self.var_nombre  = tk.StringVar()
        self.var_maquina = tk.StringVar()
        self.var_pr      = tk.StringVar()
        self._popup_busq = None
        self.var_buscar.trace_add("write", self._buscar_live)
        self.ui()
        self.grafico()

    # ── TEMA ────────────────────────────────────────────────────────
    def cambiar_tema(self):
        global TEMA_ACTUAL, C
        TEMA_ACTUAL = "Claro" if TEMA_ACTUAL == "Oscuro" else "Oscuro"
        C.update(TEMAS[TEMA_ACTUAL])
        # Destruir y reconstruir la UI
        for w in self.winfo_children():
            w.destroy()
        self.configure(bg=C["bg_dark"])
        self._popup_busq = None
        self.ui()
        self.grafico()

    # ── UI PRINCIPAL ────────────────────────────────────────────────
    def ui(self):
        # Barra superior
        top = tk.Frame(self, bg=C["bg_panel"], height=76)
        top.pack(fill="x")
        top.pack_propagate(False)

        tk.Label(top, text="Dashboard Operador",
                 fg=C["accent2"], bg=C["bg_panel"],
                 font=("Segoe UI", 16, "bold")).pack(side="left", padx=20)

        # Botón tema a la izquierda después del título
        self.btn_tema = tk.Button(top, text="☀ Tema",
            command=self.cambiar_tema,
            bg=C["bg_card"], fg=C["text"],
            font=("Segoe UI", 10, "bold"),
            padx=10, pady=6, bd=0, cursor="hand2",
            activebackground=C["accent1"], activeforeground="white",
            relief="flat")
        self.btn_tema.pack(side="left", padx=8, pady=20)

        # Buscador con lista desplegable
        bf = tk.Frame(top, bg=C["bg_panel"])
        bf.pack(side="left", padx=10, pady=18)

        self.entry_buscar = tk.Entry(bf, textvariable=self.var_buscar,
                 font=("Segoe UI", 14), width=30,
                 bg=C["bg_card"], fg=C["entry_fg"],
                 insertbackground=C["text"], relief="flat", bd=8)
        self.entry_buscar.pack(side="left", ipady=6)
        self.entry_buscar.bind("<Escape>", lambda e: self._cerrar_popup())
        self.entry_buscar.bind("<Down>",   lambda e: self._popup_focus())
        self.entry_buscar.bind("<Return>", lambda e: self.buscar_directo())

        boton(bf, "Buscar", self.buscar_directo, C["accent1"], 9).pack(side="left", padx=6)

        # Botones derecha
        for txt, cmd, col in [
            ("Eliminar",  self.eliminar,  C["danger"]),
            ("Editar",    self.editar,    C["success"]),
            ("Catalogo",  self.catalogo,  C["purple"]),
            ("Registrar", self.registrar, C["accent1"]),
        ]:
            boton(top, txt, cmd, col, 11).pack(side="right", padx=5, pady=18)

        # Panel izquierdo
        left = tk.Frame(self, bg=C["bg_panel"], width=340)
        left.pack(side="left", fill="y", padx=(10,4), pady=10)
        left.pack_propagate(False)

        tk.Label(left, text="EMPLEADO SELECCIONADO",
                 fg=C["subtext"], bg=C["bg_panel"],
                 font=("Segoe UI", 9, "bold")).pack(pady=(16,0))
        sep(left)

        tk.Label(left, textvariable=self.var_nomina,
                 fg=C["accent2"], bg=C["bg_panel"],
                 font=("Segoe UI", 20, "bold")).pack(pady=(6,2))
        tk.Label(left, textvariable=self.var_nombre,
                 fg=C["text"], bg=C["bg_panel"],
                 font=("Segoe UI", 13)).pack()

        # Foto más grande
        ff = tk.Frame(left, bg=C["bg_card"], width=180, height=180)
        ff.pack(pady=12)
        ff.pack_propagate(False)
        self.foto = tk.Label(ff, text="Sin foto", fg=C["subtext"],
                             bg=C["bg_card"], font=("Segoe UI", 10))
        self.foto.place(relx=0.5, rely=0.5, anchor="center")

        sep(left)
        tk.Label(left, text="MAQUINA", fg=C["subtext"],
                 bg=C["bg_panel"], font=("Segoe UI", 9, "bold")).pack()
        self.combo_maquina = ttk.Combobox(left, textvariable=self.var_maquina,
                                          font=("Segoe UI", 12), width=26, state="readonly")
        self.combo_maquina.pack(pady=6, ipady=4)
        self.combo_maquina.bind("<<ComboboxSelected>>", self.cargar_pr)

        tk.Label(left, text="PR / PROCESO", fg=C["subtext"],
                 bg=C["bg_panel"], font=("Segoe UI", 9, "bold")).pack()
        self.combo_pr = ttk.Combobox(left, textvariable=self.var_pr,
                                     font=("Segoe UI", 12), width=26, state="readonly")
        self.combo_pr.pack(pady=6, ipady=4)
        self.combo_pr.bind("<<ComboboxSelected>>", self.actualizar)

        self.frame = tk.Frame(self, bg=C["bg_panel"])
        self.frame.pack(side="right", fill="both", expand=True, padx=(4,10), pady=10)

    # ── GRAFICO ─────────────────────────────────────────────────────
    def grafico(self):
        estilo = "default" if TEMA_ACTUAL == "Claro" else "dark_background"
        plt.style.use(estilo)
        self.fig, self.ax = plt.subplots(figsize=(5,5))
        self.fig.patch.set_facecolor(C["fig_bg"])
        self.ax.set_facecolor(C["fig_bg"])
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    # ── BUSCADOR LIVE ───────────────────────────────────────────────
    def _buscar_live(self, *args):
        texto = _norm(self.var_buscar.get())
        if not texto:
            self._cerrar_popup(); return

        resultados = [
            t for t in TRABAJADORES
            if texto in _norm(t["nombre"]) or texto in _norm(t["no_nom"])
        ]

        if not resultados:
            self._cerrar_popup(); return

        self._mostrar_popup(resultados)

    def _mostrar_popup(self, resultados):
        self._cerrar_popup()

        # Posición justo debajo del entry
        self.entry_buscar.update_idletasks()
        x = self.entry_buscar.winfo_rootx()
        y = self.entry_buscar.winfo_rooty() + self.entry_buscar.winfo_height() + 2
        w = self.entry_buscar.winfo_width() + 80

        popup = tk.Toplevel(self)
        popup.wm_overrideredirect(True)
        popup.geometry(f"{w}x{min(len(resultados)*36+6, 300)}+{x}+{y}")
        popup.configure(bg=C["bg_card"])
        popup.attributes("-topmost", True)
        self._popup_busq = popup

        lb = tk.Listbox(popup, bg=C["bg_card"], fg=C["text"],
                        font=("Segoe UI", 12), selectbackground=C["accent1"],
                        selectforeground="white",
                        relief="flat", bd=0,
                        activestyle="none")
        lb.pack(fill="both", expand=True, padx=2, pady=2)

        for t in resultados:
            lb.insert("end", f"  {t['no_nom']}  —  {t['nombre']}")

        def seleccionar(event=None):
            sel = lb.curselection()
            if not sel: return
            idx = sel[0]
            self._cargar_empleado(resultados[idx])
            self._cerrar_popup()

        lb.bind("<Double-Button-1>", seleccionar)
        lb.bind("<Return>", seleccionar)

        # Cerrar popup al hacer click fuera
        popup.bind("<FocusOut>", lambda e: self.after(100, self._cerrar_popup_si_perdio_foco))

    def _popup_focus(self):
        if self._popup_busq:
            for w in self._popup_busq.winfo_children():
                if isinstance(w, tk.Listbox):
                    w.focus_set()
                    if w.size() > 0:
                        w.selection_set(0)
                    break

    def _cerrar_popup(self):
        if self._popup_busq:
            try: self._popup_busq.destroy()
            except: pass
            self._popup_busq = None

    def _cerrar_popup_si_perdio_foco(self):
        if self._popup_busq:
            try:
                foco = self.focus_get()
                if foco and str(foco).startswith(str(self._popup_busq)):
                    return
                if foco == self.entry_buscar:
                    return
            except: pass
            self._cerrar_popup()

    def buscar_directo(self):
        texto = _norm(self.var_buscar.get())
        if not texto: return
        resultados = [
            t for t in TRABAJADORES
            if texto in _norm(t["nombre"]) or texto in _norm(t["no_nom"])
        ]
        if not resultados:
            messagebox.showinfo("Sin resultados", "No se encontro ningun empleado."); return
        self._cargar_empleado(resultados[0])
        self._cerrar_popup()

    def _cargar_empleado(self, t):
        self.var_nomina.set(t["no_nom"])
        self.var_nombre.set(t["nombre"])
        try:
            img = Image.open(t["foto"])
            img.thumbnail((170,170))
            img = ImageTk.PhotoImage(img)
            self.foto.config(image=img, text="")
            self.foto.image = img
        except:
            self.foto.config(image="", text="Sin foto")
        maquinas_emp = list(dict.fromkeys(
            r["maquina"] for r in RELACIONES if r["nomina"] == t["no_nom"]
        ))
        self.combo_maquina["values"] = maquinas_emp
        self.combo_pr["values"] = []
        self.var_maquina.set(""); self.var_pr.set("")
        self.ax.clear(); self.canvas.draw()

    # ── BUSCAR / PR / DONUT ─────────────────────────────────────────
    def cargar_pr(self, e=None):
        nom = self.var_nomina.get()
        maq = _norm(self.var_maquina.get())
        prs = list(dict.fromkeys(
            r["pr"] for r in RELACIONES
            if r["nomina"] == nom and _norm(r["maquina"]) == maq
        ))
        self.combo_pr["values"] = prs
        self.var_pr.set("")

    def actualizar(self, e=None):
        nom = self.var_nomina.get()
        maq = _norm(self.var_maquina.get())
        pr  = _norm(self.var_pr.get())
        for r in RELACIONES:
            if r["nomina"] == nom and _norm(r["maquina"]) == maq and _norm(r["pr"]) == pr:
                self.donut(r.get("ILUO", r.get("ILOU", [0,0,0,0])))

    def donut(self, iluo):
        colores = COLORES_ILUO
        final = [colores[i] if iluo[i] else "#aaa" for i in range(4)]
        tc = "#1a1a2e" if TEMA_ACTUAL == "Claro" else "white"
        self.ax.clear()
        self.ax.pie([1,1,1,1], labels=LETRAS_ILUO, colors=final,
                    wedgeprops=dict(width=0.38),
                    textprops={"color": tc, "fontsize":15, "fontweight":"bold"})
        self.ax.set_title(f"{porcentaje(iluo)}%", color=C["accent2"],
                          fontsize=24, fontweight="bold", pad=20)
        self.fig.patch.set_facecolor(C["fig_bg"])
        self.canvas.draw()

    def existe_nomina(self, nom):
        return any(t["no_nom"] == nom for t in TRABAJADORES)

    def _win(self, titulo, w=680, h=700):
        win = tk.Toplevel(self)
        win.title(titulo)
        win.geometry(f"{w}x{h}")
        win.configure(bg=C["bg_dark"])
        win.grab_set(); win.focus_force()
        win.resizable(False, False)
        return win

    def _campo(self, parent, etiqueta, var):
        tk.Label(parent, text=etiqueta, fg=C["subtext"], bg=parent["bg"],
                 font=("Segoe UI", 10, "bold"), anchor="w").pack(fill="x", padx=30, pady=(10,2))
        e = tk.Entry(parent, textvariable=var, font=("Segoe UI", 13),
                     bg=C["bg_card"], fg=C["entry_fg"],
                     insertbackground=C["text"], relief="flat", bd=8)
        e.pack(fill="x", padx=30, ipady=6)
        return e

    def _bloque_foto(self, win, ruta_var, foto_actual=""):
        sep(win, pady=6)
        tk.Label(win, text="FOTOGRAFIA", fg=C["subtext"], bg=C["bg_dark"],
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=30)
        fila = tk.Frame(win, bg=C["bg_dark"])
        fila.pack(fill="x", padx=30, pady=8)
        marco = tk.Frame(fila, bg=C["bg_card"], width=100, height=100)
        marco.pack(side="left"); marco.pack_propagate(False)
        prev = tk.Label(marco, text="Sin\nimagen", fg=C["subtext"],
                        bg=C["bg_card"], font=("Segoe UI", 9))
        prev.place(relx=0.5, rely=0.5, anchor="center")
        if foto_actual:
            try:
                img = Image.open(foto_actual); img.thumbnail((95,95))
                imgtk = ImageTk.PhotoImage(img)
                prev.config(image=imgtk, text=""); prev.image = imgtk
            except: pass
        info = tk.Label(fila, text=os.path.basename(foto_actual) or "Sin foto",
                        fg=C["subtext"], bg=C["bg_dark"], font=("Segoe UI",10))
        info.pack(side="left", padx=14)
        def elegir():
            f = filedialog.askopenfilename(parent=win, title="Seleccionar foto",
                filetypes=[("Imagenes","*.png *.jpg *.jpeg *.bmp *.gif")])
            if not f: return
            ruta_var.set(f); info.config(text=os.path.basename(f))
            try:
                img = Image.open(f); img.thumbnail((95,95))
                imgtk = ImageTk.PhotoImage(img)
                prev.config(image=imgtk, text=""); prev.image = imgtk
            except Exception as ex:
                messagebox.showerror("Error", str(ex), parent=win)
        boton(fila, "Elegir foto", elegir, C["accent1"], 12).pack(side="left", padx=10)

    def _bloque_asignaciones(self, win, asignaciones):
        sep(win, pady=6)
        tk.Label(win, text="ASIGNACIONES  (Maquina / PR / ILUO)",
                 fg=C["subtext"], bg=C["bg_dark"],
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=30)

        cont = tk.Frame(win, bg=C["bg_dark"])
        cont.pack(fill="x", padx=30, pady=(4,0))
        lb = tk.Listbox(cont, bg=C["lista_bg"], fg=C["lista_fg"],
                        font=("Segoe UI", 10), selectbackground=C["accent1"],
                        relief="flat", bd=0, height=4)
        lb.pack(fill="x", padx=4, pady=4)

        def refrescar():
            lb.delete(0, "end")
            for a in asignaciones:
                iluo = a.get("ILUO", a.get("ILOU", [0,0,0,0]))
                etq = "".join([LETRAS_ILUO[i] if iluo[i] else "-" for i in range(4)])
                lb.insert("end", f"  {a['maquina']:<18}  {a['pr']:<22}  {etq}")
        refrescar()

        fila = tk.Frame(win, bg=C["bg_dark"])
        fila.pack(fill="x", padx=30, pady=6)

        maq_v = tk.StringVar(); pr_v = tk.StringVar()
        cb_m = ttk.Combobox(fila, textvariable=maq_v, values=CATALOGO["maquinas"],
                            font=("Segoe UI", 11), width=16, state="readonly")
        cb_m.grid(row=0, column=0, padx=(0,6), ipady=4)
        cb_p = ttk.Combobox(fila, textvariable=pr_v, values=CATALOGO["prs"],
                            font=("Segoe UI", 11), width=20, state="readonly")
        cb_p.grid(row=0, column=1, padx=(0,6), ipady=4)

        # Botones ILUO más grandes
        iluo_vs = []
        for i, (letra, nombre) in enumerate(zip(LETRAS_ILUO, NOMBRES_ILUO)):
            v = tk.IntVar()
            f = tk.Frame(fila, bg=COLORES_ILUO[i], padx=8, pady=4)
            f.grid(row=0, column=2+i, padx=3)
            tk.Checkbutton(f, text=f"{letra}\n{nombre[:3]}", variable=v,
                           bg=COLORES_ILUO[i], fg="white",
                           selectcolor=COLORES_ILUO[i],
                           activebackground=COLORES_ILUO[i],
                           font=("Segoe UI", 10, "bold"),
                           justify="center",
                           relief="flat").pack()
            iluo_vs.append(v)

        def agregar():
            m = maq_v.get().strip(); p = pr_v.get().strip()
            if not m:
                messagebox.showwarning("Falta maquina", "Selecciona una maquina.", parent=win); return
            if not p:
                messagebox.showwarning("Falta PR", "Selecciona un PR.", parent=win); return
            for a in asignaciones:
                if a["maquina"] == m and a["pr"] == p:
                    messagebox.showwarning("Duplicado", f"Ya existe {m} / {p}.", parent=win); return
            iluo = [v.get() for v in iluo_vs]
            asignaciones.append({"maquina": m, "pr": p, "ILUO": iluo})
            refrescar()
            maq_v.set(""); pr_v.set("")
            for v in iluo_vs: v.set(0)

        def quitar():
            sel = lb.curselection()
            if not sel: return
            asignaciones.pop(sel[0]); refrescar()

        bf = tk.Frame(win, bg=C["bg_dark"])
        bf.pack(pady=4)
        boton(bf, "+ Agregar", agregar, C["success"], 12).pack(side="left", padx=6)
        boton(bf, "- Quitar",  quitar,  C["danger"],  12).pack(side="left", padx=6)

    # ── REGISTRAR ───────────────────────────────────────────────────
    def registrar(self):
        win = self._win("Registrar Empleado", 720, 820)
        tk.Label(win, text="NUEVO EMPLEADO",
                 fg=C["accent2"], bg=C["bg_dark"],
                 font=("Segoe UI", 18, "bold")).pack(pady=(20,4))
        sep(win, pady=4)
        nom = tk.StringVar(); nombre = tk.StringVar(); ruta_foto = tk.StringVar()
        self._campo(win, "Numero de Nomina", nom)
        self._campo(win, "Nombre Completo", nombre)
        self._bloque_foto(win, ruta_foto)
        asignaciones = []
        self._bloque_asignaciones(win, asignaciones)
        sep(win, pady=8)

        def guardar_all():
            n = nom.get().strip(); nb = nombre.get().strip()
            if not n or not nb:
                messagebox.showerror("Campos vacios", "Nomina y Nombre son obligatorios.", parent=win); return
            if self.existe_nomina(n):
                messagebox.showerror("Duplicada", f"Ya existe nomina {n}.", parent=win); return
            if not asignaciones:
                messagebox.showerror("Sin asignaciones", "Agrega al menos una maquina y PR.", parent=win); return
            TRABAJADORES.append({"no_nom": n, "nombre": nb, "foto": ruta_foto.get()})
            for a in asignaciones:
                RELACIONES.append({"nomina": n, "maquina": a["maquina"],
                                   "pr": a["pr"], "ILUO": a["ILUO"]})
            guardar(ARCH_EMP, TRABAJADORES); guardar(ARCH_REL, RELACIONES)
            messagebox.showinfo("Exito", f"'{nb}' registrado con {len(asignaciones)} asignacion(es).", parent=win)
            win.destroy()

        boton(win, "Guardar Empleado", guardar_all, C["success"], 22).pack(pady=6)
        boton(win, "Cancelar", win.destroy, "#888", 14).pack()

    # ── EDITAR ──────────────────────────────────────────────────────
    def editar(self):
        nom = self.var_nomina.get().strip()
        if not nom:
            messagebox.showwarning("Sin seleccion", "Primero busca y selecciona un empleado."); return
        emp = next((t for t in TRABAJADORES if t["no_nom"] == nom), None)
        if not emp:
            messagebox.showerror("Error", "Empleado no encontrado."); return

        win = self._win("Editar Empleado", 720, 860)
        tk.Label(win, text="EDITAR EMPLEADO",
                 fg=C["warning"], bg=C["bg_dark"],
                 font=("Segoe UI", 18, "bold")).pack(pady=(20,4))
        sep(win, pady=4)
        nombre_var = tk.StringVar(value=emp["nombre"])
        ruta_foto  = tk.StringVar(value=emp.get("foto",""))
        tk.Label(win, text=f"Nomina: {emp['no_nom']}",
                 fg=C["accent2"], bg=C["bg_dark"],
                 font=("Segoe UI", 14, "bold")).pack(pady=6)
        self._campo(win, "Nombre Completo", nombre_var)
        self._bloque_foto(win, ruta_foto, emp.get("foto",""))

        asignaciones = []
        for r in RELACIONES:
            if r["nomina"] == nom:
                d = dict(r)
                if "ILOU" in d and "ILUO" not in d:
                    d["ILUO"] = d.pop("ILOU")
                asignaciones.append(d)

        self._bloque_asignaciones(win, asignaciones)
        sep(win, pady=8)

        def guardar_edicion():
            nb = nombre_var.get().strip()
            if not nb:
                messagebox.showerror("Vacio", "El nombre no puede estar vacio.", parent=win); return
            if not asignaciones:
                messagebox.showerror("Sin asignaciones", "Debe haber al menos una asignacion.", parent=win); return
            emp["nombre"] = nb; emp["foto"] = ruta_foto.get()
            guardar(ARCH_EMP, TRABAJADORES)
            self.var_nombre.set(nb)
            global RELACIONES
            RELACIONES = [r for r in RELACIONES if r["nomina"] != nom]
            for a in asignaciones:
                RELACIONES.append({"nomina": nom, "maquina": a["maquina"],
                                   "pr": a["pr"], "ILUO": a["ILUO"]})
            guardar(ARCH_REL, RELACIONES)
            messagebox.showinfo("Actualizado", "Empleado actualizado correctamente.", parent=win)
            win.destroy()

        boton(win, "Guardar Cambios", guardar_edicion, C["success"], 22).pack(pady=6)
        boton(win, "Cancelar", win.destroy, "#888", 14).pack()

    # ── ELIMINAR ────────────────────────────────────────────────────
    def eliminar(self):
        nom = self.var_nomina.get().strip()
        if not nom:
            messagebox.showwarning("Sin seleccion", "Primero busca y selecciona un empleado."); return
        nombre_emp = self.var_nombre.get()
        if not messagebox.askyesno("Confirmar", f"Eliminar a {nombre_emp} ({nom})?"):
            return
        global TRABAJADORES, RELACIONES
        TRABAJADORES = [t for t in TRABAJADORES if t["no_nom"] != nom]
        RELACIONES   = [r for r in RELACIONES   if r["nomina"] != nom]
        guardar(ARCH_EMP, TRABAJADORES); guardar(ARCH_REL, RELACIONES)
        self.var_nomina.set(""); self.var_nombre.set("")
        self.foto.config(image="", text="Sin foto")
        self.combo_maquina["values"] = []; self.combo_pr["values"] = []
        self.var_maquina.set(""); self.var_pr.set("")
        self.ax.clear(); self.canvas.draw()
        messagebox.showinfo("Eliminado", f"Empleado {nom} eliminado.")

    # ── CATALOGO ────────────────────────────────────────────────────
    def catalogo(self):
        win = self._win("Catalogo", 740, 620)
        tk.Label(win, text="CATALOGO DE MAQUINAS Y PRs",
                 fg=C["purple"], bg=C["bg_dark"],
                 font=("Segoe UI", 18, "bold")).pack(pady=(20,4))
        sep(win, pady=4)

        main = tk.Frame(win, bg=C["bg_dark"])
        main.pack(fill="both", expand=True, padx=20, pady=10)
        main.columnconfigure(0, weight=1); main.columnconfigure(1, weight=1)

        def _panel(key, titulo, color, col_idx):
            pf = tk.Frame(main, bg=C["bg_panel"])
            pf.grid(row=0, column=col_idx, sticky="nsew",
                    padx=(0, 8) if col_idx == 0 else (8, 0))
            tk.Label(pf, text=titulo, fg=color, bg=C["bg_panel"],
                     font=("Segoe UI", 13, "bold")).pack(pady=10)
            tk.Label(pf, text="Escribe y presiona + Agregar o Enter",
                     fg=C["subtext"], bg=C["bg_panel"], font=("Segoe UI", 9)).pack()

            lb = tk.Listbox(pf, bg=C["lista_bg"], fg=C["lista_fg"],
                            font=("Segoe UI", 11), selectbackground=C["accent1"],
                            relief="flat", bd=0, height=11)
            lb.pack(fill="both", expand=True, padx=10, pady=8)
            for item in CATALOGO[key]:
                lb.insert("end", item)

            var_nuevo = tk.StringVar()
            entry = tk.Entry(pf, textvariable=var_nuevo,
                     bg=C["bg_card"], fg=C["entry_fg"],
                     insertbackground=C["text"], font=("Segoe UI", 11),
                     relief="flat", bd=6)
            entry.pack(fill="x", padx=10, pady=(0,4), ipady=6)

            def agregar(event=None, _k=key, _lb=lb, _var=var_nuevo, _e=entry):
                txt = _var.get().strip()
                if not txt: return
                if txt in CATALOGO[_k]:
                    messagebox.showwarning("Duplicado", f"'{txt}' ya existe.", parent=win)
                    return
                CATALOGO[_k].append(txt)
                _lb.insert("end", txt)
                guardar(ARCH_CAT, CATALOGO)
                _var.set("")
                _e.focus()

            def eliminar_item(_k=key, _lb=lb):
                sel = _lb.curselection()
                if not sel:
                    messagebox.showinfo("Sin seleccion", "Selecciona un elemento.", parent=win); return
                item = _lb.get(sel[0])
                if messagebox.askyesno("Confirmar", f"Eliminar '{item}'?", parent=win):
                    CATALOGO[_k].remove(item)
                    _lb.delete(sel[0])
                    guardar(ARCH_CAT, CATALOGO)

            entry.bind("<Return>", agregar)
            br = tk.Frame(pf, bg=C["bg_panel"])
            br.pack(pady=4)
            boton(br, "+ Agregar", agregar, C["success"], 13).pack(side="left", padx=6)
            boton(br, "- Eliminar", eliminar_item, C["danger"], 11).pack(side="left", padx=6)

        _panel("maquinas", "MAQUINAS",      C["accent2"], 0)
        _panel("prs",      "PRs / PROCESOS", C["warning"], 1)

        sep(win, pady=6)
        boton(win, "Cerrar", win.destroy, "#888", 14).pack(pady=8)


if __name__ == "__main__":
    App().mainloop()
