"""
Estrategias del bot.

1) TENDENCIA (acciones y cripto)
   Compra cuando el precio esta en tendencia de subida:
     - promedio de 20 dias por encima del de 50 dias
     - precio por encima del promedio de 20 dias
     - RSI entre 50 y 75 (con fuerza, pero sin estar "sobrecalentado")
   Vende cuando la tendencia se rompe (precio debajo del promedio de 50
   o el de 20 cruza por debajo del de 50), o por stop loss.

2) POLYMARKET
   Sigue la tendencia de la probabilidad, con limite de apuestas por tema.

Son reglas para APRENDER y medir en simulacion. Ninguna estrategia
garantiza ganancias.
"""
import math

import configuracion as cfg


# =====================================================================
# Indicadores
# =====================================================================
def promedio(valores, n):
    if len(valores) < n:
        return None
    return sum(valores[-n:]) / n


def rsi(valores, n=14):
    if len(valores) < n + 1:
        return None
    subidas = bajadas = 0.0
    for a, b in zip(valores[-n - 1:-1], valores[-n:]):
        cambio = b - a
        if cambio > 0:
            subidas += cambio
        else:
            bajadas -= cambio
    if bajadas == 0:
        return 100.0
    rs = (subidas / n) / (bajadas / n)
    return 100 - 100 / (1 + rs)


def analizar_tendencia(cierres, t=cfg.TENDENCIA):
    """Analiza una lista de precios de cierre (del mas viejo al mas nuevo)."""
    corta = promedio(cierres, t["media_corta"])
    larga = promedio(cierres, t["media_larga"])
    fuerza = rsi(cierres, t["rsi_dias"])
    if corta is None or larga is None or fuerza is None:
        return None
    precio = cierres[-1]
    compra = (corta > larga and precio > corta
              and t["rsi_min_compra"] <= fuerza <= t["rsi_max_compra"])
    rota = precio < larga * (1 - t.get("margen_salida", 0)) or (
        t.get("vender_si_cruce", True) and corta < larga)
    ref = cierres[-64] if len(cierres) >= 64 else cierres[0]
    return {"precio": precio, "media_corta": corta, "media_larga": larga,
            "rsi": fuerza, "compra": compra, "tendencia_rota": rota,
            "puntaje": precio / ref - 1}  # subida de ~3 meses


def razon_venta_tendencia(pos, analisis, precio_venta, t=cfg.TENDENCIA):
    if precio_venta <= pos["precio_entrada"] * (1 - t["stop_loss"]):
        return f"STOP LOSS ({(precio_venta / pos['precio_entrada'] - 1) * 100:+.1f}%)"
    if precio_venta <= pos.get("precio_max", pos["precio_entrada"]) * (1 - t["stop_dinamico"]):
        return f"STOP DINAMICO (cayo {t['stop_dinamico'] * 100:.0f}% desde su maximo)"
    if analisis and analisis["tendencia_rota"]:
        return "SE ROMPIO LA TENDENCIA"
    return None


def mercado_favorable(cierres_ref, t=cfg.TENDENCIA):
    """True si el indice de referencia esta arriba de su promedio largo."""
    if not t.get("filtro_mercado"):
        return True
    media = promedio(cierres_ref, t["media_mercado"])
    return media is None or cierres_ref[-1] > media


def indice_decision(cierres, invertido, i=cfg.INDICE):
    """Regresa 'COMPRAR', 'VENDER' o None para la estrategia de indice."""
    media = promedio(cierres, i["media"])
    if media is None:
        return None
    precio = cierres[-1]
    if not invertido and precio > media:
        return "COMPRAR"
    if invertido and precio < media * (1 - i["margen_salida"]):
        return "VENDER"
    return None


def variante(nombre):
    t = dict(cfg.TENDENCIA)
    t.update(cfg.VARIANTES[nombre])
    return t


def texto_compra(a, t=cfg.TENDENCIA):
    return (f"Tendencia al alza: precio {a['precio']:.4g} > prom.{t['media_corta']} "
            f"{a['media_corta']:.4g} > prom.{t['media_larga']} {a['media_larga']:.4g}, "
            f"RSI {a['rsi']:.0f}")


# =====================================================================
# Polymarket
# =====================================================================
def tema(pregunta):
    texto = f" {pregunta.lower()} "
    for palabra, nombre in cfg.TEMAS_POLYMARKET.items():
        if palabra in texto:
            return nombre
    return None  # sin tema conocido: no cuenta para el limite


def pm_precio_compra(m, lado):
    return m["ask"] if lado == "YES" else 1 - m["bid"]


def pm_precio_venta(m, lado):
    return m["bid"] if lado == "YES" else 1 - m["ask"]


def pm_dias(m, ahora):
    return None if not m["fecha_fin"] else (m["fecha_fin"] - ahora).total_seconds() / 86400


def pm_oportunidades(mercados, ahora, p=cfg.POLYMARKET):
    ops = []
    for m in mercados.values():
        if m["cerrado"] or not m["acepta_ordenes"]:
            continue
        if m["spread"] is None or m["spread"] > p["max_spread"]:
            continue
        if m["liquidez"] < p["min_liquidez"] or m["volumen_24h"] < p["min_volumen_24h"]:
            continue
        dias = pm_dias(m, ahora)
        if dias is None or not (p["dias_min"] <= dias <= p["dias_max"]):
            continue
        c1, c7 = m["cambio_1d"], m["cambio_1s"]
        if c1 is None or c7 is None:
            continue
        if c1 >= p["umbral_dia"] and c7 >= p["umbral_semana"]:
            lado = "YES"
        elif c1 <= -p["umbral_dia"] and c7 <= -p["umbral_semana"]:
            lado = "NO"
        else:
            continue
        precio = pm_precio_compra(m, lado)
        if not (p["precio_min"] <= precio <= p["precio_max"]):
            continue
        ops.append({
            "mercado": m, "lado": lado, "precio": precio, "tema": tema(m["pregunta"]),
            "puntaje": (abs(c1) + abs(c7) / 2) * math.log10(max(m["liquidez"], 10)),
            "razon": (f"Probabilidad {'subiendo' if lado == 'YES' else 'bajando'}: "
                      f"{c1 * 100:+.1f} pts en 24h, {c7 * 100:+.1f} pts en 7 dias"),
        })
    ops.sort(key=lambda o: o["puntaje"], reverse=True)
    return ops


def pm_razon_venta(pos, m, ahora, p=cfg.POLYMARKET):
    """Regresa (razon o None, precio_actual)."""
    lado = pos["lado"]
    resuelto = m["cerrado"] and (m["p_yes"] >= 0.99 or m["p_yes"] <= 0.01)
    valor_final = m["p_yes"] if lado == "YES" else 1 - m["p_yes"]
    if resuelto:
        return "MERCADO RESUELTO", valor_final
    if m["cerrado"]:
        return None, valor_final  # esperando resultado oficial
    precio = pm_precio_venta(m, lado)
    rend = precio / pos["precio_entrada"] - 1
    if rend >= p["toma_ganancia"]:
        return f"TOMA DE GANANCIA ({rend * 100:+.1f}%)", precio
    if rend <= -p["stop_loss"]:
        return f"STOP LOSS ({rend * 100:+.1f}%)", precio
    dias = pm_dias(m, ahora)
    if dias is not None and dias < p["cerrar_si_faltan_dias"]:
        return "VENCE PRONTO", precio
    c1 = m["cambio_1d"]
    if c1 is not None and ((lado == "YES" and c1 <= -p["umbral_dia"])
                           or (lado == "NO" and c1 >= p["umbral_dia"])):
        return "CAMBIO DE TENDENCIA", precio
    return None, precio
