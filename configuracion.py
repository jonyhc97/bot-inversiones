"""
CONFIGURACION DEL BOT DE INVERSIONES (MODO SIMULACION)

Todo el dinero es FICTICIO. El bot solo lee precios publicos; no tiene
codigo para conectarse a ningun broker ni para operar con dinero real.
Cambia aqui lo que quieras probar.
"""

# =====================================================================
# ACCIONES (bolsa de EE.UU.)
# =====================================================================
ACCIONES = {
    "activo": True,
    # "tendencia": compra/vende acciones individuales (estrategia de abajo)
    # "indice":    compra SPY y se sale a efectivo cuando la bolsa va en caida
    "estrategia": "indice",
    "capital_inicial": 1000.0,
    "simbolos": ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA",
                 "JPM", "V", "KO", "WMT", "COST", "AMD", "NFLX"],
    "referencia": "SPY",          # indice para comparar (S&P 500)
    "comision": 0.0,              # la mayoria de brokers ya no cobra
    "deslizamiento": 0.001,       # 0.1% de diferencia al comprar/vender
}

# =====================================================================
# CRIPTOMONEDAS (precios de Coinbase)
# =====================================================================
CRIPTO = {
    "activo": True,
    # "indice": compra BTC y se sale a efectivo cuando va en caida
    # "tendencia": compra/vende varias criptos con la estrategia de tendencia
    "estrategia": "indice",
    "capital_inicial": 1000.0,
    "simbolos": ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "ADA-USD",
                 "DOGE-USD", "LINK-USD", "AVAX-USD", "LTC-USD"],
    "referencia": "BTC-USD",
    "comision": 0.004,            # 0.4% por operacion
    "deslizamiento": 0.002,
}

# =====================================================================
# ESTRATEGIA DE TENDENCIA (acciones y cripto)
# =====================================================================
TENDENCIA = {
    "media_corta": 20,            # promedio de 20 dias
    "media_larga": 50,            # promedio de 50 dias
    "rsi_dias": 14,
    "rsi_min_compra": 50,         # solo comprar con fuerza...
    "rsi_max_compra": 75,         # ...pero sin estar sobrecomprado

    # --- Ajuste 1: menos nervioso ---
    "stop_loss": 0.15,            # vender si cae 15% desde la compra (antes 8%)
    "stop_dinamico": 0.20,        # vender si cae 20% desde su maximo (antes 12%)
    "margen_salida": 0.03,        # vender solo si el precio queda 3% DEBAJO del prom. 50
    "vender_si_cruce": False,     # ya no vende solo porque el prom. 20 cruce al de 50

    # --- Ajuste 2: revisar el mercado en general ---
    "filtro_mercado": True,       # comprar solo si SPY (acciones) / BTC (cripto)
    "media_mercado": 200,         # esta arriba de su promedio de 200 dias

    "max_posiciones": 5,
    "porcentaje_por_posicion": 0.18,
    "reserva_efectivo": 0.10,
}

# --- Ajuste 3: versiones que compara la prueba con el pasado (--backtest) ---
# Cada una cambia solo algunos valores de TENDENCIA.
VARIANTES = {
    "Original (version anterior)": {
        "stop_loss": 0.08, "stop_dinamico": 0.12, "margen_salida": 0.0,
        "vender_si_cruce": True, "filtro_mercado": False},
    "Menos nervioso": {"filtro_mercado": False},
    "Menos nervioso + mercado (ACTUAL)": {},
    "Lento 50/200 + mercado": {"media_corta": 50, "media_larga": 200,
                               "margen_salida": 0.02},
}

# =====================================================================
# ESTRATEGIA DE INDICE (comprar el indice y salirse en las caidas)
# =====================================================================
INDICE = {
    "media": 200,                 # promedio de 200 dias del indice
    "margen_salida": 0.02,        # salir si queda 2% debajo del promedio
    "porcentaje_invertido": 0.98, # cuanto se invierte cuando el mercado va bien
}

# =====================================================================
# POLYMARKET (apuestas sobre eventos)
# =====================================================================
POLYMARKET = {
    "activo": True,
    "capital_inicial": 1000.0,
    "comision": 0.0,
    "min_liquidez": 5000,
    "min_volumen_24h": 1000,
    "max_spread": 0.03,
    "precio_min": 0.10,
    "precio_max": 0.90,
    "dias_min": 3,                # no entrar a mercados que vencen ya
    "dias_max": 90,
    "umbral_dia": 0.03,           # 3 puntos de cambio en 24 h
    "umbral_semana": 0.05,        # 5 puntos en 7 dias
    "max_posiciones": 8,
    "max_por_tema": 2,            # NUEVO: max 2 apuestas del mismo tema
    "porcentaje_por_posicion": 0.05,  # apuestas mas chicas (antes 10%)
    "reserva_efectivo": 0.20,
    "dias_bloqueo_tema": 3,       # si pierde en un tema, no vuelve a apostar ahi en 3 dias
    "toma_ganancia": 0.25,
    "stop_loss": 0.15,
    "cerrar_si_faltan_dias": 1,
    "horas_espera_recompra": 24,
    "paginas": 5,
}

# Temas para no concentrar apuestas en lo mismo (palabra -> tema)
TEMAS_POLYMARKET = {
    # Todas las apuestas de precios cripto son el mismo tema: se mueven juntas
    "bitcoin": "Cripto", "btc": "Cripto", "ethereum": "Cripto", "eth ": "Cripto",
    "solana": "Cripto", "xrp": "Cripto", "crypto": "Cripto", "dogecoin": "Cripto",
    "elon": "Elon Musk", "musk": "Elon Musk", "tesla": "Elon Musk",
    "trump": "Trump", "fed ": "Tasas Fed", "rate cut": "Tasas Fed",
    "interest rate": "Tasas Fed",
    "democratic": "Elecciones EE.UU.", "republican": "Elecciones EE.UU.",
    "presidential": "Elecciones EE.UU.", "senate": "Elecciones EE.UU.",
    "governor": "Elecciones EE.UU.",
    "nfl": "Deportes", "nba": "Deportes", "super bowl": "Deportes",
    "premier league": "Deportes", "champions": "Deportes",
    "ukraine": "Guerra", "russia": "Guerra", "israel": "Medio Oriente",
    "iran": "Medio Oriente", "gaza": "Medio Oriente",
}

# =====================================================================
# ARCHIVOS
# =====================================================================
CARPETA_DATOS = "datos"           # carteras, operaciones e historial
CARPETA_PANEL = "docs"            # pagina web (GitHub Pages usa "docs")
