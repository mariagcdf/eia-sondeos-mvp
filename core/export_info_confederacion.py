import json, time, re, sys
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import ActionChains
from selenium.common.exceptions import NoSuchElementException


# =========================================================
# === Funciones auxiliares ================================
# =========================================================
def step(msg): print(f"RN_STEP: {msg}", flush=True)
def warn(msg): print(f"RN_WARN: {msg}", flush=True)
def done(msg): print(f"RN_DONE: {msg}", flush=True)


# =========================================================
# === Scrapers de pop-up ================================
# =========================================================

def scrape_popup_unidad_y_subzona(driver):
    """Extrae Unidad Hidrogeológica y Subzona desde el pop-up (buscando globalmente en el DOM)."""
    step("Intentando extraer Unidad Hidrogeológica y Subzona desde el pop-up…")
    data = {}

    try:
        # Esperar hasta que aparezcan tablas con esos captions en cualquier parte del DOM
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((
                By.XPATH,
                "//caption[contains(., 'Unidades hidrogeológicas') or contains(., 'Subzonas propuestas')]"
            ))
        )

        # Buscar todas las tablas con caption de interés
        captions = driver.find_elements(
            By.XPATH,
            "//caption[contains(., 'Unidades hidrogeológicas') or contains(., 'Subzonas propuestas')]"
        )

        for caption in captions:
            try:
                titulo = caption.text.strip()
                tabla = caption.find_element(By.XPATH, "./ancestor::table")
                filas = tabla.find_elements(By.XPATH, ".//tr")

                bloque = {}
                for fila in filas:
                    try:
                        campo = fila.find_element(By.CLASS_NAME, "campo").text.strip().rstrip(":")
                        valor = fila.find_element(By.CLASS_NAME, "valor").text.strip()
                        bloque[campo] = valor
                    except Exception:
                        continue

                if bloque:
                    if "hidrogeológicas" in titulo.lower():
                        data["Unidad hidrogeológica"] = bloque
                        step(f"Unidad hidrogeológica detectada: {bloque}")
                    elif "subzonas" in titulo.lower():
                        data["Subzona propuesta"] = bloque
                        step(f"Subzona propuesta detectada: {bloque}")
            except Exception as e:
                warn(f"No se pudo procesar una de las tablas: {e}")

        if not data:
            warn("No se encontraron tablas de Unidad o Subzona en el popup.")
    except Exception:
        warn("No se encontró el contenido del popup con Unidad o Subzona.")

    return data



# =========================================================
# === Scrapers de pestañas de la ficha ====================
# =========================================================
def scrape_datos_generales(driver):
    """Extrae los campos principales de la pestaña 'Datos generales'."""
    wait = WebDriverWait(driver, 15)
    try:
        # Activar la pestaña
        xpath_tab = "//div[contains(@class,'mat-tab-label-content') and normalize-space(text())='Datos generales']"
        tab = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_tab)))
        driver.execute_script("arguments[0].click();", tab)
        time.sleep(3)

        # Obtener los valores (en los spans con clase 'float-end')
        spans = wait.until(EC.presence_of_all_elements_located(
            (By.XPATH, "//mat-tab-body[contains(@class,'mat-tab-body-active')]//span[contains(@class,'float-end')]")
        ))
        valores = [s.text.strip() for s in spans if s.text.strip()]

        # Asignar los valores esperados por orden
        claves = [
            "Código",
            "Nombre",
            "Código europeo",
            "Horizonte",
            "Población asentada (2022)"
        ]
        data = {k: valores[i] if i < len(valores) else "" for i, k in enumerate(claves)}

        return {"Datos generales": data}

    except Exception as e:
        warn(f"Error en scrape_datos_generales: {e}")
        return {"Datos generales": {}}


def scrape_recurso(driver):
    """Extrae datos de la pestaña 'Recurso'."""
    wait = WebDriverWait(driver, 15)
    try:
        xpath_tab = "//div[contains(@class,'mat-tab-label-content') and normalize-space(text())='Recurso']"
        tab = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_tab)))
        driver.execute_script("arguments[0].click();", tab)
        time.sleep(4)
        body = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//mat-tab-body[contains(@class,'mat-tab-body-active')]")
        ))
        text = body.text
        result = {}
        for i, line in enumerate(text.split("\n")):
            if line in ["Restricciones ambientales [hm3/año]", "Recurso disponible [hm3/año]"]:
                try:
                    result[line] = float(text.split("\n")[i + 1].replace(",", "."))
                except:
                    result[line] = text.split("\n")[i + 1]
        return {"Recurso": result}
    except Exception as e:
        warn(f"Error en scrape_recurso: {e}")
        return {"Recurso": {}}


def scrape_hidrogeo(driver):
    """Extrae datos de la pestaña 'Hidrogeo'."""
    wait = WebDriverWait(driver, 15)
    try:
        label = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//label[normalize-space(text())='Hidrogeo']")
        ))
        tab = label.find_element(By.XPATH, "./ancestor::div[@role='tab']")
        driver.execute_script("arguments[0].click();", tab)
        time.sleep(2)
        active_tab = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//mat-tab-body[contains(@class,'mat-tab-body-active')]")
        ))
        items = active_tab.find_elements(By.XPATH, ".//mat-list-item")
        data = {}
        for item in items:
            try:
                k = item.find_element(By.CLASS_NAME, "float-start").text.strip()
                v = item.find_element(By.CLASS_NAME, "float-end").text.strip()
                data[k] = v
            except:
                continue
        return {"Hidrogeo": data}
    except Exception as e:
        warn(f"Error en scrape_hidrogeo: {e}")
        return {"Hidrogeo": {}}


def scrape_explotacion(driver):
    """Extrae datos de la pestaña 'Explotación'."""
    wait = WebDriverWait(driver, 15)
    try:
        xpath = "//div[@role='tab' and .//label[normalize-space(text())='Explotación']]"
        tab = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
        driver.execute_script("arguments[0].click();", tab)
        time.sleep(5)
        active_tab = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//mat-tab-body[contains(@class,'mat-tab-body-active')]")
        ))
        text = active_tab.text
        data = {}
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        for i, line in enumerate(lines):
            if line in ["Índice de explotación (derecho inscrito)", "Índice de explotación (volumen demandado)"]:
                try:
                    data[line] = float(lines[i + 1].replace(",", "."))
                except:
                    data[line] = lines[i + 1]
        return {"Explotación": data}
    except Exception as e:
        warn(f"Error en scrape_explotacion: {e}")
        return {"Explotación": {}}


def scrape_estado(driver):
    """Extrae datos de la pestaña 'Estado'."""
    wait = WebDriverWait(driver, 15)
    try:
        xpath_tab = "//div[contains(@class,'mat-tab-label-content') and normalize-space(text())='Estado']"
        tab = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_tab)))
        driver.execute_script("arguments[0].click();", tab)
        time.sleep(2)
        body = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//mat-tab-body[contains(@class,'mat-tab-body-active')]")
        ))
        text = body.text
        secciones = {
            "Estado final de la masa": {},
            "Estado cuantitativo de la masa": {},
            "Estado químico de la masa": {}
        }
        current = None
        lines = text.split("\n")
        for i, l in enumerate(lines):
            if "Estado final de la masa" in l: current = "Estado final de la masa"
            elif "Estado cuantitativo de la masa" in l: current = "Estado cuantitativo de la masa"
            elif "Estado químico de la masa" in l: current = "Estado químico de la masa"
            elif current:
                if "Designación definitiva" in l and i + 1 < len(lines):
                    secciones[current]["Designación definitiva"] = lines[i + 1]
                if "Justificación" in l and i + 1 < len(lines):
                    secciones[current]["Justificación"] = lines[i + 1]
        return {"Estado": secciones}
    except Exception as e:
        warn(f"Error en scrape_estado: {e}")
        return {"Estado": {}}

def accept_cookies(driver):
        try:
            btn = WebDriverWait(driver, 8).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a.cc-btn.cc-allow"))
            )
            driver.execute_script("arguments[0].click();", btn)
            step("Cookies aceptadas.")
            time.sleep(1)
        except Exception:
            warn("No se encontró banner de cookies, continuando…")


# =========================================================
# === FLUJO PRINCIPAL =====================================
# =========================================================
def main():
    if len(sys.argv) < 2:
        raise SystemExit("Uso: python export_info_confederacion.py <json_path>")

    json_path = Path(sys.argv[1]).resolve()
    if not json_path.exists():
        raise FileNotFoundError(f"No existe: {json_path}")

    data = json.loads(json_path.read_text(encoding="utf-8"))
    utm_x = str(data["utm_x_principal"]).replace(".", ",")
    utm_y = str(data["utm_y_principal"]).replace(".", ",")
    step(f"Coordenadas UTM => X={utm_x}, Y={utm_y}")

    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 60)

    try:
        # === Abrir visor ===
        step("Abriendo visor CH Duero…")
        driver.get("https://mirame.chduero.es/chduero/viewer")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.m-areas")))
        accept_cookies(driver)
        step("Visor cargado correctamente.")

        # === Localizar coordenadas ===
        btn_coord = wait.until(EC.element_to_be_clickable((By.ID, "m-locator-xylocator")))
        driver.execute_script("arguments[0].click();", btn_coord)
        Select(driver.find_element(By.ID, "m-xylocator-srs")).select_by_value("EPSG:25830")
        driver.find_element(By.ID, "UTM-X").send_keys(utm_x)
        driver.find_element(By.ID, "UTM-Y").send_keys(utm_y)
        driver.find_element(By.ID, "m-xylocator-loc").click()
        step("Coordenadas localizadas.")
        time.sleep(3)


        # === Activar capa ===
        step("Activando capa 'Información Plan Hidrológico 2022-2027'…")
        btn_capas = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Catálogo de capas')]")))
        driver.execute_script("arguments[0].click();", btn_capas)
        time.sleep(2)

        capa_xpath = ("//span[contains(., 'Información Plan Hidrológico 2022-2027')]/ancestor::mat-checkbox"
                      "//span[contains(@class,'mat-checkbox-inner-container')]")
        inner = wait.until(EC.presence_of_element_located((By.XPATH, capa_xpath)))
        ActionChains(driver).move_to_element(inner).pause(0.3).click(inner).perform()
        step("Capa 'Información Plan Hidrológico 2022-2027' activada.")
        time.sleep(2)

         # === Refrescar capas ===
        step("Refrescando capas…")
        try:
            btn_refresh = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//span[contains(., 'Refrescar capas')]/parent::button")
            ))
            driver.execute_script("arguments[0].click();", btn_refresh)
            time.sleep(3)
            wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, ".m-loading")))
            step("✅ Capas refrescadas correctamente.")
        except Exception:
            warn("No se pudo refrescar capas correctamente.")

        # === Cerrar catálogo ===
        try:
            btn_close = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(., 'Cerrar')]/parent::button")))
            driver.execute_script("arguments[0].click();", btn_close)
            step("Ventana del catálogo cerrada.")
        except Exception:
            warn("No se pudo cerrar el catálogo.")

        step("Haz clic en el punto del mapa para abrir el popup (no pulses masInfo todavía).")
        for _ in range(40):
            overlays = driver.find_elements(By.CSS_SELECTOR, "div.ol-overlay-container")
            if any("Subzonas propuestas" in o.text or "Unidades hidrogeológicas" in o.text for o in overlays):
                step("Popup detectado, comenzando la extracción…")
                break
            time.sleep(1)
        else:
            warn("No se detectó el popup a tiempo, continúo sin extraer.")
            
        popup_info = scrape_popup_unidad_y_subzona(driver)
        if popup_info:
            if "confederacion_info" not in data:
                data["confederacion_info"] = {}
            data["confederacion_info"]["Popup"] = popup_info
            json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            step("Datos del popup extraídos y guardados correctamente.")
        else:
            warn("No se encontraron datos en el popup.")


        # === Espera manual ===
        step("Espera manual: haz clic en el punto y luego en 'masInfo' para abrir la ficha técnica en otra pestaña.")
        step("Esperando que abras la ficha técnica manualmente...")
        initial_tabs = driver.window_handles
        for _ in range(60):  # 2 minutos
            handles = driver.window_handles
            if len(handles) > len(initial_tabs):
                new_tab = [h for h in handles if h not in initial_tabs][0]
                driver.switch_to.window(new_tab)
                step("Ficha técnica abierta correctamente.")
                break
            time.sleep(2)
        else:
            warn("No se detectó la apertura de la ficha técnica en el tiempo máximo.")
            return


        # === Scrapeo ===
        resultado = {}
        resultado.update(scrape_datos_generales(driver))
        resultado.update(scrape_recurso(driver))
        resultado.update(scrape_hidrogeo(driver))
        resultado.update(scrape_explotacion(driver))
        resultado.update(scrape_estado(driver))
        # Fusionar la nueva información con la ya existente (sin borrar Popup)
        if "confederacion_info" not in data:
            data["confederacion_info"] = {}

        data["confederacion_info"].update(resultado)


        json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        done("Datos de Confederación extraídos y guardados correctamente.")

        # === Generar texto de masas de agua afectadas ===
        try:
            from sintesis.confederacion_llm import generar_masas_agua_afectadas
            generar_masas_agua_afectadas(str(json_path))
            done("Texto automático de 'Masas de agua afectadas' generado y añadido al JSON.")
        except Exception as e:
            warn(f"No se pudo generar el texto automático: {e}")

    except Exception as e:
        warn(f"Error general: {e}")
        driver.save_screenshot("debug_confederacion_error.png")

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
