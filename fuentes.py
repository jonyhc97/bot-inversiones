"""
Descarga de precios publicos. Solo lectura, sin llaves ni librerias externas.

- Acciones:  Yahoo Finance (respaldo: Stooq)
- Cripto:    Coinbase Exchange
- Polymarket: API Gamma
Cada vela es un dict: {"fecha": date, "cierre": float}
"""
import csv
import io
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

CABECERAS = {"User-Agent": "Mozilla/5.0 (BotInversionesSimulador/1.0)"}


def _descargar(url, intentos=3):
    ultimo_error = None
    for i in range(intentos):
        try:
            req = urllib.request.Request(url, headers=CABECERAS)
            with urllib.request.urlopen(req, timeout=25) as r:
                return r.read().decode("utf-8")
        except Exception as e:  # red, 429, 5xx...
            ultimo_error = e
            time.sleep(2 * (i + 1))
    raise ultimo_error


def _json(url):
    return json.loads(_descargar(url))


# ---------------------------------------------------------------------
# ACCIONES
# ---------------------------------------------------------------------
def _velas_yahoo(simbolo, dias):
    rango = "5y" if dias > 500 else ("2y" if dias > 250 else "1y")
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/"
           f"{urllib.parse.quote(simbolo)}?range={rango}&interval=1d")
    datos = _json(url)["chart"]["result"][0]
    tiempos = datos["timestamp"]
    cierres = datos["indicators"]["quote"][0]["close"]
    velas = []
    for t, c in zip(tiempos, cierres):
        if c is not None:
            velas.append({"fecha": datetime.fromtimestamp(t, timezone.utc).date(),
                          "cierre": float(c)})
    return velas


def _velas_stooq(simbolo, dias):
    url = f"https://stooq.com/q/d/l/?s={simbolo.lower()}.us&i=d"
    texto = _descargar(url)
    velas = []
    for fila in csv.DictReader(io.StringIO(texto)):
        try:
            velas.append({"fecha": datetime.strptime(fila["Date"], "%Y-%m-%d").date(),
                          "cierre": float(fila["Close"])})
        except (KeyError, ValueError):
            continue
    return velas


def velas_accion(simbolo, dias=400):
    for fuente in (_velas_yahoo, _velas_stooq):
        try:
            velas = fuente(simbolo, dias)
            if len(velas) > 10:
                return velas[-dias:]
        except Exception:
            continue
    raise RuntimeError(f"No pude descargar precios de {simbolo}")


# ---------------------------------------------------------------------
# CRIPTO (Coinbase: maximo 300 velas por consulta, de la mas nueva a la vieja)
# ---------------------------------------------------------------------
def velas_cripto(par, dias=400):
    fin = datetime.now(timezone.utc)
    todas = {}
    while len(todas) < dias:
        inicio = fin - timedelta(days=300)
        url = (f"https://api.exchange.coinbase.com/products/{par}/candles"
               f"?granularity=86400&start={inicio.strftime('%Y-%m-%dT%H:%M:%SZ')}"
               f"&end={fin.strftime('%Y-%m-%dT%H:%M:%SZ')}")
        lote = _json(url)
        if not isinstance(lote, list) or not lote:
            break
        for t, _bajo, _alto, _apertura, cierre, _vol in lote:
            todas[datetime.fromtimestamp(t, timezone.utc).date()] = float(cierre)
        fin = inicio
        time.sleep(0.4)
    if len(todas) < 10:
        raise RuntimeError(f"No pude descargar precios de {par}")
    return [{"fecha": f, "cierre": todas[f]} for f in sorted(todas)][-dias:]


# ---------------------------------------------------------------------
# POLYMARKET
# ---------------------------------------------------------------------
GAMMA = "https://gamma-api.polymarket.com"


def _lista(v):
    if isinstance(v, list):
        return v
    try:
        return json.loads(v or "[]")
    except (ValueError, TypeError):
        return []


def _num(v, defecto=0.0):
    if v is None or v == "":
        return defecto
    try:
        return float(v)
    except (ValueError, TypeError):
        return defecto


def leer_fecha(texto):
    if not texto:
        return None
    texto = re.sub(r"\.\d+", "", str(texto).strip().replace("Z", "+00:00"))
    try:
        f = datetime.fromisoformat(texto)
    except ValueError:
        return None
    return f if f.tzinfo else f.replace(tzinfo=timezone.utc)


def _normalizar_mercado(m):
    resultados = [str(r).strip().lower() for r in _lista(m.get("outcomes"))]
    precios = [_num(p) for p in _lista(m.get("outcomePrices"))]
    if resultados != ["yes", "no"] or len(precios) != 2:
        return None
    p_yes = precios[0]
    bid, ask = _num(m.get("bestBid"), None), _num(m.get("bestAsk"), None)
    if bid is not None and ask is not None and ask >= bid > 0:
        spread = ask - bid
    else:
        bid = ask = p_yes
        spread = None
    return {
        "id": str(m.get("id", "")),
        "pregunta": m.get("question", "") or "",
        "p_yes": p_yes, "bid": bid, "ask": ask, "spread": spread,
        "cambio_1d": _num(m.get("oneDayPriceChange"), None),
        "cambio_1s": _num(m.get("oneWeekPriceChange"), None),
        "liquidez": _num(m.get("liquidityNum", m.get("liquidity"))),
        "volumen_24h": _num(m.get("volume24hr")),
        "fecha_fin": leer_fecha(m.get("endDate")),
        "cerrado": bool(m.get("closed")) or not bool(m.get("active", True)),
        "acepta_ordenes": m.get("acceptingOrders", True) is not False,
    }


def mercados_polymarket(paginas=5, por_pagina=100):
    encontrados = {}
    for pagina in range(paginas):
        params = {"active": "true", "closed": "false", "limit": por_pagina,
                  "offset": pagina * por_pagina,
                  "order": "volume24hr", "ascending": "false"}
        datos = _json(f"{GAMMA}/markets?{urllib.parse.urlencode(params)}")
        if not isinstance(datos, list):
            raise ValueError("Respuesta inesperada de Polymarket")
        for crudo in datos:
            m = _normalizar_mercado(crudo)
            if m and m["id"]:
                encontrados[m["id"]] = m
        if len(datos) < por_pagina:
            break
        time.sleep(0.5)
    return encontrados


def mercado_polymarket(identificador):
    try:
        return _normalizar_mercado(_json(f"{GAMMA}/markets/{identificador}"))
    except Exception:
        return None
