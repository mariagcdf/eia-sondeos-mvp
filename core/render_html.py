# core/render_html.py
from jinja2 import Template

def render_html(datos: dict, literal_blocks: dict) -> str:
    tpl = Template("""
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8"/>
  <title>EIA — {{ (datos.localizacion.municipio or 'Proyecto') }}</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 22px; color: #111; }
    h1 { color: #244b62; }
    .card { border:1px solid #ddd; border-radius:10px; padding:14px; margin:16px 0; }
    table { border-collapse: collapse; width:100%; margin-top:10px; }
    th,td { border:1px solid #ddd; padding:8px; vertical-align: top; }
    th { background:#f6f7fb; text-align:left; }
    pre { white-space: pre-wrap; background:#fafafa; border:1px solid #eee; padding:10px; border-radius:8px; }
  </style>
</head>
<body>
  <h1>Documento Ambiental Simplificado — Sondeo</h1>

  <div class="card">
    <h2>1) Datos clave</h2>
    <table>
      <tr><th>Municipio / Provincia</th><td>{{ datos.localizacion.municipio }} / {{ datos.localizacion.provincia }}</td></tr>
      <tr><th>Polígono / Parcela</th><td>{{ datos.localizacion.poligono }} / {{ datos.localizacion.parcela }}</td></tr>
      <tr><th>Referencia catastral</th><td>{{ datos.localizacion.referencia_catastral }}</td></tr>

      <tr><th>UTM X</th><td>{{ datos.coordenadas.utm.x }}</td></tr>
      <tr><th>UTM Y</th><td>{{ datos.coordenadas.utm.y }}</td></tr>
      <tr><th>Huso</th><td>{{ datos.coordenadas.utm.huso }}</td></tr>
      <tr><th>Datum</th><td>{{ datos.coordenadas.utm.datum }}</td></tr>

      <tr><th>Profundidad proyectada (m)</th><td>{{ datos.parametros.profundidad_proyectada_m }}</td></tr>
      <tr><th>Ø perforación INICIAL (mm)</th><td>{{ datos.parametros.diametro_perforacion_inicial_mm }}</td></tr>
      <tr><th>Ø perforación DEFINITIVO / entubación (mm)</th><td>{{ datos.parametros.diametro_perforacion_definitivo_mm }}</td></tr>
      <tr><th>Ø tubería de impulsión (mm)</th><td>{{ datos.parametros.diametro_tuberia_impulsion_mm }}</td></tr>

      <tr><th>Caudal máx. instantáneo (L/s)</th><td>{{ datos.parametros.caudal_max_instantaneo_l_s }}</td></tr>
      <tr><th>Caudal mínimo (L/s)</th><td>{{ datos.parametros.caudal_minimo_l_s }}</td></tr>
      <tr><th>Potencia bomba (kW)</th><td>{{ datos.parametros.potencia_bombeo_kw }}</td></tr>

      <tr><th>Uso previsto</th><td>{{ (datos.parametros.uso_previsto or '') }}</td></tr>
      <tr><th>Detalles de uso</th><td>{{ (datos.parametros.detalles_de_uso or '') }}</td></tr>
    </table>
  </div>

  <div class="card">
    <h2>2) Introducción y antecedentes (literal)</h2>
    <pre>{{ literal_blocks.introduccion_antecedentes }}</pre>
  </div>

  <div class="card">
    <h2>3) Situación del sondeo (literal)</h2>
    <pre>{{ literal_blocks.situacion_sondeo }}</pre>
  </div>

  <div class="card">
    <h2>4) Geología e Hidrogeología (literal)</h2>
    <pre>{{ literal_blocks.geologia_hidro }}</pre>
  </div>

  <p style="color:#777;font-size:12px;">Informe generado automáticamente a partir del PROYECTO PDF (regex + IA mínima).</p>
</body>
</html>
""")
    return tpl.render(datos=datos, literal_blocks=literal_blocks)
