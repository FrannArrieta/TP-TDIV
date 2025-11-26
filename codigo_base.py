from socket import *
import sys
import os
from urllib.parse import parse_qs, urlparse
import qrcode
import gzip

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

def leer_headers(conn):
    data = b""
    while b"\r\n\r\n" not in data:
        chunk = conn.recv(1024)
        if not chunk:
            break
        data += chunk

    # Separa headers y lo que ya es parte del body

    data_leida = data.split(b"\r\n\r\n", 1)
    header_bytes = data_leida[0]
    body_start = b""
    if(len(data_leida) > 1):
        body_start = data_leida[1]

    return header_bytes.decode(errors="ignore"), body_start

def leer_body(conn, content_length, body_start):
    body = body_start
    # Leer el resto del body si falta
    while len(body) < content_length:
        chunk = conn.recv(1024)
        if not chunk:
            break
        body += chunk
    return body

def extraer_boundary(headers):
    return headers.split("boundary=")[1].split("\r\n")[0]

def extraer_content_length(headers):
    return int(headers.split("Content-Length: ")[1].split("\r\n")[0])

def extraer_encoding_gzip(headers):
    return "Accept-Encoding: gzip" in headers

def generar_headers_http(body, codigo, archivo = None, incluir_gzip = False):
    response_headers = "HTTP/1.1" + codigo +  "\r\n"
    response_headers += f"Content-Length: {len(body)}\r\n"

    if archivo:
        response_headers += "Content-Type: application/octet-stream\r\n"
        response_headers += f'Content-Disposition: attachment; filename="{archivo}"\r\n'
    else:
        response_headers += "Content-Type: text/html\r\n"

    if incluir_gzip:
        response_headers += "Content-Encoding: gzip\r\n"
    
    response_headers += "\r\n"  # Separador entre headers and body
    
    return response_headers.encode() + body

def generar_respuesta_http(headers, body, modo_upload, tipo_req, ruta_pedida, archivo_pedido = None, usa_gzip = False):
    res = b""
    
    if(tipo_req == "GET"):
        if(ruta_pedida == "/" or ruta_pedida == "/favicon.ico"): # PREGUNTAR A EMI (o rafa)
            body = ""
            if modo_upload == True:
                body = generar_html_interfaz("upload")
            else:
                body = generar_html_interfaz("download")
            res = generar_headers_http(body.encode(), "200 OK")
        elif(ruta_pedida == "/download"):
            cliente_soporta_gzip = False
            if usa_gzip:
                cliente_soporta_gzip = extraer_encoding_gzip(headers)
            res = manejar_descarga(archivo_pedido, cliente_soporta_gzip)
        else:
            body = generar_pagina_error("404: NOT FOUND")
            res = generar_headers_http(body.encode(), "404 NOT FOUND")

    elif(tipo_req == "POST"):
        boundary = extraer_boundary(headers)
        res = manejar_carga(body, boundary, "archivos_servidor")

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

def leer_campo_contra(body, boundary): # EMI
    """Devuelve el valor del campo 'contra' asumiendo que body NO incluye los headers HTTP."""
    boundary_bytes = f'--{boundary}'.encode()
    parts = body.split(boundary_bytes)

    for part in parts:
        # Saltar partes vacías
        if not part.strip():
            continue

        # Buscar específicamente el campo `contra`
        if b'name="contra"' not in part:
            continue

        # Asumiendo que encontramos la parte correcta
        parte_con_contra = part.decode()
        contra_ingresada = parte_con_contra.split("\r\n\r\n")[1].split("\r\n")[0]
        return contra_ingresada

    return None

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
        <div>
            <label for="contra">Ingrese la contraseña: </label>
            <input type="password" name="contra" required>
        </div>
      <input type="file" name="file" required>
      <input type="submit" value="Subir">
    </form>
  </body>
</html>
"""

def generar_pagina_error(error):
    return f"""
<html>
  <head>
    <meta charset="utf-8">
    <title>Error</title>
    <style>
      body {{ font-family: sans-serif; max-width: 500px; margin: 50px auto; }}
      a {{ display: inline-block; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; }}
    </style>
  </head>
  <body>
    <h1>Ha ocurrido un error</h1>
    <p>{error}</p>
    <a href="/">Volver a inicio</a>
  </body>
</html>
"""

def generar_pagina_exito(nombre_archivo):
    return f"""
<html>
  <head>
    <meta charset="utf-8">
    <title>Subido con éxito</title>
    <style>
      body {{ font-family: sans-serif; max-width: 500px; margin: 50px auto; }}
      a {{ display: inline-block; padding: 10px 20px; background: #28a745; color: white; text-decoration: none; border-radius: 5px; }}
    </style>
  </head>
  <body>
    <h1>Se ha subido el archivo con éxito</h1>
    <p>Arhivo subido: {nombre_archivo}</p>
    <a href="/">Volver a inicio</a>
  </body>
</html>
"""

#CODIGO A COMPLETAR

def manejar_descarga(archivo, cliente_soporta_gzip):
    """
    Genera una respuesta HTTP con el archivo solicitado. 
    Si el archivo no existe debe devolver un error.
    Debe incluir los headers: Content-Type, Content-Length y Content-Disposition.
    """
    res = b""
    if os.path.isfile(archivo):
        body = b""
        with open(archivo, "rb") as f:     # rb = leer en binario
            body = f.read()
        
        if cliente_soporta_gzip:
            body = gzip.compress(body) # EMI
        res = generar_headers_http(body, "200 OK", os.path.basename(archivo), incluir_gzip=cliente_soporta_gzip)
    else:
        body = generar_pagina_error("404 NOT FOUND")
        res = generar_headers_http(body.encode(), "404 NOT FOUND")
    return res

def manejar_carga(body, boundary, directorio_destino="."):
    """
    Procesa un POST con multipart/form-data, guarda el archivo y devuelve una página de confirmación.
    """
    res = b""
    contra_ingresada = leer_campo_contra(body, boundary)
    CONTRASEÑA_SECRETA = "EMIYRAFA"
    if contra_ingresada != CONTRASEÑA_SECRETA:
        body = generar_pagina_error("403 FORBIDDEN")
        res = generar_headers_http(body.encode(), "403 FORBIDDEN")
        return res

    multipart = parsear_multipart(body, boundary)
    nombre_archivo = multipart[0]
    contenido = multipart[1]

    if(nombre_archivo is not None):
        print(nombre_archivo)
        ruta = directorio_destino + "/" + nombre_archivo

        f = open(ruta, "wb")
        f.write(contenido)
        f.close()

        body = generar_pagina_exito(nombre_archivo)
        res = generar_headers_http(body.encode(), "200 OK")
        

    return res


def start_server(archivo_descarga=None, modo_upload=False, usa_gzip = False):
    """
    Inicia el servidor TCP.
    - Si se especifica archivo_descarga, se inicia en modo 'download'.
    - Si modo_upload=True, se inicia en modo 'upload'.
    """

    # 1. Obtener IP local y poner al servidor a escuchar en un puerto aleatorio
    #COMPLETAR

    ip_server = get_wifi_ip()
    puerto = 5003
    print("arrancando el server en el puerto " + str(puerto) + " con ip " + ip_server + " con GZIP en: " + str(usa_gzip))

    # 2. Mostrar información del servidor y el código QR
    # COMPLETAR: imprimir URL y modo de operación (download/upload)
    url = "http://" + ip_server + ":" + str(puerto)
    if modo_upload == True: 
        print("Estas en modo Upload")
    else:
        print("Estas en modo Download")
    imprimir_qr_en_terminal(url)
    print(url)
    s = socket(AF_INET, SOCK_STREAM)
    s.bind((ip_server, puerto))
    
    s.listen()

    while True:
        conn, addr = s.accept() # Si queremos mantener abierto esto arriba
        headers, body_start = leer_headers(conn)
        print(headers.split("\r\n")[0])
        
        split_espacio = headers.split("\r\n")[0].split(" ")
        tipo_req = split_espacio[0]

        ruta_pedida = "/"
        if len(split_espacio) > 1:
            ruta_pedida = split_espacio[1]

        print(f"-- Request {tipo_req} {ruta_pedida} de {addr[0]} con socket {addr[1]}")
        body = b""

        if(tipo_req == "POST"):
            content_length = extraer_content_length(headers)
            body = leer_body(conn, content_length, body_start)

        res = generar_respuesta_http(headers, body, modo_upload, tipo_req, ruta_pedida, archivo_descarga, usa_gzip)
       
        conn.sendall(res)
        conn.close() # Y sacar esto para mantener abierto EMI

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso:")
        print("  python tp.py upload                    # Servidor para subir archivos")
        print("  python tp.py download archivo.txt      # Servidor para descargar un archivo")
        sys.exit(1)

    comando = sys.argv[1].lower()

    if comando == "upload":
        start_server(archivo_descarga=None, modo_upload=True, usa_gzip= False)

    elif comando == "download" and len(sys.argv) > 2:
        archivo = sys.argv[2]
        ruta_archivo = os.path.join("archivos_servidor", archivo)

        USA_GZIP = False
        if "--gzip" in sys.argv:
            USA_GZIP = True
        start_server(archivo_descarga=ruta_archivo, modo_upload=False, usa_gzip=USA_GZIP)

    else:
        print("Comando no reconocido o archivo faltante")
        sys.exit(1)
