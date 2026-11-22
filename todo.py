#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
To Do List - Aplicación de control de tareas para Debian 13 con XFCE.
Interfaz gráfica con GTK3 y persistencia en JSON.
"""

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")

from gi.repository import Gtk, Gdk, GLib
import json
import os
import sys
from datetime import datetime


DATA_FILE = os.path.join(os.path.expanduser("~"), ".todolist_tasks.json")


class Task:
    """Representa una tarea individual."""

    def __init__(self, title, description="", priority="Media",
                 due_date=None, completed=False, created_at=None):
        self.title = title
        self.description = description
        self.priority = priority  # Baja, Media, Alta
        self.due_date = due_date  # string YYYY-MM-DD o None
        self.completed = completed
        self.created_at = created_at or datetime.now().isoformat()

    def to_dict(self):
        return {
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "due_date": self.due_date,
            "completed": self.completed,
            "created_at": self.created_at,
        }

    @staticmethod
    def from_dict(d):
        return Task(
            title=d.get("title", ""),
            description=d.get("description", ""),
            priority=d.get("priority", "Media"),
            due_date=d.get("due_date"),
            completed=d.get("completed", False),
            created_at=d.get("created_at"),
        )


class TodoWindow(Gtk.Window):
    """Ventana principal de la aplicación."""

    PRIORITIES = ["Baja", "Media", "Alta"]
    FILTER_ALL = "Todas"
    FILTER_ACTIVE = "Pendientes"
    FILTER_COMPLETED = "Completadas"

    def __init__(self):
        Gtk.Window.__init__(self, title="To Do List")
        self.set_default_size(700, 500)
        self.set_border_width(10)
        self.set_position(Gtk.WindowPosition.CENTER)

        self.tasks = []
        self.filter_mode = self.FILTER_ALL
        self.sort_reverse = False
        self.listbox = None
        self.lbl_stats = None
        self.load_tasks()

        # Ícono de la ventana (debe coincidir con el archivo .desktop)
        self.set_icon_name("appointment-new")

        self._build_ui()
        if self.listbox is not None:
            self.refresh_task_list()

        self.connect("destroy", Gtk.main_quit)

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(main_box)

        # --- Barra de filtro ---
        filter_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        filter_box.set_halign(Gtk.Align.FILL)
        filter_box.set_hexpand(True)

        lbl_filter = Gtk.Label(label="Ver: ")
        filter_box.pack_start(lbl_filter, False, False, 0)

        self.btn_filter_all = Gtk.Button.new_with_label(self.FILTER_ALL)
        self.btn_filter_active = Gtk.Button.new_with_label(self.FILTER_ACTIVE)
        self.btn_filter_completed = Gtk.Button.new_with_label(self.FILTER_COMPLETED)

        for b in (self.btn_filter_all, self.btn_filter_active, self.btn_filter_completed):
            b.set_relief(Gtk.ReliefStyle.NONE)
            b.connect("clicked", self.on_filter_clicked, b.get_label())

        filter_box.pack_start(self.btn_filter_all, False, False, 0)
        filter_box.pack_start(self.btn_filter_active, False, False, 0)
        filter_box.pack_start(self.btn_filter_completed, False, False, 0)
        self._set_filter_button_active(self.btn_filter_all)

        main_box.pack_start(filter_box, False, False, 0)

        separador = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        main_box.pack_start(separador, False, False, 0)

        # --- Formulario de nueva tarea ---
        form_frame = Gtk.Frame(label="Nueva tarea")
        form_frame.set_shadow_type(Gtk.ShadowType.ETCHED_OUT)
        main_box.pack_start(form_frame, False, False, 0)

        form_grid = Gtk.Grid()
        form_grid.set_column_spacing(6)
        form_grid.set_row_spacing(4)
        form_grid.set_border_width(10)
        form_frame.add(form_grid)

        self.entry_title = Gtk.Entry()
        self.entry_title.set_placeholder_text("Título de la tarea...")
        self.entry_title.set_hexpand(True)
        self.entry_title.connect("activate", self.on_add_task)

        self.entry_desc = Gtk.Entry()
        self.entry_desc.set_placeholder_text("Descripción (opcional)...")
        self.entry_desc.set_hexpand(True)

        self.combo_priority = Gtk.ComboBoxText()
        for p in self.PRIORITIES:
            self.combo_priority.append_text(p)
        self.combo_priority.set_active(1)  # Media

        self.entry_due = Gtk.Entry()
        self.entry_due.set_placeholder_text("Vence: YYYY-MM-DD (opcional)")
        self.entry_due.set_hexpand(True)

        btn_add = Gtk.Button.new_with_label("Agregar tarea")
        btn_add.connect("clicked", self.on_add_task)
        btn_add.get_style_context().add_class("suggested-action")

        form_grid.attach(Gtk.Label(label="Título:"), 0, 0, 1, 1)
        form_grid.attach(self.entry_title, 1, 0, 3, 1)
        form_grid.attach(Gtk.Label(label="Descripción:"), 0, 1, 1, 1)
        form_grid.attach(self.entry_desc, 1, 1, 2, 1)
        form_grid.attach(Gtk.Label(label="Prioridad:"), 3, 1, 1, 1)
        form_grid.attach(self.combo_priority, 4, 1, 1, 1)
        form_grid.attach(Gtk.Label(label="Vencimiento:"), 0, 2, 1, 1)
        form_grid.attach(self.entry_due, 1, 2, 2, 1)
        form_grid.attach(btn_add, 3, 2, 2, 1)

        # --- Lista de tareas ---
        list_frame = Gtk.Frame(label="Tareas")
        list_frame.set_shadow_type(Gtk.ShadowType.ETCHED_OUT)
        main_box.pack_start(list_frame, True, True, 0)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        list_frame.add(scrolled)

        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.listbox.activate_on_row_enter = False
        scrolled.add(self.listbox)

        # --- Barra inferior ---
        bottom_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        bottom_box.set_halign(Gtk.Align.FILL)
        bottom_box.set_hexpand(True)

        self.lbl_stats = Gtk.Label(label="0 tareas")
        self.lbl_stats.set_halign(Gtk.Align.START)
        bottom_box.pack_start(self.lbl_stats, True, True, 0)

        btn_clear = Gtk.Button.new_with_label("Limpiar completadas")
        btn_clear.connect("clicked", self.on_clear_completed)
        bottom_box.pack_end(btn_clear, False, False, 0)

        self.main_box = main_box
        self.bottom_box = bottom_box
        self._finish_ui()
    # ------------------------------------------------------------------ Lógica
    def load_tasks(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.tasks = [Task.from_dict(d) for d in data]
            except (json.JSONDecodeError, IOError):
                self.tasks = []
        else:
            self.tasks = []

    def save_tasks(self):
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump([t.to_dict() for t in self.tasks], f,
                          ensure_ascii=False, indent=2)
        except IOError as e:
            dialog = Gtk.MessageDialog(
                transient_for=self, flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Error al guardar",
            )
            dialog.format_secondary_text(str(e))
            dialog.run()
            dialog.destroy()

    def refresh_task_list(self):
        if self.listbox is None:
            return
        for child in self.listbox.get_children():
            self.listbox.remove(child)

        if self.filter_mode == self.FILTER_ACTIVE:
            filtered = [t for t in self.tasks if not t.completed]
        elif self.filter_mode == self.FILTER_COMPLETED:
            filtered = [t for t in self.tasks if t.completed]
        else:
            filtered = list(self.tasks)

        filtered.sort(key=lambda t: (t.completed, t.created_at),
                      reverse=self.sort_reverse)

        for task in filtered:
            row = self._build_task_row(task)
            self.listbox.add(row)

        self.listbox.show_all()
        self._update_stats()
    def _build_task_row(self, task):
        row = Gtk.ListBoxRow()
        row.set_activatable(False)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        hbox.set_border_width(6)
        hbox.set_hexpand(True)
        row.add(hbox)

        chk = Gtk.CheckButton()
        chk.set_active(task.completed)
        chk.connect("toggled", self.on_task_toggled, task)
        hbox.pack_start(chk, False, False, 0)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        vbox.set_hexpand(True)

        title_label = Gtk.Label(label=task.title)
        title_label.set_xalign(0)
        title_label.set_hexpand(True)
        title_label.get_style_context().add_class("task-title")
        if task.completed:
            title_label.get_style_context().add_class("completed")

        desc_label = Gtk.Label(label=task.description if task.description else "")
        desc_label.set_xalign(0)
        desc_label.set_hexpand(True)
        if task.description:
            desc_label.get_style_context().add_class("task-desc")
            if task.completed:
                desc_label.get_style_context().add_class("completed")

        meta_parts = []
        if task.priority:
            meta_parts.append(f"Prioridad: {task.priority}")
        if task.due_date:
            meta_parts.append(f"Vence: {task.due_date}")
        else:
            meta_parts.append("Sin fecha de vencimiento")
        meta_label = Gtk.Label(label="  |  ".join(meta_parts))
        meta_label.set_xalign(0)
        meta_label.set_hexpand(True)
        meta_label.get_style_context().add_class("task-meta")

        vbox.pack_start(title_label, False, False, 0)
        if task.description:
            vbox.pack_start(desc_label, False, False, 0)
        vbox.pack_start(meta_label, False, False, 0)

        hbox.pack_start(vbox, True, True, 0)

        btn_edit = self._create_icon_button(
            "accessories-text-editor", "Editar tarea", "Editar",
            self.on_task_edit, task
        )
        hbox.pack_end(btn_edit, False, False, 0)

        btn_del = self._create_icon_button(
            "user-trash", "Eliminar tarea", "Eliminar",
            self.on_task_delete, task
        )
        hbox.pack_end(btn_del, False, False, 0)

        row.show_all()
        return row

    def _build_ui_bottom_buttons(self):
        # Esta función se llama al final de _build_ui para agregar los botones inferiores
        pass

    def _finish_ui(self):
        btn_exit = Gtk.Button.new_with_label("Salir")
        btn_exit.connect("clicked", lambda b: Gtk.main_quit())
        self.bottom_box.pack_end(btn_exit, False, False, 0)

        btn_about = Gtk.Button.new_with_label("Acerca de")
        btn_about.connect("clicked", self.on_about)
        self.bottom_box.pack_end(btn_about, False, False, 0)

        self.main_box.pack_start(self.bottom_box, False, False, 0)

        self.show_all()

    def _create_icon_button(self, icon_name, tooltip_text, fallback_label,
                            callback, callback_arg):
        """Crea un botón con ícono, con fallback a texto si el ícono no existe."""
        icon_theme = Gtk.IconTheme.get_default()
        btn = Gtk.Button()
        btn.set_relief(Gtk.ReliefStyle.NONE)
        btn.set_tooltip_text(tooltip_text)
        if icon_theme and icon_theme.has_icon(icon_name):
            img = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.BUTTON)
            btn.set_image(img)
        else:
            lbl = Gtk.Label(label=fallback_label)
            btn.add(lbl)
        if callback is not None:
            btn.connect("clicked", callback, callback_arg)
        return btn

    def on_add_task(self, widget=None):
        title = self.entry_title.get_text().strip()
        if not title:
            dialog = Gtk.MessageDialog(
                transient_for=self, flags=0,
                message_type=Gtk.MessageType.WARNING,
                buttons=Gtk.ButtonsType.OK,
                text="Título requerido",
            )
            dialog.format_secondary_text("Por favor, ingresa un título para la tarea.")
            dialog.run()
            dialog.destroy()
            return

        due = self.entry_due.get_text().strip()
        if due:
            try:
                datetime.strptime(due, "%Y-%m-%d")
            except ValueError:
                dialog = Gtk.MessageDialog(
                    transient_for=self, flags=0,
                    message_type=Gtk.MessageType.ERROR,
                    buttons=Gtk.ButtonsType.OK,
                    text="Fecha inválida",
                )
                dialog.format_secondary_text("Usa el formato YYYY-MM-DD.")
                dialog.run()
                dialog.destroy()
                return

        task = Task(
            title=title,
            description=self.entry_desc.get_text().strip(),
            priority=self.combo_priority.get_active_text() or "Media",
            due_date=due if due else None,
        )
        self.tasks.append(task)
        self.save_tasks()
        self.refresh_task_list()

        self.entry_title.set_text("")
        self.entry_desc.set_text("")
        self.combo_priority.set_active(1)
        self.entry_due.set_text("")
        self.entry_title.grab_focus()

    def on_task_toggled(self, check_button, task):
        task.completed = check_button.get_active()
        self.save_tasks()
        self.refresh_task_list()

    def on_task_delete(self, button, task):
        dialog = Gtk.MessageDialog(
            transient_for=self, flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text="Eliminar tarea",
        )
        dialog.format_secondary_text(f"¿Eliminar '{task.title}'?")
        response = dialog.run()
        dialog.destroy()

        if response == Gtk.ResponseType.YES:
            self.tasks = [t for t in self.tasks if t is not task]
            self.save_tasks()
            self.refresh_task_list()

    def on_task_edit(self, button, task):
        dialog = Gtk.Dialog(title="Editar tarea", transient_for=self, flags=0)
        dialog.add_button("Cancelar", Gtk.ResponseType.CANCEL)
        dialog.add_button("Guardar", Gtk.ResponseType.OK)
        dialog.set_default_size(450, 300)

        content = dialog.get_content_area()
        content.set_spacing(6)
        content.set_border_width(12)

        # Título
        box_title = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lbl_title = Gtk.Label(label="Título: ")
        lbl_title.set_xalign(0)
        entry_title = Gtk.Entry()
        entry_title.set_text(task.title)
        entry_title.set_hexpand(True)
        box_title.pack_start(lbl_title, False, False, 0)
        box_title.pack_start(entry_title, True, True, 0)
        content.pack_start(box_title, False, False, 0)

        # Descripción
        box_desc = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lbl_desc = Gtk.Label(label="Descripción: ")
        lbl_desc.set_xalign(0)
        entry_desc = Gtk.Entry()
        entry_desc.set_text(task.description if task.description else "")
        entry_desc.set_hexpand(True)
        box_desc.pack_start(lbl_desc, False, False, 0)
        box_desc.pack_start(entry_desc, True, True, 0)
        content.pack_start(box_desc, False, False, 0)

        # Prioridad
        box_pri = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lbl_pri = Gtk.Label(label="Prioridad: ")
        lbl_pri.set_xalign(0)
        combo_pri = Gtk.ComboBoxText()
        for p in self.PRIORITIES:
            combo_pri.append_text(p)
        if task.priority in self.PRIORITIES:
            combo_pri.set_active(self.PRIORITIES.index(task.priority))
        else:
            combo_pri.set_active(1)
        combo_pri.set_hexpand(True)
        box_pri.pack_start(lbl_pri, False, False, 0)
        box_pri.pack_start(combo_pri, True, True, 0)
        content.pack_start(box_pri, False, False, 0)

        # Fecha de vencimiento
        box_due = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lbl_due = Gtk.Label(label="Vencimiento: ")
        lbl_due.set_xalign(0)
        entry_due = Gtk.Entry()
        entry_due.set_placeholder_text("YYYY-MM-DD (opcional)")
        entry_due.set_text(task.due_date if task.due_date else "")
        entry_due.set_hexpand(True)
        box_due.pack_start(lbl_due, False, False, 0)
        box_due.pack_start(entry_due, True, True, 0)
        content.pack_start(box_due, False, False, 0)

        dialog.show_all()

        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            new_title = entry_title.get_text().strip()
            if not new_title:
                err = Gtk.MessageDialog(
                    transient_for=self, flags=0,
                    message_type=Gtk.MessageType.WARNING,
                    buttons=Gtk.ButtonsType.OK,
                    text="Título requerido",
                )
                err.format_secondary_text("El título no puede estar vacío.")
                err.run()
                err.destroy()
                dialog.destroy()
                return

            new_due = entry_due.get_text().strip()
            if new_due:
                try:
                    datetime.strptime(new_due, "%Y-%m-%d")
                except ValueError:
                    err = Gtk.MessageDialog(
                        transient_for=self, flags=0,
                        message_type=Gtk.MessageType.ERROR,
                        buttons=Gtk.ButtonsType.OK,
                        text="Fecha inválida",
                    )
                    err.format_secondary_text("Usa el formato YYYY-MM-DD.")
                    err.run()
                    err.destroy()
                    dialog.destroy()
                    return

            # Actualizar la tarea
            task.title = new_title
            task.description = entry_desc.get_text().strip()
            task.priority = combo_pri.get_active_text() or "Media"
            task.due_date = new_due if new_due else None

            self.save_tasks()
            self.refresh_task_list()

        dialog.destroy()

    def on_clear_completed(self, button):
        completed = [t for t in self.tasks if t.completed]
        if not completed:
            return
        dialog = Gtk.MessageDialog(
            transient_for=self, flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text="Limpiar tareas completadas",
        )
        dialog.format_secondary_text(f"Se eliminarán {len(completed)} tarea(s). ¿Continuar?")
        response = dialog.run()
        dialog.destroy()
        if response == Gtk.ResponseType.YES:
            self.tasks = [t for t in self.tasks if not t.completed]
            self.save_tasks()
            self.refresh_task_list()

    def _set_filter_button_active(self, active_button):
        """Marca visualmente el botón de filtro activo y desactiva los demás."""
        for b in (self.btn_filter_all, self.btn_filter_active, self.btn_filter_completed):
            if b is active_button:
                b.set_property("sensitive", False)
                b.get_style_context().add_class("active-filter")
            else:
                b.set_property("sensitive", True)
                b.get_style_context().remove_class("active-filter")

    def on_filter_clicked(self, button, label):
        self.filter_mode = label
        self._set_filter_button_active(button)
        self.refresh_task_list()

    def _update_stats(self):
        total = len(self.tasks)
        pendientes = sum(1 for t in self.tasks if not t.completed)
        completadas = total - pendientes
        self.lbl_stats.set_text(
            f"{total} tarea(s)  |  {pendientes} pendiente(s), {completadas} completada(s)"
        )

    def on_about(self, button):
        dialog = Gtk.AboutDialog()
        dialog.set_transient_for(self)
        dialog.set_title("Acerca de To Do List")
        dialog.set_program_name("To Do List")
        dialog.set_version("1.0")
        dialog.set_copyright(
            "Copyright © 2026 - Jesús A. Vásquez-Córdova"  # TODO: Reemplaza con tu nombre real (I DID IT)
        )
        dialog.set_comments(
            "Aplicación de lista de tareas para Debian 13 con entorno XFCE."
        )
        # TODO: Reemplaza con tus datos reales (I DID IT)
        dialog.set_authors(["Jesús A. Vásquez-Córdova <jesusavc@gmail.com> (Mexicali, México)"])
        dialog.set_website("https://jesusavc.com")
        dialog.set_website_label("Sitio web del autor")
        dialog.set_license_type(Gtk.License.MIT_X11)
        dialog.set_icon_name("appointment-new")
        dialog.run()
        dialog.destroy()

def main():
    css_provider = Gtk.CssProvider()
    css = """
    .task-title { font-weight: bold; font-size: 1.05em; }
    .task-title.completed { text-decoration: line-through; color: #888; }
    .task-desc { font-size: 0.9em; color: #555; }
    .task-meta { font-size: 0.85em; color: #777; }
    .active-filter { font-weight: bold; color: #0066cc; }
    """
    css_provider.load_from_data(css.encode("utf-8"))
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(),
        css_provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
    )

    app = TodoWindow()
    app.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()

