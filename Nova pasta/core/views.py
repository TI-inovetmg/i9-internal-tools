from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required(login_url='/admin/login/') # Usando o login do admin temporariamente
def home(request):
    return render(request, 'home.html')