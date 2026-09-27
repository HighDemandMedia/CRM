#!/usr/bin/env python3
"""One-time desktop OAuth setup. Saves private Render variables, never prints secrets.

Uses only the Python standard library; no CRM database or running server is needed.
"""

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"
SCOPES = f"{SEND_SCOPE} openid email"


def read_json(url, data=None, headers=None):
    request = urllib.request.Request(url, data=data, headers=headers or {})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def private_output(path, values):
    """Exclusive creation avoids overwriting another connection or following a symlink."""
    path = Path(path).expanduser().resolve()
    repo = Path(__file__).resolve().parent.parent
    if path == repo or repo in path.parents:
        raise ValueError("Guarda las credenciales fuera del repositorio.")
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    content = "".join(f"{key}={json.dumps(value)}\n" for key, value in values.items())
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as output:
        output.write(content)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--credentials", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--sender", default="info@highdemandmedia.com")
    args = parser.parse_args()
    if args.output.expanduser().exists():
        raise ValueError("El archivo de salida ya existe; elige otro nombre para renovarlo.")
    client = json.loads(args.credentials.expanduser().read_text()).get("installed", {})
    if not client.get("client_id") or not client.get("client_secret"):
        raise ValueError("Selecciona el JSON de un cliente OAuth de tipo Desktop app.")
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    result = {}

    class Callback(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass  # The callback URL contains an authorization code.

        def do_GET(self):
            url = urllib.parse.urlsplit(self.path)
            query = urllib.parse.parse_qs(url.query)
            if url.path != "/oauth/callback":
                self.send_error(404)
                return
            if not secrets.compare_digest(query.get("state", [""])[0], state):
                self.send_error(400, "Invalid authorization state")
                return
            if query.get("error"):
                result["error"] = True
            elif query.get("code"):
                result["code"] = query["code"][0]
            else:
                self.send_error(400, "Missing authorization code")
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.end_headers()
            self.wfile.write(
                b"<!doctype html><title>High Demand Media CRM</title>"
                b"<h1>Respuesta de Google recibida</h1>"
                b"<p>Puedes cerrar esta ventana y volver a Codex para comprobar el resultado.</p>"
            )

    with HTTPServer(("127.0.0.1", 0), Callback) as server:
        server.timeout = 1
        redirect_uri = f"http://127.0.0.1:{server.server_port}/oauth/callback"
        params = {
            "client_id": client["client_id"], "redirect_uri": redirect_uri,
            "response_type": "code", "scope": SCOPES, "state": state,
            "code_challenge": challenge, "code_challenge_method": "S256",
            "access_type": "offline", "prompt": "consent",
            "login_hint": args.sender,
        }
        auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)
        print("Abriendo Google. Autoriza el envio de correo con " + args.sender + ".", flush=True)
        if not webbrowser.open(auth_url):
            print("Abre este enlace en tu navegador:\n" + auth_url, flush=True)
        deadline = time.monotonic() + 600
        while not result and time.monotonic() < deadline:
            server.handle_request()
    if not result.get("code"):
        raise ValueError("Autorizacion cancelada o tiempo agotado. Puedes intentarlo de nuevo.")
    token = read_json(
        "https://oauth2.googleapis.com/token",
        urllib.parse.urlencode({
            "client_id": client["client_id"], "client_secret": client["client_secret"],
            "code": result["code"], "redirect_uri": redirect_uri,
            "grant_type": "authorization_code", "code_verifier": verifier,
        }).encode(),
        {"Content-Type": "application/x-www-form-urlencoded"},
    )
    if not token.get("refresh_token") or SEND_SCOPE not in token.get("scope", "").split():
        raise ValueError("Google no concedio envio de correo y acceso continuo. Repite la autorizacion.")
    # Userinfo validates the selected identity over HTTPS without reading mail.
    identity = read_json(
        "https://openidconnect.googleapis.com/v1/userinfo",
        headers={"Authorization": "Bearer " + token["access_token"]},
    )
    if identity.get("email_verified") is not True or identity.get("email", "").casefold() != args.sender.casefold():
        raise ValueError("La cuenta autorizada no coincide con el remitente. No se guardaron credenciales.")
    path = private_output(args.output, {
        "EMAIL_BACKEND": "common.gmail_backend.GmailEmailBackend",
        "DEFAULT_FROM_EMAIL": f"High Demand Media CRM <{args.sender}>",
        "GMAIL_SYSTEM_SENDER": args.sender,
        "GMAIL_SYSTEM_CLIENT_ID": client["client_id"],
        "GMAIL_SYSTEM_CLIENT_SECRET": client["client_secret"],
        "GMAIL_SYSTEM_REFRESH_TOKEN": token["refresh_token"],
    })
    print(f"Cuenta verificada: {args.sender}. Configuracion privada guardada en {path}")
    print("No se ha enviado ningun correo. No subas este archivo a GitHub.")


if __name__ == "__main__":
    try:
        main()
    except (urllib.error.URLError, OSError, ValueError, KeyError):
        # Do not print third-party exceptions: they may contain codes or tokens.
        print("No se completo la conexion. Revisa el archivo Desktop app, la cuenta autorizada, los permisos y la conexion a internet.")
        raise SystemExit(1) from None
