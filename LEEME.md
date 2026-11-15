# Bot de inversiones: acciones, cripto y Polymarket (simulación)

Bot que analiza **acciones**, **criptomonedas** y **Polymarket**. Cada mercado tiene su propia cartera con **1,000 USD ficticios** y el bot decide solo qué comprar y cuándo vender. Todo es simulado: no tiene código para conectarse a ningún broker ni para usar dinero real.

---

## 1. Probarlo en tu Mac

Abre la **Terminal** (⌘ + Espacio y escribe "Terminal") y pega estas líneas, una por una:

```bash
cd ~/Documents/BOT_INVERSIONES
python3 bot.py --backtest     # ¿Habría ganado en los últimos ~3 años? (compara 4 versiones)
python3 bot.py                # Un ciclo real: analiza, compra/vende y actualiza el panel
open docs/index.html          # Abre el panel en tu navegador
```

Otros comandos:

| Comando | Qué hace |
|---|---|
| `python3 bot.py --solo cripto` | Corre solo un mercado (`acciones`, `cripto` o `polymarket`) |
| `python3 bot.py --cada 60` | Lo repite cada 60 minutos mientras la Terminal esté abierta |
| `python3 bot.py --reiniciar` | Borra las carteras y empieza de cero |

---

## 2. Que funcione solo en la nube (GitHub, gratis)

Con esto el bot corre **cada 2 horas aunque tu Mac esté apagada**, y ves el panel desde tu celular.

1. **Crea tu cuenta** en https://github.com (gratis).
2. Arriba a la derecha, da clic en **+ → New repository**.
   - Nombre: `bot-inversiones`
   - Elige **Public**. GitHub Pages solo es gratis en repositorios públicos; solo se ven tus resultados simulados, nada privado.
   - Clic en **Create repository**.
3. En la página nueva, da clic en **"uploading an existing file"** y arrastra todos los archivos de la carpeta `BOT_INVERSIONES`. Luego da clic en **Commit changes**.
4. **Programa el bot para que corra solo:** en tu repositorio da clic en **Add file → Create new file**.
   - En el nombre escribe exactamente: `.github/workflows/bot.yml`
   - Abre el archivo `PEGAR_EN_GITHUB_bot.yml` (con doble clic se abre en TextEdit), copia todo su contenido y pégalo en el recuadro grande.
   - Da clic en **Commit changes**.
5. **Activa los permisos:** ve a **Settings → Actions → General**, baja a "Workflow permissions", elige **Read and write permissions** y da clic en **Save**.
6. **Primera corrida:** ve a la pestaña **Actions**, elige **"Bot de inversiones"** y da clic en **Run workflow**. Debe terminar con una palomita verde ✅.
7. **Activa el panel:** ve a **Settings → Pages**. En "Branch" elige **main** y la carpeta **/docs**, y da clic en **Save**. En uno o dos minutos te aparece el link, algo como
   `https://TU-USUARIO.github.io/bot-inversiones/`
   Guárdalo en favoritos del celular.

Listo: a partir de ahí el bot corre solo cada 2 horas y el panel se actualiza.

---

## 3. Cómo funciona la estrategia

**Acciones y cripto (estrategia de índice, la que está activa):**
- **Acciones:** compra el índice **SPY**, que equivale a un pedacito de las 500 empresas más grandes de EE.UU.
- **Cripto:** compra **Bitcoin**.
- Si el precio cae más de 2% debajo de su promedio de 200 días, vende todo y se queda en efectivo. Cuando vuelve a subir arriba del promedio, vuelve a comprar.
- Es un "seguro": en años buenos gana un poco menos que comprar y aguantar, pero en caídas grandes te protege.
- Se eligió con `python3 bot.py --backtest`, que compara esta regla contra otras 4 versiones.
- La estrategia anterior, de varias acciones a la vez, sigue disponible: en `configuracion.py` cambia `"estrategia": "indice"` por `"estrategia": "tendencia"`.

**Polymarket:**
- Compra el lado cuya probabilidad viene subiendo en el día y en la semana.
- Pone **máximo 2 apuestas del mismo tema** (Bitcoin, Elon Musk, elecciones…) para no apostar todo a lo mismo.
- Vende al ganar 25%, al perder 15%, si cambia la tendencia, si el mercado está por vencer o cuando se resuelve.

Todo esto se cambia en **`configuracion.py`**: capital, acciones y criptos a seguir, porcentajes, etc.

## 4. Archivos

| Archivo | Para qué sirve |
|---|---|
| `bot.py` | Programa principal |
| `configuracion.py` | **Aquí cambias todo** |
| `estrategias.py` | Reglas de compra y venta |
| `mercados.py` | El ciclo de cada mercado |
| `fuentes.py` | Descarga precios (Yahoo Finance, Coinbase, Polymarket) |
| `backtest.py` | Prueba con precios pasados |
| `panel.py` | Genera la página `docs/index.html` |
| `cartera.py` | Carteras simuladas |
| `datos/` | Carteras, operaciones e historial (se crean solos) |
| `PEGAR_EN_GITHUB_bot.yml` | Se pega en GitHub para que lo corra cada 2 horas (paso 4) |

## Importante

- Ninguna estrategia garantiza ganancias. Que algo haya funcionado en el pasado no asegura el futuro.
- Déjalo correr **al menos 1 o 2 meses** en simulación antes de pensar en dinero real. Compáralo siempre contra "solo comprar y aguantar" (el backtest lo hace por ti).
