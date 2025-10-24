
# 🧠 Desarrollo de un Sistema Inteligente para la Redacción Automatizada de Estudios de Impacto Ambiental (EIA)

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-App-brightgreen)
![OpenAI](https://img.shields.io/badge/OpenAI-LLM-orange)
![Selenium](https://img.shields.io/badge/Selenium-Automation-lightgrey)

## 📄 Descripción general

Este proyecto implementa un **sistema inteligente** para la **automatización de la redacción de Estudios de Impacto Ambiental (EIA) simplificados** en proyectos hidráulicos, con foco en **sondeos de captación de aguas subterráneas**. Combina **RPA (Selenium)**, **procesamiento de documentos** y **modelos de lenguaje (LLM)** para producir un **borrador completo y editable** a partir de un **Proyecto de Ingeniería en PDF**.

**Objetivos clave:**
- Reducir el tiempo de elaboración de 3–5 horas a ~**5 minutos**.
- **Homogeneidad técnica** y documental.
- Minimizar **errores humanos** en recopilación y transcripción.

Colaboración con **IPSA Ingenieros y Soluciones Avanzadas S.L.** (Salamanca, España).

---

## 🔧 Características principales

- **Extracción automática** de datos técnicos desde PDF (coordenadas UTM/WGS84, profundidades, caudales, potencias, geología, etc.).
- **Consultas automatizadas** a fuentes oficiales:
  - **CH Duero (Mírame CHD)** → recurso, masa y nivel de explotación.
  - **Red Natura 2000** → detección de códigos ESXXXXXXX y descarga/uso de SDF.
  - **Catastro** → clase/uso del suelo, superficie, cultivos.
- **Redacción asistida por LLM** de apartados clave:
  - Alternativas, instalación eléctrica, usos del terreno, medio biótico, perceptual y socioeconómico, repercusión en masas de agua, impactos sociales, resumen final.
- **Exportación a DOCX** con **plantilla corporativa** (placeholders y tablas respetando estilos/formatos).
- **Interfaz en Streamlit** para ejecutar el flujo extremo a extremo.

---

## 🧱 Arquitectura del sistema

El sistema sigue una **arquitectura modular** y jerárquica. Los módulos se comunican mediante un **JSON central** que actúa como “verdad única” del proyecto.

1) **Módulo 1 — Extracción del Proyecto de Ingeniería**
- `regex_extract.py`: extracción robusta por **expresiones regulares** (coordenadas UTM, lat/long, profundidad, caudal, diámetros, potencias).
- `bloques_textuales` (integrado): limpieza y segmentación de bloques narrativos (antecedentes, localización, consumo, geología).
- `pdf_reader.py`: lectura con **pdfplumber**, eliminación de encabezados/pies y detección de páginas ricas en información.
- `llm_utils.py`: prompts técnicos, **parseo a JSON**, fusión con regex y **fallback** para datos incompletos.

2) **Módulo 2 — Exportación de información de páginas públicas**
- `export_info_confederacion.py`: automatiza **Mírame CHD** (Selenium) para obtener “Recurso”, “Hidrogeo” y “Explotación”.
- `export_info_red_natura.py`: activa capas Red Natura, detecta códigos ESXXXXXXX y lanza:
  - `medio_biotico_red_natura.py` (si aplica) o
  - `medio_biotico_no_red_natura.py` (si no aplica).
- `catastro_client.py`: obtiene referencia catastral, clase/uso, superficie y cultivos desde **Catastro** (Selenium + LLM para estructuración).

3) **Módulo 3 — Redacción de apartados con LLM**
- `usos_actuales_llm.py`: redacta **Usos actuales del terreno** con datos catastrales + captura PNOA vía:
- `captura_usos_actuales.py`: recorte automático de ortofoto **PNOA** (Selenium + PIL).
- `alternativas_llm.py`: genera **Alternativas** (descripción, valoración y justificación).
- `instalacion_llm.py`: redacta **Instalación eléctrica** (conexión a red o fotovoltaica).

4) **Módulo 4 — Síntesis y exportación**
- `placeholders_global.py`: construye el **mapa global de placeholders** (datos técnicos + bloques textuales + marcadores IA).
- `redactar_placeholder.py`: sintetiza, limpia y normaliza textos (consumo, localización, impactos, resumen).
- `export_docx_from_placeholder_map.py`: reemplaza `{{placeholders}}` en **plantilla Word**, completa **tablas** y exporta a `outputs/`.

5) **Módulo 5 — Interfaz**
- `app.py` (**Streamlit**): orquestra el flujo (subida PDF → extracción → consultas → redacción → exportación DOCX) con logs y acciones guiadas.

---

## 🗂️ Estructura del repositorio

## 🧭 Estructura del repositorio

```bash
proyecto-eia-automatizado/
│
├─ extraccion/
│  ├─ __init__.py
│  ├─ bloques_textuales.py
│  ├─ llm_utils.py
│  ├─ pdf_reader.py
│  └─ regex_extract.py
│
├─ sintesis/
│  ├─ __init__.py
│  ├─ alternativas_llm.py
│  ├─ captura_usos_actuales.py
│  ├─ catastro_client.py
│  ├─ confederacion_llm.py
│  ├─ instalacion_electrica_llm.py
│  ├─ medio_biotico_no_rednatura_llm.py
│  ├─ medio_biotico_rednatura_llm.py
│  ├─ redactar_placeholder.py
│  └─ usos_actuales_llm.py
│
├─ build_global_json.py
├─ export_docx_template.py
├─ export_info_confederacion.py
├─ export_info_rednatura.py
├─ plantilla_EIA.docx
├─ app.py
├─ requirements.txt
├─ .env
└─ README.md

🧰 Instalación y uso
--------------------

1️⃣ Clonar el repositorio
-------------------------
git clone https://github.com/usuario/eia-automatizado.git
cd eia-automatizado


2️⃣ Crear y activar un entorno virtual
--------------------------------------
python -m venv venv
source venv/bin/activate   # En Linux / macOS
venv\Scripts\activate      # En Windows


3️⃣ Instalar dependencias
-------------------------
pip install -r requirements.txt


4️⃣ Configurar variables de entorno
-----------------------------------
Crea un archivo llamado .env en la raíz del proyecto con tu clave de OpenAI:

OPENAI_API_KEY=tu_clave_aqui


5️⃣ Ejecutar la aplicación
--------------------------
streamlit run app.py

Una vez iniciado, abre el enlace local que aparece en consola
(por defecto http://localhost:8501) para acceder a la interfaz.


---------------------------------------------------------------
🔒 Limitaciones actuales
---------------------------------------------------------------
- Requiere intervención manual mínima en el visor CH Duero (clic de localización)
- La estructura del PDF debe mantener un formato técnico estándar
- La disponibilidad de fuentes oficiales depende de los portales públicos
- No sustituye la validación ni firma profesional del ingeniero


---------------------------------------------------------------
🔭 Futuras líneas de desarrollo
---------------------------------------------------------------
- Extensión a Proyectos de Ingeniería completos (Memoria, Pliego, Presupuesto)
- Incorporación de microcálculos hidráulicos y eléctricos
- Compatibilidad con otras confederaciones hidrográficas
- Integración de visión artificial para reconocimiento de planos y diagramas


---------------------------------------------------------------
👩‍💻 Autora
---------------------------------------------------------------
María García-Cruz de Felipe
Máster en Ingeniería e Innovación – Evolve Academy (2025)
Colaboración con IPSA Ingenieros y Soluciones Avanzadas S.L.
