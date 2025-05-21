# app/widgets/config_bar.py

from PyQt6.QtWidgets import QWidget, QFormLayout, QSlider, QLabel
from PyQt6.QtCore import Qt

class ConfigBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ConfigBar")
        self._init_ui()

    def _init_ui(self):
        layout = QFormLayout(self)

        self.top_p_slider = QSlider(Qt.Orientation.Horizontal)
        self.top_p_slider.setObjectName("TopPSlider")
        self.top_p_slider.setMinimum(1)  # 对应 0.01
        self.top_p_slider.setMaximum(100) # 对应 1.0
        self.top_p_slider.setValue(70) # 默认 0.7
        self.top_p_slider.setTickInterval(10)
        self.top_p_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        
        self.top_p_label = QLabel(f"Top P: {self.top_p_slider.value() / 100:.2f}")
        self.top_p_label.setObjectName("TopPLabel")
        self.top_p_slider.valueChanged.connect(lambda value: self.top_p_label.setText(f"Top P: {value / 100:.2f}"))
        
        layout.addRow(self.top_p_label, self.top_p_slider)
        self.setLayout(layout)

    def get_top_p_value(self) -> float:
        return self.top_p_slider.value() / 100.0