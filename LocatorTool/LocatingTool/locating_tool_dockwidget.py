# -*- coding: utf-8 -*-
"""
/***************************************************************************
 LocatingToolDockWidget
                                 A QGIS plugin
 Finds suitable areas for a mobile control center
                             -------------------
        begin                : 2017-12-15
        git sha              : $Format:%H$
        copyright            : (C) 2017 by Group 2
        email                : group2@group2company.enterprise
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os
import os.path
import shutil

from PyQt4 import QtGui, QtCore, uic
from PyQt4.QtCore import pyqtSignal
from PyQt4.QtCore import QFileInfo
from qgis.core import *
import processing

from . import utility_functions as uf

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'locating_tool_dockwidget_base.ui'))


class LocatingToolDockWidget(QtGui.QDockWidget, FORM_CLASS):

    closingPlugin = pyqtSignal()

    def __init__(self, iface, parent=None):
        """Constructor."""
        super(LocatingToolDockWidget, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

        #define globals
        self.iface = iface
        self.canvas = self.iface.mapCanvas()

        # set up GUI operation signals

        # data

        # elf.selectInBufferButton.clicked.connect(self.selectFeaturesBuffer)
        # self.minMaxBufferButton.clicked.connect(self.calculateDonut)
        # self.clearBuffersButton.clicked.connect(self.removeLegendLayer)
        # self.markAreasButton.clicked.connect(self.markAreas)
        # self.clearMarkedButton.clicked.connect(self.clearMarked)
        # self.calculateConeButton.clicked.connect(self.calculateCone)
        # self.takeBiteFromDonutButton.clicked.connect(self.biteFromDonut)
        # self.shortestRouteButton.clicked.connect(self.calculateRoute)
        # self.getSummaryButton.clicked.connect(self.setSelectedAttribute)

        self.openFireButton.clicked.connect(self.warningLoadData)
        self.selectFireButton.activated.connect(self.selectFire)

        self.chooseWindDirectionCombo.activated.connect(self.chooseWindDirection)
        self.selectFireSeverityCombo.activated.connect(self.updateDistances)

        self.testMessageButton.clicked.connect(self.giveMessage)
        self.everythingAtOnceButton.clicked.connect(self.everythingAtOnce)
        self.completeClearButton.clicked.connect(self.clearAllAnalysisLayers)

        # results tab
        self.tied_points = []

        # Standing attributes - 'global variables'
        self.plugin_dir = os.path.dirname(__file__)
        self.fire_layer = self.setFireLayer()

    # Initial settings functions
    def warningLoadData(self):
        msgBox = QtGui.QMessageBox()
        msgBox.setText("All current layers will be dropped, continue?")
        msgBox.setStandardButtons(QtGui.QMessageBox.Yes)
        msgBox.addButton(QtGui.QMessageBox.No)
        msgBox.setDefaultButton(QtGui.QMessageBox.No)
        if msgBox.exec_() == QtGui.QMessageBox.Yes:
            self.openFire()

    def openFire(self,filename=""):
        last_dir = os.path.join(self.plugin_dir, 'sample_data')
        new_file = QtGui.QFileDialog.getOpenFileName(self, "", last_dir, "(*.qgs)")

        if new_file:
           self.iface.addProject(unicode(new_file))

        self.fire_layer = self.setFireLayer()

    def selectFire(self):
        fire = self.selectFireButton.currentText()
        scenario_nr = 0
        if fire == ' ':
            pass
        elif fire == 'Fire 1':
            scenario_nr = 1
        elif fire == 'Fire 2':
            scenario_nr = 2
        elif fire == 'Fire 3':
            scenario_nr = 3
        elif fire == 'Fire 4':
            scenario_nr = 4

        path = os.path.join(self.plugin_dir, 'sample_data', 'Fire{}_scenario.qgs'.format(str(scenario_nr)))
        self.clearLegend()
        project = QgsProject.instance().read(QFileInfo(path))
        self.setFireLayer()
        self.iface.mainWindow().setWindowTitle(os.path.splitext(os.path.basename(path))[0])

    def setFireLayer(self):
        fire = None
        fire = uf.getLegendLayerByRegExp(self.iface, 'Fire[1234]\Z')
        if fire:
            self.fire_layer = fire

        else:
            uf.showMessage(self.iface, 'No fire scenario has been found', lev=2,dur=3)
        self.setStylesLayers()
        return fire

    def setStylesLayers(self):
        path = "%s/styles/" % QgsProject.instance().homePath()

        for layer in QgsMapLayerRegistry.instance().mapLayers().values():
            processing.runalg('qgis:setstyleforvectorlayer', layer.name(), "{}{}{}".format(path, layer.name(), "_style.qml"))

    def updateDistances(self):
        severity = self.selectFireSeverityCombo.currentText()
        if severity == 'CAT 1':
            self.minDistLineEdit.setText(str(100))
            self.maxDistLineEdit.setText(str(750))
        elif severity == 'CAT 2':
            self.minDistLineEdit.setText(str(250))
            self.maxDistLineEdit.setText(str(1000))
        elif severity == 'CAT 3':
            self.minDistLineEdit.setText(str(400))
            self.maxDistLineEdit.setText(str(1250))
        elif severity == 'CAT 4':
            self.minDistLineEdit.setText(str(500))
            self.maxDistLineEdit.setText(str(1250))
        elif severity == 'CAT 5':
            self.minDistLineEdit.setText(str(500))
            self.maxDistLineEdit.setText(str(1500))

    # analysis functions
    def setSelectedAttribute(self):
        layer = uf.getLegendLayerByName(self.iface, 'ok_areas_final')
        fields = uf.getFieldNames(layer)
        self.extractAttributeSummary(fields)

    def getMinBufferCutoff(self):
        cutoff = self.minDistLineEdit.text()
        if uf.isNumeric(cutoff):
            return uf.convertNumeric(cutoff)
        else:
            return 0

    def getMaxBufferCutoff(self):
        cutoff = self.maxDistLineEdit.text()
        if uf.isNumeric(cutoff):
            return uf.convertNumeric(cutoff)
        else:
            return 0

    def calculateDonut(self, layer=0):
        layer = self.fire_layer

        #create the buffers needed min and max
        max_dist = self.getMaxBufferCutoff()
        min_dist = self.getMinBufferCutoff()
        MaxBuffer = processing.runalg('qgis:fixeddistancebuffer', layer, max_dist, 12, False, None)
        MinBuffer = processing.runalg('qgis:fixeddistancebuffer', layer, min_dist, 12, False, None)

        #create the donut (difference)
        runalg = processing.runalg('qgis:symmetricaldifference', MaxBuffer['OUTPUT'], MinBuffer['OUTPUT'], '{}/analysis_data/donut.shp'.format(self.plugin_dir))
        self.runalgShortcut(runalg, 'donut')

    def chooseWindDirection(self):
        choosetext = self.chooseWindDirectionCombo.currentText()
        direction = {'no wind': -1, 'N': 0, 'NE': 45, 'E': 90, 'SE': 135, 'S': 180, 'SW': 225, 'W': 270, 'NW': 315}
        WindDirection = direction[choosetext]
        return WindDirection

    def calculateCone(self, firelayer=0):
        if self.chooseWindDirectionCombo.currentText() != 'no wind':
            if not firelayer:
                firelayer = self.fire_layer

            processing.runandload('qgis:meancoordinates', firelayer, None, None, None)
            attlayer = uf.getLegendLayerByName(self.iface, "Mean coordinates")

            coords = []
            for feature in attlayer.getFeatures():
                attrs = feature.attributes()
                coords.append(float(attrs[0]))
                coords.append(float(attrs[1]))
            maxdist = float(self.maxDistLineEdit.text())
            coordstring = "{}, {}, {}, {}".format(coords[0], coords[0] + 60, coords[1], coords[1] - maxdist)

            #Create points in a line
            processing.runandload('qgis:regularpoints', coordstring, 100, 0, False, True, None)

            #create attribute named width (id * 60)
            layer = uf.getLegendLayerByName(self.iface, "Regular points")
            processing.runandload('qgis:fieldcalculator', layer, "width", 0, 10, 0, True, ' "id" * 60', None)

            #Create variabledistancebuffer on attribute width
            layer2 = uf.getLegendLayerByName(self.iface, "Calculated")
            processing.runandload('qgis:variabledistancebuffer', layer2, "width", 12, True, None)

            wind_direction = self.chooseWindDirection()
            self.rotateCone(wind_direction)

    def rotateCone(self, angle):
        attlayer = uf.getLegendLayerByName(self.iface, "Mean coordinates")

        coords = []
        for feature in attlayer.getFeatures():
            attrs = feature.attributes()
            coords.append(float(attrs[0]))
            coords.append(float(attrs[1]))

        # select the active layer
        layer = uf.getLegendLayerByName(self.iface, "Buffer")

        # get feature of the layer
        feature = layer.getFeatures().next()
        geom = feature.geometry()

        pt = QgsPoint(coords[0], coords[1])

        geom.rotate(angle, pt)

        # Extract CRS from route
        CRS = layer.crs().postgisSrid()

        URI = "Polygon?crs=epsg:" + str(CRS) + "&field=id:integer""&index=yes"
        # Create polygon layer for buffer
        mem_layer = QgsVectorLayer(URI,"Smoke cone","memory")

        # add Map Layer to Registry
        QgsMapLayerRegistry.instance().addMapLayer(mem_layer)

        # Prepare mem_layer for editing
        mem_layer.startEditing()

        # Set feature for Smoke cone layer
        feat = QgsFeature()

        # Set geometry for Smoke cone layer
        feat.setGeometry(geom)

        # set attributes values for Smoke cone layer
        feat.setAttributes([1])

        mem_layer.addFeature(feat, True)

        # stop editing and save changes
        mem_layer.commitChanges()

        cone = uf.getLegendLayerByName(self.iface, "Smoke cone")
        path = "%s/styles/" % QgsProject.instance().homePath()
        processing.runalg('qgis:setstyleforvectorlayer', cone, "%ssmoke_style.qml" % path)

        # remove OG cone and the other shit that's no longer necessary
        cone_layer = uf.getLegendLayerByName(self.iface, "Buffer")
        points = uf.getLegendLayerByName(self.iface, "Regular points")
        mean_coord_layer = uf.getLegendLayerByName(self.iface, "Mean coordinates")
        cone_width_layer = uf.getLegendLayerByName(self.iface, "Calculated")
        self.removeLegendLayer(cone_layer)
        self.removeLegendLayer(points)
        self.removeLegendLayer(mean_coord_layer)
        self.removeLegendLayer(cone_width_layer)

    def biteFromDonut(self):
        donut = QgsVectorLayer('{}/analysis_data/donut.shp'.format(self.plugin_dir), 'test', 'ogr')
        bite = uf.getLegendLayerByName(self.iface, "Smoke cone") #TODO change!
        if donut and bite:
            self.runalgShortcut(processing.runalg('qgis:difference', donut, bite, True, '{}/analysis_data/donut_bite.shp'.format(self.plugin_dir)))

    def focusArea(self, layer=0):
        #create the buffers needed min and max
        min_dist = self.getMaxBufferCutoff()
        max_dist = 7500
        MinBuffer = processing.runalg('qgis:fixeddistancebuffer', layer, min_dist, 12, False, None)
        MaxBuffer = processing.runalg('qgis:fixeddistancebuffer', layer, max_dist, 12, False, None)

        #create the donut (difference)
        processing.runandload('qgis:symmetricaldifference', MaxBuffer['OUTPUT'], MinBuffer['OUTPUT'], None)

        testname = uf.getLegendLayerByName(self.iface, "Symmetrical difference")

        path = "%s/styles/" % QgsProject.instance().homePath()
        processing.runalg('qgis:setstyleforvectorlayer', testname, "%sfocal_zone_style.qml" % path)

    # Network and route methods
    def getNetwork(self):
        roads_layer = uf.getLegendLayerByName(self.iface, 'Roads')
        if roads_layer:
            # see if there is an obstacles layer to subtract roads from the network TODO: Do we want obstacles??
            obstacles_layer = uf.getLegendLayerByName(self.iface, "Obstacles")
            if obstacles_layer:
                # retrieve roads outside obstacles (inside = False)
                features = uf.getFeaturesByIntersection(roads_layer, obstacles_layer, False)
                # add these roads to a new temporary layer
                road_network = uf.createTempLayer('Temp_Network','LINESTRING',roads_layer.crs().postgisSrid(),[],[])
                road_network.dataProvider().addFeatures(features)
            else:
                road_network = roads_layer
            return road_network

    def buildNetwork(self):
        self.network_layer = self.getNetwork()
        if self.network_layer:
            sources_layer = QgsVectorLayer('{}/analysis_data/Selection.shp'.format(self.plugin_dir), 'Selection', 'ogr')

            source_points = [feature.geometry().centroid().asPoint() for feature in sources_layer.getFeatures()]

            fire = self.fire_layer
            fire_point = [feature.geometry().centroid().asPoint() for feature in fire.getFeatures()]
            source_points.insert(0, fire_point[0])

            # build the graph including these points
            if len(source_points) > 1:
                self.graph, self.tied_points = uf.makeUndirectedGraph(self.network_layer, source_points)
        return sources_layer

    def calculateRoute(self):
        locations_layer = self.buildNetwork() # instead of a buildNetwork-button
        locations_list = [feature.attribute('FID2') for feature in locations_layer.getFeatures()]

        # origin and destination must be in the set of tied_points
        options = len(self.tied_points)
        if options > 1:
            # origin and destination are given as an index in the tied_points list
            origin = 0

            # calculate the shortest path for the given origin and every destination
            for destination in range(1, len(self.tied_points)):
                (path, cost) = uf.calculateRouteDijkstra(self.graph, self.tied_points, origin, destination)
                # store the route results in temporary layer called "Routes"
                routes_layer = uf.getLegendLayerByName(self.iface, "Routes")
                # create one if it doesn't exist
                if not routes_layer:
                    attribs = ['to_FID', 'length']
                    types = [QtCore.QVariant.LongLong]
                    routes_layer = uf.createTempLayer('Routes','LINESTRING',self.network_layer.crs().postgisSrid(), attribs, types)
                    uf.loadTempLayer(routes_layer)
                # insert route line
                cost = QgsDistanceArea().measureLine(path) #Calculates the length of the path
                uf.insertTempFeatures(routes_layer, [path], [[locations_list[destination-1],cost]])

            # style_path = "%s/styles/" % QgsProject.instance().homePath()
            # processing.runalg('qgis:setstyleforvectorlayer', routes_layer, "%sShortestRoute_style.qml" % style_path)

    def deleteRoutes(self): #TODO: implement this function? - maybe not needed since it is implemented in the 'clear-all'button?
        routes_layer = uf.getLegendLayerByName(self.iface, "Routes")
        if routes_layer:
            ids = uf.getAllFeatureIds(routes_layer)
            routes_layer.startEditing()
            for id in ids:
                routes_layer.deleteFeature(id)
            routes_layer.commitChanges()

    # Filtering and selection functions

    def selectFeaturesBuffer(self, layer=0):
        intersect_layer = QgsVectorLayer('{}/analysis_data/donut_bite.shp'.format(self.plugin_dir), 'donut', 'ogr')
        if not intersect_layer:
            intersect_layer = QgsVectorLayer('{}/analysis_data/donut.shp'.format(self.plugin_dir), 'donut', 'ogr')

        # QgsMapLayerRegistry.instance().addMapLayers([intersect_layer])


        if layer and intersect_layer:
            uf.selectFeaturesByIntersection(layer, intersect_layer, True)

    def markAreas(self):

        result_area = QgsVectorLayer('{}/analysis_data/donut_bite.shp'.format(self.plugin_dir), 'donut', 'ogr')
        if not result_area:
            uf.showMessage(self.iface, 'no donut', dur=5)
            result_area = QgsVectorLayer('{}/analysis_data/donut.shp'.format(self.plugin_dir), 'donut_bite', 'ogr')

        ok_areas = uf.getLegendLayerByName(self.iface, "ok_areas_final")
        # Check possibility of this function
        if result_area and ok_areas:
            self.selectFeaturesBuffer(ok_areas)
            runalg = processing.runalg('qgis:saveselectedfeatures', ok_areas,
                                       '{}/analysis_data/Selection.shp'.format(self.plugin_dir))
            selection_layer = self.runalgShortcut(runalg, 'Selection')
            # QgsMapLayerRegistry.instance().addMapLayers([selection_layer])
            ok_areas.removeSelection()

        return selection_layer

    def filterSelectionLayer(self, selection_layer):
        routes_layer = uf.getLegendLayerByName(self.iface, 'Routes')

        if not routes_layer:
            filtered_layer = None
        else:
            dicti = processing.runalg('qgis:joinattributestable', selection_layer, routes_layer, 'FID2', 'to_FID', None)

            join_path = dicti[dicti.keys()[0]]  # this is the folder path to the layer
            join_layer = QgsVectorLayer(join_path, "join_layer", "ogr")
            # QgsMapLayerRegistry.instance().addMapLayers([join_layer])

            idx = join_layer.fieldNameIndex('Area')
            max_area = join_layer.maximumValue(idx)
            required_area = int(self.areaEdit.text())
            uf.selectFeaturesByRangeValues(join_layer, 'Area', required_area, max_area)

            area_dict = processing.runalg('qgis:saveselectedfeatures', join_layer, None)

            area_layer = QgsVectorLayer(area_dict[area_dict.keys()[0]], 'selected_area', 'ogr')
            QgsMapLayerRegistry.instance().addMapLayers([area_layer])

            sorted_features = uf.sortByField(area_layer, 'length')


            return area_layer, sorted_features

    def selectTopLocations(self, locations_layer, sorted_features):
        top_nr = int(self.numOfResultsLineEdit.text())
        top = sorted_features[0:top_nr]
        top_fid = []
        for feature in top:
            top_fid.append(feature[3])

        uf.selectFeaturesByListValues(locations_layer, 'FID2', top_fid)
        top_dict = processing.runalg('qgis:saveselectedfeatures', locations_layer, None)
        top_path = top_dict[top_dict.keys()[0]]
        top_layer = QgsVectorLayer(top_path, "Top locations", "ogr")
        QgsMapLayerRegistry.instance().addMapLayers([top_layer])
        self.removeLegendLayer(locations_layer)
        path = "%s/styles/" % QgsProject.instance().homePath()
        processing.runalg('qgis:setstyleforvectorlayer', top_layer, "%stop_style.qml" % path)

        self.filterRoutes(top_fid)

        return top_layer

    def filterRoutes(self, top_fid):
        routes_layer = uf.getLegendLayerByName(self.iface, 'Routes')
        uf.selectFeaturesByListValues(routes_layer, 'to_FID', top_fid)

        runalg = processing.runalg('qgis:saveselectedfeatures', routes_layer, None) #TODO: do we want to save this layer?
        top_layer = self.runalgShortcut(runalg, "Fire-routes", load=True)

        self.removeLegendLayer(routes_layer)

        path = "%s/styles/" % QgsProject.instance().homePath()
        processing.runalg('qgis:setstyleforvectorlayer', top_layer, "%sShortestRoute_style.qml" % path)

    # Reporting functions
    def extractAttributeSummary(self, layer):
        # get summary of the attribute
        fields = uf.getFieldNames(layer)
        attribute = [fields[0], fields[2], fields[5]]  # desc, area, length
        summary = []
        for feature in layer.getFeatures():
            row = [] #contains all the attributes for the current feature
            for col_name in attribute:
                row.append((feature.attribute(col_name)))
            summary.append(row)

        # send this to the table
        self.clearTable()
        self.updateTable(summary)

    def updateTable(self, values):
        self.statisticsTable.setColumnCount(3)
        self.statisticsTable.setHorizontalHeaderLabels(["Landuse", "Size", "Distance"])
        self.statisticsTable.setRowCount(len(values))
        i = 0
        for item in values:
            # i is the table row, items must tbe added as QTableWidgetItems
            # self.statisticsTable.setItem(i,0,QtGui.QTableWidgetItem(unicode(i)))
            self.statisticsTable.setItem(i,0,QtGui.QTableWidgetItem(unicode(item[0]))) #eng_desc
            self.statisticsTable.setItem(i,1,QtGui.QTableWidgetItem(unicode(item[1]))) #area
            self.statisticsTable.setItem(i,2,QtGui.QTableWidgetItem(unicode(item[2]))) #length
            i += 1
        self.statisticsTable.horizontalHeader().setResizeMode(0, QtGui.QHeaderView.ResizeToContents)
        self.statisticsTable.horizontalHeader().setResizeMode(1, QtGui.QHeaderView.Stretch)
        self.statisticsTable.resizeRowsToContents()

    def clearTable(self):
        self.statisticsTable.clear()

    # help functions
    def runalgShortcut(self, dicti, name='layer', memory=False, load=False):
        path = dicti[dicti.keys()[0]]
        if not memory:
            provider = 'ogr'
        else:
            provider = 'memory'

        layer = QgsVectorLayer(path, name, provider)

        if load:
            QgsMapLayerRegistry.instance().addMapLayers([layer])

        return layer

    def giveMessage(self):
        self.iface.messageBar().pushMessage("test test:", "{}".format("testing"), level=0, duration=5)

    # clearing functions
    def removeLegendLayer(self, layer):
        if layer:
            QgsMapLayerRegistry.instance().removeMapLayer(layer.id())

    def clearLegend(self):
        legend = uf.getLegendLayers(self.iface)
        for layer in legend:
            self.removeLegendLayer(layer)

    def clearAllAnalysisLayers(self):
        layers = ["Symmetrical difference", "Routes","join_layer", "Regular points", "Mean coordinates",
                  "selected_area", "Smoke cone", "Top locations", "Fire-routes"]
        for layer_name in layers:
            layer = uf.getLegendLayerByName(self.iface, layer_name)
            if layer:
                self.removeLegendLayer(layer)

    def clearAnalysisDataFolder(self):
        folder = '{}/analysis_data/'.format(self.plugin_dir)
        for the_file in os.listdir(folder):
            file_path = os.path.join(folder, the_file)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception as e:
                uf.showMessage(self.iface, 'OBS analysis_data folder not cleared completely!', lev=2, dur=5)

    # The BIG button function
    def everythingAtOnce(self):
        if self.selectFireButton.currentIndex() == 0:
            uf.showMessage(self.iface, 'OBS Please select a fire scenario', lev=2, dur=5)
        else:
            self.clearAnalysisDataFolder()
            firelayer = self.fire_layer
            self.calculateDonut(firelayer)
            self.calculateCone(firelayer)
            self.biteFromDonut()
            selection_lyr = self.markAreas()
            self.focusArea(firelayer)
            self.calculateRoute()
            area_layer, sorted_features = self.filterSelectionLayer(selection_lyr)
            top_layer = self.selectTopLocations(area_layer, sorted_features)
            self.extractAttributeSummary(top_layer)

    def closeEvent(self, event):
        # self.clearAllAnalysisLayers()
        #TODO clear analysis_data folder
        self.clearAnalysisDataFolder()
        self.closingPlugin.emit()
        event.accept()

