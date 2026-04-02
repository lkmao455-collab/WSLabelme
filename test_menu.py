import sys
from PyQt5 import QtWidgets, QtCore

class TestWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Test Menu")
        
        # Create menu bar
        menubar = self.menuBar()
        
        # Create Edit menu
        edit_menu = menubar.addMenu("&Edit")
        
        # Add actions similar to labelme
        create_polygon = QtWidgets.QAction("Create Polygon", self)
        create_polygon.setEnabled(False)  # Initially disabled
        edit_menu.addAction(create_polygon)
        
        edit_action = QtWidgets.QAction("Edit", self)
        edit_action.setEnabled(False)
        edit_menu.addAction(edit_action)
        
        duplicate = QtWidgets.QAction("Duplicate", self)
        duplicate.setEnabled(False)
        edit_menu.addAction(duplicate)
        
        copy = QtWidgets.QAction("Copy", self)
        copy.setEnabled(False)
        edit_menu.addAction(copy)
        
        paste = QtWidgets.QAction("Paste", self)
        paste.setEnabled(True)  # This one is enabled
        edit_menu.addAction(paste)
        
        # Add a separator
        edit_menu.addSeparator()
        
        undo = QtWidgets.QAction("Undo", self)
        undo.setEnabled(False)
        edit_menu.addAction(undo)
        
        self.show()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = TestWindow()
    sys.exit(app.exec_())