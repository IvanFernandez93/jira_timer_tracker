import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPixmap, QPainter, QColor, QPen, QBrush, QFont
from PyQt6.QtCore import Qt, QRect

def create_additional_icons():
    """Create additional icons for common UI elements"""
    app = QApplication([])
    
    icons_dir = "resources/icons"
    
    def create_icon(name, size=24):
        pix = QPixmap(size, size)
        pix.fill(QColor(0, 0, 0, 0))
        
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        pen = QPen(QColor(64, 64, 64), 2)
        painter.setPen(pen)
        
        margin = 3
        rect = QRect(margin, margin, size - 2*margin, size - 2*margin)
        
        if name == 'plus':
            # Draw plus sign
            center_x = rect.x() + rect.width()//2
            center_y = rect.y() + rect.height()//2
            painter.drawLine(center_x, rect.y() + 2, center_x, rect.y() + rect.height() - 2)
            painter.drawLine(rect.x() + 2, center_y, rect.x() + rect.width() - 2, center_y)
            
        elif name == 'minus':
            # Draw minus sign
            center_y = rect.y() + rect.height()//2
            painter.drawLine(rect.x() + 2, center_y, rect.x() + rect.width() - 2, center_y)
            
        elif name == 'close':
            # Draw X
            painter.drawLine(rect.x() + 2, rect.y() + 2, 
                           rect.x() + rect.width() - 2, rect.y() + rect.height() - 2)
            painter.drawLine(rect.x() + rect.width() - 2, rect.y() + 2,
                           rect.x() + 2, rect.y() + rect.height() - 2)
            
        elif name == 'check':
            # Draw checkmark
            painter.setPen(QPen(QColor(0, 150, 0), 2))
            painter.drawLine(rect.x() + 3, rect.y() + rect.height()//2,
                           rect.x() + rect.width()//2, rect.y() + rect.height() - 4)
            painter.drawLine(rect.x() + rect.width()//2, rect.y() + rect.height() - 4,
                           rect.x() + rect.width() - 3, rect.y() + 3)
                           
        elif name == 'play':
            # Draw play triangle
            painter.setBrush(QBrush(QColor(0, 150, 0)))
            painter.drawPolygon([
                rect.x() + 4, rect.y() + 2,
                rect.x() + 4, rect.y() + rect.height() - 2,
                rect.x() + rect.width() - 2, rect.y() + rect.height()//2
            ])
            
        elif name == 'pause':
            # Draw pause bars
            painter.setBrush(QBrush(QColor(150, 150, 0)))
            bar_width = rect.width()//4
            painter.drawRect(rect.x() + 2, rect.y() + 2, bar_width, rect.height() - 4)
            painter.drawRect(rect.x() + rect.width() - bar_width - 2, rect.y() + 2, 
                           bar_width, rect.height() - 4)
                           
        elif name == 'sync':
            # Draw circular arrows
            painter.drawArc(rect.x() + 2, rect.y() + 2, rect.width() - 4, rect.height() - 4, 
                          45 * 16, 270 * 16)
            # Arrow heads
            painter.drawLine(rect.x() + rect.width() - 4, rect.y() + 4,
                           rect.x() + rect.width() - 2, rect.y() + 2)
            painter.drawLine(rect.x() + rect.width() - 4, rect.y() + 4,
                           rect.x() + rect.width() - 6, rect.y() + 6)
            
        elif name == 'grid':
            # Draw grid
            step = rect.width() // 3
            for i in range(1, 3):
                painter.drawLine(rect.x() + i * step, rect.y(), 
                               rect.x() + i * step, rect.y() + rect.height())
                painter.drawLine(rect.x(), rect.y() + i * step,
                               rect.x() + rect.width(), rect.y() + i * step)
                               
        elif name == 'document':
            # Draw document
            painter.setBrush(QBrush(QColor(255, 255, 255)))
            painter.drawRect(rect.x() + 2, rect.y() + 2, rect.width() - 6, rect.height() - 4)
            # Folded corner
            corner_size = 4
            painter.drawLine(rect.x() + rect.width() - corner_size - 2, rect.y() + 2,
                           rect.x() + rect.width() - 2, rect.y() + corner_size + 2)
            
        else:
            # Default fallback
            painter.setBrush(QBrush(QColor(200, 200, 255)))
            painter.drawRoundedRect(rect, 3, 3)
            painter.setPen(QPen(QColor(0, 0, 0)))
            font = QFont()
            font.setPointSize(10)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, name[0].upper() if name else '?')
        
        painter.end()
        return pix
    
    # Create additional icons
    additional_icons = ['plus', 'minus', 'close', 'check', 'play', 'pause', 'sync', 'grid', 'document']
    
    for icon_name in additional_icons:
        pix = create_icon(icon_name)
        file_path = os.path.join(icons_dir, f"{icon_name}.png")
        success = pix.save(file_path, "PNG")
        print(f"Created {icon_name}.png: {'Success' if success else 'Failed'}")
    
    print(f"Created {len(additional_icons)} additional icon files")

if __name__ == "__main__":
    create_additional_icons()