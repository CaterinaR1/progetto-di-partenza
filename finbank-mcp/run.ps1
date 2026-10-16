# Avvio in streamable-http per l'Inspector col browser (Windows).
# Bind su 127.0.0.1: vedi run.sh per la ragione del fix.
# L'avvio normale (OpenCode / Inspector CLI) e' la stdio: python finbank-mcp/server.py

$env:LIPARIBANK_USERNAME = if ($env:LIPARIBANK_USERNAME) { $env:LIPARIBANK_USERNAME } else { "svc_mcp" }
if (-not $env:LIPARIBANK_PASSWORD) {
    Write-Error "Imposta LIPARIBANK_PASSWORD (vedi README FASE 3) e rilancia."
    exit 1
}

fastmcp run server.py --transport streamable-http --host 127.0.0.1 --port 8765
