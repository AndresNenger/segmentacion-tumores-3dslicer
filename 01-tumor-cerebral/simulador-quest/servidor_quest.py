"""Servidor HTTPS local para abrir Craniotomy Trainer XR en el navegador de Meta Quest 3.
Uso:  python servidor_quest.py      (el PC y las Quest deben estar en la misma red Wi-Fi)
WebXR solo funciona en contexto seguro (HTTPS). El certificado es autofirmado: la primera vez el navegador
de las Quest mostrara un aviso; elige "Avanzado" > "Continuar". Pulsa Ctrl+C para detener."""
import http.server, ssl, socket, os, functools

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = 8443


def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map, ".glb": "model/gltf-binary", ".json": "application/json", ".js": "text/javascript"}

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


httpd = http.server.ThreadingHTTPServer(("0.0.0.0", PORT), functools.partial(Handler, directory=HERE))
ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ctx.load_cert_chain(os.path.join(HERE, "cert.pem"), os.path.join(HERE, "key.pem"))
httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
print("Craniotomy Trainer XR")
print("  En las Meta Quest 3 abre:  https://%s:%d/index.html" % (lan_ip(), PORT))
print("  En este PC:               https://localhost:%d/index.html" % PORT)
print("Ctrl+C para detener.")
httpd.serve_forever()
