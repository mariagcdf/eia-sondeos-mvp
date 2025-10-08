# -*- coding: utf-8 -*-
"""
Cliente Selenium para el visor CH Duero:
https://mirame.chduero.es/chduero/viewer

Devuelve: {"id": str|None, "url": str|None, "ok": bool, "error": str|None}

Requisitos:
    pip install selenium webdriver-manager python-dotenv
Opcional .env:
    CHROME_DRIVER_PATH=/ruta/a/chromedriver   # si no quieres webdriver-manager
    CHD_VIEWER_URL=https://mirame.chduero.es/chduero/viewer
    SELENIUM_WAIT_TIME=15
    SELENIUM_HEADLESS=1
"""

from __future__ import annotations
import os
import time
from typing import Dict, Any, List
from dotenv import load_dotenv

load_dotenv(override=True)

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

try:
    from webdriver_manager.chrome import ChromeDriverManager
    _HAS_WDM = True
except Exception:
    _HAS_WDM = False

CHD_VIEWER_URL = os.getenv("CHD_VIEWER_URL", "https://mirame.chduero.es/chduero/viewer")
CHROMEDRIVER_PATH = os.getenv("CHROME_DRIVER_PATH", "").strip()
WAIT_TIME = int(os.getenv("SELENIUM_WAIT_TIME", "15"))
_HEADLESS = os.getenv("SELENIUM_HEADLESS", "1") not in ("0", "false", "False")


def _mk_driver() -> webdriver.Chrome:
    opts = webdriver.ChromeOptions()
    if _HEADLESS:
        opts.add_argument("--headless=new")
    opts.add_argument("--start-maximized")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")

    if CHROMEDRIVER_PATH and os.path.exists(CHROMEDRIVER_PATH):
        service = Service(CHROMEDRIVER_PATH)
    else:
        if not _HAS_WDM:
            raise RuntimeError(
                "No se encontró CHROME_DRIVER_PATH y falta webdriver-manager. "
                "Instala: pip install webdriver-manager, o define CHROME_DRIVER_PATH en .env"
            )
        service = Service(ChromeDriverManager().install())

    return webdriver.Chrome(service=service, options=opts)


def _to_comma_decimal(x: float) -> str:
    return str(x).replace(".", ",")


def consultar_punto(lon: float, lat: float, wait_time: int = WAIT_TIME) -> Dict[str, Any]:
    """
    Consulta un único punto (lon/lat WGS84).
    """
    out: Dict[str, Any] = {"id": None, "url": None, "ok": False, "error": None}
    driver = _mk_driver()
    wait = WebDriverWait(driver, wait_time)

    try:
        driver.get(CHD_VIEWER_URL)
        wait.until(EC.presence_of_element_located((By.ID, "LON")))

        lon_input = driver.find_element(By.ID, "LON")
        lat_input = driver.find_element(By.ID, "LAT")
        lon_input.clear()
        lat_input.clear()
        lon_input.send_keys(_to_comma_decimal(lon))
        lat_input.send_keys(_to_comma_decimal(lat))

        driver.find_element(By.ID, "m-xylocator-loc").click()

        try:
            span = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".valor > span.masInfo")))
            id_text = (span.text or "").strip()
            if id_text:
                out["id"] = id_text
                out["ok"] = True
                out["url"] = f"https://mirame.chduero.es/chduero/public/surfaceWaterBody/river/search/general/{id_text}"
            else:
                out["error"] = "Span masInfo vacío."
        except TimeoutException:
            out["error"] = "No apareció el ID (timeout)."

    except Exception as e:
        out["error"] = f"EXC: {e}"
    finally:
        try:
            driver.quit()
        except Exception:
            pass

    return out


def consultar_batch(puntos: List[Dict[str, float]], pause_s: float = 1.5) -> List[Dict[str, Any]]:
    """
    Lista de puntos: [{'lon': -5.8, 'lat': 37.6}, ...]
    """
    out = []
    for p in puntos:
        out.append(consultar_punto(p["lon"], p["lat"]))
        time.sleep(pause_s)
    return out
