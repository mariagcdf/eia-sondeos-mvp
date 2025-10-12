import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import ActionChains
from pathlib import Path
import json

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

chrome_options = Options()
# chrome_options.add_argument("--headless")  # Opcional: ejecuta sin ventana
chrome_options.add_argument("--start-maximized")

driver = webdriver.Chrome(service=Service(), options=chrome_options)
wait = WebDriverWait(driver, 20)

try:
    driver.get("https://mirame.chduero.es/chduero/viewer/gwb")
    time.sleep(3)

    # Cambiar a iframe si existe
    iframes = driver.find_elements(By.TAG_NAME, "iframe")
    if iframes:
        driver.switch_to.frame(iframes[0])
        time.sleep(2)

    # Abrir panel de búsqueda
    locator_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Plugin panelLocator']")))
    driver.execute_script("arguments[0].scrollIntoView(true);", locator_button)
    time.sleep(1)
    driver.execute_script("arguments[0].click();", locator_button)
    time.sleep(2)

    panel_div = driver.find_element(By.CSS_SELECTOR, "div.m-plugin-locator")
    if "opened" not in panel_div.get_attribute("class"):
        actions = ActionChains(driver)
        actions.move_to_element(locator_button).click().perform()
        time.sleep(2)

    wait.until(lambda d: "opened" in d.find_element(By.CSS_SELECTOR, "div.m-plugin-locator").get_attribute("class"))

    # Clic en "Buscar por coordenadas"
    coord_button = wait.until(EC.element_to_be_clickable((By.ID, "m-locator-xylocator")))
    coord_button.click()
    time.sleep(1)

    # Seleccionar sistema de coordenadas (3ª opción)
    select_element = wait.until(EC.element_to_be_clickable((By.ID, "m-xylocator-srs")))
    select = Select(select_element)
    select.select_by_index(2)

    # Rellenar coordenadas
    input_x = wait.until(EC.presence_of_element_located((By.ID, "UTM-X")))
    input_y = wait.until(EC.presence_of_element_located((By.ID, "UTM-Y")))
    input_x.clear()
    input_x.send_keys(utm_x)
    input_y.clear()
    input_y.send_keys(utm_y)

    # Click en "Localizar"
    boton_localizar = wait.until(EC.element_to_be_clickable((By.ID, "m-xylocator-loc")))
    boton_localizar.click()

    # Esperar a que aparezca el marcador/popup en el mapa y hacer click
    marcador = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div.ol-overlaycontainer-stopevent div.m-popup")))
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", marcador)
    time.sleep(0.5)
    driver.execute_script("arguments[0].click();", marcador)

    # Esperar que aparezca la información
    wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.m-information-content-info")))
    time.sleep(2)

    # Extraer la información
    bloques = driver.find_elements(By.CSS_SELECTOR, "div.m-information-content-info")
    filas_data = []

    for bloque in bloques:
        try:
            titulo_elem = bloque.find_element(By.CSS_SELECTOR, "div > p > strong")
            titulo = titulo_elem.text.strip()
            filas = bloque.find_elements(By.CSS_SELECTOR, "table.caja tbody tr")

            for fila in filas:
                campo = fila.find_element(By.CSS_SELECTOR, "td.campo").text.strip().rstrip(":")
                valor = fila.find_element(By.CSS_SELECTOR, "td.valor").text.strip()
                filas_data.append({
                    "titulo": titulo,
                    "campo": campo,
                    "valor": valor
                })
        except Exception as e:
            print(f"Error extrayendo bloque: {e}")

    # Crear el DataFrame
    df = pd.DataFrame(filas_data)
    print(df)

except Exception as e:
    print("Error general:", e)

finally:
    driver.quit()