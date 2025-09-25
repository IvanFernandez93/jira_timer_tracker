# Simple icon creator script (run manually when needed)
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPixmap, QPainter, QColor, QPen, QBrush, QFont
from PyQt6.QtCore import Qt, QRect

def create_icon(name, size=24):
    """Create a simple icon pixmap with proper transparency"""
    # Create pixmap with alpha channel for transparency
    pix = QPixmap(size, size)
    pix.fill(QColor(0, 0, 0, 0))  # Completely transparent background
    
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    
    # Use darker colors for better visibility on any background
    pen = QPen(QColor(40, 40, 40), 2)
    painter.setPen(pen)
    
    margin = 2
    rect = QRect(margin, margin, size - 2*margin, size - 2*margin)
    
    if name == 'brush':
        # Draw a simple brush icon with better contrast
        handle_color = QColor(139, 69, 19)  # Brown handle
        brush_color = QColor(0, 100, 0)     # Green brush
        
        painter.setPen(QPen(handle_color, 2))
        painter.setBrush(QBrush(handle_color))
        # Handle
        painter.drawRect(rect.x() + rect.width()//2 - 1, rect.y() + rect.height()//2, 
                        2, rect.height()//2)
        
        painter.setPen(QPen(brush_color, 3))
        painter.setBrush(QBrush(brush_color))
        # Brush head
        painter.drawEllipse(rect.x() + rect.width()//2 - 3, rect.y() + 2, 6, 6)
        # Bristles
        for i in range(3):
            x = rect.x() + rect.width()//2 - 1 + i - 1
            painter.drawLine(x, rect.y() + 8, x, rect.y() + rect.height()//2 - 1)
    
    elif name == 'checkbox':
        # Draw a checkbox with transparent background
        painter.setPen(QPen(QColor(0, 0, 0), 2))
        painter.setBrush(QBrush(QColor(255, 255, 255, 0)))  # Transparent fill
        painter.drawRect(rect.adjusted(2, 2, -2, -2))
        
        # Draw checkmark in green
        painter.setPen(QPen(QColor(0, 150, 0), 2))
        check_rect = rect.adjusted(4, 4, -4, -4)
        painter.drawLine(check_rect.x(), check_rect.y() + check_rect.height()//2,
                        check_rect.x() + check_rect.width()//3, 
                        check_rect.y() + check_rect.height() - 2)
        painter.drawLine(check_rect.x() + check_rect.width()//3, 
                        check_rect.y() + check_rect.height() - 2,
                        check_rect.x() + check_rect.width(), check_rect.y() + 2)
    
    elif name == 'edit':
        # Draw a pencil with better detail
        painter.setPen(QPen(QColor(255, 165, 0), 3))  # Orange pencil
        painter.drawLine(rect.x() + 2, rect.y() + rect.height() - 2,
                        rect.x() + rect.width() - 2, rect.y() + 2)
        
        # Pencil tip
        painter.setPen(QPen(QColor(0, 0, 0), 2))
        painter.drawLine(rect.x() + rect.width() - 4, rect.y(),
                        rect.x() + rect.width(), rect.y() + 4)
        
        # Eraser
        painter.setPen(QPen(QColor(255, 192, 203), 2))  # Pink eraser
        painter.drawLine(rect.x(), rect.y() + rect.height() - 4,
                        rect.x() + 4, rect.y() + rect.height())
    
    elif name == 'delete':
        # Draw a trash can with better visibility
        painter.setPen(QPen(QColor(200, 0, 0), 2))  # Red for delete
        painter.setBrush(QBrush(QColor(0, 0, 0, 0)))  # Transparent fill
        
        # Trash can body
        can_rect = rect.adjusted(3, 5, -3, -2)
        painter.drawRect(can_rect)
        
        # Lid
        lid_rect = QRect(rect.x() + 1, rect.y() + 4, rect.width() - 2, 2)
        painter.setBrush(QBrush(QColor(200, 0, 0)))
        painter.drawRect(lid_rect)
        
        # Handle
        handle_rect = QRect(rect.x() + rect.width()//2 - 2, rect.y() + 2, 4, 2)
        painter.drawRect(handle_rect)
        
        # Vertical lines inside
        for i in range(2):
            x = can_rect.x() + 2 + i * 3
            painter.drawLine(x, can_rect.y() + 2, x, can_rect.y() + can_rect.height() - 2)
    
    elif name == 'folder':
        # Draw a folder with yellow color
        painter.setPen(QPen(QColor(184, 134, 11), 2))  # Dark yellow border
        painter.setBrush(QBrush(QColor(255, 193, 7, 180)))  # Semi-transparent yellow
        
        # Main folder body
        folder_rect = rect.adjusted(1, 4, -1, -1)
        painter.drawRect(folder_rect)
        
        # Folder tab
        tab_rect = QRect(rect.x() + 1, rect.y() + 2, rect.width()//2, 4)
        painter.drawRect(tab_rect)
    
    elif name == 'history':
        # Draw a clock with better details
        painter.setPen(QPen(QColor(0, 0, 0), 2))
        painter.setBrush(QBrush(QColor(255, 255, 255, 180)))  # White face
        
        # Clock face
        clock_rect = rect.adjusted(1, 1, -1, -1)
        painter.drawEllipse(clock_rect)
        
        # Clock hands
        center_x = rect.x() + rect.width()//2
        center_y = rect.y() + rect.height()//2
        
        # Hour hand (pointing to 3)
        painter.setPen(QPen(QColor(0, 0, 0), 2))
        painter.drawLine(center_x, center_y, 
                        center_x + rect.width()//4, center_y)
        
        # Minute hand (pointing to 12)
        painter.drawLine(center_x, center_y, 
                        center_x, rect.y() + 3)
        
        # Center dot
        painter.setBrush(QBrush(QColor(0, 0, 0)))
        painter.drawEllipse(center_x - 1, center_y - 1, 2, 2)
    
    elif name == 'search':
        # Draw a magnifying glass
        painter.setPen(QPen(QColor(0, 100, 200), 2))
        painter.setBrush(QBrush(QColor(0, 0, 0, 0)))  # Transparent
        
        # Lens
        lens_size = rect.width() - 6
        painter.drawEllipse(rect.x() + 2, rect.y() + 2, lens_size, lens_size)
        
        # Handle
        handle_start_x = rect.x() + lens_size - 1
        handle_start_y = rect.y() + lens_size - 1
        painter.drawLine(handle_start_x, handle_start_y,
                        rect.x() + rect.width() - 2, rect.y() + rect.height() - 2)
    
    elif name == 'setting':
        # Draw a gear/cog
        painter.setPen(QPen(QColor(100, 100, 100), 2))
        painter.setBrush(QBrush(QColor(150, 150, 150, 180)))
        
        # Outer gear teeth (simplified as octagon)
        center_x = rect.x() + rect.width()//2
        center_y = rect.y() + rect.height()//2
        gear_radius = rect.width()//2 - 2
        
        # Draw simplified gear as circle with notches
        painter.drawEllipse(center_x - gear_radius, center_y - gear_radius, 
                          gear_radius * 2, gear_radius * 2)
        
        # Inner hole
        inner_radius = gear_radius // 3
        painter.setBrush(QBrush(QColor(0, 0, 0, 0)))  # Transparent center
        painter.drawEllipse(center_x - inner_radius, center_y - inner_radius,
                          inner_radius * 2, inner_radius * 2)
        
        # Gear teeth (4 simple lines)
        painter.setPen(QPen(QColor(100, 100, 100), 1))
        for i in range(4):
            angle = i * 90
            if angle == 0:  # Right
                painter.drawLine(center_x + gear_radius, center_y - 2,
                               center_x + gear_radius + 2, center_y - 2)
                painter.drawLine(center_x + gear_radius, center_y + 2,
                               center_x + gear_radius + 2, center_y + 2)
            elif angle == 90:  # Bottom
                painter.drawLine(center_x - 2, center_y + gear_radius,
                               center_x - 2, center_y + gear_radius + 2)
                painter.drawLine(center_x + 2, center_y + gear_radius,
                               center_x + 2, center_y + gear_radius + 2)
            elif angle == 180:  # Left
                painter.drawLine(center_x - gear_radius, center_y - 2,
                               center_x - gear_radius - 2, center_y - 2)
                painter.drawLine(center_x - gear_radius, center_y + 2,
                               center_x - gear_radius - 2, center_y + 2)
            elif angle == 270:  # Top
                painter.drawLine(center_x - 2, center_y - gear_radius,
                               center_x - 2, center_y - gear_radius - 2)
                painter.drawLine(center_x + 2, center_y - gear_radius,
                               center_x + 2, center_y - gear_radius - 2)
    
    else:
        # Default: draw letter with better contrast
        painter.setBrush(QBrush(QColor(200, 200, 255, 180)))
        painter.setPen(QPen(QColor(0, 0, 0), 1))
        painter.drawRoundedRect(rect, 3, 3)
        
        painter.setPen(QPen(QColor(0, 0, 0)))
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, name[0].upper() if name else '?')
    
    painter.end()
    return pix

if __name__ == "__main__":
    app = QApplication([])
    
    # Create icons directory and save common icons
    icons_dir = "resources/icons"
    os.makedirs(icons_dir, exist_ok=True)
    
    icons_to_create = ['brush', 'checkbox', 'edit', 'delete', 'folder', 'history', 'search', 'setting']
    
    for icon_name in icons_to_create:
        pix = create_icon(icon_name)
        file_path = os.path.join(icons_dir, f"{icon_name}.png")
        success = pix.save(file_path, "PNG")
        print(f"Created {icon_name}.png: {'Success' if success else 'Failed'}")
    
    print(f"Created {len(icons_to_create)} icon files in {icons_dir}")