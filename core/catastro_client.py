import sys, time, json
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC


def step(msg): print(f"CATA_STEP: {msg}", flush=True)
def warn(msg): print(f"CATA_WARN: {msg}", flush=True)
def done(msg): print(f"CATA_DONE: {msg}", flush=True)


def accept_cookies(driver):
    step("Buscando banner de cookies…")
    try:
        btn = WebDriverWait(driver, 8).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "a.cc-btn.cc-allow"))
        )
        driver.execute_script("arguments[0].click();", btn)
        step("Cookies aceptadas.")
        time.sleep(1)
    except Exception:
        warn("No se encontró banner de cookies, continuando…")


def open_coords_panel(driver):
    step("Abriendo panel de coordenadas…")
    btn_coord = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.ID, "m-locator-xylocator"))
    )
    driver.execute_script("arguments[0].click();", btn_coord)
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "m-xylocator-srs"))
    )
    step("Panel de coordenadas abierto correctamente.")


def locate_coords(driver, utm_x, utm_y):
    step("Localizando coordenadas…")
    Select(driver.find_element(By.ID, "m-xylocator-srs")).select_by_value("EPSG:25830")
    x_field = driver.find_element(By.ID, "UTM-X")
    y_field = driver.find_element(By.ID, "UTM-Y")
    x_field.clear(); y_field.clear()
    x_field.send_keys(utm_x)
    y_field.send_keys(utm_y)
    driver.find_element(By.ID, "m-xylocator-loc").click()
    step(f"Coordenadas localizadas: X={utm_x}, Y={utm_y}")
    time.sleep(3)


def open_backimg_panel(driver):
    step("Abriendo panel de mapas base…")
    btn = WebDriverWait(driver, 15).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "button.backimglyr-simbolo-cuadros"))
    )
    driver.execute_script("arguments[0].click();", btn)
    time.sleep(2)
    step("Panel de mapas base abierto.")


def enable_catastro_layer(driver):
    """Activa la capa del Catastro automáticamente."""
    step("Activando capa Catastro…")
    try:
        # Buscar imagen con alt o id del Catastro
        img = driver.find_element(
            By.XPATH,
            "//img[contains(@alt, 'Catastro') or contains(@src, 'catastro')]"
        )
        driver.execute_script("arguments[0].click();", img)
        step("Capa Catastro activada correctamente.")
        time.sleep(4)
        return True
    except Exception as e:
        warn(f"No se pudo activar capa Catastro automáticamente: {e}")
        return False


def click_on_map(driver):
    """Hace clic en el centro del mapa para abrir el pop-up catastral."""
    step("Haciendo clic en el mapa para abrir información catastral…")
    try:
        map_el = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.ol-viewport"))
        )
        driver.execute_script("""
            const rect = arguments[0].getBoundingClientRect();
            const x = rect.left + rect.width / 2;
            const y = rect.top + rect.height / 2;
            const el = document.elementFromPoint(x, y);
            el.dispatchEvent(new MouseEvent('click', {bubbles: true}));
        """, map_el)
        step("Clic en el mapa ejecutado.")
        time.sleep(3)
    except Exception as e:
        warn(f"No se pudo hacer clic en el mapa: {e}")


def extract_catastro_info(driver):
    """Extrae el texto visible del pop-up."""
    step("Extrayendo información visible del visor…")
    try:
        overlay = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.ol-overlay-container"))
        )
        text_blocks = overlay.find_elements(By.XPATH, ".//div")
        texts = [t.text.strip() for t in text_blocks if t.text.strip()]
        if texts:
            step("Información catastral detectada:")
            for line in texts:
                print(f"📋 {line}")
            return "\n".join(texts)
        else:
            warn("No se encontró texto en el pop-up.")
            return ""
    except Exception:
        warn("No se pudo leer el pop-up.")
        return ""


def main():
    if len(sys.argv) < 2:
        print("Uso: python catastro_client.py <json_path>", flush=True)
        sys.exit(1)

    json_path = Path(sys.argv[1]).resolve()
    if not json_path.exists():
        print(f"❌ No existe JSON: {json_path}", flush=True)
        sys.exit(1)

    data = json.loads(json_path.read_text(encoding="utf-8"))
    utm_x = str(data.get("utm_x_principal", "")).replace(",", ".")
    utm_y = str(data.get("utm_y_principal", "")).replace(",", ".")

    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 40)

    try:
        step("Abriendo visor CH Duero…")
        driver.get("https://mirame.chduero.es/chduero/viewer")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.m-areas")))
        time.sleep(2)
        accept_cookies(driver)

        # Localizar y activar capa
        open_coords_panel(driver)
        locate_coords(driver, utm_x, utm_y)
        open_backimg_panel(driver)
        enable_catastro_layer(driver)

        # Clic para mostrar popup
        click_on_map(driver)
        info = extract_catastro_info(driver)

        if info:
            data["catastro_info"] = info
            json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            done("Información catastral guardada correctamente.")
        else:
            warn("No se obtuvo información textual.")

    except Exception as e:
        warn(f"Error inesperado: {e}")
        driver.save_screenshot("debug_catastro_error.png")

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
