# tools/inspect_placeholders.py
"""
Inspecciona un JSON de placeholders (generado junto al DOCX)
y vuelca automáticamente cada bloque largo en /resultados_pruebas/.
"""

import json
import argparse
import os
import sys
from textwrap import shorten

DEF_KEYS = [
    "PH_Antecedentes",
    "PH_Consumo",
    "alternativas_desc",
    "alternativas_val",
    "alternativas_just",
]

def main():
    ap = argparse.ArgumentParser(description="Inspecciona un JSON de placeholders y guarda los bloques largos.")
    ap.add_argument(
        "json_path",
        help="Ruta al archivo *.placeholders.json generado junto al DOCX"
    )
    ap.add_argument(
        "--keys",
        nargs="*",
        default=DEF_KEYS,
        help="Claves a mostrar completas (por defecto las principales)"
    )
    ap.add_argument(
        "--preview",
        type=int,
        default=220,
        help="Tamaño del preview (por defecto 220 chars)"
    )
    args = ap.parse_args()

    if not os.path.isfile(args.json_path):
        print(f"❌ No existe el archivo: {args.json_path}")
        sys.exit(1)

    with open(args.json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # === Carpeta fija de salida ===
    out_dir = os.path.join(os.getcwd(), "resultados_pruebas")
    os.makedirs(out_dir, exist_ok=True)

    print(f"\n📁 Guardando resultados en: {out_dir}\n")

    # === Resumen general ===
    print("=== RESUMEN PLACEHOLDERS ===")
    keys_sorted = sorted(data.keys())
    for k in keys_sorted:
        v = data.get(k)
        s = "" if v is None else str(v)
        print(f"- {k}: {len(s)} chars")

    # === Detalle de las claves pedidas ===
    print("\n=== DETALLE (texto completo) ===")
    for k in args.keys:
        v = data.get(k, "")
        s = "" if v is None else str(v)
        print(f"\n[{k}]  len={len(s)}")
        if len(s) == 0:
            print("(vacío)")
        else:
            prev = shorten(s.replace("\n", " ⏎ "), width=args.preview, placeholder="…")
            print(f"preview: {prev}")
            print("-" * 60)
            print(s)
            print("-" * 60)

        # Guardar en archivo .txt
        out_file = os.path.join(out_dir, f"{k}.txt")
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(s)
        print(f"💾 Guardado: {out_file}")

    print("\n✅ Finalizado. Todos los bloques se guardaron en resultados_pruebas/")

if __name__ == "__main__":
    main()
