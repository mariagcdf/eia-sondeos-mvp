import json
import time
import re
import subprocess
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import ActionChains

# === 1. Buscar el último JSON ===
output_dir = Path("outputs")
json_files = sorted(output_dir.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
if not json_files:
    raise FileNotFoundError("❌ No se encontró ningún archivo JSON en outputs.")
latest_json = json_files[0]
print(f"📂 Usando JSON más reciente: {latest_json.name}")

# === 2. Leer coordenadas ===
with open(latest_json, "r", encoding="utf-8") as f:
    data = json.load(f)
utm_x = str(data["utm_x_principal"]).replace(".", ",")
utm_y = str(data["utm_y_principal"]).replace(".", ",")
print(f"📍 Coordenadas UTM detectadas: X={utm_x}, Y={utm_y}")

# === 3. Configurar navegador ===

# 👉 Si quieres ver el proceso en pantalla, déjalo SIN headless (como ahora).
#    Si prefieres que el script se ejecute en segundo plano (sin abrir Chrome),
#    descomenta la configuración de "headless" aquí abajo.

# --- MODO HEADLESS (sin ventana gráfica) ---
# chrome_options = Options()
# chrome_options.add_argument("--headless=new")        # Ejecuta sin mostrar ventana
# chrome_options.add_argument("--disable-gpu")         # Evita errores de renderizado
# chrome_options.add_argument("--window-size=1920,1080") # Tamaño de la ventana virtual
# chrome_options.add_argument("--no-sandbox")          # Necesario en algunos entornos Linux
# chrome_options.add_argument("--disable-dev-shm-usage") # Mejora estabilidad en Docker/WSL
# chrome_options.add_argument("--disable-extensions")  # Desactiva extensiones
# chrome_options.add_argument("--log-level=3")         # Reduce mensajes del navegador

# --- MODO NORMAL (ventana visible) ---
chrome_options = Options()                             # Se crea objeto de configuración
chrome_options.add_argument("--start-maximized")       # Abre Chrome en pantalla completa

driver = webdriver.Chrome(options=chrome_options)
wait = WebDriverWait(driver, 60)


# === 4. Cargar visor ===
driver.get("https://mirame.chduero.es/chduero/viewer")
print("🌍 Cargando visor CH Duero...")
wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.m-areas")))
print("✅ Visor cargado completamente.")

# === 5. Activar buscador por coordenadas ===
btn_coord = wait.until(EC.element_to_be_clickable((By.ID, "m-locator-xylocator")))
driver.execute_script("arguments[0].click();", btn_coord)
wait.until(EC.presence_of_element_located((By.ID, "m-xylocator-srs")))
print("🟢 Panel de coordenadas cargado.")

# === 6. Activar capa Red Natura 2000 ===
btn_capas = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Catálogo de capas')]")))
driver.execute_script("arguments[0].click();", btn_capas)
time.sleep(8)
try:
    checkbox_natura = wait.until(EC.element_to_be_clickable((By.ID, "mat-checkbox-8-input")))
    if checkbox_natura.get_attribute("aria-checked") != "true":
        driver.execute_script("arguments[0].click();", checkbox_natura)
        print("🟩 Capa 'Red Natura 2000' activada.")
except:
    print("⚠️ No se pudo activar capa 'Red Natura 2000'.")

# Refrescar y cerrar catálogo
try:
    btn_refrescar = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//span[contains(text(),'Refrescar capas')]/parent::button"))
    )
    driver.execute_script("arguments[0].click();", btn_refrescar)
    time.sleep(12)
except:
    pass
try:
    close_button = driver.find_element(By.XPATH, "//button[@title='Cerrar catálogo de capas']")
    driver.execute_script("arguments[0].click();", close_button)
except:
    pass
# === 7. Insertar coordenadas y localizar ===
print("📍 Insertando coordenadas UTM y localizando en el mapa...")

# Seleccionar sistema EPSG:25830 (ETRS89 / UTM zona 30N)
select_srs = Select(wait.until(EC.presence_of_element_located((By.ID, "m-xylocator-srs"))))
select_srs.select_by_value("EPSG:25830")
time.sleep(1)

# Buscar los campos correctos de coordenadas (UTM-X y UTM-Y)
input_x = wait.until(EC.presence_of_element_located((By.ID, "UTM-X")))
input_y = wait.until(EC.presence_of_element_located((By.ID, "UTM-Y")))

# Limpiar y escribir las coordenadas
driver.execute_script("arguments[0].value = '';", input_x)
driver.execute_script("arguments[0].value = '';", input_y)
input_x.send_keys(utm_x)
input_y.send_keys(utm_y)

# Pulsar el botón de localizar
btn_localizar = wait.until(EC.element_to_be_clickable((By.ID, "m-xylocator-loc")))
driver.execute_script("arguments[0].click();", btn_localizar)

print(f"📌 Coordenadas localizadas en mapa: X={utm_x}, Y={utm_y}")
time.sleep(3)
# === 7.5 Activar herramienta de información ===
print("ℹ️ Activando herramienta de información en el visor...")
try:
    info_button = wait.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "button[title='Información'], button[aria-label='Información']"))
    )
    driver.execute_script("arguments[0].click();", info_button)
    print("✅ Herramienta de información activada correctamente.")
    time.sleep(2)
except Exception as e:
    print(f"⚠️ No se pudo activar la herramienta de información: {e}")

# === 8. Ejecutar clic real sobre el punto localizado ===
print("🖱️ Simulando clic en el punto localizado para abrir popup...")

try:
    # Ejecutar JavaScript directamente dentro del visor
    driver.execute_script("""
        try {
            const map = window.map;  // acceso al mapa OpenLayers
            if (map && map.getView) {
                const center = map.getView().getCenter();
                if (center) {
                    map.forEachFeatureAtPixel(map.getPixelFromCoordinate(center), function(feature, layer) {
                        map.dispatchEvent({
                            type: 'singleclick',
                            coordinate: center,
                            pixel: map.getPixelFromCoordinate(center)
                        });
                    });
                    console.log('✅ Click forzado sobre el punto localizado');
                } else {
                    console.log('⚠️ No se encontró el centro del mapa.');
                }
            } else {
                console.log('⚠️ Objeto map no disponible.');
            }
        } catch (err) {
            console.error('❌ Error al simular clic:', err);
        }
    """)
    print("✅ Clic JavaScript interno ejecutado sobre el punto localizado.")
except Exception as e:
    print(f"⚠️ Fallo en la ejecución del clic simulado: {e}")

time.sleep(5)



# === 9. Detectar Red Natura 2000 (versión robusta) ===
print("📖 Buscando información de Red Natura 2000...")

html_doc = None
try:
    # Esperar hasta que aparezca algo que contenga "Red Natura 2000" en todo el documento
    WebDriverWait(driver, 60).until(
        lambda d: "Red Natura 2000" in d.page_source
    )
    print("🟢 Texto 'Red Natura 2000' detectado en el HTML general.")

    # Espera adicional para que termine de cargar todo el bloque
    time.sleep(2)

    # Obtener el HTML completo del documento (no solo el popup)
    html_doc = driver.page_source

    # Guardar HTML para depuración
    Path("debug_html").mkdir(exist_ok=True)
    debug_file = Path("debug_html") / f"page_full_{int(time.time())}.html"
    with open(debug_file, "w", encoding="utf-8") as f:
        f.write(html_doc)
    print(f"🧩 HTML completo guardado: {debug_file}")

    # Buscar información de Red Natura 2000
    bloque_natura = re.search(
        r"Red Natura 2000.*?(ES\d{6,}).*?Nombre\s*</[^>]+>\s*<[^>]*>(.*?)</",
        html_doc,
        re.DOTALL,
    )

    if bloque_natura:
        codigo = bloque_natura.group(1).strip()
        nombre = bloque_natura.group(2).strip()
        print(f"🟢 Proyecto dentro de Red Natura 2000: {codigo} ({nombre})")
        data["codigos_red_natura"] = [codigo]
        data["nombres_red_natura"] = [nombre]
        data["estado_red_natura"] = "en_red_natura"
    else:
        print("⚪ No se detectaron códigos válidos de Red Natura.")
        data["estado_red_natura"] = "no_aplica"

except Exception as e:
    print(f"⚠️ Error procesando popup: {e}")
    if html_doc:
        Path("debug_html").mkdir(exist_ok=True)
        debug_file = Path("debug_html") / f"page_error_{int(time.time())}.html"
        with open(debug_file, "w", encoding="utf-8") as f:
            f.write(html_doc)
        print(f"🧩 HTML parcial guardado para depuración: {debug_file}")
    data["estado_red_natura"] = "no_aplica"


# === 10. Guardar JSON ===
with open(latest_json, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print("💾 Información Red Natura actualizada en el JSON.")

# === 11. Si no pertenece a Red Natura ===
if data.get("estado_red_natura") == "no_aplica":
    alt_script = Path("core/sintesis/medio_biotico_no_red_natura.py").resolve()
    if alt_script.exists():
        print("🪶 Ejecutando análisis ambiental complementario...")
        subprocess.run(["python", str(alt_script), str(latest_json)], check=True)
        print("🪶 Texto alternativo de medio biótico generado correctamente.")
    else:
        print("⚠️ Script medio_biotico_no_red_natura.py no encontrado.")

driver.quit()
print("✅ Proceso completado correctamente.")
