// Datos mock que imitan la respuesta del backend (build_report).
// Se usan mientras el Integrante 1 no tenga el endpoint listo.
//Campos alineados al contrato de la API (api_models.py: ResultadoReglaAPI).
export const MOCK_REPORT = {
  semaforo: 'rojo',
  resumen: { total: 31, fallidos_error: 3, fallidos_warning: 2 },
  resultados: [
    { rule_id: 'papel_tamano', paso: true, severidad: 'error', mensaje: 'El tamaño del papel debe ser A4', esperado: '210 x 297 mm', encontrado: 'cumple' },
    { rule_id: 'fuente_principal', paso: true, severidad: 'error', mensaje: 'La fuente del cuerpo debe ser Times New Roman', esperado: 'Times New Roman', encontrado: 'cumple' },
    { rule_id: 'tamano_cuerpo', paso: true, severidad: 'error', mensaje: 'El tamaño de letra del cuerpo debe ser 12pt', esperado: '12pt', encontrado: 'cumple' },
    { rule_id: 'interlineado', paso: true, severidad: 'error', mensaje: 'El interlineado del cuerpo debe ser 1.5', esperado: '1.5 líneas', encontrado: 'cumple' },
    { rule_id: 'margen_superior', paso: true, severidad: 'error', mensaje: 'El margen superior debe ser 2.5 cm', esperado: '2.5 cm', encontrado: 'cumple' },
    { rule_id: 'margen_izquierdo', paso: true, severidad: 'error', mensaje: 'El margen izquierdo debe ser 3 cm', esperado: '3 cm', encontrado: 'cumple' },
    { rule_id: 'margen_derecho', paso: false, severidad: 'warning', mensaje: 'El margen derecho debe ser 2.5 cm', esperado: '2.5 cm', encontrado: '2.5 cm aprox. (plantillas usan 708/709)' },
    { rule_id: 'sangria_parrafo', paso: false, severidad: 'warning', mensaje: 'La sangría de primera línea debe ser 1.27 cm', esperado: '1.27 cm', encontrado: '1.25 cm (708 twips)' },
    { rule_id: 'numeracion_cuerpo_arabigo', paso: true, severidad: 'error', mensaje: 'El cuerpo debe numerarse con arábigos desde la introducción', esperado: 'arábigos', encontrado: 'cumple' },
    { rule_id: 'numeracion_preliminares_romano', paso: false, severidad: 'error', mensaje: 'Los preliminares deben numerarse en romanos', esperado: 'romanos (i, ii, iii...)', encontrado: 'arábigos en preliminares' },
    { rule_id: 'caratula_universidad_negrita_mayusculas', paso: true, severidad: 'error', mensaje: 'El nombre de la universidad debe ir en negrita y mayúsculas', esperado: 'negrita + MAYÚS', encontrado: 'cumple' },
    { rule_id: 'caratula_titulo_negrita_mixta', paso: false, severidad: 'error', mensaje: 'El título del trabajo debe ir en negrita y mixta', esperado: 'negrita + mixta', encontrado: 'todo mayúsculas' },
    { rule_id: 'estructura_tinv_cuantitativo', paso: true, severidad: 'error', mensaje: 'Se deben incluir las secciones del diseño cuantitativo', esperado: 'secciones obligatorias', encontrado: 'cumple' }
  ],
  como_preguntar_a_una_ia: [
    { rule_id: 'margen_derecho', prompt: 'Tengo un documento de tesis en Word (Universidad Nacional de Trujillo). Detecté un problema de formato:\n\n- Regla incumplida: El margen derecho debe ser 2.5 cm\n- Valor esperado según el reglamento: 2.5 cm\n- Lo que encontró el validador: 2.5 cm aprox. (plantillas usan 708/709)\n\n¿Puedes darme instrucciones paso a paso para corregir esto en Microsoft Word, sin afectar el resto del formato del documento?' },
    { rule_id: 'sangria_parrafo', prompt: 'Tengo un documento de tesis en Word (Universidad Nacional de Trujillo). Detecté un problema de formato:\n\n- Regla incumplida: La sangría de primera línea debe ser 1.27 cm\n- Valor esperado según el reglamento: 1.27 cm\n- Lo que encontró el validador: 1.25 cm (708 twips)\n\n¿Puedes darme instrucciones paso a paso para corregir esto en Microsoft Word, sin afectar el resto del formato del documento?' },
    { rule_id: 'numeracion_preliminares_romano', prompt: 'Tengo un documento de tesis en Word (Universidad Nacional de Trujillo). Detecté un problema de formato:\n\n- Regla incumplida: Los preliminares deben numerarse en romanos\n- Valor esperado según el reglamento: romanos (i, ii, iii...)\n- Lo que encontró el validador: arábigos en preliminares\n\n¿Puedes darme instrucciones paso a paso para corregir esto en Microsoft Word, sin afectar el resto del formato del documento?' },
    { rule_id: 'caratula_titulo_negrita_mixta', prompt: 'Tengo un documento de tesis en Word (Universidad Nacional de Trujillo). Detecté un problema de formato:\n\n- Regla incumplida: El título del trabajo debe ir en negrita y mixta\n- Valor esperado según el reglamento: negrita + mixta\n- Lo que encontró el validador: todo mayúsculas\n\n¿Puedes darme instrucciones paso a paso para corregir esto en Microsoft Word, sin afectar el resto del formato del documento?' }
  ]
}
