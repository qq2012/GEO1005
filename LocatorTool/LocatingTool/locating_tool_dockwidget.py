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
    updateAttribute = QtCore.pyqtSignal(list)

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
        self.selectLayerCombo.activated.connect(self.setSelectedLayer)
        self.selectFireSeverityCombo.activated.connect(self.updateDistances)
        self.clearBuffersButton.clicked.connect(self.clearBuffers)

        # results tab
        self.updateAttribute.connect(self.extractAttributeSummary)

        # initialisation
        self.updateLayers()


    def openFire(self,filename=""):
        last_dir = uf.getLastDir("data_MCC")
        new_file = QtGui.QFileDialog.getOpenFileName(self, "", last_dir, "(*.qgs)")
        if new_file:
            self.iface.addProject(unicode(new_file))


    def updateLayers(self):
        layers = uf.getLegendLayers(self.iface, 'all', 'all')
        self.selectLayerCombo.clear()
        if layers:
            layer_names = uf.getLayersListNames(layers)
            self.selectLayerCombo.addItems(layer_names)
            self.setSelectedLayer()
        else:
            self.selectAttributeCombo.clear()
            # self.clearChart()

    def updateDistances(self):
        severity = self.selectFireSeverityCombo.currentText()
        if severity == 'GRIP 1':
            self.minDistLineEdit.setText(str(100))
            self.maxDistLineEdit.setText(str(750))
        elif severity == 'GRIP 2':
            self.minDistLineEdit.setText(str(250))
            self.maxDistLineEdit.setText(str(1000))
        elif severity == 'GRIP 3':
            self.minDistLineEdit.setText(str(400))
            self.maxDistLineEdit.setText(str(1250))
        elif severity == 'GRIP 4':
            self.minDistLineEdit.setText(str(500))
            self.maxDistLineEdit.setText(str(1250))
        elif severity == 'GRIP 5':
            self.minDistLineEdit.setText(str(500))
            self.maxDistLineEdit.setText(str(1500))

    def clearBuffers(self):
        buffer_layer = uf.getLegendLayerByName(self.iface, "Symmetrical difference")
        QgsMapLayerRegistry.instance().removeMapLayer(buffer_layer.id())

    def setSelectedLayer(self):
        # layer_name = self.selectLayerCombo.currentText()
        # layer = uf.getLegendLayerByName(self.iface,layer_name)
        self.setSelectedAttribute() #before: self.updateAttributes(layer)

    def getSelectedLayer(self):
        layer_name = self.selectLayerCombo.currentText()
        layer = uf.getLegendLayerByName(self.iface,layer_name)
        return layer


    def setSelectedAttribute(self):
        # TODO: 'ok_areas' should be changed to the final locations layer - global variable?
        layer = uf.getLegendLayerByName(self.iface, 'ok_areas')
        fields = uf.getFieldNames(layer)
        self.updateAttribute.emit(fields)

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

    def calculateDonut(self):
        #open layer
        layer = self.getSelectedLayer()

        #create the buffers needed min and max
        max_dist = self.getMaxBufferCutoff()
        min_dist = self.getMinBufferCutoff()
        MaxBuffer = processing.runalg('qgis:fixeddistancebuffer', layer, max_dist, 12, False, None)
        MinBuffer = processing.runalg('qgis:fixeddistancebuffer', layer, min_dist, 12, False, None)

        #create the donut (difference)
        donut = processing.runandload('qgis:symmetricaldifference', MaxBuffer['OUTPUT'], MinBuffer['OUTPUT'], None)

        self.refreshCanvas(donut)
    def chooseWindDirection(self):
        choosetext = self.chooseWindDirectionCombo.currentText()
        direction = {'no wind': -1, 'N': 0, 'NE': 45, 'E': 90, 'SE': 135, 'S': 180, 'SW': 225, 'W': 270, 'NW': 315}
        WindDirection = direction[choosetext]
        return WindDirection

    def selectFeaturesBuffer(self):
        layer = self.getSelectedLayer()
        intersect_layer = uf.getLegendLayerByName(self.iface, "Symmetrical difference")

        if layer and intersect_layer:
            uf.selectFeaturesByIntersection(layer, intersect_layer, True)

    def refreshCanvas(self, layer):
        if self.canvas.isCachingEnabled():
            layer.setCacheImage(None)
        else:
            self.canvas.refresh()

    #################
    #   Reporting tab
    #################

    def extractAttributeSummary(self, attribute):
        # get summary of the attribute
        # TODO: should layer (variable) be retrieved by name always?
        # TODO: 'ok_areas' should be changed to the final locations layer - global variable?
        layer = uf.getLegendLayerByName(self.iface, 'ok_areas')
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

