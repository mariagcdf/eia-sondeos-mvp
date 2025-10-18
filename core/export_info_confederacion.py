import json, time, re, sys
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import ActionChains
from selenium.common.exceptions import NoSuchElementException
from streamlit import info



def step(msg):
    print(f"RN_STEP: {msg}", flush=True)

def warn(msg):
    print(f"RN_WARN: {msg}", flush=True)

def done(msg):
    print(f"RN_DONE: {msg}", flush=True)


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
        raise SystemExit("Uso: python export_info_confederacion_manual.py <json_path>")

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
        # === 1️⃣ Abrir visor ===
        step("Abriendo visor CH Duero…")
        driver.get("https://mirame.chduero.es/chduero/viewer")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.m-areas")))
        time.sleep(2)
        accept_cookies(driver)
        step("Visor cargado correctamente.")

        # === 2️⃣ Localizar coordenadas ===
        step("Abriendo panel de coordenadas…")
        btn_coord = wait.until(EC.element_to_be_clickable((By.ID, "m-locator-xylocator")))
        driver.execute_script("arguments[0].click();", btn_coord)
        wait.until(EC.presence_of_element_located((By.ID, "m-xylocator-srs")))

        select_srs = Select(driver.find_element(By.ID, "m-xylocator-srs"))
        select_srs.select_by_value("EPSG:25830")
        driver.find_element(By.ID, "UTM-X").clear()
        driver.find_element(By.ID, "UTM-Y").clear()
        driver.find_element(By.ID, "UTM-X").send_keys(utm_x)
        driver.find_element(By.ID, "UTM-Y").send_keys(utm_y)
        driver.find_element(By.ID, "m-xylocator-loc").click()
        step("Coordenadas localizadas en el visor.")
        time.sleep(4)

        # === 3️⃣ Abrir catálogo de capas ===
        step("Abriendo catálogo de capas…")
        btn_capas = wait.until(EC.element_to_be_clickable((
            By.XPATH,
            "//button[contains(., 'Catálogo de capas') or .//i[contains(@class,'fa-layer-group')]]"
        )))
        driver.execute_script("arguments[0].click();", btn_capas)
        time.sleep(2)

        # === 4️⃣ Activar capa de Confederación ===
        capa_xpath = ("//span[contains(., 'Información Plan Hidrológico 2022-2027')]/ancestor::mat-checkbox"
                      "//span[contains(@class,'mat-checkbox-inner-container')]")
        inner = wait.until(EC.presence_of_element_located((By.XPATH, capa_xpath)))
        ActionChains(driver).move_to_element(inner).pause(0.3).click(inner).perform()
        step("Capa 'Información Plan Hidrológico 2022-2027' activada.")
        time.sleep(2)

        # === 5️⃣ Refrescar y cerrar ===
        try:
            step("Refrescando capas…")
            btn_refresh = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//span[contains(., 'Refrescar capas')]/parent::button")))
            driver.execute_script("arguments[0].click();", btn_refresh)
            time.sleep(3)
            wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, ".m-loading")))
        except Exception:
            warn("No se pudo refrescar capas correctamente.")
        try:
            btn_close = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//span[contains(., 'Cerrar')]/parent::button")))
            driver.execute_script("arguments[0].click();", btn_close)
        except Exception:
            driver.execute_script("""
                document.querySelectorAll('mat-dialog-container, .cdk-overlay-backdrop')
                .forEach(el => el.remove());
            """)
        time.sleep(7)

        # === 7️⃣ Esperar apertura o detección de ficha técnica ===
        step("Esperando clic manual en el mapa y apertura de ficha técnica…")
        step("Haz clic en el punto y luego en el enlace 'masInfo'. No cierres el navegador.")
        step("Comprobando si ya estás en la ficha técnica (por ejemplo, si la URL contiene 'groundWaterBody')…")

        initial_tabs = driver.window_handles
        new_tab = None
        for _ in range(60):
            handles = driver.window_handles
            if len(handles) > len(initial_tabs):
                new_tab = [h for h in handles if h not in initial_tabs][0]
                driver.switch_to.window(new_tab)
                step("Nueva pestaña detectada y activada.")
                break
            time.sleep(2)
        else:
            warn("No se detectó nueva pestaña abierta tras el clic manual.")
            return

        # === 8️⃣ Confirmar que estamos en la ficha técnica ===
        for _ in range(30):
            url = driver.current_url
            if "groundWaterBody/gwb/search/technical" in url:
                step(f"Página de FICHA TÉCNICA detectada: {url}")
                break
            elif "groundWaterBody/gwb/search/general" in url:
                step("Página general detectada, esperando que entres en 'Ficha técnica'…")
            time.sleep(2)
        else:
            warn("No se detectó la ficha técnica tras 60 segundos.")
            return

        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "mat-list-item i.fa-gear")))
        time.sleep(2)

        # ---- 💧 RECURSO ----
        step("Extrayendo información de pestaña 'Recurso'…")
        try:
            recurso_tab = driver.find_element(By.XPATH, "//div[contains(., 'Recurso') and @role='tab']")
            driver.execute_script("arguments[0].click();", recurso_tab)
            time.sleep(2)
            recurso_val = driver.find_element(By.CSS_SELECTOR, "span.float-end.text-wrap.ng-star-inserted").text.strip()
        except Exception:
            recurso_val = ""
            warn("No se encontró valor de recurso.")

        # ---- 🌍 HIDROGEO ----
        step("Extrayendo información de pestaña 'Hidrogeo'…")
        hidro_desc = []
        try:
            hidrogeo_tab = driver.find_element(By.XPATH, "//label[contains(., 'Hidrogeo')]")
            driver.execute_script("arguments[0].click();", hidrogeo_tab)
            time.sleep(2)
            hidro_texts = driver.find_elements(By.CSS_SELECTOR, "span.float-end.text-wrap")
            hidro_desc = [t.text.strip() for t in hidro_texts if t.text.strip()]
        except Exception:
            warn("No se encontró información de hidrogeo.")

        # ---- ⚙️ EXPLOTACIÓN ----
        step("Extrayendo información de pestaña 'Explotación'…")
        valores = []
        try:
            explotacion_tab = driver.find_element(By.XPATH, "//label[contains(., 'Explotación')]")
            driver.execute_script("arguments[0].click();", explotacion_tab)
            time.sleep(2)
            valores_expl = driver.find_elements(By.CSS_SELECTOR, "span.float-end.text-wrap.ng-star-inserted")
            valores = [v.text.strip() for v in valores_expl if re.match(r"^\d", v.text.strip())]
        except Exception:
            warn("No se encontró información de explotación.")


        # ---- 💾 Guardar resultados ----
        data["confederacion_info"] = {
            "codigo": info.get("Código", ""),
            "nombre": info.get("Nombre", ""),
            "codigo_europeo": info.get("Código europeo", ""),
            "horizonte": info.get("Horizonte", ""),
            "poblacion_asentada": info.get("Población asentada (2022)", ""),
            "recurso": recurso_val,
            "hidrogeo": hidro_desc,
            "explotacion": valores
        }

        json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        done("Información de Confederación guardada correctamente.")

    except Exception as e:
        warn(f"Error durante la extracción: {e}")
        driver.save_screenshot("debug_confederacion_error.png")

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
