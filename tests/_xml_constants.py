"""Constantes XML/OPC del factory de DOCX sintéticos (soporte de F6).

Concentra los namespaces WordprocessingML/DrawingML y las plantillas XML
fijas del paquete OPC (_rels, [Content_Types]). Nada de esto depende de
otro módulo; es el estrato de "datos estáticos" de la construcción.
"""

WNS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
ANS = "http://schemas.openxmlformats.org/drawingml/2006/main"
PNS = "http://schemas.openxmlformats.org/drawingml/2006/picture"
RNS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
WPN = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Default Extension="png" ContentType="image/png"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>
</Types>"""

RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rIdFooter" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="word/footer1.xml"/>
  <Relationship Id="rIdImg" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/logo.png"/>
  <Relationship Id="rIdOrc" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" Target="https://orcid.org/0000-0002-1825-0097" TargetMode="External"/>
</Relationships>"""