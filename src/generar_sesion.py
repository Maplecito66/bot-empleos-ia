import os
from playwright.sync_api import sync_playwright

DIRECTORIO_ACTUAL = os.path.dirname(os.path.abspath(__file__))
RUTA_SESION = os.path.join(DIRECTORIO_ACTUAL, "estado_sesion.json")

def generar_llave_maestra():
    print("🔑 INICIANDO GENERADOR DE SESIÓN MAESTRA (USANDO CHROME REAL) 🔑\n")

    with sync_playwright() as p:
        # 🛠️ EL TRUCO: channel="chrome" fuerza a usar tu navegador real en lugar de Chromium
        browser = p.chromium.launch(
            headless=False,
            channel="chrome",
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )

        perfil = {
            "viewport": {"width": 1366, "height": 768},
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        context = browser.new_context(**perfil)
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")

        print("1️⃣ Abriendo Computrabajo...")
        page_ct = context.new_page()
        page_ct.goto("https://cl.computrabajo.com/")
        input("👉 Inicia sesión en Computrabajo. Cuando estés dentro, PRESIONA ENTER aquí en la consola...")

        print("\n2️⃣ Abriendo Laborum...")
        page_lab = context.new_page()
        page_lab.goto("https://www.laborum.cl/")
        input("👉 Inicia sesión en Laborum. Cuando estés dentro, PRESIONA ENTER aquí en la consola...")

        print("\n3️⃣ Abriendo Trabajando.com...")
        page_tr = context.new_page()
        page_tr.goto("https://www.trabajando.cl/")
        input("👉 Inicia sesión en Trabajando.com. Cuando estés dentro, PRESIONA ENTER aquí en la consola...")

        context.storage_state(path=RUTA_SESION)
        print(f"\n✅ ¡ÉXITO! Tu llave maestra ha sido actualizada y guardada.")

        browser.close()

if __name__ == "__main__":
    generar_llave_maestra()