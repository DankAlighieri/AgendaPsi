from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from functools import wraps

# decorator proprio p/ impedir outros usuarios alem dos profissionais de acessarem certas views
def profissional_required(view):
    @wraps(view)
    @login_required
    def wrapper(req, *args, **kargs):
        profissional = getattr(req.user, "profissional", None)
        if profissional is None:
            return redirect("login")
        req.profissional = profissional
        return view(req, *args, **kargs)
    return wrapper