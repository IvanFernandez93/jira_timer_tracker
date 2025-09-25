#!/usr/bin/env python3
"""
Simple icon creator with transparent backgrounds
"""
import os
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPixmap, QPainter, QColor, QPen, QBrush, QFont
from PyQt6.QtCore import Qt, QRect

def create_transparent_icon(name, size=24):
    """Create icon with proper transparent background"""
    # Create pixmap with alpha channel
    pix = QPixmap(size, size)
    pix.fill(QColor(0, 0, 0, 0))  # Fully transparent
    
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    # Use solid colors with good contrast
    rect = QRect(2, 2, size-4, size-4)
    
    if name == 'brush':
        # Simple brush - brown handle, green bristles
        painter.setPen(QPen(QColor(139, 69, 19), 3))
        painter.drawLine(rect.center().x(), rect.y(), rect.center().x(), rect.bottom())
        painter.setPen(QPen(QColor(0, 128, 0), 2))
        painter.drawEllipse(rect.center().x()-3, rect.y()-1, 6, 6)
        
    elif name == 'checkbox':
        # Checkbox with green check
        painter.setPen(QPen(QColor(0, 0, 0), 2))
        painter.drawRect(rect)
        painter.setPen(QPen(QColor(0, 128, 0), 2))
        # Simple checkmark
        painter.drawLine(rect.x()+3, rect.center().y(), 
                        rect.center().x(), rect.bottom()-3)
        painter.drawLine(rect.center().x(), rect.bottom()-3,
                        rect.right()-3, rect.y()+3)
        
    elif name == 'edit':
        # Simple pencil
        painter.setPen(QPen(QColor(255, 140, 0), 3))
        painter.drawLine(rect.x()+2, rect.bottom()-2, rect.right()-2, rect.y()+2)
        painter.setPen(QPen(QColor(0, 0, 0), 2))
        painter.drawLine(rect.right()-3, rect.y(), rect.right(), rect.y()+3)
        
    elif name == 'delete':
        # Red trash can
        painter.setPen(QPen(QColor(220, 20, 60), 2))
        painter.drawRect(rect.x()+2, rect.y()+4, rect.width()-4, rect.height()-6)
        painter.drawLine(rect.x(), rect.y()+4, rect.right(), rect.y()+4)
        painter.drawRect(rect.center().x()-2, rect.y()+2, 4, 2)
        
    elif name == 'folder':
        # Yellow folder
        painter.setPen(QPen(QColor(218, 165, 32), 2))
        painter.setBrush(QBrush(QColor(255, 215, 0, 150)))
        painter.drawRect(rect.x(), rect.y()+4, rect.width(), rect.height()-4)
        painter.drawRect(rect.x(), rect.y()+2, rect.width()//2, 4)
        
    elif name == 'history':
        # Clock
        painter.setPen(QPen(QColor(0, 0, 0), 2))
        painter.drawEllipse(rect)
        center = rect.center()
        painter.drawLine(center.x(), center.y(), center.x(), rect.y()+4)
        painter.drawLine(center.x(), center.y(), center.x()+6, center.y())
        
    elif name == 'search':
        # Magnifying glass
        painter.setPen(QPen(QColor(0, 100, 200), 2))
        glass_rect = QRect(rect.x()+1, rect.y()+1, rect.width()-6, rect.height()-6)
        painter.drawEllipse(glass_rect)
        painter.drawLine(glass_rect.right()-2, glass_rect.bottom()-2,
                        rect.right()-1, rect.bottom()-1)
        
    elif name == 'setting':
        # Simple gear
        painter.setPen(QPen(QColor(105, 105, 105), 2))
        painter.drawEllipse(rect)
        # Inner circle
        inner = QRect(rect.center().x()-4, rect.center().y()-4, 8, 8)
        painter.drawEllipse(inner)
        
    else:
        # Default letter
        painter.setPen(QPen(QColor(0, 0, 0), 2))
        painter.setBrush(QBrush(QColor(220, 220, 255, 150)))
        painter.drawRoundedRect(rect, 3, 3)
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QPen(QColor(0, 0, 0)))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, name[0].upper() if name else '?')
    
    painter.end()
    return pix

def main():
    print("Creating transparent icons...")
    app = QApplication(sys.argv if __name__ == "__main__" else [])
    
    # Ensure directory exists
    icons_dir = "resources/icons"
    os.makedirs(icons_dir, exist_ok=True)
    
    # Create improved icons
    icons = ['brush', 'checkbox', 'edit', 'delete', 'folder', 'history', 'search', 'setting']
    
    for icon_name in icons:
        try:
            pix = create_transparent_icon(icon_name)
            file_path = os.path.join(icons_dir, f"{icon_name}.png")
            
            # Save with explicit format for transparency
            success = pix.save(file_path, "PNG")
            print(f"{'✓' if success else '✗'} {icon_name}.png")
            
        except Exception as e:
            print(f"✗ {icon_name}.png - Error: {e}")
    
    print(f"Icon creation complete. Check {icons_dir} directory.")
    return True

if __name__ == "__main__":
    main()