# core/sintesis/export_info_red_natura.py
import json, time, re, sys
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import ActionChains

def step(msg): print(f"RN_STEP: {msg}", flush=True)
def warn(msg): print(f"RN_WARN: {msg}", flush=True)
def result_inside(code, name): print(f"RESULT: EN_RED_NATURA|{code}|{name}", flush=True)
def result_outside(): print("RESULT: NO_APLICA", flush=True)

def main():
    # 0) JSON de entrada
    if len(sys.argv) < 2:
        raise SystemExit("Uso: python export_info_red_natura.py <json_path>")
    json_path = Path(sys.argv[1]).resolve()
    if not json_path.exists():
        raise FileNotFoundError(f"No existe: {json_path}")
    step(f"Usando JSON => {json_path.name}")

    data = json.loads(json_path.read_text(encoding="utf-8"))
    utm_x = str(data["utm_x_principal"]).replace(".", ",")
    utm_y = str(data["utm_y_principal"]).replace(".", ",")
    step(f"Coordenadas UTM => X={utm_x}, Y={utm_y}")

    # 1) Selenium
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")  # activa si ejecutas en servidor sin GUI
    chrome_options.add_argument("--start-maximized")
    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 60)

    try:
        step("Abriendo visor CH Duero…")
        driver.get("https://mirame.chduero.es/chduero/viewer")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.m-areas")))
        step("Visor cargado")

        step("Abriendo panel de coordenadas…")
        btn_coord = wait.until(EC.element_to_be_clickable((By.ID, "m-locator-xylocator")))
        driver.execute_script("arguments[0].click();", btn_coord)
        wait.until(EC.presence_of_element_located((By.ID, "m-xylocator-srs")))
        step("Panel coordenadas OK")

        # Activar capa Red Natura por texto (best-effort)
        try:
            step("Abriendo catálogo de capas…")
            btn_capas = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Catálogo de capas')]")))
            driver.execute_script("arguments[0].click();", btn_capas)
            time.sleep(2)
            label = wait.until(EC.presence_of_element_located(
                (By.XPATH, "//mat-checkbox//span[contains(normalize-space(.), 'Red Natura 2000')]")
            ))
            host = label.find_element(By.XPATH, "./ancestor::mat-checkbox")
            driver.execute_script("arguments[0].click();", host)
            step("Capa 'Red Natura 2000' activada")
            # refrescar/cerrar (opcionales)
            try:
                btn_refrescar = wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//span[contains(text(),'Refrescar capas')]/parent::button"))
                )
                driver.execute_script("arguments[0].click();", btn_refrescar)
                time.sleep(2)
            except: pass
            try:
                close_button = driver.find_element(By.XPATH, "//button[@title='Cerrar catálogo de capas']")
                driver.execute_script("arguments[0].click();", close_button)
            except: pass
        except Exception as e:
            warn(f"No se pudo activar capa Red Natura 2000: {e}. Continuamos…")

        # Localizar punto
        step("Seleccionando EPSG:25830 y localizando…")
        select_srs = Select(wait.until(EC.presence_of_element_located((By.ID, "m-xylocator-srs"))))
        select_srs.select_by_value("EPSG:25830")
        input_x = wait.until(EC.presence_of_element_located((By.ID, "UTM-X")))
        input_y = wait.until(EC.presence_of_element_located((By.ID, "UTM-Y")))
        driver.execute_script("arguments[0].value='';", input_x)
        driver.execute_script("arguments[0].value='';", input_y)
        input_x.send_keys(utm_x)
        input_y.send_keys(utm_y)
        btn_localizar = wait.until(EC.element_to_be_clickable((By.ID, "m-xylocator-loc")))
        driver.execute_script("arguments[0].click();", btn_localizar)
        time.sleep(2)
        step("Coordenadas localizadas")

        # Info y clic real
        try:
            info_button = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[title='Información'], button[aria-label='Información']"))
            )
            driver.execute_script("arguments[0].click();", info_button)
            time.sleep(1)
        except Exception as e:
            warn(f"No se pudo activar 'Información': {e}")

        try:
            canvas = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.ol-viewport canvas")))
            actions = ActionChains(driver)
            w, h = canvas.size.get("width", 400), canvas.size.get("height", 300)
            actions.move_to_element_with_offset(canvas, int(w/2), int(h/2)).click().perform()
            step("Click en el centro del mapa realizado")
            time.sleep(3)
        except Exception as e:
            warn(f"No se pudo clickar en mapa: {e}")

        # Parseo HTML
        html_doc = driver.page_source
        Path("debug_html").mkdir(exist_ok=True)
        Path("debug_html/page_full.html").write_text(html_doc, encoding="utf-8")

        m = re.search(r"Red Natura 2000.*?(ES\d{6,}).*?Nombre\s*</[^>]+>\s*<[^>]*>(.*?)</", html_doc, re.DOTALL)
        if m:
            code = m.group(1).strip()
            name = m.group(2).strip()
            data["codigos_red_natura"] = [code]
            data["nombres_red_natura"] = [name]
            data["estado_red_natura"] = "en_red_natura"
            data["red_natura"] = True
            result_inside(code, name)
        else:
            data["estado_red_natura"] = "no_aplica"
            data["red_natura"] = False
            result_outside()

        json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        step("JSON actualizado")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
