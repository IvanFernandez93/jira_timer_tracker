from PyQt6.QtWidgets import QApplication
from views.main_window import MainWindow

app = QApplication([])

w = MainWindow()

# Show the window so widgets get laid out and painted; process events
# to allow geometry to settle before inspection.
w.show()
app.processEvents()


def describe(widget):
    try:
        name = widget.objectName() or '<no name>'
    except Exception:
        name = '<no name>'
    try:
        cls = type(widget).__name__
    except Exception:
        cls = '<no type>'
    try:
        geom = widget.geometry()
        geom_s = f'{geom.x()},{geom.y()} {geom.width()}x{geom.height()}'
    except Exception:
        geom_s = '<no geometry>'
    try:
        vis = widget.isVisible()
    except Exception:
        vis = '<no visible>'
    try:
        style = widget.styleSheet()
    except Exception:
        style = '<no stylesheet>'
    try:
        parent = widget.parent()
        parent_name = parent.objectName() if parent else '<no parent>'
    except Exception:
        parent_name = '<no parent>'
    return dict(name=name, type=cls, geometry=geom_s, visible=vis, stylesheet=style, parent=parent_name)

items_to_check = []

# titleBar
try:
    tb = w.titleBar
    items_to_check.append(('titleBar', tb))
except Exception:
    pass

# nav rail
try:
    nav = w._nav_rail
    items_to_check.append(('_nav_rail', nav))
except Exception:
    pass

# nav rail children
try:
    if hasattr(w, '_nav_layout') and w._nav_layout is not None:
        for i in range(w._nav_layout.count()):
            it = w._nav_layout.itemAt(i)
            widget = it.widget()
            if widget:
                items_to_check.append((f'_nav_child_{i}', widget))
            else:
                items_to_check.append((f'_nav_child_{i}', it))
except Exception:
    pass

# stacked
try:
    st = w._stacked
    items_to_check.append(('_stacked', st))
    try:
        for idx in range(st.count()):
            pg = st.widget(idx)
            items_to_check.append((f'stack_page_{idx}', pg))
    except Exception:
        pass
except Exception:
    pass

print('--- Widget diagnostics ---')
for label, obj in items_to_check:
    print('\n==', label)
    if hasattr(obj, 'widget') and not hasattr(obj, 'geometry'):
        # it's a layout item
        try:
            print('layout item:', obj)
        except Exception:
            pass
        continue
    try:
        d = describe(obj)
        for k, v in d.items():
            print(f'{k}: {v}')
    except Exception as e:
        print('error describing:', e)

# Also list nav item texts
nav = getattr(w, 'navigationInterface', None)
if nav:
    print('\n-- navigationInterface items --')
    for i, btn in enumerate(getattr(nav, 'items', [])):
        try:
            print(i, btn.objectName(), btn.text(), 'visible=', btn.isVisible())
        except Exception:
            print(i, '<error reading button>')

app.quit()
