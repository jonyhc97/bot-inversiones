"""
PRUEBA CON EL PASADO (backtest)

Repite la estrategia de tendencia dia por dia sobre los precios reales
de los ultimos ~3 anos, como si el bot hubiera estado corriendo, y la
compara contra simplemente comprar y aguantar.

Ademas prueba varias VERSIONES de las reglas (configuracion.VARIANTES)
sobre exactamente los mismos dias, para ver cual se porta mejor.
"""
import time

import configuracion as cfg
import estrategias as est
import fuentes

DIAS_HISTORIA = 800      # ~3 anos de acciones, ~2 anos de cripto
DIAS_PREPARACION = 210   # dias que se usan solo para calcular promedios


def _caida_maxima(valores):
    pico, peor = valores[0], 0.0
    for v in valores:
        pico = max(pico, v)
        peor = min(peor, v / pico - 1)
    return peor * 100


def descargar_todo(conf, descargar):
    precios = {}
    for s in dict.fromkeys(conf["simbolos"] + [conf["referencia"]]):
        try:
            precios[s] = {v["fecha"]: v["cierre"] for v in descargar(s, DIAS_HISTORIA)}
        except Exception as e:
            print(f"  (sin datos de {s}: {e})")
        time.sleep(0.3)
    return precios


def simular(conf, precios, t):
    """Corre una version de las reglas sobre los precios ya descargados."""
    simbolos = [s for s in conf["simbolos"] if s in precios]
    ref = conf["referencia"]
    fechas = sorted(set().union(*[set(precios[s]) for s in simbolos]))
    if len(fechas) <= DIAS_PREPARACION + 20:
        return None

    capital = conf["capital_inicial"]
    com, desl = conf["comision"], conf["deslizamiento"]
    efectivo, posiciones, valores, ops = capital, {}, [], []
    historia = {s: [] for s in simbolos}
    hist_ref = []

    for i, fecha in enumerate(fechas):
        for s in simbolos:
            if fecha in precios[s]:
                historia[s].append(precios[s][fecha])
        if fecha in precios.get(ref, {}):
            hist_ref.append(precios[ref][fecha])
        if i < DIAS_PREPARACION:
            continue

        analisis = {s: est.analizar_tendencia(historia[s], t) for s in simbolos if historia[s]}

        # ventas
        for s in list(posiciones):
            a = analisis.get(s)
            if not a:
                continue
            p = posiciones[s]
            pv = a["precio"] * (1 - desl)
            p["precio_max"] = max(p["precio_max"], pv)
            if est.razon_venta_tendencia(p, a, pv, t):
                neto = p["cantidad"] * pv * (1 - com)
                ops.append(neto - p["costo"])
                efectivo += neto
                del posiciones[s]

        # compras (solo si el mercado en general va bien)
        if not hist_ref or est.mercado_favorable(hist_ref, t):
            total = efectivo + sum(p["cantidad"] * historia[s][-1] for s, p in posiciones.items())
            candidatos = sorted(((s, a) for s, a in analisis.items()
                                 if a and a["compra"] and s not in posiciones),
                                key=lambda x: x[1]["puntaje"], reverse=True)
            for s, a in candidatos:
                if len(posiciones) >= t["max_posiciones"]:
                    break
                monto = min(total * t["porcentaje_por_posicion"],
                            efectivo - total * t["reserva_efectivo"])
                if monto < 1:
                    break
                pc = a["precio"] * (1 + desl)
                posiciones[s] = {"cantidad": monto * (1 - com) / pc, "precio_entrada": pc,
                                 "precio_max": pc, "costo": monto}
                efectivo -= monto

        valores.append(efectivo + sum(p["cantidad"] * historia[s][-1]
                                      for s, p in posiciones.items()))

    fechas_prueba = fechas[DIAS_PREPARACION:]
    return {"desde": fechas_prueba[0], "hasta": fechas_prueba[-1],
            "final": valores[-1], "rendimiento": (valores[-1] / capital - 1) * 100,
            "caida": _caida_maxima(valores), "operaciones": len(ops),
            "ganadas": sum(1 for g in ops if g > 0), "fechas": fechas_prueba}


def simular_indice(conf, precios, fechas_todas):
    """Comprar el indice de referencia y salirse cuando cae debajo de su promedio."""
    i, ref = cfg.INDICE, conf["referencia"]
    if ref not in precios:
        return None
    com, desl = conf["comision"], conf["deslizamiento"]
    efectivo, cantidad, costo = conf["capital_inicial"], 0.0, 0.0
    hist, valores, ops = [], [], []
    for n, fecha in enumerate(fechas_todas):
        if fecha in precios[ref]:
            hist.append(precios[ref][fecha])
        if n < DIAS_PREPARACION or not hist:
            continue
        d = est.indice_decision(hist, cantidad > 0)
        if d == "VENDER":
            neto = cantidad * hist[-1] * (1 - desl) * (1 - com)
            ops.append(neto - costo)
            efectivo, cantidad = efectivo + neto, 0.0
        elif d == "COMPRAR":
            costo = (efectivo + 0) * i["porcentaje_invertido"]
            cantidad = costo * (1 - com) / (hist[-1] * (1 + desl))
            efectivo -= costo
        valores.append(efectivo + cantidad * hist[-1])
    if not valores:
        return None
    capital = conf["capital_inicial"]
    return {"final": valores[-1], "rendimiento": (valores[-1] / capital - 1) * 100,
            "caida": _caida_maxima(valores), "operaciones": len(ops),
            "ganadas": sum(1 for g in ops if g > 0)}


def comprar_y_aguantar(precios, simbolos, fechas):
    def serie(s):
        return [precios[s][f] for f in fechas if f in precios[s]]
    rends, caidas = [], []
    for s in simbolos:
        v = serie(s)
        if len(v) > 1:
            rends.append(v[-1] / v[0] - 1)
            caidas.append(_caida_maxima(v))
    return rends, caidas


def probar_mercado(nombre, conf, descargar):
    print(f"\nPRUEBA CON EL PASADO: {nombre.upper()} (descargando precios...)")
    precios = descargar_todo(conf, descargar)
    simbolos = [s for s in conf["simbolos"] if s in precios]
    if not simbolos:
        print("  No hubo datos.")
        return

    resultados = {}
    for nombre_var in cfg.VARIANTES:
        r = simular(conf, precios, est.variante(nombre_var))
        if r:
            resultados[nombre_var] = r
    if not resultados:
        print("  No hubo suficientes dias para la prueba.")
        return

    cualquiera = next(iter(resultados.values()))
    fechas = cualquiera["fechas"]
    print(f"  Periodo: {cualquiera['desde']} a {cualquiera['hasta']}  "
          f"(capital {conf['capital_inicial']:.0f} USD)\n")
    print(f"  {'Version':<36}{'Resultado':>11}{'Peor caida':>12}{'Operac.':>9}{'Ganadoras':>11}")
    print("  " + "-" * 79)
    for nombre_var, r in resultados.items():
        tasa = f"{r['ganadas'] / r['operaciones'] * 100:.0f}%" if r["operaciones"] else "-"
        print(f"  {nombre_var:<36}{r['rendimiento']:>+10.1f}%{r['caida']:>11.1f}%"
              f"{r['operaciones']:>9}{tasa:>11}")

    ref = conf["referencia"]
    fechas_todas = sorted(set().union(*[set(precios[s]) for s in simbolos]))
    r = simular_indice(conf, precios, fechas_todas)
    if r:
        tasa = f"{r['ganadas'] / r['operaciones'] * 100:.0f}%" if r["operaciones"] else "-"
        print(f"  {ref + ' + salir en caidas (NUEVA)':<36}{r['rendimiento']:>+10.1f}%{r['caida']:>11.1f}%"
              f"{r['operaciones']:>9}{tasa:>11}")
    if ref in precios:
        rr, cr = comprar_y_aguantar(precios, [ref], fechas)
        if rr:
            print(f"  {'Solo comprar ' + ref + ' y aguantar':<36}{rr[0] * 100:>+10.1f}%{cr[0]:>11.1f}%")
    rends, caidas = comprar_y_aguantar(precios, simbolos, fechas)
    if rends:
        print(f"  {'Comprar todos y aguantar':<36}{sum(rends) / len(rends) * 100:>+10.1f}%"
              f"{sum(caidas) / len(caidas):>11.1f}%  (promedio)")
    print("\n  'Peor caida' = lo maximo que llego a bajar desde un punto alto.")


def correr():
    probar_mercado("acciones", cfg.ACCIONES, fuentes.velas_accion)
    probar_mercado("cripto", cfg.CRIPTO, fuentes.velas_cripto)
    print("\nPolymarket no se puede probar asi: los mercados viejos ya cerraron.")
    print("Recuerda: que haya funcionado en el pasado no garantiza el futuro.")
