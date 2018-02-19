from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^machines$', views.machines, name='machines'),
    url(r'^log$', views.log, name='log'),
    url(r'^estimate_price$', views.estimate_price, name='estimate_price'),
    url(r'^ws/virtual_machines$', views.ws_virtual_machines, name='ws_virtual_machines'),
    url(r'^ws/virtual_machines/set', views.ws_virtual_machines_set, name='ws_virtual_machines_set'),
    url(r'^ws/login$', views.ws_login, name='ws_login'),
    url(r'^register$', views.register, name='register'),
    url(r'^signin$', views.signin, name='signin'),
    url(r'^signout$', views.signout, name='signout'),
    url(r'^example$', views.example, name='example'),
]
