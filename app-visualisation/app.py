import tkinter as tk
from tkinter import scrolledtext
import json
import paho.mqtt.client as mqtt
import serial
import time
import threading
import random

# --- Config MQTT ---
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "application/c26f569e-4361-45b4-90e7-63c2fd56d88b/device/+/event/up"

# --- Config Série ---
SERIAL_PORT = 'COM11'       # Modifier selon ton système
BAUDRATE = 9600
SEND_INTERVAL = 10          # secondes

# --- Interface graphique ---
window = tk.Tk()
window.title("Lecteur de données LoRaWAN - ChirpStack")

text_area = scrolledtext.ScrolledText(window, width=60, height=20)
text_area.pack(padx=10, pady=10)

# --- MQTT callbacks ---
def on_connect(client, userdata, flags, rc):
    text_area.insert(tk.END, f"[INFO] Connecté au broker MQTT (code: {rc})\n")
    client.subscribe(MQTT_TOPIC)

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        decoded_text = payload.get("object", {}).get("text", None)
        dev_eui = payload.get("deviceInfo", {}).get("devEui", "unknown")

        if decoded_text:
            text_area.insert(tk.END, f"[{dev_eui}] Température reçue : {decoded_text} °C\n")
        else:
            text_area.insert(tk.END, f"[{dev_eui}] Aucun texte décodé.\n")
    except Exception as e:
        text_area.insert(tk.END, f"[ERREUR] {e}\n")

# --- Thread pour MQTT ---
def mqtt_loop():
    client.loop_forever()

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(MQTT_BROKER, MQTT_PORT, 60)

# --- Thread pour envoyer la commande série périodiquement ---
def serial_sender():
    try:
        with serial.Serial(SERIAL_PORT, BAUDRATE, timeout=1) as ser:
            print(f" Connecté à {SERIAL_PORT} @ {BAUDRATE} baud")
            while True:
                # Générer température aléatoire entre 5 et 35
                temp = random.randint(5, 35)
                temp_str = str(temp)
                hex_data = ''.join(f"{ord(c):02X}" for c in temp_str)
                length = len(temp_str)

                command = f"AT+SENDB=1,2,{length},{hex_data}\r\n"
                ser.write(command.encode())
                print(f" Commande envoyée: {command.strip()}")

                time.sleep(SEND_INTERVAL)
    except serial.SerialException as e:
        print(f"Erreur série: {e}")

# --- Démarrage des threads ---
threading.Thread(target=mqtt_loop, daemon=True).start()
threading.Thread(target=serial_sender, daemon=True).start()

# --- Lancement de la GUI (thread principal) ---
window.mainloop()
