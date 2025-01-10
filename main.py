import Metashape
import os
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
        self.setWindowTitle("Wizard") 
        self.setFixedSize(450, 400)

        self.labelImageFolder = QtWidgets.QLabel("Select folder with photos")
        self.textImageFolder = QtWidgets.QLineEdit()
        self.textImageFolder.setPlaceholderText("Folder with photos")
        self.btnImageFolder = QtWidgets.QPushButton("Select")
        self.btnImageFolder.setFixedSize(80, 20)

        self.labelOutputFolder = QtWidgets.QLabel("Select output folder")
        self.textOutputFolder = QtWidgets.QLineEdit()
        self.textOutputFolder.setPlaceholderText("Output folder")
        self.btnOutputFolder = QtWidgets.QPushButton("Select")
        self.btnOutputFolder.setFixedSize(80, 20)

        self.labelOsnowa = QtWidgets.QLabel("Load markers from .txt file")
        self.textOsnowa = QtWidgets.QLineEdit() 
        self.textOsnowa.setPlaceholderText("Markers file")
        self.btnOsnowa = QtWidgets.QPushButton("Select")
        self.btnOsnowa.setFixedSize(80, 20)

        self.btnChooseCRS = QtWidgets.QPushButton("Select Coordinate System of loaded markers")
        self.btnChooseCRS.setFixedSize(200, 30)
        self.btnChooseCRS.clicked.connect(self.chooseCoordinateSystem)

        # photo alignment accuracy
        self.labelDownscale = QtWidgets.QLabel("Photo alignment accuracy: ")
        self.comboDownscale = QtWidgets.QComboBox()
        self.comboDownscale.addItems(["0 (Highest)", "1 (High)", "2 (Medium)", "4 (Low)", "8 (Lowest)"])
        self.comboDownscale.setCurrentIndex(4)

        # add radio buttons
        self.labelPointCloud = QtWidgets.QLabel("Generate point cloud")
        self.checkboxPointCloud = QtWidgets.QCheckBox()

        self.labelModel3D = QtWidgets.QLabel("Generate 3D model")
        self.checkboxModel3D = QtWidgets.QCheckBox()

        self.checkboxPointCloud.setChecked(False)
        self.checkboxModel3D.setChecked(False)

        # depth map quality
        self.labelDepthMapQuality = QtWidgets.QLabel("Depth map quality: ")
        self.comboDepthMapQuality = QtWidgets.QComboBox()
        self.comboDepthMapQuality.addItems(["1 (Ultra high)", "2 (High)", "4 (Medium)", "8 (Low)", "16 (Lowest)"])
        self.comboDepthMapQuality.setCurrentIndex(4)

        self.btnImageFolder.clicked.connect(lambda: self.chooseFolder(self.textImageFolder))
        self.btnOutputFolder.clicked.connect(lambda: self.chooseFolder(self.textOutputFolder))
        self.btnOsnowa.clicked.connect(lambda: self.chooseFile(self.textOsnowa))

        self.fromChunk = QtWidgets.QComboBox()
        for chunk in Metashape.app.document.chunks:
            self.fromChunk.addItem(chunk.label)

        self.btnRun = QtWidgets.QPushButton("Run")
        self.btnRun.setFixedSize(90, 30)

        self.btnQuit = QtWidgets.QPushButton("Close")
        self.btnQuit.setFixedSize(90, 30)

        layout = QtWidgets.QGridLayout() 
        layout.addWidget(self.labelImageFolder, 0, 0)
        layout.addWidget(self.textImageFolder, 0, 1)
        layout.addWidget(self.btnImageFolder, 0, 2)  

        layout.addWidget(self.labelOutputFolder, 1, 0)
        layout.addWidget(self.textOutputFolder, 1, 1)
        layout.addWidget(self.btnOutputFolder, 1, 2)

        layout.addWidget(self.labelOsnowa, 2, 0)
        layout.addWidget(self.textOsnowa, 2, 1)
        layout.addWidget(self.btnOsnowa, 2, 2)

        layout.addWidget(self.btnChooseCRS, 3, 0, 1, 3)

        layout.addWidget(self.labelDownscale, 4, 0)
        layout.addWidget(self.comboDownscale, 4, 1)

        #add radio buttons
        layout.addWidget(self.labelPointCloud, 5, 0)
        layout.addWidget(self.checkboxPointCloud, 5, 1)
        layout.addWidget(self.labelModel3D, 6, 0)
        layout.addWidget(self.checkboxModel3D, 6, 1) 

        layout.addWidget(self.labelDepthMapQuality, 7, 0)
        layout.addWidget(self.comboDepthMapQuality, 7, 1)

        buttonLayout = QtWidgets.QHBoxLayout()
        buttonLayout.addWidget(self.btnRun)
        self.btnRun.setFixedWidth(200)
        self.btnQuit.setFixedWidth(200)
        buttonLayout.addWidget(self.btnQuit)
        layout.addLayout(buttonLayout, 8, 0, 1, 3) 

        self.setLayout(layout)
        
        QtCore.QObject.connect(self.btnRun, QtCore.SIGNAL("clicked()"), self.runMainApp)
        QtCore.QObject.connect(self.btnQuit, QtCore.SIGNAL("clicked()"), self, QtCore.SLOT("reject()"))
        self.exec()
    
    def chooseFolder(self, target_field):
        """Function that opens a dialog window to choose a folder."""
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Select folder")
        if folder:
            target_field.setText(folder)  
            print(f"Selected folder: {folder}")

    def chooseFile(self, target_field):
        """Function that opens a dialog window to choose a file."""
        file = QtWidgets.QFileDialog.getOpenFileName(self, "Select file")[0]  
        if file:
            if not file.endswith('.txt'):
                print("Invalid file format. Please select a .txt file.")
                return
            target_field.setText(file)
            print(f"Selected file: {file}")

    def chooseCoordinateSystem(self):
            """Function that opens a dialog window to choose a coordinate system."""
            selected_crs = Metashape.app.getCoordinateSystem("Select Coordinate System")
            
            if selected_crs:
                self.selected_crs = selected_crs  
                print(f"Selected CRS: {selected_crs}")
                self.selected_epsg = selected_crs.authority
                print(f"Selected EPSG: {self.selected_epsg}")
            else:
                print("No CRS selected.")

    def runMainApp(self):
        document = Metashape.app.document
        chunk: Metashape.Chunk = document.chunk

        # input parameters
        image_folder = self.textImageFolder.text() 
        output_folder = self.textOutputFolder.text() 
        osnowa_file = self.textOsnowa.text() 
        photo_downscale = int(self.comboDownscale.currentText().split()[0])
        generate_point_cloud = self.checkboxPointCloud.isChecked()
        generate_model3d = self.checkboxModel3D.isChecked()
        depth_map_downscale = int(self.comboDepthMapQuality.currentText().split()[0])

        selected_epsg = self.selected_epsg
        
        # create chunk
        if chunk is None:
            chunk = Metashape.app.document.addChunk()
        
        cameras: List[Metashape.Camera] = chunk.cameras
        chunk.crs = Metashape.CoordinateSystem(selected_epsg)
        chunk.camera_crs = Metashape.CoordinateSystem("EPSG::4326")
        chunk.marker_crs = Metashape.CoordinateSystem(selected_epsg)

        def find_files(folder, types):
            return [entry.path for entry in os.scandir(folder) if (entry.is_file() and os.path.splitext(entry.name)[1].lower() in types)]

        if chunk.tie_points is None:
            # load photos
            photos = find_files(image_folder, [".jpg", ".jpeg", ".tif", ".tiff"])
            chunk.addPhotos(photos)
            # transform photos to selected crs
            for camera in chunk.cameras:
                location_wgs = camera.reference.location
                location_2000 = Metashape.CoordinateSystem.transform(location_wgs, chunk.camera_crs, chunk.marker_crs)
                camera.reference.location = location_2000

            chunk.camera_crs = Metashape.CoordinateSystem(selected_epsg)

            # load markers
            with open (osnowa_file) as file:
                lines = file.readlines()

            loaded_markers = []
            for line in lines:
                label, y_coord, x_coord, z_coord = line.split()
                marker = chunk.addMarker()
                marker.label = label
                marker.reference.location = float(x_coord), float(y_coord), float(z_coord) - 31.13
                loaded_markers.append(marker)
        
            # photo alignment
            chunk.matchPhotos(downscale=photo_downscale) 
            chunk.alignCameras() 
                
            # detect markers
            marker_type = Metashape.TargetType.CrossTarget
            chunk.detectMarkers(marker_type)

            # transform detected markers
            for marker in chunk.markers:
                if marker.position:
                    marker_position_transformed = chunk.crs.project(chunk.transform.matrix.mulp(marker.position))
                    marker.reference.location = marker_position_transformed

            # remove distant detected markers
            def calculate_distance(coord1, coord2):
                return math.sqrt(sum((a - b) ** 2 for a, b in zip(coord1, coord2)))

            def remove_distant_points(distance):
                reference_coords = [marker.reference.location for marker in loaded_markers if marker.reference.location]

                for marker in chunk.markers:
                    if marker in loaded_markers:
                        continue
                    detected_location = marker.reference.location
                    if detected_location:
                        distances = [
                            calculate_distance(detected_location, ref_coord) for ref_coord in reference_coords
                        ]
                        if min(distances) > distance:
                            chunk.remove(marker) 

            remove_distant_points(10)

        # generate depth maps if not already generated
        if chunk.depth_maps is None: 
            chunk.buildDepthMaps(downscale=depth_map_downscale, filter_mode=Metashape.MildFiltering)
        else:
            print("Depth maps already generated.")
        
        # generate point cloud and 3D model
        if generate_point_cloud:
            if not chunk.point_cloud:
                chunk.buildPointCloud(source_data=Metashape.DepthMapsData, point_confidence=False)

        if generate_model3d:
            if not chunk.model:
                chunk.buildModel(source_data = Metashape.DepthMapsData)

        # export results
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