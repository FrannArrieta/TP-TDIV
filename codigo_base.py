from socket import *
import sys
import os
from urllib.parse import parse_qs, urlparse
import qrcode


#FUNCIONES AUXILIARES

def imprimir_qr_en_terminal(url):
    """Dada una URL la imprime por terminal como un QR"""
    #COMPLETAR usando la librería qrcode
    qr = qrcode.QRCode(border=1)
    qr.add_data(url)
    qr.make()

    qr.print_ascii()
    

def get_wifi_ip():
    """Obtiene la IP local asociada a la interfaz de red (por ejemplo, Wi-Fi)."""
    s = socket(AF_INET, SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip #Devuelve la IP como string

def extraer_boundary(headers):
    return headers.split("boundary=")[1].split("\r\n")[0]

def extraer_content_length(headers):
    return int(headers.split("\r\n")[3].split(" ")[1])

def generar_headers_http(body, codigo):
    response_headers = "HTTP/1.1" + codigo +  "\r\n"
    response_headers += "Content-Type: text/html\r\n"
    response_headers += f"Content-Length: {len(body)}\r\n"
    response_headers += "\r\n"  # Separator between headers and body

    full_response = (response_headers + body)
    return full_response

def generar_respuesta_http(headers, body, modo_upload, tipo_req):
    res = ""
    
    if(tipo_req == "GET"):
        body = ""
        if modo_upload == True:
            body = generar_html_interfaz("upload")
        else:
            body = generar_html_interfaz("download")
        res = generar_headers_http(body, "200 OK")
    elif(tipo_req == "POST"):
        boundary = extraer_boundary(headers)
        manejar_carga(body, boundary, "archivos_servidor")

    return res

def parsear_multipart(body, boundary):
    """Función auxiliar (ya implementada) para parsear multipart/form-data."""
    try:
        # Se divide el cuerpo por el boundary para luego poder extraer el nombre y contenido del archivo
        parts = body.split(f'--{boundary}'.encode())
        for part in parts:
            if b'filename=' in part:
                # Se extrae el nombre del archivo
                filename_start = part.find(b'filename="') + len(b'filename="')
                filename_end = part.find(b'"', filename_start)
                filename = part[filename_start:filename_end].decode()

                # Se extrae el contenido del archivo que arranca después de los headers
                header_end = part.find(b'\r\n\r\n')
                if header_end == -1:
                    header_end = part.find(b'\n\n')
                    content_start = header_end + 2
                else:
                    content_start = header_end + 4

                # El contenido va hasta el último CRLF antes del boundary
                content_end = part.rfind(b'\r\n')
                if content_end <= content_start:
                    content_end = part.rfind(b'\n')

                file_content = part[content_start:content_end]
                if filename and file_content:
                    return filename, file_content
        return None, None
    except Exception as e:
        print(f"Error al parsear multipart: {e}")
        return None, None

def generar_html_interfaz(modo):
    """
    Genera el HTML de la interfaz principal:
    - Si modo == 'download': incluye un enlace o botón para descargar el archivo.
    - Si modo == 'upload': incluye un formulario para subir un archivo.
    """
    if modo == 'download':
        return """
<html>
  <head>
    <meta charset="utf-8">
    <title>Descargar archivo</title>
    <style>
      body { font-family: sans-serif; max-width: 500px; margin: 50px auto; }
      a { display: inline-block; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; }
    </style>
  </head>
  <body>
    <h1>Descargar archivo</h1>
    <p>Haz click en el botón para descargar:</p>
    <a href="/download">Descargar archivo</a>
  </body>
</html>
"""
    
    else:  # upload
        return """
<html>
  <head>
    <meta charset="utf-8">
    <title>Subir archivo</title>
    <style>
      body { font-family: sans-serif; max-width: 500px; margin: 50px auto; }
      form { border: 2px dashed #ccc; padding: 20px; border-radius: 5px; }
      input[type="submit"] { padding: 10px 20px; background: #28a745; color: white; border: none; border-radius: 5px; cursor: pointer; }
    </style>
  </head>
  <body>
    <h1>Subir archivo</h1>
    <form method="POST" enctype="multipart/form-data">
      <input type="file" name="file" required>
      <input type="submit" value="Subir">
    </form>
  </body>
</html>
"""



#CODIGO A COMPLETAR

def manejar_descarga(archivo, request_line):
    """
    Genera una respuesta HTTP con el archivo solicitado. 
    Si el archivo no existe debe devolver un error.
    Debe incluir los headers: Content-Type, Content-Length y Content-Disposition.
    """
    # COMPLETAR
    return b""


def manejar_carga(body, boundary, directorio_destino="."):
    """
    Procesa un POST con multipart/form-data, guarda el archivo y devuelve una página de confirmación.
    """
    multipart = parsear_multipart(body, boundary)

    nombre_archivo = multipart[0]
    contenido = multipart[1]

    print(nombre_archivo)
    ruta = directorio_destino + "/" + nombre_archivo

    f = open(ruta, "wb")
    f.write(contenido)
    f.close()

    return b""


def start_server(archivo_descarga=None, modo_upload=False):
    """
    Inicia el servidor TCP.
    - Si se especifica archivo_descarga, se inicia en modo 'download'.
    - Si modo_upload=True, se inicia en modo 'upload'.
    """

    # 1. Obtener IP local y poner al servidor a escuchar en un puerto aleatorio
    #COMPLETAR

    ip_server = get_wifi_ip()
    puerto = 5003
    print("arrancando el server en el puerto " + str(puerto) + " con ip " + ip_server)

    # 2. Mostrar información del servidor y el código QR
    # COMPLETAR: imprimir URL y modo de operación (download/upload)
    url = "http://" + ip_server + ":" + str(puerto)
    if modo_upload == True: 
        print("Estas en modo Upload")
    else:
        print("Estas en modo Download")
    imprimir_qr_en_terminal(url)
    print(url)

    while True:
        s = socket(AF_INET, SOCK_STREAM)
        s.bind((ip_server, puerto))
        s.listen()

        # 3. Esperar conexiones y atender un cliente
        # COMPLETAR:
        # - aceptar la conexión (accept)
        conn, addr = s.accept()

        # - recibir los datos (recv)
        print(f"Connected by {addr}")
        headers = b""
        while b"\r\n\r\n" not in headers:
            chunk = conn.recv(1024)
            if not chunk:
                break
            headers += chunk

        headers = headers.decode(errors="ignore")
        tipo_req = headers.split("\r\n")[0].split(" ")[0]
        body = b""

        if(tipo_req == "POST"):
            content_length = extraer_content_length(headers)
            # Leer el resto del body si falta
            while len(body) < content_length:
                chunk = conn.recv(1024)
                if not chunk:
                    break
                body += chunk

        res = generar_respuesta_http(headers, body, modo_upload, tipo_req)
       
        conn.sendall(res.encode('utf-8'))
            

        # - decodificar la solicitud HTTP
        # - determinar método (GET/POST) y ruta (/ o /download)
        # - generar la respuesta correspondiente (HTML o archivo)
        # - enviar la respuesta al cliente
        # - cerrar la conexión
   

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso:")
        print("  python tp.py upload                    # Servidor para subir archivos")
        print("  python tp.py download archivo.txt      # Servidor para descargar un archivo")
        sys.exit(1)

    comando = sys.argv[1].lower()

    if comando == "upload":
        start_server(archivo_descarga=None, modo_upload=True)

    elif comando == "download" and len(sys.argv) > 2:
        archivo = sys.argv[2]
        ruta_archivo = os.path.join("archivos_servidor", archivo)
        start_server(archivo_descarga=ruta_archivo, modo_upload=False)

    else:
        print("Comando no reconocido o archivo faltante")
        sys.exit(1)
