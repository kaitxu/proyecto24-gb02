import uuid
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
import requests

# Comando de ejecución: uvicorn Streamflix:app --reload --host localhost --port 8003

# Creación de la API de interfaz
app = FastAPI()

"""

Acceso a bases de datos antes de realizar los cambios de Docker

BASE_URL_CONTENIDOS = "http://127.0.0.1:8000"
BASE_URL_USUARIOS = "http://127.0.0.1:8001"
BASE_URL_INTERACCIONES = "http://127.0.0.1:8002"

"""


BASE_URL_CONTENIDOS = "http://contenidos:8000"  # Nombre del servicio 'contenidos' en docker-compose.yml
BASE_URL_USUARIOS = "http://usuarios:8001"    # Nombre del servicio 'usuarios' en docker-compose.yml
BASE_URL_INTERACCIONES = "http://interacciones:8002"  # Nombre del servicio 'interacciones' en docker-compose.yml


# Métodos auxiliares
def cargar_datos(user_id: str):
    """
    Obtiene y organiza los datos necesarios para la pantalla principal.
    """
    mensajes = []  # Lista para almacenar mensajes personalizados
    recomendaciones = []
    tendencias = []
    historial = []
    generos = []
    generos_con_contenidos = []
    lista_personalizada = []

    # Realizamos las solicitudes a los microservicios
    recomendaciones_response = requests.get(
        f"{BASE_URL_INTERACCIONES}/usuarios/{user_id}/recomendaciones"
    )
    if recomendaciones_response.ok:
        recomendaciones = recomendaciones_response.json()
    else:
        mensajes.append("No se pudieron obtener las recomendaciones personalizadas.")

    tendencias_response = requests.get(f"{BASE_URL_INTERACCIONES}/contenido/tendencias")
    if tendencias_response.ok:
        tendencias = tendencias_response.json()
    else:
        mensajes.append("No se pudieron obtener las tendencias.")

    historial_response = requests.get(
        f"{BASE_URL_INTERACCIONES}/usuarios/{user_id}/historial"
    )
    if historial_response.ok:
        historial = historial_response.json()
    else:
        mensajes.append("No se pudo recuperar el historial de usuario.")

    generos_response = requests.get(f"{BASE_URL_CONTENIDOS}/generos")
    if generos_response.ok:
        generos = generos_response.json()
    else:
        mensajes.append("No se pudieron obtener los géneros.")

    # Recuperar los contenidos por género
    for genero in generos:
        contenidos_response = requests.get(
            f"{BASE_URL_CONTENIDOS}/generos/{genero['id']}/contenidos"
        )
        if contenidos_response.ok:
            generos_con_contenidos.append(
                {"nombre": genero["nombre"], "contenidos": contenidos_response.json()}
            )
        else:
            mensajes.append(
                f"No se pudieron obtener los contenidos para el género {genero['nombre']}."
            )

    lista_personalizada_response = requests.get(f"{BASE_URL_INTERACCIONES}/usuarios/{user_id}/listaPersonalizada")
    if lista_personalizada_response.ok:
        lista_personalizada = lista_personalizada_response.json()
    else:
        mensajes.append("No se pudo obtener la lista personalizada.")

    # Si no hay mensajes, significa que todo salió bien
    if not mensajes:
        mensajes.append("Los datos se cargaron correctamente.")

    return {
        "recomendaciones": recomendaciones,
        "tendencias": tendencias,
        "historial": historial,
        "generos_con_contenidos": generos_con_contenidos,
        "lista_personalizada": lista_personalizada,
        "mensaje": " | ".join(mensajes),  # Unimos todos los mensajes en una sola cadena
    }


# Configuración de rutas estáticas para CSS
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configuración de plantillas Jinja2
templates = Jinja2Templates(directory="templates")


# Endpoint para la página principal
@app.get("/", response_class=HTMLResponse)
async def index(request: Request, mensaje_credenciales: str = None):
    # Renderiza la página index.html y la devuelve al usuario
    return templates.TemplateResponse("index.html", 
                                      {"request": request,
                                       "mensaje_credenciales": mensaje_credenciales})


# Endpoint para hacer login
@app.post("/login")
async def login(request: Request, email: str = Form(...), password: str = Form(...)):
    # Enviar las credenciales al microservicio para verificar el login
    data = {"email": email, "password": password}
    response = requests.post(f"{BASE_URL_USUARIOS}/usuarios/login", json=data)

    if response.status_code != 200:
        mensaje_credenciales = "Error: las credenciales no son correctas"
        response_redirect = RedirectResponse(url=f"/?mensaje_credenciales={mensaje_credenciales}", status_code=303)
        return response_redirect

    # Si las credenciales son correctas, obtenemos los datos del usuario
    user_data = response.json()
    user_id = user_data.get("id")

    # Redirigimos al endpoint de pantalla principal con el `user_id`
    response_redirect = RedirectResponse(url=f"/pantalla_principal?user_id={user_id}", status_code=303)
    response_redirect.set_cookie(key="user_id", value=user_id)
    return response_redirect



# Endpoint para mostrar la página de registro
@app.get("/registro_usuario", response_class=HTMLResponse)
async def registro_usuario(request: Request):
    return templates.TemplateResponse("registro_usuario.html", {"request": request})


# Endpoint para obtener los planes de suscripción
@app.get("/planes_suscripcion")
async def obtener_planes():
    # Aquí haces una solicitud a tu microservicio que devuelve los planes
    response = requests.get(f"{BASE_URL_USUARIOS}/planes-suscripcion")
    if response.status_code != 200:
        raise HTTPException(
            status_code=500, detail="No se pudieron obtener los planes."
        )
    return response.json()


@app.post("/registro")
async def registrar_usuario(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    language: str = Form(None),
    subscription_plan: str = Form(...),
):
    # Datos para el microservicio de usuarios
    data = {
        "nombre": name,
        "email": email,
        "password": password,
        "idioma": language,
        "idPlanSuscripcion": subscription_plan,
    }
    response = requests.post(f"{BASE_URL_USUARIOS}/usuarios/registro", json=data)

    if response.status_code != 200:
        mensaje_credenciales = "Error: Las credenciales ya están en uso"
        return RedirectResponse(
        url=f"/?mensaje_credenciales={mensaje_credenciales}", status_code=303
    )

    # Guardamos el id del usuario retornado
    user_data = response.json()
    user_id = user_data.get("id")

    # Redirigimos al endpoint de pantalla principal con el `user_id`
    return RedirectResponse(
        url=f"/pantalla_principal?user_id={user_id}", status_code=303
    )


# Endpoint para mostrar los detalles de un contenido
@app.get("/detalles_contenido/{idContenido}", response_class=HTMLResponse)
async def detalles_contenido(request: Request, idContenido: str, user_id: str):
    # Solicita los detalles del contenido al microservicio de contenidos
    contenido = requests.get(f"{BASE_URL_CONTENIDOS}/contenidos/{idContenido}")

    if contenido.status_code != 200:
        raise HTTPException(
            status_code=404, detail="No se encontraron los detalles de la película."
        )

    # Extrae los detalles de la película del JSON de la respuesta
    detalles_contenido = contenido.json()

    #Extraer nombre del genero a partir del id
    genero = requests.get(f"{BASE_URL_CONTENIDOS}/generos/{detalles_contenido['idGenero']}")
    detalles_genero = genero.json()
    nombre_genero = detalles_genero["nombre"]

    if detalles_contenido["tipoContenido"] == "Pelicula":
        #Extraer nombre del director a partir del id
        director = requests.get(f"{BASE_URL_CONTENIDOS}/directores/{detalles_contenido['idDirector']}")
        detalles_director = director.json()
        nombre_director = detalles_director["nombre"]
        detalles_contenido["idDirector"] = nombre_director
        temporadas = None
        todos_los_episodios = None
    else:
        # Obtener las temporadas y los capítulos de una serie
        temps_caps = requests.get(f"{BASE_URL_CONTENIDOS}/series/{detalles_contenido['id']}")
        detalles_temps_caps = temps_caps.json()

        # Obtener todas las temporadas
        temporadas = detalles_temps_caps["Temporadas"]

        # Lista para almacenar todos los episodios
        todos_los_episodios = []

        # Recorrer las temporadas para acceder a los episodios
        for temporada in temporadas:
            episodios = temporada["Episodios"]  # Acceder a los episodios de la temporada
            for episodio in episodios:
                idDirector = episodio.get("idDirector")
                if idDirector:  # Verificar si existe un idDirector
                    director_response = requests.get(f"{BASE_URL_CONTENIDOS}/directores/{idDirector}")
                    if director_response.status_code == 200:
                        director_data = director_response.json()
                        episodio["director"] = director_data.get("nombre", "Desconocido")
                    else:
                        raise HTTPException(
                            status_code=404, detail="No se encontraron los detalles del director del episodio."
                        )
            todos_los_episodios.extend(episodios) # Agregar todos los episodios a la lista


    #Cambiar los valores de ids por nombres
    detalles_contenido["idGenero"] = nombre_genero
    

    #Obtener el reparto
    reparto = requests.get(f"{BASE_URL_CONTENIDOS}/contenidos/{detalles_contenido['id']}/reparto")
    detalles_reparto = reparto.json()

    #Obtener los subtitulos
    subtitulos = requests.get(f"{BASE_URL_CONTENIDOS}/contenidos/{detalles_contenido['idSubtitulosContenido']}/subtitulos")
    detalles_subtitulos = subtitulos.json()
    
    #Obtener los doblajes
    doblajes = requests.get(f"{BASE_URL_CONTENIDOS}/contenidos/{detalles_contenido['idDoblajeContenido']}/doblajes")
    detalles_doblajes = doblajes.json()
         
    # Obtener el historial
    esta_en_historial = False
    historial_response = requests.get(f"{BASE_URL_INTERACCIONES}/usuarios/{user_id}/historial")

    # Validar que la respuesta sea válida
    if historial_response.status_code == 200:
        historial = historial_response.json()
        if isinstance(historial, list) and len(historial) > 0:  # Verificar si es una lista no vacía
            if any(content["id"] == idContenido for content in historial):
                esta_en_historial = True
    else:
        #print(f"No se ha obtenido el historial: {historial_response.status_code}")
        historial = []

    # Si no está en el historial, agregarlo
    if not esta_en_historial:
        try:
            response = requests.post(f"{BASE_URL_INTERACCIONES}/usuarios/{user_id}/historial/{idContenido}")
            if response.status_code == 200:
                print(f"Contenido {idContenido} agregado al historial.")
            else:
                print(f"Error al agregar contenido al historial: {response.status_code}")
        except Exception as e:
            print(f"Error al comunicarse con POST en HISTORIAL: {e}")
        
    # Renderiza la plantilla detalles_contenido.html con los datos de la película
    return templates.TemplateResponse("detalles_contenido.html", {
        "request": request,
        "detalles_contenido": detalles_contenido,
        "reparto": detalles_reparto,
        "subtitulos": detalles_subtitulos,
        "doblajes": detalles_doblajes,
        "temporadas": temporadas,
        "episodios": todos_los_episodios,
        "user_id": user_id
    })


@app.get("/buscar", response_class=HTMLResponse)
async def buscar(request: Request, query: str, tipo: str):

    user_id = request.cookies.get("user_id")

    contenidos = []  # Variable para almacenar contenidos
    actores = []     # Variable para almacenar actores
    mensaje = ""

    if tipo == "contenido":
        # Búsqueda de contenidos
        response = requests.get(f"{BASE_URL_CONTENIDOS}/contenidos/{query}/buscar")
        if response.status_code == 200:
            contenidos = response.json().get("resultados", [])
    elif tipo == "actor":
        # Búsqueda de actores
        response = requests.get(f"{BASE_URL_CONTENIDOS}/contenidos/{query}/actores")
        if response.status_code == 200:
            actores = response.json().get("resultados", [])
    elif tipo == "todos":
        # Búsqueda combinada
        response_contenido = requests.get(f"{BASE_URL_CONTENIDOS}/contenidos/{query}/buscar")
        response_actor = requests.get(f"{BASE_URL_CONTENIDOS}/contenidos/{query}/actores")

        # Almacenar resultados si las respuestas son exitosas
        if response_contenido.status_code == 200:
            contenidos = response_contenido.json().get("resultados", [])
        if response_actor.status_code == 200:
            actores = response_actor.json().get("resultados", [])
    else:
        raise HTTPException(status_code=400, detail="Tipo de búsqueda no válido")

    # Si no hay resultados en ninguno de los tipos, asignamos un mensaje
    if not contenidos and not actores:
        mensaje = "No se han encontrado resultados."

    # Para devolver las peliculas en las que ha participado un actor
    contenidos_por_actor = {}  # Diccionario para almacenar contenidos por actor
    if actores:
        for actor in actores:
            # Obtenemos los contenidos relacionados con el actor
            response_contenidos_actor = requests.get(f"{BASE_URL_CONTENIDOS}/actores/{actor['id']}/contenidos")
            if response_contenidos_actor.status_code == 200:
                # Guardamos los contenidos del actor en el diccionario usando el id del actor
                contenidos_por_actor[actor['id']] = response_contenidos_actor.json()


    # Renderizamos la página con los resultados separados
    return templates.TemplateResponse(
        "resultados_busqueda.html",
        {
            "request": request,
            "user_id": user_id,
            "contenidos": contenidos,
            "actores": actores,
            "contenidos_por_actor": contenidos_por_actor,
            "tipo": tipo,
            "query": query,
            "mensaje": mensaje
        }
    )


import logging
logging.basicConfig(level=logging.INFO)

@app.get("/pantalla_principal", response_class=HTMLResponse)
async def pantalla_principal(request: Request, user_id: str = None, mensaje_credenciales: str = None):
    datos = cargar_datos(user_id)  # Centralizamos la lógica aquí
    mensaje = datos.get("mensaje", "Error al cargar los datos")

    # Renderizamos la pantalla principal
    return templates.TemplateResponse(
        "pantalla_principal.html",
        {
            "request": request,
            "user_id": user_id,
            "recomendaciones": datos["recomendaciones"],
            "tendencias": datos["tendencias"],
            "historial": datos["historial"],
            "generos_con_contenidos": datos["generos_con_contenidos"],
            "lista_personalizada": datos["lista_personalizada"],
            "mensaje": mensaje,
            "mensaje_credenciales": mensaje_credenciales,
        }
    )

@app.get("/usuarios/{user_id}/perfil", response_class=HTMLResponse)
async def get_user_profile(request: Request, user_id: str, mensaje: str = None):
    # Llama al endpoint /perfil para obtener el perfil de un usuario y lo renderiza en HTML
    response = requests.get(f"{BASE_URL_USUARIOS}/usuarios/{user_id}")
    me_gusta_response = requests.get(
        f"{BASE_URL_INTERACCIONES}/usuarios/{user_id}/me-gusta"
    )

    if response.status_code == 200:
        # Obtiene los datos del perfil del usuario
        user_profile = response.json()

        # Inicializa los datos de "Me Gusta"
        contenidos_me_gusta = []
        mensaje_me_gusta = None

        if me_gusta_response.status_code == 200:
            # Obtiene la lista de contenidos "Me Gusta" y la convierte a una lista de objetos ContenidoMeGusta
            me_gusta_data = me_gusta_response.json()
            contenidos_me_gusta = [
                {
                    "id": contenido["id"],
                    "titulo": contenido["titulo"],
                    "descripcion": contenido.get("descripcion", ""),
                    "fechaLanzamiento": contenido["fechaLanzamiento"],
                    "idGenero": contenido["idGenero"],
                    "valoracionPromedio": contenido.get("valoracionPromedio", None),
                    "idSubtitulosContenido": contenido.get(
                        "idSubtitulosContenido", None
                    ),
                    "idDoblajeContenido": contenido.get("idDoblajeContenido", None),
                }
                for contenido in me_gusta_data
            ]
        else:
            # Si no hay "Me Gusta", guarda un mensaje indicando que no existen
            mensaje_me_gusta = "No existen 'Me Gusta' para este usuario."

        # Renderiza la plantilla HTML con los datos del perfil y los "Me Gusta"
        return templates.TemplateResponse(
            "perfil.html",  # Plantilla HTML que renderizará los datos
            {
                "request": request,
                "user_id": user_id,
                "nombre": user_profile["nombre"],
                "email": user_profile["email"],
                "password": user_profile["password"],
                "me_gusta": contenidos_me_gusta,  # Pasa la lista de contenidos "Me Gusta"
                "mensaje_me_gusta": mensaje_me_gusta,  # Pasa el mensaje en caso de que no haya "Me Gusta"
                "mensaje": mensaje,
            },
        )
    else:
        # En caso de error al obtener los datos del perfil
        error_message = (
            f"Error al obtener el perfil del usuario: {response.status_code}"
        )
        return templates.TemplateResponse(
            "perfil.html",
            {
                "request": request,
                "error_message": error_message,
            },
        )


@app.delete("/interacciones/me-gusta")
async def eliminar_interaccion(request: Request):
    """
    Endpoint para manejar la eliminación de una interacción "Me Gusta"
    en el sistema de interacciones.
    """
    # Leer el cuerpo de la solicitud
    datos = await request.json()

    # Extraer idUsuario e idContenido
    id_usuario = datos.get("idUsuario")
    idContenido = datos.get("idContenido")

    # Validar que los datos requeridos estén presentes
    if not id_usuario or not idContenido:
        raise HTTPException(
            status_code=400, detail="Faltan datos obligatorios: idUsuario o idContenido"
        )

    # Construir la URL de la API de interacciones
    url = f"{BASE_URL_INTERACCIONES}/usuarios/{id_usuario}/me-gusta/{idContenido}"

    # Realizar la petición DELETE a la API de interacciones
    try:
        response = requests.delete(url)

        # Verificar el estado de la respuesta
        if response.status_code == 200:
            return {"message": "Interacción eliminada correctamente"}
        elif response.status_code == 404:
            raise HTTPException(status_code=404, detail="Interacción no encontrada")
        else:
            raise HTTPException(
                status_code=500, detail="Error al eliminar la interacción"
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al comunicarse con la API de interacciones: {str(e)}",
        )


@app.post("/usuarios/{id_usuario}/perfil")
async def actualizar_perfil(request: Request, id_usuario: str):
    """
    Endpoint para actualizar el perfil de un usuario.
    """
    data = await request.form()

    # Extraemos los datos del JSON recibido
    nombre = data.get("name")
    password = data.get("password")
    email = data.get("email")  # Aunque no editable, se puede validar
    idioma = data.get("language")

    # Construir el payload para la API externa
    payload = {"nombre": nombre, "password": password, "email": email, "idioma": idioma}

    # URL del endpoint de la API externa para actualizar el perfil
    api_url = f"{BASE_URL_USUARIOS}/usuarios/{id_usuario}/perfil"

    try:
        # Enviar la solicitud PUT a la API externa
        response = requests.put(api_url, json=payload)

        # Comprobar el estado de la respuesta de la API
        if response.status_code == 200:
            mensaje = "Perfil actualizado exitosamente"
            data = response.json()
            return RedirectResponse(
                url=f"/usuarios/{id_usuario}/perfil?mensaje={mensaje}", status_code=303
            )
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail="Error al actualizar el perfil en la API externa",
            )

    except requests.exceptions.RequestException as e:
        # Manejar errores de red o conexión
        raise HTTPException(
            status_code=500, detail=f"Error al comunicarse con la API externa: {str(e)}"
        )


@app.get("/perfil_usuario/{user_id}")
async def obtener_perfil_usuario(user_id: str):
    """
    Obtiene los datos del perfil del usuario desde la API de usuarios.
    """
    try:
        # Hacer una solicitud GET al servicio de usuarios para obtener el perfil
        response = requests.get(f"{BASE_URL_USUARIOS}/usuarios/{user_id}")

        if response.status_code != 200:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        # Obtener los datos del usuario
        user_data = response.json()

        # Devolver los datos del usuario
        return {
            "nombre": user_data["nombre"],
            "email": user_data["email"],
            "idioma": user_data.get("idioma", "es"),  # Asumir 'es' si no está presente
        }
    except requests.exceptions.RequestException as e:
        # En caso de error al hacer la petición a la API de usuarios
        raise HTTPException(
            status_code=500, detail=f"Error al obtener el perfil del usuario: {str(e)}"
        )


@app.get("/usuarios/{userId}/me-gusta")
def obtener_me_gusta(userId: str):

    try:
        # Hacer una solicitud GET al servicio de usuarios para obtener el perfil
        response = requests.get(f"{BASE_URL_INTERACCIONES}/usuarios/{userId}/me-gusta")

        if response.status_code != 200:
            raise HTTPException(
                status_code=404,
                detail="No se han encontrado contenidos a los que el usuario le haya dado me gusta",
            )

        # Obtener los datos del usuario
        contenidos = response.json()

        # Devolver los datos del usuario
        return contenidos
    except requests.exceptions.RequestException as e:
        # En caso de error al hacer la petición a la API de usuarios
        raise HTTPException(
            status_code=500, detail=f"Error al obtener el perfil del usuario: {str(e)}"
        )


@app.get("/usuarios/{user_id}/metodos-pago")
async def get_user_payment_methods(user_id: str):
    """
    Este endpoint obtiene los métodos de pago de un usuario a través de la API de usuarios
    y devuelve una lista con los métodos de pago (Tarjeta o PayPal).
    """
    # Hacemos la petición GET a la API de usuarios para obtener los métodos de pago
    try:
        response = requests.get(f"{BASE_URL_USUARIOS}/usuarios/{user_id}/metodos-pago")

        # Verificamos si la respuesta fue exitosa
        if response.status_code == 200:
            payment_methods = response.json()
            # Formateamos la respuesta según el esquema necesario
            formatted_methods = []
            for method in payment_methods:
                if method["tipo"] == "Tarjeta de Crédito":
                    formatted_methods.append(
                        {
                            "tipo": method["tipo"],
                            "numeroTarjeta": method.get("numeroTarjeta"),
                            "emailPaypal": None,
                        }
                    )
                elif method["tipo"] == "Paypal":
                    formatted_methods.append(
                        {
                            "tipo": method["tipo"],
                            "numeroTarjeta": None,
                            "emailPaypal": method.get("emailPaypal"),
                        }
                    )
            return formatted_methods
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail="Error al obtener métodos de pago del usuario",
            )

    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=500, detail=f"Error al comunicar con la API externa: {str(e)}"
        )


@app.post("/usuarios/{user_id}/metodos-pago")
async def add_payment_method(user_id: str, request: Request):
    try:
        # Obtener los datos del formulario
        form_data = await request.form()
        payment_method = form_data.get("payment-method")

        # Preparar los datos según el tipo de método de pago
        if payment_method == "credit_card":
            numero_tarjeta = form_data.get("numeroTarjeta")
            data = {
                "tipo": "Tarjeta de Crédito",
                "numeroTarjeta": numero_tarjeta,
                "emailPaypal": None,  # No se utiliza para tarjeta de crédito
            }
        elif payment_method == "paypal":
            email = form_data.get("email")
            data = {
                "tipo": "Paypal",
                "numeroTarjeta": None,  # No se utiliza para PayPal
                "emailPaypal": email,
            }
        else:
            raise HTTPException(status_code=400, detail="Método de pago no válido")

        # Realizar la solicitud POST al servicio de la API de usuarios para agregar el método de pago
        response = requests.post(
            f"{BASE_URL_USUARIOS}/usuarios/{user_id}/metodos-pago", json=data
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=500, detail="Error al agregar el método de pago"
            )
        mensaje = "Método de pago añadido exitosamente"
        return RedirectResponse(url=f"/usuarios/{user_id}/perfil?mensaje={mensaje}", status_code=303)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Funciones para la gestión del administrador

@app.get("/admin_menu", response_class=HTMLResponse)
async def admin_menu(request: Request):
    peliculas_response = requests.get(f"{BASE_URL_CONTENIDOS}/todopeliculas")
    series_response = requests.get(f"{BASE_URL_CONTENIDOS}/series")
    actores_response = requests.get(f"{BASE_URL_CONTENIDOS}/actores")
    directores_response = requests.get(f"{BASE_URL_CONTENIDOS}/directores")
    generos_response = requests.get(f"{BASE_URL_CONTENIDOS}/generos")

    if peliculas_response.status_code == 200:
        peliculas = peliculas_response.json()

    if series_response.status_code == 200:
        series = series_response.json()

    if actores_response.status_code == 200:
        actores = actores_response.json()
    
    if directores_response.status_code == 200:
        directores = directores_response.json()

    if generos_response.status_code == 200:
        generos = generos_response.json()

    success_message = request.cookies.get("success_message")
    # Renderizamos el menu de admin.
    response = templates.TemplateResponse(
        "admin_menu.html",
        {
            "request": request,
            "peliculas": peliculas,
            "series": series,
            "actores": actores,
            "directores": directores,
            "generos": generos,
            "message": success_message,
        },
    )
    response.delete_cookie("success_message")
    return response

@app.get("/administrador/usuarios", response_class=HTMLResponse)
async def lista_usuarios(request: Request):
    # Realizamos la solicitud al microservicio de usuarios
    response = requests.get(f"{BASE_URL_USUARIOS}/usuarios")
    if response.status_code != 200:
        raise HTTPException(
            status_code=500, detail="No se pudieron obtener los usuarios."
        )

    usuarios = response.json()  # Suponiendo que la respuesta es una lista de usuarios

    return templates.TemplateResponse(
        "admin_usuarios.html",
        {
            "request": request,
            "usuarios": usuarios,
        },
    )

TEMPLATE_CREAR_PELICULA_HTML = "admin_crear_pelicula.html"

@app.get("/administrador/pelicula/crear", response_class=HTMLResponse)
async def crear_pelicula_form(request: Request):
    """
    Muestra el formulario para crear una película.
    """
    # Obtener los géneros y directores desde el microservicio de contenidos
    generos_response = requests.get(f"{BASE_URL_CONTENIDOS}/generos")

    generos = generos_response.json() if generos_response.status_code == 200 else []
    
    # Realizar una solicitud GET a la API de contenidos para obtener la lista de directores
    directores_response = requests.get(f"{BASE_URL_CONTENIDOS}/directores")

    # Verifica si la respuesta fue exitosa
    directores = directores_response.json() if directores_response.status_code == 200 else []

    # Realizar una solicitud GET a la API de contenidos para obtener la lista de actores
    actores_response = requests.get(f"{BASE_URL_CONTENIDOS}/actores")

    # Verifica si la respuesta fue exitosa
    actores = actores_response.json() if actores_response.status_code == 200 else []    

    return templates.TemplateResponse(
    TEMPLATE_CREAR_PELICULA_HTML,  # Nombre de la plantilla
    {
        "request": request,
        "generos": generos,
        "directores": directores,
        "actores": actores,
    },
)


@app.post("/administrador/pelicula/crear", response_class=HTMLResponse)
async def crear_pelicula(
    request: Request,
    titulo: str = Form(...),
    descripcion: str = Form(...),
    fecha_lanzamiento: str = Form(...),
    id_genero: str = Form(...),
    duracion: int = Form(...),
    idDirector: str = Form(...),
    actores: list[str] = Form(...),
):
    """
    Procesa el formulario para crear una película.
    """
    data = {
        "tipoContenido": "Pelicula",
        "titulo": titulo,
        "descripcion": descripcion,
        "fechaLanzamiento": fecha_lanzamiento,
        "idGenero": id_genero,
        "valoracionPromedio": 0.0,
        "duracion": duracion,
        "idDirector": idDirector,
    }

    response = requests.post(f"{BASE_URL_CONTENIDOS}/peliculas", json=data)

    if response.status_code == 200:
        idPelicula = response.json().get("id")

        # Añadir los actores uno por uno al reparto del contenido
        for idActor in actores:
            response = requests.post(f"{BASE_URL_CONTENIDOS}/contenidos/{idPelicula}/reparto/{idActor}")

            if response.status_code != 200:
                return templates.TemplateResponse(
                    TEMPLATE_CREAR_PELICULA_HTML,
                    {
                        "request": request,
                        "error_message": f"Error al añadir el actor al reparto. Por favor, inténtelo de nuevo.",
                    }
                )

        redirect_response = RedirectResponse(url=f"/admin_menu", status_code=303)
        redirect_response.set_cookie(
            key="success_message", value="Película creada exitosamente", max_age=5
        )
        return redirect_response
    else:
        return templates.TemplateResponse(
            TEMPLATE_CREAR_PELICULA_HTML,
            {
                "request": request,
                "error_message": "Error al crear la película. Por favor, inténtelo de nuevo.",
            }
        )

TEMPLATE_CREAR_SERIE_HTML = "admin_crear_serie.html"

@app.get("/administrador/serie/crear", response_class=HTMLResponse)
async def crear_serie_form(request: Request):
    """
    Muestra el formulario para crear una serie.
    """
    # Obtener los géneros y directores desde el microservicio de contenidos
    generos_response = requests.get(f"{BASE_URL_CONTENIDOS}/generos")

    generos = generos_response.json() if generos_response.status_code == 200 else []

    # Realizar una solicitud GET a la API de contenidos para obtener la lista de actores
    actores_response = requests.get(f"{BASE_URL_CONTENIDOS}/actores")

    # Verifica si la respuesta fue exitosa
    actores = actores_response.json() if actores_response.status_code == 200 else []      

    return templates.TemplateResponse(
        TEMPLATE_CREAR_SERIE_HTML,
        {
            "request": request,
            "generos": generos,
            "actores": actores,
        },
    )


@app.post("/administrador/serie/crear", response_class=HTMLResponse)
async def crear_serie(
    request: Request,
    titulo: str = Form(...),
    descripcion: str = Form(...),
    fecha_lanzamiento: str = Form(...),
    id_genero: str = Form(...),
    actores: list[str] = Form(...),    
):
    """
    Procesa el formulario para crear una serie.
    """
    data = {
        "tipoContenido": "Serie",
        "titulo": titulo,
        "descripcion": descripcion,
        "fechaLanzamiento": fecha_lanzamiento,
        "idGenero": id_genero,
        "valoracionPromedio": 0.0,
        "duracion": None,
        "idDirector": None,
    }

    response = requests.post(f"{BASE_URL_CONTENIDOS}/series", json=data)

    if response.status_code == 200:
        idSerie = response.json().get("id")

        # Añadir los actores uno por uno al reparto del contenido
        for idActor in actores:
            response = requests.post(f"{BASE_URL_CONTENIDOS}/contenidos/{idSerie}/reparto/{idActor}")

            if response.status_code != 200:
                return templates.TemplateResponse(
                    TEMPLATE_CREAR_SERIE_HTML,
                    {
                        "request": request,
                        "error_message": f"Error al añadir el actor al reparto. Por favor, inténtelo de nuevo.",
                    }
                )

        redirect_response = RedirectResponse(url=f"/admin_menu", status_code=303)
        redirect_response.set_cookie(
            key="success_message", value="Serie creada exitosamente", max_age=5
        )
        return redirect_response

        redirect_response = RedirectResponse(url="/admin_menu", status_code=303)
        redirect_response.set_cookie(
            key="success_message", value="Serie creada exitosamente", max_age=5
        )
        return redirect_response
    else:
        return templates.TemplateResponse(
            TEMPLATE_CREAR_SERIE_HTML,
            {
                "request": request,
                "error_message": "Error al crear la serie. Por favor, inténtelo de nuevo.",
            },
        )
    

@app.get("/administrador/temporada/crear", response_class=HTMLResponse)
async def crear_temporada_form(request: Request):
    """
    Muestra el formulario para crear una temporada de una serie.
    """
    # Obtener los géneros y directores desde el microservicio de contenidos
    series_response = requests.get(f"{BASE_URL_CONTENIDOS}/todoseries")

    series = series_response.json() if series_response.status_code == 200 else []

    return templates.TemplateResponse(
        "admin_crear_temporada.html",
        {
            "request": request,
            "series": series,
        },
    )


@app.post("/administrador/temporada/crear", response_class=HTMLResponse)
async def crear_temporada(
    request: Request,
    id_serie : str = Form (...),
    numeroTemporada: int = Form(...)
):
    """
    Procesa el formulario para crear una temporada de una serie.
    """
    data = {
        "idContenido": id_serie,
        "numeroTemporada": numeroTemporada
    }

    response = requests.post(f"{BASE_URL_CONTENIDOS}/contenidos/{id_serie}/temporadas", json=data)

    if response.status_code == 200:
        redirect_response = RedirectResponse(url="/admin_menu", status_code=303)
        redirect_response.set_cookie(
            key="success_message", value="Temporada creada exitosamente", max_age=5
        )
        return redirect_response
    else:
        return templates.TemplateResponse(
            "admin_crear_temporada.html",
            {
                "request": request,
                "error_message": "Error al crear la temporada. Por favor, inténtelo de nuevo.",
            },
        )


@app.get("/administrador/genero/crear", response_class=HTMLResponse)
async def crear_genero_form(request: Request):
    """
    Muestra el formulario para crear un género de contenido multimedia.
    """
    return templates.TemplateResponse(
        "admin_crear_genero.html",
        {
            "request": request,
        },
    )


@app.get("/contenidos/{idSerie}/temporadas")
async def obtener_temporadas(idSerie: str):
    """
    Endpoint para obtener todas las temporadas de una serie específica.
    """
    # Obtener temporadas desde el microservicio de contenidos
    response = requests.get(f"{BASE_URL_CONTENIDOS}/contenidos/{idSerie}/temporadas")
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Error al obtener las temporadas.")
    
    return response.json()



@app.get("/administrador/episodio/crear", response_class=HTMLResponse)
async def crear_episodio_form(request: Request):
    """
    Muestra el formulario para crear un episodio.
    """
    # Obtener todas las series desde el microservicio de contenidos
    series_response = requests.get(f"{BASE_URL_CONTENIDOS}/todoseries")
    series = series_response.json() if series_response.status_code == 200 else []

    # Realizar una solicitud GET a la API de contenidos para obtener la lista de directores
    directores_response = requests.get(f"{BASE_URL_CONTENIDOS}/directores")

    # Verifica si la respuesta fue exitosa
    directores = directores_response.json() if directores_response.status_code == 200 else []

    return templates.TemplateResponse(
        "admin_crear_episodio.html",  # Plantilla HTML del formulario
        {
            "request": request,
            "series": series,  # Lista de series disponibles
            "directores": directores, # Lista de directores
        },
    )


@app.post("/administrador/episodio/crear", response_class=HTMLResponse)
async def crear_episodio(
    request: Request,
    idSerie: str = Form(...),
    idTemporada: str = Form(...),
    numeroEpisodio: int = Form(...),
    duracion: int = Form(...),
    idDirector: str = Form(...),
):
    """
    Procesa el formulario para crear un episodio.
    """
    # Construcción de los datos a enviar al microservicio
    data = {
        "idDirector": idDirector,
        "numeroEpisodio": numeroEpisodio,
        "duracion": duracion,
    }

    # Hacer la solicitud POST al microservicio de contenidos
    response = requests.post(
        f"{BASE_URL_CONTENIDOS}/contenidos/{idSerie}/temporadas/{idTemporada}/episodios",
        json=data,
    )

    # Redirigir con un mensaje si el episodio se creó correctamente
    if response.status_code == 200:
        redirect_response = RedirectResponse(url="/admin_menu", status_code=303)
        redirect_response.set_cookie(
            key="success_message", value="Episodio creado exitosamente", max_age=5
        )
        return redirect_response
    else:
        # Renderizar el formulario nuevamente con un mensaje de error
        error_message = "Error al crear el episodio. Por favor, inténtelo de nuevo."
        return templates.TemplateResponse(
            "admin_crear_episodio.html",
            {"request": request, "error_message": error_message},
        )



@app.post("/administrador/genero/crear", response_class=HTMLResponse)
async def crear_genero(
    request: Request,
    nombre: str = Form(...),
    descripcion: str = Form(...),
):
    """
    Procesa el formulario para crear un género de contenido multimedia.
    """
    data = {
        "nombre": nombre,
        "descripcion": descripcion,
    }

    response = requests.post(f"{BASE_URL_CONTENIDOS}/generos", json=data)

    if response.status_code == 200:
        redirect_response = RedirectResponse(url="/admin_menu", status_code=303)
        redirect_response.set_cookie(
            key="success_message", value="Género creado exitosamente", max_age=5
        )
        return redirect_response
    else:
        return templates.TemplateResponse(
            "admin_crear_genero.html",
            {
                "request": request,
                "error_message": "Error al crear el género. Por favor, inténtelo de nuevo.",
            },
        )

@app.get("/administrador/peliculas/{idPelicula}", response_class=HTMLResponse)
async def get_actualizar_pelicula(request: Request, idPelicula: str):
    response = requests.get(f"{BASE_URL_CONTENIDOS}/contenidos/{idPelicula}")
    generos_response = requests.get(f"{BASE_URL_CONTENIDOS}/generos")
    directores_response = requests.get(f"{BASE_URL_CONTENIDOS}/directores")
    actores_response = requests.get(f"{BASE_URL_CONTENIDOS}/actores")
    reparto_response = requests.get(f"{BASE_URL_CONTENIDOS}/contenidos/{idPelicula}/reparto")

    if response.status_code == 200:
        # Obtiene los datos de la pelicula
        pelicula_data = response.json()
        generos = []
        directores = []
        actores = []
        reparto = []

        if generos_response.status_code == 200:
            # Obtiene la lista de géneros y la convierte a una lista de objetos Genero
            generos_data = generos_response.json()
            generos = [
                {
                    "id": genero["id"],
                    "nombre": genero["nombre"],
                    "descripcion": genero.get("descripcion", ""),
                }
                for genero in generos_data
            ]
        else:
            # En caso de error al obtener los géneros
            error_message = f"Error al obtener los géneros de la base de datos: {response.status_code}"
            return templates.TemplateResponse(
                "admin_actualizar_pelicula.html",
                {"request": request, "error_message": error_message},
            )
                
        if directores_response.status_code == 200:
            # Obtiene la lista de directores
            directores_data = directores_response.json()
            directores = [
                {
                    "id": director["id"],
                    "nombre": director["nombre"],
                }
                for director in directores_data
            ]
        else:
            # En caso de error al obtener los directores
            error_message = f"Error al obtener los directores de la base de datos: {directores_response.status_code}"
            return templates.TemplateResponse(
                "admin_actualizar_pelicula.html",
                {"request": request, "error_message": error_message},
            )
        
        if actores_response.status_code == 200:
            # Obtiene la lista de actores
            actores_data = actores_response.json()
            actores = [
                {
                    "id": actor["id"],
                    "nombre": actor["nombre"],
                }
                for actor in actores_data
            ]
        else:
            # En caso de error al obtener los directores
            error_message = f"Error al obtener los actores de la base de datos: {actores_response.status_code}"
            return templates.TemplateResponse(
                "admin_actualizar_pelicula.html",
                {"request": request, "error_message": error_message},
            )

        if reparto_response.status_code == 200:
            # Obtiene la lista del reparto
            reparto_data = reparto_response.json()
            reparto = [actor["id"] for actor in reparto_data]
        else:
            # En caso de error al obtener los directores
            error_message = f"Error al obtener el reparto de la base de datos: {reparto_response.status_code}"
            return templates.TemplateResponse(
                "admin_actualizar_pelicula.html",
                {"request": request, "error_message": error_message},
            )                

        # Renderiza la plantilla HTML con los datos de la pelicula
        return templates.TemplateResponse(
            "admin_actualizar_pelicula.html",  # Plantilla HTML que renderizará los datos
            {
                "request": request,
                "pelicula_id": idPelicula,
                "titulo": pelicula_data["titulo"],
                "descripcion": pelicula_data["descripcion"],
                "fecLanzamiento": pelicula_data["fechaLanzamiento"],
                "idGenero": pelicula_data["idGenero"],
                "generos": generos,  # Pasa la lista de todos los géneros para elegir
                "duracion": pelicula_data["duracion"],
                "idDirector": pelicula_data["idDirector"],
                "directores": directores,   # Pasa la lista de todos los directores
                "actores": actores,
                "reparto": reparto,
            },
        )
    else:
        # En caso de error al obtener los datos de la pelicula
        error_message = (
            f"Error al obtener los datos de la pelicula: {response.status_code}"
        )
        return templates.TemplateResponse(
            "admin_actualizar_pelicula.html",
            {
                "request": request,
                "error_message": error_message,
            },
        )


@app.post("/administrador/update_pelicula/{idPelicula}")
async def actualizar_pelicula(request: Request, idPelicula: str, actores: list[str] = Form(...)):
    """
    Endpoint para actualizar el perfil de un usuario.
    """
    data = await request.form()

    # Extraemos los datos del JSON recibido
    titulo = data.get("titulo")
    descripcion = data.get("descripcion")
    fechaLanzamiento = data.get("fecLanzamiento")
    idGenero = data.get("genero")
    idDirector = data.get("idDirector")

    # Construir el payload para la API externa
    payload = {
        "titulo": titulo,
        "descripcion": descripcion,
        "fechaLanzamiento": fechaLanzamiento,
        "idGenero": idGenero,
        "idDirector": idDirector,
    }

    # URL del endpoint de la API externa para actualizar la pelicula
    api_url = f"{BASE_URL_CONTENIDOS}/peliculas/{idPelicula}"

    # Enviar la solicitud PUT a la API externa
    response = requests.put(api_url, json=payload)

    # Comprobar el estado de la respuesta de la API
    if response.status_code == 200:
        response_delete = requests.delete(f"{BASE_URL_CONTENIDOS}/contenidos/{idPelicula}/reparto")
        if response_delete.status_code != 200:
            return templates.TemplateResponse(
                "admin_actualizar_pelicula.html",
                {
                    "request": request,
                    "error_message": f"Error al añadir el actor al reparto. Por favor, inténtelo de nuevo.",
                }
            )

        # Añadir los actores uno por uno al reparto del contenido
        for idActor in actores:
            response = requests.post(f"{BASE_URL_CONTENIDOS}/contenidos/{idPelicula}/reparto/{idActor}")

            if response.status_code != 200:
                return templates.TemplateResponse(
                    "admin_actualizar_pelicula.html",
                    {
                        "request": request,
                        "error_message": f"Error al añadir el actor al reparto. Por favor, inténtelo de nuevo.",
                    }
                )

        redirect_response = RedirectResponse(url=f"/admin_menu", status_code=303)
        redirect_response.set_cookie(
            key="success_message", value="Película actualizada exitosamente", max_age=5
        )
        return redirect_response
    else:
        return templates.TemplateResponse(
            "admin_actualizar_pelicula.html",
            {
                "request": request,
                "error_message": "Error al actualizar la película. Por favor, inténtelo de nuevo.",
            }
        )
        raise HTTPException(
            status_code=response.status_code, detail="Error al actualizar la pelicula"
        )

@app.get("/administrador/series/{idSerie}", response_class=HTMLResponse)
async def get_actualizar_serie(request: Request, idSerie: str):
    response = requests.get(f"{BASE_URL_CONTENIDOS}/contenidos/{idSerie}")
    generos_response = requests.get(f"{BASE_URL_CONTENIDOS}/generos")
    actores_response = requests.get(f"{BASE_URL_CONTENIDOS}/actores")
    reparto_response = requests.get(f"{BASE_URL_CONTENIDOS}/contenidos/{idSerie}/reparto")    

    if response.status_code == 200:
        # Obtiene los datos de la serie
        serie_data = response.json()
        generos = []

        if generos_response.status_code == 200:
            # Obtiene la lista de géneros y la convierte a una lista de objetos Genero
            generos_data = generos_response.json()
            generos = [
                {
                    "id": genero["id"],
                    "nombre": genero["nombre"],
                    "descripcion": genero.get("descripcion", ""),
                }
                for genero in generos_data
            ]
        else:
            # En caso de error al obtener los géneros
            error_message = f"Error al obtener los géneros de la base de datos: {generos_response.status_code}"
            return templates.TemplateResponse(
                "admin_actualizar_serie.html",
                {"request": request, "error_message": error_message},
            )

        if actores_response.status_code == 200:
            # Obtiene la lista de actores
            actores_data = actores_response.json()
            actores = [
                {
                    "id": actor["id"],
                    "nombre": actor["nombre"],
                }
                for actor in actores_data
            ]
        else:
            # En caso de error al obtener los directores
            error_message = f"Error al obtener los actores de la base de datos: {actores_response.status_code}"
            return templates.TemplateResponse(
                "admin_actualizar_serie.html",
                {"request": request, "error_message": error_message},
            )

        if reparto_response.status_code == 200:
            # Obtiene la lista del reparto
            reparto_data = reparto_response.json()
            reparto = [actor["id"] for actor in reparto_data]
        else:
            # En caso de error al obtener los directores
            error_message = f"Error al obtener el reparto de la base de datos: {reparto_response.status_code}"
            return templates.TemplateResponse(
                "admin_actualizar_serie.html",
                {"request": request, "error_message": error_message},
            )

        # Renderiza la plantilla HTML con los datos de la serie
        return templates.TemplateResponse(
            "admin_actualizar_serie.html",  # Plantilla HTML que renderizará los datos
            {
                "request": request,
                "serie_id": idSerie,
                "titulo": serie_data["titulo"],
                "descripcion": serie_data["descripcion"],
                "fecLanzamiento": serie_data["fechaLanzamiento"],
                "idGenero": serie_data["idGenero"],
                "generos": generos,  # Pasa la lista de todos los géneros para elegir
                "actores": actores,
                "reparto": reparto, 
            },
        )            

    else:
        # En caso de error al obtener los datos de la serie
        error_message = (
            f"Error al obtener los datos de la serie: {response.status_code}"
        )
        return templates.TemplateResponse(
            "admin_actualizar_serie.html",
            {
                "request": request,
                "error_message": error_message,
            },
        )


@app.post("/administrador/update_serie/{idSerie}", response_class=HTMLResponse)
async def actualizar_serie(request: Request, idSerie: str, actores: list[str] = Form(...)):
    """
    Endpoint para actualizar una serie.
    """
    data = await request.form()

    # Extraemos los datos del JSON recibido
    titulo = data.get("titulo")
    descripcion = data.get("descripcion")
    fechaLanzamiento = data.get("fecLanzamiento")
    idGenero = data.get("genero")

    # Construir el payload para la API externa
    payload = {
        "titulo": titulo,
        "descripcion": descripcion,
        "fechaLanzamiento": fechaLanzamiento,
        "idGenero": idGenero,
    }

    # URL del endpoint de la API externa para actualizar la serie
    api_url = f"{BASE_URL_CONTENIDOS}/series/{idSerie}"

    # Enviar la solicitud PUT a la API externa
    response = requests.put(api_url, json=payload)

    # Comprobar el estado de la respuesta de la API
    if response.status_code == 200:
        response_delete = requests.delete(f"{BASE_URL_CONTENIDOS}/contenidos/{idSerie}/reparto")
        if response_delete.status_code != 200:
            return templates.TemplateResponse(
                "admin_actualizar_serie.html",
                {
                    "request": request,
                    "error_message": f"Error al añadir el actor al reparto. Por favor, inténtelo de nuevo.",
                }
            )

        # Añadir los actores uno por uno al reparto del contenido
        for idActor in actores:
            response = requests.post(f"{BASE_URL_CONTENIDOS}/contenidos/{idSerie}/reparto/{idActor}")

            if response.status_code != 200:
                return templates.TemplateResponse(
                    "admin_actualizar_serie.html",
                    {
                        "request": request,
                        "error_message": f"Error al añadir el actor al reparto. Por favor, inténtelo de nuevo.",
                    }
                )

        redirect_response = RedirectResponse(url=f"/admin_menu", status_code=303)
        redirect_response.set_cookie(
            key="success_message", value="Serie actualizada exitosamente", max_age=5
        )
        return redirect_response
    else:
        return templates.TemplateResponse(
            "admin_actualizar_serie.html",
            {
                "request": request,
                "error_message": "Error al actualizar la serie. Por favor, inténtelo de nuevo.",
            }
        )
        raise HTTPException(
            status_code=response.status_code, detail="Error al actualizar la serie"
        )    
    
@app.get("/administrador/series/{idSerie}/temporadas/{idTemporada}", response_class=HTMLResponse)
async def get_actualizar_temporada(request: Request, idSerie: str, idTemporada: str):
    response = requests.get(f"{BASE_URL_CONTENIDOS}/contenidos/{idSerie}/temporadas/{idTemporada}")
    series_response = requests.get(f"{BASE_URL_CONTENIDOS}/todoseries")

    if response.status_code == 200:
        # Obtiene los datos de la serie
        temporada_data = response.json()
        series = []

        if series_response.status_code == 200:
            # Obtiene la lista de series
            series_data = series_response.json()
            series = [
                {
                    "id": serie["id"],
                    "titulo": serie["titulo"],
                }
                for serie in series_data
            ]
        else:
            # En caso de error al obtener las series
            error_message = f"Error al obtener las series de la base de datos: {series_response.status_code}"
            return templates.TemplateResponse(
                "admin_actualizar_temporada.html",
                {"request": request, "error_message": error_message},
            )

        # Renderiza la plantilla HTML con los datos de la temporada
        return templates.TemplateResponse(
            "admin_actualizar_temporada.html",  # Plantilla HTML que renderizará los datos
            {
                "request": request,
                "idSerie": idSerie,
                "temporada_id": idTemporada,
                "numeroTemporada": temporada_data["numeroTemporada"],
                "series": series,  # Pasa la lista de todas las series
            },
        )
    else:
        # En caso de error al obtener los datos de la temporada
        error_message = (
            f"Error al obtener los datos de la temporada: {response.status_code}"
        )
        return templates.TemplateResponse(
            "admin_actualizar_temporada.html",
            {
                "request": request,
                "error_message": error_message,
            },
        )

@app.post("/administrador/update_temporada/{idTemporada}", response_class=HTMLResponse)
async def actualizar_temporada(request: Request, idTemporada: str):
    """
    Endpoint para actualizar una temporada.
    """
    data = await request.form()

    # Extraemos los datos del JSON recibido
    idSerie = data.get("id_serie")
    numeroTemporada = data.get("numeroTemporada")

    # Construir el payload para la API externa
    payload = {
        "idContenido": idSerie,
        "numeroTemporada": numeroTemporada,
    }

    # URL del endpoint de la API externa para actualizar la temporada
    api_url = f"{BASE_URL_CONTENIDOS}/contenidos/{idSerie}/temporadas/{idTemporada}"

    # Enviar la solicitud PUT a la API externa
    response = requests.put(api_url, json=payload)

    # Comprobar el estado de la respuesta de la API
    if response.status_code == 200:
        redirect_response = RedirectResponse(url=f"/admin_menu", status_code=303)
        redirect_response.set_cookie(
            key="success_message", value="Temporada actualizada exitosamente", max_age=5
        )
        return redirect_response
    else:
        return templates.TemplateResponse(
            "admin_actualizar_temporada.html",
            {
                "request": request,
                "error_message": "Error al actualizar la temporada. Por favor, inténtelo de nuevo.",
            }
        )
        raise HTTPException(
            status_code=response.status_code, detail="Error al actualizar la temporada"
        )    

@app.get("/administrador/series/{idSerie}/temporadas/{idTemporada}/episodios/{idEpisodio}", response_class=HTMLResponse)
async def get_actualizar_episodio(request: Request, idSerie: str, idTemporada: str, idEpisodio: str):
    response = requests.get(f"{BASE_URL_CONTENIDOS}/contenidos/{idSerie}/temporadas/{idTemporada}/episodios/{idEpisodio}")
    directores_response = requests.get(f"{BASE_URL_CONTENIDOS}/directores")

    if response.status_code == 200:
        # Obtiene los datos de la serie
        episodio_data = response.json()
        directores = []
                
        if directores_response.status_code == 200:
            # Obtiene la lista de directores
            directores_data = directores_response.json()
            directores = [
                {
                    "id": director["id"],
                    "nombre": director["nombre"],
                }
                for director in directores_data
            ]
        else:
            # En caso de error al obtener los directores
            error_message = f"Error al obtener los directores de la base de datos: {directores_response.status_code}"
            return templates.TemplateResponse(
                "admin_actualizar_episodio.html",
                {"request": request, "error_message": error_message},
            )

        # Renderiza la plantilla HTML con los datos de la temporada
        return templates.TemplateResponse(
            "admin_actualizar_episodio.html",  # Plantilla HTML que renderizará los datos
            {
                "request": request,
                "idSerie": idSerie,
                "idTemporada": idTemporada,
                "episodio_id": idEpisodio,
                "numeroEpisodio": episodio_data["numeroEpisodio"],
                "duracion": episodio_data["duracion"],
                "idDirector": episodio_data["idDirector"],
                "directores": directores,   # Pasa la lista de todos los directores
            },
        )
    else:
        # En caso de error al obtener los datos del episodio
        error_message = (
            f"Error al obtener los datos del episodio: {response.status_code}"
        )
        return templates.TemplateResponse(
            "admin_actualizar_episodio.html",
            {
                "request": request,
                "error_message": error_message,
            },
        )

@app.post("/administrador/update_episodio/series/{idSerie}/temporadas/{idTemporada}/episodios/{idEpisodio}", response_class=HTMLResponse)
async def actualizar_episodio(request: Request, idSerie: str, idTemporada: str, idEpisodio: str):
    """
    Endpoint para actualizar un episodio.
    """
    data = await request.form()

    # Extraemos los datos del JSON recibido
    idSerie = idSerie
    idTemporada = idTemporada
    numeroEpisodio = data.get("numeroEpisodio")
    duracion = data.get("duracion")
    idDirector = data.get("idDirector")

    # Construir el payload para la API externa
    payload = {
        "idContenido": idSerie,
        "idTemporada": idTemporada,
        "numeroEpisodio": numeroEpisodio,
        "duracion": duracion,
        "idDirector": idDirector,
    }

    # URL del endpoint de la API externa para actualizar el episodio
    api_url = f"{BASE_URL_CONTENIDOS}/contenidos/{idSerie}/temporadas/{idTemporada}/episodios/{idEpisodio}"

    # Enviar la solicitud PUT a la API externa
    response = requests.put(api_url, json=payload)

    # Comprobar el estado de la respuesta de la API
    if response.status_code == 200:
        redirect_response = RedirectResponse(url=f"/admin_menu", status_code=303)
        redirect_response.set_cookie(
            key="success_message", value="Episodio actualizado exitosamente", max_age=5
        )
        return redirect_response
    else:
        return templates.TemplateResponse(
            "admin_actualizar_episodio.html",
            {
                "request": request,
                "error_message": "Error al actualizar el episodio. Por favor, inténtelo de nuevo.",
            }
        )
        raise HTTPException(
            status_code=response.status_code, detail="Error al actualizar el episodio"
        )    

@app.get("/administrador/generos/{idGenero}", response_class=HTMLResponse)
async def get_actualizar_genero(request: Request, idGenero: str):
    response = requests.get(f"{BASE_URL_CONTENIDOS}/generos/{idGenero}")

    if response.status_code == 200:
        # Obtiene los datos de la serie
        genero_data = response.json()

        # Renderiza la plantilla HTML con los datos de la temporada
        return templates.TemplateResponse(
            "admin_actualizar_genero.html",  # Plantilla HTML que renderizará los datos
            {
                "request": request,
                "idGenero": idGenero,
                "nombre": genero_data["nombre"],
                "descripcion": genero_data["descripcion"],
            },
        )
    else:
        # En caso de error al obtener los datos del género
        error_message = (
            f"Error al obtener los datos del genero: {response.status_code}"
        )
        return templates.TemplateResponse(
            "admin_actualizar_genero.html",
            {
                "request": request,
                "error_message": error_message,
            },
        )

@app.post("/administrador/update_genero/{idGenero}", response_class=HTMLResponse)
async def actualizar_genero(request: Request, idGenero: str):
    """
    Endpoint para actualizar un género.
    """
    data = await request.form()

    # Extraemos los datos del JSON recibido
    nombre = data.get("nombre")
    descripcion = data.get("descripcion")

    # Construir el payload para la API externa
    payload = {
        "nombre": nombre,
        "descripcion": descripcion,
    }

    # URL del endpoint de la API externa para actualizar el episodio
    api_url = f"{BASE_URL_CONTENIDOS}/generos/{idGenero}"

    # Enviar la solicitud PUT a la API externa
    response = requests.put(api_url, json=payload)

    # Comprobar el estado de la respuesta de la API
    if response.status_code == 200:
        redirect_response = RedirectResponse(url=f"/admin_menu", status_code=303)
        redirect_response.set_cookie(
            key="success_message", value="Género actualizado exitosamente", max_age=5
        )
        return redirect_response
    else:
        return templates.TemplateResponse(
            "admin_actualizar_genero.html",
            {
                "request": request,
                "error_message": "Error al actualizar el género. Por favor, inténtelo de nuevo.",
            }
        )
        raise HTTPException(
            status_code=response.status_code, detail="Error al actualizar el género"
        )    


@app.get("/peliculas/borrar", response_class=HTMLResponse)
def borrar_peliculas(request: Request):
    """
    Obtiene la lista de películas desde la API de Contenidos y redirige a la página HTML.
    """
    try:
        # Petición a la API de Contenidos para obtener el listado de películas
        response = requests.get(f"{BASE_URL_CONTENIDOS}/todopeliculas")
        response.raise_for_status()
        peliculas = response.json()
    except requests.exceptions.RequestException as e:
        return HTMLResponse(
            content=f"<h1>Error al obtener las películas: {e}</h1>", status_code=500
        )

    mensaje = request.query_params.get("mensaje", None)
    # Renderizar la plantilla con los datos de las películas
    return templates.TemplateResponse(
        "admin_borrar_peliculas.html",
        {"request": request, "peliculas": peliculas, "mensaje": mensaje},
    )


@app.post("/peliculas/{idPelicula}/borrar")
def borrar_pelicula(idPelicula: str, request: Request):
    """
    Realiza una solicitud a la API de Contenidos para eliminar una película.
    """
    try:
        # Petición a la API de Contenidos para borrar la película
        response = requests.delete(f"{BASE_URL_CONTENIDOS}/contenidos/{idPelicula}")
        response.raise_for_status()
        mensaje = response.json().get("message")

    except requests.exceptions.RequestException as e:
        mensaje = f"Error al intentar borrar la película: {e}"

    # Redirigir nuevamente al listado de películas
    return RedirectResponse(url=f"/peliculas/borrar?mensaje={mensaje}", status_code=303)              

@app.get("/series/borrar", response_class=HTMLResponse)
def borrar_series(request: Request):
    """
    Obtiene la lista de series desde la API de Contenidos y redirige a la página HTML.
    """
    try:
        # Petición a la API de Contenidos para obtener el listado de series
        response = requests.get(f"{BASE_URL_CONTENIDOS}/todoseries")
        response.raise_for_status()
        series = response.json()
    except requests.exceptions.RequestException as e:
        return HTMLResponse(
            content=f"<h1>Error al obtener las series: {e}</h1>", status_code=500
        )

    mensaje = request.query_params.get("mensaje", None)
    # Renderizar la plantilla con los datos de las series
    return templates.TemplateResponse(
        "admin_borrar_series.html",
        {"request": request, "series": series, "mensaje": mensaje},
    )


@app.post("/series/{idSerie}/borrar")
def borrar_serie(idSerie: str, request: Request):
    """
    Realiza una solicitud a la API de Contenidos para eliminar una serie.
    """
    try:
        # Petición a la API de Contenidos para borrar la serie
        response = requests.delete(f"{BASE_URL_CONTENIDOS}/contenidos/{idSerie}")
        response.raise_for_status()
        mensaje = response.json().get("message")

    except requests.exceptions.RequestException as e:
        mensaje = f"Error al intentar borrar la serie: {e}"

    # Redirigir nuevamente al listado de series
    return RedirectResponse(url=f"/series/borrar?mensaje={mensaje}", status_code=303) 

@app.get("/temporadas/borrar", response_class=HTMLResponse)
def borrar_temporadas(request: Request):
    """
    Obtiene la lista de series desde la API de Contenidos y redirige a la página HTML.
    """
    try:
        # Petición a la API de Contenidos para obtener el listado de series
        response = requests.get(f"{BASE_URL_CONTENIDOS}/series")
        response.raise_for_status()
        series = response.json()
    except requests.exceptions.RequestException as e:
        return HTMLResponse(
            content=f"<h1>Error al obtener las series: {e}</h1>", status_code=500
        )

    mensaje = request.query_params.get("mensaje", None)
    # Renderizar la plantilla con los datos de las series
    return templates.TemplateResponse(
        "admin_borrar_temporadas.html",
        {"request": request, "series": series, "mensaje": mensaje},
    )

@app.post("/series/{idSerie}/temporadas/{idTemporada}/borrar")
def borrar_temporada(idSerie: str, idTemporada: str, request: Request):
    """
    Realiza una solicitud a la API de Contenidos para eliminar una temporada.
    """
    try:
        # Petición a la API de Contenidos para borrar la temporada
        response = requests.delete(f"{BASE_URL_CONTENIDOS}/contenidos/{idSerie}/temporadas/{idTemporada}")
        response.raise_for_status()
        mensaje = response.json().get("message")

    except requests.exceptions.RequestException as e:
        mensaje = f"Error al intentar borrar la temporada: {e}"

    # Redirigir nuevamente al listado de series
    return RedirectResponse(url=f"/temporadas/borrar?mensaje={mensaje}", status_code=303)

# Endpoint para admin borrar episodios
@app.get("/episodios/borrar", response_class=HTMLResponse)
def borrar_episodios(request: Request):
    """
    Obtiene la lista de series desde la API de Contenidos y redirige a la página HTML.
    """
    try:
        # Petición a la API de Contenidos para obtener el listado de series
        response = requests.get(f"{BASE_URL_CONTENIDOS}/series")
        response.raise_for_status()
        series = response.json()
    except requests.exceptions.RequestException as e:
        return HTMLResponse(
            content=f"<h1>Error al obtener las series: {e}</h1>", status_code=500
        )

    mensaje = request.query_params.get("mensaje", None)
    # Renderizar la plantilla con los datos de las series
    return templates.TemplateResponse(
        "admin_borrar_episodio.html",
        {"request": request, "series": series, "mensaje": mensaje},
    )

@app.post("/series/{idSerie}/temporadas/{idTemporada}/episodios/{idEpisodio}/borrar")
def borrar_episodio(idSerie: str, idTemporada: str, idEpisodio: str, request: Request):
    """
    Realiza una solicitud a la API de Contenidos para eliminar un episodio.
    """
    try:
        # Petición a la API de Contenidos para borrar el episodio
        response = requests.delete(f"{BASE_URL_CONTENIDOS}/contenidos/{idSerie}/temporadas/{idTemporada}/episodios/{idEpisodio}")
        response.raise_for_status()
        mensaje = response.json().get("message")

    except requests.exceptions.RequestException as e:
        mensaje = f"Error al intentar borrar el episodio: {e}"

    # Redirigir nuevamente al listado de episodios
    return RedirectResponse(url=f"/episodios/borrar?mensaje={mensaje}", status_code=303)

# Endpoints para borrar generos
@app.get("/generos/borrar", response_class=HTMLResponse)
def borrar_generos(request: Request):
    """
    Obtiene la lista de géneros desde la base de datos y redirige a la página HTML.
    """
    try:
        # Petición a la base de datos para obtener el listado de géneros
        response = requests.get(f"{BASE_URL_CONTENIDOS}/generos")
        response.raise_for_status()
        generos = response.json()
    except requests.exceptions.RequestException as e:
        return HTMLResponse(
            content=f"<h1>Error al obtener los géneros: {e}</h1>", status_code=500
        )

    mensaje = request.query_params.get("mensaje", None)
    # Renderizar la plantilla con los datos de los géneros
    return templates.TemplateResponse(
        "admin_borrar_generos.html",
        {"request": request, "generos": generos, "mensaje": mensaje},
    )

@app.post("/generos/{idGenero}/borrar")
def borrar_genero(idGenero: str, request: Request):
    """
    Elimina un género de la base de datos.
    """
    try:
        # Petición a la base de datos para borrar el género
        response = requests.delete(f"{BASE_URL_CONTENIDOS}/generos/{idGenero}")
        response.raise_for_status()
        mensaje = response.json().get("message")
    except requests.exceptions.RequestException as e:
        mensaje = f"Error al intentar borrar el género: {e}"

    # Redirigir nuevamente al listado de géneros con el mensaje
    return RedirectResponse(url=f"/generos/borrar?mensaje={mensaje}", status_code=303)

#Endpoints para crear un actor
@app.get("/administrador/actor/crear", response_class=HTMLResponse)
async def crear_actor_form(request: Request):
    """
    Muestra el formulario para crear un actor.
    """
    return templates.TemplateResponse(
        "admin_crear_actor.html",  # Plantilla HTML del formulario
        {"request": request},
    )

@app.post("/administrador/actor/crear", response_class=HTMLResponse)
async def crear_actor(
    request: Request,
    nombre: str = Form(...),
    nacionalidad: str = Form(...),
    fechaNacimiento: str = Form(...),
):
    """
    Procesa el formulario para crear un actor.
    """
    # Construcción de los datos a enviar al microservicio
    data = {
        "nombre": nombre,
        "nacionalidad": nacionalidad,
        "fechaNacimiento": fechaNacimiento,
    }

    # Hacer la solicitud POST al microservicio de contenidos para crear el actor
    response = requests.post(f"{BASE_URL_CONTENIDOS}/actores", json=data)

    # Redirigir con un mensaje si el actor se creó correctamente
    if response.status_code == 200:
        redirect_response = RedirectResponse(url="/admin_menu", status_code=303)
        redirect_response.set_cookie(
            key="success_message", value="Actor creado exitosamente", max_age=5
        )
        return redirect_response
    else:
        # Renderizar el formulario nuevamente con un mensaje de error
        error_message = "Error al crear el actor. Por favor, inténtelo de nuevo."
        return templates.TemplateResponse(
            "admin_crear_actor.html",
            {"request": request, "error_message": error_message},
        )
    
# Endpoints para crear un director:
@app.get("/administrador/director/crear", response_class=HTMLResponse)
async def crear_director_form(request: Request):
    """
    Muestra el formulario para crear un director.
    """
    return templates.TemplateResponse(
        "admin_crear_director.html",  # Plantilla HTML del formulario
        {"request": request},
    )

@app.post("/administrador/director/crear", response_class=HTMLResponse)
async def crear_director(
    request: Request,
    nombre: str = Form(...),
    nacionalidad: str = Form(...),
    fechaNacimiento: str = Form(...),
):
    """
    Procesa el formulario para crear un director.
    """
    # Construcción de los datos a enviar al microservicio
    data = {
        "nombre": nombre,
        "nacionalidad": nacionalidad,
        "fechaNacimiento": fechaNacimiento,
    }

    # Hacer la solicitud POST al microservicio de contenidos para crear el director
    response = requests.post(f"{BASE_URL_CONTENIDOS}/directores", json=data)

    # Redirigir con un mensaje si el director se creó correctamente
    if response.status_code == 200:
        redirect_response = RedirectResponse(url="/admin_menu", status_code=303)
        redirect_response.set_cookie(
            key="success_message", value="Director creado exitosamente", max_age=5
        )
        return redirect_response
    else:
        # Renderizar el formulario nuevamente con un mensaje de error
        error_message = "Error al crear el director. Por favor, inténtelo de nuevo."
        return templates.TemplateResponse(
            "admin_crear_director.html",
            {"request": request, "error_message": error_message},
        )

# Endpoints para actualizar un actor:
@app.get("/actores/actualizar", response_class=HTMLResponse)
async def actualizar_actores(request: Request, success: str = None):
    # Realizar una solicitud GET a la API de contenidos para obtener la lista de actores
    response = requests.get(f"{BASE_URL_CONTENIDOS}/actores")

    # Verifica si la respuesta fue exitosa
    if response.status_code == 200:
        actores = response.json()  # Obtenemos la lista de actores como JSON
        return templates.TemplateResponse(
            "admin_actualizar_actores.html",
            {
                "request": request,
                "actores": actores,
                "message": success
            },
        )
    else:
        return {"error": "No se pudo obtener la lista de actores"}

@app.post("/actor/actualizar")
async def actualizar_actor(request: Request):
    # Obtenemos los datos del formulario
    form_data = await request.form()

    # Creamos una lista con los datos a actualizar
    actores_actualizados = []
    for actor_id in form_data.getlist("id_actor"):
        actor_data = {
            "id": actor_id,
            "nombre": form_data.get(f"nombre_{actor_id}"),
            "nacionalidad": form_data.get(f"nacionalidad_{actor_id}"),
            "fechaNacimiento": form_data.get(f"fechaNacimiento_{actor_id}"),
        }
        actores_actualizados.append(actor_data)

    for actor in actores_actualizados:
        response = requests.put(
            f"{BASE_URL_CONTENIDOS}/actores/{actor['id']}", json=actor
        )
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code, detail="Error al actualizar actor"
            )
    
    # Redirigimos a la página de actualización de actores con un mensaje de éxito
    return RedirectResponse(url=f"/actores/actualizar?success=true", status_code=303)



# Endpoints para eliminar actores o directores
@app.get("/actores/borrar", response_class=HTMLResponse)
def borrar_actores(request: Request):
    """
    Obtiene la lista de actores desde la API de Contenidos y redirige a la página HTML.
    """
    try:
        # Petición a la API de Contenidos para obtener el listado de actores
        response = requests.get(f"{BASE_URL_CONTENIDOS}/actores")
        response.raise_for_status()
        actores = response.json()
    except requests.exceptions.RequestException as e:
        return HTMLResponse(
            content=f"<h1>Error al obtener actores: {e}</h1>", status_code=500
        )

    mensaje = request.query_params.get("mensaje", None)
    # Renderizar la plantilla con los datos de actores
    return templates.TemplateResponse(
        "admin_borrar_actores.html",
        {"request": request, "actores": actores, "mensaje": mensaje},
    )


@app.post("/actores/{idActor}/borrar")
def borrar_actor(idActor: str, request: Request):
    """
    Realiza una solicitud a la API de Contenidos para eliminar un actor.
    """
    try:
        # Petición a la API de Contenidos para borrar el actor
        response = requests.delete(f"{BASE_URL_CONTENIDOS}/actores/{idActor}")
        response.raise_for_status()
        mensaje = response.json().get("message")

    except requests.exceptions.RequestException as e:
        mensaje = f"Error al intentar borrar el actor: {e}"

    # Redirigir nuevamente al listado de actores
    return RedirectResponse(url=f"/actores/borrar?mensaje={mensaje}", status_code=303)


@app.get("/directores/borrar", response_class=HTMLResponse)
def borrar_directores(request: Request):
    """
    Obtiene la lista de directores desde la API de Contenidos y redirige a la página HTML.
    """
    try:
        # Petición a la API de Contenidos para obtener el listado de actores
        response = requests.get(f"{BASE_URL_CONTENIDOS}/directores")
        response.raise_for_status()
        directores = response.json()
    except requests.exceptions.RequestException as e:
        return HTMLResponse(
            content=f"<h1>Error al obtener directores: {e}</h1>", status_code=500
        )

    mensaje = request.query_params.get("mensaje", None)
    # Renderizar la plantilla con los datos de directores
    return templates.TemplateResponse(
        "admin_borrar_directores.html",
        {"request": request, "directores": directores, "mensaje": mensaje},
    )


@app.post("/directores/{idDirector}/borrar")
def borrar_director(idDirector: str, request: Request):
    """
    Realiza una solicitud a la API de Contenidos para eliminar un director.
    """
    try:
        # Petición a la API de Contenidos para borrar el actor
        response = requests.delete(f"{BASE_URL_CONTENIDOS}/directores/{idDirector}")
        response.raise_for_status()
        mensaje = response.json().get("message")

    except requests.exceptions.RequestException as e:
        mensaje = f"Error al intentar borrar el director: {e}"

    # Redirigir nuevamente al listado de actores
    return RedirectResponse(
        url=f"/directores/borrar?mensaje={mensaje}", status_code=303
    )


# Función para manejar la actualización de los directores
@app.get("/directores/actualizar", response_class=HTMLResponse)
async def actualizar_directores(request: Request, success: str = None):
    # Realizar una solicitud GET a la API de contenidos para obtener la lista de directores
    response = requests.get(f"{BASE_URL_CONTENIDOS}/directores")

    # Verifica si la respuesta fue exitosa
    if response.status_code == 200:
        directores = response.json()  # Obtenemos la lista de directores como JSON
        return templates.TemplateResponse(
            "admin_actualizar_directores.html",
            {
                "request": request,
                "directores": directores,
                "message": success
            },
        )
    else:
        return {"error": "No se pudo obtener la lista de directores"}


@app.post("/director/actualizar")
async def actualizar_director(request: Request):
    # Obtenemos los datos del formulario
    form_data = await request.form()

    # Creamos una lista con los datos a actualizar
    directores_actualizados = []
    for director_id in form_data.getlist("id_director"):
        director_data = {
            "id": director_id,
            "nombre": form_data.get(f"nombre_{director_id}"),
            "nacionalidad": form_data.get(f"nacionalidad_{director_id}"),
            "fechaNacimiento": form_data.get(f"fechaNacimiento_{director_id}"),
        }
        directores_actualizados.append(director_data)

    for director in directores_actualizados:
        response = requests.put(
            f"{BASE_URL_CONTENIDOS}/directores/{director['id']}", json=director
        )
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code, detail="Error al actualizar director"
            )
    # Redirigimos a la página de actualización de directores
    return RedirectResponse(url=f"/directores/actualizar?success=true", status_code=303)

# Endpoints para dar / quitar me-gusta
@app.post("/contenidos/{user_id}/dar-me-gusta/{idContenido}")
def dar_me_gusta(user_id: str, idContenido: str):
    
    try:
        # Petición a la API de Contenidos para dar me gusta
        response = requests.post(f"{BASE_URL_INTERACCIONES}/usuarios/{user_id}/me-gusta/{idContenido}")
        response.raise_for_status()
        mensaje = response.json().get("message")

    except requests.exceptions.RequestException as e:
        mensaje = f"Error al dar me gusta: {e}"

@app.delete("/contenidos/{user_id}/eliminar-me-gusta/{idContenido}")
def eliminar_me_gusta(user_id: str, idContenido: str):
    
    try:
        # Petición a la API de Interacciones para eliminar me gusta
        response = requests.delete(f"{BASE_URL_INTERACCIONES}/usuarios/{user_id}/me-gusta/{idContenido}")
        response.raise_for_status()
        mensaje = response.json().get("message")

    except requests.exceptions.RequestException as e:
        mensaje = f"Error al eliminar me gusta: {e}"

# Endpoints para aniadir / eliminar de LP
@app.post("/contenidos/{userId}/aniadir_a_LP/{contentId}")
def aniadir_a_LP(userId: str, contentId: str):
    
    try:
        # Petición a la API de Interacciones para aniadir a LP
        response = requests.post(f"{BASE_URL_INTERACCIONES}/usuarios/{userId}/listaPersonalizada/{contentId}")
        response.raise_for_status()
        mensaje = response.json().get("message")

    except requests.exceptions.RequestException as e:
        mensaje = f"Error al aniadir a LP: {e}"

@app.delete("/contenidos/{user_id}/eliminar_de_LP/{idContenido}")
def eliminar_de_LP(user_id: str, idContenido: str):
    
    try:
        # Petición a la API de Contenidos para eliminar de LP
        response = requests.delete(f"{BASE_URL_INTERACCIONES}/usuarios/{user_id}/listaPersonalizada/{idContenido}")
        response.raise_for_status()
        mensaje = response.json().get("message")
    except requests.exceptions.RequestException as e:
        mensaje = f"Error al eliminar de LP: {e}"

@app.get("/contenidos/{user_id}/esta_en_lista/{idContenido}")
def esta_en_lista(user_id: str, idContenido: str):
    # Realizar la solicitud al endpoint para obtener la lista personalizada del usuario
    response = requests.get(f"{BASE_URL_INTERACCIONES}/usuarios/{user_id}/listaPersonalizada")

    # Verificar si la solicitud fue exitosa
    if response.status_code == 200:
        try:
            # Procesar la respuesta JSON (lista de contenidos)
            lista_personalizada = response.json()
            
            # Buscar el contenido por su ID en la lista personalizada
            for contenido in lista_personalizada:
                if contenido["id"] == idContenido:  # Si el ID coincide, devolver True
                    return True
            
            # Si no se encuentra el contenido, devolver False
            return False
        except ValueError:
            # Manejar errores si la respuesta no es JSON válido
            raise HTTPException(
                status_code=500,
                detail="La respuesta del servidor no contiene un JSON válido."
            )
    else:
        # Si la solicitud falla, devolver un mensaje de error
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Error al obtener la lista personalizada: {response.text}"
        )


@app.get("/contenidos/{user_id}/esta_en_mg/{idContenido}")
def esta_en_mg(user_id: str, idContenido: str):
    # Realizar la solicitud al endpoint para obtener los contenidos marcados como "Me gusta"
    response = requests.get(f"{BASE_URL_INTERACCIONES}/usuarios/{user_id}/me-gusta")
    
    # Verificar si la solicitud fue exitosa
    if response.status_code == 200:
        try:
            # Procesar la respuesta JSON (debe ser una lista de objetos que cumplen con ContenidoMeGusta)
            me_gusta = response.json()
            
            # Buscar el contenido por su ID en la lista de "Me gusta"
            for contenido in me_gusta:
                if contenido["id"] == idContenido:  # Si el ID coincide, devolver True
                    return True
            
            # Si no se encuentra el contenido, devolver False
            return False
        except ValueError:
            # Manejar errores si la respuesta no es JSON válido
            raise HTTPException(
                status_code=500,
                detail="La respuesta del servidor no contiene un JSON válido."
            )
    else:
        # Si la solicitud falla, devolver un mensaje de error
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Error al obtener los contenidos 'Me gusta': {response.text}"
        )
    
@app.post("/usuarios/{userId}/valorarContenido/{contentId}")
async def valorarContenido(userId: str, contentId: str, request: Request):
    try:
        # Extraemos el cuerpo de la solicitud
        body = await request.json()

        # Validamos que el JSON tenga la clave "valoracion"
        if "valoracion" not in body:
            raise HTTPException(status_code=400, detail="Falta el campo 'valoracion' en el cuerpo de la solicitud")

        valoracion = body["valoracion"]

        response = requests.post(f"{BASE_URL_INTERACCIONES}/usuarios/{userId}/valoraciones/{contentId}?valoracion={valoracion}")

        if response.status_code == 200:
            return {"message": "Valoración enviada correctamente", "data": response.json()}
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Error al procesar la valoración: {response.text}",
            )
    except requests.RequestException as e:
        print("Error al conectar con el servicio:", e)  # Log para depurar
        raise HTTPException(status_code=500, detail=f"Error al conectarse al servicio: {e}")
    except Exception as e:
        print("Error inesperado:", e)  # Log para depurar
        raise HTTPException(status_code=500, detail=f"Error inesperado: {e}")
    
# Endpoint para obtener todos los contenidos (para HTML)
@app.get("/administrador/contenidos")
def obtener_todos_los_contenidos():
    """
    Endpoint en el servicio de Streamflix que llama al microservicio Contenido
    para obtener todos los contenidos.
    """
    try:
        # Realiza la llamada al microservicio Contenido
        response = requests.get(f"{BASE_URL_CONTENIDOS}/contenidos")
        
        # Maneja errores de la respuesta
        response.raise_for_status()
        
        # Devuelve los contenidos obtenidos
        return response.json()
    
    except requests.exceptions.RequestException as e:
        # Lanza una excepción HTTP si hay algún error en la llamada
        raise HTTPException(status_code=500, detail=f"Error al obtener los contenidos: {e}")
    
# Endpoint para obtener todos los subtitulos de un contenido (para HTML)
@app.get("/administrador/contenidos/{idSubtitulosContenido}/subtitulos")
def obtener_subtitulos_contenido(idSubtitulosContenido: str):
    """
    Endpoint en el servicio de Interface que llama al microservicio Contenido
    para obtener los subtítulos de un contenido específico.
    """
    try:
        # Realiza la llamada al microservicio Contenido para obtener los subtítulos
        response = requests.get(f"{BASE_URL_CONTENIDOS}/contenidos/{idSubtitulosContenido}/subtitulos")
        
        # Maneja errores de la respuesta
        response.raise_for_status()
        
        # Devuelve los subtítulos obtenidos
        return response.json()
    
    except requests.exceptions.RequestException as e:
        # Lanza una excepción HTTP si hay algún error en la llamada
        raise HTTPException(status_code=500, detail=f"Error al obtener los subtítulos: {e}")

# Endpoint para obtener todos los subtitulos (para HTML)
@app.get("/administrador/contenidos/subtitulos")
def obtener_todos_los_subtitulos():
    """
    Endpoint en el servicio de Interface que llama al microservicio Contenido
    para obtener todos los subtítulos disponibles.
    """
    try:
        # Realiza la llamada al microservicio Contenido para obtener todos los subtítulos
        response = requests.get(f"{BASE_URL_CONTENIDOS}/contenidos/subtitulos")
        
        # Maneja errores de la respuesta
        response.raise_for_status()
        
        # Devuelve la lista de subtítulos obtenida
        return response.json()
    
    except requests.exceptions.RequestException as e:
        # Lanza una excepción HTTP si hay algún error en la llamada
        raise HTTPException(status_code=500, detail=f"Error al obtener los subtítulos: {e}")
    
# Endpoint post para eliminar los subtitulos
@app.post("/administrador/eliminar_subtitulos")
async def eliminar_subtitulos(
    idSubtitulosContenido: str = Form(...),  # Recibimos idContenido como Form
    idSubtitulo: str = Form(...)   # Recibimos idSubtitulo como Form
):
    """
    Endpoint en el servicio de Interface para eliminar un subtítulo de un contenido.
    """
    try:
        # Realiza la llamada DELETE al microservicio Contenido para eliminar el subtítulo
        response = requests.delete(f"{BASE_URL_CONTENIDOS}/contenidos/{idSubtitulosContenido}/subtitulos/{idSubtitulo}")
        
        # Maneja errores de la respuesta
        response.raise_for_status()
        
        # Redirige a la página de actualización de subtítulos con un mensaje de éxito
        return RedirectResponse(url="/administrador/actualizar_subtitulos?success=true&success_message=Se%20han%20actualizado%20los%20subtitulos%20del%20contenido", status_code=303)
    
    except requests.exceptions.RequestException as e:
        # Lanza una excepción HTTP si hay algún error en la llamada
        raise HTTPException(status_code=500, detail=f"Error al eliminar subtítulo: {e}")
    
# Endpoint get para actualizar los subtitulos
@app.get("/administrador/actualizar_subtitulos",  response_class=HTMLResponse)
async def actualizar_subtitulos(request: Request, success: str = None):
    # Realizar una solicitud GET a la API de contenidos para obtener los subtitulos y los contenidos
    responseSub = requests.get(f"{BASE_URL_CONTENIDOS}/contenidos/subtitulos")
    responseCont = requests.get(f"{BASE_URL_CONTENIDOS}/contenidos")

    # Verifica si la respuesta fue exitosa
    if responseCont.status_code == 200 and responseSub.status_code == 200:
        subtitulos = responseSub.json() 
        contenidos = responseCont.json()
        return templates.TemplateResponse(
            "admin_actualizar_subtitulos.html",
            {
                "request": request,
                "subtitulos_contenido": subtitulos,
                "subtitulos_disponibles": subtitulos,
                "contenidos": contenidos,
                "message": success
            },
        )
    else:
        return {"error": "No se pudo obtener la lista de contenido"}
    
# Enpoint post para actualizar los subtitulos de un contenido
@app.post("/administrador/actualizar_subtitulo")
async def actualizar_subtitulos(
    idSubtitulosContenido: str = Form(...),  # Recibimos idContenido como Form
    idSubtitulo: str = Form(...),  # Recibimos idSubtitulo como Form
):
    """
    Endpoint para asignar un subtítulo a un contenido.
    Si el subtítulo ya está asignado al contenido, no lo vuelve a asignar.
    """
    try:
        

        # Realiza la llamada GET al endpoint /contenidos/{idContenido}/subtitulos para obtener los subtítulos asignados
        response_check = requests.get(
            f"{BASE_URL_CONTENIDOS}/contenidos/{idSubtitulosContenido}/subtitulos"
        )

        # Si la respuesta es exitosa, obtenemos los subtítulos asignados
        if response_check.status_code == 200:
            subtitulos_asignados = response_check.json()
        else:
            # Si la respuesta no es 200, se lanza una excepción
            raise HTTPException(status_code=500, detail="Error al obtener los subtítulos asignados.")

        # Verificar si el subtítulo ya está asignado al contenido
        if any(subtitulo['idSubtitulo'] == idSubtitulo for subtitulo in subtitulos_asignados):
            # Si el subtítulo ya está asignado, redirige con un mensaje de error
            return RedirectResponse(
                url="/administrador/actualizar_subtitulos?error=true&message=El%20subt%C3%ADtulo%20ya%20est%C3%A1%20asignado%20a%20este%20contenido",
                status_code=303
            )

        # Si no está asignado, intenta añadirlo
        response = requests.post(
            f"{BASE_URL_CONTENIDOS}/contenidos/{idSubtitulosContenido}/subtitulos/{idSubtitulo}"
        )

        # Verifica si la llamada al backend fue exitosa
        response.raise_for_status()

        # Redirige con éxito
        return RedirectResponse(
            url="/administrador/actualizar_subtitulos?success=true&message=Subt%C3%ADtulo%20asignado%20correctamente%20al%20contenido",
            status_code=303
        )

    except requests.exceptions.RequestException as e:
        # Lanza una excepción HTTP si hay algún error en la llamada
        raise HTTPException(status_code=500, detail=f"Error al asignar subtítulo: {e}")
    
# Endpoint para obtener todos los doblajes de un contenido (para HTML)
@app.get("/administrador/contenidos/{idDoblajeContenido}/doblajes")
def obtener_doblajes_contenido(idDoblajeContenido: str):
    """
    Endpoint en el servicio de Interface que llama al microservicio Contenido
    para obtener los doblajes de un contenido específico.
    """
    try:
        # Realiza la llamada al microservicio Contenido para obtener los doblajes
        response = requests.get(f"{BASE_URL_CONTENIDOS}/contenidos/{idDoblajeContenido}/doblajes")
        
        # Maneja errores de la respuesta
        response.raise_for_status()
        
        # Devuelve los doblajes obtenidos
        return response.json()
    
    except requests.exceptions.RequestException as e:
        # Lanza una excepción HTTP si hay algún error en la llamada
        raise HTTPException(status_code=500, detail=f"Error al obtener los doblajes: {e}")
    
# Endpoint para obtener todos los doblajes (para HTML)
@app.get("/administrador/contenidos/doblajes")
def obtener_todos_los_doblajes():
    """
    Endpoint en el servicio de Interface que llama al microservicio Contenido
    para obtener todos los doblajes disponibles.
    """
    try:
        # Realiza la llamada al microservicio Contenido para obtener todos los doblajes
        response = requests.get(f"{BASE_URL_CONTENIDOS}/contenidos/doblajes")
        
        # Maneja errores de la respuesta
        response.raise_for_status()
        
        # Devuelve la lista de doblajes obtenida
        return response.json()
    
    except requests.exceptions.RequestException as e:
        # Lanza una excepción HTTP si hay algún error en la llamada
        raise HTTPException(status_code=500, detail=f"Error al obtener los doblajes: {e}")
    
# Endpoint post para eliminar los doblajes
@app.post("/administrador/eliminar_doblajes")
async def eliminar_doblajes(
    idDoblajeContenido: str = Form(...),  # Recibimos idContenido como Form
    idDoblaje: str = Form(...)   # Recibimos idDoblaje como Form
):
    """
    Endpoint en el servicio de Interface para eliminar un doblaje de un contenido.
    """
    try:
        # Realiza la llamada DELETE al microservicio Contenido para eliminar el doblaje
        response = requests.delete(f"{BASE_URL_CONTENIDOS}/contenidos/{idDoblajeContenido}/doblajes/{idDoblaje}")
        
        # Maneja errores de la respuesta
        response.raise_for_status()
        
        # Redirige a la página de actualización de doblajes con un mensaje de éxito
        return RedirectResponse(url="/administrador/actualizar_doblajes?success=true&success_message=Se%20han%20actualizado%20los%20doblajes%20del%20contenido", status_code=303)
    
    except requests.exceptions.RequestException as e:
        # Lanza una excepción HTTP si hay algún error en la llamada
        raise HTTPException(status_code=500, detail=f"Error al eliminar doblaje: {e}")
    
# Endpoint get para actualizar los doblajes
@app.get("/administrador/actualizar_doblajes",  response_class=HTMLResponse)
async def actualizar_doblajes(request: Request, success: str = None):
    # Realizar una solicitud GET a la API de contenidos para obtener la lista de directores
    responseDobl = requests.get(f"{BASE_URL_CONTENIDOS}/contenidos/doblajes")
    responseCont = requests.get(f"{BASE_URL_CONTENIDOS}/contenidos")

    # Verifica si la respuesta fue exitosa
    if responseCont.status_code == 200 and responseDobl.status_code == 200:
        doblajes = responseDobl.json() 
        contenidos = responseCont.json()
        return templates.TemplateResponse(
            "admin_actualizar_doblajes.html",
            {
                "request": request,
                "doblajes_contenido": doblajes,
                "doblajes_disponibles": doblajes,
                "contenidos": contenidos,
                "message": success
            },
        )
    else:
        return {"error": "No se pudo obtener la lista de contenido"}


# Endpoint post para actualizar los doblajes de un contenido
@app.post("/administrador/actualizar_doblaje")
async def actualizar_doblajes(
    idDoblajeContenido: str = Form(...),  # Recibimos idContenido como Form
    idDoblaje: str = Form(...),  # Recibimos idDoblaje como Form
):
    """
    Endpoint para asignar un doblaje a un contenido.
    Si el doblaje ya está asignado al contenido, no lo vuelve a asignar.
    """
    try:
        # Realiza la llamada GET al endpoint /contenidos/{idContenido}/doblajes para obtener los doblajes asignados
        response_check = requests.get(
            f"{BASE_URL_CONTENIDOS}/contenidos/{idDoblajeContenido}/doblajes"
        )

        # Si la respuesta es exitosa, obtenemos los doblajes asignados
        if response_check.status_code == 200:
            doblajes_asignados = response_check.json()
        else:
            # Si la respuesta no es 200, se lanza una excepción
            raise HTTPException(status_code=500, detail="Error al obtener los doblajes asignados.")

        # Verificar si el doblaje ya está asignado al contenido
        if any(doblaje['idDoblaje'] == idDoblaje for doblaje in doblajes_asignados):
            # Si el doblaje ya está asignado, redirige con un mensaje de error
            return RedirectResponse(
                url="/administrador/actualizar_doblajes?error=true&message=El%20doblaje%20ya%20est%C3%A1%20asignado%20a%20este%20contenido",
                status_code=303
            )

        # Si no está asignado, intenta añadirlo
        response = requests.post(
            f"{BASE_URL_CONTENIDOS}/contenidos/{idDoblajeContenido}/doblajes/{idDoblaje}"
        )

        # Verifica si la llamada al backend fue exitosa
        response.raise_for_status()

        # Redirige con éxito
        return RedirectResponse(
            url="/administrador/actualizar_doblajes?success=true&message=Doblaje%20asignado%20correctamente%20al%20contenido",
            status_code=303
        )

    except requests.exceptions.RequestException as e:
        # Lanza una excepción HTTP si hay algún error en la llamada
        raise HTTPException(status_code=500, detail=f"Error al asignar doblaje: {e}")
    
@app.get("/administrador/administrar_subtitulos_idiomas")
async def administrar_subtitulos_idiomas(
    request: Request, success: str = None, message: str = None
):
    """
    Renderiza la página de administración de subtítulos y muestra mensajes según el estado de las operaciones.
    """
    # Realizar una solicitud GET a la API de contenidos para obtener los subtítulos
    responseSub = requests.get(f"{BASE_URL_CONTENIDOS}/contenidos/subtitulos")

    # Verifica si la respuesta fue exitosa
    if responseSub.status_code == 200:
        subtitulos = responseSub.json()
        return templates.TemplateResponse(
            "admin_administrar_subtitulos_idiomas.html",
            {
                "request": request,
                "subtitulos": subtitulos,
                "success": success,  # Indica si fue exitoso o no
                "message": message,  # Mensaje detallado para el usuario
            },
        )
    else:
        return {
            "error": "No se pudo obtener la lista de subtítulos. Por favor, intente nuevamente."
        }

# Endpoint para crear un nuevo subtítulo
@app.post("/administrador/crear_subtitulo")
async def crear_subtitulo(nuevoIdioma: str = Form(...)):
    """
    Endpoint para crear un nuevo subtítulo.
    Se genera automáticamente un ID para el subtítulo y se envía al backend.
    """
    try:
        # Generar un ID único para el subtítulo
        idSubtitulo = str(uuid.uuid4())[:8]  # Puedes ajustar el formato del ID según sea necesario

        # Enviar la solicitud al microservicio
        response = requests.post(
            f"{BASE_URL_CONTENIDOS}/contenidos/subtitulos/{idSubtitulo}/{nuevoIdioma}"
        )
        response.raise_for_status()  # Lanza una excepción si el backend falla

        # Redirige al mismo HTML con un mensaje de éxito
        return RedirectResponse(
            url=f"/administrador/administrar_subtitulos_idiomas?success=true&message=Subtítulo%20creado%20correctamente",
            status_code=303,
        )

    except requests.exceptions.RequestException as e:
        # Redirige al mismo HTML con un mensaje de error
        return RedirectResponse(
            url=f"/administrador/administrar_subtitulos_idiomas?success=false&message=Error%20al%20crear%20el%20subtítulo",
            status_code=303,
        )


# Endpoint para eliminar un subtítulo
@app.post("/administrador/eliminar_subtitulo")
async def eliminar_subtitulo(idSubtitulo: str = Form(...)):
    """
    Endpoint para eliminar un subtítulo existente.
    """
    try:
        # Realizar la solicitud DELETE al backend
        response = requests.delete(f"{BASE_URL_CONTENIDOS}/contenidos/subtitulos/{idSubtitulo}")
        response.raise_for_status()  # Lanza una excepción si el backend falla

        # Redirige al mismo HTML con un mensaje de éxito
        return RedirectResponse(
            url=f"/administrador/administrar_subtitulos_idiomas?success=true&message=Subtítulo%20eliminado%20correctamente",
            status_code=303,
        )

    except requests.exceptions.RequestException as e:
        # Redirige al mismo HTML con un mensaje de error
        return RedirectResponse(
            url=f"/administrador/administrar_subtitulos_idiomas?success=false&message=Error%20al%20eliminar%20el%20subtítulo",
            status_code=303,
        )
    
@app.get("/administrador/administrar_doblajes_idiomas")
async def administrar_doblajes_idiomas(
    request: Request, success: str = None, message: str = None
):
    """
    Renderiza la página de administración de doblajes y muestra mensajes según el estado de las operaciones.
    """
    # Realizar una solicitud GET a la API de contenidos para obtener los doblajes
    responseSub = requests.get(f"{BASE_URL_CONTENIDOS}/contenidos/doblajes")

    # Verifica si la respuesta fue exitosa
    if responseSub.status_code == 200:
        doblajes = responseSub.json()
        return templates.TemplateResponse(
            "admin_administrar_doblajes_idiomas.html",
            {
                "request": request,
                "doblajes": doblajes,
                "success": success,  # Indica si fue exitoso o no
                "message": message,  # Mensaje detallado para el usuario
            },
        )
    else:
        return {
            "error": "No se pudo obtener la lista de doblajes. Por favor, intente nuevamente."
        }

# Endpoint para crear un nuevo doblaje
@app.post("/administrador/crear_doblaje")
async def crear_doblaje(nuevoIdioma: str = Form(...)):
    """
    Endpoint para crear un nuevo doblaje.
    Se genera automáticamente un ID para el doblaje y se envía al backend.
    """
    try:
        # Generar un ID único para el doblaje
        idDoblaje = str(uuid.uuid4())[:8]  # Puedes ajustar el formato del ID según sea necesario

        # Enviar la solicitud al microservicio
        response = requests.post(
            f"{BASE_URL_CONTENIDOS}/contenidos/doblajes/{idDoblaje}/{nuevoIdioma}"
        )
        response.raise_for_status()  # Lanza una excepción si el backend falla

        # Redirige al mismo HTML con un mensaje de éxito
        return RedirectResponse(
            url=f"/administrador/administrar_doblajes_idiomas?success=true&message=Doblaje%20creado%20correctamente",
            status_code=303,
        )

    except requests.exceptions.RequestException as e:
        # Redirige al mismo HTML con un mensaje de error
        return RedirectResponse(
            url=f"/administrador/administrar_doblajes_idiomas?success=false&message=Error%20al%20crear%20el%20doblaje",
            status_code=303,
        )


# Endpoint para eliminar un doblaje
@app.post("/administrador/eliminar_doblaje")
async def eliminar_doblaje(idDoblaje: str = Form(...)):
    """
    Endpoint para eliminar un doblaje existente.
    """
    try:
        # Realizar la solicitud DELETE al backend
        response = requests.delete(f"{BASE_URL_CONTENIDOS}/contenidos/doblajes/{idDoblaje}")
        response.raise_for_status()  # Lanza una excepción si el backend falla

        # Redirige al mismo HTML con un mensaje de éxito
        return RedirectResponse(
            url=f"/administrador/administrar_doblajes_idiomas?success=true&message=Doblaje%20eliminado%20correctamente",
            status_code=303,
        )

    except requests.exceptions.RequestException as e:
        # Redirige al mismo HTML con un mensaje de error
        return RedirectResponse(
            url=f"/administrador/administrar_doblajes_idiomas?success=false&message=Error%20al%20eliminar%20el%20doblaje",
            status_code=303,
        )


#Endpoint para acceder a la lista de planes de suscripción para actualizarlo o cambiarlo
@app.get("/usuarios/{user_id}/plan_suscripcion")
def obtener_planes_de_suscripcion(request: Request, user_id: str, mensaje: str = None):
    # Se obtienen todos los planes de suscripcion
    response = requests.get(f"{BASE_URL_USUARIOS}/planes-suscripcion")
    if response.status_code != 200:
        mensaje = "Error: no se ha encontrado ningún Plan de Suscripción"
    planes_suscripcionBD = response.json()
    
    # Se obtiene el id del plan de suscripción que posee el usuario
    response = requests.get(f"{BASE_URL_USUARIOS}/usuarios/{user_id}")
    if response.status_code != 200:
        mensaje = "Error: No se ha podido obtener el Plan del Usuario"
    usuario = response.json()
    idPlanSuscripcionUsuario = usuario.get("idPlanSuscripcion")

    #Se redirecciona a la página para mostrar los planes de suscripción
    return templates.TemplateResponse (
            "gestionar_planes_usuario.html",
            {
                "request": request,
                "planes_suscripcionBD": planes_suscripcionBD,
                "idPlanSuscripcionUsuario": idPlanSuscripcionUsuario,
                "user_id": user_id,
                "mensaje": mensaje,
            },
    )

@app.post("/usuarios/{user_id}/actualizar_plan")
async def actualizar_plan(request: Request, user_id: str, plan_id: str = Form(...)):
    # Cuerpo de la solicitud para cambiar el plan de suscripción
    data = {
        "accion": "cambiar",
        "idPlanSuscripcion": plan_id
    }

    # Hacer la solicitud PUT al servicio de usuarios
    response = requests.put(
        f"{BASE_URL_USUARIOS}/usuarios/{user_id}/suscripcion",
        json=data
    )

    if response.status_code == 200:
        mensaje = "Plan actualizado exitosamente"
    else:
        mensaje = "Error: el plan no se pudo actualizar"

    return RedirectResponse(
        url=f"/usuarios/{user_id}/plan_suscripcion?mensaje={mensaje}", status_code=303
    )

@app.post("/usuarios/{user_id}/cancelar_suscripcion")
def cancelar_suscripcion(request: Request, user_id: str):
    data = {
        "accion": "cancelar",
        "idPlanSuscripcion": None
    }

    # Hacer la solicitud PUT al servicio de usuarios
    response = requests.put(
        f"{BASE_URL_USUARIOS}/usuarios/{user_id}/suscripcion",
        json=data
    )

    if response.status_code == 200:
        mensaje = "Actualmente no posees ningún plan en la plataforma"
    else:
        mensaje = "Error: el plan no se pudo eliminar"

    return RedirectResponse(
        url=f"/usuarios/{user_id}/plan_suscripcion?mensaje={mensaje}", status_code=303
    )


