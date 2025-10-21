import sys, time, json
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from openai import OpenAI


def step(msg): print(f"CATA_STEP: {msg}", flush=True)
def warn(msg): print(f"CATA_WARN: {msg}", flush=True)
def done(msg): print(f"CATA_DONE: {msg}", flush=True)


# ==========================
# FUNCIONES DEL VISOR CH DUERO
# ==========================
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
    step("Activando capa Catastro…")
    try:
        img = driver.find_element(
            By.XPATH,
            "//img[contains(@alt, 'Catastro') or contains(@src, 'catastro')]"
        )
        driver.execute_script("arguments[0].click();", img)
        step("Capa Catastro activada correctamente.")
        time.sleep(8)
        return True
    except Exception as e:
        warn(f"No se pudo activar capa Catastro automáticamente: {e}")
        return False


def click_on_map(driver):
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


# ==========================
# NUEVO BLOQUE: EXTRACCIÓN DEL ENLACE DEL POPUP
# ==========================
def extract_catastro_link(driver):
    """Busca el enlace <a> del Catastro dentro del pop-up."""
    step("Extrayendo enlace catastral…")
    try:
        overlay = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.ol-overlay-container"))
        )
        a_tag = overlay.find_element(By.XPATH, ".//a[contains(@href,'sedecatastro') or contains(@href,'catastro')]")
        href = a_tag.get_attribute("href")
        ref_text = a_tag.text.strip()
        step(f"Referencia: {ref_text}")
        step(f"Enlace Catastro: {href}")
        return ref_text, href
    except Exception as e:
        warn(f"No se pudo extraer el enlace del Catastro: {e}")
        return None, None


# ==========================
# NUEVO BLOQUE: CAPTURA Y PROCESO CON LLM
# ==========================
def extract_from_popup_with_llm(driver, href):
    """Abre la ficha del Catastro, extrae el body y obtiene solo los datos técnicos."""
    step("Abriendo ficha del Catastro…")
    driver.execute_script("window.open(arguments[0]);", href)
    time.sleep(2)

    popup = [w for w in driver.window_handles if w != driver.current_window_handle][0]
    driver.switch_to.window(popup)

    # Esperar carga completa
    for _ in range(30):
        if driver.execute_script("return document.readyState") == "complete":
            break
        time.sleep(0.5)

    body_html = driver.find_element(By.TAG_NAME, "body").get_attribute("outerHTML")
    step("Contenido HTML capturado. Enviando al modelo…")

    client = OpenAI()

    prompt = f"""
    A partir del siguiente HTML del Catastro, extrae SOLO la información técnica relevante
    en formato JSON con los siguientes campos:
    - clase
    - uso_principal
    - superficie_grafica (en m2)
    - cultivos: lista de objetos con subparcela, cultivo, intensidad, superficie_m2

    HTML:
    {body_html[:12000]}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        structured = response.choices[0].message.content.strip()
        step("Respuesta del modelo recibida.")
        return structured
    except Exception as e:
        warn(f"No se pudo procesar con el modelo: {e}")
        return None


# ==========================
# MAIN
# ==========================
def main():
    if len(sys.argv) < 2:
        print("Uso: python catastro_client.py <json_path>", flush=True)
        sys.exit(1)

    json_path = Path(sys.argv[1]).resolve()
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

        # 1️⃣ Localizar y activar capa
        open_coords_panel(driver)
        locate_coords(driver, utm_x, utm_y)
        open_backimg_panel(driver)
        enable_catastro_layer(driver)

        # 2️⃣ Clic en mapa y extraer enlace
        click_on_map(driver)
        ref, href = extract_catastro_link(driver)

        if href:
            data["catastro_ref"] = ref
            data["catastro_url"] = href

            # 3️⃣ Extraer datos del popup del Catastro con LLM
            structured = extract_from_popup_with_llm(driver, href)
            if structured:
                data["catastro_structured"] = structured

            json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            done("Información catastral extraída y guardada correctamente.")
        else:
            warn("No se encontró enlace al Catastro en el visor.")

    except Exception as e:
        warn(f"Error inesperado: {e}")
        driver.save_screenshot("debug_catastro_error.png")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
