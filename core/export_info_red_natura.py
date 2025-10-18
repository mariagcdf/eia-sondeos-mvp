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


def main():
    if len(sys.argv) < 2:
        raise SystemExit("Uso: python export_info_red_natura_manual.py <json_path>")

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

        # === 2. Panel de coordenadas ===
        step("Abriendo panel de coordenadas…")
        btn_coord = wait.until(EC.element_to_be_clickable((By.ID, "m-locator-xylocator")))
        driver.execute_script("arguments[0].click();", btn_coord)
        wait.until(EC.presence_of_element_located((By.ID, "m-xylocator-srs")))
        step("Panel de coordenadas abierto.")

        select_srs = Select(driver.find_element(By.ID, "m-xylocator-srs"))
        select_srs.select_by_value("EPSG:25830")
        driver.find_element(By.ID, "UTM-X").clear()
        driver.find_element(By.ID, "UTM-Y").clear()
        driver.find_element(By.ID, "UTM-X").send_keys(utm_x)
        driver.find_element(By.ID, "UTM-Y").send_keys(utm_y)
        driver.find_element(By.ID, "m-xylocator-loc").click()
        step("Coordenadas localizadas en el visor.")
        time.sleep(4)

        # === 3. Activar capa Red Natura ===
        step("Abriendo catálogo de capas…")
        btn_capas = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Catálogo de capas') or .//i[contains(@class,'fa-layer-group')]]")))
        driver.execute_script("arguments[0].click();", btn_capas)
        time.sleep(2)

        capa_xpath = ("//span[contains(., 'Red Natura 2000') or contains(., 'Espacios protegidos')]/ancestor::mat-checkbox//span[contains(@class,'mat-checkbox-inner-container')]")
        inner = wait.until(EC.presence_of_element_located((By.XPATH, capa_xpath)))
        ActionChains(driver).move_to_element(inner).pause(0.3).click(inner).perform()
        step("Capa 'Red Natura 2000 / Espacios protegidos' activada.")
        time.sleep(2)

        # === 4. Refrescar capas ===
        try:
            step("Refrescando capas…")
            btn_refresh = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(., 'Refrescar capas')]/parent::button")))
            driver.execute_script("arguments[0].click();", btn_refresh)
            time.sleep(3)
            wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, ".m-loading")))
            step("Capas refrescadas correctamente.")
        except Exception as e:
            warn(f"No se pudo refrescar capas: {e}")

        # === 5. Cerrar catálogo ===
        try:
            btn_close = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(., 'Cerrar')]/parent::button")))
            driver.execute_script("arguments[0].click();", btn_close)
            step("Catálogo cerrado.")
        except Exception:
            warn("No se pudo cerrar el catálogo con el botón, cerrando overlays por script.")
            driver.execute_script("""
                document.querySelectorAll('mat-dialog-container, .cdk-overlay-backdrop')
                .forEach(el => el.remove());
            """)
        time.sleep(1)

        # === 6. Desbloquear mapa ===
        driver.execute_script("""
            document.querySelectorAll('mat-dialog-container, .cdk-overlay-backdrop')
            .forEach(p => p.style.display='none');
        """)
        step("Cierres forzados de overlays y catálogos para habilitar clic automático.")
        time.sleep(1)

        # === Nuevo paso: forzar movimiento y zoom para activar clics ===
        step("Reactivando mapa (movimiento y zoom-out)...")
        driver.execute_script("""
            try {
                const map = document.querySelector('div.ol-viewport');
                const wheelEvent = new WheelEvent('wheel', {deltaY: 100, bubbles: true});
                map.dispatchEvent(wheelEvent);
                map.dispatchEvent(new WheelEvent('wheel', {deltaY: -100, bubbles: true}));
                map.dispatchEvent(new MouseEvent('mousedown', {clientX: 300, clientY: 300, bubbles: true}));
                map.dispatchEvent(new MouseEvent('mouseup', {clientX: 310, clientY: 310, bubbles: true}));
            } catch(e) {
                console.log('Error reactivando mapa', e);
            }
        """)
        time.sleep(10)


        # === 7. Autoclick en el punto ===
        step("Simulando clic automático en las coordenadas localizadas…")
        driver.execute_script("""
            const map = document.querySelector('div.ol-viewport');
            if (map) {
                const rect = map.getBoundingClientRect();
                const clickX = rect.width / 2;
                const clickY = rect.height / 2;
                map.dispatchEvent(new MouseEvent('click', {
                    bubbles: true, cancelable: true, clientX: clickX, clientY: clickY
                }));
            }
        """)
        time.sleep(7)

        # === 8. Buscar popup con código ES ===
        popup = None
        selectors = [
            "div.m-popup",
            "div.ol-overlaycontainer-stopevent div.m-popup",
            "div.ol-overlaycontainer-stopevent"
        ]
        found_html = ""
        for _ in range(40):
            for sel in selectors:
                try:
                    popup = driver.find_element(By.CSS_SELECTOR, sel)
                    if popup.is_displayed():
                        html = popup.get_attribute("innerHTML")
                        if "Area:" in html or "Distance:" in html or "display: none" in html:
                            continue
                        found_html = html
                        step(f"Popup detectado con selector: {sel}")
                        break
                except Exception:
                    continue
            if found_html:
                break
            time.sleep(1)

        if found_html:
            # Buscar solo los ES dentro del bloque de Red Natura 2000
            import re

            # 1️⃣ Localizar el bloque correcto del HTML
            rn_block = re.search(r"Red Natura 2000(.+?)Informaci[oó]n de", found_html, re.DOTALL)
            if rn_block:
                rn_html = rn_block.group(1)
            else:
                rn_html = found_html  # fallback si no se encuentra

            # 2️⃣ Extraer códigos válidos (solo del bloque RN2000)
            matches = re.findall(r"\bES\d{4,7}\b", rn_html)

            if matches:
                code = matches[0]
                step(f"Red Natura detectada: {code}")
                data["codigos_red_natura"] = [code]
                data["estado_red_natura"] = "en_red_natura"
                data["red_natura"] = True
                result_inside(code, "AutoClick")
            else:
                step("Popup encontrado pero sin código ES visible.")
                snippet = found_html[:300].replace("\n", " ")
                warn(f"Fragmento HTML popup: {snippet}")
                data["estado_red_natura"] = "no_aplica"
                data["red_natura"] = False
                result_outside()
        else:
            warn("No se detectó ningún popup tras el clic automático.")
            driver.save_screenshot("debug_no_popup.png")
            html_snippet = driver.page_source[:1000].replace("\n", " ")
            warn(f"Guardada captura debug_no_popup.png. Primeros 1000 caracteres del HTML: {html_snippet}")
            data["estado_red_natura"] = "no_aplica"
            data["red_natura"] = False
            result_outside()

    except Exception as e:
        warn(f"Error inesperado: {e}")

    finally:
        json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        step("JSON actualizado con información de Red Natura.")
        driver.quit()


if __name__ == "__main__":
    main()
