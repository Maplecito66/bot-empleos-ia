import os
import asyncio
import base64
import random
import unicodedata
import urllib.parse

class PortalEmpleo:
    def __init__(self, ia, perfil):
        self.ia = ia
        self.perfil = perfil
        self.reporte_qa = os.path.join(os.path.dirname(os.path.abspath(__file__)), "informe_errores_qa.html")
        self.historial = os.path.join(os.path.dirname(os.path.abspath(__file__)), "historial.txt")

    def url_ya_procesada(self, url):
        if not os.path.exists(self.historial): return False
        with open(self.historial, "r", encoding="utf-8") as f:
            return url in f.read()

    def registrar_error_qa(self, titulo, url, msj, captura_bytes):
        if not os.path.exists(self.reporte_qa):
            with open(self.reporte_qa, "w", encoding="utf-8") as f:
                f.write("<html><body style='font-family:Arial;'><h1>🕵️‍♂️ Reporte QA</h1><hr>")
        img = base64.b64encode(captura_bytes).decode('utf-8')
        html = f"<div><h3>⚠️ {titulo}</h3><p><a href='{url}'>Link</a> | {msj}</p><img src='data:image/png;base64,{img}' width='600'></div><hr>"
        with open(self.reporte_qa, "a", encoding="utf-8") as f: f.write(html)

        webhook_url = os.getenv("DISCORD_WEBHOOK_ERRORES")
        if webhook_url:
            from datetime import datetime
            import requests
            hora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            files = {"file": (f"error_{datetime.now().timestamp()}.png", captura_bytes, "image/png")}
            payload = {"content": f"🚨 **ERROR EN FORMULARIO**\n**Fecha/Hora:** {hora}\n**Cargo:** {titulo}\n**Link:** <{url}>\n**Detalle:** {msj}"}
            try: requests.post(webhook_url, data=payload, files=files, timeout=5)
            except: pass

    def registrar_url(self, url):
        with open(self.historial, "a", encoding="utf-8") as f: f.write(url + "\n")

    async def extraer_descripcion(self, page, url: str) -> str:
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(2000)
            return (await page.locator("body").inner_text())[:1500]
        except Exception:
            return ""

class Computrabajo(PortalEmpleo):
    async def obtener_enlaces(self, page, cargo: str, cantidad: int = 5) -> list:
        print(f"   🔵 [COMPUTRABAJO] Buscando: {cargo}")
        cargo_encoded = urllib.parse.quote_plus(cargo)
        url_base = f"https://cl.computrabajo.com/ofertas-de-trabajo/?q={cargo_encoded}+Santiago"
        ofertas = []

        for pag in range(1, 6):
            try:
                await page.goto(f"{url_base}&p={pag}", wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(3000)
                enlaces = await page.locator("a.js-o-link, a[href*='/ofertas-de-trabajo/oferta-de-trabajo']").all()
                if not enlaces: break
                for enlace in enlaces:
                    if len(ofertas) >= cantidad: break
                    try:
                        titulo = await enlace.inner_text()
                        if "postulado" in titulo.lower(): continue
                        href = await enlace.get_attribute("href")
                        if href and len(titulo.strip()) > 5:
                            link = "https://cl.computrabajo.com" + href if href.startswith("/") else href
                            if not self.url_ya_procesada(link):
                                ofertas.append({"titulo": titulo.strip(), "url": link})
                    except Exception: continue
            except Exception: break
        return ofertas

    async def postular(self, context, url: str) -> tuple:
        print("   Iniciando postulación en Computrabajo...")
        page = await context.new_page()
        qa_log = []

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            if "Bad Request" in await page.title(): return "Oferta expirada", []

            try:
                btn = page.locator("a.b_primary[data-href-offer-apply], a.b_primary:has-text('Postularme')").first
                await btn.wait_for(state="visible", timeout=5000)
                await btn.click()
                await page.wait_for_timeout(3000)
            except TimeoutError:
                return "Error: Botón postular oculto o inactivo", []

            inputs = page.locator("input[type='text'], input[type='number'], input[type='tel']")
            for i in range(await inputs.count()):
                campo = inputs.nth(i)
                if await campo.is_visible() and await campo.is_editable():
                    tipo = await campo.get_attribute("type")
                    if tipo == "tel": await campo.fill(self.perfil.telefono)
                    elif tipo == "number": await campo.fill(self.perfil.renta_esperada)
                    else: await campo.fill(self.perfil.comuna)

            textareas = page.locator("textarea")
            for i in range(await textareas.count()):
                ta = textareas.nth(i)
                if await ta.is_visible():
                    pregunta = ""
                    try:
                        pregunta = await ta.evaluate("""(el) => {
                            let prev = el.previousElementSibling;
                            if (!prev) prev = el.parentElement?.previousElementSibling;
                            return prev ? prev.innerText : '';
                        }""")
                    except Exception: pass

                    if not pregunta or len(pregunta) < 5:
                        pregunta = await ta.get_attribute("placeholder") or "Detalle su experiencia:"

                    instruccion = f"{pregunta} (Responde de forma estratégica y muy positiva. Muestra total disposición y adaptabilidad. Si preguntan por herramientas o ropa de trabajo, asume que sí tienes o puedes conseguir. PROHIBIDO inventar que tienes licencia de conducir o cursos como OS10. Sé conciso y persuasivo.)"
                    respuesta = await self.ia.responder_pregunta(instruccion, self.perfil.cv_texto)

                    await ta.clear()
                    await ta.press_sequentially(respuesta, delay=3, timeout=90000)
                    qa_log.append(f"Q: {pregunta}\nA: {respuesta}")

            selects = page.locator("select")
            for i in range(await selects.count()):
                sel = selects.nth(i)
                if await sel.is_visible():
                    try:
                        pregunta_sel = await sel.evaluate("""(el) => {
                            let prev = el.previousElementSibling;
                            if (!prev) prev = el.parentElement?.previousElementSibling;
                            return prev ? prev.innerText : 'Seleccione una opción:';
                        }""")

                        opciones_elementos = await sel.locator("option").all()
                        valores_opcion = {}
                        textos_limpios = []

                        for op in opciones_elementos:
                            texto = await op.inner_text()
                            valor = await op.get_attribute("value")
                            if valor and texto.strip() and "seleccione" not in texto.lower():
                                textos_limpios.append(texto.strip())
                                valores_opcion[texto.strip()] = valor

                        if textos_limpios:
                            prompt_select = f"Pregunta: {pregunta_sel}. Opciones: {', '.join(textos_limpios)}. Actúa estratégicamente: elige la opción más favorable y positiva para conseguir el empleo. PROHIBIDO elegir opciones que impliquen tener licencia de conducir o certificaciones oficiales (como OS10) si no están en el CV. Responde ÚNICAMENTE con el texto exacto de la opción."
                            respuesta_ia = await self.ia.responder_pregunta(prompt_select, self.perfil.cv_texto)

                            mejor_valor = list(valores_opcion.values())[0]
                            for texto_opt, val_opt in valores_opcion.items():
                                if respuesta_ia.lower() in texto_opt.lower() or texto_opt.lower() in respuesta_ia.lower():
                                    mejor_valor = val_opt
                                    break
                            await sel.select_option(value=mejor_valor)
                            qa_log.append(f"Select: {pregunta_sel} | IA eligió: {respuesta_ia}")
                    except Exception: pass

            radios = page.locator("input[type='radio']")
            if await radios.count() > 0:
                grupos = {}
                for i in range(await radios.count()):
                    r = radios.nth(i)
                    if await r.is_visible():
                        name = await r.get_attribute("name")
                        if name:
                            if name not in grupos: grupos[name] = []
                            grupos[name].append(r)

                for name, lista_radios in grupos.items():
                    try:
                        pregunta_radio = await lista_radios[0].evaluate("""(el) => {
                            let container = el.closest('div.mb10') || el.closest('div');
                            let label = container ? container.querySelector('p.font_bold') || container.querySelector('label.font_bold') : null;
                            return label ? label.innerText : 'Seleccione Sí o No:';
                        }""")

                        opciones_texto = []
                        valores_radio = {}
                        for r in lista_radios:
                            label_txt = await r.evaluate("""(el) => {
                                let label = el.closest('label');
                                if (label) return label.innerText.trim();
                                let next = el.nextElementSibling;
                                if (next && next.tagName.toLowerCase() === 'LABEL') return next.innerText.trim();
                                return el.value;
                            }""")
                            if label_txt:
                                opciones_texto.append(label_txt)
                                valores_radio[label_txt] = r

                        if opciones_texto:
                            prompt_radio = f"Pregunta: {pregunta_radio}. Opciones: {', '.join(opciones_texto)}. Elige la opción más positiva para conseguir el empleo. PROHIBIDO inventar licencia de conducir o cursos como OS10. Responde ÚNICAMENTE con la opción elegida."
                            respuesta_ia = await self.ia.responder_pregunta(prompt_radio, self.perfil.cv_texto)

                            locator_elegido = valores_radio[opciones_texto[0]]
                            texto_log = opciones_texto[0] + " (Salvavidas)"

                            for texto_opt, locator_radio in valores_radio.items():
                                if respuesta_ia.lower() in texto_opt.lower() or texto_opt.lower() in respuesta_ia.lower():
                                    locator_elegido = locator_radio
                                    texto_log = texto_opt
                                    break

                            try:
                                await locator_elegido.check(timeout=2000)
                            except:
                                await locator_elegido.evaluate("el => el.click()")

                            qa_log.append(f"Radio: {pregunta_radio} | Marcado: {texto_log}")
                    except Exception: pass

            try: await page.locator("label:has-text('Sí'), label:has-text('Part')").first.click(timeout=1000)
            except Exception: pass

            botones_enviar = page.locator("button:has-text('Enviar mi CV'), a:has-text('Enviar mi CV'), input[type='submit']")
            for i in range(await botones_enviar.count()):
                btn = botones_enviar.nth(i)
                if await btn.is_visible():
                    await btn.click(timeout=3000)
                    break

            try:
                btn_omitir = page.locator("button:has-text('Omitir'), a:has-text('Omitir')").first
                await btn_omitir.click(timeout=3000)
            except Exception: pass

            for _ in range(8):
                await page.wait_for_timeout(1000)
                content = (await page.content()).lower()
                if any(kw in content for kw in ["postulaste correctamente", "postulación enviada", "ya te postulaste", "postulado", "exitosamente"]):
                    return "Éxito: Postulación enviada.", qa_log

            try:
                captura_bytes = await page.screenshot(full_page=True)
                titulo_pag = await page.title() or "Oferta Computrabajo"
                self.registrar_error_qa(titulo_pag, url, "Formulario atascado. Revisa la imagen.", captura_bytes)
            except Exception: pass

            return "Aviso: Postulación dudosa", qa_log
        except Exception as e:
            return f"Error: {e}", []
        finally:
            await page.close()

class Laborum(PortalEmpleo):
    async def obtener_enlaces(self, page, cargo: str, cantidad: int = 5) -> list:
        print(f"   🟣 [LABORUM] Buscando: {cargo}")
        cargo_limpio = unicodedata.normalize('NFKD', cargo).encode('ASCII', 'ignore').decode('utf-8').lower()
        url_base = f"https://www.laborum.cl/empleos-busqueda-{cargo_limpio.replace(' ', '-')}.html"
        ofertas = []

        for pag in range(1, 6):
            try:
                url_paginada = f"{url_base}?page={pag}" if pag > 1 else url_base
                await page.goto(url_paginada, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(4000)

                enlaces = await page.locator("a[href*='/empleos/']").all()
                if not enlaces: break

                for enlace in enlaces:
                    if len(ofertas) >= cantidad: break
                    try:
                        href = await enlace.get_attribute("href")
                        if href and "busqueda" not in href:
                            link = "https://www.laborum.cl" + href if href.startswith("/") else href
                            if not self.url_ya_procesada(link) and not any(o['url'] == link for o in ofertas):
                                texto_bruto = await enlace.inner_text()
                                lineas = [l.strip() for l in texto_bruto.split('\n') if l.strip() and not l.lower().startswith(('actualizado', 'publicado', 'nuevo', 'destacada'))]
                                titulo = lineas[0] if lineas else "Oferta Laborum"
                                if len(titulo) > 3:
                                    ofertas.append({"titulo": titulo, "url": link})
                    except Exception: continue
            except Exception: break
        return ofertas

    async def postular(self, context, url: str) -> tuple:
        print("   Iniciando postulación en Laborum...")
        page = await context.new_page()
        qa_log = []
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            try:
                btn = page.locator("button:has-text('Postularme')").first
                await btn.wait_for(state="visible", timeout=5000)
                await btn.click()
            except TimeoutError: return "Error: Sin botón postular", []

            textareas = page.locator("textarea")
            for i in range(await textareas.count()):
                ta = textareas.nth(i)
                if await ta.is_visible():
                    pregunta = ""
                    try:
                        pregunta = await ta.evaluate("""(el) => {
                            let prev = el.previousElementSibling;
                            if (!prev) prev = el.parentElement?.previousElementSibling;
                            return prev ? prev.innerText : '';
                        }""")
                    except Exception: pass

                    if not pregunta or len(pregunta) < 3:
                        pregunta = await ta.get_attribute("placeholder") or "Pregunta del reclutador:"

                    instruccion = f"Pregunta: {pregunta}. (Responde de forma estratégica y muy positiva. Muestra total disposición y adaptabilidad. Si preguntan por herramientas, asume que sí tienes o puedes conseguir. PROHIBIDO inventar licencia de conducir o cursos como OS10. Sé conciso.)"
                    respuesta = await self.ia.responder_pregunta(instruccion, self.perfil.cv_texto)
                    await ta.fill(respuesta)

                    qa_log.append(f"Q: {pregunta}\nA: {respuesta}")

            try: await page.locator("button:has-text('Responder')").first.click(timeout=2000)
            except Exception: pass

            for _ in range(5):
                await page.wait_for_timeout(1000)
                if "exitosa" in (await page.content()).lower(): return "Éxito: Postulación enviada.", qa_log

            return "Aviso: Postulación dudosa", qa_log
        except Exception as e: return f"Error: {e}", []
        finally:
            await page.close()

class TrabajandoCom(PortalEmpleo):
    async def obtener_enlaces(self, page, cargo: str, cantidad: int = 5) -> list:
        print(f"   🟢 [TRABAJANDO] Buscando: {cargo}")
        ofertas = []
        try:
            await page.goto("https://www.trabajando.cl/trabajo-empleo/", wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(4000)

            try:
                btn_cookies = page.locator("button:has-text('Acepto')").first
                if await btn_cookies.is_visible(timeout=2000):
                    await btn_cookies.click()
                    await page.wait_for_timeout(1000)
            except Exception: pass

            buscador = page.locator("input[placeholder*='trabajo buscas']").first

            if await buscador.is_visible():
                await buscador.click()
                await buscador.fill(cargo)
                await page.keyboard.press("Enter")
                print("      Escribiendo en barra de búsqueda como humano...")
                await page.wait_for_timeout(5000)

                for _ in range(4):
                    await page.keyboard.press("PageDown")
                    await page.wait_for_timeout(1500)

            enlaces = await page.locator("a[href*='/empleos/ofertas/']").all()
            for enlace in enlaces:
                if len(ofertas) >= cantidad: break
                try:
                    href = await enlace.get_attribute("href")
                    if href:
                        link = "https://www.trabajando.cl" + href if href.startswith("/") else href
                        if not self.url_ya_procesada(link) and not any(o['url'] == link for o in ofertas):
                            titulo = (await enlace.inner_text()).split("\n")[0]
                            if len(titulo) > 3:
                                ofertas.append({"titulo": titulo.strip(), "url": link})
                except Exception:
                    continue
        except Exception: pass
        return ofertas

    async def postular(self, context, url: str) -> tuple:
        print("   Iniciando postulación en Trabajando.com...")
        page = await context.new_page()
        qa_log = []
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(3000)

            try:
                btn = page.locator("button:has-text('Postular'), a:has-text('Postular')").first
                await btn.wait_for(state="visible", timeout=5000)
                await btn.click()
                await page.wait_for_timeout(3000)
            except TimeoutError:
                return "Error: Botón postular oculto o inactivo", []

            textareas = page.locator("textarea")
            for i in range(await textareas.count()):
                ta = textareas.nth(i)
                if await ta.is_visible():
                    pregunta = await ta.get_attribute("placeholder") or "Pregunta de Trabajando.com:"
                    instruccion = f"{pregunta} (Responde de forma estratégica y positiva. PROHIBIDO inventar licencia de conducir o cursos como OS10. Sé conciso.)"
                    respuesta = await self.ia.responder_pregunta(instruccion, self.perfil.cv_texto)
                    await ta.clear()
                    await ta.press_sequentially(respuesta, delay=3, timeout=90000)

                    qa_log.append(f"Q: {pregunta}\nA: {respuesta}")

            try:
                await page.locator("button:has-text('Enviar'), button:has-text('Confirmar postulación')").first.click(timeout=3000)
            except Exception: pass

            for _ in range(8):
                await page.wait_for_timeout(1000)
                content = (await page.content()).lower()
                if any(kw in content for kw in ["éxito", "postulaste", "enviada", "felicitaciones"]):
                    return "Éxito: Postulación enviada.", qa_log

            try:
                captura_bytes = await page.screenshot(full_page=True)
                titulo_pag = await page.title() or "Oferta Trabajando.com"
                self.registrar_error_qa(titulo_pag, url, "Formulario atascado en Trabajando.com.", captura_bytes)
            except Exception: pass

            return "Aviso: Postulación dudosa", qa_log
        except Exception as e: return f"Error: {e}", []
        finally:
            await page.close()