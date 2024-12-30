# app.py

import streamlit as st
import datetime
import pandas as pd
import altair as alt  # para los gráficos
import requests
import math
import json

# -------------------------------------------------------------------
# Configuración de la página (Debe ser la primera llamada de Streamlit)
# -------------------------------------------------------------------
st.set_page_config(page_title="Aplicación de Malee", layout="wide")

# -------------------------------------------------------------------
# AÑADIMOS Sucursales y funciones geocoding / nearest
# -------------------------------------------------------------------

# Función para cargar las sucursales desde un archivo JSON
@st.cache_data
def cargar_sucursales(archivo):
    try:
        with open(archivo, "r", encoding="utf-8") as file:
            sucursales = json.load(file)
        return sucursales
    except FileNotFoundError:
        st.error(f"No se encontró el archivo {archivo}.")
        return []

# Función para cargar sucursales desde un archivo CSV (si es necesario)
def cargar_sucursales_csv(archivo):
    try:
        df = pd.read_csv(archivo)
        sucursales = df.to_dict(orient="records")
        return sucursales
    except FileNotFoundError:
        st.error(f"No se encontró el archivo {archivo}.")
        return []

# Función de geocodificación (opcional)
def geocode_address_nominatim(address):
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": address, "format": "json", "addressdetails": 1, "limit": 1}
    headers = {"User-Agent": "malee-app/1.0 (mailto:tucorreo@ejemplo.com)"}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        data = resp.json()
        if not data:
            return None
        lat = float(data[0]["lat"])
        lon = float(data[0]["lon"])
        return lat, lon
    except (requests.RequestException, ValueError, KeyError):
        return None

# Función para calcular distancia Haversine
def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371.0  # Radio de la Tierra en km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# Función para encontrar la sucursal más cercana
def find_nearest_branch(user_lat, user_lon, sucursales):
    nearest = None
    min_dist = float("inf")
    for s in sucursales:
        try:
            dist = haversine_distance(user_lat, user_lon, float(s["lat"]), float(s["lng"]))
            if dist < min_dist:
                min_dist = dist
                nearest = s
        except (KeyError, ValueError, TypeError):
            continue
    return nearest, min_dist

# -------------------------------------------------------------------
# Carga de Sucursales desde el archivo actualizado
# -------------------------------------------------------------------
SUCURSALES = cargar_sucursales("sucursales_con_coordenadas_actualizado.json")

# -------------------------------------------------------------------
# Importamos las funciones del database.py (ajusta ruta si es necesario)
# -------------------------------------------------------------------
from database import (
    # Usuarios
    register_user, authenticate_user, check_admin_exists,
    get_all_pending_users, approve_user, delete_user, get_all_users,
    # Empleados
    get_all_empleados, create_empleado, update_empleado, delete_empleado,
    # Clientes
    get_all_clientes, create_cliente, update_cliente, delete_cliente,
    # Pedidos
    get_all_pedidos, create_pedido, update_pedido, delete_pedido,
    # Trabajos
    get_all_trabajos, create_trabajo, update_trabajo, delete_trabajo
)

# -------------------------------------------------------------------
# Sección de Login
# -------------------------------------------------------------------
def login_section():
    st.subheader("Iniciar Sesión")
    username = st.text_input("Usuario (Username/Email)")
    password = st.text_input("Contraseña", type="password")

    if st.button("Iniciar Sesión"):
        if username and password:
            user = authenticate_user(username, password)
            if user:
                st.session_state["user"] = user
                st.success(f"¡Bienvenido, {user['username']}!")
            else:
                st.error("Credenciales inválidas o usuario pendiente de aprobación.")
        else:
            st.error("Por favor, ingresa tanto el usuario como la contraseña.")

# -------------------------------------------------------------------
# Sección de Registro
# -------------------------------------------------------------------
def register_section():
    st.subheader("Registrarse")
    username = st.text_input("Nuevo usuario (o email)", key="register_username")
    password = st.text_input("Contraseña nueva", type="password", key="register_password")

    if st.button("Crear cuenta"):
        if username and password:
            data = register_user(username, password)
            if data:
                st.success("Cuenta creada. Puedes iniciar sesión (o esperar aprobación si no eres admin).")
            else:
                st.error("Error al crear cuenta. ¿Usuario ya existe?")
        else:
            st.error("Faltan datos para registrarse.")

# -------------------------------------------------------------------
# Gestión de usuarios (solo para Admin)
# -------------------------------------------------------------------
def admin_user_management():
    st.header("Gestión de Usuarios (Solo Admin)")

    # Mostrar usuarios pendientes
    st.subheader("Usuarios Pendientes")
    pending_users = get_all_pending_users()
    if not pending_users:
        st.write("No hay usuarios pendientes.")
    else:
        for user in pending_users:
            col1, col2, col3 = st.columns([3,2,2])
            with col1:
                st.write(f"ID: {user['id_user']} | Username: {user['username']}")
            with col2:
                new_role = st.selectbox("Rol a asignar", ["user", "admin"], key=f"role_{user['id_user']}")
            with col3:
                if st.button("Aprobar", key=f"approve_{user['id_user']}"):
                    approve_user(user['id_user'], new_role)
                    st.success(f"Usuario {user['username']} aprobado con rol '{new_role}'.")
                    st.experimental_rerun()

    # Mostrar todos los usuarios
    st.subheader("Todos los Usuarios")
    users = get_all_users()
    for user in users:
        with st.expander(f"{user['username']} (Rol: {user['rol']}, Activado: {user['activado']})"):
            if user['rol'] != "admin":  # Evitar borrar administradores
                if st.button("Eliminar Usuario", key=f"del_{user['id_user']}"):
                    delete_user(user['id_user'])
                    st.warning(f"Usuario {user['username']} eliminado.")
                    st.experimental_rerun()

# -------------------------------------------------------------------
# Empleados
# -------------------------------------------------------------------
def empleados_page():
    st.header("Gestión de Empleados")

    # Listar
    st.subheader("Lista de Empleados")
    empleados = get_all_empleados()
    if not empleados:
        st.info("No hay empleados registrados.")
    else:
        for emp in empleados:
            st.write(f"ID: {emp['id']} | {emp['nombre']} {emp['apellido']} | Cargo: {emp['cargo']}")

    # Crear
    st.subheader("Crear Empleado")
    with st.form("CrearEmpleadoForm"):
        col1, col2 = st.columns(2)
        with col1:
            nombre = st.text_input("Nombre")
            apellido = st.text_input("Apellido")
            telefono = st.text_input("Teléfono")
        with col2:
            direccion = st.text_input("Dirección")
            cargo = st.text_input("Cargo")
            id_user = st.number_input("ID_User (tabla usuarios)", min_value=1, step=1)

        submitted = st.form_submit_button("Crear Empleado")
        if submitted:
            if nombre and apellido and telefono and direccion and cargo and id_user:
                create_empleado(nombre, apellido, telefono, direccion, cargo, id_user)
                st.success("Empleado creado. Refresca la página para ver cambios.")
                st.experimental_rerun()
            else:
                st.error("Por favor, completa todos los campos.")

    # Actualizar/Eliminar
    st.subheader("Actualizar o Eliminar Empleado")
    if empleados:
        selected_emp = st.selectbox(
            "Selecciona un empleado:",
            empleados,
            format_func=lambda x: f"[ID: {x['id']}] {x['nombre']} {x['apellido']}"
        )
        if selected_emp:
            with st.form("ActualizarEmpleadoForm"):
                new_nombre = st.text_input("Nuevo Nombre", value=selected_emp.get('nombre',''))
                new_apellido = st.text_input("Nuevo Apellido", value=selected_emp.get('apellido',''))
                new_telefono = st.text_input("Nuevo Teléfono", value=selected_emp.get('telefono',''))
                new_direccion = st.text_input("Nueva Dirección", value=selected_emp.get('direccion',''))
                new_cargo = st.text_input("Nuevo Cargo", value=selected_emp.get('cargo',''))
                new_id_user = st.number_input("Nuevo ID_User",
                                              min_value=1,
                                              value=selected_emp.get('id_user',1),
                                              step=1)

                submitted_update = st.form_submit_button("Actualizar Empleado")
                if submitted_update:
                    if new_nombre and new_apellido and new_telefono and new_direccion and new_cargo and new_id_user:
                        update_empleado(
                            selected_emp['id'],
                            new_nombre,
                            new_apellido,
                            new_telefono,
                            new_direccion,
                            new_cargo,
                            new_id_user
                        )
                        st.success("Empleado actualizado. Refresca la página para ver cambios.")
                        st.experimental_rerun()
                    else:
                        st.error("Por favor, completa todos los campos.")

            if st.button("Eliminar Empleado"):
                delete_empleado(selected_emp['id'])
                st.warning("Empleado eliminado. Refresca la página para ver cambios.")
                st.experimental_rerun()

# -------------------------------------------------------------------
# Clientes
# -------------------------------------------------------------------
def clientes_page():
    st.header("Gestión de Clientes")

    # Listar
    st.subheader("Lista de Clientes")
    clientes = get_all_clientes()
    if not clientes:
        st.info("No hay clientes registrados.")
    else:
        for cli in clientes:
            st.write(f"ID: {cli['id_cliente']} | {cli['nombre']} {cli['apellido']} | Email: {cli['email']}")

    # Crear
    st.subheader("Crear Cliente")
    with st.form("CrearClienteForm"):
        col1, col2 = st.columns(2)
        with col1:
            nombre = st.text_input("Nombre")
            apellido = st.text_input("Apellido")
            telefono = st.text_input("Teléfono")
        with col2:
            direccion = st.text_input("Dirección")
            email = st.text_input("Email")

        submitted = st.form_submit_button("Crear Cliente")
        if submitted:
            if nombre and apellido and telefono and direccion and email:
                resultado = create_cliente(nombre, apellido, telefono, direccion, email)
                if resultado:
                    st.success("Cliente creado. Refresca la página para ver cambios.")
                    st.experimental_rerun()
                else:
                    st.error("No se pudo crear el cliente. Revisa los logs para más detalles.")
            else:
                st.error("Por favor, completa todos los campos.")

    # Actualizar/Eliminar
    st.subheader("Actualizar o Eliminar Cliente")
    if clientes:
        selected_cli = st.selectbox(
            "Selecciona un cliente:",
            clientes,
            format_func=lambda x: f"[ID: {x['id_cliente']}] {x['nombre']} {x['apellido']}"
        )
        if selected_cli:
            with st.form("ActualizarClienteForm"):
                new_nombre = st.text_input("Nuevo Nombre", value=selected_cli.get('nombre',''))
                new_apellido = st.text_input("Nuevo Apellido", value=selected_cli.get('apellido',''))
                new_telefono = st.text_input("Nuevo Teléfono", value=selected_cli.get('telefono',''))
                new_direccion = st.text_input("Nueva Dirección", value=selected_cli.get('direccion',''))
                new_email = st.text_input("Nuevo Email", value=selected_cli.get('email',''))

                submitted_update = st.form_submit_button("Actualizar Cliente")
                if submitted_update:
                    if new_nombre and new_apellido and new_telefono and new_direccion and new_email:
                        resultado = update_cliente(
                            selected_cli['id_cliente'],
                            new_nombre,
                            new_apellido,
                            new_telefono,
                            new_direccion,
                            new_email
                        )
                        if resultado:
                            st.success("Cliente actualizado. Refresca la página para ver cambios.")
                            st.experimental_rerun()
                        else:
                            st.error("No se pudo actualizar el cliente. Revisa los logs para más detalles.")
                    else:
                        st.error("Por favor, completa todos los campos obligatorios.")

            with st.form("EliminarClienteForm"):
                st.warning(f"¿Estás seguro de que deseas eliminar al cliente {selected_cli['nombre']} {selected_cli['apellido']}?")
                eliminar_cliente = st.form_submit_button("Eliminar Cliente")
                if eliminar_cliente:
                    resultado = delete_cliente(selected_cli['id_cliente'])
                    if resultado:
                        st.success("Cliente eliminado correctamente.")
                    else:
                        st.error("No se pudo eliminar el cliente. Revisa los logs para más detalles.")
                    st.experimental_rerun()


# -------------------------------------------------------------------
# Pedidos Unificados (seleccionando Cliente y Empleado por nombre)
# + Ubicar sucursal más cercana con Nominatim (gratuito)
# -------------------------------------------------------------------
def pedidos_unificados_page():
    st.header("Gestión de Pedidos (Clientes + Empleados en un solo formulario)")

    # ------------------------------------------------------
    # Sección para BUSCAR sucursal cercana sin almacenar
    # ------------------------------------------------------
    st.subheader("Buscar sucursal Correos de Chile más cercana")
    user_address = st.text_input("Dirección para ubicar sucursal más cercana (Calle, Ciudad, etc.)")

    # Utilizamos un formulario para encapsular la búsqueda y evitar recargas innecesarias
    with st.form("BuscarSucursalForm"):
        buscar_sucursal = st.form_submit_button("Buscar Sucursal Cercana")
        if buscar_sucursal:
            if user_address.strip() == "":
                st.error("Por favor, ingresa una dirección válida.")
            else:
                coords = geocode_address_nominatim(user_address)
                if coords is None:
                    st.warning("No se encontró la dirección o falló la geocodificación.")
                else:
                    lat_user, lon_user = coords
                    nearest, dist_km = find_nearest_branch(lat_user, lon_user, SUCURSALES)
                    if nearest:
                        # Asegúrate de que la clave correcta sea 'nombre' según tu JSON
                        sucursal_nombre = nearest.get("nombre", "Desconocida")
                        st.success(f"La sucursal más cercana es: {sucursal_nombre} (~{dist_km:.2f} km).")
                    else:
                        st.error("No se encontró ninguna sucursal en la lista local.")

    st.write("---")  # Línea divisoria

    # ------------------------------------------------------
    # Sección para CRUD de Pedidos
    # ------------------------------------------------------
    lista_clientes = get_all_clientes()    # [{'id_cliente':..., 'nombre':..., 'apellido':...}, ...]
    lista_empleados = get_all_empleados()  # [{'id':..., 'nombre':..., 'apellido':..., ...}, ...]

    # Validar que existan clientes y empleados
    if not lista_clientes:
        st.warning("No hay clientes registrados. Por favor, crea un cliente primero.")
        return

    if not lista_empleados:
        st.warning("No hay empleados registrados. Por favor, crea un empleado primero.")
        return

    dict_clientes = {c["id_cliente"]: c for c in lista_clientes}
    dict_empleados = {e["id"]: e for e in lista_empleados}
    pedidos_list = get_all_pedidos()

    # Listar Pedidos
    st.subheader("Lista de Pedidos")
    if not pedidos_list:
        st.write("No hay pedidos registrados.")
    else:
        for ped in pedidos_list:
            nom_cli = "Desconocido"
            if ped["cliente"] in dict_clientes:
                c = dict_clientes[ped["cliente"]]
                nom_cli = f"{c['nombre']} {c['apellido']}"

            nom_emp = "Desconocido"
            if ped["empleado_id"] in dict_empleados:
                e = dict_empleados[ped["empleado_id"]]
                nom_emp = f"{e['nombre']} {e['apellido']}"

            st.write(
                f"Pedido ID: {ped['id_pedido']} | "
                f"Cliente: {nom_cli} | "
                f"Empleado: {nom_emp} | "
                f"Estado: {ped.get('estado','')} | "
                f"Dirección: {ped.get('direccion','')}"
            )

    # Crear Pedido
    st.subheader("Crear Nuevo Pedido")
    with st.form("CrearPedidoForm"):
        col1, col2 = st.columns(2)
        with col1:
            seleccion_cliente = st.selectbox(
                "Selecciona Cliente",
                lista_clientes,
                format_func=lambda c: f"{c['nombre']} {c['apellido']}"
            )
            seleccion_empleado = st.selectbox(
                "Selecciona Empleado",
                lista_empleados,
                format_func=lambda e: f"{e['nombre']} {e['apellido']}"
            )

            detalles = st.text_area("Detalles del Pedido")
            fecha_pedido = st.date_input("Fecha del Pedido", datetime.date.today())
            estado = st.text_input("Estado (ej: Pendiente, Aprobado)", value="Pendiente")

        with col2:
            direccion = st.text_input("Dirección de Envío")
            color = st.text_input("Color (opcional)")
            rut = st.text_input("RUT (opcional)")
            region = st.text_input("Región (opcional)")

        submitted_create = st.form_submit_button("Crear Pedido")
        if submitted_create:
            if seleccion_cliente and seleccion_empleado and detalles and direccion:
                cliente_id = seleccion_cliente["id_cliente"]
                empleado_id = seleccion_empleado["id"]
                create_pedido(
                    cliente_id,
                    detalles,
                    fecha_pedido.isoformat(),
                    estado,
                    empleado_id,
                    direccion,
                    color,
                    rut,
                    region
                )
                st.success("Pedido creado. Refresca la página para ver cambios.")
                st.experimental_rerun()
            else:
                st.error("Por favor, completa todos los campos obligatorios.")

    # Actualizar / Eliminar Pedido
    st.subheader("Actualizar o Eliminar Pedido")
    if pedidos_list:
        selected_ped = st.selectbox(
            "Selecciona un pedido para modificar:",
            pedidos_list,
            format_func=lambda x: f"ID: {x['id_pedido']} (Cliente: {dict_clientes.get(x['cliente'], {}).get('nombre', 'Desconocido')} {dict_clientes.get(x['cliente'], {}).get('apellido', '')}, Empleado: {dict_empleados.get(x['empleado_id'], {}).get('nombre', 'Desconocido')} {dict_empleados.get(x['empleado_id'], {}).get('apellido', '')})"
        )

        if selected_ped:
            # Formulario para actualizar el pedido
            with st.form(f"ActualizarPedidoForm_{selected_ped['id_pedido']}"):
                st.write("### Actualizar Pedido ID:", selected_ped['id_pedido'])
                col1, col2 = st.columns(2)
                with col1:
                    # Selección de nuevo cliente
                    nuevo_cliente = st.selectbox(
                        "Nuevo Cliente",
                        lista_clientes,
                        index=lista_clientes.index(dict_clientes.get(selected_ped["cliente"], lista_clientes[0])),
                        format_func=lambda c: f"{c['nombre']} {c['apellido']}"
                    )

                    # Selección de nuevo empleado
                    nuevo_empleado = st.selectbox(
                        "Nuevo Empleado",
                        lista_empleados,
                        index=lista_empleados.index(dict_empleados.get(selected_ped["empleado_id"], lista_empleados[0])),
                        format_func=lambda e: f"{e['nombre']} {e['apellido']}"
                    )

                    # Nuevos detalles
                    new_detalles = st.text_area("Nuevos Detalles", value=selected_ped.get("detalles", ""))

                with col2:
                    # Nueva fecha del pedido
                    fecha_valor = selected_ped.get("fecha_pedido", str(datetime.date.today()))
                    try:
                        fecha_obj = datetime.datetime.fromisoformat(fecha_valor).date()
                    except:
                        fecha_obj = datetime.date.today()
                    new_fecha = st.date_input("Nueva Fecha Pedido", fecha_obj)

                    # Nuevo estado
                    new_estado = st.text_input("Nuevo Estado", value=selected_ped.get("estado", ""))

                    # Nueva dirección de envío
                    new_direccion = st.text_input("Nueva Dirección", value=selected_ped.get("direccion", ""))

                    # Nuevos campos opcionales
                    new_color = st.text_input("Nuevo Color", value=selected_ped.get("color", ""))
                    new_rut = st.text_input("Nuevo RUT", value=selected_ped.get("rut", ""))
                    new_region = st.text_input("Nueva Región", value=selected_ped.get("region", ""))

                submitted_update = st.form_submit_button("Actualizar Pedido")
                if submitted_update:
                    if nuevo_cliente and nuevo_empleado and new_detalles and new_direccion:
                        update_pedido(
                            selected_ped["id_pedido"],
                            nuevo_cliente["id_cliente"],
                            new_detalles,
                            new_fecha.isoformat(),
                            new_estado,
                            nuevo_empleado["id"],
                            new_direccion,
                            new_color,
                            new_rut,
                            new_region
                        )
                        st.success("Pedido actualizado. Refresca la página para ver cambios.")
                        st.experimental_rerun()
                    else:
                        st.error("Por favor, completa todos los campos obligatorios.")

            # Formulario para eliminar el pedido
            with st.form(f"EliminarPedidoForm_{selected_ped['id_pedido']}"):
                st.warning(f"¿Estás seguro de que deseas eliminar el Pedido ID {selected_ped['id_pedido']}?")
                eliminar_pedido = st.form_submit_button("Eliminar Pedido")
                if eliminar_pedido:
                    delete_pedido(selected_ped["id_pedido"])
                    st.warning("Pedido eliminado. Refresca la página para ver cambios.")
                    st.experimental_rerun()

# -------------------------------------------------------------------
# Página de Gráficos (Ejemplo)
# -------------------------------------------------------------------
def graficos_page():
    st.header("Gráficos de Pedidos por Región")

    pedidos_data = get_all_pedidos()
    if not pedidos_data:
        st.info("No hay pedidos registrados.")
        return

    df = pd.DataFrame(pedidos_data)
    if "region" not in df.columns:
        st.warning("No existe la columna 'region' en la tabla 'pedidos'.")
        return

    region_count = df.groupby("region")["id_pedido"].count().reset_index(name="count")
    chart = alt.Chart(region_count).mark_bar().encode(
        x=alt.X("region:N", title="Región"),
        y=alt.Y("count:Q", title="Cantidad de Pedidos"),
        tooltip=["region", "count"]
    ).properties(title="Pedidos por Región")
    st.altair_chart(chart, use_container_width=True)

# -------------------------------------------------------------------
# Menú principal / Navegación
# -------------------------------------------------------------------
def main_page():
    st.sidebar.title("Menú de Navegación")
    user_role = st.session_state["user"]["rol"]

    if user_role == "admin":
        choice = st.sidebar.selectbox("Opciones", [
            "Gestión de Usuarios",
            "Empleados",
            "Clientes",
            "Pedidos Unificados",
            "Gráficos",
            "Cerrar Sesión"
        ])
        if choice == "Gestión de Usuarios":
            admin_user_management()
        elif choice == "Empleados":
            empleados_page()
        elif choice == "Clientes":
            clientes_page()
        elif choice == "Pedidos Unificados":
            pedidos_unificados_page()
        elif choice == "Gráficos":
            graficos_page()
        elif choice == "Cerrar Sesión":
            st.session_state.pop("user", None)
            st.info("Sesión cerrada.")
            st.experimental_rerun()

    elif user_role == "user":
        choice = st.sidebar.selectbox("Opciones", [
            "Empleados",
            "Clientes",
            "Pedidos Unificados",
            "Gráficos",
            "Cerrar Sesión"
        ])
        if choice == "Empleados":
            empleados_page()
        elif choice == "Clientes":
            clientes_page()
        elif choice == "Pedidos Unificados":
            pedidos_unificados_page()
        elif choice == "Gráficos":
            graficos_page()
        elif choice == "Cerrar Sesión":
            st.session_state.pop("user", None)
            st.info("Sesión cerrada.")
            st.experimental_rerun()
    else:
        st.write(f"Tu rol actual es '{user_role}', no tienes acceso al menú.")
        if st.button("Cerrar Sesión"):
            st.session_state.pop("user", None)
            st.info("Sesión cerrada.")
            st.experimental_rerun()

# -------------------------------------------------------------------
# Lógica principal
# -------------------------------------------------------------------
def main():
    st.title("Aplicación de Malee")

    if "user" not in st.session_state:
        tab1, tab2 = st.tabs(["Iniciar Sesión", "Registrarse"])
        with tab1:
            login_section()
        with tab2:
            register_section()
    else:
        main_page()

if __name__ == "__main__":
    main()
