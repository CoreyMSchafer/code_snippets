import sys, random, time, datetime
import numpy as np
from matplotlib.backends.qt_compat import QtWidgets
from matplotlib.backends.backend_qt5agg import (
    FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
from PyQt5.QtWidgets import *
from PyQt5 import QtCore, QtWidgets
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.figure import Figure
from matplotlib.animation import FuncAnimation
from threading import *

# Create List Variables to store Random GPS and Temperature values
gps_list = []
gps_n_list = [] # Nested list for gps values check it by print statement while running
temp_list = []
delay = 1 # delay for data generation

# Class for Data Generation
class dataGeneration:
    # Method for generating random temperature data
    def tempSenor(self):
        global temp, temp_array
        while True:
            QApplication.processEvents()
            temp = random.randint(5, 50)
            temp_list.append(temp)
            temp_array = np.array(temp_list)
            time.sleep(delay)

    # Method for generating random GPS data
    def input_gps(self):
        global gps_n_list, Current_DateTime, lat, long
        while True:
            QApplication.processEvents()
            long = random.randint(7585707193, 7585898276)
            long = long/100000000
            lat = random.randint(3086340228, 3086405821)
            lat = lat/100000000
            gps_list.append(long)
            gps_list.append(lat)
            length = 0
            # Logic for generating nested list for lat long data i.e., gps_n_list
            while length < len(gps_list):
                gps_n_list.append(gps_list[length:length + 2])
                length += 2
            #  Logic for live date with time update
            dt = datetime.datetime.now()
            Current_DateTime = dt.strftime('%d-%b-%Y & %H:%M:%S')
            time.sleep(delay)

# Class for GUI design and implementation
class ApplicationWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Location based Temperature sensor Project ')
        self.resize(800, 480)

        #  Create Layout to insert things
        layout = QGridLayout()
        layout.setSpacing(10)

        self._main = QtWidgets.QWidget()
        self.setCentralWidget(self._main)
        layout = QGridLayout(self._main)

        # Create labels to show update data
        self.t1 = QLabel(self)
        self.t1.setStyleSheet("background-color: rgb(82, 119, 152);\n"
                              "font: 75 10pt \"MS Shell Dlg 2\";\n"
                              "color: rgb(255, 255, 255);")
        self.t1.setText("Easting")
        layout.addWidget(self.t1, 0, 0)

        self.t2 = QLabel(self)
        self.t2.setStyleSheet("background-color: rgb(82, 119, 152);\n"
                              "font: 75 10pt \"MS Shell Dlg 2\";\n"
                              "color: rgb(255, 255, 255);")
        self.t2.setText("Northing")
        layout.addWidget(self.t2, 0, 1)

        self.t3 = QLabel(self)
        self.t3.setStyleSheet("background-color: rgb(65, 184, 57);\n"
                              "color: rgb(255, 255, 255);\n"
                              "font: 75 10pt \"MS Shell Dlg 2\";")
        self.t3.setText("Temperature")
        layout.addWidget(self.t3, 0, 2)

        self.t4 = QLabel(self)
        self.t4.setStyleSheet("background-color: rgb(255, 150, 97);\n"
                              "font: 75 10pt \"MS Shell Dlg 2\";\n"
                              "color: rgb(255, 255, 255);")
        self.t4.setText("Current Time:")
        layout.addWidget(self.t4, 0, 3)

        self.setLayout(layout)

        #  Function to continuously update data in gui window
        def update_data():
            self.t1.setText(" Long: " + str(long))
            self.t2.setText(" Lat: " + str(lat))
            self.t3.setText(" Temp: " + str(temp))
            self.t4.setText(" " + str(Current_DateTime))

        #  Timer to continuously call update_data() function
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(update_data)
        self.timer.start(500)

        self.fig = Figure(figsize=(12, 9)) # declare size of figure

        self.canvas = FigureCanvas(self.fig) # Canvas for figure to insert in main gui window
        layout.addWidget(self.canvas, 2, 0, 1, 4)

        self.Toolbar = NavigationToolbar(self.canvas, self) # Toolbar for figure to insert in main gui window
        layout.addWidget(self.Toolbar, 3, 1, 1, 4)

        self.setup()

    def setup(self):
        self.ax = self.fig.subplots()
        self.ax.set_aspect('auto')
        self.ax.grid(True, linestyle='dotted', color='0.50')
        self.ax.set_xlim([75.85707180, 75.85898300])
        self.ax.set_ylim([30.86340200, 30.86405850])

        self.ax.set_xlabel('Longitude')
        self.ax.set_ylabel('Latitude')
        self.ax.set_title('GPS - Temperature Live Plot')
        colors = [(0, "lightgray"), (0.1, "lightgray"), (0.18, "lightgray"), (0.30, "red"),
                  (0.38, "yellow"), (0.48, "lightgreen"), (0.58, "lime"), (0.63, "limegreen"),
                  (0.67, "mediumseagreen"), (0.77, "green"), (1, "darkgreen")]
        cmap = LinearSegmentedColormap.from_list("bwwr", colors)

        self.scat = self.ax.scatter([], [], [10], [], vmin=5, vmax=50,
                                    marker='s', cmap=cmap, edgecolor="green",
                                    linewidth=0.5, alpha=0.75)

        cbar = self.fig.colorbar(self.scat, ax=self.ax)
        cbar.set_label('Temperature')

        self.anim = FuncAnimation(self.fig, self.update, frames=900, interval=500)

    def update(self, i):
        self.scat.set_offsets((gps_n_list))
        self.scat.set_array(temp_array)

if __name__ == "__main__":
    obj1 = dataGeneration()
    # Create multi-threading for both functions in dataGeneration Class
    t1 = Thread(target=obj1.input_gps)
    t2 = Thread(target=obj1.tempSenor)

    # To start the threads
    t1.start()
    t2.start()

    app = QtWidgets.QApplication(sys.argv)
    window = ApplicationWindow()
    window.show()
    sys.exit(app.exec_())
