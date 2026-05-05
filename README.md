ERP System – Business Management & Workflow Platform
Descripción

Sistema ERP web desarrollado con Django para la gestión integral de una empresa orientada a servicios y venta de productos. Permite administrar clientes, proveedores, 
cotizaciones, órdenes de compra, facturación, órdenes de trabajo (OT) y control de procesos internos por áreas.

El sistema centraliza la operación completa de la empresa, desde la cotización hasta la ejecución y cierre del trabajo.

FUNCIONALIDADES PRINCIPALES

GESTION COMERCIAL:
Gestión de servicios y productos internos (crear, editar, eliminar)
Administración de clientes y proveedores
Diferenciación entre:
Clientes - servicios/productos vendidos
Proveedores - insumos para compra y reventa

COTIZACIONES:
Creación de cotizaciones personalizadas
Ajuste dinámico de precios (ej: descuentos por cliente)
Generación automática de PDF listo para envío al cliente

ÓRDENES DE COMPRA:
Generación de órdenes para proveedores
Exportación en PDF
Gestión de compras empresariales

FACTURACION:
Registro de facturas
Subida de PDF externos (ej: sistema tributario)
Asociación de facturas a trabajos finalizados

ÓRDENES DE TRABAJO (OT):
Sistema completo de flujo de trabajo por áreas:

Creación de OT por ADMINISTRACIÓN
Asignación a:
Taller
Diseño
Ambos
Diseño:
Gestión de medidas, imágenes y archivos
Edición de datos
Aprobación final del diseño
Taller:
Control de producción (impresión, corte, etc.)
Checklists de procesos
Datos técnicos (riesgos, instalación, permisos, etc.)
Flujo:

Administración - Diseño - Taller - Administración - Facturación - Finalización

GESTION DE USUARIOS POR ROLES:

Administrador:
-Control total del sistema
-Seguimiento de procesos y métricas

Diseñador:
-Acceso a órdenes de diseño
-Edición y aprobación de trabajos

Taller:
-Gestión de producción
-Seguimiento de tareas asignadas

CONTROL Y MONITOREO:
Historial completo de acciones de usuarios (auditoría)
Visualización de progreso en porcentaje por trabajo
Panel administrativo

GESTIÓN DE STOCK:
Control de inventario interno
Ajuste de materiales (entrada/salida)
Alertas automáticas por correo cuando el stock baja (ej: 30%)

REPORTES Y ANÁLISIS:
Ventas (facturas pagadas)
Compras realizadas
Exportación de datos a Excel:
Clientes
Proveedores
Ventas
Compras

TECNOLOGIAS UTILIZADAS:
Python
Django
SQLite / MySQL
HTML5, CSS3, JavaScript
Generación de PDF
Envío de correos automáticos

CARACTERÍSTICAS TÉCNICAS:
Arquitectura basada en Django (MVT)
Sistema multiusuario con roles y permisos
Flujo de trabajo empresarial automatizado
Integración de archivos (PDF, imágenes)
Sistema modular y escalable

OBJETIVO DEL PROYECTO:
Desarrollar una solución completa para la gestión operativa de una empresa, digitalizando procesos comerciales, productivos y administrativos en una única plataforma.
