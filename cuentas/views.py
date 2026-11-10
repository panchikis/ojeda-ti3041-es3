from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, render


def ingresar(request):
    if request.method == "POST":
        nombreUsuario = request.POST.get("usuario", "").strip()
        clave = request.POST.get("password", "")

        usuario = authenticate(request, username=nombreUsuario, password=clave)

        if usuario is not None:
            login(request, usuario)
            request.session["usuario"] = usuario.get_username()
            request.session["nombre"] = usuario.get_full_name() or usuario.get_username()
            request.session["rol"] = "admin" if usuario.is_staff else "cliente"
            return redirect("catalogo:lista")
        contexto = {
            "error": "Usuario o contraseña incorrectos.",
            "usuario": nombreUsuario,
        }
        return render(request, "cuentas/ingresar.html", contexto)

    return render(request, "cuentas/ingresar.html")


def salir(request):
    if request.method == "POST":
        logout(request)
    return redirect("catalogo:inicio")
