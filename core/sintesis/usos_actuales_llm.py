from pathlib import Path
import os, sys, json, subprocess, time
from datetime import datetime
from dotenv import load_dotenv

# --- rutas y entorno ---
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.extraccion.llm_utils import get_client

load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=True)

# --- utilidades de impresión ---
def step(msg): 
    print(f"UA_STEP: {msg}", flush=True)

def warn(msg): 
    print(f"UA_WARN: {msg}", flush=True)

def done(path_img=None):
    print("UA_RESULT: OK", flush=True)
    if path_img:
        print(f"UA_CAPTURE: {path_img}", flush=True)

# --- función principal ---
def usos_actuales_llm(json_path: Path):
    """Genera texto técnico de 'Usos actuales del terreno' y lanza la captura CH Duero."""

    # === 1. Cargar JSON ===
    if not json_path.exists():
        print(f"❌ No existe JSON: {json_path}", flush=True)
        sys.exit(1)

    step(f"JSON de trabajo => {json_path.name}")
    data = json.loads(json_path.read_text(encoding="utf-8"))

    municipio = (
        data.get("municipio")
        or data.get("PH_Localizacion", {}).get("municipio")
        or "municipio desconocido"
    )
    loc = data.get("localizacion") or {}
    parcela = loc.get("parcela") or data.get("parcela") or ""
    poligono = loc.get("poligono") or data.get("poligono") or ""

    # === 2. Generar texto técnico con el modelo ===
    client = get_client()
    prompt = f"""
    Redacta un párrafo técnico, sin encabezado ni título, describiendo los usos actuales del terreno 
    en el ámbito del Estudio de Impacto Ambiental. Explica la ocupación actual, los cultivos o 
    coberturas vegetales, las construcciones próximas y el estado general del terreno en 
    {municipio}, polígono {poligono}, parcela {parcela}. 

    Debe tener tono técnico-administrativo, extensión media (6–8 líneas), y estar redactado 
    en español de España. No incluyas ningún título, subtítulo ni negritas al inicio.
    """


    step("Solicitando redacción al modelo…")
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
        )
        texto_usos = (resp.choices[0].message.content or "").strip()
        step("Texto recibido del modelo.")
    except Exception as e:
        warn(f"Fallo LLM: {e}. Se usa texto genérico.")
        texto_usos = (
            "El terreno presenta ocupación predominantemente agrícola, con coberturas vegetales "
            "herbáceas y matorral disperso. No existen construcciones destacadas en las inmediaciones, "
            "manteniendo un uso rural tradicional."
        )

    # === 3. Generar captura CH Duero ===
    captura_path = None
    try:
        step("Generando captura en visor CH Duero…")

        # Buscar el script de captura
        cap_script = PROJECT_ROOT / "core" / "sintesis" / "captura_usos_actuales.py"
        alt_script = PROJECT_ROOT / "core" / "captura_usos_actuales.py"
        script = cap_script if cap_script.exists() else alt_script

        t0 = time.time()
        res = subprocess.run(
            [sys.executable, "-u", str(script), str(json_path)],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=300,
        )

        combined = (res.stdout or "") + "\n" + (res.stderr or "")

        # Buscar línea con UA_CAPTURE en la salida del proceso
        for line in combined.splitlines():
            if line.strip().startswith("UA_CAPTURE:"):
                captura_path = line.split("UA_CAPTURE:", 1)[1].strip()
                break

        # Fallback: buscar PNG más reciente
        if not captura_path:
            out_dir = PROJECT_ROOT / "outputs"
            recent_pngs = sorted(out_dir.glob("*.png"), key=os.path.getmtime, reverse=True)
            if recent_pngs and (recent_pngs[0].stat().st_mtime > t0 - 10):
                captura_path = str(recent_pngs[0].resolve())
                step(f"Fallback: captura detectada => {captura_path}")
            else:
                warn("No se encontró ninguna captura reciente.")

    except Exception as e:
        warn(f"Error durante la captura: {e}")

    # === 4. Guardar resultados ===
    step("Escribiendo 'usos_actuales_llm' en el JSON…")
    data["usos_actuales_llm"] = texto_usos
    if captura_path:
        data["captura_usos_actuales"] = str(Path(captura_path).resolve()).replace("\\", "/")

    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    step("JSON actualizado correctamente.")
    done(captura_path)


# === ejecución directa ===
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python usos_actuales_llm.py <json_path>", flush=True)
        sys.exit(1)
    usos_actuales_llm(Path(sys.argv[1]).resolve())
