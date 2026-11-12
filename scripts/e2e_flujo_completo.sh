#!/usr/bin/env bash
# Pruebas finales del flujo completo — Semana 7 (flujo completo con
# notificación v1.3.0). Versionado en el repo (observación Arreglos.txt v4).
#
# Uso (desde cualquier directorio):
#   ./scripts/e2e_flujo_completo.sh
#
# Requisitos: puertos libres para la API y el dev server (por defecto
# :8000 y :5173; configurables con VISTOBUENO_API_PUERTO y
# VISTOBUENO_FRONTEND_PUERTO), frontend con dependencias instaladas
# (npm ci) y un intérprete Python con las dependencias del proyecto
# (.venv o nix). La evidencia se imprime en stdout (redirigir a un .log
# si se desea).

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND="$ROOT/frontend"
if [ -x "$ROOT/.venv/bin/python" ]; then
  BACKEND_VENV="$ROOT/.venv/bin/python"
else
  BACKEND_VENV="python3"
fi
DOCX="/tmp/tesis_prueba.docx"
BAD="/tmp/bad.txt"

# El ensayo levanta su propia API y su propio dev server, así que sus
# puertos tienen que estar libres. Son configurables para poder correrlo
# junto a otra instancia en vez de tener que detenerla.
PUERTO_API="${VISTOBUENO_API_PUERTO:-8000}"
PUERTO_FRONTEND="${VISTOBUENO_FRONTEND_PUERTO:-5173}"
API="http://127.0.0.1:${PUERTO_API}"
FRONTEND_URL="http://127.0.0.1:${PUERTO_FRONTEND}"

PID_API=""
PID_FRONTEND=""

# Solo se detienen los procesos que levantó este ensayo. Un pkill
# general mataría cualquier otra API o cualquier dev server del
# sistema, y el ensayo no podría distinguir los suyos de los ajenos.
detener() {
  for pid in "$PID_API" "$PID_FRONTEND"; do
    [ -n "$pid" ] || continue
    kill -- "-$pid" 2>/dev/null || kill "$pid" 2>/dev/null || true
  done
}
trap detener EXIT

# ¿Hay alguien escuchando en el puerto? (sale 0 si está ocupado)
puerto_ocupado() {
  "$BACKEND_VENV" - "$1" <<'PY'
import socket
import sys

sock = socket.socket()
sock.settimeout(0.5)
try:
    sock.connect(("127.0.0.1", int(sys.argv[1])))
except OSError:
    sys.exit(1)  # libre
finally:
    sock.close()
sys.exit(0)  # ocupado
PY
}

for puerto in "$PUERTO_API" "$PUERTO_FRONTEND"; do
  if puerto_ocupado "$puerto"; then
    echo "❌ El puerto $puerto ya está ocupado."
    echo "   El ensayo levanta su propia API y su propio dev server:"
    echo "   necesita puertos libres. Cerrá el proceso que los ocupa, o"
    echo "   corré el ensayo con otros puertos:"
    echo ""
    echo "     VISTOBUENO_API_PUERTO=8020 VISTOBUENO_FRONTEND_PUERTO=5174 \\"
    echo "       nix run .#test-local"
    exit 1
  fi
done

echo "=== PRUEBAS E2E FLUJO COMPLETO S7 ==="
echo "Repo: $ROOT"
echo "API: $API | frontend: $FRONTEND_URL"
echo "Fecha: $(date)"
echo

# 0. Build frontend
echo "[0/9] Build frontend (npm run build)..."
cd "$FRONTEND" && npm run build > /tmp/build.log 2>&1
echo "  ✅ Build OK (dist/ generado)"

# 1. Tests backend (sin --cov: el addopts de pyproject ya no lo exige)
echo "[1/9] Tests backend (pytest)..."
cd "$ROOT" && "$BACKEND_VENV" -m pytest tests/ -q --tb=no 2>&1 | tail -1
echo "  ✅ pytest terminó sin fallos (el resumen real está en la línea de arriba; puede incluir skipped)"

# 2. Levantar backend
# Bind a 127.0.0.1: el despliegue documentado es local y el loopback es
# la frontera de confianza (docs/CONTRATO_API.md, "Control de acceso").
echo "[2/9] Levantando backend en :${PUERTO_API}..."
setsid nohup "$BACKEND_VENV" -m uvicorn validator.api:app --host 127.0.0.1 --port "$PUERTO_API" \
  > /tmp/backend.log 2>&1 < /dev/null &
PID_API=$!
sleep 3
curl -sf -o /dev/null "$API/docs" && echo "  ✅ Backend UP" || { echo "  ❌ Backend no arrancó"; exit 1; }

# 3. Levantar frontend (dev)
# El `cd` va dentro del subshell: el script sigue en la raíz (el paso 4
# importa `tests._docx_generator` con ruta relativa) y `$!` es el PID
# del proceso final, para poder detenerlo al terminar.
echo "[3/9] Levantando frontend en :${PUERTO_FRONTEND}..."
( cd "$FRONTEND" && VITE_DEV_OPEN=false VISTOBUENO_API_URL="$API" \
  exec setsid nohup npm run dev -- --port "$PUERTO_FRONTEND" --host 127.0.0.1 \
  > /tmp/frontend.log 2>&1 < /dev/null ) &
PID_FRONTEND=$!
sleep 5
curl -sf -o /dev/null "$FRONTEND_URL" && echo "  ✅ Frontend UP" || { echo "  ❌ Frontend no arrancó"; exit 1; }

# 4. Generar DOCX de prueba
echo "[4/9] Generando DOCX de prueba (1024 bytes objetivo)..."
"$BACKEND_VENV" -c "
from tests._docx_generator import build_large_docx
open('$DOCX','wb').write(build_large_docx(1024))
print('  ✅ DOCX generado:', __import__('os').path.getsize('$DOCX'), 'bytes')
"

# 5. Test válido -> 200 + reglas (>= 47: el PR #46 del backend amplió la suite)
echo "[5/9] POST /validar con DOCX válido (proxy :${PUERTO_FRONTEND})..."
HTTP=$(curl -s -m 15 -o /tmp/ok.json -w "%{http_code}" -X POST "$FRONTEND_URL"/validar -F "archivo=@$DOCX")
"$BACKEND_VENV" -c "
import json
d=json.load(open('/tmp/ok.json'))
assert d['resumen']['total']>=47, 'reglas<47'
assert d['semaforo'] in ('rojo','verde'), 'semaforo invalido'
# Contrato v1.5: aplicabilidad por tipo de documento
r=d['resumen']
assert 'total_evaluadas' in r, 'falta total_evaluadas'
assert r['total'] >= r['total_evaluadas'] >= 0, 'total_evaluadas incoherente'
assert r['total'] - r['total_evaluadas'] == r.get('reglas_no_aplicables', 0), 'reglas_no_aplicables incoherente'
assert all('aplicable' in x for x in d['resultados']), 'falta aplicable en resultados'
m=d.get('metadatos', {})
assert m.get('tipo_documento_estado') in ('vigente','sin_determinar','contradictorio'), f'tipo_documento_estado invalido: {m.get(\"tipo_documento_estado\")!r}'
print('  ✅ HTTP', '$HTTP', '| total:', r['total'], '| evaluadas:', r['total_evaluadas'], '| semaforo:', d['semaforo'])
" || { echo "  ❌ Falló validación"; exit 1; }

# 6. Error 415 con detail JSON (NO mock)
echo "[6/9] POST /validar con archivo .txt (debe dar 415 + detail JSON)..."
echo "x" > "$BAD"
HTTP=$(curl -s -m 5 -o /tmp/bad.json -w "%{http_code}" -X POST "$FRONTEND_URL"/validar -F "archivo=@$BAD")
"$BACKEND_VENV" -c "
import json
assert '$HTTP' == '415', 'HTTP!=415'
d=json.load(open('/tmp/bad.json'))
assert 'detail' in d, 'falta detail'
assert 'docx' in d['detail'].lower(), 'detail no menciona docx'
print('  ✅ HTTP', '$HTTP', '| detail:', d['detail'][:80])
" || { echo "  ❌ Error 415 sin detail"; exit 1; }

# 7. Correo inválido -> 422 con detail español (NO mock)
echo "[7/9] correo inválido (debe dar 422 + detail)..."
HTTP=$(curl -s -m 15 -o /tmp/mal.json -w "%{http_code}" -X POST "$FRONTEND_URL"/validar -F "archivo=@$DOCX" -F "correo=esto-no-es-un-correo")
"$BACKEND_VENV" -c "
import json
assert '$HTTP' == '422', 'HTTP!=422'
d=json.load(open('/tmp/mal.json'))
assert 'detail' in d, 'falta detail'
print('  ✅ HTTP', '$HTTP', '| detail:', str(d['detail'])[:80])
" || { echo "  ❌ 422 esperado"; exit 1; }

# 8. Correo válido + notificar=true -> 200 (opt-in aceptado + estado)
echo "[8/9] correo válido + notificar=true (debe dar 200 + notificacion.estado)..."
HTTP=$(curl -s -m 15 -o /tmp/notif.json -w "%{http_code}" -X POST "$FRONTEND_URL"/validar \
  -F "archivo=@$DOCX" -F "correo=estudiante@correo.unt.edu.pe" -F "notificar=true")
"$BACKEND_VENV" -c "
import json
assert '$HTTP' == '200', 'HTTP!=200'
d=json.load(open('/tmp/notif.json'))
estado = d.get('notificacion', {}).get('estado')
VALIDOS = {'enviado','fallo','sin_correo','sin_observaciones','deshabilitado','no_solicitado'}
assert estado in VALIDOS, f'estado inesperado: {estado!r}'
print('  ✅ HTTP', '$HTTP', '| notificacion.estado:', estado)
" || { echo "  ❌ notificar=true rechazado o estado inválido"; exit 1; }

# 8b. Correo SIN notificar -> estado no_solicitado (opt-in real)
echo "[8b/9] correo SIN notificar (debe dar notificacion.estado=no_solicitado)..."
HTTP=$(curl -s -m 15 -o /tmp/no_sol.json -w "%{http_code}" -X POST "$FRONTEND_URL"/validar \
  -F "archivo=@$DOCX" -F "correo=estudiante@correo.unt.edu.pe")
"$BACKEND_VENV" -c "
import json
assert '$HTTP' == '200', 'HTTP!=200'
d=json.load(open('/tmp/no_sol.json'))
estado = d.get('notificacion', {}).get('estado')
assert estado == 'no_solicitado', f'esperaba no_solicitado, vino: {estado!r}'
print('  ✅ HTTP', '$HTTP', '| notificacion.estado:', estado)
" || { echo "  ❌ no_solicitado no devuelto"; exit 1; }

# 9. Backend caído -> proxy 500 body vacío -> mock avisado
echo "[9/9] Backend caído -> proxy 500 vacío -> mock avisado..."
kill -- "-$PID_API" 2>/dev/null || kill "$PID_API" 2>/dev/null || true
PID_API=""
sleep 1
HTTP=$(curl -s -m 5 -o /tmp/down.json -w "%{http_code}" -X POST "$FRONTEND_URL"/validar -F "archivo=@$DOCX")
SIZE=$(wc -c < /tmp/down.json)
"$BACKEND_VENV" -c "
assert '$HTTP' == '500', f'esperaba 500, vino $HTTP'
assert '$SIZE' == '0', f'body no vacio: $SIZE'
print('  ✅ Proxy 500 body vacío (size=0) -> frontend debe ir a mock demo')
"

# Restaurar backend
setsid nohup "$BACKEND_VENV" -m uvicorn validator.api:app --host 127.0.0.1 --port "$PUERTO_API" \
  > /tmp/backend.log 2>&1 < /dev/null &
PID_API=$!
sleep 3
curl -sf -o /dev/null "$API/docs" && echo "  ✅ Backend restaurado"

echo
echo "=== TODAS LAS PRUEBAS E2E PASARON ==="
echo "Fecha fin: $(date)"
