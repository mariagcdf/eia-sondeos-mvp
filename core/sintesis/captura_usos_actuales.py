# import sys, time, json, traceback
# from pathlib import Path
# from PIL import Image

# from selenium import webdriver
# from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait, Select
# from selenium.webdriver.support import expected_conditions as EC

# def step(m): print(f"CAP_STEP: {m}", flush=True)
# def warn(m): print(f"CAP_WARN: {m}", flush=True)
# def err(m):  print(f"CAP_ERR: {m}", flush=True)

# def click_js(driver, el):
#     driver.execute_script("arguments[0].click();", el)

# def safe_find(driver, by, sel, timeout=10):
#     try:
#         return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, sel)))
#     except Exception:
#         return None

# def safe_click(driver, by, sel, timeout=10):
#     try:
#         el = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((by, sel)))
#         click_js(driver, el)
#         return True
#     except Exception:
#         return False

# def accept_cookies(driver, timeout=8):
#     step("Buscando banner de cookies…")
#     selectors = [
#         (By.XPATH, "//button[contains(translate(., 'ACEPT', 'acept'), 'acept')]"),
#         (By.XPATH, "//button[contains(., 'Aceptar')]"),
#         (By.XPATH, "//button[contains(., 'Acepto')]"),
#         (By.XPATH, "//button[contains(., 'Accept')]"),
#         (By.CSS_SELECTOR, "button#onetrust-accept-btn-handler"),
#         (By.CSS_SELECTOR, "button[aria-label*='acept'],button[aria-label*='Accept']"),
#     ]
#     deadline = time.time() + timeout
#     while time.time() < deadline:
#         for by, sel in selectors:
#             try:
#                 btns = driver.find_elements(by, sel)
#                 for b in btns:
#                     if b.is_displayed():
#                         click_js(driver, b)
#                         step("Cookies aceptadas.")
#                         time.sleep(1)
#                         return True
#             except Exception:
#                 pass
#         time.sleep(0.5)
#     warn("No se encontró banner de cookies (continuamos).")
#     return False

# def close_side_panels(driver):
#     """Cierra los paneles laterales izquierdo y derecho del visor CH Duero."""
#     step("Cerrando paneles laterales…")
#     try:
#         # Botón derecho (flecha hacia la derecha)
#         btn_right = driver.find_elements(By.CSS_SELECTOR, "button.g-cartografia-flecha-derecha")
#         for b in btn_right:
#             if b.is_displayed():
#                 click_js(driver, b)
#                 step("Panel derecho cerrado.")
#                 time.sleep(1)
#                 break

#         # Botón izquierdo (flecha hacia la izquierda)
#         btn_left = driver.find_elements(By.CSS_SELECTOR, "button.g-cartografia-flecha-izquierda")
#         for b in btn_left:
#             if b.is_displayed():
#                 click_js(driver, b)
#                 step("Panel izquierdo cerrado.")
#                 time.sleep(1)
#                 break

#     except Exception as e:
#         warn(f"No se pudieron cerrar todos los paneles: {e}")

# def open_coords_panel(driver):
#     step("Abriendo panel de coordenadas…")
#     if not safe_click(driver, By.ID, "m-locator-xylocator", timeout=15):
#         if not safe_click(driver, By.XPATH, "//button[contains(., 'Coordenadas') or contains(., 'Localizar')]", timeout=8):
#             raise RuntimeError("No se pudo abrir el panel de coordenadas.")
#     sel = safe_find(driver, By.ID, "m-xylocator-srs", timeout=10)
#     if not sel:
#         raise RuntimeError("No apareció el selector de SRS en el panel de coordenadas.")

# def set_coords_and_locate(driver, utm_x, utm_y):
#     step("Seleccionando EPSG:25830 y localizando punto…")
#     Select(driver.find_element(By.ID, "m-xylocator-srs")).select_by_value("EPSG:25830")
#     x = driver.find_element(By.ID, "UTM-X")
#     y = driver.find_element(By.ID, "UTM-Y")
#     driver.execute_script("arguments[0].value='';", x)
#     driver.execute_script("arguments[0].value='';", y)
#     x.send_keys(utm_x)
#     y.send_keys(utm_y)
#     click_js(driver, driver.find_element(By.ID, "m-xylocator-loc"))
#     time.sleep(3)

# def open_layers_panel(driver):
#     step("Abriendo panel de fondo (BackImgLayer)…")
#     try:
#         btn = safe_find(driver, By.CSS_SELECTOR, "button.backimglyr-simbolo-cuadros", timeout=10)
#         if not btn:
#             raise RuntimeError("No se encontró el botón BackImgLayer.")
#         click_js(driver, btn)
#         time.sleep(2)
#         step("Panel de mapas base abierto.")
#         return True
#     except Exception as e:
#         warn(f"No se pudo abrir BackImgLayer: {e}")
#         return False

# def enable_pnoa_layer(driver):
#     step("Buscando miniatura de PNOA (Ministerio de Fomento)…")
#     try:
#         pnoa_imgs = driver.find_elements(
#             By.XPATH,
#             "//img[contains(translate(@alt, 'PNOA', 'pnoa'), 'pnoa') or contains(@src, 'pnoa')]"
#         )
#         if not pnoa_imgs:
#             raise RuntimeError("No se encontró la miniatura PNOA en el panel.")
#         for img in pnoa_imgs:
#             alt = img.get_attribute("alt") or ""
#             if "fomento" in alt.lower() or "pnoa" in alt.lower():
#                 click_js(driver, img)
#                 step(f"Mapa base PNOA activado: {alt}")
#                 time.sleep(4)
#                 return True
#         click_js(driver, pnoa_imgs[0])
#         step("Mapa PNOA activado (fallback).")
#         time.sleep(4)
#         return True
#     except Exception as e:
#         warn(f"No se pudo activar capa PNOA: {e}")
#         return False

# def find_map_for_screenshot(driver):
#     for sel in [
#         "div.ol-viewport",
#         "div.m-areas div.ol-viewport",
#         "div[class*='map'] div.ol-viewport",
#         "div.ol-viewport canvas"
#     ]:
#         el = safe_find(driver, By.CSS_SELECTOR, sel, timeout=6)
#         if el and el.is_displayed():
#             return el
#     return None

# def crop_center(in_path: Path, out_path: Path):
#     """Recorta el centro del mapa (quita paneles laterales y barras)."""
#     img = Image.open(in_path)
#     w, h = img.size
#     left = int(w * 0.25)
#     right = int(w * 0.75)
#     top = int(h * 0.10)
#     bottom = int(h * 0.90)
#     img.crop((left, top, right, bottom)).save(out_path)

# def main():
#     if len(sys.argv) < 2:
#         print("Uso: python captura_usos_actuales.py <json_path>", flush=True)
#         sys.exit(1)

#     json_path = Path(sys.argv[1]).resolve()
#     data = json.loads(json_path.read_text(encoding="utf-8"))

#     utm_x = str(data.get("utm_x_principal", "")).replace(".", ",")
#     utm_y = str(data.get("utm_y_principal", "")).replace(".", ",")

#     chrome_options = Options()
#     chrome_options.add_argument("--start-maximized")
#     chrome_options.add_argument("--disable-gpu")
#     chrome_options.add_argument("--no-sandbox")
#     chrome_options.add_argument("--disable-dev-shm-usage")
#     # chrome_options.add_argument("--headless=new")  # activa si es servidor sin GUI

#     driver = webdriver.Chrome(options=chrome_options)
#     wait = WebDriverWait(driver, 60)

#     out_dir = Path("outputs"); out_dir.mkdir(exist_ok=True)
#     ts = int(time.time())
#     tmp_path = out_dir / f"tmp_captura_usos_{ts}.png"
#     out_path = out_dir / f"captura_usos_{ts}.png"

#     try:
#         step("Abriendo visor CH Duero…")
#         driver.get("https://mirame.chduero.es/chduero/viewer")
#         wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.m-areas")))
#         time.sleep(3)

#         # Aceptar cookies y cerrar paneles
#         accept_cookies(driver)
#         close_side_panels(driver)

#         # Localizar coordenadas y activar capa
#         open_coords_panel(driver)
#         set_coords_and_locate(driver, utm_x, utm_y)
#         if open_layers_panel(driver):
#             enable_pnoa_layer(driver)
#         close_side_panels(driver)  # cerrar de nuevo antes de capturar

#         # Captura
#         step("Capturando mapa…")
#         target = find_map_for_screenshot(driver)
#         if not target:
#             raise RuntimeError("No se encontró el mapa para captura.")
#         target.screenshot(str(tmp_path))
#         crop_center(tmp_path, out_path)
#         tmp_path.unlink(missing_ok=True)

#         print(f"UA_CAPTURE: {out_path}", flush=True)
#         step(f"Imagen guardada: {out_path}")

#         # Actualizar JSON
#         data["captura_usos_actuales"] = str(out_path)
#         json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
#         step("JSON actualizado con la ruta de la captura.")
#         sys.exit(0)

#     except Exception:
#         print("CAP_ERR: Error no controlado:", flush=True)
#         traceback.print_exc()
#         sys.exit(3)
#     finally:
#         try:
#             driver.quit()
#         except Exception:
#             pass

# if __name__ == "__main__":
#     main()

import sys, time, json
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from PIL import Image


def step(msg):
    print(f"UA_STEP: {msg}", flush=True)

def warn(msg):
    print(f"UA_WARN: {msg}", flush=True)

def done(path_img):
    print(f"UA_CAPTURE: {path_img}", flush=True)


def crop_center(in_path: Path, out_path: Path):
    """Recorta el centro del mapa (quita paneles laterales y barras)."""
    img = Image.open(in_path)
    w, h = img.size
    left = int(w * 0.25)
    right = int(w * 0.75)
    top = int(h * 0.10)
    bottom = int(h * 0.90)
    img.crop((left, top, right, bottom)).save(out_path)
    img.close()


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
        print("Uso: python captura_usos_actuales.py <json_path>", flush=True)
        sys.exit(1)

    json_path = Path(sys.argv[1]).resolve()
    if not json_path.exists():
        print(f"❌ No existe JSON: {json_path}", flush=True)
        sys.exit(1)

    data = json.loads(json_path.read_text(encoding="utf-8"))
    utm_x = str(data.get("utm_x_principal", "")).replace(",", ".")
    utm_y = str(data.get("utm_y_principal", "")).replace(",", ".")
    step(f"Coordenadas UTM => X={utm_x}, Y={utm_y}")

    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # chrome_options.add_argument("--headless=new")  # activar si no hay entorno gráfico

    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 40)

    out_dir = Path("outputs"); out_dir.mkdir(exist_ok=True)
    ts = int(time.time())
    tmp_path = out_dir / f"tmp_captura_usos_{ts}.png"
    out_path = out_dir / f"captura_usos_{ts}.png"

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

        # === 3. Localizar coordenadas ===
        try:
            Select(driver.find_element(By.ID, "m-xylocator-srs")).select_by_value("EPSG:25830")
        except Exception:
            warn("No se encontró selector EPSG:25830, buscando alternativa…")
            select_alt = driver.find_elements(By.XPATH, "//select[contains(., '25830')]")
            if select_alt:
                Select(select_alt[0]).select_by_visible_text("EPSG:25830")

        try:
            x_field = driver.find_element(By.ID, "UTM-X")
            y_field = driver.find_element(By.ID, "UTM-Y")
        except Exception:
            x_field = driver.find_element(By.XPATH, "//input[contains(@placeholder,'X')]")
            y_field = driver.find_element(By.XPATH, "//input[contains(@placeholder,'Y')]")

        x_field.clear(); y_field.clear()
        x_field.send_keys(utm_x)
        y_field.send_keys(utm_y)
        driver.find_element(By.ID, "m-xylocator-loc").click()
        step("Coordenadas localizadas correctamente.")
        time.sleep(3)

        # === 4. Activar capa PNOA ===
        step("Activando mapa base PNOA…")
        try:
            btn_backimg = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.backimglyr-simbolo-cuadros"))
            )
            driver.execute_script("arguments[0].click();", btn_backimg)
            time.sleep(1.5)

            # Seleccionar el DIV del PNOA
            pnoa_div = wait.until(
                EC.presence_of_element_located((By.ID, "m-backimglayer-lyr-pnoa"))
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", pnoa_div)
            time.sleep(0.5)

            # Hacer clic real sobre el DIV (no sobre el IMG)
            driver.execute_script("""
                const el = arguments[0];
                const evt = new MouseEvent('click', {bubbles: true, cancelable: true, view: window});
                el.dispatchEvent(evt);
            """, pnoa_div)
            time.sleep(2)

            # Confirmar que está activo
            for _ in range(20):
                cls = pnoa_div.get_attribute("class") or ""
                if "active" in cls:
                    step("✅ Confirmado: capa PNOA activa.")
                    break
                time.sleep(5)
            else:
                warn("⚠️ No se detectó la clase 'active' en el PNOA tras el clic.")

            # Cerrar el panel de mapas base
            driver.execute_script("arguments[0].click();", btn_backimg)
            step("Panel de mapas base cerrado.")
            time.sleep(1.5)

        except Exception as e:
            warn(f"No se pudo activar capa PNOA: {e}")
            # Intento alternativo mediante JS
            driver.execute_script("""
                try {
                    const visor = window.mapea || window.visor || window.mapjs;
                    if (visor && visor.setBaseLayer) visor.setBaseLayer('PNOA (Ministerio de Fomento)');
                } catch(e) { console.warn('Fallback JS PNOA error', e); }
            """)
            time.sleep(2)

        # === 5. Cerrar paneles laterales ===
        step("Cerrando paneles laterales…")
        try:
            for sel, name in [
                ("button.g-cartografia-flecha-derecha", "derecho"),
                ("button.g-cartografia-flecha-izquierda", "izquierdo")
            ]:
                for b in driver.find_elements(By.CSS_SELECTOR, sel):
                    if b.is_displayed():
                        driver.execute_script("arguments[0].click();", b)
                        step(f"Panel {name} cerrado.")
                        time.sleep(1)
        except Exception as e:
            warn(f"No se pudieron cerrar todos los paneles: {e}")

        # === 6. Capturar mapa ===
        step("Capturando mapa…")
        target = None
        for sel in ["div.ol-viewport", "div.m-areas div.ol-viewport", "canvas.ol-layer"]:
            try:
                el = driver.find_element(By.CSS_SELECTOR, sel)
                if el.is_displayed():
                    target = el
                    break
            except Exception:
                continue

        if not target:
            raise RuntimeError("No se encontró el mapa para captura.")

        target.screenshot(str(tmp_path))
        crop_center(tmp_path, out_path)
        tmp_path.unlink(missing_ok=True)
        step(f"Imagen guardada: {out_path}")
        done(out_path)

        # === 7. Actualizar JSON ===
        data["captura_usos_actuales"] = str(out_path)
        json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        step("JSON actualizado con la ruta de la captura.")

    except Exception as e:
        warn(f"Error inesperado: {e}")
        driver.save_screenshot("debug_usos_error.png")

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
