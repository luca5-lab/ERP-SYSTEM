from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_clientes, name='lista_clientes'),
    path('nuevo/', views.registrar_cliente, name='registrar_cliente'),
    path('editar/<int:pk>/', views.editar_cliente, name='editar_cliente'),
    path('eliminar/<int:pk>/', views.eliminar_cliente, name='eliminar_cliente'),
    path('exportar/excel/', views.exportar_clientes_excel, name='exportar_clientes_excel'),
    path('proveedores/', views.lista_proveedores, name='lista_proveedores'),
    path('proveedores/nuevo/', views.registrar_proveedor, name='registrar_proveedor'),
    path('proveedores/editar/<int:pk>/', views.editar_proveedor, name='editar_proveedor'),
    path('proveedores/eliminar/<int:pk>/', views.eliminar_proveedor, name='eliminar_proveedor'),
    path('exportar-proveedores/', views.exportar_proveedores_excel, name='exportar_proveedores_excel'),
    path('informes/', views.informes, name='informes'),
    path('procesos/', views.lista_procesos_clientes, name='procesos_clientes'),
    path('informes/exportar-ventas/', views.exportar_ventas_excel, name='exportar_ventas_excel'),
    path('informes/exportar-compras/', views.exportar_compras_excel, name='exportar_compras_excel'),
    
]