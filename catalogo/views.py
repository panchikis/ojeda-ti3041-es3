from django.db.models import Avg, Count, F, Sum
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.html import escape

from . import carrito as bolsa
from .forms import ConsultaClienteForm
from .models import Categoria, ConsultaCliente, Producto


def imagen_producto(_request, id):
  producto = get_object_or_404(
      Producto.objects.select_related("categoria"),
      pk=id,
  )

  categoria = producto.categoria.nombre
  formas = {
    "Herramientas manuales": '<path d="M355 120h70v170h-70z"/><path d="M330 265h120l50 190H280z"/>',
    "Medición": '<rect x="185" y="220" width="430" height="90" rx="15"/><path d="M230 220v42m48-42v25m48-25v42m48-42v25m48-25v42m48-42v25m48-25v42"/>',
    "Herramientas eléctricas": '<path d="M290 160h180v170H290z"/><path d="M330 330h100v145H330z"/><circle cx="380" cy="245" r="48"/>',
    "Accesorios eléctricos": '<path d="M330 120h100v110H330z"/><path d="M355 230v240m50-240v240M300 470h160"/>',
    "Fijaciones": '<path d="M270 150h220v65H270z"/><path d="M300 215v270m80-270v270m80-270v270"/>',
    "Pinturas": '<path d="M285 145h190v280H285z"/><path d="M315 110h130v35H315z"/><path d="M320 255h120"/>',
    "Electricidad": '<path d="M340 110h80v120h-80z"/><path d="M360 230v240m40-240v240"/><circle cx="380" cy="170" r="18"/>',
    "Gasfitería": '<path d="M255 190h250v75H255z"/><path d="M330 265v150h100V265"/><circle cx="380" cy="455" r="45"/>',
    "Seguridad": '<path d="M270 245q110-150 220 0v55H270z"/><path d="M310 300v125h140V300"/>',
    "Escaleras": '<path d="M280 120h55l130 360h-55z"/><path d="M425 120h55L350 480h-55z"/><path d="M330 210h125m-95 80h125m-95 80h125"/>',
  }
  forma = formas.get(categoria, formas["Herramientas manuales"])
  nombre = escape(producto.nombre)
  categoria_segura = escape(categoria.upper())
  svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 560" role="img" aria-label="{nombre}">
    <rect width="760" height="560" fill="#e8ece7"/>
    <path d="M0 430 180 250l160 150 130-180 290 250v90H0z" fill="#d9e1db"/>
    <circle cx="650" cy="105" r="72" fill="#f4a33a" opacity=".3"/>
    <g fill="#20282a" stroke="#f36a21" stroke-width="12" stroke-linejoin="round">{forma}</g>
    <text x="42" y="62" fill="#c95113" font-family="Arial,sans-serif" font-size="18" font-weight="700" letter-spacing="3">{categoria_segura}</text>
    <text x="42" y="515" fill="#20282a" font-family="Arial,sans-serif" font-size="24" font-weight="700">{nombre}</text>
  </svg>'''
  return HttpResponse(svg, content_type="image/svg+xml")

def lista(request):
    productos = Producto.objects.select_related("categoria").order_by("pk")
    total = productos.count()
    disponibles = productos.filter(stock__gt=0).count()
    contexto = {
        "productos": productos,
        "categorias": Categoria.objects.order_by("nombre"),
        "total": total,
        "disponibles": disponibles,
        "sin_stock": total - disponibles,
    }
    return render(request, "catalogo/lista.html", contexto)


def contacto(request):
    if request.method == "POST":
        formulario = ConsultaClienteForm(request.POST)
        if formulario.is_valid():
            consulta = formulario.save()
            return render(
                request,
                "catalogo/contacto_listo.html",
                {"consulta": consulta},
            )
    else:
        formulario = ConsultaClienteForm()

    return render(request, "catalogo/contacto.html", {"formulario": formulario})


def _obtener_productos_recientes(request, producto_actual=None):
    visitados = request.session.get("productos_visitados", [])
    if not isinstance(visitados, list):
        visitados = []

    ids_visitados = []
    if producto_actual is not None:
        ids_visitados.append(producto_actual.pk)

    for producto_id in visitados:
        try:
            producto_id = int(producto_id)
        except (TypeError, ValueError):
            continue
        if producto_id not in ids_visitados:
            ids_visitados.append(producto_id)
        if len(ids_visitados) == 3:
            break

    productos_por_id = {
        producto.pk: producto
        for producto in Producto.objects.select_related("categoria").filter(
            pk__in=ids_visitados
        )
    }
    ids_visitados = [
        producto_id for producto_id in ids_visitados if producto_id in productos_por_id
    ]
    request.session["productos_visitados"] = ids_visitados
    return [productos_por_id[pk] for pk in ids_visitados]


def consultas_clientes(request):
    if request.session.get("rol") != "admin":
        return redirect("cuentas:ingresar")

    consultas = ConsultaCliente.objects.select_related("producto").order_by("-fecha")
    return render(
        request,
        "catalogo/consultas.html",
        {
            "consultas": consultas,
            "estados_consulta": ConsultaCliente.Estado.choices,
        },
    )


def actualizar_estado_consulta(request, id):
    if request.session.get("rol") != "admin":
        return redirect("cuentas:ingresar")
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    consulta = get_object_or_404(ConsultaCliente, pk=id)
    estado = request.POST.get("estado")
    if estado not in ConsultaCliente.Estado.values:
        return HttpResponseBadRequest("Estado de consulta no válido.")

    consulta.estado = estado
    consulta.save(update_fields=["estado"])
    return redirect("catalogo:consultas_clientes")


def reporte_categorias(request):
    if request.session.get("rol") != "admin":
        return redirect("cuentas:ingresar")

    categorias = Categoria.objects.annotate(
        cantidad_productos=Count("producto"),
        precio_promedio=Avg("producto__precio"),
        stock_total=Sum("producto__stock"),
    ).order_by("nombre")

    return render(
        request,
        "catalogo/reporte_categorias.html",
        {"categorias": categorias},
    )


def reporte_stock_critico(request):
    if request.session.get("rol") != "admin":
        return redirect("cuentas:ingresar")

    try:
        umbral = int(request.GET.get("umbral", "10"))
        if umbral < 0:
            raise ValueError
        error_umbral = ""
    except ValueError:
        umbral = 10
        error_umbral = "Ingresa un umbral válido de cero o más unidades."

    productos = Producto.objects.select_related("categoria").filter(
        stock__lte=umbral,
    ).order_by("stock", "nombre")
    contexto = {
        "productos": productos,
        "umbral": umbral,
        "error_umbral": error_umbral,
    }
    return render(request, "catalogo/reporte_stock.html", contexto)


def detalle(request, id):
    producto = get_object_or_404(
        Producto.objects.select_related("categoria"),
        pk=id,
    )
    productos_recientes = _obtener_productos_recientes(request, producto)

    return render(
        request,
        "catalogo/detalle.html",
        {
            "producto": producto,
            "productos_recientes": productos_recientes,
        },
    )


def agregar_stock(request, id):
    if request.session.get("rol", "") != "admin":
        return redirect("cuentas:ingresar")

    producto = get_object_or_404(Producto, pk=id)

    if request.method == "POST":
        try:
            cantidad = int(request.POST.get("cantidad", "0"))
        except ValueError:
            cantidad = 0

        if cantidad > 0:
            Producto.objects.filter(pk=producto.pk).update(stock=F("stock") + cantidad)

    return redirect("catalogo:detalle", id=producto.pk)


def inicio(request):
    contexto = {
        "destacados": Producto.objects.select_related("categoria").order_by("pk")[:6],
        "total": Producto.objects.count(),
        "disponibles": Producto.objects.filter(stock__gt=0).count(),
        "categorias": Categoria.objects.order_by("nombre"),
        "productos_recientes": _obtener_productos_recientes(request),
    }
    return render(request, "catalogo/inicio.html", contexto)


def agregar_producto(request):
    if request.session.get("rol", "") != "admin":
        return redirect("cuentas:ingresar")

    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()
        categoria = request.POST.get("categoria", "").strip()
        precio = request.POST.get("precio", "").strip()
        stock = request.POST.get("stock", "").strip()
        imagen_url = request.POST.get("imagen_url", "").strip()

        errores = []
        if nombre == "":
            errores.append("El nombre es obligatorio.")
        if categoria == "":
            errores.append("La categoría es obligatoria.")
        if imagen_url and not imagen_url.startswith(("http://", "https://")):
            errores.append("La URL de imagen debe comenzar con http:// o https://.")

        try:
            precio = int(precio)
            if precio < 0:
                errores.append("El precio no puede ser negativo.")
        except ValueError:
            errores.append("El precio tiene que ser un número entero.")

        try:
            stock = int(stock)
            if stock < 0:
                errores.append("El stock no puede ser negativo.")
        except ValueError:
            errores.append("El stock tiene que ser un número entero.")

        if errores:
            contexto = {
                "errores": errores,
                "categorias": Categoria.objects.order_by("nombre").values_list(
                    "nombre",
                    flat=True,
                ),
                "datos": request.POST,
            }
            return render(request, "catalogo/agregar.html", contexto)

        categoria_obj, _ = Categoria.objects.get_or_create(nombre=categoria)
        producto = Producto.objects.create(
            nombre=nombre,
            categoria=categoria_obj,
            precio=precio,
            stock=stock,
            imagen=imagen_url,
        )
        if not imagen_url:
            producto.imagen = reverse("catalogo:imagen_producto", args=[producto.pk])
            producto.save(update_fields=["imagen"])
        return redirect("catalogo:lista")

    contexto = {
        "categorias": Categoria.objects.order_by("nombre").values_list(
            "nombre",
            flat=True,
        )
    }
    return render(request, "catalogo/agregar.html", contexto)







def editar_producto(request, id):
    """Edita un producto existente desde el sitio."""
    if request.session.get("rol", "") != "admin":
        return redirect("cuentas:ingresar")

    producto = get_object_or_404(Producto, pk=id)

    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()
        categoria = request.POST.get("categoria", "").strip()
        precio = request.POST.get("precio", "").strip()
        stock = request.POST.get("stock", "").strip()
        imagen = request.POST.get("imagen", "").strip()

        errores = []
        if nombre == "":
            errores.append("El nombre es obligatorio.")
        if categoria == "":
            errores.append("La categoria es obligatoria.")

        try:
            precio = int(precio)
            if precio < 0:
                errores.append("El precio no puede ser negativo.")
        except ValueError:
            errores.append("El precio tiene que ser un numero entero.")

        try:
            stock = int(stock)
            if stock < 0:
                errores.append("El stock no puede ser negativo.")
        except ValueError:
            errores.append("El stock tiene que ser un numero entero.")

        if errores:
            contexto = {
                "producto": producto,
                "errores": errores,
                "categorias": Categoria.objects.order_by("nombre").values_list(
                    "nombre", flat=True,
                ),
                "datos": request.POST,
            }
            return render(request, "catalogo/editar.html", contexto)

        categoria_obj, _ = Categoria.objects.get_or_create(nombre=categoria)

        producto.nombre = nombre
        producto.categoria = categoria_obj
        producto.precio = precio
        producto.stock = stock
        producto.imagen = imagen
        producto.save()

        return redirect("catalogo:lista")

    contexto = {
        "producto": producto,
        "categorias": Categoria.objects.order_by("nombre").values_list(
            "nombre", flat=True,
        ),
    }
    return render(request, "catalogo/editar.html", contexto)


def eliminar_producto(request, id):
    """Elimina un producto, pidiendo confirmacion antes."""
    if request.session.get("rol", "") != "admin":
        return redirect("cuentas:ingresar")

    producto = get_object_or_404(Producto, pk=id)

    if request.method == "POST":
        producto.delete()
        return redirect("catalogo:lista")

    return render(request, "catalogo/eliminar.html", {"producto": producto})



def ver_carrito(request):
    """Muestra el carrito con sus productos, subtotales y total."""
    guardado = bolsa.obtener_carrito(request)

    ids = [int(clave) for clave in guardado.keys()]
    productos = Producto.objects.select_related("categoria").filter(pk__in=ids)

    lineas = []
    total = 0
    for producto in productos:
        cantidad = guardado[str(producto.pk)]
        subtotal = producto.precio * cantidad
        total = total + subtotal
        lineas.append({
            "producto": producto,
            "cantidad": cantidad,
            "subtotal": subtotal,
            "sin_stock_suficiente": cantidad > producto.stock,
        })

    contexto = {
        "lineas": lineas,
        "total": total,
        "hay_problemas": any(linea["sin_stock_suficiente"] for linea in lineas),
    }
    return render(request, "catalogo/carrito.html", contexto)


def agregar_al_carrito(request, id):
    """Agrega unidades de un producto al carrito."""
    producto = get_object_or_404(Producto, pk=id)

    if request.method == "POST":
        try:
            cantidad = int(request.POST.get("cantidad", "1"))
        except ValueError:
            cantidad = 1

        if cantidad > 0 and producto.stock > 0:
            bolsa.agregar(request, producto.pk, cantidad)

    return redirect("catalogo:ver_carrito")


def actualizar_carrito(request, id):
    """Cambia la cantidad de un producto que ya esta en el carrito."""
    if request.method == "POST":
        try:
            cantidad = int(request.POST.get("cantidad", "0"))
        except ValueError:
            cantidad = 0
        bolsa.cambiar_cantidad(request, id, cantidad)

    return redirect("catalogo:ver_carrito")


def quitar_del_carrito(request, id):
    """Saca un producto del carrito."""
    if request.method == "POST":
        bolsa.quitar(request, id)

    return redirect("catalogo:ver_carrito")


def vaciar_carrito(request):
    """Deja el carrito vacio."""
    if request.method == "POST":
        bolsa.vaciar(request)

    return redirect("catalogo:ver_carrito")


def confirmar_carrito(request):
    """Confirma la compra: descuenta el stock de todos los productos."""
    if "usuario" not in request.session:
        return redirect("cuentas:ingresar")

    if request.method != "POST":
        return redirect("catalogo:ver_carrito")

    guardado = bolsa.obtener_carrito(request)
    if not guardado:
        return redirect("catalogo:ver_carrito")

    comprados = []
    errores = []

    for clave, cantidad in guardado.items():
        producto = Producto.objects.filter(pk=int(clave)).first()
        if producto is None:
            continue

        actualizado = Producto.objects.filter(
            pk=producto.pk,
            stock__gte=cantidad,
        ).update(stock=F("stock") - cantidad)

        if actualizado:
            comprados.append({"nombre": producto.nombre, "cantidad": cantidad,
                              "subtotal": producto.precio * cantidad})
        else:
            producto.refresh_from_db()
            errores.append(
                f"{producto.nombre}: pediste {cantidad} y quedan {producto.stock}."
            )

    if comprados:
        nuevo = {}
        for clave, cantidad in guardado.items():
            producto = Producto.objects.filter(pk=int(clave)).first()
            if producto is not None and any(c["nombre"] == producto.nombre for c in comprados):
                continue
            nuevo[clave] = cantidad
        bolsa.guardar_carrito(request, nuevo)

    contexto = {
        "comprados": comprados,
        "errores": errores,
        "total": sum(c["subtotal"] for c in comprados),
    }
    return render(request, "catalogo/compra_lista.html", contexto)
