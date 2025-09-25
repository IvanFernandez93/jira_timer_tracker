from PyQt6.QtWidgets import QApplication
from views.main_window import MainWindow

app = QApplication([])

w = MainWindow()

nav = getattr(w, 'navigationInterface', None)
if nav is None:
    print('navigationInterface is None')
else:
    items = getattr(nav, 'items', [])
    print('nav_items_count:', len(items))
    for i, btn in enumerate(items):
        try:
            name = btn.objectName()
        except Exception:
            name = '<no objectName>'
        try:
            text = btn.text()
        except Exception:
            text = '<no text>'
        print(f'item {i}: objectName="{name}", text="{text}"')

stacked = getattr(w, '_stacked', None)
if stacked is None:
    print('_stacked is None')
else:
    print('_stacked_count:', stacked.count())
    for idx in range(stacked.count()):
        pg = stacked.widget(idx)
        try:
            oname = pg.objectName()
        except Exception:
            oname = '<no objname>'
        print(f'stack page {idx}: objectName="{oname}", type={type(pg).__name__}')

app.quit()
