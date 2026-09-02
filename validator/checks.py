"""Ejecución de los checks individuales definidos en el YAML de reglas.

Cada check se ejecuta contra un ExtractedDocx y devuelve (passed, detalle).
Migrado y limpiado a partir del prototipo eval_checks2.py.
"""
import re
from typing import Tuple

from .extractor import W, ExtractedDocx, NS, text_of

# Namespaces también usados para resolver prefijos en nombres de atributo
# (ej. "@w:val" -> {namespace-w}val).
PREFIX_NS = NS


def _resolve_attr_key(atributo: str) -> str:
    name = atributo[1:]  # quita el '@'
    if ":" in name:
        prefix, local = name.split(":", 1)
        return "{" + PREFIX_NS[prefix] + "}" + local
    return name


def run_check(check: dict, extracted: ExtractedDocx, rule: dict) -> Tuple[bool, str]:
    tipo = check["tipo"]

    if tipo == "secuencia_titulos":
        return _check_secuencia(rule, extracted)

    parte = check.get("parte", "document")
    tree = extracted.part(parte)
    if tree is None:
        return False, f"parte '{parte}' no disponible en este archivo"

    nodes = tree.xpath(check["xpath"], namespaces=NS)
    if check.get("contexto") == "cuerpo":
        nodes = [n for n in nodes if extracted.is_cuerpo(n)]

    comp = check.get("comparacion")

    if tipo == "xml_presencia":
        if comp == "exists":
            return len(nodes) > 0, f"exists {len(nodes)} nodos"
        if comp == "not_exists":
            return len(nodes) == 0, f"not_exists {len(nodes)} nodos"
        return False, f"comparacion '{comp}' no soportada para xml_presencia"

    if tipo == "xml_atributo":
        key = _resolve_attr_key(check["atributo"])
        vals = [n.get(key) for n in nodes]
        vals = [v for v in vals if v is not None]
        esperado = check.get("esperado")
        if comp == "eq":
            ok = bool(vals) and vals[0] == esperado
        elif comp == "all_eq":
            ok = bool(vals) and all(v == esperado for v in vals)
        else:
            return False, f"comparacion '{comp}' no soportada para xml_atributo"
        return ok, f"{check['atributo']}={vals[:3]} esperado={esperado}"

    if tipo == "texto_regex":
        patron = re.compile(check["patron"])
        textos = [t.text for n in nodes for t in n.iter(W + "t") if t.text]
        if not textos:
            return False, "sin nodos w:t que evaluar"
        incumplen = [t for t in textos if not patron.fullmatch(t)]
        return not incumplen, f"textos={len(textos)} incumplen={len(incumplen)}"

    if tipo == "texto_en_lista":
        lista = check.get("lista", [])
        ignore_case = check.get("ignore_case", False)
        textos = [text_of(n).strip() for n in nodes if text_of(n).strip()]
        if not textos:
            return False, "sin nodos de texto que evaluar"
        def _norm(s: str) -> str:
            s = re.sub(r"\s+", " ", s).strip()
            return s.lower() if ignore_case else s
        valores = [_norm(t) for t in textos]
        permitidos = [_norm(x) for x in lista]
        incumplen = [v for v in valores if v not in permitidos]
        return not incumplen, f"textos={valores[:3]} en_lista_faltan={incumplen[:3]}"

    if tipo == "imagen_presencia":
        n = len(nodes)
        minimo = check.get("cantidad_minima", 1)
        return n >= minimo, f"imagenes={n} minimo={minimo}"

    return False, f"tipo de check '{tipo}' no soportado"


def _check_secuencia(rule: dict, extracted: ExtractedDocx) -> Tuple[bool, str]:
    esperados = rule.get("valor_esperado", [])
    doc = extracted.document

    heading_texts = []
    for p in doc.xpath("//w:body//w:p", namespaces=NS):
        pPr = p.find(W + "pPr")
        st = pPr.find(W + "pStyle") if pPr is not None else None
        val = st.get(W + "val") if st is not None else None
        if val and ("eading" in val or "tulo" in val):
            heading_texts.append(text_of(p).strip())

    def norm(s: str) -> str:
        return re.sub(r"\s+", " ", s.upper().replace("(OPCIONAL)", " ").strip(" ."))

    def sig_token(t: str) -> str:
        for tk in t.split():
            tk = re.sub(r"[^A-ZÁÉÍÓÚÑ0-9]+", "", tk)
            if len(tk) >= 4:
                return tk
        return re.sub(r"[^A-ZÁÉÍÓÚÑ0-9]+", "", t.split()[0]) if t.split() else ""

    h_norm = [norm(t) for t in heading_texts if t]

    cover_ok = False
    for p in doc.xpath("//w:body/w:p", namespaces=NS):
        t = text_of(p).strip()
        if t:
            cover_ok = "universidad" in t.lower()
            break

    pos = 0
    faltantes = []
    for item in esperados:
        if "(OPCIONAL)" in item.upper():
            continue
        target = norm(item)
        if target in ("CARÁTULA", "CARATULA") and cover_ok:
            continue
        found = None
        for k in range(pos, len(h_norm)):
            h = h_norm[k]
            if (
                h.startswith(target)
                or target.startswith(h[:25])
                or (sig_token(target) and sig_token(target) == sig_token(h))
            ):
                found = k
                break
        if found is None:
            faltantes.append(item)
        else:
            pos = found + 1

    return not faltantes, f"headings={len(h_norm)} faltantes={faltantes[:6]}"
