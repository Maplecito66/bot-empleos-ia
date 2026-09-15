import asyncio
import os
from playwright.async_api import async_playwright

DIRECTORIO_ACTUAL = os.path.dirname(os.path.abspath(__file__))
RUTA_SESION = os.path.join(DIRECTORIO_ACTUAL, "estado_sesion.json")

async def capturar_todas_las_sesiones():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)

        # 🧠 NUEVO: Revisa si ya tienes credenciales guardadas y las carga
        if os.path.exists(RUTA_SESION):
            context = await browser.new_context(storage_state=RUTA_SESION)
            print("♻️ Cargando tu archivo de sesión actual...")
        else:
            context = await browser.new_context()
            print("🆕 Iniciando desde cero (sin sesiones)...")

        print("🌐 Abriendo los tres portales...")
        p1 = await context.new_page()
        await p1.goto("https://cl.computrabajo.com/")

        p2 = await context.new_page()
        await p2.goto("https://www.trabajando.cl/login")

        p3 = await context.new_page()
        await p3.goto("https://www.laborum.cl/login")

        print("\n" + "="*50)
        print("🛑 NAVEGADOR EN PAUSA 🛑")
        print("1. Revisa las 3 pestañas una por una.")
        print("2. Si en alguna te pide clave, pon tu correo y contraseña.")
        print("3. Asegúrate de ver tu nombre, tu foto o 'Mi Perfil' en LAS TRES.")
        print("="*50)

        # El bot se congela aquí hasta que le des la orden
        await asyncio.to_thread(input, "\n👉 Vuelve a esta consola negra y presiona ENTER *solo* cuando estés 100% logueado en las 3: ")

        # Guarda la "foto" definitiva
        await context.storage_state(path=RUTA_SESION)
        print("\n✅ ¡Sesiones guardadas de forma definitiva!")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(capturar_todas_las_sesiones())