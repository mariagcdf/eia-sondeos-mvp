# core/sintesis/captura_usos_actuales.py
import json, time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

# ==============================================================
# 🔹 CAPTURA AUTOMÁTICA DE VISOR CH DUERO SEGÚN COORDENADAS JSON
# ==============================================================
def captura_usos_actuales():
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
    utm_x = str(data.get("utm_x_principal", "")).replace(",", ".")
    utm_y = str(data.get("utm_y_principal", "")).replace(",", ".")
    if not utm_x or not utm_y:
        raise ValueError("❌ No se encontraron coordenadas UTM válidas en el JSON.")
    print(f"📍 Coordenadas UTM detectadas: X={utm_x}, Y={utm_y}")

    # === 3. Configurar navegador ===
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 60)

    try:
        # === 4. Cargar visor ===
        driver.get("https://mirame.chduero.es/chduero/viewer")
        print("🌍 Cargando visor CH Duero...")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.m-areas")))
        print("✅ Visor cargado completamente.")
        time.sleep(3)

        # === 5. Activar buscador por coordenadas ===
        btn_coord = wait.until(EC.element_to_be_clickable((By.ID, "m-locator-xylocator")))
        driver.execute_script("arguments[0].click();", btn_coord)
        wait.until(EC.presence_of_element_located((By.ID, "m-xylocator-srs")))
        print("🟢 Panel de coordenadas cargado.")

        # === 6. Seleccionar EPSG:25830 (ETRS89 / UTM zona 30N) ===
        select_srs = Select(wait.until(EC.presence_of_element_located((By.ID, "m-xylocator-srs"))))
        select_srs.select_by_value("EPSG:25830")
        time.sleep(1)

        # === 7. Introducir coordenadas y localizar ===
        input_x = wait.until(EC.presence_of_element_located((By.ID, "UTM-X")))
        input_y = wait.until(EC.presence_of_element_located((By.ID, "UTM-Y")))
        driver.execute_script("arguments[0].value = '';", input_x)
        driver.execute_script("arguments[0].value = '';", input_y)
        input_x.send_keys(utm_x)
        input_y.send_keys(utm_y)
        btn_localizar = wait.until(EC.element_to_be_clickable((By.ID, "m-xylocator-loc")))
        driver.execute_script("arguments[0].click();", btn_localizar)
        print(f"📌 Coordenadas localizadas: X={utm_x}, Y={utm_y}")
        time.sleep(5)

        # === 8. Abrir “Capas de fondo” ===
        print("🗺️ Cambiando a fondo PNOA...")
        back_layer_button = wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "button.backimglyr-simbolo-cuadros, button[aria-label='Plugin BackImgLayer']")
            )
        )
        driver.execute_script("arguments[0].click();", back_layer_button)
        time.sleep(2)

        # === 9. Seleccionar PNOA ===
        pnoa_img = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//img[contains(@alt, 'PNOA')]"))
        )
        driver.execute_script("arguments[0].click();", pnoa_img)
        print("🛰️ Fondo PNOA activado correctamente.")
        time.sleep(6)

        # === 10. Captura de pantalla ===
        capture_path = output_dir / f"{latest_json.stem}_captura_chduero.png"
        driver.save_screenshot(str(capture_path))
        print(f"📸 Captura guardada en: {capture_path}")

        # === 11. Guardar referencia en el JSON ===
        data["captura_chduero"] = str(capture_path.name)
        with open(latest_json, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("💾 Referencia de captura añadida al JSON.")

    finally:
        driver.quit()
        print("🧹 Navegador cerrado correctamente.")

    return capture_path


# ==============================================================
# 🔹 EJECUCIÓN DIRECTA
# ==============================================================
if __name__ == "__main__":
    captura_usos_actuales()