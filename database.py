# database.py

import os
from dotenv import load_dotenv
from supabase import create_client, Client
import bcrypt

# ---------------------------------------------------------------------
#             Carga de variables de entorno y conexión a Supabase
# ---------------------------------------------------------------------
load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise EnvironmentError("Las variables de entorno SUPABASE_URL y SUPABASE_KEY deben estar definidas.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------------------------------------------------------------------
#                  Utilidades para contraseñas (bcrypt)
# ---------------------------------------------------------------------
def hash_password(password: str) -> bytes:
    """
    Devuelve la contraseña hasheada en formato bytes usando bcrypt.
    """
    salt = bcrypt.gensalt()  # salt aleatorio
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed

def check_password(password: str, hashed: bytes) -> bool:
    """
    Verifica si la contraseña en texto plano coincide con la hasheada.
    """
    return bcrypt.checkpw(password.encode("utf-8"), hashed)

# ---------------------------------------------------------------------
#                  Manejo de Usuarios (Login / Registro)
# ---------------------------------------------------------------------
def check_admin_exists() -> bool:
    """
    Retorna True si existe al menos un usuario con rol='admin' y activado=True.
    """
    response = supabase.table("usuarios").select("*")\
        .eq("rol", "admin")\
        .eq("activado", True)\
        .execute()
    data = response.data
    return len(data) > 0 if data else False

def register_user(username: str, password: str):
    """
    Registra un nuevo usuario.
      - Si no existe admin, el primer usuario se crea con rol='admin', activado=True.
      - Si ya existe admin, se crea con rol='pendiente', activado=False.
    """
    # Verificar si ya hay admin
    if not check_admin_exists():
        rol = "admin"
        activado = True
    else:
        rol = "user"  # Asignar 'user' directamente o 'pendiente' según tu lógica
        activado = True  # Cambiar a False si deseas que los usuarios estén pendientes de aprobación

    hashed_pw = hash_password(password).decode("utf-8")
    data = supabase.table("usuarios").insert({
        "username": username,
        "pass": hashed_pw,
        "rol": rol,
        "activado": activado
    }).execute()
    return data.data

def authenticate_user(username: str, password: str):
    """
    Autentica a un usuario: debe tener activado=True, y contraseña bcrypt válida.
    """
    resp = supabase.table("usuarios").select("*")\
        .eq("username", username)\
        .eq("activado", True)\
        .execute()
    if not resp.data:
        return None

    user = resp.data[0]
    hashed_pw_db = user["pass"]  # Contraseña hasheada almacenada
    if check_password(password, hashed_pw_db.encode("utf-8")):
        return user
    return None

def get_all_pending_users():
    """
    Retorna todos los usuarios con rol='pendiente'.
    """
    response = supabase.table("usuarios").select("*").eq("rol", "pendiente").execute()
    return response.data

def approve_user(user_id: int, new_role="user"):
    """
    Cambia el rol de un usuario 'pendiente' a new_role y lo activa.
    """
    supabase.table("usuarios").update({
        "rol": new_role,
        "activado": True
    }).eq("id_user", user_id).execute()

def get_all_users():
    """
    Retorna todos los usuarios (admin, user, pendiente, etc.).
    """
    response = supabase.table("usuarios").select("*").execute()
    return response.data

def delete_user(user_id: int):
    """
    Elimina un usuario por su id_user.
    """
    supabase.table("usuarios").delete().eq("id_user", user_id).execute()

# ---------------------------------------------------------------------
#                  Empleados (CRUD)
# ---------------------------------------------------------------------
def get_all_empleados():
    resp = supabase.table("empleados").select("*").execute()
    return resp.data

def create_empleado(nombre, apellido, telefono, direccion, cargo, id_user):
    supabase.table("empleados").insert({
        "nombre": nombre,
        "apellido": apellido,
        "telefono": telefono,
        "direccion": direccion,
        "cargo": cargo,
        "id_user": id_user
    }).execute()

def update_empleado(empleado_id, nombre, apellido, telefono, direccion, cargo, id_user):
    supabase.table("empleados").update({
        "nombre": nombre,
        "apellido": apellido,
        "telefono": telefono,
        "direccion": direccion,
        "cargo": cargo,
        "id_user": id_user
    }).eq("id", empleado_id).execute()

def delete_empleado(empleado_id):
    supabase.table("empleados").delete().eq("id", empleado_id).execute()

# ---------------------------------------------------------------------
#                  Clientes (CRUD)
# ---------------------------------------------------------------------
def get_all_clientes():
    response = supabase.table("clientes").select("*").execute()
    return response.data

def create_cliente(nombre, apellido, telefono, direccion, email):
    supabase.table("clientes").insert({
        "nombre": nombre,
        "apellido": apellido,
        "telefono": telefono,
        "direccion": direccion,
        "email": email
    }).execute()

def update_cliente(cliente_id, nombre, apellido, telefono, direccion, email):
    supabase.table("clientes").update({
        "nombre": nombre,
        "apellido": apellido,
        "telefono": telefono,
        "direccion": direccion,
        "email": email
    }).eq("id_cliente", cliente_id).execute()

def delete_cliente(cliente_id):
    supabase.table("clientes").delete().eq("id_cliente", cliente_id).execute()

# ---------------------------------------------------------------------
#                         Pedidos (CRUD)
# ---------------------------------------------------------------------
def get_all_pedidos():
    resp = supabase.table("pedidos").select("*").execute()
    return resp.data

def create_pedido(cliente, detalles, fecha_pedido, estado, empleado_id,
                  direccion, color, rut, region):
    supabase.table("pedidos").insert({
        "cliente": cliente,
        "detalles": detalles,
        "fecha_pedido": fecha_pedido,
        "estado": estado,
        "empleado_id": empleado_id,
        "direccion": direccion,
        "color": color,
        "rut": rut,
        "region": region
    }).execute()

def update_pedido(id_pedido, cliente, detalles, fecha_pedido, estado,
                  empleado_id, direccion, color, rut, region):
    supabase.table("pedidos").update({
        "cliente": cliente,
        "detalles": detalles,
        "fecha_pedido": fecha_pedido,
        "estado": estado,
        "empleado_id": empleado_id,
        "direccion": direccion,
        "color": color,
        "rut": rut,
        "region": region
    }).eq("id_pedido", id_pedido).execute()

def delete_pedido(id_pedido):
    supabase.table("pedidos").delete().eq("id_pedido", id_pedido).execute()

# ---------------------------------------------------------------------
#                         Trabajos (CRUD)
# ---------------------------------------------------------------------
def get_all_trabajos():
    response = supabase.table("trabajos").select("*").execute()
    return response.data

def create_trabajo(titulo, descripcion, fecha_inicio, fecha_termino, estado, pedido_id, empleado_id):
    supabase.table("trabajos").insert({
        "titulo": titulo,
        "descripcion": descripcion,
        "fecha_inicio": fecha_inicio,
        "fecha_termino": fecha_termino,
        "estado": estado,
        "pedido_id": pedido_id,
        "empleado_id": empleado_id
    }).execute()

def update_trabajo(id_trabajo, titulo, descripcion, fecha_inicio, fecha_termino, estado, pedido_id, empleado_id):
    supabase.table("trabajos").update({
        "titulo": titulo,
        "descripcion": descripcion,
        "fecha_inicio": fecha_inicio,
        "fecha_termino": fecha_termino,
        "estado": estado,
        "pedido_id": pedido_id,
        "empleado_id": empleado_id
    }).eq("id_trabajo", id_trabajo).execute()

def delete_trabajo(id_trabajo):
    supabase.table("trabajos").delete().eq("id_trabajo", id_trabajo).execute()
