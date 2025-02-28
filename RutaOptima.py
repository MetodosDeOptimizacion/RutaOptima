import requests
import streamlit as st  
import folium
import json
import geopy
import time
from geopy.geocoders import Nominatim
from streamlit_folium import folium_static, st_folium
from scipy.spatial.distance import euclidean
from itertools import permutations
from geopy.exc import GeocoderTimedOut

def obtener_ubicacion(direccion):
    geolocalizador = Nominatim(user_agent="streamlit_route_optimizer", timeout=5)
    for _ in range(3):  # Intentar 3 veces
        try:
            ubicacion = geolocalizador.geocode(direccion)
            if ubicacion:
                return ubicacion
        except GeocoderTimedOut:
            print("🌐 Timeout, reintentando...")
            time.sleep(2)  # Esperar 2 segundos antes de intentar de nuevo
    return None  # Si falla después de 3 intentos

# 📌 Función para calcular la ruta óptima con el primer punto como origen
def calcular_ruta_optima(puntos):
    num_puntos = len(puntos)
    if num_puntos < 2:
        return []

    # El primer punto será el origen
    origen = puntos[0]
    puntos_sin_origen = puntos[1:]  # Resto de los puntos después del origen

    mejor_ruta = None
    menor_distancia = float("inf")

    # Evaluar todas las permutaciones de los puntos restantes
    for perm in permutations(puntos_sin_origen):
        # Agregar la distancia desde el origen al primer punto
        distancia_total = euclidean(origen, perm[0])
        # Sumar distancias entre puntos consecutivos
        distancia_total += sum(euclidean(perm[i], perm[i+1]) for i in range(len(perm) - 1))

        if distancia_total < menor_distancia:
            menor_distancia = distancia_total
            mejor_ruta = [origen] + list(perm)  # El primer punto es el origen

    return mejor_ruta

# 📌 Función para obtener la ruta usando OSRM (Open Source Routing Machine)
def obtener_ruta_real(puntos):
    # Convertir puntos de (lat, lon) a (lon, lat), que es el formato que OSRM espera
    coords = ";".join([f"{lon},{lat}" for lat, lon in puntos])
    
    # Hacer la solicitud a OSRM (servidor público)
    url = f"http://router.project-osrm.org/route/v1/driving/{coords}?overview=full&geometries=geojson"
    response = requests.get(url)
    data = response.json()  # Obtener los datos en formato JSON

    # Verificamos si la respuesta contiene rutas
    if "routes" in data and len(data["routes"]) > 0:
        return data  # Si hay rutas, devolverlas
    else:
        return None  # Si no hay rutas, devolver None

# 📍 Interfaz con Streamlit
st.set_page_config(page_title="Optimizador de Rutas", layout="wide")

st.title("🚚 Optimizador de Rutas de Entrega")
st.write("Seleccione un punto de partida y agregue otros puntos en el mapa.")

# 📌 Configurar sesión para almacenar puntos seleccionados
if "puntos" not in st.session_state:
    st.session_state["puntos"] = []

# 📌 Barra lateral con opciones
st.sidebar.header("📌 Seleccionar Departamento y Agregar Puntos")

# Diccionario con coordenadas de los centros aproximados de los departamentos
centro_departamentos = {
    "Amazonas": [-3.7741, -77.2448],
    "Áncash": [-9.0227, -77.5321],
    "Apurímac": [-13.5902, -73.3635],
    "Arequipa": [-16.4095, -71.5375],
    "Ayacucho": [-13.1587, -74.2248],
    "Cajamarca": [-7.1530, -78.5100],
    "Callao": [-12.0549, -77.1185],
    "Cusco": [-13.5320, -71.9675],
    "Huancavelica": [-12.7713, -74.9895],
    "Huánuco": [-9.9701, -76.2424],
    "Ica": [-13.4240, -75.2033],
    "Junín": [-12.0444, -75.2010],
    "La Libertad": [-8.1185, -77.0331],
    "Lambayeque": [-6.7720, -79.9199],
    "Lima": [-12.0464, -77.0428],
    "Loreto": [-3.7431, -73.2561],
    "Madre de Dios": [-12.5936, -69.1892],
    "Moquegua": [-17.0947, -70.9343],
    "Pasco": [-10.7114, -75.2645],
    "Piura": [-5.1945, -80.6328],
    "Puno": [-15.8401, -69.2228],
    "San Martín": [-6.9404, -76.9201],
    "Tacna": [-18.0104, -70.2490],
    "Tumbes": [-3.5663, -80.4530],
    "Ucayali": [-8.3794, -74.5301],
}

# 🗺️ Selección de un departamento
departamento_seleccionado = st.sidebar.selectbox("Selecciona un Departamento de Perú", list(centro_departamentos.keys()))
# Agregar esto en la barra lateral donde se seleccionan los puntos
direccion = st.sidebar.text_input("Buscar Dirección o Ciudad", "")

# Usar geolocalizador si se ingresa una dirección
if direccion:
    # Ajusta el timeout a un valor más alto (por ejemplo, 5 segundos)
    geolocalizador = Nominatim(user_agent="streamlit_route_optimizer", timeout=5)
    ubicacion = geolocalizador.geocode(direccion)

    # Usar la función con la dirección
    ubicacion = obtener_ubicacion(direccion)
    if ubicacion:
        st.sidebar.success(f"🔍 Dirección encontrada: {ubicacion.address}")
        st.session_state["puntos"] = [(ubicacion.latitude, ubicacion.longitude)]  # Primer punto = Origen
        st.sidebar.write(f"📍 Origen actualizado: ({ubicacion.latitude:.4f}, {ubicacion.longitude:.4f})")
    else:
        st.sidebar.error("❌ No se pudo encontrar la dirección después de varios intentos.")
        
# 📌 Mostrar puntos seleccionados en la barra lateral
st.sidebar.subheader("📍 Puntos Seleccionados:")
if st.session_state["puntos"]:
    for idx, (lat, lon) in enumerate(st.session_state["puntos"]):
        col1, col2 = st.sidebar.columns([4, 1])  # Distribuir espacio
        col1.write(f"🔹 Punto {idx+1}: ({lat:.4f}, {lon:.4f})")
        if col2.button("❌", key=f"del_{idx}"):
            st.session_state["puntos"].pop(idx)
            st.rerun()  # Recargar la página para actualizar la lista
# 📌 Guardar y Cargar ruta
with st.sidebar:
    # Botón para guardar la ruta
    if st.button("Guardar ruta"):
        with open("ruta_guardada.json", "w") as f:
            json.dump(st.session_state["puntos"], f)
        st.success("Ruta guardada con éxito.")  # Mensaje de éxito en la barra lateral

    # Botón para cargar la ruta
    if st.button("Cargar ruta"):
        try:
            with open("ruta_guardada.json", "r") as f:
                st.session_state["puntos"] = json.load(f)
            st.success("Ruta cargada con éxito.")  # Mensaje de éxito en la barra lateral
        except FileNotFoundError:
            st.error("❌ No se encontró ningún archivo guardado.")  # Mensaje de error en la barra lateral

# 🗺️ Mapa de selección de puntos
col1, col2 = st.columns(2)

with col1:
    st.subheader("📍 Mapa de Selección")

    # Centrar el mapa en el departamento seleccionado
    lat, lon = centro_departamentos[departamento_seleccionado]
    
    # Si hay un punto de origen, usa esas coordenadas para centrar el mapa
    if st.session_state["puntos"]:
        lat, lon = st.session_state["puntos"][0]

    mapa_seleccion = folium.Map(location=[lat, lon], zoom_start=10)

    # 📍 Agregar los puntos al mapa
    for idx, (lat, lon) in enumerate(st.session_state["puntos"]):
        color = "blue"  # Cambiar a azul para los puntos
        folium.Marker(
            [lat, lon], 
            popup=f"Punto {idx+1}", 
            tooltip=f"Orden: {idx+1}",
            icon=folium.Icon(color=color)
        ).add_to(mapa_seleccion)

    # 📍 Usar st_folium para capturar clics y agregar puntos
    map_data = st_folium(mapa_seleccion, width=700, height=500)

    # 📌 Capturar clics en el mapa
    if map_data and map_data.get("last_clicked") is not None:
        click_lat = map_data["last_clicked"].get("lat", None)
        click_lon = map_data["last_clicked"].get("lng", None)

        if click_lat is not None and click_lon is not None:
            st.session_state["puntos"].append((click_lat, click_lon))  # Agregar el punto
            st.sidebar.success(f"📍 Punto agregado: ({click_lat}, {click_lon})")

# 📌 Mapa con la ruta óptima
with col2:
    st.subheader("📍 Ruta Óptima")

    if st.button("🚀 Calcular Ruta Óptima"):
        if len(st.session_state["puntos"]) < 2:  # Necesitamos al menos 2 puntos para calcular la ruta
            st.warning("⚠️ Selecciona al menos un punto más para calcular la ruta.")
        else:
            ruta_optima = obtener_ruta_real(st.session_state["puntos"])
            if ruta_optima:
                st.success(f"✅ Ruta óptima calculada.")
                
                # Generar mapa con la ruta óptima
                m_resultado = folium.Map(location=st.session_state["puntos"][0], zoom_start=12)

                # 📌 Dibujar los puntos en el mapa con números de orden
                for i, (lat, lon) in enumerate(st.session_state["puntos"]):
                    color = "blue"
                    folium.Marker(
                        [lat, lon],
                        popup=f"Punto {i+1} (Orden {i+1})",
                        icon=folium.Icon(color=color),
                    ).add_to(m_resultado)

                    # 🔢 Etiqueta visual con el número de orden
                    folium.map.Marker(
                        [lat, lon],
                        icon=folium.DivIcon(
                            html=f"""<div style="font-size: 14pt; font-weight: bold; color: red;">{i+1}</div>"""
                        ),
                    ).add_to(m_resultado)

                # 📌 Verificar si la ruta está disponible en la respuesta
                if ruta_optima:
                    # 📌 Dibujar la ruta real basada en las carreteras (GeoJSON)
                    folium.GeoJson(ruta_optima["routes"][0]["geometry"], name="Ruta Óptima").add_to(m_resultado)

                    # 📌 Mostrar la distancia y tiempo estimado
                    distancia_total = ruta_optima["routes"][0]["distance"] / 1000  # Convertir de metros a kilómetros
                    st.sidebar.write(f"🚗 Distancia total de la ruta: {distancia_total:.2f} km")

                    tiempo_estimado = ruta_optima["routes"][0]["duration"] / 60  # Convertir de segundos a minutos
                    st.sidebar.write(f"⏱️ Tiempo estimado: {tiempo_estimado:.2f} minutos")

                # 📌 Mostrar el mapa con la ruta óptima
                folium_static(m_resultado)
            else:
                st.error("❌ No se pudo calcular la ruta óptima.")
