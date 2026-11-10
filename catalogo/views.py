from django.db.models import F
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.html import escape

from . import carrito as bolsa
from .models import Categoria, Producto


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


def detalle(request, id):
    producto = get_object_or_404(
        Producto.objects.select_related("categoria"),
        pk=id,
    )
    return render(request, "catalogo/detalle.html", {"producto": producto})


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
    }
    return render(request, "catalogo/inicio.html", contexto)


def comprar(request, id):
    if "usuario" not in request.session:
        return redirect("cuentas:ingresar")

    producto = get_object_or_404(
        Producto.objects.select_related("categoria"),
        pk=id,
    )

    if producto.stock == 0:
        contexto = {"producto": producto, "sin_stock": True}
        return render(request, "catalogo/comprar.html", contexto)

    cantidad = 0
    error = None
    if request.method == "POST":
        try:
            cantidad = int(request.POST.get("cantidad", "0"))
        except ValueError:
            cantidad = 0

        if cantidad < 1:
            error = "Selecciona al menos una unidad."
        else:
            actualizado = Producto.objects.filter(
                pk=producto.pk,
                stock__gte=cantidad,
            ).update(stock=F("stock") - cantidad)
            producto.refresh_from_db()
            if not actualizado:
                error = f"Solo quedan {producto.stock} unidades disponibles."

    if request.method != "POST" or error:
        contexto = {"producto": producto, "sin_stock": False, "error": error}
        return render(request, "catalogo/comprar.html", contexto)

    contexto = {"producto": producto, "sin_stock": False, "cantidad": cantidad}
    return render(request, "catalogo/comprar.html", contexto)


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
        return redirect("catalogo:detalle", id=producto.pk)

    contexto = {
        "categorias": Categoria.objects.order_by("nombre").values_list(
            "nombre",
            flat=True,
        )
    }
    return render(request, "catalogo/agregar.html", contexto)


def ver_carrito(request):
    guardado = bolsa.obtener_carrito(request)
    ids = []
    for clave in guardado.keys():
        try:
            ids.append(int(clave))
        except (TypeError, ValueError):
            continue

    productos = Producto.objects.select_related("categoria").filter(pk__in=ids)
    lineas = []
    total = 0
    for producto in productos:
        cantidad = guardado.get(str(producto.pk), 0)
        subtotal = producto.precio * cantidad
        total += subtotal
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
    producto = get_object_or_404(Producto, pk=id)
    if request.method == "POST":
        try:
            cantidad = int(request.POST.get("cantidad", "1"))
        except (TypeError, ValueError):
            cantidad = 1
        if cantidad > 0:
            actual = bolsa.obtener_carrito(request).get(str(producto.pk), 0)
            if actual + cantidad <= producto.stock:
                bolsa.agregar(request, producto.pk, cantidad)
    return redirect("catalogo:ver_carrito")


def actualizar_carrito(request, id):
    producto = get_object_or_404(Producto, pk=id)
    if request.method == "POST":
        try:
            cantidad = int(request.POST.get("cantidad", "0"))
        except (TypeError, ValueError):
            cantidad = 0
        if cantidad <= producto.stock:
            bolsa.cambiar_cantidad(request, producto.pk, cantidad)
        else:
            bolsa.cambiar_cantidad(request, producto.pk, producto.stock)
    return redirect("catalogo:ver_carrito")


def quitar_del_carrito(request, id):
    if request.method == "POST":
        bolsa.quitar(request, id)
    return redirect("catalogo:ver_carrito")


def vaciar_carrito(request):
    if request.method == "POST":
        bolsa.vaciar(request)
    return redirect("catalogo:ver_carrito")


def confirmar_carrito(request):
    if "usuario" not in request.session:
        return redirect("cuentas:ingresar")
    if request.method != "POST":
        return redirect("catalogo:ver_carrito")

    guardado = bolsa.obtener_carrito(request)
    if not guardado:
        return redirect("catalogo:ver_carrito")

    comprados = []
    errores = []
    exitosas = set()
    for clave, cantidad in guardado.items():
        try:
            producto_id = int(clave)
            cantidad = int(cantidad)
        except (TypeError, ValueError):
            continue

        producto = Producto.objects.filter(pk=producto_id).first()
        if producto is None or cantidad < 1:
            continue

        actualizado = Producto.objects.filter(
            pk=producto.pk,
            stock__gte=cantidad,
        ).update(stock=F("stock") - cantidad)

        if actualizado:
            comprados.append({
                "nombre": producto.nombre,
                "cantidad": cantidad,
                "subtotal": producto.precio * cantidad,
            })
            exitosas.add(clave)
        else:
            producto.refresh_from_db()
            errores.append(
                f"{producto.nombre}: pediste {cantidad} y quedan {producto.stock}."
            )

    if exitosas:
        nuevo = {
            clave: cantidad
            for clave, cantidad in guardado.items()
            if clave not in exitosas
        }
        bolsa.guardar_carrito(request, nuevo)

    contexto = {
        "comprados": comprados,
        "errores": errores,
        "total": sum(item["subtotal"] for item in comprados),
    }
    return render(request, "catalogo/compra_lista.html", contexto)
