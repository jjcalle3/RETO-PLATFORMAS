# ISBER Solutions — Plataforma de Distribución

Plataforma web para que una distribuidora gestione su catálogo, su inventario, los pedidos de sus tiendas clientas y las entregas — todo en un solo lugar, sin depender de llamadas telefónicas o WhatsApp para coordinar.

**Demo en vivo:** https://isber-distribution-hub--josuexpardoch.replit.app/


---

## ¿Qué hace la plataforma?

- **Catálogo e inventario** — el distribuidor mantiene sus productos, categorías, marcas, precios y descuentos, y controla el stock por bodega: recepción de mercadería, conteos físicos, ajustes y un historial completo de cada movimiento.
- **Pedidos con flujo claro** — cada tienda arma su pedido explorando el catálogo, lo envía a su vendedor asignado, y ambos ven en tiempo real por qué etapa va pasando.
- **Entregas confirmadas por quien recibe** — el repartidor marca la entrega con un toque desde el celular, pero es la propia tienda quien confirma que todo llegó bien (o reporta un problema) — así el registro queda validado por quien de verdad lo recibió, no solo por quien lo dejó.
- **Notificaciones automáticas** — cada cambio de estado avisa a quien corresponde dentro de la plataforma; nadie tiene que preguntar "¿cómo va mi pedido?".
- **Panel de operaciones y auditoría** — el distribuidor tiene métricas del negocio (pedidos por estado, tiempos de cumplimiento, alertas de stock bajo) y puede consultar el historial completo de cualquier pedido o cambio en el catálogo.
- **Cada distribuidora ve solo lo suyo** — usuarios, productos, tiendas y pedidos están completamente separados entre distribuidoras distintas que usan la misma plataforma.

## Los cuatro roles

| Rol | Qué hace en la plataforma |
|---|---|
| **Distribuidor** | Administra el catálogo y el inventario, crea las cuentas del resto del equipo, revisa el panel de operaciones y consulta la auditoría. |
| **Vendedor** | Recibe los pedidos de las tiendas que tiene asignadas, revisa el stock disponible y decide si los acepta, los rechaza o los despacha. |
| **Dueño de Tienda** | Arma sus pedidos desde el catálogo, sigue su estado paso a paso, y al recibir la mercadería confirma que llegó bien o reporta un problema. |
| **Repartidor** | Ve los pedidos listos para entregar, obtiene la ruta hacia la tienda y confirma cada entrega con un solo toque. |

## El flujo de un pedido, de principio a fin

1. **La tienda arma su pedido** — explora el catálogo, agrega productos al carrito y lo envía. El pedido queda **Pendiente**.
2. **El vendedor lo revisa** — si hay stock suficiente, lo **acepta** (el inventario se descuenta automáticamente); si no puede cumplirlo, lo **rechaza** explicando el motivo.
3. **El vendedor despacha el pedido** — una vez aceptado, lo marca como **Despachado** y se vuelve visible para el equipo de reparto.
4. **El repartidor lo entrega** — ve la ruta hacia la tienda y, al dejarlo, lo marca como **Entregado**.
5. **La tienda confirma la recepción** — si todo llegó correctamente, lo **confirma** y el pedido queda cerrado; si algo no llegó bien, **reporta el problema** y el vendedor (o el distribuidor) lo resuelve.


---

## Cuentas de prueba (demo)

http://127.0.0.1:8000/accounts/

| Rol | Correo | Contraseña |
|---|---|---|
| Administrador (Distribuidor) | admin@isber.ec | password123 / testpass123 |
| Vendedor | vendedor@isber.ec | password123 / testpass123 |
| Tienda (Dueño de Tienda) | tienda@isber.ec | password123 / testpass123 |
| Repartidor | repartidor@isber.ec | password123 / testpass123 |

<img width="657" height="321" alt="image" src="https://github.com/user-attachments/assets/d93822dd-51cc-4757-b0e8-cbce0d48f730" />

---

## Para desarrolladores

Arranque rápido en local:

```
Con un entorno virtual instalar las dependencias utilizando el requirements.txt
cd proyectoDistribuidora
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```
