
import hashlib
import json
import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


def hash_table(file_route):
    """Kiszámítja egy fájl SHA-256 hash értékét."""
    hasher = hashlib.sha256()
    with open(file_route, "rb") as file:
        while chunk := file.read(4096):
            hasher.update(chunk)
    return hasher.hexdigest()


def mappa_fajljai_es_hashei(direct):
    """Bejárja a könyvtárat és legenerálja a relatív utakhoz tartozó hasheket."""
    file_datas = {}
    if not os.path.exists(direct):
        return file_datas
    for root, smalldirectory, files in os.walk(direct):
        
        smalldirectory[:] = [d for d in smalldirectory if not d.startswith(".")]
        for file in files:
            if file.startswith("."):
                continue
            whole_path = os.path.join(root, file)
            relative_path = os.path.relpath(whole_path, direct)
            file_datas[relative_path] = hash_table(whole_path)
    return file_datas


def get_commit_manifest(konyvtar, commit_name):
    """Beolvassa egy adott commit .manifest.json tartalmát."""
    manifest_file = os.path.join(konyvtar, commit_name, ".manifest.json")
    if os.path.exists(manifest_file):
        with open(manifest_file, "r", encoding="utf-8") as file:
            return json.load(file)
    return {}




app = tk.Tk()
app.title("Verziókezelő")
app.geometry("540x500")
app.resizable(False, False)

munkamappa = tk.StringVar()


def commit_lista_frissites():
    """Megkeresi és rendezi a létező commit mappákat."""
    konyvtar = munkamappa.get()
    if not konyvtar or not os.path.exists(konyvtar):
        combo_commitok["values"] = []
        combo_commitok.set("")
        return

    commitok = [
        d
        for d in os.listdir(konyvtar)
        if os.path.isdir(os.path.join(konyvtar, d)) and d.startswith(".")
    ]
    combo_commitok["values"] = commitok
    if commitok:
        if combo_commitok.get() not in commitok:
            combo_commitok.current(len(commitok) - 1)
    else:
        combo_commitok.set("")


def mappa_kivalasztas():
    kivalasztott = filedialog.askdirectory(title="Válassz munkamappát")
    if kivalasztott:
        munkamappa.set(kivalasztott)
        commit_lista_frissites()


def commit_letrehozas():
    konyvtar = munkamappa.get()
    nev = entry_commit_nev.get().strip()

    if not konyvtar:
        messagebox.showerror("Hiba", "Előbb válassz ki egy munkamappát!")
        return
    if not nev:
        messagebox.showerror("Hiba", "Adj meg egy commit nevet!")
        return

    if not nev.startswith("."):
        nev = "." + nev

    cel_mappa = os.path.join(konyvtar, nev)
    if os.path.exists(cel_mappa):
        messagebox.showerror(
            "Hiba", "Már létezik ilyen nevű commit mentés ebben a mappában!"
        )
        return

    aktualis_fajlok = mappa_fajljai_es_hashei(konyvtar)
    if not aktualis_fajlok:
        messagebox.showwarning(
            "Figyelem", "A munkamappa üres, nincs mit menteni!"
        )
        return

    elozo_commit_nev = combo_commitok.get()
    elozo_manifest = (
        get_commit_manifest(konyvtar, elozo_commit_nev)
        if elozo_commit_nev
        else {}
    )

    os.makedirs(cel_mappa)
    uj_manifest = {}
    masolt_db = 0
    orokolt_db = 0

    for rel_ut, h in aktualis_fajlok.items():
        if (
            rel_ut in elozo_manifest
            and elozo_manifest[rel_ut].get("hash") == h
        ):
          
            uj_manifest[rel_ut] = {
                "hash": h,
                "forras_commit": elozo_manifest[rel_ut]["forras_commit"],
            }
            orokolt_db += 1
        else:
            
            forras_fajl = os.path.join(konyvtar, rel_ut)
            cel_fajl = os.path.join(cel_mappa, rel_ut)
            os.makedirs(os.path.dirname(cel_fajl), exist_ok=True)
            shutil.copy2(forras_fajl, cel_fajl)

            uj_manifest[rel_ut] = {"hash": h, "forras_commit": nev}
            masolt_db += 1

    
    with open(
        os.path.join(cel_mappa, ".manifest.json"), "w", encoding="utf-8"
    ) as f:
        json.dump(uj_manifest, f, indent=2)

    entry_commit_nev.delete(0, tk.END)
    commit_lista_frissites()
    combo_commitok.set(nev)

    messagebox.showinfo(
        "Siker",
        f"Commit elkészült: {nev}\n"
        f"• Újonnan elmentett fájlok: {masolt_db} db\n"
        f"• Tárhelykímélő (korábbi verzióból hivatkozott) fájlok: {orokolt_db} db",
    )


def commit_visszaallitas():
    konyvtar = munkamappa.get()
    kivalasztott_commit = combo_commitok.get()

    if not konyvtar or not kivalasztott_commit:
        messagebox.showerror(
            "Hiba", "Válassz ki egy munkamappát és egy commitot!"
        )
        return

    if not messagebox.askyesno(
        "Megerősítés",
        f"Visszaállítod a munkamappát a(z) '{kivalasztott_commit}' állapotra?\nA nem mentett változtatások elvesznek!",
    ):
        return

    manifest = get_commit_manifest(konyvtar, kivalasztott_commit)
    if not manifest:
        messagebox.showerror(
            "Hiba", "A commit jegyzéke (.manifest.json) sérült vagy hiányzik!"
        )
        return

   
    for elem in os.listdir(konyvtar):
        if elem.startswith("."):
            continue
        cel = os.path.join(konyvtar, elem)
        if os.path.isdir(cel):
            shutil.rmtree(cel)
        else:
            os.remove(cel)

    
    for rel_ut, info in manifest.items():
        forras_commit = info["forras_commit"]
        fizikai_forras = os.path.join(konyvtar, forras_commit, rel_ut)
        cel_ut = os.path.join(konyvtar, rel_ut)

        os.makedirs(os.path.dirname(cel_ut), exist_ok=True)
        shutil.copy2(fizikai_forras, cel_ut)

    messagebox.showinfo(
        "Siker", f"A munkamappa visszaállítva a(z) {kivalasztott_commit} pontra!"
    )


def commit_torles():
    konyvtar = munkamappa.get()
    kivalasztott_commit = combo_commitok.get()

    if not konyvtar or not kivalasztott_commit:
        messagebox.showerror("Hiba", "Válassz ki egy törlendő commitot!")
        return

    osszes_commit = [
        d
        for d in os.listdir(konyvtar)
        if os.path.isdir(os.path.join(konyvtar, d)) and d.startswith(".")
    ]
    fuggosegek = []
    for c in osszes_commit:
        if c == kivalasztott_commit:
            continue
        m = get_commit_manifest(konyvtar, c)
        for _, info in m.items():
            if info.get("forras_commit") == kivalasztott_commit:
                fuggosegek.append(c)
                break

    if fuggosegek:
        messagebox.showerror(
            "Nem törölhető!",
            f"A(z) '{kivalasztott_commit}' mentést nem törölheted, mert a következő későbbi commit(ok) innen örökölnek fájlokat:\n"
            + ", ".join(fuggosegek),
        )
        return

    if messagebox.askyesno(
        "Törlés megerősítése",
        f"Biztosan törölni szeretnéd a(z) '{kivalasztott_commit}' mentést?",
    ):
        shutil.rmtree(os.path.join(konyvtar, kivalasztott_commit))
        commit_lista_frissites()
        messagebox.showinfo(
            "Törölve", "A commit sikeresen törölve, tárhely felszabadítva!"
        )


def ellenorzes_szukseges_e():
    konyvtar = munkamappa.get()
    kivalasztott_commit = combo_commitok.get()

    if not konyvtar:
        messagebox.showerror("Hiba", "Válassz ki egy munkamappát!")
        return
    if not kivalasztott_commit:
        messagebox.showinfo("Infó", "Még nincs korábbi commit rögzítve!")
        return

    aktualis_hashek = mappa_fajljai_es_hashei(konyvtar)
    manifest = get_commit_manifest(konyvtar, kivalasztott_commit)
    mentett_hashek = {fajl: info["hash"] for fajl, info in manifest.items()}

    if aktualis_hashek == mentett_hashek:
        messagebox.showinfo(
            "Eredmény",
            f"Egyetlen fájl hash-e sem változott a(z) '{kivalasztott_commit}' commithoz képest.\n\nÚj commit NEM szükséges!",
        )
    else:
        modosult = []
        uj = []
        torolt = []

        for f, h in aktualis_hashek.items():
            if f not in mentett_hashek:
                uj.append(f)
            elif mentett_hashek[f] != h:
                modosult.append(f)

        for f in mentett_hashek:
            if f not in aktualis_hashek:
                torolt.append(f)

        reszletek = ""
        if uj:
            reszletek += f"\nÚj fájlok: {len(uj)} db"
        if modosult:
            reszletek += f"\nMódosult fájlok: {len(modosult)} db"
        if torolt:
            reszletek += f"\nTörölt fájlok: {len(torolt)} db"

        messagebox.showwarning(
            "Eredmény",
            f"Változás történt a(z) '{kivalasztott_commit}' commithoz képest!{reszletek}\n\nÚj commit szükséges!",
        )




frame_mappa = tk.LabelFrame(app, text="Munkamappa", padx=10, pady=8)
frame_mappa.pack(fill="x", padx=15, pady=5)
entry_mappa = tk.Entry(
    frame_mappa, textvariable=munkamappa, width=44, state="readonly"
)
entry_mappa.pack(side="left", padx=(0, 5))
btn_talloz = tk.Button(frame_mappa, text="Tallózás...", command=mappa_kivalasztas)
btn_talloz.pack(side="left")

frame_commit = tk.LabelFrame(app, text="Új Commit mentése", padx=10, pady=8)
frame_commit.pack(fill="x", padx=15, pady=5)
lbl_nev = tk.Label(frame_commit, text="Commit neve (automatikusan ponttal indul):")
lbl_nev.pack(anchor="w")
entry_commit_nev = tk.Entry(frame_commit, width=40)
entry_commit_nev.pack(fill="x", pady=4)
btn_commit = tk.Button(
    frame_commit,
    text="Commit mentése (Csak a változások tárolása)",
    bg="#d1e7dd",
    command=commit_letrehozas,
)
btn_commit.pack(fill="x")

frame_kezeles = tk.LabelFrame(
    app, text="Mentett Commitok kezelése", padx=10, pady=8
)
frame_kezeles.pack(fill="x", padx=15, pady=5)
combo_commitok = ttk.Combobox(frame_kezeles, state="readonly")
combo_commitok.pack(fill="x", pady=(0, 8))
btn_visszaallit = tk.Button(
    frame_kezeles,
    text="Kiválasztott állapot visszaállítása",
    bg="#cfe2ff",
    command=commit_visszaallitas,
)
btn_visszaallit.pack(fill="x", pady=2)
btn_torol = tk.Button(
    frame_kezeles,
    text="Kiválasztott commit törlése",
    bg="#f8d7da",
    command=commit_torles,
)
btn_torol.pack(fill="x", pady=2)

frame_check = tk.LabelFrame(app, text="Változásvizsgálat", padx=10, pady=8)
frame_check.pack(fill="x", padx=15, pady=5)
btn_ellenoriz = tk.Button(
    frame_check,
    text="Commit szükséges-e? (Hash összehasonlítás)",
    font=("Arial", 9, "bold"),
    command=ellenorzes_szukseges_e,
)
btn_ellenoriz.pack(fill="x")

app.mainloop()