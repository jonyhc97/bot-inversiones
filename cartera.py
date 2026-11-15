"""
Cartera simulada, una por mercado (acciones, cripto, polymarket).
Guarda todo en la carpeta datos/. Nada aqui usa dinero real.
"""
import csv
import json
import os
from datetime import datetime, timezone

import configuracion as cfg

BASE = os.path.dirname(os.path.abspath(__file__))
DATOS = os.path.join(BASE, cfg.CARPETA_DATOS)


def ahora():
    return datetime.now(timezone.utc)


def ahora_texto():
    return ahora().strftime("%Y-%m-%d %H:%M UTC")


def agregar_csv(ruta, fila):
    nuevo = not os.path.exists(ruta)
    with open(ruta, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(fila.keys()))
        if nuevo:
            w.writeheader()
        w.writerow(fila)


def leer_csv(ruta):
    if not os.path.exists(ruta):
        return []
    with open(ruta, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


class Cartera:
    def __init__(self, nombre, capital_inicial, comision=0.0):
        os.makedirs(DATOS, exist_ok=True)
        self.nombre = nombre
        self.comision = comision
        self.ruta = os.path.join(DATOS, f"cartera_{nombre}.json")
        self.ruta_ops = os.path.join(DATOS, f"operaciones_{nombre}.csv")
        self.ruta_hist = os.path.join(DATOS, f"historial_{nombre}.csv")
        if os.path.exists(self.ruta):
            with open(self.ruta, encoding="utf-8") as f:
                d = json.load(f)
        else:
            d = {"capital_inicial": capital_inicial, "efectivo": capital_inicial,
                 "posiciones": {}, "vendidos": {}, "creada": ahora_texto()}
        self.capital_inicial = d["capital_inicial"]
        self.efectivo = d["efectivo"]
        self.posiciones = d["posiciones"]
        self.vendidos = d.get("vendidos", {})
        self.creada = d.get("creada", ahora_texto())
        self.mensajes = []  # lo que paso en este ciclo (para pantalla y panel)

    def guardar(self):
        with open(self.ruta, "w", encoding="utf-8") as f:
            json.dump({"capital_inicial": self.capital_inicial,
                       "efectivo": round(self.efectivo, 6),
                       "posiciones": self.posiciones, "vendidos": self.vendidos,
                       "creada": self.creada}, f, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------
    def comprar(self, ident, nombre, lado, precio, monto, razon, extra=None):
        neto = monto * (1 - self.comision)
        cantidad = neto / precio
        self.efectivo -= monto
        pos = {"id": ident, "nombre": nombre, "lado": lado, "cantidad": cantidad,
               "precio_entrada": precio, "costo": monto, "precio_actual": precio,
               "precio_max": precio, "fecha_entrada": ahora_texto()}
        pos.update(extra or {})
        self.posiciones[ident] = pos
        self._registrar("COMPRA", pos, precio, monto, 0.0, razon)
        etiqueta = f"{lado} " if lado in ("YES", "NO") else ""
        self.mensajes.append(f"COMPRA {etiqueta}{nombre} | {monto:.2f} USD a {precio:.4g} | {razon}")

    def vender(self, ident, precio, razon):
        pos = self.posiciones.pop(ident)
        bruto = pos["cantidad"] * precio
        neto = bruto * (1 - self.comision)
        ganancia = neto - pos["costo"]
        self.efectivo += neto
        self.vendidos[ident] = ahora().isoformat()
        self._registrar("VENTA", pos, precio, neto, ganancia, razon)
        etiqueta = f"{pos['lado']} " if pos["lado"] in ("YES", "NO") else ""
        self.mensajes.append(f"VENTA  {etiqueta}{pos['nombre']} | {ganancia:+.2f} USD | {razon}")
        return ganancia

    def actualizar_precio(self, ident, precio):
        p = self.posiciones[ident]
        p["precio_actual"] = precio
        p["precio_max"] = max(p.get("precio_max", precio), precio)

    def _registrar(self, accion, pos, precio, monto, ganancia, razon):
        agregar_csv(self.ruta_ops, {
            "fecha": ahora_texto(), "accion": accion, "id": pos["id"],
            "nombre": pos["nombre"], "lado": pos["lado"],
            "cantidad": round(pos["cantidad"], 6), "precio": round(precio, 6),
            "monto_usd": round(monto, 2), "ganancia_usd": round(ganancia, 2),
            "razon": razon})

    # ------------------------------------------------------------------
    def recompra_bloqueada(self, ident, horas):
        fecha = self.vendidos.get(ident)
        if not fecha:
            return False
        if (ahora() - datetime.fromisoformat(fecha)).total_seconds() > horas * 3600:
            del self.vendidos[ident]
            return False
        return True

    def valor_posiciones(self):
        return sum(p["cantidad"] * p["precio_actual"] for p in self.posiciones.values())

    def valor_total(self):
        return self.efectivo + self.valor_posiciones()

    def rendimiento(self):
        return (self.valor_total() / self.capital_inicial - 1) * 100

    def monto_para_comprar(self, porcentaje, reserva):
        total = self.valor_total()
        return max(0.0, min(total * porcentaje, self.efectivo - total * reserva))

    def guardar_historial(self, referencia=None):
        agregar_csv(self.ruta_hist, {
            "fecha": ahora_texto(), "total_usd": round(self.valor_total(), 2),
            "efectivo_usd": round(self.efectivo, 2),
            "rendimiento_pct": round(self.rendimiento(), 2),
            "posiciones": len(self.posiciones),
            "referencia": "" if referencia is None else round(referencia, 6)})

    def operaciones(self):
        return leer_csv(self.ruta_ops)

    def historial(self):
        return leer_csv(self.ruta_hist)

    def resumen_cerradas(self):
        ventas = [o for o in self.operaciones() if o["accion"] == "VENTA"]
        ganadas = sum(1 for v in ventas if float(v["ganancia_usd"]) > 0)
        neto = sum(float(v["ganancia_usd"]) for v in ventas)
        return len(ventas), ganadas, neto
