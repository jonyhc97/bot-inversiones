"""
Genera el panel web (docs/index.html) con el estado de las 3 carteras.
Se puede abrir con doble clic en tu Mac o publicarse con GitHub Pages.
"""
import html
import json
import os

import configuracion as cfg
from cartera import BASE, Cartera, ahora_texto

TITULOS = {"acciones": "Acciones", "cripto": "Criptomonedas", "polymarket": "Polymarket"}
CONFS = {"acciones": cfg.ACCIONES, "cripto": cfg.CRIPTO, "polymarket": cfg.POLYMARKET}


def _e(x):
    return html.escape(str(x))


def _cambio(pct):
    if pct > 0.005:
        return f'<span class="sube">▲ {pct:+.2f}%</span>'
    if pct < -0.005:
        return f'<span class="baja">▼ {pct:+.2f}%</span>'
    return f'<span class="igual">● {pct:+.2f}%</span>'


def _seccion(nombre):
    conf = CONFS[nombre]
    c = Cartera(nombre, conf["capital_inicial"], conf["comision"])
    hist = [{"f": h["fecha"], "v": float(h["total_usd"])} for h in c.historial()]
    cerradas, ganadas, neto = c.resumen_cerradas()
    tasa = f"{ganadas / cerradas * 100:.0f}%" if cerradas else "—"

    filas_pos = ""
    for p in sorted(c.posiciones.values(), key=lambda p: -p["cantidad"] * p["precio_actual"]):
        valor = p["cantidad"] * p["precio_actual"]
        r = (p["precio_actual"] / p["precio_entrada"] - 1) * 100
        filas_pos += (f"<tr><td class='nom' title='{_e(p['nombre'])}'>{_e(p['nombre'])}</td>"
                      f"<td>{_e(p['lado'])}</td><td class='n'>{p['precio_entrada']:.4g}</td>"
                      f"<td class='n'>{p['precio_actual']:.4g}</td><td class='n'>{valor:,.2f}</td>"
                      f"<td class='n'>{_cambio(r)}</td></tr>")
    if not filas_pos:
        filas_pos = "<tr><td colspan='6' class='vacio'>Sin posiciones abiertas (todo en efectivo)</td></tr>"

    filas_ops = ""
    for o in list(reversed(c.operaciones()))[:12]:
        g = float(o["ganancia_usd"])
        res = _cambio(g / max(float(o["monto_usd"]) - g, 0.01) * 100) if o["accion"] == "VENTA" else ""
        filas_ops += (f"<tr><td>{_e(o['fecha'])}</td><td>{_e(o['accion'])}</td>"
                      f"<td class='nom' title='{_e(o['nombre'])}'>{_e(o['nombre'])}</td>"
                      f"<td class='n'>{float(o['monto_usd']):,.2f}</td><td class='n'>{res}</td>"
                      f"<td class='razon'>{_e(o['razon'])}</td></tr>")
    if not filas_ops:
        filas_ops = "<tr><td colspan='6' class='vacio'>Todavia no hay operaciones</td></tr>"

    resumen = {"total": c.valor_total(), "inicial": c.capital_inicial, "rend": c.rendimiento()}
    bloque = f"""
<section>
  <h2>{TITULOS[nombre]}</h2>
  <div class="tiles">
    <div class="tile"><div class="et">Valor total</div><div class="big">{c.valor_total():,.2f} <small>USD</small></div><div>{_cambio(c.rendimiento())} desde {c.capital_inicial:,.0f} USD</div></div>
    <div class="tile"><div class="et">Efectivo</div><div class="big">{c.efectivo:,.2f}</div><div class="sec">{len(c.posiciones)} posiciones abiertas</div></div>
    <div class="tile"><div class="et">Operaciones cerradas</div><div class="big">{cerradas}</div><div class="sec">ganadoras: {tasa} · resultado {neto:+,.2f} USD</div></div>
  </div>
  <figure class="graf" data-serie='{_e(json.dumps(hist))}' data-base="{c.capital_inicial}">
    <figcaption>Valor de la cartera (USD) · línea punteada = capital inicial</figcaption>
    <svg></svg><div class="tip" hidden></div>
  </figure>
  <h3>Posiciones abiertas</h3>
  <div class="tabla"><table><thead><tr><th>Nombre</th><th>Lado</th><th class='n'>Entrada</th><th class='n'>Actual</th><th class='n'>Valor USD</th><th class='n'>Resultado</th></tr></thead><tbody>{filas_pos}</tbody></table></div>
  <h3>Últimas operaciones</h3>
  <div class="tabla"><table><thead><tr><th>Fecha</th><th>Acción</th><th>Nombre</th><th class='n'>Monto</th><th class='n'>Resultado</th><th>Razón</th></tr></thead><tbody>{filas_ops}</tbody></table></div>
</section>"""
    return bloque, resumen


PLANTILLA = """<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bot de inversiones · simulación</title>
<style>
:root{--fondo:#fcfcfb;--tarjeta:#ffffff;--borde:#e6e5e0;--t1:#0b0b0b;--t2:#52514e;--serie:#2a78d6;--rejilla:#ecebe7;--sube:#0a7d0a;--baja:#c03030}
@media (prefers-color-scheme:dark){:root{--fondo:#1a1a19;--tarjeta:#222220;--borde:#383835;--t1:#f0efec;--t2:#c3c2b7;--serie:#3987e5;--rejilla:#2e2e2b;--sube:#0ca30c;--baja:#e66767}}
*{box-sizing:border-box}body{margin:0;font:15px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:var(--fondo);color:var(--t1)}
main{max-width:1000px;margin:auto;padding:20px 16px 60px}
h1{font-size:22px;margin:0 0 4px}h2{font-size:19px;margin:36px 0 12px;padding-top:16px;border-top:1px solid var(--borde)}h3{font-size:15px;margin:20px 0 8px;color:var(--t2)}
.aviso{color:var(--t2);font-size:13px;margin:0 0 16px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px}
.tile{background:var(--tarjeta);border:1px solid var(--borde);border-radius:10px;padding:12px 14px}
.et{font-size:12px;color:var(--t2);text-transform:uppercase;letter-spacing:.04em}.big{font-size:24px;font-weight:600;font-variant-numeric:tabular-nums}.big small{font-size:13px;color:var(--t2);font-weight:400}.sec{color:var(--t2);font-size:13px}
.sube{color:var(--sube);font-weight:600}.baja{color:var(--baja);font-weight:600}.igual{color:var(--t2)}
.graf{position:relative;margin:14px 0 0;background:var(--tarjeta);border:1px solid var(--borde);border-radius:10px;padding:10px}
.graf figcaption{font-size:12px;color:var(--t2);margin-bottom:4px}.graf svg{width:100%;height:220px;display:block}
.tip{position:absolute;pointer-events:none;background:var(--t1);color:var(--fondo);font-size:12px;padding:4px 8px;border-radius:6px;white-space:nowrap}
.tabla{overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:13px}th,td{padding:6px 8px;border-bottom:1px solid var(--borde);text-align:left;vertical-align:top}th{color:var(--t2);font-weight:500}
.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}.nom{max-width:320px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.razon{color:var(--t2);min-width:220px}.vacio{color:var(--t2);text-align:center;padding:14px}
</style></head><body><main>
<h1>Bot de inversiones</h1>
<p class="aviso">MODO SIMULACIÓN · dinero ficticio · actualizado: __FECHA__</p>
<div class="tiles">__GLOBAL__</div>
__SECCIONES__
</main>
<script>
document.querySelectorAll('.graf').forEach(function(fig){
  var datos=JSON.parse(fig.dataset.serie||'[]'),base=+fig.dataset.base,svg=fig.querySelector('svg'),tip=fig.querySelector('.tip');
  var W=svg.clientWidth||600,H=220,ml=52,mr=10,mt=8,mb=24,NS='http://www.w3.org/2000/svg';
  svg.setAttribute('viewBox','0 0 '+W+' '+H);
  function el(n,a){var e=document.createElementNS(NS,n);for(var k in a)e.setAttribute(k,a[k]);svg.appendChild(e);return e}
  if(datos.length<2){el('text',{x:W/2,y:H/2,'text-anchor':'middle',fill:'var(--t2)','font-size':13}).textContent='La gráfica aparece después de 2 ciclos';return}
  var vs=datos.map(function(d){return d.v}).concat([base]),mn=Math.min.apply(0,vs),mx=Math.max.apply(0,vs),pad=(mx-mn)*0.1||1;mn-=pad;mx+=pad;
  var X=function(i){return ml+i*(W-ml-mr)/(datos.length-1)},Y=function(v){return mt+(mx-v)*(H-mt-mb)/(mx-mn)};
  for(var k=0;k<=4;k++){var v=mn+(mx-mn)*k/4;el('line',{x1:ml,x2:W-mr,y1:Y(v),y2:Y(v),stroke:'var(--rejilla)','stroke-width':1});el('text',{x:ml-6,y:Y(v)+4,'text-anchor':'end',fill:'var(--t2)','font-size':11}).textContent=v.toFixed(0)}
  el('line',{x1:ml,x2:W-mr,y1:Y(base),y2:Y(base),stroke:'var(--t2)','stroke-dasharray':'4 4','stroke-width':1});
  el('text',{x:ml,y:H-6,fill:'var(--t2)','font-size':11}).textContent=datos[0].f.slice(0,10);
  el('text',{x:W-mr,y:H-6,'text-anchor':'end',fill:'var(--t2)','font-size':11}).textContent=datos[datos.length-1].f.slice(0,10);
  el('path',{d:datos.map(function(d,i){return(i?'L':'M')+X(i)+' '+Y(d.v)}).join(''),fill:'none',stroke:'var(--serie)','stroke-width':2,'stroke-linejoin':'round'});
  var guia=el('line',{y1:mt,y2:H-mb,stroke:'var(--t2)','stroke-width':1,visibility:'hidden'}),pt=el('circle',{r:4,fill:'var(--serie)',stroke:'var(--tarjeta)','stroke-width':2,visibility:'hidden'});
  svg.addEventListener('pointermove',function(ev){var r=svg.getBoundingClientRect(),x=(ev.clientX-r.left)*W/r.width,i=Math.round((x-ml)/(W-ml-mr)*(datos.length-1));i=Math.max(0,Math.min(datos.length-1,i));var d=datos[i];
    guia.setAttribute('x1',X(i));guia.setAttribute('x2',X(i));guia.setAttribute('visibility','visible');pt.setAttribute('cx',X(i));pt.setAttribute('cy',Y(d.v));pt.setAttribute('visibility','visible');
    tip.hidden=false;tip.textContent=d.f+' · '+d.v.toLocaleString('es-MX',{minimumFractionDigits:2,maximumFractionDigits:2})+' USD';var px=X(i)*r.width/W;tip.style.left=Math.min(px+14,r.width-tip.offsetWidth)+'px';tip.style.top='28px'});
  svg.addEventListener('pointerleave',function(){tip.hidden=true;guia.setAttribute('visibility','hidden');pt.setAttribute('visibility','hidden')});
});
</script></body></html>"""


def generar():
    secciones, total, inicial = "", 0.0, 0.0
    for nombre in ("acciones", "cripto", "polymarket"):
        if not CONFS[nombre]["activo"]:
            continue
        bloque, r = _seccion(nombre)
        secciones += bloque
        total += r["total"]
        inicial += r["inicial"]
    rend = (total / inicial - 1) * 100 if inicial else 0
    glob = (f'<div class="tile"><div class="et">Total de las 3 carteras</div>'
            f'<div class="big">{total:,.2f} <small>USD</small></div>'
            f'<div>{_cambio(rend)} desde {inicial:,.0f} USD</div></div>')
    pagina = (PLANTILLA.replace("__FECHA__", ahora_texto())
              .replace("__GLOBAL__", glob).replace("__SECCIONES__", secciones))
    carpeta = os.path.join(BASE, cfg.CARPETA_PANEL)
    os.makedirs(carpeta, exist_ok=True)
    ruta = os.path.join(carpeta, "index.html")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(pagina)
    return ruta
