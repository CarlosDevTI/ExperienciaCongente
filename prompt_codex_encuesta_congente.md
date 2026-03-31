# Prompt para Codex — Calificador de Atención / Encuesta de Satisfacción Congente 2026

Quiero que construyas una aplicación web **mobile-first** para **Congente** usando **Django como stack principal**, con interfaz moderna, animada y fácil de usar desde un **QR** por área/canal.

## Decisión técnica obligatoria

Usa este stack:

- **Backend:** Django 5+
- **Base de datos:** PostgreSQL
- **Frontend:** Django Templates + HTMX + Alpine.js
- **Estilos/UI:** Tailwind CSS
- **Gráficos/reportes internos:** Chart.js en dashboard administrativo
- **Autenticación admin:** Django Admin + módulo administrativo personalizado
- **Despliegue preparado para producción:** variables de entorno, settings por entorno, logs básicos, requirements.txt, README

### Importante
**No uses React para la encuesta pública.**  
La razón es que este producto requiere:
- carga rápida al abrir desde QR,
- bajo mantenimiento,
- simplicidad operativa,
- fácil integración con Django,
- formularios dinámicos pero no complejos,
- registro estable por área/canal/pregunta.

Si consideras React útil, úsalo solo en el futuro para un dashboard más avanzado, pero **la primera versión debe quedar 100% funcional con Django + HTMX + Alpine.js + Tailwind**.

---

## Objetivo del sistema

Construir un **calificador de atención** para asociados de Congente, accesible por QR.  
Cada QR estará asociado a un **área** y, al escanearlo, debe abrir una encuesta web con preguntas específicas según el área.  
Las respuestas deben almacenarse en base de datos y permitir seguimiento por:
- área,
- canal,
- fecha,
- pregunta,
- tipo de respuesta,
- dispositivo/sesión,
- QR usado.

El sistema debe servir para medir la satisfacción y experiencia de usuario de forma clara, visual y amigable.

---

## Contexto de negocio

Encuesta: **Encuesta de Satisfacción 2026**  
Objetivo: medir el nivel de satisfacción y experiencia de los asociados Congente.  
Cobertura: canales Congente.  
Metodología: plataforma interactiva ligada a la página web desarrollada en Django.  
Seguimiento: diario por el área de servicio al asociado.  
Población objetivo: asociados activos.  
La encuesta tiene **10 preguntas**, pero cada área usa un subconjunto distinto.

---

## Áreas y preguntas por QR

Debes diseñar el sistema para que cada **área** tenga un identificador único y uno o varios QR.

### Área: Caja
Preguntas:
1, 2, 7, 8, 9 y 10

### Área: Asesoría
Preguntas:
1, 3, 7, 8, 9 y 10

### Área: Servicio al asociado
Preguntas:
4, 7, 8, 9 y 10

### Área: Servicio convenios
Preguntas:
5, 6, 7, 8, 9 y 10

---

## Banco de preguntas

1. Califica tu experiencia como asociado Congente  
2. Califica el servicio recibido en caja  
3. Califica el servicio recibido en asesoría  
4. Califica tu experiencia en respuesta a peticiones, quejas, reclamos y sugerencias (PQRS)  
5. Califica nuestro portafolio de productos, servicios y convenios  
6. Califica tu experiencia con los beneficios de nuestra ticketera Congente  
7. ¿Nos recomendaría con un familiar, amigo o conocido? (Sí / No)  
8. ¿Cuál es su canal de preferencia?
   - WhatsApp
   - ChatBot
   - Mensaje de texto
   - Email
   - Llamadas
   - Facebook / Instagram / YouTube
   - Página web
   - Presencial
9. ¿Qué tipo de servicio, beneficio o convenio le gustaría encontrar? (múltiple selección)
   - Más opciones de crédito
   - Capacitaciones o talleres para asociados
   - Beneficios para familias o hijos
   - Descuentos en comercios o convenios nuevos
   - Asesoría financiera o educativa
   - Otro: ¿Cuál?
10. ¿Cómo podemos mejorar? (respuesta abierta)

---

## Requisitos funcionales

### 1. Acceso por QR
- Cada QR debe apuntar a una URL como:
  - `/encuesta/caja/<token>/`
  - `/encuesta/asesoria/<token>/`
  - `/encuesta/servicio-asociado/<token>/`
  - `/encuesta/servicio-convenios/<token>/`
- El sistema debe identificar el área a partir del QR/token.
- El token debe permitir trazabilidad del punto físico o canal específico.
- Debe haber protección básica contra manipulación simple del QR.

### 2. Encuesta dinámica por área
- La encuesta debe cargar automáticamente las preguntas asociadas al área.
- No debe mostrarse una pregunta que no corresponda al área.
- Debe existir un modelo de configuración para asociar preguntas a áreas sin hardcodear todo.

### 3. Experiencia visual
La encuesta debe sentirse moderna, cálida y confiable.  
Inspirarse en un **calificador de atención** con enfoque corporativo.

#### UI/UX deseada
- Diseño **mobile-first**
- Pantallas limpias
- Carga rápida
- Muy fácil de tocar con el dedo
- Barra de progreso
- Transiciones suaves entre preguntas
- Confirmación final amable

#### Sistema de calificación
Implementa un componente visual tipo rating con alguna de estas variantes:
- estrellas animadas,
- caritas de satisfacción,
- o una propuesta inspirada en elementos de marca Congente.

### Recomendación visual
Propón una experiencia híbrida:
- **5 niveles de calificación**
- cada nivel con animación hover/tap,
- microinteracciones,
- estados seleccionados claros,
- acompañamiento de texto:
  - Muy mala
  - Mala
  - Regular
  - Buena
  - Excelente

No copies exactamente el arte actual; modernízalo.

### Identidad visual
Inspirarse en Congente:
- tonos naranja y azul corporativos,
- estilo amable e institucional,
- interfaz profesional pero cercana,
- uso discreto del logotipo en header/footer,
- evitar saturación visual.

### 4. Validaciones
- Preguntas obligatorias según configuración.
- En pregunta 9, si selecciona “Otro”, mostrar campo de texto obligatorio.
- Evitar envíos duplicados accidentales.
- Validación frontend y backend.
- Sanitizar respuestas abiertas.

### 5. Registro de datos
Guardar mínimo:
- área,
- token QR,
- fecha y hora,
- IP anonimizada si es posible,
- user-agent,
- canal preferido,
- respuestas completas,
- sesión/uuid de participación,
- estado de finalización.

### 6. Prevención de duplicados
Implementa una estrategia razonable:
- session UUID,
- cookie ligera,
- control de reenvío,
- posibilidad de definir si un QR admite múltiples respuestas o una por sesión.

No bloquear de forma agresiva; el objetivo es reducir duplicados accidentales.

### 7. Panel administrativo
Crear módulo administrativo para:
- ver respuestas por área,
- filtrar por rango de fechas,
- filtrar por canal,
- ver resultados por pregunta,
- exportar a Excel/CSV,
- ver comentarios abiertos,
- ver tasa de recomendación,
- ver conteos y promedios.

### 8. Dashboard
Crear dashboard interno con:
- total de respuestas,
- respuestas por área,
- promedio de calificación por pregunta,
- distribución por canal preferido,
- NPS simple o indicador equivalente para recomendación,
- nube/listado de comentarios,
- tendencias por fecha.

### 9. Gestión de configuración
Debe existir CRUD o administración para:
- áreas,
- preguntas,
- relación área-preguntas,
- QRs/tokens,
- activación/desactivación de encuesta,
- textos de bienvenida y cierre.

### 10. Auditoría básica
Registrar:
- fecha de creación,
- fecha de actualización,
- usuario admin que crea/edita configuraciones clave.

---

## Requisitos de modelo de datos

Diseña modelos bien normalizados. Como mínimo:

- `Area`
- `Survey`
- `Question`
- `AreaQuestion`
- `QrEntryPoint` o `SurveyAccessPoint`
- `SurveySubmission`
- `Answer`
- `ChoiceOption`
- `SubmissionEvent` opcional para trazabilidad

### Tipos de pregunta soportados
- rating 1–5
- sí/no
- selección única
- selección múltiple
- texto abierto

---

## Requisitos técnicos de implementación

### Backend
- Django apps separadas, por ejemplo:
  - `core`
  - `surveys`
  - `analytics`
  - `dashboard`
- Formularios y validaciones robustas
- Servicios/helpers limpios
- Tests básicos de modelos, vistas y lógica de encuesta
- URLs legibles
- Protección CSRF
- Settings por entorno con `.env`

### Frontend
- Tailwind CSS
- HTMX para pasos dinámicos sin recargar toda la página
- Alpine.js para estados ligeros e interacción
- Componentes reutilizables
- Accesibilidad básica:
  - contraste razonable,
  - foco visible,
  - labels correctos,
  - navegación usable en móvil

### Base de datos
- PostgreSQL
- índices en campos de consulta frecuente:
  - área,
  - fecha,
  - token,
  - pregunta

### Exportación
- CSV obligatorio
- Excel deseable

---

## Flujo de usuario esperado

1. Usuario escanea QR.
2. Llega a landing de encuesta del área.
3. Ve mensaje corto de bienvenida.
4. Responde preguntas del área con experiencia animada.
5. Envía.
6. Ve pantalla final de agradecimiento.
7. Datos quedan registrados y visibles en panel interno.

---

## Pantallas mínimas

- Landing de encuesta por área
- Encuesta paso a paso o en una sola vista bien diseñada
- Pantalla de gracias
- Dashboard admin
- Vista de listado de respuestas
- Vista de detalle de una respuesta
- Pantalla de configuración de áreas/QR/preguntas

---

## Criterios de diseño

Quiero una UI que se vea mejor que un formulario tradicional.  
Debe sentirse como un **calificador de experiencia**, no como una encuesta aburrida.

### Detalles deseados
- tarjetas/redondeados modernos,
- sombras suaves,
- animaciones cortas,
- progreso visible,
- excelente experiencia móvil,
- CTA claros,
- feedback inmediato al seleccionar opciones.

---

## Entregables esperados

Genera:

1. **Estructura del proyecto Django**
2. **Modelos**
3. **Migraciones**
4. **Vistas**
5. **URLs**
6. **Templates**
7. **Componentes HTMX/Alpine**
8. **Estilos con Tailwind**
9. **Dashboard administrativo**
10. **Datos semilla**
11. **README de instalación**
12. **Tests mínimos**
13. **Script o comando para crear QRs por área/token**
14. **Ejemplo de carga inicial de preguntas y áreas**

---

## Datos semilla obligatorios

Crea seed inicial con:
- las 4 áreas,
- las 10 preguntas,
- las opciones de preguntas 7, 8 y 9,
- relaciones de preguntas por área,
- algunos tokens QR de ejemplo.

---

## Convenciones de calidad

- Código limpio, profesional y mantenible
- Nombres claros en inglés para código y en español para textos de interfaz
- Buen uso de clases, helpers y separación de responsabilidades
- Evitar lógica excesiva en templates
- Comentarios solo donde agreguen valor
- README claro para correr localmente

---

## Qué quiero como salida de tu trabajo

Entrégame el proyecto o, si no puedes entregar archivos completos de una vez, entrégalo por fases en este orden:

### Fase 1
- arquitectura del proyecto,
- estructura de carpetas,
- modelos,
- flujo de datos,
- decisiones técnicas justificadas.

### Fase 2
- implementación backend,
- vistas,
- formularios,
- urls,
- admin.

### Fase 3
- frontend completo con Tailwind + HTMX + Alpine,
- experiencia animada de rating,
- templates responsivos.

### Fase 4
- dashboard,
- filtros,
- exportación,
- métricas.

### Fase 5
- tests,
- datos semilla,
- README,
- mejoras futuras.

---

## Extra importante

Quiero que propongas una **mejora visual concreta** para el rating.  
Por ejemplo, una de estas ideas:
- estrellas corporativas con microanimación,
- medidor emocional de 5 estados,
- fichas circulares con iconografía inspirada en atención/satisfacción,
- o un componente inspirado sutilmente en la identidad de Congente.

Debes escoger una y desarrollarla bien.

---

## Resultado esperado
Necesito que construyas una solución lista para producción inicial, no un demo superficial.  
Prioriza mantenibilidad, rapidez y claridad de implementación en Django.
