import os
import json
import time
import asyncio
from dotenv import load_dotenv
from google import genai
from google.genai import types

class MotorIA:
    """Clase que encapsula la lógica, conexión (Rotación de Claves) y Memoria (RAG) con la API de Gemini."""

    def __init__(self):
        directorio_actual = os.path.dirname(os.path.abspath(__file__))
        load_dotenv(os.path.join(directorio_actual, ".env"))

        claves_str = os.getenv("GEMINI_API_KEYS") or os.getenv("GEMINI_API_KEY")
        if not claves_str:
            raise ValueError("❌ ERROR CRÍTICO: No se encontraron claves en .env")

        self.api_keys = [k.strip() for k in claves_str.split(',') if k.strip()]
        self.indice_clave = 0
        # 👇 EL MODELO CORRECTO: Inteligente, rapidísimo y con cuota gigante diaria
        self.modelo = "gemini-flash-lite-latest"
        self._conectar_cliente()

    def _conectar_cliente(self):
        clave_actual = self.api_keys[self.indice_clave]
        self.client = genai.Client(api_key=clave_actual)
        print(f"   🔄 Motor IA en línea (Usando clave {self.indice_clave + 1} de {len(self.api_keys)})")

    def _rotar_clave(self):
        self.indice_clave = (self.indice_clave + 1) % len(self.api_keys)
        print(f"   ⚠️ Problema con la API detectado. Rotando a la clave {self.indice_clave + 1}...")
        self._conectar_cliente()

    # 👇 TABULACIÓN REPARADA: Ahora sí pertenece a la clase MotorIA
    def _ejecutar_con_reintentos(self, instrucciones: str, config: types.GenerateContentConfig, es_json: bool = False):
        max_intentos = len(self.api_keys) * 2

        for intento in range(max_intentos):
            try:
                print(f"   ⏳ [DEBUG] Conectando con Google usando '{self.modelo}'...")
                res = self.client.models.generate_content(
                    model=self.modelo,
                    contents=instrucciones,
                    config=config
                )
                print("   ✅ [DEBUG] Respuesta recibida con éxito.")
                return json.loads(res.text) if es_json else res.text
            except Exception as e:
                print(f"   ⚠️ [DEBUG] Ocurrió un error en la API: {e}")
                error_str = str(e).lower()
                # Atrapa excesos de cuota, bloqueos de proyecto (403) y caídas de servidor (503)
                if any(k in error_str for k in ["429", "quota", "exhausted", "rate limit", "too many", "503", "unavailable", "403", "permission_denied"]):
                    self._rotar_clave()
                    time.sleep(2)
                else:
                    print(f"   ⚠️ Error interno API: {e}")
                    time.sleep(2)
        return None

    def _sugerir_sync(self, mi_cv: str, estadisticas: dict) -> list:
        stats_str = json.dumps(estadisticas, ensure_ascii=False) if estadisticas else "Sin datos."
        instrucciones = f"""
        Actúa como un reclutador experto. Analiza el CV del candidato y sus estadísticas de búsqueda.
        Devuelve EXACTAMENTE 10 términos de búsqueda cortos en Chile, separados por comas.
        
        Reglas de exploración estratégica (Epsilon-Greedy):
        - 7 términos deben ser variaciones de las categorías más exitosas del historial (ej. TI, Administración, Recepción, Logística).
        - 3 términos deben ser 'comodines' para explorar áreas distintas afines a sus habilidades.
        - OBLIGATORIO: Todos los términos deben incluir 'part time' o 'fines de semana' al final.
        - NO incluyas comida rápida ni guardias de seguridad.
        - Responde ÚNICAMENTE con la lista separada por comas, sin texto adicional.
        
        HISTORIAL DE DESEMPEÑO: {stats_str}
        CV: {mi_cv}
        """
        config = types.GenerateContentConfig(temperature=0.6)
        texto = self._ejecutar_con_reintentos(instrucciones, config)

        if texto:
            texto_limpio = texto.replace('\n', '').replace('"', '').replace("'", "")
            roles = [r.strip() for r in texto_limpio.split(',') if 3 < len(r.strip()) < 50]
            return roles[:10] if len(roles) >= 5 else ["Soporte TI Part Time", "Call Center Part Time", "Administrativo Part Time"]
        return ["Soporte TI Part Time", "Call Center Part Time"]

    def _evaluar_sync(self, texto_oferta: str, mi_cv: str) -> dict:
        instrucciones = f"""
        Evalúa esta oferta basándote en el CV.
        1. Jornada completa (>30 hrs) → puntaje < 50
        2. Guardia / comida rápida → puntaje = 0
        3. Comuna: El Bosque (RM). Presencial en otra región → 0
        
        JSON exacto: "puntaje" (0-100), "razon" (texto corto), "carta_presentacion" (párrafo), "sueldo", "comuna".
        CV: {mi_cv}
        OFERTA: {texto_oferta[:1500]}
        """
        config = types.GenerateContentConfig(response_mime_type="application/json", temperature=0.1)
        resultado = self._ejecutar_con_reintentos(instrucciones, config, es_json=True)

        if resultado: return resultado
        return {"puntaje": 0, "razon": "Error IA Exhausta", "carta_presentacion": "", "sueldo": "N/A", "comuna": "N/A"}

    def _leer_memoria_respuestas(self) -> str:
        ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "base_conocimiento.json")
        if os.path.exists(ruta):
            try:
                with open(ruta, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data:
                        return "\n".join([f"- Si preguntan por '{k}': responde integrando esta idea: '{v}'" for k, v in data.items()])
            except Exception as e:
                print(f"⚠️ Error leyendo base de conocimiento: {e}")
        return "No hay respuestas predefinidas."

    def _responder_sync(self, pregunta: str, mi_cv: str) -> str:
        memoria_rag = self._leer_memoria_respuestas()

        instrucciones = f"""Actúa como el candidato llenando un formulario de empleo. Eres una persona, no una IA.
        Datos inmutables: Comuna: El Bosque | Disp: Part-time / Fines de Semana | Cel: +56932147684 | Correo: 28exequielaguilera@gmail.com
        
        🧠 BASE DE CONOCIMIENTO (Prioridad 1):
        {memoria_rag}
        
        PERFIL BASE: {mi_cv} 
        PREGUNTA DEL FORMULARIO: {pregunta}
        
        🎯 REGLAS DE ORO PARA VENDERTE (PERSUASIÓN AVANZADA):
        1. PROHIBIDO DECIR "NO TENGO EXPERIENCIA". Transforma tus vivencias en experiencia útil. 
        2. ADAPTA EL DISCURSO AL CARGO (SIN REPETIR SIEMPRE "SOY ESTUDIANTE DE DUOC"):
           - Para Retail/Ventas/Atención/Comida: Traduce tu experiencia de KFC, Burger King y Carnicería a lenguaje corporativo: "Manejo de alto flujo de clientes bajo presión, resolución de conflictos en tiempo real, control de stock y cumplimiento de métricas".
           - Para Administrativo/Cajero/Sistemas: Destaca tu facilidad natural con la tecnología. Di algo como: "Dada mi base informática, aprendo sistemas POS, ERP y software de gestión en tiempo récord", SIN nombrar a Duoc UC en cada respuesta.
           - Para Seguridad: Destaca tu liderazgo como Jefe de Guardias en Liderman, control de accesos y manejo de situaciones críticas con criterio.
           - Para Mantenimiento (Solo si el cargo es técnico): Destaca tus habilidades en "mantenimiento preventivo, diagnóstico y electromecánica de precisión", omitiendo que son máquinas de coser a menos que pregunten específicamente por maquinaria textil.
        3. EL "PART-TIME IDEAL": Si preguntan motivación o por qué te interesa, responde que buscas estabilidad laboral a largo plazo en formato part-time, demostrando alto compromiso, responsabilidad y madurez.
        4. LA REGLA DE LA HUMILDAD TÉCNICA: SOLO di la verdad si te preguntan por una herramienta hiper-especializada (Ej: SAP avanzado, lenguajes de programación específicos). Responde: "Tengo bases sólidas tecnológicas y gran facilidad para aprender software nuevo rápidamente".
        5. Tono directo, seco, seguro de sí mismo y persuasivo. PROHIBIDO saludar o despedirse.
        6. DATOS CORTOS: Si piden un número, comuna o correo, responde SOLO con ese dato.
        """
        config = types.GenerateContentConfig(temperature=0.3)
        texto = self._ejecutar_con_reintentos(instrucciones, config)

        if texto: return texto.strip().replace('"', '')
        return "Disponibilidad inmediata."

    async def sugerir_roles(self, cv: str, stats: dict): return await asyncio.to_thread(self._sugerir_sync, cv, stats)
    async def evaluar_oferta(self, texto: str, cv: str): return await asyncio.to_thread(self._evaluar_sync, texto, cv)
    async def responder_pregunta(self, pregunta: str, cv: str): return await asyncio.to_thread(self._responder_sync, pregunta, cv)