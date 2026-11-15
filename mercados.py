"""
Un ciclo de trabajo por mercado: actualizar precios, vender, comprar.
"""
import time

import configuracion as cfg
import estrategias as est
import fuentes
from cartera import Cartera, ahora


# =====================================================================
# ACCIONES Y CRIPTO (misma estrategia de tendencia)
# =====================================================================
def ciclo_tendencia(nombre, conf, descargar):
    t = cfg.TENDENCIA
    cartera = Cartera(nombre, conf["capital_inicial"], conf["comision"])
    desliz = conf["deslizamiento"]

    simbolos = list(dict.fromkeys(conf["simbolos"] + list(cartera.posiciones)))
    dias = max(t["media_larga"], t["media_mercado"]) + 70
    analisis, errores, cierres_ref = {}, [], None
    for s in simbolos + [conf["referencia"]]:
        if s in analisis:
            continue
        try:
            cierres = [v["cierre"] for v in descargar(s, dias)]
            analisis[s] = est.analizar_tendencia(cierres)
            if s == conf["referencia"]:
                cierres_ref = cierres
        except Exception as e:
            errores.append(f"{s}: {e}")
        time.sleep(0.3)
    if errores:
        cartera.mensajes.append("Sin datos para: " + "; ".join(errores))

    # 1) Revisar lo que ya tenemos
    for s in list(cartera.posiciones):
        a = analisis.get(s)
        if not a:
            continue  # sin datos hoy: se mantiene
        precio_venta = a["precio"] * (1 - desliz)
        cartera.actualizar_precio(s, precio_venta)
        razon = est.razon_venta_tendencia(cartera.posiciones[s], a, precio_venta)
        if razon:
            cartera.vender(s, precio_venta, razon)

    # 2) Buscar compras (solo si el mercado en general va bien)
    if cierres_ref and not est.mercado_favorable(cierres_ref):
        cartera.mensajes.append(f"{conf['referencia']} esta debajo de su promedio de "
                                f"{t['media_mercado']} dias: hoy no se compra nada nuevo.")
        candidatos = []
    else:
        candidatos = [(s, a) for s, a in analisis.items()
                      if s in conf["simbolos"] and a and a["compra"]
                      and s not in cartera.posiciones
                      and not cartera.recompra_bloqueada(s, 24)]
    candidatos.sort(key=lambda x: x[1]["puntaje"], reverse=True)
    for s, a in candidatos:
        if len(cartera.posiciones) >= t["max_posiciones"]:
            break
        monto = cartera.monto_para_comprar(t["porcentaje_por_posicion"], t["reserva_efectivo"])
        if monto < 1:
            break
        cartera.comprar(s, s, "COMPRA", a["precio"] * (1 + desliz), monto, est.texto_compra(a, t))

    ref = analisis.get(conf["referencia"])
    cartera.guardar()
    cartera.guardar_historial(ref["precio"] if ref else None)
    return cartera


def ciclo_indice(nombre, conf, descargar):
    i = cfg.INDICE
    cartera = Cartera(nombre, conf["capital_inicial"], conf["comision"])
    ref, desliz = conf["referencia"], conf["deslizamiento"]
    cierres = [v["cierre"] for v in descargar(ref, i["media"] + 60)]
    precio = cierres[-1]
    media = sum(cierres[-i["media"]:]) / i["media"]

    # Si quedaron acciones de la estrategia anterior, se venden primero
    for s in [s for s in cartera.posiciones if s != ref]:
        try:
            p = descargar(s, 5)[-1]["cierre"] * (1 - desliz)
            cartera.vender(s, p, "CAMBIO A ESTRATEGIA DE INDICE")
        except Exception:
            pass

    invertido = ref in cartera.posiciones
    if invertido:
        cartera.actualizar_precio(ref, precio * (1 - desliz))
    decision = est.indice_decision(cierres, invertido)
    if decision == "VENDER":
        cartera.vender(ref, precio * (1 - desliz),
                       f"{ref} cayo debajo de su promedio de {i['media']} dias")
    elif decision == "COMPRAR":
        monto = cartera.valor_total() * i["porcentaje_invertido"]
        cartera.comprar(ref, ref, "COMPRA", precio * (1 + desliz), min(monto, cartera.efectivo),
                        f"{ref} arriba de su promedio de {i['media']} dias ({precio:.2f} > {media:.2f})")
    else:
        estado = "invertido" if invertido else "en efectivo (esperando)"
        cartera.mensajes.append(f"Sin cambios: {estado}. {ref} {precio:.2f} vs promedio {media:.2f}")

    cartera.guardar()
    cartera.guardar_historial(precio)
    return cartera


def ciclo_acciones():
    if cfg.ACCIONES.get("estrategia") == "indice":
        return ciclo_indice("acciones", cfg.ACCIONES, fuentes.velas_accion)
    return ciclo_tendencia("acciones", cfg.ACCIONES, fuentes.velas_accion)


def ciclo_cripto():
    if cfg.CRIPTO.get("estrategia") == "indice":
        return ciclo_indice("cripto", cfg.CRIPTO, fuentes.velas_cripto)
    return ciclo_tendencia("cripto", cfg.CRIPTO, fuentes.velas_cripto)


# =====================================================================
# POLYMARKET
# =====================================================================
def ciclo_polymarket():
    p = cfg.POLYMARKET
    cartera = Cartera("polymarket", p["capital_inicial"], p["comision"])
    momento = ahora()
    mercados = fuentes.mercados_polymarket(p["paginas"])
    cartera.mensajes.append(f"Mercados revisados: {len(mercados)}")

    for ident in list(cartera.posiciones):
        m = mercados.get(ident) or fuentes.mercado_polymarket(ident)
        if m is None:
            continue
        razon, precio = est.pm_razon_venta(cartera.posiciones[ident], m, momento)
        cartera.actualizar_precio(ident, precio)
        if razon:
            cartera.vender(ident, precio, razon)

    por_tema = {}
    for pos in cartera.posiciones.values():
        if pos.get("tema"):
            por_tema[pos["tema"]] = por_tema.get(pos["tema"], 0) + 1

    for op in est.pm_oportunidades(mercados, momento):
        if len(cartera.posiciones) >= p["max_posiciones"]:
            break
        m = op["mercado"]
        if m["id"] in cartera.posiciones or cartera.recompra_bloqueada(m["id"], p["horas_espera_recompra"]):
            continue
        if op["tema"] and por_tema.get(op["tema"], 0) >= p["max_por_tema"]:
            continue
        monto = cartera.monto_para_comprar(p["porcentaje_por_posicion"], p["reserva_efectivo"])
        if monto < 1:
            break
        cartera.comprar(m["id"], m["pregunta"], op["lado"], op["precio"], monto,
                        op["razon"], extra={"tema": op["tema"]})
        if op["tema"]:
            por_tema[op["tema"]] = por_tema.get(op["tema"], 0) + 1

    cartera.guardar()
    cartera.guardar_historial()
    return cartera
