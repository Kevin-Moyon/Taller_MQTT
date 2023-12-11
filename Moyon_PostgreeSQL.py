import psutil
import paho.mqtt.client as mqtt
import time
import smtplib
import psycopg2  # Asegúrate de tener instalado psycopg2

# Configuración de MQTT a través de WebSockets
mqtt_broker = "mqtt-dashboard.com"
mqtt_port = 8884
mqtt_topic = "Prueba"

# Configuración de PostgreSQL
pg_host = "localhost"
pg_port = 5432
pg_user = "KevinJoel"
pg_password = "Centrales1930"
pg_database = "Rendimientos"

# Configurar los detalles del servidor SMTP de Hotmail
smtp_server = "smtp-mail.outlook.com"
smtp_port = 587  # Puerto de SMTP
sender_email = "cnff001@hotmail.com"
password = "Cuentanueva2023"

# Crear el objeto SMTP
server = smtplib.SMTP(smtp_server, smtp_port)
server.starttls()
server.login(sender_email, password)

# Conectar a PostgreSQL
try:
    pg_conn = psycopg2.connect(
        host=pg_host,
        port=pg_port,
        user=pg_user,
        password=pg_password,
        database=pg_database
    )
    pg_cursor = pg_conn.cursor()

except psycopg2.Error as e:
    print(f"Error al conectar a PostgreSQL: {e}")
    exit()


# Función de callback cuando se conecta al broker MQTT
def on_connect(client, userdata, flags, rc):
    print(f"Conectado al broker MQTT con resultado {rc}")


# Función de callback cuando se publica un mensaje
def on_publish(client, userdata, mid):
    print(f"Mensaje publicado con éxito")


# Función para enviar correo electrónico
def enviar_correo():
    uso_memoria = psutil.virtual_memory().percent
    if uso_memoria > 60:
        message = f"El rendimiento de la MEMORIA es: {uso_memoria}%"
        receiver_email = "kevincitojoel@outlook.es"
        subject = "Advertencia: Rendimiento de la MEMORIA"
        body = f"Subject: {subject}\n\n{message}"

        # Enviar el mensaje de correo electrónico
        server.sendmail(sender_email, receiver_email, body)
        print("Correo electrónico enviado exitosamente!")


# Función para comparar metadatos y mostrar la diferencia en la consola de PyCharm y en MQTT
def comparar_metadatos(client1, client2):
    metadata1 = obtener_metadatos(client1)
    metadata2 = obtener_metadatos(client2)

    claves_relevantes = ["Rendimiento de la RED", "Porcentaje de Memoria Usada", "Rendimiento de la PC"]

    diferencia = {}

    for clave in claves_relevantes:
        valor1 = metadata1.get(clave)
        valor2 = metadata2.get(clave)

        if valor1 is not None and valor2 is not None and valor1 != valor2:
            diferencia[clave] = f"{valor1} (Cliente 1) - {valor2} (Cliente 2)"

    # Imprimir la diferencia en la consola de PyCharm
    print("Diferencia de metadatos:")
    for clave, valor in diferencia.items():
        print(f"{clave}: {valor}")

    # Publicar la diferencia en MQTT
    for clave, valor in diferencia.items():
        mensaje_diferencia = f"Diferencia de metadatos - {clave}: {valor}"
        client1.publish(mqtt_topic, mensaje_diferencia)
        print(mensaje_diferencia)


# Función para obtener metadatos específicos del sistema
def obtener_metadatos(client):
    memoria_disponible = psutil.virtual_memory().available / (1024 * 1024)
    memoria_usada = psutil.virtual_memory().percent

    try:
        temperatura_cpu = psutil.sensors_temperatures()['coretemp'][0].current
    except AttributeError:
        temperatura_cpu = "No disponible en esta plataforma"

    # Obtener estadísticas de la interfaz de red
    estadisticas_red = psutil.net_io_counters()
    rendimiento_mb = estadisticas_red.bytes_sent / (1024 * 1024)

    return {
        "Rendimiento de la RED": rendimiento_mb,
        "Porcentaje de Memoria Usada": memoria_usada,
        "Rendimiento de la PC": temperatura_cpu
    }


# Función para insertar datos en PostgreSQL
def insertar_datos_postgresql(metadata_actual):
    try:
        query = "INSERT INTO tabla_datos (clave, valor) VALUES (%s, %s);"
        for clave, valor in metadata_actual.items():
            pg_cursor.execute(query, (clave, valor))

        pg_conn.commit()
        print("Datos insertados en PostgreSQL correctamente!")

    except psycopg2.Error as e:
        print(f"Error al insertar datos en PostgreSQL: {e}")


# Crear un cliente MQTT con soporte de WebSockets
client = mqtt.Client(transport="websockets")

# Configurar las funciones de callback
client.on_connect = on_connect
client.on_publish = on_publish

# Conectar al broker MQTT a través de WebSockets
client.tls_set()  # Habilitar el cifrado TLS
client.connect(mqtt_broker, mqtt_port, 60)

# Esperar a que la conexión se establezca
client.loop_start()
time.sleep(1)

# Obtener y mostrar metadatos del cliente actual
metadata_actual = obtener_metadatos(client)
print("Metadatos actuales:")
for clave, valor in metadata_actual.items():
    print(f"{clave}: {valor}")

# Enviar correo electrónico
enviar_correo()

# Mostrar la diferencia entre metadatos en la consola de PyCharm y publicar en MQTT
comparar_metadatos(client, client)

# Insertar metadatos en PostgreSQL
insertar_datos_postgresql(metadata_actual)

# Publicar metadatos en el servidor MQTT
mensaje_metadata = "\n".join([f"{clave}: {valor}" for clave, valor in metadata_actual.items()])
client.publish(mqtt_topic, mensaje_metadata)

# Esperar un momento antes de cerrar la conexión MQTT
time.sleep(1)

# Detener el bucle de eventos y cerrar la conexión MQTT
client.loop_stop()
client.disconnect()

# Cerrar la conexión SMTP
server.quit()

# Cerrar la conexión PostgreSQL
pg_cursor.close()
pg_conn.close()
