
CLAVE = "carrito"


def obtener_carrito(request):

    return request.session.get(CLAVE, {})


def guardar_carrito(request, carrito):

    request.session[CLAVE] = carrito

    request.session.modified = True


def agregar(request, id_producto, cantidad):

    carrito = obtener_carrito(request)
    clave = str(id_producto)
    carrito[clave] = carrito.get(clave, 0) + cantidad
    guardar_carrito(request, carrito)


def cambiar_cantidad(request, id_producto, cantidad):

    carrito = obtener_carrito(request)
    clave = str(id_producto)
    if cantidad > 0:
        carrito[clave] = cantidad
    elif clave in carrito:
        del carrito[clave]
    guardar_carrito(request, carrito)


def quitar(request, id_producto):

    carrito = obtener_carrito(request)
    clave = str(id_producto)
    if clave in carrito:
        del carrito[clave]
    guardar_carrito(request, carrito)


def vaciar(request):

    guardar_carrito(request, {})


def contar_unidades(request):

    return sum(obtener_carrito(request).values())
