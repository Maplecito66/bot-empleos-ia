import os
import json
import time
import asyncio
from dotenv import load_dotenv
from google import genai
from google.genai import types

class MotorIA:
    def __init__(self):
        directorio_actual = os.path.dirname(os.path.abspath(__file__))
        load_dotenv(os.path.join(directorio_actual, ".env"))

        claves_str = os.getenv("GEMINI_API_KEYS") or os.getenv("GEMINI_API_KEY")
        if not claves_str:
            raise ValueError("❌ ERROR CRÍTICO: No se encontraron claves en .env")

        self.api_keys = [k.strip() for k in claves_str.split(',') if k.strip()]
        self.indice_clave = 0
        self.modelo = "gemini-flash-lite-latest"
        self._conectar_cliente()

    def _conectar_cliente(self):
        clave_actual = self.api_keys[self.indice_clave]
        self.client = genai.Client(api_key=clave_actual)
        print(f"   🔄 Motor IA en línea (Usando clave {self.indice_clave + 1} de {len(self.api_keys)})")

    def _rotar_clave(self):
        self.indice_clave = (self.indice_clave + 1) % len(self.api_keys)
        print(f"   ⚠️ Cambiando a la clave {self.indice_clave + 1}...")
        self._conectar_cliente()

    def _ejecutar_con_reintentos(self, instrucciones: str, config: types.GenerateContentConfig, es_json: bool = False):
        max_intentos = len(self.api_keys) * 2
        for intento in range(max_intentos):
            try:
                res = self.client.models.generate_content(model=self.modelo, contents=instrucciones, config=config)
                return json.loads(res.text) if es_json else res.text
            except Exception as e:
                error_str = str(e).lower()
                if any(k in error_str for k in ["429", "quota", "exhausted", "rate limit"]):
                    self._rotar_clave(); time.sleep(2)
                elif any(k in error_str for k in ["503", "unavailable"]):
                    self._rotar_clave(); time.sleep(5)
                elif any(k in error_str for k in ["403", "permission_denied", "404"]):
                    self._rotar_clave(); time.sleep(1)
                else:
                    time.sleep(2)
        return None

    def _sugerir_sync(self, mi_cv: str, estadisticas: dict) -> list:
        stats_str = json.dumps(estadisticas, ensure_ascii=False) if estadisticas else "Sin datos."
        instrucciones = f"""
        Actúa como un reclutador experto. Analiza el CV del candidato.
        Devuelve EXACTAMENTE 10 términos de búsqueda cortos en Chile, separados por comas.
        
        Reglas de exploración estratégica:
        - El candidato tiene experiencia en: Informática, Soporte, Guardias de Seguridad (Liderman), Comida Rápida (Burger King/KFC), y Ventas.
        - Genera búsquedas balanceadas abarcando todas esas áreas.
        - OBLIGATORIO: Todos los términos deben incluir 'part time' o 'fines de semana' al final.
        - Responde ÚNICAMENTE con la lista separada por comas.
        HISTORIAL: {stats_str} \nCV: {mi_cv}
        """
        config = types.GenerateContentConfig(temperature=0.6)
        texto = self._ejecutar_con_reintentos(instrucciones, config)
        if texto:
            roles = [r.strip() for r in texto.replace('\n', '').replace('"', '').replace("'", "").split(',') if 3 < len(r.strip()) < 50]
            return roles[:10] if len(roles) >= 5 else ["Soporte TI Part Time", "Cajero Part Time", "Guardia Fines de Semana"]
        return ["Soporte TI Part Time", "Cajero Part Time"]

    def _evaluar_sync(self, texto_oferta: str, mi_cv: str) -> dict:
        instrucciones = f"""
        Evalúa esta oferta basándote en el CV.
        1. Jornada completa (>30 hrs) → puntaje < 50. El candidato busca solo PART TIME.
        2. Guardia full time o conserje full time → puntaje 0
        3. Comuna: El Bosque (RM). Presencial en otra región lejana → 0
        
        JSON exacto: "puntaje" (0-100), "razon" (texto corto), "carta_presentacion" (párrafo), "sueldo", "comuna".
        CV: {mi_cv} \nOFERTA: {texto_oferta[:1500]}
        """
        config = types.GenerateContentConfig(response_mime_type="application/json", temperature=0.1)
        res = self._ejecutar_con_reintentos(instrucciones, config, es_json=True)
        return res if res else {"puntaje": 0, "razon": "Error IA Exhausta", "carta_presentacion": "", "sueldo": "N/A", "comuna": "N/A"}

    def _leer_memoria_respuestas(self) -> str:
        ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "base_conocimiento.json")
        if os.path.exists(ruta):
            try:
                with open(ruta, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data: return "\n".join([f"- Si preguntan por '{k}': usa esta idea: '{v}'" for k, v in data.items()])
            except: pass
        return "No hay respuestas predefinidas."

    def _responder_sync(self, pregunta: str, mi_cv: str) -> str:
        memoria_rag = self._leer_memoria_respuestas()
        instrucciones = f"""Actúa como el candidato llenando un formulario de empleo. Eres una persona, no una IA.
        Datos inmutables: Comuna: El Bosque | Disp: Part-time / Fines de Semana | Cel: +56932147684 | Correo: 28exequielaguilera@gmail.com
        
        🧠 BASE DE CONOCIMIENTO: {memoria_rag}
        PERFIL BASE: {mi_cv} 
        PREGUNTA DEL FORMULARIO: {pregunta}
        
        🎯 REGLAS DE ORO (PERSUASIÓN AVANZADA Y ULTRA CORTA):
        1. BREVEDAD EXTREMA: Tus respuestas persuasivas deben ser de MÁXIMO 1 o 2 oraciones (menos de 40 palabras). Ve directo al grano.
        2. PROHIBIDO DECIR "NO TENGO EXPERIENCIA". Transforma tus vivencias en experiencia útil de forma concisa. 
        3. ADAPTA EL DISCURSO AL CARGO (SIN EXPLICACIONES LARGAS):
           - Retail/Ventas/Atención: "Tengo experiencia en manejo de alto flujo de clientes bajo presión, resolución de conflictos y control de stock".
           - Administrativo/Sistemas: "Dada mi base tecnológica, aprendo sistemas POS, ERP y software de gestión en tiempo récord".
           - Seguridad: "Poseo experiencia liderando equipos y controlando accesos e incidencias como Jefe de Guardias".
           - Mantenimiento: "Cuento con experiencia en mantenimiento preventivo, diagnóstico y electromecánica de precisión".
        4. EL "PART-TIME IDEAL": Si preguntan motivación, responde brevemente: "Busco estabilidad laboral a largo plazo para complementar mis estudios".
        5. LA REGLA DE LA HUMILDAD TÉCNICA: SOLO di la verdad si preguntan por una herramienta hiper-especializada. Responde: "Tengo bases sólidas tecnológicas y gran facilidad para aprender software rápidamente".
        6. Tono directo y persuasivo. PROHIBIDO saludar o despedirse.
        7. DATOS CORTOS: Si piden SOLO un número, comuna o correo, responde SOLO con la palabra exacta, sin oraciones.
        """
        config = types.GenerateContentConfig(temperature=0.3)
        texto = self._ejecutar_con_reintentos(instrucciones, config)
        if texto: return texto.strip().replace('"', '')
        return "Disponibilidad inmediata."

    async def sugerir_roles(self, cv: str, stats: dict): return await asyncio.to_thread(self._sugerir_sync, cv, stats)
    async def evaluar_oferta(self, texto: str, cv: str): return await asyncio.to_thread(self._evaluar_sync, texto, cv)
    async def responder_pregunta(self, pregunta: str, cv: str): return await asyncio.to_thread(self._responder_sync, pregunta, cv)