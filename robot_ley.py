import os
import time
import threading
import gdown
import requests
from flask import Flask
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select

# Servidor Flask para mantener activo el Web Service gratuito en Render
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot de Facturación Casa Ley activo y escuchando en Telegram."

# ==========================================
# CONFIGURACIÓN Y CREDENCIALES DE ACCESO
# ==========================================
url_carpeta_drive = "https://drive.google.com/drive/folders/1NyQsqPhdMIdVOtfAuIqb-PZstNW-C0Cw"
carpeta_local_descarga = "temp_facturas_drive"

url_portal = "https://aplicaciones.casaley.com.mx/cfacturaweb/"
url_carga = "https://aplicaciones.casaley.com.mx/CFacturaWeb/Facturas/CargaFactura.aspx"
correo_fijo = "anaisabelpv_@hotmail.com"

# Credenciales de Casa Ley
USUARIO_LEY = "PAVA690703MV1"
CONTRASENA_LEY = "PAV5792T"

# Credenciales del Bot de Telegram
TELEGRAM_TOKEN = "8890020053:AAEDQHgYhw1ZzvWuuxARhH8JkqwWv1Lky24"
TELEGRAM_CHAT_ID = "5223754610"

def enviar_mensaje_telegram(mensaje):
    """Envía una notificación directamente a tu Telegram."""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": mensaje,
            "parse_mode": "Markdown"
        }
        requests.post(url, json=payload)
    except Exception as e:
        print(f"⚠️ No se pudo enviar el mensaje a Telegram: {e}")

def crear_driver_navegador():
    """Configura Chrome para correr en la nube de forma invisible."""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    
    driver = webdriver.Chrome(options=options)
    return driver

def descargar_archivos_de_google_drive():
    print("☁ Conectando con Google Drive para descargar los archivos...")
    os.makedirs(carpeta_local_descarga, exist_ok=True)
    try:
        gdown.download_folder(url_carpeta_drive, output=carpeta_local_descarga, quiet=False, use_cookies=False)
        print("✔ ¡Archivos descargados con éxito desde Google Drive!")
        return True
    except Exception as e:
        print(f"❌ Error al descargar de Google Drive: {e}")
        return False

def realizar_login_automatico(driver):
    """Inicia sesión automáticamente en el portal de Casa Ley."""
    try:
        print("🔐 Iniciando sesión automáticamente en Casa Ley...")
        driver.get(url_portal)
        wait = WebDriverWait(driver, 20)

        campo_usuario = wait.until(EC.presence_of_element_located((By.ID, "txtLogin_us")))
        campo_usuario.clear()
        campo_usuario.send_keys(USUARIO_LEY)
        time.sleep(1)

        campo_pass = wait.until(EC.presence_of_element_located((By.ID, "txtLogin_pa")))
        campo_pass.clear()
        campo_pass.send_keys(CONTRASENA_LEY)
        time.sleep(1)

        btn_ingresar = wait.until(EC.element_to_be_clickable((By.ID, "btnLogin")))
        btn_ingresar.click()
        time.sleep(3)

        print("✔ ¡Sesión iniciada con éxito en la nube!")
        return True
    except Exception as e:
        print(f"❌ Error durante el login automático: {e}")
        enviar_mensaje_telegram("❌ *Error:* El robot falló al intentar iniciar sesión en la nube.")
        return False

def ejecutar_proceso_facturacion():
    """Ejecuta todo el flujo automatizado levantando un navegador temporal."""
    driver = crear_driver_navegador()
    try:
        if not realizar_login_automatico(driver):
            return

        if not descargar_archivos_de_google_drive():
            enviar_mensaje_telegram("❌ *Error:* El robot no pudo descargar los archivos de Google Drive.")
            return

        archivo_pedidos = os.path.join(carpeta_local_descarga, "pedidos.txt")
        carpeta_xmls = carpeta_local_descarga

        if not os.path.exists(archivo_pedidos):
            for item in os.listdir(carpeta_local_descarga):
                sub_path = os.path.join(carpeta_local_descarga, item)
                if os.path.isdir(sub_path):
                    posible_txt = os.path.join(sub_path, "pedidos.txt")
                    if os.path.exists(posible_txt):
                        archivo_pedidos = posible_txt
                        carpeta_xmls = sub_path
                        break

        if not os.path.exists(archivo_pedidos):
            print(f"❌ No se encontró el archivo 'pedidos.txt'.")
            enviar_mensaje_telegram("❌ *Error:* No se encontró el archivo `pedidos.txt` en Google Drive.")
            return

        enviar_mensaje_telegram("🚀 *El robot en la nube ha iniciado.* Procesando facturas...")

        with open(archivo_pedidos, "r", encoding="utf-8") as f:
            lineas = f.readlines()

        wait = WebDriverWait(driver, 30)
        reporte_final = "📊 *Reporte de Facturas Casa Ley (Nube):*\n\n"

        for linea in lineas:
            linea = linea.strip()
            if not linea:
                continue
            
            partes = linea.split()
            if len(partes) < 2:
                continue
                
            num_factura = ''.join(c for c in partes[0] if c.isalnum())
            num_pedido = ''.join(c for c in partes[1] if c.isdigit())

            if not num_factura or not num_pedido:
                continue

            try:
                driver.get(url_carga)
                time.sleep(2)

                xml_encontrado = None
                for archivo in os.listdir(carpeta_xmls):
                    if num_factura.lower() in archivo.lower() and archivo.endswith(".xml"):
                        xml_encontrado = os.path.join(carpeta_xmls, archivo)
                        break
                
                if not xml_encontrado:
                    reporte_final += f"❌ `{num_factura}`: XML no encontrado en Drive\n"
                    continue

                xml_encontrado = os.path.abspath(xml_encontrado)

                input_archivo = wait.until(EC.presence_of_element_located((By.ID, "ContentPlaceHolder1_File1")))
                input_archivo.send_keys(xml_encontrado)
                time.sleep(2)

                btn_servicios = wait.until(EC.element_to_be_clickable((By.ID, "ContentPlaceHolder1_btnServicios")))
                btn_servicios.click()
                time.sleep(3)

                radio_sistema = wait.until(EC.element_to_be_clickable((By.ID, "ContentPlaceHolder1_RaBuSistema")))
                radio_sistema.click()
                time.sleep(1)

                select_proveedor = Select(wait.until(EC.presence_of_element_located((By.ID, "ContentPlaceHolder1_ListProSap"))))
                select_proveedor.select_by_value("2")
                time.sleep(1)

                campo_pedido = wait.until(EC.presence_of_element_located((By.ID, "ContentPlaceHolder1_TxBxNumPedido")))
                campo_pedido.clear()
                campo_pedido.send_keys(num_pedido)
                time.sleep(1)

                btn_validar = wait.until(EC.element_to_be_clickable((By.ID, "ContentPlaceHolder1_lnkbtnValidarPedido")))
                btn_validar.click()

                time.sleep(2.5)

                pedido_con_error = False
                try:
                    modal_alerta = WebDriverWait(driver, 2).until(
                        EC.visibility_of_element_located((By.ID, "ContentPlaceHolder1_lblModalBodySalir"))
                    )
                    texto_alerta = modal_alerta.text.strip()
                    
                    if "no valido" in texto_alerta.lower() or "favor de verificar" in texto_alerta.lower() or "error" in texto_alerta.lower():
                        reporte_final += f"❌ `{num_factura}`: Pedido no válido\n"
                        pedido_con_error = True
                        
                        try:
                            btn_cerrar_error = wait.until(EC.element_to_be_clickable((By.ID, "ContentPlaceHolder1_BtnCerrar")))
                            btn_cerrar_error.click()
                            time.sleep(1)
                        except:
                            pass

                        try:
                            logo_inicio = wait.until(EC.element_to_be_clickable((By.ID, "imgLogoSistema")))
                            logo_inicio.click()
                            time.sleep(2)
                        except:
                            pass
                except:
                    pass

                if pedido_con_error:
                    continue

                chk_centro = wait.until(EC.element_to_be_clickable((By.ID, "ContentPlaceHolder1_chkCentro")))
                chk_centro.click()
                time.sleep(1.5)

                campo_correo = wait.until(EC.presence_of_element_located((By.ID, "ContentPlaceHolder1_TxBxCorreo")))
                campo_correo.clear()
                campo_correo.send_keys(correo_fijo)
                time.sleep(1)

                btn_aceptar = wait.until(EC.element_to_be_clickable((By.ID, "ContentPlaceHolder1_btnAceptar")))
                btn_aceptar.click()
                
                time.sleep(2)
                try:
                    lbl_modal = WebDriverWait(driver, 6).until(
                        EC.presence_of_element_located((By.ID, "ContentPlaceHolder1_lblModalBodySalir"))
                    )
                    mensaje_sistema = lbl_modal.text.strip()

                    if "ya se encuentra en la Base de Datos" in mensaje_sistema:
                        reporte_final += f"🔵 `{num_factura}`: Factura ya registrada\n"
                    elif "valido" in mensaje_sistema.lower() or "exito" in mensaje_sistema.lower() or "correcto" in mensaje_sistema.lower():
                        reporte_final += f"✅ `{num_factura}`: Subida con éxito\n"
                    else:
                        reporte_final += f"📢 `{num_factura}`: {mensaje_sistema}\n"

                    btn_cerrar = wait.until(EC.element_to_be_clickable((By.ID, "ContentPlaceHolder1_BtnCerrar")))
                    btn_cerrar.click()
                except Exception as ex:
                    reporte_final += f"✅ `{num_factura}`: Procesada correctamente\n"

                time.sleep(2)

            except Exception as e:
                reporte_final += f"❌ `{num_factura}`: Error técnico\n"

        reporte_final += "\n🏁 Proceso de facturación en la nube concluido."
        enviar_mensaje_telegram(reporte_final)

    finally:
        driver.quit()

def escuchar_telegram():
    """Mantiene el bot en la nube escuchando comandos."""
    print("🤖 ¡Robot en la nube iniciado y escuchando Telegram!")
    enviar_mensaje_telegram("🤖 *¡Robot en la nube en línea (Gratis)!* Mándame `/facturar` cuando gustes.")

    offset = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={offset}&timeout=30"
            response = requests.get(url)
            data = response.json()

            if data.get("ok") and data.get("result"):
                for update in data["result"]:
                    offset = update["update_id"] + 1
                    
                    if "message" in update and "text" in update["message"]:
                        chat_id_remitente = str(update["message"]["chat"]["id"])
                        texto_mensaje = update["message"]["text"].strip().lower()

                        if chat_id_remitente == TELEGRAM_CHAT_ID:
                            if texto_mensaje == "/facturar":
                                enviar_mensaje_telegram("🔄 *Orden recibida.* Conectando al portal...")
                                ejecutar_proceso_facturacion()
                            elif texto_mensaje == "/start":
                                enviar_mensaje_telegram("👋 ¡Hola desde la nube! Usa `/facturar` para ejecutar las facturas.")
        except Exception as e:
            print(f"⚠️ Error al consultar Telegram: {e}")
            time.sleep(5)
        
        time.sleep(2)

if __name__ == "__main__":
    # Iniciar el bot de Telegram en un hilo secundario
    hilo_bot = threading.Thread(target=escuchar_telegram)
    hilo_bot.daemon = True
    hilo_bot.start()

    # Iniciar Flask en el puerto que asigna Render de manera gratuita
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
