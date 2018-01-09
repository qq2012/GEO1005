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

from PyQt4 import QtGui, QtCore, uic
from PyQt4.QtCore import pyqtSignal
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

        self.iface.projectRead.connect(self.updateLayers)
        self.iface.newProjectCreated.connect(self.updateLayers)
        self.iface.legendInterface().itemRemoved.connect(self.updateLayers)
        self.iface.legendInterface().itemAdded.connect(self.updateLayers)
        self.chooseWindDirectionCombo.activated.connect(self.chooseWindDirection)
        self.selectInBufferButton.clicked.connect(self.selectFeaturesBuffer)

        self.openFireButton.clicked.connect(self.openFire)
        self.minMaxBufferButton.clicked.connect(self.calculateDonut)
        self.selectLayerCombo.activated.connect(self.setSelectedLayer) #TODO: this uses the method setSelectedLayer - which doesn't do anythin, why is this line needed?
        self.selectFireSeverityCombo.activated.connect(self.updateDistances)
        self.clearBuffersButton.clicked.connect(self.clearBuffers)
        self.markAreasButton.clicked.connect(self.markAreas)
        self.clearMarkedButton.clicked.connect(self.clearMarked)

        self.calculateConeButton.clicked.connect(self.calculateCone)
        self.testMessageButton.clicked.connect(self.giveMessage)
        self.takeBiteFromDonutButton.clicked.connect(self.biteFromDonut)
        self.everythingAtOnceButton.clicked.connect(self.everythingAtOnce)
        self.completeClearButton.clicked.connect(self.clearAll)

        # results tab
        self.getSummaryButton.clicked.connect(self.setSelectedAttribute)
        self.tied_points = []
        self.shortestRouteButton.clicked.connect(self.calculateRoute)

        # initialisation
        self.updateLayers()

        # Standing attributes - 'global variables'
        self.plugin_dir = os.path.dirname(__file__)
        self.fire_layer = self.setFireLayer()


    def openFire(self,filename=""):
        last_dir = uf.getLastDir("data_MCC")
        new_file = QtGui.QFileDialog.getOpenFileName(self, "", last_dir, "(*.qgs)")
        if new_file:
            self.iface.addProject(unicode(new_file))

    def setFireLayer(self):
        uf.showMessage(self.iface, 'plugin dir: {}'.format(self.plugin_dir), dur=10)
        return None


    def updateLayers(self):
        layers = uf.getLegendLayers(self.iface, 'all', 'all')
        self.selectLayerCombo.clear()
        if layers:
            layer_names = uf.getLayersListNames(layers)
            self.selectLayerCombo.addItems(layer_names)
            self.setSelectedLayer()


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

    def clearBuffers(self, buffer_layer=0):
        if not buffer_layer:
            buffer_layer = uf.getLegendLayerByName(self.iface, "Symmetrical difference")
            QgsMapLayerRegistry.instance().removeMapLayer(buffer_layer.id())
            self.clearBuffers()
        elif buffer_layer:
            QgsMapLayerRegistry.instance().removeMapLayer(buffer_layer.id())

    def clearMarked(self):
        marked_layer = uf.getLegendLayerByName(self.iface, "Selection")
        if marked_layer:
            self.clearBuffers(marked_layer)

    def setSelectedLayer(self):
        """Some buttons use this method but it doesn't do anything since we have commented out everything?"""
        # layer_name = self.selectLayerCombo.currentText()
        # layer = uf.getLegendLayerByName(self.iface,layer_name)
        # self.setSelectedAttribute() #before: self.updateAttributes(layer)
        pass

    def getSelectedLayer(self):
        layer_name = self.selectLayerCombo.currentText()
        layer = uf.getLegendLayerByName(self.iface,layer_name)
        return layer


    def setSelectedAttribute(self):
        # TODO: 'ok_areas' should be changed to the final locations layer - global variable?
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
        #open layer if necessary
        if not layer:
            layer = self.getSelectedLayer() # TODO put fire layer here

        #create the buffers needed min and max
        max_dist = self.getMaxBufferCutoff()
        min_dist = self.getMinBufferCutoff()
        MaxBuffer = processing.runalg('qgis:fixeddistancebuffer', layer, max_dist, 12, False, None)
        MinBuffer = processing.runalg('qgis:fixeddistancebuffer', layer, min_dist, 12, False, None)

        #create the donut (difference)
        processing.runandload('qgis:symmetricaldifference', MaxBuffer['OUTPUT'], MinBuffer['OUTPUT'], None)

        #self.refreshCanvas(donut)

    def chooseWindDirection(self):
        choosetext = self.chooseWindDirectionCombo.currentText()
        direction = {'no wind': -1, 'N': 0, 'NE': 45, 'E': 90, 'SE': 135, 'S': 180, 'SW': 225, 'W': 270, 'NW': 315}
        WindDirection = direction[choosetext]
        return WindDirection

    def selectFeaturesBuffer(self, layer=0):
        #Add possibility of loading def with pre-set layer
        if not layer:
            layer = self.getSelectedLayer()
        if uf.getLegendLayerByName(self.iface, "Difference"):
            intersect_layer = uf.getLegendLayerByName(self.iface, "Difference")
        elif uf.getLegendLayerByName(self.iface, "Symmetrical difference"):
            intersect_layer = uf.getLegendLayerByName(self.iface, "Symmetrical difference")

        if layer and intersect_layer:
            uf.selectFeaturesByIntersection(layer, intersect_layer, True)

    def filterSelectionLayer(self, selection_layer):
        # This method filters out the 10 best locations based on size, traveltime etc... TODO: actually filter based on the join
        routes_layer = uf. getLegendLayerByName(self.iface, 'Routes')

        if routes_layer:
            filtered_layer = processing.runalg('qgis:joinattributestable', selection_layer, routes_layer, 'FID2', 'to_FID', None)
        else:
            filtered_layer = None

        return filtered_layer

    def markAreas(self):
        if uf.getLegendLayerByName(self.iface, "Difference"):
            result_area = uf.getLegendLayerByName(self.iface, "Difference")
        elif uf.getLegendLayerByName(self.iface, "Symmetrical difference"):
            result_area = uf.getLegendLayerByName(self.iface, "Symmetrical difference")

        ok_areas = uf.getLegendLayerByName(self.iface, "ok_areas_final")
        #Check possibility of this function
        if result_area and ok_areas:
            self.selectFeaturesBuffer(ok_areas)
            processing.runandload('qgis:saveselectedfeatures', ok_areas, None)
            selection_layer = uf.getLegendLayerByName(self.iface, "Selection")
            path = "%s/styles/" % QgsProject.instance().homePath()
            processing.runalg('qgis:setstyleforvectorlayer', selection_layer, "%sok_areas_style.qml" % path)
            ok_areas.removeSelection()
        return selection_layer

    def giveMessage(self):
        self.iface.messageBar().pushMessage("test test:", "{}".format("testing"), level=0, duration=5)

    def calculateCone(self, firelayer=0):
        if self.chooseWindDirectionCombo.currentText() != 'no wind':
            if not firelayer:
                firelayer = self.getSelectedLayer()

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

            if self.chooseWindDirectionCombo.currentText() == 'N':
                self.rotateCone(0)
            elif self.chooseWindDirectionCombo.currentText() == 'NE':
                self.rotateCone(45)
            elif self.chooseWindDirectionCombo.currentText() == 'E':
                self.rotateCone(90)
            elif self.chooseWindDirectionCombo.currentText() == 'SE':
                self.rotateCone(135)
            elif self.chooseWindDirectionCombo.currentText() == 'S':
                self.rotateCone(180)
            elif self.chooseWindDirectionCombo.currentText() == 'SW':
                self.rotateCone(225)
            elif self.chooseWindDirectionCombo.currentText() == 'W':
                self.rotateCone(270)
            elif self.chooseWindDirectionCombo.currentText() == 'NW':
                self.rotateCone(315)

    def rotateCone(self, angle):
        attlayer = uf.getLegendLayerByName(self.iface, "Mean coordinates")

        coords = []
        for feature in attlayer.getFeatures():
            attrs = feature.attributes()
            coords.append(float(attrs[0]))
            coords.append(float(attrs[1]))

        # select the active layer
        #OLD layer = iface.activeLayer()
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
        mem_layer = QgsVectorLayer(URI,
                                   "Smoke cone",
                                   "memory")

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
        self.clearBuffers(cone_layer)
        self.clearBuffers(points)
        self.clearBuffers(mean_coord_layer)
        self.clearBuffers(cone_width_layer)

    def biteFromDonut(self):
        donut = uf.getLegendLayerByName(self.iface, "Symmetrical difference")
        bite = uf.getLegendLayerByName(self.iface, "Smoke cone")
        if donut and bite:
            processing.runandload('qgis:difference', donut, bite, True, None)

    def defineFocalZone(self, layer=0):
        #open layer
        if not layer:
            layer = self.getSelectedLayer()

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

    def everythingAtOnce(self):
        firelayer = self.getSelectedLayer() # TODO change this to fire-layer
        self.calculateDonut(firelayer)
        self.calculateCone(firelayer)
        self.biteFromDonut()
        selection_lyr = self.markAreas()
        if uf.getLegendLayerByName(self.iface, "Symmetrical difference"):
            self.clearBuffers(uf.getLegendLayerByName(self.iface, "Symmetrical difference"))
        if uf.getLegendLayerByName(self.iface, "Difference"):
            self.clearBuffers(uf.getLegendLayerByName(self.iface, "Difference"))
        self.defineFocalZone(firelayer)
        self.calculateRoute()
        filtered_lyr = self.filterSelectionLayer(selection_lyr)


    def clearAll(self):
        if uf.getLegendLayerByName(self.iface, "Symmetrical difference"):
            self.clearBuffers(uf.getLegendLayerByName(self.iface, "Symmetrical difference"))
        if uf.getLegendLayerByName(self.iface, "Difference"):
            self.clearBuffers(uf.getLegendLayerByName(self.iface, "Difference"))
        if uf.getLegendLayerByName(self.iface, "Smoke cone"):
            self.clearBuffers(uf.getLegendLayerByName(self.iface, "Smoke cone"))
        if uf.getLegendLayerByName(self.iface, "Selection"):
            self.clearBuffers(uf.getLegendLayerByName(self.iface, "Selection"))
        if uf.getLegendLayerByName(self.iface, "Intersection"):
            self.clearBuffers(uf.getLegendLayerByName(self.iface, "Intersection"))
        if uf.getLegendLayerByName(self.iface, "Routes"):
            self.clearBuffers(uf.getLegendLayerByName(self.iface, "Routes"))
        if uf.getLegendLayerByName(self.iface, "Saved routes"):
            self.clearBuffers(uf.getLegendLayerByName(self.iface, "Saved routes"))


    #############################
    #   Network and route methods
    #############################

    def getNetwork(self):
        # TODO: change roads_clipped to the final road-layer (?)
        roads_layer = uf.getLegendLayerByName(self.iface, 'roads_clipped')
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
        else:
            return

    def buildNetwork(self):
        self.network_layer = self.getNetwork()
        if self.network_layer:
            # TODO: Change sources_layer to final locations-within-buffer-layer
            sources_layer = uf.getLegendLayerByName(self.iface, 'Selection')
            source_points = [feature.geometry().centroid().asPoint() for feature in sources_layer.getFeatures()]

            # TODO: change to final fire-layer
            fire = uf.getLegendLayerByName(self.iface, 'Fire2')
            fire_point = [feature.geometry().centroid().asPoint() for feature in fire.getFeatures()]
            source_points.insert(0, fire_point[0])

            # build the graph including these points
            if len(source_points) > 1:
                self.graph, self.tied_points = uf.makeUndirectedGraph(self.network_layer, source_points)
        return

    def calculateRoute(self):
        self.buildNetwork() # instead of a buildNetwork-button
        # TODO: make this nicer? Retrieving the FID-attribute of the locations.
        # TODO:  Change input-parameter to final-within-buffer-layer
        locations_layer = uf.getLegendLayerByName(self.iface, 'Selection')
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
                # TODO: The cost is inf, fix that!!
                cost = QgsDistanceArea().measureLine(path) #Calculates the length of the path
                uf.insertTempFeatures(routes_layer, [path], [[locations_list[destination-1],cost]])

            style_path = "%s/styles/" % QgsProject.instance().homePath()
            processing.runalg('qgis:setstyleforvectorlayer', routes_layer, "%sShortestRoute_style.qml" % style_path)

    def deleteRoutes(self): #TODO: implement this function? - maybe not needed since it is implemented in the 'clear-all'button?
        routes_layer = uf.getLegendLayerByName(self.iface, "Routes")
        if routes_layer:
            ids = uf.getAllFeatureIds(routes_layer)
            routes_layer.startEditing()
            for id in ids:
                routes_layer.deleteFeature(id)
            routes_layer.commitChanges()

    def refreshCanvas(self, layer):
        if self.canvas.isCachingEnabled():
            layer.setCacheImage(None)
        else:
            self.canvas.refresh()

    #################
    #   Results tab
    #################

    def extractAttributeSummary(self, attribute):
        # get summary of the attribute
        # TODO: should layer (variable) be retrieved by name always?
        """   ROB: Can also be done differently, but if it works it works.. Right? """
        # TODO: 'ok_areas' should be changed to the final locations layer - global variable?

        layer = uf.getLegendLayerByName(self.iface, 'ok_areas_final')
        summary = []
        # only use the first attribute in the list
        for feature in layer.getFeatures():
            row = [] #contains all the attributes for the current feature
            for col_name in attribute:
                row.append((feature.attribute(col_name)))
            summary.append(row)

        # send this to the table
        self.clearTable()
        self.updateTable(summary)

    # table window functions
    def updateTable(self, values):
        self.statisticsTable.setColumnCount(3)
        self.statisticsTable.setHorizontalHeaderLabels(["ID", "Landuse", "Area"])
        self.statisticsTable.setRowCount(len(values))
        i = 0
        for item in values:
            # i is the table row, items must tbe added as QTableWidgetItems
            # self.statisticsTable.setItem(i,0,QtGui.QTableWidgetItem(unicode(i)))
            self.statisticsTable.setItem(i,0,QtGui.QTableWidgetItem(unicode(item[3]))) #ID
            self.statisticsTable.setItem(i,1,QtGui.QTableWidgetItem(unicode(item[1]))) #Landuse
            self.statisticsTable.setItem(i,2,QtGui.QTableWidgetItem(unicode(item[4]))) #Area
            i += 1
        self.statisticsTable.horizontalHeader().setResizeMode(0, QtGui.QHeaderView.ResizeToContents)
        self.statisticsTable.horizontalHeader().setResizeMode(1, QtGui.QHeaderView.Stretch)
        self.statisticsTable.resizeRowsToContents()

    def clearTable(self):
        self.statisticsTable.clear()

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()

