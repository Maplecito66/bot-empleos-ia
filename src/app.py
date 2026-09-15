import streamlit as st
from buscador import obtener_enlaces, extraer_descripcion, postular_oferta
from evaluador import evaluar_oferta
from playwright.sync_api import sync_playwright

MI_CV = """
Soy Exequiel, técnico y estudiante de desarrollo de software.
Tengo conocimientos sólidos en Python, arquitectura de microservicios y consumo de APIs REST.
Busco oportunidades donde pueda aplicar mis habilidades técnicas, aprender nuevas tecnologías y crecer profesionalmente.
"""

st.set_page_config(page_title="Bot de Empleos AI", layout="centered")
st.title("🤖 Asistente de Postulación Automática")

if 'ofertas_guardadas' not in st.session_state:
    st.session_state['ofertas_guardadas'] = None

cargo_buscar = st.text_input("¿Qué cargo buscas hoy?", "desarrollador junior")

# ----------------- PRIMER CLIC (BÚSQUEDA) -----------------
if st.button("Buscar Ofertas (Clic 1)"):
    st.session_state['ofertas_guardadas'] = []

    with st.spinner('Navegando y extrayendo datos con tu sesión...'):
        with sync_playwright() as p:
            # Usamos el estado guardado para la búsqueda también
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(storage_state="src/estado_sesion.json")
            page = context.new_page()

            mensaje_estado = st.empty()
            mensaje_estado.info("Buscando ofertas...")

            ofertas_basicas = obtener_enlaces(page, cargo_buscar, cantidad=2)

            if not ofertas_basicas:
                mensaje_estado.error("No se encontraron enlaces en la página.")
            else:
                ofertas_analizadas = []
                for i, oferta in enumerate(ofertas_basicas):
                    texto_oferta = extraer_descripcion(page, oferta['url'])
                    if texto_oferta:
                        evaluacion = evaluar_oferta(texto_oferta, MI_CV)
                        ofertas_analizadas.append({
                            'titulo': oferta['titulo'],
                            'url': oferta['url'],
                            'evaluacion': evaluacion
                        })
                st.session_state['ofertas_guardadas'] = ofertas_analizadas
                mensaje_estado.success("¡Análisis completado!")

            browser.close()

# ----------------- MOSTRAR Y SEGUNDO CLIC -----------------
if st.session_state['ofertas_guardadas']:
    st.divider()
    st.subheader("Resultados listos para ti:")

    for i, oferta in enumerate(st.session_state['ofertas_guardadas']):
        with st.container(border=True):
            st.markdown(f"#### {oferta['titulo']}")
            st.info(f"**Análisis de Gemini:** {oferta['evaluacion']}")

            # --- Human in the Loop ---
            st.write("¿Hay preguntas adicionales en la postulación?")
            respuesta_sugerida = "Soy un profesional con alta motivación, bases sólidas en Python y metodologías modernas, dispuesto a aportar valor inmediato al equipo."

            # Te mostramos la sugerencia para que la edites
            texto_aprobado = st.text_area(
                "Edita el texto antes de enviar (opcional):",
                value=respuesta_sugerida,
                key=f"texto_{i}"
            )

            # EL SEGUNDO CLIC (AHORA ES REAL)
            if st.button("Aprobar y Enviar Postulación Real", key=f"postular_{i}"):
                with st.spinner("Ejecutando Playwright para postular..."):
                    resultado = postular_oferta(oferta['url'], texto_aprobado)

                    if "Éxito" in resultado:
                        st.success(f"¡{resultado} a '{oferta['titulo']}'!")
                        st.balloons()
                    else:
                        st.error(f"Problema al postular: {resultado}. Verifica si el diseño de la página cambió.")