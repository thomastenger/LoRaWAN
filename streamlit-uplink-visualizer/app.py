import streamlit as st
from mqtt_handler import MQTTHandler, message_queue
import time

st.set_page_config(page_title="LoRaWAN Dashboard", page_icon="📡")
st.title("📡 Données LoRaWAN reçues")
st.subheader("Décodage MQTT depuis ChirpStack")

if 'messages' not in st.session_state:
    st.session_state.messages = []



# Initialiser une seule fois
if 'mqtt_handler' not in st.session_state:
    handler = MQTTHandler()
    handler.start()
    st.session_state.mqtt_handler = handler
    print("🔁 MQTT handler initialisé")

# Relancer si le thread est mort (ex: après redémarrage Streamlit)
if not st.session_state.mqtt_handler.is_running():
    print("⚠️ MQTT thread mort, redémarrage...")
    new_handler = MQTTHandler()
    new_handler.start()
    st.session_state.mqtt_handler = new_handler


# Traitement des nouveaux messages
while True:
    try:
        msg = message_queue.get(timeout=1)
        st.session_state.messages.append(msg)
    except queue.Empty:
        break

# Affichage
for msg in reversed(st.session_state.messages[-30:]):
    st.markdown(f"**🧭 Topic**: `{msg.get('topic')}`")
    st.markdown(f"**🔹 Device**: `{msg.get('device')}` | **fPort**: `{msg.get('fPort')}`")
    st.markdown(f"**⏱️ Timestamp**: `{msg.get('timestamp')}`")
    st.code(msg.get("decoded", ""))
    st.markdown("---")
