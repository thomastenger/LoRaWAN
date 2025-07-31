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
import secrets
import string
import requests

# Configuration

api_token = st.secrets["CHIRPSTACK_API_TOKEN"]
device_profile_id = st.secrets["DEVICE_Profile_ID"] 

SMTP_SERVER = st.secrets["SMTP_SERVER"]
SMTP_PORT = int(st.secrets["SMTP_PORT"])
SMTP_LOGIN = st.secrets["SMTP_LOGIN"]
SMTP_PASSWORD = st.secrets["SMTP_PASSWORD"]
CHIRPSTACK_SERVER = st.secrets["CHIRPSTACK_SERVER"]


def create_user_and_app(email, tenant_id=st.secrets["TENANT_ID"], is_admin=False):

    api_token_admin = st.secrets["CHIRPSTACK_ADMIN_API_TOKEN"]
    auth_token = [("authorization", f"Bearer {api_token_admin}")]

    channel = grpc.insecure_channel(CHIRPSTACK_SERVER)
    user_client = api.UserServiceStub(channel)
    tenant_client = api.TenantServiceStub(channel)
    app_client = api.ApplicationServiceStub(channel)

    password = generate_secure_password()

    try:
        # Create User
        create_req = api.CreateUserRequest()
        create_req.user.email = email
        create_req.user.is_active = True
        create_req.user.is_admin = is_admin
        create_req.password = password
        user_client.Create(create_req, metadata=auth_token)

        list_req = api.ListUsersRequest(limit=100)
        resp = user_client.List(list_req, metadata=auth_token)
        user_id = next((u.id for u in resp.result if u.email == email), None)
        if not user_id:
            return False

        add_req = api.AddTenantUserRequest()
        add_req.tenant_user.CopyFrom(api.TenantUser(
            tenant_id=tenant_id,
            user_id=user_id,
            email=email,
            is_admin=False,
            is_device_admin=True,
            is_gateway_admin=False
        ))
        tenant_client.AddUser(add_req, metadata=auth_token)

        # Create ChirpStack App
        app_name = email.split("@")[0]
        app_req = api.CreateApplicationRequest()
        app_req.application.name = app_name
        app_req.application.description = f"Application for {email}"
        app_req.application.tenant_id = tenant_id
        app_req.application.tags["owner"] = email
        app_client.Create(app_req, metadata=auth_token)

        
        send_ok = send_password_email(email, password)
        if not send_ok:
            return True

    except grpc.RpcError as e:
        st.error(f"Error ChirpStack : {e.details()} (code: {e.code()})")
        return False


def user_exists(email):

    api_token_admin = st.secrets["CHIRPSTACK_ADMIN_API_TOKEN"]
    auth_token = [("authorization", f"Bearer {api_token_admin}")]
    channel = grpc.insecure_channel(CHIRPSTACK_SERVER)
    user_client = api.UserServiceStub(channel)

    try:
        req = api.ListUsersRequest(limit=1000)
        resp = user_client.List(req, metadata=auth_token)

        for user in resp.result:
            if user.email.lower() == email.lower():
                return True 
        return False
    except grpc.RpcError as e:
        st.error(f"Error verification of user : {e.details()} ({e.code()})")
        return False 



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

def get_application_id_by_email(email):

    api_token = st.secrets["CHIRPSTACK_API_TOKEN"]
    tenant_id = st.secrets["TENANT_ID"]
    auth_token = [("authorization", f"Bearer {api_token}")]

    channel = grpc.insecure_channel(CHIRPSTACK_SERVER)
    app_client = api.ApplicationServiceStub(channel)

    try:
        req = api.ListApplicationsRequest(limit=100, tenant_id=tenant_id)
        resp = app_client.List(req, metadata=auth_token)

        for app_item in resp.result:
            if not app_item.id:
                continue

            app_detail = app_client.Get(api.GetApplicationRequest(id=app_item.id), metadata=auth_token)
            owner = app_detail.application.tags.get("owner")
            if owner == email:
                return app_detail.application.id

        return None

    except grpc.RpcError as e:
        st.error(f"Error application: {e.details()} ({e.code()})")
        return None

def generate_secure_password(length=12):
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def send_password_email(to_email, password):
    subject = t["email_subject_password"]
    body = t["email_body_password"].format(email=to_email, password=password)

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
        st.error(f"Error send email : {e}")
        return False






# Traductions
translations = {
    "fr": {
        "title": "Vérification email & ajout device ChirpStack (OTAA)",
        "User_exist": "✅ Utilisateur existant, veuillez valider votre identité.",
        "email_label": "Adresse email",
        "unique_id": "Identifiant unique du device (16 caractères hexadécimaux, souvent fourni par le constructeur)",
        "name_device": "Nom libre du device (ex: capteur_temp_salon). Sert à l'identification dans ChirpStack",
        "App_keys": "Clé de sécurité (AppKey) utilisée pour l'authentification OTAA. 32 caractères hexadécimaux",
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
        "rgpd_contact": "contact@votresite.com",
        "email_subject_password": "Votre accès à la plateforme ChirpStack",
        "email_body_password": """Bonjour,

        Votre compte ChirpStack a bien été créé.

        Voici vos informations de connexion :
        📧 Email : {email}
        🔑 Mot de passe : {password}

        Merci d'utiliser notre service.

        L’équipe technique
        """
    },
    "en": {
        "title": "Email verification & ChirpStack device registration (OTAA)",
        "User_exist": "✅ Existing user, please verify your identity.",
        "name_device": "Free name for the device (e.g., living_room_temp_sensor). Used for identification in ChirpStack",
        "App_keys": "Security key (AppKey) used for OTAA authentication. 32 hexadecimal characters",
        "email_label": "Email address",
        "unique_id": "Unique device identifier (16 hexadecimal characters, often provided by the manufacturer)",
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
        "rgpd_contact": "contact@yourdomain.com",
        "email_subject_password": "Your ChirpStack platform access",
        "email_body_password": """Hello,

        Your ChirpStack account has been successfully created.

        Here are your login details:
        📧 Email: {email}
        🔑 Password: {password}

        Thank you for using our service.

        The technical team
        """
    },
    "sk": {
        "title": "Overenie e-mailu a pridanie zariadenia ChirpStack (OTAA)",
        "User_exist": "✅ Ak ste existujúci používateľ, potvrďte svoju identitu.",
        "email_label": "Emailová adresa",
        "unique_id": "Jedinečné identifikačné číslo zariadenia (16 hexadecimálnych znakov, často poskytované výrobcom)",
        "name_device": "Voľný názov zariadenia (napr.: senzor_temp_obývačka). Slúži na identifikáciu v ChirpStack",
        "App_keys": "Bezpečnostný kľúč (AppKey) používaný na autentifikáciu OTAA. 32 hexadecimálnych znakov",
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
        "rgpd_footer": "🔐 Používaním tejto aplikácie súhlasíte s našimi <a onclick=\"document.getElementById('rgpd-modal').style.display='block';\">zásadami ochrany osobných údajov</a>.",
        "rgpd_title": "Zásady ochrany osobných údajov",
        "rgpd_collected": "Zhromažďované údaje:",
        "rgpd_fields": "- Emailová adresa<br>- IP adresa<br>- Čas pripojenia",
        "rgpd_usage": "Použitie: na účely bezpečnosti, protokolovania a zlepšenia služby.",
        "rgpd_duration": "Uchovávanie: 6 mesiacov, potom vymazané.",
        "rgpd_rights": "Vaše práva: Žiadosť o prístup/vymazanie na:",
        "rgpd_contact": "kontakt@vasedomena.sk",
        "email_subject_password": "Váš prístup na platformu ChirpStack",
        "email_body_password": """Dobrý deň,

        Váš účet ChirpStack bol úspešne vytvorený.

        Tu sú vaše prihlasovacie údaje:
        📧 Email: {email}
        🔑 Heslo: {password}

        Ďakujeme, že používate naše služby.

        Technický tím
        """
    }
}


lang = st.sidebar.selectbox("🌐 Choisir la langue / Select language / Zvoliť jazyk", ["sk", "en", "fr"])
t = translations[lang]



if "email_verified" not in st.session_state:
    st.session_state.email_verified = False
if "otp_sent" not in st.session_state:
    st.session_state.otp_sent = False
if "generated_otp" not in st.session_state:
    st.session_state.generated_otp = ""
if "login_step" not in st.session_state:
    st.session_state.login_step = "start"  # start, otp, login, verified


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


st.title(t["title"])

email = st.text_input(t["email_label"])

if st.session_state.login_step == "start":
    if st.button(t["send_code"]):
        if user_exists(email):
            otp = f"{random.randint(100000, 999999)}"
            sent = send_otp_email(email, otp)
            if sent:
                st.session_state.generated_otp = otp
                st.session_state.email = email
                st.session_state.login_step = "login"
                st.success(t["code_sent"])
                st.rerun()    
        else:
            otp = f"{random.randint(100000, 999999)}"
            sent = send_otp_email(email, otp)
            if sent:
                st.session_state.generated_otp = otp
                st.session_state.email = email
                st.session_state.login_step = "otp"
                st.success(t["code_sent"])
                st.rerun()  

elif st.session_state.login_step == "login":
    st.info(t["User_exist"])
    otp_input = st.text_input(t["enter_code"])
    if st.button(t["verify_code"]):
        if otp_input == st.session_state.generated_otp:

            st.session_state.login_step = "verified"
            st.success(t["code_validated"])
        else:
            st.error(t["invalid_code"])
            log_api_usage(email, endpoint="failed_verification", status="fail connection")

elif st.session_state.login_step == "otp":
    otp_input = st.text_input(t["enter_code"])
    if st.button(t["verify_code"]):
        if otp_input == st.session_state.generated_otp:

            st.session_state.login_step = "verified"
            st.success(t["code_validated"])
            log_api_usage(email, endpoint="email_verification", status="success connection")
            created = create_user_and_app(st.session_state.email)
            if not created:
                st.stop()
        else:
            st.error(t["invalid_code"])
            log_api_usage(email, endpoint="failed_verification", status="fail connection")


if st.session_state.login_step == "verified":
    st.subheader(t["add_device"])
    with st.form("add_device_form"):
        dev_eui = st.text_input(t["dev_eui_label"], max_chars=16, help=t["unique_id"])
        dev_name = st.text_input(t["device_name_label"], help=t["name_device"])
        app_key = st.text_input(t["app_key_label"], max_chars=32, help=t["App_keys"])
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
                    channel = grpc.insecure_channel(CHIRPSTACK_SERVER)
                    client = api.DeviceServiceStub(channel)
                    metadata = [("authorization", f"Bearer {api_token}")]

                    device = api.Device()
                    device.dev_eui = dev_eui
                    device.name = dev_name
                    user_app_id = get_application_id_by_email(st.session_state.email)
                    if not user_app_id:
                        st.stop()
                    device.application_id = user_app_id
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
