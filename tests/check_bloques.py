# check_bloques.py
import sys, os, json
from core.extraccion.bloques_textuales import extraer_bloques_literal

def leer_texto(ruta):
    ext = os.path.splitext(ruta)[1].lower()
    if ext == ".txt":
        return open(ruta, encoding="utf-8").read()
    # si pasas el PDF directo, lee el .raw.txt que ya generas con tu debug
    raise SystemExit("Pásame el .raw.txt/.cleaned.txt/.noindex.txt para esta prueba.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python check_bloques.py Proyecto.noindex.txt")
        sys.exit(1)

    ruta_txt = sys.argv[1]
    texto = leer_texto(ruta_txt)

    bloques = extraer_bloques_literal(texto)

    print("\n=== RESUMEN BLOQUES ===")
    for k, v in bloques.items():
        print(f"{k}: {len(v)} chars")
        preview = (v[:200] + "…") if v else "[VACÍO]"
        print(preview.replace("\n", " "))
        print("-" * 60)

    # guardar cada bloque a fichero para inspección manual
    base = os.path.splitext(ruta_txt)[0]
    outdir = f"{base}_bloques"
    os.makedirs(outdir, exist_ok=True)
    for k, v in bloques.items():
        with open(os.path.join(outdir, f"{k}.txt"), "w", encoding="utf-8") as f:
            f.write(v or "")
    print(f"\n💾 Guardados los bloques en: {outdir}")
