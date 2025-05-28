import streamlit as st
import grpc
import os
import re
import random
import smtplib
from email.mime.text import MIMEText
from chirpstack_api import api




# --------------- TRADUCTIONS ---------------

translations = {
    "fr": {
        "title": "Vérification email & ajout device ChirpStack (OTAA)",
        "email_label": "Adresse email",
        "send_code": "Envoyer le code de vérification",
        "code_sent": "Code envoyé ! Vérifiez votre boîte mail.",
        "enter_code": "Entrez le code OTP reçu par email",
        "verify_code": "Vérifier le code",
        "code_validated": "Email vérifié. Vous pouvez maintenant ajouter un device.",
        "invalid_code": "Code incorrect.",
        "add_device": "Ajout du device",
        "dev_eui_label": "DevEUI (16 caractères hex)",
        "device_name_label": "Nom du device",
        "submit_device": "Ajouter le device",
        "dev_eui_invalid": "DevEUI invalide. Il doit contenir 16 caractères hexadécimaux.",
        "device_name_required": "Le nom du device est requis.",
        "device_added": "✔️ Device ajouté avec succès !",
        "email_not_verified": "Veuillez vérifier votre email avant d'ajouter un device.",
        "email_send_error": "Erreur envoi email :",
        "chirpstack_error": "Erreur ChirpStack"
    },
    "en": {
        "title": "Email verification & ChirpStack device registration (OTAA)",
        "email_label": "Email address",
        "send_code": "Send verification code",
        "code_sent": "Code sent! Check your inbox.",
        "enter_code": "Enter the OTP code received by email",
        "verify_code": "Verify code",
        "code_validated": "Email verified. You can now add a device.",
        "invalid_code": "Incorrect code.",
        "add_device": "Add device",
        "dev_eui_label": "DevEUI (16 hex characters)",
        "device_name_label": "Device name",
        "submit_device": "Register device",
        "dev_eui_invalid": "Invalid DevEUI. Must be 16 hexadecimal characters.",
        "device_name_required": "Device name is required.",
        "device_added": "✔️ Device successfully added!",
        "email_not_verified": "Please verify your email before adding a device.",
        "email_send_error": "Email sending error:",
        "chirpstack_error": "ChirpStack Error"
    },
    "sk": {
        "title": "Overenie e-mailu a pridanie zariadenia ChirpStack (OTAA)",
        "email_label": "Emailová adresa",
        "send_code": "Odoslať overovací kód",
        "code_sent": "Kód bol odoslaný! Skontrolujte si e-mail.",
        "enter_code": "Zadajte OTP kód z e-mailu",
        "verify_code": "Overiť kód",
        "code_validated": "Email overený. Môžete pridať zariadenie.",
        "invalid_code": "Nesprávny kód.",
        "add_device": "Pridať zariadenie",
        "dev_eui_label": "DevEUI (16 hex znakov)",
        "device_name_label": "Názov zariadenia",
        "submit_device": "Pridať zariadenie",
        "dev_eui_invalid": "Neplatný DevEUI. Musí obsahovať 16 hex znakov.",
        "device_name_required": "Názov zariadenia je povinný.",
        "device_added": "✔️ Zariadenie úspešne pridané!",
        "email_not_verified": "Pred pridaním zariadenia overte e-mail.",
        "email_send_error": "Chyba pri odosielaní e-mailu:",
        "chirpstack_error": "Chyba ChirpStack"
    }
}

# --------------- CHOIX LANGUE ---------------
lang = st.sidebar.selectbox("🌐 Choisir la langue / Select language / Zvoliť jazyk", ["fr", "en", "sk"])
t = translations[lang]

# --------------- CONFIGURATION ---------------

#server = "chirpstack:8080"
server =  "1d9c-158-193-152-33.ngrok-free.app:453"
api_token = st.secrets["CHIRPSTACK_API_TOKEN"]
application_id = "c26f569e-4361-45b4-90e7-63c2fd56d88b"
device_profile_id = "0fdd2cac-d304-4e13-b310-1eca13302fe5"

SMTP_SERVER = st.secrets["SMTP_SERVER"]
SMTP_PORT = int(st.secrets["SMTP_PORT"])
SMTP_LOGIN = st.secrets["SMTP_LOGIN"]
SMTP_PASSWORD = st.secrets["SMTP_PASSWORD"]

# --------------- SESSION STATE ---------------

if "email_verified" not in st.session_state:
    st.session_state.email_verified = False
if "otp_sent" not in st.session_state:
    st.session_state.otp_sent = False
if "generated_otp" not in st.session_state:
    st.session_state.generated_otp = ""

# --------------- ENVOI EMAIL ---------------

def send_otp_email(to_email, otp_code):
    subject = "Verification Code / Code de vérification"
    body = f"{t['code_sent']}\n\nOTP: {otp_code}"
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = SMTP_LOGIN
    msg["To"] = to_email

    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SMTP_LOGIN, SMTP_PASSWORD)
            server.sendmail(SMTP_LOGIN, to_email, msg.as_string())
        return True
    except Exception as e:
        st.error(f"{t['email_send_error']} {e}")
        return False

# --------------- INTERFACE UI ---------------

st.title(t["title"])

email = st.text_input(t["email_label"])

if st.button(t["send_code"]):
    otp = f"{random.randint(100000, 999999)}"
    sent = send_otp_email(email, otp)
    if sent:
        st.session_state.generated_otp = otp
        st.session_state.otp_sent = True
        st.session_state.email = email
        st.success(t["code_sent"])

if st.session_state.otp_sent and not st.session_state.email_verified:
    otp_input = st.text_input(t["enter_code"])
    if st.button(t["verify_code"]):
        if otp_input == st.session_state.generated_otp:
            st.session_state.email_verified = True
            st.success(t["code_validated"])
        else:
            st.error(t["invalid_code"])

if st.session_state.email_verified:
    st.subheader(t["add_device"])
    with st.form("add_device_form"):
        dev_eui = st.text_input(t["dev_eui_label"], max_chars=16)
        dev_name = st.text_input(t["device_name_label"])
        submitted = st.form_submit_button(t["submit_device"])

        if submitted:
            if not re.fullmatch(r"[0-9A-Fa-f]{16}", dev_eui):
                st.error(t["dev_eui_invalid"])
            elif not dev_name:
                st.error(t["device_name_required"])
            else:
                try:
                    #channel = grpc.insecure_channel(server)
                    channel = grpc.secure_channel(server, grpc.ssl_channel_credentials())
                    client = api.DeviceServiceStub(channel)
                    metadata = [("authorization", f"Bearer {api_token}")]

                    device = api.Device()
                    device.dev_eui = dev_eui
                    device.name = dev_name
                    device.application_id = application_id
                    device.description = st.session_state.email
                    device.device_profile_id = device_profile_id

                    req = api.CreateDeviceRequest(device=device)
                    client.Create(req, metadata=metadata)

                    app_key = os.urandom(16).hex()
                    keys = api.DeviceKeys()
                    keys.dev_eui = dev_eui
                    keys.app_key = app_key
                    keys.nwk_key = app_key

                    key_req = api.CreateDeviceKeysRequest(device_keys=keys)
                    client.CreateKeys(key_req, metadata=metadata)

                    st.success(t["device_added"])
                    st.code(f"AppKey : {app_key}")

                except grpc.RpcError as e:
                    st.error(f"{t['chirpstack_error']} : {e.code()} - {e.details()}")

else:
    st.info(t["email_not_verified"])
