#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dashboard Router — API ligera con Flask
---------------------------------------
Monitorea estadísticas del sistema (CPU, RAM, red) y bloqueos de Fail2Ban.
Pensado para entornos domésticos o de laboratorio, con bajo consumo de recursos.

Autor: [Volodymyr]
GitHub: [git@github.com:vldmr-d/router-dashboard.git]
"""
import importlib
import sys

# ============================================================
# 📦 Verificación de dependencias
# ============================================================

required_modules = {
    "flask": "Flask (framework web para la API)",
    "psutil": "Psutil (para estadísticas del sistema)"
}

missing = []

for module in required_modules:
    try:
        importlib.import_module(module)
    except ImportError:
        missing.append(module)

if missing:
    print("⚠️  Faltan las siguientes dependencias:")
    for module in missing:
        print(f"   - {module}: {required_modules[module]}")
    print("\n💡 Solución recomendada:")
    print("   python3 -m venv venv && source venv/bin/activate")
    print(f"   pip install {' '.join(missing)}")
    sys.exit(1)  # Evita seguir si faltan librerías


from flask import Flask, jsonify, render_template, request
import psutil, sqlite3, ipaddress, re, threading, time
from datetime import datetime, timedelta
from pathlib import Path
from functools import lru_cache
import os

# ============================================================
# ⚙️ Configuración general
# ============================================================

app = Flask(__name__)
DB_PATH = Path("data/router.db")
DB_PATH.parent.mkdir(exist_ok=True, parents=True)
LOG_FAIL2BAN = Path("/var/log/fail2ban.log")

#from flask_cors import CORS
#CORS(app)  # Habilita CORS para todas las rutas y orígenes

nic = 'eno1'

# ===============================
# 📦 Inicialización de base de datos SQLite
# ===============================
def init_db():
    """Inicializa la base de datos: crea tablas, índices y activa modo WAL."""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()

        # --- 1. Activar modo WAL para permitir lecturas/escrituras concurrentes ---
        c.execute("PRAGMA journal_mode=WAL;")
        c.execute("PRAGMA synchronous = NORMAL;")  # Mejor rendimiento con riesgo mínimo
        c.execute("PRAGMA temp_store = MEMORY;")   # Usa memoria para tablas temporales

        # --- 2. Crear tablas si no existen ---
        c.execute("""
        CREATE TABLE IF NOT EXISTS metrics (
            timestamp TEXT PRIMARY KEY,
            cpu REAL,
            ram REAL,
            net_sent REAL,
            net_recv REAL
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS bans (
            timestamp TEXT,
            ip TEXT,
            version INTEGER,
            count INTEGER,
            PRIMARY KEY (timestamp, ip, version)
        )
        """)

        # --- 3. Crear índices para acelerar consultas y limpieza ---
        c.execute("CREATE INDEX IF NOT EXISTS idx_metrics_time ON metrics(timestamp);")
        c.execute("CREATE INDEX IF NOT EXISTS idx_bans_time ON bans(timestamp);")

        conn.commit()

        print("[DB] Inicialización completa: modo WAL activado, tablas e índices creados.")


init_db()

# ===============================
# 🔧 Funciones auxiliares ( interfaz de red activa)
# ===============================
def get_active_interface():
    """Detecta interfaz de red activa (preferidas: ppp0, enp2s0, eth0...)."""
    addrs = psutil.net_if_addrs()
    preferred = ['ppp0', 'enp2s0', 'enp3s0', 'eth0']
    for iface in preferred:
        if iface in addrs:
            return iface
    return nic # <-- aqui poner NIC


@lru_cache(maxsize=1)
def parse_fail2ban_banned(conn=None):
    """Lee el log de fail2ban y guarda solo líneas con 'fail2ban.actions ... Ban <IP>'."""
    ipv4 = {}
    ipv6 = {}

    if not LOG_FAIL2BAN.exists():
        print("No hay log fail2ban o no tengo permisos para leer")
        return ipv4, ipv6

    pattern = re.compile(
        r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d{3}\s+fail2ban\.actions\s+\[\d+\]:\s+NOTICE\s+\[\S+\]\s+Ban\s+([0-9a-fA-F\.:]+)'
    )

    with open(LOG_FAIL2BAN, 'r') as f:
        for line in f:
            match = pattern.match(line)
            if not match:
                continue

            timestamp_str, ip = match.groups()
            try:
                parsed_ip = ipaddress.ip_address(ip)
                version = 4 if parsed_ip.version == 4 else 6

                # Verificar existencia previa (para no duplicar)
                c = conn.cursor() if conn else sqlite3.connect(DB_PATH).cursor()
                c.execute("""
                    SELECT 1 FROM bans
                    WHERE ip = ? AND version = ? AND timestamp = ?
                """, (ip, version, timestamp_str))
                if not c.fetchone():
                    if conn:
                        conn.execute("""
                            INSERT INTO bans (timestamp, ip, version, count)
                            VALUES (?, ?, ?, ?)
                        """, (timestamp_str, ip, version, 1))
                    else:
                        with sqlite3.connect(DB_PATH) as local_conn:
                            local_conn.execute("""
                                INSERT INTO bans (timestamp, ip, version, count)
                                VALUES (?, ?, ?, ?)
                            """, (timestamp_str, ip, version, 1))
                            local_conn.commit()

                # Contadores en memoria (solo informativo)
                if version == 4:
                    ipv4[ip] = ipv4.get(ip, 0) + 1
                else:
                    ipv6[ip] = ipv6.get(ip, 0) + 1

            except ValueError:
                continue

    return ipv4, ipv6


# ===============================
# 🧹 Rotación de datos (Elimina registros de más de 24 h.)
# ===============================
def clean_old_data(conn):
    """Elimina registros de más de 24 h."""
    cutoff = datetime.now() - timedelta(days=1)
    with conn:
        cur = conn.execute("DELETE FROM metrics WHERE timestamp < ?", (cutoff.strftime("%Y-%m-%d %H:%M:%S"),))
        deleted_metrics = cur.rowcount
        cur = conn.execute("DELETE FROM bans WHERE timestamp < ?", (cutoff.strftime("%Y-%m-%d %H:%M:%S"),))
        deleted_bans = cur.rowcount
        print(f"🧹 Limpieza: {deleted_metrics} métricas y {deleted_bans} baneos eliminados (>{cutoff})")

# ============================================================
# 🧵 Hilo de recolección de métricas
# ============================================================
def metrics_collector():
    """Hilo que recopila métricas y limpia datos antiguos."""
    """Recoge métricas del sistema y analiza Fail2Ban cada 30s."""

    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    last_cleanup = datetime.now()
    prev_sent, prev_recv = None, None
    warmup_cycles = 3  # ← número de ciclos a ignorar
    cycle_count = 0

    print(f"🕐 Esperando {warmup_cycles} ciclos de calentamiento antes de guardar métricas reales...")

    while True:
        try:
            cpu = psutil.cpu_percent()
            ram = psutil.virtual_memory().percent
            net = psutil.net_io_counters(pernic=True)
            iface = get_active_interface()
            net_stats = net.get(iface)
            current_sent = net_stats.bytes_sent
            current_recv = net_stats.bytes_recv
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Primeras iteraciones: solo inicializar referencias
            if cycle_count < warmup_cycles:
                prev_sent, prev_recv = current_sent, current_recv
                cycle_count += 1
                print(f"⏳ Ignorando ciclo {cycle_count}/{warmup_cycles} (calentamiento)")
                time.sleep(30)
                continue

            # Calcular diferencia en MB
            sent = round((current_sent - prev_sent) / (1024 * 1024), 2)
            recv = round((current_recv - prev_recv) / (1024 * 1024), 2)
            prev_sent, prev_recv = current_sent, current_recv

            # Evitar valores negativos por reinicio de contadores
            if sent < 0 or recv < 0:
                print("⚠️ Contadores de red reiniciados, reestableciendo base...")
                prev_sent, prev_recv = current_sent, current_recv
                time.sleep(30)
                continue

            # Guardar métricas reales
            with conn:
                conn.execute(
                    "INSERT INTO metrics VALUES (?, ?, ?, ?, ?)",
                    (now, cpu, ram, sent, recv)
                )

            print(f"[OK] {now} | CPU: {cpu:.1f}% | RAM: {ram:.1f}% | ↑ {sent} MB | ↓ {recv} MB")

            # Analizar Fail2Ban
            ipv4, ipv6 = parse_fail2ban_banned(conn)
            if ipv4 or ipv6:
                print(f"🚫 IPs bloqueadas — IPv4: {len(ipv4)} | IPv6: {len(ipv6)}")

            # Limpieza periódica
            if (datetime.now() - last_cleanup).total_seconds() > 300:
                clean_old_data(conn)
                last_cleanup = datetime.now()

        except Exception as e:
            print(f"[Error Collector] {e}")

        time.sleep(30)


# ============================================================
# 🌐 Endpoints API
# ============================================================

@app.route("/")
def index():
    """Devuelve la página principal (sin cambios)."""
    return render_template("index.html")

@app.route("/api/history")
def api_history():
    """Devuelve métricas históricas agrupadas por minuto + totales (para Chart.js)"""
    hours = int(request.args.get("hours", 24))
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()

        # 1️⃣ Datos históricos para los gráficos
        c.execute("""
            SELECT
                strftime('%Y-%m-%d %H:%M:00', timestamp) AS time,
                AVG(cpu), AVG(ram), AVG(net_sent), AVG(net_recv)
            FROM metrics
            WHERE timestamp >= datetime('now', ?)
            GROUP BY time
            ORDER BY time ASC
        """, (f'-{hours} hours',))
        rows = c.fetchall()

        # 2️⃣ Totales y promedios globales del periodo
        c.execute("""
            SELECT
                SUM(net_sent), SUM(net_recv),
                AVG(cpu), AVG(ram)
            FROM metrics
            WHERE timestamp >= datetime('now', ?)
        """, (f'-{hours} hours',))
        totals = c.fetchone()

    # 3️⃣ Procesar los resultados
    labels = []
    cpu_data, ram_data, net_sent, net_recv = [], [], [], []

    for t, cpu, ram, sent, recv in rows:
        labels.append(t)
        cpu_data.append(round(cpu, 2))
        ram_data.append(round(ram, 2))
        net_sent.append(round(sent, 2))
        net_recv.append(round(recv, 2))

    total_sent = round(totals[0] or 0, 2)
    total_recv = round(totals[1] or 0, 2)
    avg_cpu = round(totals[2] or 0, 2)
    avg_ram = round(totals[3] or 0, 2)

    # 4️⃣ JSON de salida combinado
    return jsonify({
        "labels": labels,
        "datasets": {
            "cpu_usage": cpu_data,
            "ram_usage": ram_data,
            "net_sent": net_sent,
            "net_recv": net_recv
        },
        "summary": {
            "hours": hours,
            "avg_cpu": avg_cpu,
            "avg_ram": avg_ram,
            "total_net_sent_MB": total_sent,
            "total_net_recv_MB": total_recv
        }
    })

@app.route("/api/bans-details")
def api_bans_details():
    """
    Devuelve los detalles de las IPs bloqueadas en las últimas N horas (por minuto).

    Estructura de salida JSON:
    {
        "summary": {
            "hours": 24,
            "total_ipv4": 123,
            "total_ipv6": 45
        },
        "data": {
            "2025-11-02 00:10:00": {"ipv4": ["69.231.138.115"], "ipv6": []},
            "2025-11-02 09:41:00": {"ipv4": [], "ipv6": ["2a00:1450:4003:80c::200e"]},
            ...
        }
    }
    """
    # Horas configurables vía parámetro GET (?hours=12)
    hours = int(request.args.get("hours", 24))
    cutoff = datetime.now() - timedelta(hours=hours)

    with sqlite3.connect(DB_PATH, timeout=5) as conn:
        conn.row_factory = sqlite3.Row  # permite acceder por nombre de columna
        c = conn.cursor()

        # Consulta parametrizada (segura, sin SQL injection)
        c.execute("""
            SELECT
                strftime('%Y-%m-%d %H:%M:00', timestamp) AS minute,
                ip,
                version
            FROM bans
            WHERE timestamp >= ?
            ORDER BY minute ASC, ip ASC
        """, (cutoff.strftime("%Y-%m-%d %H:%M:%S"),))

        rows = c.fetchall()

    # Estructura principal
    minute_details = {}
    total_ipv4 = 0
    total_ipv6 = 0

    for row in rows:
        minute = row["minute"]
        ip = row["ip"]
        version = row["version"]

        # Crear entrada por minuto si no existe
        if minute not in minute_details:
            minute_details[minute] = {"ipv4": [], "ipv6": []}

        # Clasificar IP por versión
        if version == 4:
            minute_details[minute]["ipv4"].append(ip)
            total_ipv4 += 1
        elif version == 6:
            minute_details[minute]["ipv6"].append(ip)
            total_ipv6 += 1

    # Construir salida JSON final
    result = {
        "summary": {
            "hours": hours,
            "total_ipv4": total_ipv4,
            "total_ipv6": total_ipv6
        },
        "data": minute_details
    }

    return jsonify(result)


# ============================================================
# 🚀 Ejecución del servidor
# ============================================================
if __name__ == "__main__":
    print("🟢 Iniciando dashboard del router con recolección automática cada 30 s")
     # Evita ejecución doble del hilo cuando Flask está en modo debug
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        threading.Thread(target=metrics_collector, daemon=True).start()
    app.run(host="0.0.0.0", port=5000, debug=True)
