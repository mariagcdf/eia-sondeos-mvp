import json, time, re, sys
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import ActionChains


def step(msg): 
    print(f"RN_STEP: {msg}", flush=True)

def warn(msg): 
    print(f"RN_WARN: {msg}", flush=True)

def result_inside(code, name): 
    print(f"RESULT: EN_RED_NATURA|{code}|{name}", flush=True)

def result_outside(): 
    print("RESULT: NO_APLICA", flush=True)


# === Funciones auxiliares ===
def find_map_canvas(driver, wait):
    """Busca el canvas o contenedor principal del mapa."""
    selectors = [
        "#map > div > div.ol-unselectable.ol-layers > div:nth-child(2) > canvas",
        "div.ol-viewport canvas",
        "div.ol-viewport"
    ]
    for sel in selectors:
        try:
            el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, sel)))
            if el.is_displayed():
                return el
        except Exception:
            pass
    return None


def click_canvas_js(driver, canvas, x, y):
    """Realiza un click JS en las coordenadas absolutas indicadas."""
    return driver.execute_script("""
        const el = document.elementFromPoint(arguments[1], arguments[2]);
        if (el) {
            el.dispatchEvent(new MouseEvent('click', {
                bubbles: true, cancelable: true, clientX: arguments[1],
                clientY: arguments[2], view: window
            }));
            return el.className || el.tagName;
        }
        return null;
    """, canvas, x, y)


def accept_cookies(driver):
    """Acepta cookies si aparece el banner."""
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


# === Programa principal ===
def main():
    if len(sys.argv) < 2:
        raise SystemExit("Uso: python export_info_red_natura.py <json_path>")

    json_path = Path(sys.argv[1]).resolve()
    if not json_path.exists():
        raise FileNotFoundError(f"No existe: {json_path}")

    data = json.loads(json_path.read_text(encoding="utf-8"))
    utm_x = str(data["utm_x_principal"]).replace(".", ",")
    utm_y = str(data["utm_y_principal"]).replace(".", ",")
    step(f"Coordenadas UTM => X={utm_x}, Y={utm_y}")

    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    #chrome_options.add_argument("--headless=new")  # Desactivar si quieres ver la ejecución

    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 60)

    try:
        # === 1. Abrir visor ===
        step("Abriendo visor CH Duero…")
        driver.get("https://mirame.chduero.es/chduero/viewer")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.m-areas")))
        time.sleep(2)
        accept_cookies(driver)
        step("Visor cargado correctamente.")

        # === 2. Abrir panel coordenadas ===
        step("Abriendo panel de coordenadas…")
        btn_coord = wait.until(EC.element_to_be_clickable((By.ID, "m-locator-xylocator")))
        driver.execute_script("arguments[0].click();", btn_coord)
        wait.until(EC.presence_of_element_located((By.ID, "m-xylocator-srs")))
        step("Panel de coordenadas abierto.")

        # === 3. Localizar coordenadas ===
        select_srs = Select(driver.find_element(By.ID, "m-xylocator-srs"))
        select_srs.select_by_value("EPSG:25830")
        x_in = driver.find_element(By.ID, "UTM-X")
        y_in = driver.find_element(By.ID, "UTM-Y")
        driver.execute_script("arguments[0].value='';", x_in)
        driver.execute_script("arguments[0].value='';", y_in)
        x_in.send_keys(utm_x)
        y_in.send_keys(utm_y)
        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "m-xylocator-loc"))
        time.sleep(3)
        step("Coordenadas localizadas en el visor.")

        # === 4. Abrir catálogo y activar capa ===
        step("Abriendo catálogo de capas…")
        btn_capas = wait.until(EC.element_to_be_clickable((
            By.XPATH, "//button[contains(., 'Catálogo de capas') or .//i[contains(@class,'fa-layer-group')]]"
        )))
        driver.execute_script("arguments[0].click();", btn_capas)
        time.sleep(2)

        step("Buscando capa 'Red Natura 2000' o 'Espacios protegidos (@MITERD)'…")
        capa_xpath = (
            "//span[contains(., 'Red Natura 2000') or contains(., 'Espacios protegidos')]"
            "/ancestor::mat-checkbox//span[contains(@class,'mat-checkbox-inner-container')]"
        )
        success = False
        for attempt in range(3):
            try:
                inner = wait.until(EC.presence_of_element_located((By.XPATH, capa_xpath)))
                checkbox_input = inner.find_element(By.XPATH, ".//preceding-sibling::input")
                checked = checkbox_input.get_attribute("aria-checked")
                if checked == "true":
                    step("La capa ya estaba activada.")
                    success = True
                    break

                step(f"Activando capa (intento {attempt+1})…")
                ActionChains(driver).move_to_element(inner).pause(0.3).click(inner).perform()
                time.sleep(2)

                inner = wait.until(EC.presence_of_element_located((By.XPATH, capa_xpath)))
                checkbox_input = inner.find_element(By.XPATH, ".//preceding-sibling::input")
                checked = checkbox_input.get_attribute("aria-checked")

                if checked == "true":
                    step("✅ Capa activada correctamente.")
                    success = True
                    break
                else:
                    warn(f"Intento {attempt+1}: el checkbox aún no está activo.")

            except Exception as e:
                warn(f"Error al intentar activar la capa (intento {attempt+1}): {e}")

        if not success:
            warn("⚠️ No se logró activar la capa tras varios intentos.")

        # === 5. Refrescar y cerrar catálogo ===
        try:
            step("Refrescando capas…")
            btn_refresh = wait.until(EC.element_to_be_clickable((
                By.XPATH, "//span[contains(., 'Refrescar capas')]/parent::button"
            )))
            driver.execute_script("arguments[0].click();", btn_refresh)
            time.sleep(2)
        except Exception as e:
            warn(f"No se pudo refrescar capas: {e}")

        try:
            step("Cerrando catálogo…")
            btn_close = wait.until(EC.element_to_be_clickable((
                By.XPATH, "//span[contains(., 'Cerrar')]/parent::button"
            )))
            driver.execute_script("arguments[0].click();", btn_close)
            time.sleep(1)
            step("Catálogo cerrado.")
        except Exception as e:
            warn(f"No se pudo cerrar catálogo: {e}")

        # === 6. Activar herramienta de información ===
        try:
            step("Activando herramienta de información…")
            info_btn = wait.until(EC.element_to_be_clickable((
                By.CSS_SELECTOR, "button[title='Información'], button[aria-label='Información']"
            )))
            driver.execute_script("arguments[0].click();", info_btn)
            time.sleep(1)
        except Exception as e:
            warn(f"No se pudo activar 'Información': {e}")

               # === 7. Hacer clic en el centro del mapa ===
        try:
            step("Esperando a que el mapa esté listo…")
            time.sleep(3)

            # Localizar el viewport principal del mapa
            step("Buscando el viewport del mapa (OpenLayers)…")
            viewport = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.ol-viewport"))
            )

            # Obtener dimensiones del mapa
            rect = driver.execute_script("""
                const el = arguments[0];
                const r = el.getBoundingClientRect();
                return {x:r.x, y:r.y, width:r.width, height:r.height};
            """, viewport)
            cx = int(rect["width"] / 2)
            cy = int(rect["height"] / 2)
            step(f"Viewport encontrado: ancho={rect['width']}, alto={rect['height']} → centro=({cx},{cy})")

            # Dibujar punto visual de depuración
            driver.execute_script("""
                const mark = document.createElement('div');
                mark.style.position = 'fixed';
                mark.style.left = (arguments[1] + arguments[3]) + 'px';
                mark.style.top = (arguments[2] + arguments[4]) + 'px';
                mark.style.width = '16px';
                mark.style.height = '16px';
                mark.style.background = 'red';
                mark.style.borderRadius = '50%';
                mark.style.zIndex = 999999;
                mark.style.opacity = 0.8;
                document.body.appendChild(mark);
                setTimeout(()=>mark.remove(), 3000);
            """, viewport, rect["x"], rect["y"], cx - 8, cy - 8)

            # Hacer clic en el centro exacto del mapa
            step("Haciendo clic en el centro del mapa…")
            actions = ActionChains(driver)
            actions.move_to_element_with_offset(viewport, cx, cy)
            actions.click()
            actions.perform()
            step("✅ Clic realizado correctamente en el centro del mapa.")
            time.sleep(4)

            # Analizar el HTML tras el clic
            html = driver.page_source
            match = re.search(r"(ES\d{6,}).*?Nombre\s*</[^>]+>\s*<[^>]*>(.*?)</", html, re.DOTALL)
            if match:
                code = match.group(1).strip()
                name = match.group(2).strip()
                data["codigos_red_natura"] = [code]
                data["nombres_red_natura"] = [name]
                data["estado_red_natura"] = "en_red_natura"
                data["red_natura"] = True
                result_inside(code, name)
                step(f"🟢 Red Natura detectada: {code} - {name}")
            else:
                step("⚠ No se encontró código ES tras el clic, puede que no esté en zona protegida.")
                result_outside()
                data["estado_red_natura"] = "no_aplica"
                data["red_natura"] = False

        except Exception as e:
            warn(f"Error al hacer clic en el mapa: {e}")

    finally:
        json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        step("JSON actualizado con información de Red Natura.")
        driver.quit()


if __name__ == "__main__":
    main()
