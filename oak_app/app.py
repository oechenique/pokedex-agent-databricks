"""Esqueleto Streamlit para validar el auth app-to-app automatico contra
pokedex-mcp-server, ANTES de portar el resto de la UI (reglas/07-estado-
actual.md -- reemplaza el intento de Vercel, bloqueado por un 401 de
propagacion M2M del lado de Databricks).

WorkspaceClient() sin credenciales explicitas usa el service principal
propio de ESTA app, inyectado automaticamente por la plataforma cuando
corre como Databricks App -- patron oficial de Databricks para una app
llamando a otra app, distinto al M2M externo (client_id/secret propios)
que fallo desde Vercel. Si esto funciona, se esquivo el problema; si da
el mismo 401 con body vacio, es un bloqueo mas amplio de Databricks
Apps, no especifico de Vercel.
"""

import os

import requests
import streamlit as st
from databricks.sdk import WorkspaceClient

MCP_SERVER_URL = os.environ.get(
    "MCP_SERVER_URL",
    "https://pokedex-mcp-server-7405616363788532.12.azure.databricksapps.com",
)

st.title("Profesor Oak -- esqueleto de validación de auth")
st.caption(
    "Un solo botón: confirma si WorkspaceClient() sin credenciales explícitas "
    "autentica contra pokedex-mcp-server (auth app-to-app automática)."
)

if st.button("Probar auth app-to-app"):
    with st.spinner("Autenticando y llamando a pokedex-mcp-server..."):
        try:
            wc = WorkspaceClient()
            headers = wc.config.authenticate()
            headers["Content-Type"] = "application/json"
            headers["Accept"] = "application/json, text/event-stream"
            resp = requests.post(
                f"{MCP_SERVER_URL}/mcp",
                headers=headers,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-06-18",
                        "capabilities": {},
                        "clientInfo": {"name": "pokedex-oak-app", "version": "0.1.0"},
                    },
                },
                timeout=15,
            )
        except Exception as e:
            st.error(f"Excepción antes de recibir respuesta: {e!r}")
        else:
            st.write("Status:", resp.status_code)
            st.code(resp.text[:1000] or "(body vacío)")
            if resp.status_code == 200:
                st.success("Auth app-to-app funcionó -- pokedex-mcp-server aceptó el token.")
            else:
                st.error("Sigue fallando -- mismo síntoma que Vercel, no se esquivó el problema.")
