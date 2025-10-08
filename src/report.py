
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path

def render_report(output_dir: str, template_dir: str, context: dict) -> str:
    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape()
    )
    tpl = env.get_template("report.html")
    html = tpl.render(**context)

    outdir = Path(output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    outfile = outdir / f"reporte_{context['id']}.html"
    outfile.write_text(html, encoding="utf-8")
    return str(outfile)
