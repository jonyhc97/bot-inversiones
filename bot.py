"""
BOT DE INVERSIONES - MODO SIMULACION (dinero ficticio)

Uso:
  python3 bot.py               -> un ciclo en los 3 mercados y actualiza el panel
  python3 bot.py --backtest    -> prueba la estrategia con los precios de ~2 anos
  python3 bot.py --cada 60     -> repite cada 60 minutos (Ctrl+C para detener)
  python3 bot.py --solo cripto -> solo un mercado (acciones, cripto o polymarket)
  python3 bot.py --reiniciar   -> borra las carteras y empieza de cero
"""
import argparse
import shutil
import sys
import time
import traceback

import configuracion as cfg
import mercados
import panel
from cartera import DATOS, ahora_texto

LINEA = "=" * 66
CICLOS = {
    "acciones": (cfg.ACCIONES, mercados.ciclo_acciones),
    "cripto": (cfg.CRIPTO, mercados.ciclo_cripto),
    "polymarket": (cfg.POLYMARKET, mercados.ciclo_polymarket),
}


def mostrar(nombre, c):
    print(f"\n--- {nombre.upper()} ---")
    for m in c.mensajes:
        print("  " + m)
    print(f"  Valor total: {c.valor_total():,.2f} USD ({c.rendimiento():+.2f}%) | "
          f"efectivo {c.efectivo:,.2f} | posiciones {len(c.posiciones)}")


def ciclo(solo=None):
    print(LINEA)
    print(f"BOT DE INVERSIONES | MODO SIMULACION | {ahora_texto()}")
    print(LINEA)
    fallas = 0
    for nombre, (conf, funcion) in CICLOS.items():
        if (solo and nombre != solo) or not conf["activo"]:
            continue
        try:
            mostrar(nombre, funcion())
        except Exception as e:
            fallas += 1
            print(f"\n--- {nombre.upper()} ---\n  ERROR: {e} (se intentara en el siguiente ciclo)")
            traceback.print_exc(limit=1)
    ruta = panel.generar()
    print(f"\nPanel actualizado: {ruta}")
    print("Recordatorio: todo es simulado, no se uso dinero real.")
    return fallas


def main():
    ap = argparse.ArgumentParser(description="Bot de inversiones en modo simulacion")
    ap.add_argument("--cada", type=float, help="repetir cada N minutos")
    ap.add_argument("--solo", choices=list(CICLOS), help="correr un solo mercado")
    ap.add_argument("--backtest", action="store_true", help="probar con precios pasados")
    ap.add_argument("--reiniciar", action="store_true", help="empezar de cero")
    args = ap.parse_args()

    if args.reiniciar:
        shutil.rmtree(DATOS, ignore_errors=True)
        panel.generar()
        print("Carteras reiniciadas.")
        return
    if args.backtest:
        import backtest
        backtest.correr()
        return
    if not args.cada:
        sys.exit(1 if ciclo(args.solo) == len(CICLOS) else 0)

    print(f"Modo continuo: un ciclo cada {args.cada:g} minutos. Ctrl+C para detener.")
    try:
        while True:
            ciclo(args.solo)
            print(f"\nSiguiente ciclo en {args.cada:g} minutos...\n")
            time.sleep(args.cada * 60)
    except KeyboardInterrupt:
        print("\nBot detenido.")


if __name__ == "__main__":
    main()
