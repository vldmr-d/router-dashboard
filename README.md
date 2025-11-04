# router-dashboard

<img width="1052" height="863" alt="Screenshot from 2025-11-03 14-22-50" src="https://github.com/user-attachments/assets/abbd96a1-3682-419b-8bf7-a59ffb8aa96b" />

🧠 Proyecto: Dashboard Ligero para Router (estilo Pi-hole)

Un dashboard ligero, sin dependencias pesadas, diseñado para monitorizar CPU, RAM, red e IPs bloqueadas (Fail2Ban) desde una interfaz moderna basada en Flask + Chart.js.

🚀 Características

📊 Estadísticas en tiempo real (CPU, RAM, red, IPs bloqueadas)
🕐 Gráficos dinámicos con Chart.js
🧠 Bajo consumo de recursos (ideal para Raspberry Pi o routers Linux)

🧩 Requisitos del sistema

Python 3.8 o superior
Acceso al sistema con permisos de lectura sobre /proc (para psutil)
Interfaz de red reconocida por el sistema (ej. eth0, wlan0)
Opcional: Fail2Ban para obtener IPs bloqueadas

📦 Instalación

🔹 Clonar el repositorio
```console
git clone https://github.com/tuusuario/router-dashboard.git
cd router-dashboard
```
🔹 Crear entorno virtual (recomendado)
```console
python3 -m venv venv
source venv/bin/activate
```
🔹 Instalar dependencias
```console
pip install flask psutil
```
💡 No se instalan globalmente, solo dentro del entorno virtual.

🔹 Alternativa: instalación global desde los repositorios del sistema

Si se prefiere no usar un entorno virtual, las dependencias también se pueden instalar desde los paquetes del sistema:
```console
apt search python3-flask
apt search python3-psutil

sudo apt install python3-flask python3-psutil
```
En este caso, no es necesario crear un entorno virtual, pero se recomienda igualmente para mantener el entorno limpio y reproducible.

🔹 Configurar la interfaz de red (NIC)

En el archivo app.py, modifique el nombre de la interfaz de red (NIC) para que coincida con la de su sistema.
```console
nic = 'eno1'  # Ejemplo: 'ppp0', 'enp2s0', 'enp3s0', 'eth0'
```
🖥️  Ejecución del servidor
```console
python3 app.py
```

Abre tu navegador en:

👉 http://localhost:5000

o desde otro dispositivo en la misma red:

👉 http://<IP_del_router>:5000
