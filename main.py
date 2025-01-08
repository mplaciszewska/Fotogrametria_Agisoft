import Metashape
import os, sys, time
from pprint import pprint
from typing import List
import math
from PySide2 import QtGui, QtCore, QtWidgets

compatible_major_version = "2.1"
found_major_version = ".".join(Metashape.app.version.split('.')[:2])
if found_major_version != compatible_major_version:
    raise Exception("Incompatible Metashape version: {} != {}".format(found_major_version, compatible_major_version))


class mainApp(QtWidgets.QDialog):
    def __init__(self, parent):

        QtWidgets.QDialog.__init__(self, parent)
        self.setWindowTitle("Atomatyczna orientacja zdjęć")

        self.labelImageFolder = QtWidgets.QLabel("Folder ze zdjęciami")
        self.textImageFolder = QtWidgets.QLineEdit()
        self.textImageFolder.setPlaceholderText("Wybierz folder...")
        self.btnImageFolder = QtWidgets.QPushButton("Wybierz")
        self.btnImageFolder.setFixedSize(80, 30)

        self.labelOutputFolder = QtWidgets.QLabel("Wynikowy folder")
        self.textOutputFolder = QtWidgets.QLineEdit()
        self.textOutputFolder.setPlaceholderText("Wybierz folder...")
        self.btnOutputFolder = QtWidgets.QPushButton("Wybierz")
        self.btnOutputFolder.setFixedSize(80, 30)

        # add radio buttons
        self.labelPointCloud = QtWidgets.QLabel("Generuj chmurę punktów")
        self.checkboxPointCloud = QtWidgets.QCheckBox()

        self.labelModel3D = QtWidgets.QLabel("Generuj model 3D")
        self.checkboxModel3D = QtWidgets.QCheckBox()
        #set to be false
        self.checkboxPointCloud.setChecked(False)
        self.checkboxModel3D.setChecked(False)
    

        
        
        self.btnImageFolder.clicked.connect(lambda: self.chooseFolder(self.textImageFolder))
        self.btnOutputFolder.clicked.connect(lambda: self.chooseFolder(self.textOutputFolder))

        self.fromChunk = QtWidgets.QComboBox()
        for chunk in Metashape.app.document.chunks:
            self.fromChunk.addItem(chunk.label)


        self.btnOk = QtWidgets.QPushButton("Ok")
        self.btnOk.setFixedSize(90, 50)
        self.btnOk.setToolTip("run script")

        self.btnQuit = QtWidgets.QPushButton("Close")
        self.btnQuit.setFixedSize(90, 50)
        layout = QtWidgets.QGridLayout()  # creating layout
        layout.addWidget(self.labelImageFolder, 0, 0)
        layout.addWidget(self.textImageFolder, 0, 1)
        layout.addWidget(self.btnImageFolder, 0, 2)  # Dodanie przycisku obok pola tekstowego

        layout.addWidget(self.labelOutputFolder, 1, 0)
        layout.addWidget(self.textOutputFolder, 1, 1)
        layout.addWidget(self.btnOutputFolder, 1, 2)

        layout.addWidget(self.btnOk, 2, 1)
        layout.addWidget(self.btnQuit, 2, 2)
        #add radio buttons
        layout.addWidget(self.labelPointCloud, 3, 0)
        layout.addWidget(self.checkboxPointCloud, 3, 1)
        layout.addWidget(self.labelModel3D, 4, 0)
        layout.addWidget(self.checkboxModel3D, 4, 1) 

        self.setLayout(layout)

        QtCore.QObject.connect(self.btnOk, QtCore.SIGNAL("clicked()"), self.runMainApp)
        QtCore.QObject.connect(self.btnQuit, QtCore.SIGNAL("clicked()"), self, QtCore.SLOT("reject()"))
        self.exec()
    
    def chooseFolder(self, target_field):
        """Funkcja otwierająca okno dialogowe do wyboru folderu."""
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Wybierz folder")
        if folder:
            target_field.setText(folder)  # Ustawienie ścieżki w odpowiednim polu tekstowym
            print(f"Wybrano folder: {folder}")

    def runMainApp(self):
        document = Metashape.app.document
        chunk: Metashape.Chunk = document.chunk
        # 1. usuniecie wszystkich chunkow (zeby zdjecia nie wczytaly sie drugi raz po ponownym uruchomieniu)
        # if chunk.tie_points is None:
        # document.remove(chunk)

        # if chunk.depth_maps is None:
        #     document.remove(chunk)

        # parametry wejsciowe
        image_folder = self.textImageFolder.text()  # Odczytaj folder z pola tekstowego
        output_folder = self.textOutputFolder.text()  # Odczytaj folder z pola tekstowego
        osnowa_file =  f"{output_folder}/osnowa_UAV.txt"
        orientacja = 8 # low
        # generuj_chmure = False
        # generuj_model3d = False
        generuj_chmure = self.checkboxPointCloud.isChecked()
        generuj_model3d = self.checkboxModel3D.isChecked()

        # 2. Utworzenie chunka (stworzenie chunka przez API i ustawienie ukladu) 
        if chunk is None:
            chunk = Metashape.app.document.addChunk()
        
        cameras: List[Metashape.Camera] = chunk.cameras
        chunk.crs = Metashape.CoordinateSystem("EPSG::2178")
        chunk.camera_crs = Metashape.CoordinateSystem("EPSG::4326")
        chunk.marker_crs = Metashape.CoordinateSystem("EPSG::2178")
        # zdjecia: 4326
        # osnowa: 2180


        # 3. Wczytanie zdjec
        def find_files(folder, types):
            return [entry.path for entry in os.scandir(folder) if (entry.is_file() and os.path.splitext(entry.name)[1].lower() in types)]

        if chunk.tie_points is None:
            photos = find_files(image_folder, [".jpg", ".jpeg", ".tif", ".tiff"])
            chunk.addPhotos(photos)

            for camera in chunk.cameras:
                location_wgs = camera.reference.location
                location_2000 = Metashape.CoordinateSystem.transform(location_wgs, chunk.camera_crs, chunk.marker_crs)
                camera.reference.location = location_2000

            chunk.camera_crs = Metashape.CoordinateSystem('EPSG:2178')

            # 4. Wczytanie osnowy
            #otwarcie plik TXT
            pkty_osnowy = osnowa_file

            with open (pkty_osnowy) as file:
                lines = file.readlines()

            fotopunkty = []
            for line in lines:
                label, y_coord, x_coord, z_coord = line.split()
                marker = chunk.addMarker()
                marker.label = label
                marker.reference.location = float(x_coord), float(y_coord), float(z_coord) - 31.13
                fotopunkty.append(marker)
                
            # 6. wykrywanie znaczkow
            marker_type = Metashape.TargetType.CrossTarget
            chunk.detectMarkers(marker_type)

            # transformacja wspolrzednych do przyjetego ukladu odniesienia
            for marker in chunk.markers:
                if marker.position:
                    marker_position_transformed = chunk.crs.project(chunk.transform.matrix.mulp(marker.position))
                    marker.reference.location = marker_position_transformed
            print("transformacja zakonczona")

            # usuniecie odleglych znacznikow
            def calculate_distance(coord1, coord2):
                return math.sqrt(sum((a - b) ** 2 for a, b in zip(coord1, coord2)))

            def remove_distant_points(distance):
                reference_coords = [
                    marker.reference.location for marker in fotopunkty if marker.reference.location
                ]

                for marker in chunk.markers:
                    if marker in fotopunkty:
                        continue
                    
                    detected_location = marker.reference.location

                    if detected_location:
                        distances = [
                            calculate_distance(detected_location, ref_coord) for ref_coord in reference_coords
                        ]

                        if min(distances) > distance:
                            print(f"Removing marker {marker.label}, distance to the closest marker: {min(distances)}")
                            chunk.remove(marker) 

            remove_distant_points(10)

        # 5. Orientacja (low)
        
            chunk.matchPhotos(downscale=orientacja)  # Dopasowanie zdjęć

            chunk.alignCameras()  # Wyrównanie kamer

        # Sprawdzenie, czy mapy głębi zostały już wygenerowane (jeśli nie, wygeneruj mapy głębi)
        if chunk.depth_maps is None:  # Jeżeli nie ma map głębi
            chunk.buildDepthMaps(downscale=16, filter_mode=Metashape.MildFiltering)

            if chunk.depth_maps:
                print("Mapy głębi zostały wygenerowane.")
            else:
                print("Brak map głębi.")
        else:
            print("Mapy głębi są już wygenerowane, pomijam generowanie.")
        

        # create 3d model
        if generuj_chmure:
           if not chunk.point_cloud:
            chunk.buildPointCloud(source_data=Metashape.DepthMapsData, point_confidence=False)

        if generuj_model3d:
            if not chunk.model:
                chunk.buildModel(source_data = Metashape.DepthMapsData)

        # eksport plikow wynikowych
        with open(output_folder + '/external_orientation.txt', 'w') as f:
            f.write("Camera Label, X, Y, Z, Rotation\n")
            for camera in chunk.cameras:
                location = camera.reference.location
                rotation = camera.reference.rotation
                f.write(f"{camera.label}, {location.x}, {location.y}, {location.z}, {rotation[0]}, {rotation[1]}, {rotation[2]}\n")

        if chunk.model:
            chunk.exportModel(output_folder + '/model3d.obj')

        if chunk.point_cloud:
            chunk.exportPointCloud(output_folder + '/point_cloud.las', source_data = Metashape.PointCloudData)
                
                        
                

app = QtWidgets.QApplication.instance()
parent = app.activeWindow()

dlg = mainApp(parent)

# def copy_bbox():
#     app = QtWidgets.QApplication.instance()
#     parent = app.activeWindow()

#     dlg = mainApp(parent)

# label = "Scripts/run script"
# Metashape.app.removeMenuItem(label)
# Metashape.app.addMenuItem(label, copy_bbox)
# print("To execute this script press {}".format(label))


# - wybó układów??
# - wybór pliku txt z osnowa
# - eksport el. orientacji do txt
# - wybór rodzaju orientacji