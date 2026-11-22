# To Do List - Debian 13 + XFCE

Aplicación de escritorio para llevar el control de tus tareas por hacer, desarrollada en Python 3 con GTK3.

## Características

- Agregar tareas con título, descripción opcional, prioridad (Baja/Media/Alta) y fecha de vencimiento.
- Marcar tareas como completadas (se tachan automáticamente).
- Eliminar tareas individuales.
- Limpiar todas las tareas completadas de una vez.
- Filtrar por: Todas / Pendientes / Completadas.
- Persistencia automática en `~/.todolist_tasks.json` (JSON).
- Estadísticas en la barra inferior.
- Integración en el menú de aplicaciones de XFCE mediante archivo `.desktop`.

## Requisitos

- Debian 13 (trixie) con entorno XFCE.
- Python 3.10+
- PyGObject con bindings GTK 3 (`python3-gi`, `gir1.2-gtk-3.0`)

## Instalación

1. Clona o copia esta carpeta en tu equipo:

   ```bash
   mkdir -p ~/Apps/todo
   cp todo.py todo.desktop ~/Apps/todo/
   ```

2. Haz ejecutables los archivos:

   ```bash
   chmod +x ~/Apps/todo/todo.py
   ```

3. Instala el lanzador en el menú de XFCE:

   ```bash
   desktop-file-install ~/Apps/todo/todo.desktop
   ```

   O copia manualmente:

   ```bash
   cp ~/Apps/todo/todo.desktop ~/.local/share/applications/
   update-desktop-database ~/.local/share/applications
   ```

4. Ejecuta la aplicación desde el menú de XFCE (categoría Oficina) o desde terminal:

   ```bash
   python3 ~/Apps/todo/todo.py
   ```

## Uso

- Escribe el título de la tarea y presiona **Enter** o haz clic en **Agregar tarea**.
- Marca la casilla para completar una tarea.
- Haz clic en el icono de la papelera para eliminar una tarea.
- Usa los botones superiores para filtrar qué tareas ver.
- Haz clic en **Limpiar completadas** para borrar todas las tareas ya terminadas.

## Archivo de datos

Las tareas se guardan automáticamente en:

```
~/.todolist_tasks.json
```

Puedes hacer copias de seguridad de este archivo o editarlo manualmente si lo deseas.

## Licencia

Uso libre y personal.
