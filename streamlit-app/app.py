import streamlit as st
import grpc
from chirpstack_api import api
import re
import os

# Configuration fixe
server = "chirpstack:8080"
api_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJjaGlycHN0YWNrIiwiaXNzIjoiY2hpcnBzdGFjayIsInN1YiI6IjQzNjVkODE1LWY3YzctNDIxMy1iODk3LWQyYjNlZmQ0YTM1YiIsInR5cCI6ImtleSJ9.tcQbCFLDQBj8AFxLeNJ19E_hE3bQAQc5bSNc_X-99Ic"
application_id = "c26f569e-4361-45b4-90e7-63c2fd56d88b"
device_profile_id = "0fdd2cac-d304-4e13-b310-1eca13302fe5" 

st.title("Ajout de device ChirpStack (OTAA)")

# Formulaire utilisateur
with st.form("add_device_form"):
    dev_eui = st.text_input("DevEUI (16 caractères hex)", max_chars=16)
    dev_name = st.text_input("Nom du device")
    description = st.text_input("Adresse email (doit se terminer par .uniza.sk)")
    submitted = st.form_submit_button("Ajouter le device")

    if submitted:
        # Validation
        if not re.fullmatch(r"[0-9A-Fa-f]{16}", dev_eui):
            st.error("DevEUI invalide. Il doit contenir exactement 16 caractères hexadécimaux.")
        elif not dev_name:
            st.error("Le nom du device est obligatoire.")
        elif not re.fullmatch(r".+@(.+\.)?uniza\.sk", description):
            st.error("L'adresse e-mail doit se terminer par '.uniza.sk' (ex: user@stud.uniza.sk).")
        else:
            try:
                # Connexion gRPC
                channel = grpc.insecure_channel(server)
                client = api.DeviceServiceStub(channel)
                key_client = api.DeviceServiceStub(channel)
                auth_token = [("authorization", f"Bearer {api_token}")]

                # Création du device
                device = api.Device()
                device.dev_eui = dev_eui
                device.name = dev_name
                device.application_id = application_id
                device.description = description
                device.device_profile_id = device_profile_id

                req = api.CreateDeviceRequest(device=device)
                client.Create(req, metadata=auth_token)

                # Génération AppKey
                app_key = os.urandom(16).hex()

                # Création des clés pour OTAA
                keys = api.DeviceKeys()
                keys.dev_eui = dev_eui
                keys.nwk_key = app_key  # nwk_key est utilisé pour LoRaWAN 1.1+, remplace-le par app_key si nécessaire
                keys.app_key = app_key

                key_req = api.CreateDeviceKeysRequest(device_keys=keys)
                client.CreateKeys(key_req, metadata=auth_token)

                st.success(f"✔️ Device '{dev_name}' ajouté avec succès avec AppKey générée automatiquement.")
                st.code(f"AppKey : {app_key}", language="text")

            except grpc.RpcError as e:
                st.error(f"❌ Erreur : {e.code()} - {e.details()}")
