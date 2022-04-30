"""climada_calc URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from .settings import BASE_DIR

urlpatterns = [
    path('rest/', include('calc_api.urls')),
    path('restricted/', include('calc_api.rurls')),
    path('admin/', admin.site.urls),
] + static('media', document_root=(BASE_DIR.parent / 'media')) \
  + static('static', document_root=(BASE_DIR.parent / 'static'))
# the static(...) part is for development only
