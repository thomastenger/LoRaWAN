import streamlit as st
import streamlit.components.v1 as components
import grpc
import os
import re
import random
import smtplib
from email.mime.text import MIMEText
from chirpstack_api import api
import psycopg2
from datetime import datetime
import socket

def log_api_usage(user_email, endpoint=None, status='success'):
    try:
        conn = psycopg2.connect(
            dbname="chirpstack",
            user="chirpstack",
            password="chirpstack",
            host="postgres"
        )
        cur = conn.cursor()

        ip = socket.gethostbyname(socket.gethostname())

        cur.execute(
            "INSERT INTO api_logs (user_email, endpoint, status, ip_address, connexion_at) VALUES (%s, %s, %s, %s, %s)",
            (user_email, endpoint, status, ip, datetime.now())
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        st.warning(f"Log failed: {e}")

# Traductions
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
        "device_added": "Device ajouté avec succès !",
        "email_not_verified": "Veuillez vérifier votre email avant d'ajouter un device.",
        "email_send_error": "Erreur envoi email :",
        "chirpstack_error": "Erreur ChirpStack",
        "app_key_label": "AppKey (32 caractères hex)",
        "rgpd_footer": "🔐 En utilisant cette application, vous acceptez notre <a onclick=\"document.getElementById('rgpd-modal').style.display='block';\">politique de confidentialité</a>.",
        "rgpd_title": "Politique de confidentialité",
        "rgpd_collected": "Données collectées :",
        "rgpd_fields": "- Adresse e-mail<br>- Adresse IP<br>- Horaires de connexion",
        "rgpd_usage": "Utilisation : à des fins de sécurité, journalisation, amélioration du service.",
        "rgpd_duration": "Durée : conservées 6 mois puis supprimées.",
        "rgpd_rights": "Vos droits : Demande d’accès/suppression via :",
        "rgpd_contact": "contact@votresite.com"
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
        "device_added": "Device successfully added!",
        "email_not_verified": "Please verify your email before adding a device.",
        "email_send_error": "Email sending error:",
        "chirpstack_error": "ChirpStack Error",
        "app_key_label": "AppKey (32 hex characters)",
        "rgpd_footer": "🔐 By using this app, you agree to our <a onclick=\"document.getElementById('rgpd-modal').style.display='block';\">privacy policy</a>.",
        "rgpd_title": "Privacy Policy",
        "rgpd_collected": "Collected Data:",
        "rgpd_fields": "- Email address<br>- IP address<br>- Connection timestamps",
        "rgpd_usage": "Purpose: security, logging, and service improvement.",
        "rgpd_duration": "Retention: stored for 6 months then deleted.",
        "rgpd_rights": "Your rights: Request access/removal via:",
        "rgpd_contact": "contact@yourdomain.com"
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
        "device_added": "Zariadenie úspešne pridané!",
        "email_not_verified": "Pred pridaním zariadenia overte e-mail.",
        "email_send_error": "Chyba pri odosielaní e-mailu:",
        "chirpstack_error": "Chyba ChirpStack",
        "app_key_label": "AppKey (32 hex znakov)",
        "rgpd_footer": "🔐 Používaním tejto aplikácie súhlasíte s našimi <a onclick=\\\"document.getElementById('rgpd-modal').style.display='block';\\\">zásadami ochrany osobných údajov</a>.",
        "rgpd_title": "Zásady ochrany osobných údajov",
        "rgpd_collected": "Zhromažďované údaje:",
        "rgpd_fields": "- Emailová adresa<br>- IP adresa<br>- Čas pripojenia",
        "rgpd_usage": "Použitie: na účely bezpečnosti, protokolovania a zlepšenia služby.",
        "rgpd_duration": "Uchovávanie: 6 mesiacov, potom vymazané.",
        "rgpd_rights": "Vaše práva: Žiadosť o prístup/vymazanie na:",
        "rgpd_contact": "kontakt@vasedomena.sk"
    }
}

# Choix de la langue
lang = st.sidebar.selectbox("🌐 Choisir la langue / Select language / Zvoliť jazyk", ["fr", "en", "sk"])
t = translations[lang]

# Configuration
server = "chirpstack:8080"
api_token = st.secrets["CHIRPSTACK_API_TOKEN"]
application_id = st.secrets["APPLICATION_ID"] 
device_profile_id = st.secrets["DEVICE_Profile_ID"] 

SMTP_SERVER = st.secrets["SMTP_SERVER"]
SMTP_PORT = int(st.secrets["SMTP_PORT"])
SMTP_LOGIN = st.secrets["SMTP_LOGIN"]
SMTP_PASSWORD = st.secrets["SMTP_PASSWORD"]

# Session
if "email_verified" not in st.session_state:
    st.session_state.email_verified = False
if "otp_sent" not in st.session_state:
    st.session_state.otp_sent = False
if "generated_otp" not in st.session_state:
    st.session_state.generated_otp = ""

# Envoi de l'OTP
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

# Interface
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
            log_api_usage(email, endpoint="email_verification", status="success connection")
        else:
            st.error(t["invalid_code"])
            log_api_usage(email, endpoint="failed_verification", status="fail connection")

if st.session_state.email_verified:
    st.subheader(t["add_device"])
    with st.form("add_device_form"):
        dev_eui = st.text_input(t["dev_eui_label"], max_chars=16)
        dev_name = st.text_input(t["device_name_label"])
        app_key = st.text_input(t["app_key_label"], max_chars=32)
        submitted = st.form_submit_button(t["submit_device"])

        if submitted:
            if not re.fullmatch(r"[0-9A-Fa-f]{16}", dev_eui):
                st.error(t["dev_eui_invalid"])
            elif not dev_name:
                st.error(t["device_name_required"])
            elif not re.fullmatch(r"[0-9A-Fa-f]{32}", app_key):
                st.error("Invalid AppKey. Must be 32 hexadecimal characters.")
            else:
                try:
                    channel = grpc.insecure_channel(server)
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

                    keys = api.DeviceKeys()
                    keys.dev_eui = dev_eui
                    keys.app_key = app_key
                    keys.nwk_key = app_key

                    key_req = api.CreateDeviceKeysRequest(device_keys=keys)
                    client.CreateKeys(key_req, metadata=metadata)

                    st.success(t["device_added"])
                    log_api_usage(email, endpoint="device_creation", status="success add device")

                except grpc.RpcError as e:
                    st.error(f"{t['chirpstack_error']}: {e.code()} - {e.details()}")
                    log_api_usage(email, endpoint="chirpstack_error", status="Grpc exception")
else:
    st.info(t["email_not_verified"])

# Modale RGPD dynamique
components.html(f"""
<style>
.footer-rgpd {{
    text-align: center;
    color: gray;
    font-size: 0.9em;
    margin-top: 50px;
}}
.footer-rgpd a {{
    color: #4c8bf5;
    text-decoration: underline;
    cursor: pointer;
}}

#rgpd-modal {{
    display: none;
    position: fixed;
    z-index: 9998;
    left: 0; top: 0;
    width: 100%; height: 100%;
    background-color: rgba(0, 0, 0, 0.6);
}}

#rgpd-content {{
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    background-color: white;
    padding: 20px;
    width: 90%;
    max-width: 600px;
    border-radius: 12px;
    box-shadow: 0 0 20px rgba(0,0,0,0.3);
    z-index: 9999;
    font-family: sans-serif;
    color: #333;
    box-sizing: border-box;
    animation: fadeIn 0.3s ease-out;
}}
@keyframes fadeIn {{
    from {{ opacity: 0; transform: translate(-50%, -60%); }}
    to   {{ opacity: 1; transform: translate(-50%, -50%); }}
}}

#close-btn {{
    position: absolute;
    top: 10px;
    right: 15px;
    font-size: 24px;
    color: #888;
    cursor: pointer;
    font-weight: bold;
}}
#close-btn:hover {{
    color: black;
}}

@media only screen and (max-width: 480px) {{
    #rgpd-content {{
        width: 95%;
        padding: 16px;
        font-size: 0.95em;
    }}
    #close-btn {{
        font-size: 20px;
        right: 5px;
    }}
}}
</style>

<div class="footer-rgpd">
    {t["rgpd_footer"]}
</div>

<div id="rgpd-modal">
    <div id="rgpd-content">
        <span id="close-btn" onclick="document.getElementById('rgpd-modal').style.display='none';">&times;</span>
        <h3>{t["rgpd_title"]}</h3>
        <p><strong>{t["rgpd_collected"]}</strong><br>
        {t["rgpd_fields"]}</p>
        <p><strong>{t["rgpd_usage"]}</strong></p>
        <p><strong>{t["rgpd_duration"]}</strong></p>
        <p><strong>{t["rgpd_rights"]}</strong>
        <a href='mailto:{t["rgpd_contact"]}'>{t["rgpd_contact"]}</a></p>
    </div>
</div>
""", height=300)
