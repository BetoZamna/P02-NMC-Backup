#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
P02-NCM-Backup
Script para conectarse a varios routers (Cisco IOS) y extraer su configuración.
Se ejecuta en un bucle infinito cada 5 segundos.
Compara solo la parte pura del running-config (ignorando encabezado) para detectar cambios reales.
Si se crea/actualiza un archivo, hace commit y push a GitHub automáticamente.
"""

import os
import datetime
import time
import subprocess
from netmiko import ConnectHandler

# 1. Definir dispositivos
device_r1 = {
    'name': 'R1',
    'device_type': 'cisco_ios',
    'host': '192.168.110.50',
    'username': 'paulo',
    'password': 'paulo123',
    'secret': '',
    'port': 22,
}
device_r2 = {
    'name': 'R2',
    'device_type': 'cisco_ios',
    'host': '192.168.1.2',
    'username': 'paulo',
    'password': 'paulo123',
    'secret': '',
    'port': 22,
}
device_r3 = {
    'name': 'R3',
    'device_type': 'cisco_ios',
    'host': '192.168.1.3',
    'username': 'paulo',
    'password': 'paulo123',
    'secret': '',
    'port': 22,
}

devices = [device_r1, device_r2, device_r3]

# 2. Función para hacer commit y push a GitHub
def commit_and_push_changes():
    """
    Lanza comandos Git para subir los cambios al repositorio remoto.
    Requiere que ya hayas hecho 'git init', 'git remote add origin ...', y que
    tengas tus credenciales (o SSH keys) configuradas para no pedir usuario/pass.
    """
    # Agregar todos los archivos que hayan cambiado
    subprocess.run(["git", "add", "."])
    
    # Crear un mensaje de commit con fecha/hora
    commit_msg = f"Backup automatico {datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')}"
    subprocess.run(["git", "commit", "-m", commit_msg])
    
    # Empujar a la rama principal (puede ser 'main' o 'master', según tu repo)
    subprocess.run(["git", "push", "origin", "main"])

# 3. Función principal de backup
def backup_configs():
    """
    Se conecta a cada router, obtiene su running-config pura,
    la combina con un encabezado y un marcador '++START-CONFIG++',
    y compara SOLO la parte posterior al marcador con el backup anterior.
    Si hay cambios, reemplaza el archivo anterior y luego hace un git commit/push.
    """

    backups_root = "BACKUPS_P02-NCM-Backup"
    if not os.path.exists(backups_root):
        os.mkdir(backups_root)

    for device in devices:
        print(f"\n*** Conectando a {device['name']} [{device['host']}] via SSH...")

        # Copia sin 'name' para Netmiko
        device_for_netmiko = device.copy()
        device_for_netmiko.pop('name', None)

        net_connect = ConnectHandler(**device_for_netmiko)
        print(f"Obteniendo configuración de {device['name']}...")

        # 1) Config pura desde el router
        pure_config = net_connect.send_command("show running-config")
        net_connect.disconnect()

        # 2) Encabezado
        now_for_content = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        header = (
            "##### BACKUP AUTOMÁTICO #####\n"
            f"# Dispositivo : {device['name']} ({device['host']})\n"
            f"# Fecha/Hora  : {now_for_content}\n"
            "# Descripción : Respaldo de running-config\n"
            "##############################\n\n"
        )
        # Marcador para separar encabezado y config pura
        marker = "++START-CONFIG++\n"
        
        # Contenido final
        new_file_content = header + marker + pure_config

        # 3) Carpeta del dispositivo
        device_folder_name = f"{device['name']}-{device['host']}"
        device_folder_path = os.path.join(backups_root, device_folder_name)
        if not os.path.exists(device_folder_path):
            os.mkdir(device_folder_path)

        # 4) Verificar si existe un archivo previo
        existing_files = [f for f in os.listdir(device_folder_path) if f.endswith(".txt")]
        previous_file_path = None
        if existing_files:
            previous_file_path = os.path.join(device_folder_path, existing_files[0])

        # 5) Comparar parte pura (ignorando el encabezado)
        config_changed = True  # asume que cambió, hasta comprobar lo contrario
        if previous_file_path and os.path.exists(previous_file_path):
            with open(previous_file_path, "r") as prev_file:
                old_file_content = prev_file.read()

            idx = old_file_content.find(marker)
            if idx != -1:
                old_pure_config = old_file_content[idx + len(marker):].strip()
            else:
                old_pure_config = ""

            if old_pure_config == pure_config.strip():
                print(f"--> No hay cambios en {device['name']}. Se conserva el backup anterior.")
                config_changed = False
            else:
                print(f"--> Configuración diferente en {device['name']}. Se reemplaza el archivo anterior.")
                os.remove(previous_file_path)
        else:
            print(f"--> No existe backup previo para {device['name']}. Creando uno nuevo...")

        # 6) Solo si hay cambios se crea un nuevo archivo
        if config_changed:
            now_for_filename = datetime.datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
            file_name = f"{device['name']}_fecha_{now_for_filename.replace('_','_hora_')}.txt"
            file_path = os.path.join(device_folder_path, file_name)
            
            with open(file_path, "w") as backup_file:
                backup_file.write(new_file_content)

            print(f"Respaldo guardado en: {file_path}")

            # 7) Subir a GitHub
            commit_and_push_changes()

# 4. Bucle infinito para ejecutarlo cada 5 segundos
if __name__ == "__main__":
    print("Iniciando respaldos en bucle infinito (cada 5 segundos). Presiona Ctrl + C para detener.")
    while True:
        backup_configs()
        print("¡Proceso de respaldo completado con éxito en esta iteración!\n")
        print("Esperando 5 segundos...")
        time.sleep(5)
        print("Listo. Continuando...\n")
