import os, json, sys, asyncio, random, requests
from datetime import datetime
from dotenv import load_dotenv
from playwright.async_api import async_playwright
from evaluador import MotorIA
from buscador import Computrabajo, Laborum, TrabajandoCom
from perfil import PerfilCandidato

DIRECTORIO_ACTUAL = os.path.dirname(os.path.abspath(__file__))
RUTA_SESION = os.path.join(DIRECTORIO_ACTUAL, "estado_sesion.json")

load_dotenv(os.path.join(DIRECTORIO_ACTUAL, ".env"))

class NotificadorDiscord:
    def __init__(self):
        self.url_general = os.getenv("DISCORD_WEBHOOK_GENERAL")
        self.url_exitos = os.getenv("DISCORD_WEBHOOK_EXITOS")
        self.url_errores = os.getenv("DISCORD_WEBHOOK_ERRORES")

    async def notificar_estado(self, mensaje):
        if not self.url_general: return
        try: await asyncio.to_thread(requests.post, self.url_general, json={"content": f"🤖 **BOT STATUS:** {mensaje}"})
        except: pass

    async def reportar_estrategia(self, roles):
        if not self.url_general: return
        texto_roles = "\n".join([f"**{i}.** {r}" for i, r in enumerate(roles, 1)])
        embed = {
            "title": "🧠 Sistema Híbrido Iniciado (PRODUCCIÓN)",
            "description": f"🔄 **Motor IA en línea**\n\n🎯 **[ESTRATEGIA IA] Roles:**\n{texto_roles}",
            "color": 3447003
        }
        try: await asyncio.to_thread(requests.post, self.url_general, json={"embeds": [embed]})
        except: pass

    async def reportar_exito(self, titulo, url, qa_log, portal_nombre):
        if not self.url_exitos: return
        texto_qa = "\n\n".join(qa_log) if qa_log else "🚀 Postulación Express (1-Clic sin preguntas)."
        if len(texto_qa) > 1000: texto_qa = texto_qa[:997] + "..."
        color_embed = 3447003 if portal_nombre == "Computrabajo" else 10181046 if portal_nombre == "Laborum" else 3066993
        embed = {
            "title": f"✅ ¡POSTULACIÓN ENVIADA en {portal_nombre}!",
            "description": f"**Cargo:** [{titulo}]({url})\n**Hora:** {datetime.now().strftime('%H:%M:%S')}",
            "color": color_embed,
            "fields": [{"name": "🧠 Análisis y Respuestas", "value": f"```text\n{texto_qa}\n```"}]
        }
        try: await asyncio.to_thread(requests.post, self.url_exitos, json={"embeds": [embed]})
        except: pass

class MemoriaBot:
    def __init__(self):
        self.ruta = os.path.join(DIRECTORIO_ACTUAL, "estadisticas_roles.json")
        self.data = self._cargar()

    def _cargar(self):
        if os.path.exists(self.ruta):
            with open(self.ruta, "r", encoding="utf-8") as f: return json.load(f)
        return {"Soporte TI Part Time": {"exitos": 0, "descartes": 0}}

    def guardar(self):
        with open(self.ruta, "w", encoding="utf-8") as f: json.dump(self.data, f, indent=4, ensure_ascii=False)

    def registrar(self, rol, exito=False):
        if rol not in self.data: self.data[rol] = {"exitos": 0, "descartes": 0}
        if exito: self.data[rol]["exitos"] += 1
        else: self.data[rol]["descartes"] += 1

class OrquestadorBot:
    def __init__(self):
        self.memoria = MemoriaBot()
        self.discord = NotificadorDiscord()
        self.ia = MotorIA()
        self.perfil = PerfilCandidato()
        self.ct = Computrabajo(self.ia, self.perfil)
        self.lab = Laborum(self.ia, self.perfil)
        self.tr = TrabajandoCom(self.ia, self.perfil)
        self.meta = 15
        self.exitos = 0

    def guardar_auditoria_qa(self, titulo, portal, qa_log):
        if not qa_log: return
        ruta_log = os.path.join(DIRECTORIO_ACTUAL, "auditoria_respuestas.txt")
        with open(ruta_log, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*60}\n🏢 PORTAL: {portal} (PRODUCCIÓN)\n💼 CARGO:  {titulo}\n📅 FECHA:  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n{'-'*60}\n")
            for interaccion in qa_log: f.write(f"{interaccion}\n\n")
            f.write(f"{'='*60}\n")

    async def iniciar(self):
        print("🧠 Consultando IA (Arquitectura Híbrida de Producción)...")
        roles = await self.ia.sugerir_roles(self.perfil.cv_texto, self.memoria.data)

        print("\n🎯 [ESTRATEGIA IA] Roles generados para esta sesión:")
        for i, r in enumerate(roles, 1): print(f"   {i}. {r}")
        print("="*40)
        await self.discord.reportar_estrategia(roles)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-dev-shm-usage"])
            perfil = {"viewport": {"width": 1366, "height": 768}, "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
            context = await browser.new_context(storage_state=RUTA_SESION if os.path.exists(RUTA_SESION) else None, **perfil)
            await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")

            for cargo in roles:
                if self.exitos >= self.meta: break
                print(f"\n========================================\n🔍 Categoría: {cargo}\n========================================")
                termino_amplio = cargo.lower().replace("part time", "").replace("fines de semana", "").strip()

                p1, p2, p3 = await context.new_page(), await context.new_page(), await context.new_page()
                res = await asyncio.gather(
                    self.ct.obtener_enlaces(p1, termino_amplio, cantidad=30),
                    self.lab.obtener_enlaces(p2, termino_amplio, cantidad=30),
                    self.tr.obtener_enlaces(p3, termino_amplio, cantidad=30)
                )
                await p1.close(); await p2.close(); await p3.close()
                enlaces = res[0] + res[1] + res[2]

                p_oferta = await context.new_page()
                for oferta in enlaces:
                    if self.exitos >= self.meta: break
                    print(f"\n📄 Analizando: {oferta['titulo']}")

                    palabras_prohibidas = ["full time", "fulltime", "full-time", "44 horas", "45 horas", "40 hrs", "guardia", "cocina", "ingeniero", "conductor", "senior"]
                    if any(bad in oferta['titulo'].lower() for bad in palabras_prohibidas):
                        print(f"   ⚡ Filtro rápido (Descartado: {oferta['titulo']}).")
                        self.ct.registrar_url(oferta['url'])
                        continue

                    desc = await self.ct.extraer_descripcion(p_oferta, oferta['url'])
                    if not desc: continue

                    evaluacion = await self.ia.evaluar_oferta(desc, self.perfil.cv_texto)

                    if evaluacion.get("puntaje", 0) >= 65:
                        print("   ✨ Match alto! Postulando...")
                        portal = self.lab if "laborum" in oferta['url'] else self.tr if "trabajando" in oferta['url'] else self.ct
                        msj, log = await portal.postular(context, oferta['url'])

                        if "Éxito" in msj:
                            self.exitos += 1
                            self.memoria.registrar(cargo, True)
                            print(f"   🏆 ÉXITO! {oferta['titulo']}\n   🔗 {oferta['url']}")
                            nombre_plataforma = "Laborum" if "laborum" in oferta['url'] else "Trabajando.com" if "trabajando" in oferta['url'] else "Computrabajo"
                            await self.discord.reportar_exito(oferta['titulo'], oferta['url'], log, nombre_plataforma)
                            self.guardar_auditoria_qa(oferta['titulo'], nombre_plataforma, log)
                        else:
                            self.memoria.registrar(cargo, False)
                            print(f"   => {msj}")
                        portal.registrar_url(oferta['url'])
                    else:
                        print(f"   ❌ Puntaje bajo ({evaluacion.get('puntaje', 0)}): {evaluacion.get('razon', '')}")
                        self.memoria.registrar(cargo, False)
                        self.ct.registrar_url(oferta['url'])
                await p_oferta.close()
            await browser.close()
        await self.discord.notificar_estado(f"Apagado normal. Meta de postulaciones reales: {self.exitos}")

if __name__ == "__main__":
    bot = OrquestadorBot()
    try: asyncio.run(bot.iniciar())
    except KeyboardInterrupt: asyncio.run(bot.discord.notificar_estado(f"Apagado forzado. Postulaciones: {bot.exitos}"))
    finally: bot.memoria.guardar()