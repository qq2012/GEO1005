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
import processing

from . import utility_functions as uf

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'locating_tool_dockwidget_base.ui'))


class LocatingToolDockWidget(QtGui.QDockWidget, FORM_CLASS):

    closingPlugin = pyqtSignal()
    updateAttribute = QtCore.pyqtSignal(str)

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

#NEWNEWNEWNEWNEWNEWNEW
        self.iface.projectRead.connect(self.updateLayers)
        self.iface.newProjectCreated.connect(self.updateLayers)
        self.iface.legendInterface().itemRemoved.connect(self.updateLayers)
        self.iface.legendInterface().itemAdded.connect(self.updateLayers)
        self.chooseWindDirectionCombo.activated.connect(self.chooseWindDirection)
        self.selectInBufferButton.clicked.connect(self.selectFeaturesBuffer)
#NEWNEWNEWNEWNENEWNEW

        self.openFireButton.clicked.connect(self.openFire)
        self.minMaxBufferButton.clicked.connect(self.minMaxDist)
        self.selectLayerCombo.activated.connect(self.setSelectedLayer)

        # results tab
        self.updateAttribute.connect(self.extractAttributeSummary)

        # initialisation

#NEWNEWNEWNEWNEWNEWNEW
        self.updateLayers()
#NEWNEWNEWNEWNEWNEWNEW

    def openFire(self,filename=""):
        last_dir = uf.getLastDir("data_MCC")
        new_file = QtGui.QFileDialog.getOpenFileName(self, "", last_dir, "(*.qgs)")
        if new_file:
            self.iface.addProject(unicode(new_file))

    def minMaxDist(self):
        self.calculateBuffer('max')
        self.calculateBuffer('min')


#NEWNEWNEWNEWNEW
    def updateLayers(self):
        layers = uf.getLegendLayers(self.iface, 'all', 'all')
        #self.selectLayerCombo.clear()
        if layers:
            layer_names = uf.getLayersListNames(layers)
            self.selectLayerCombo.addItems(layer_names)
            self.setSelectedLayer()
        else:
            self.selectAttributeCombo.clear()
            self.clearChart()
#NEWNEWNEWNEWNEW


    def setSelectedLayer(self):
        layer_name = self.selectLayerCombo.currentText()
        layer = uf.getLegendLayerByName(self.iface,layer_name)
        #self.updateAttributes(layer)

    def getSelectedLayer(self):
        layer_name = self.selectLayerCombo.currentText()
        layer = uf.getLegendLayerByName(self.iface,layer_name)
        return layer

    def getBufferCutoff(self, minmax):
        if minmax == 'min':
            cutoff = self.minDistLineEdit.text()
        elif minmax == 'max':
            cutoff = self.maxDistLineEdit.text()
        if uf.isNumeric(cutoff):
            return uf.convertNumeric(cutoff)
        else:
            return 0

    def calculateBuffer(self, minmax):
        origins = self.getSelectedLayer().selectedFeatures()
        layer = self.getSelectedLayer()
        if minmax == 'min':
            buffer_layer_name = "MinDistBuffer"
        elif minmax == 'max':
            buffer_layer_name = "MaxDistBuffer"
        if origins > 0:
            cutoff_distance = self.getBufferCutoff(minmax)
            buffers = {}
            for point in origins:
                geom = point.geometry()
                buffers[point.id()] = geom.buffer(cutoff_distance,12).asPolygon()

            # store the buffer results in temporary layer called "Buffers"

            buffer_layer = uf.getLegendLayerByName(self.iface, buffer_layer_name)
            # create one if it doesn't exist
            if not buffer_layer:
                attribs = ['id', 'distance']
                types = [QtCore.QVariant.Int, QtCore.QVariant.Double]
                buffer_layer = uf.createTempLayer(buffer_layer_name,'POLYGON',layer.crs().postgisSrid(), attribs, types)
                uf.loadTempLayer(buffer_layer)
                buffer_layer.setLayerName(buffer_layer_name)
            # insert buffer polygons
            geoms = []
            values = []
            for buffer in buffers.iteritems():
                # each buffer has an id and a geometry
                geoms.append(buffer[1])
                # in the case of values, it expects a list of multiple values in each item - list of lists
                values.append([buffer[0],cutoff_distance])
            uf.insertTempFeatures(buffer_layer, geoms, values)
            self.refreshCanvas(buffer_layer)

    def chooseWindDirection(self):
        chooestext = self.chooseWindDirectionCombo.currentText()
        direction = {'no wind': -1, 'N': 0, 'NE': 45, 'E': 90, 'SE': 135, 'S': 180, 'SW': 225, 'W': 270, 'NW': 315}
        WindDirection = direction[chooestext]
        return WindDirection

    def selectFeaturesBuffer(self):
        layer = self.getSelectedLayer()
        max_buffer_layer = uf.getLegendLayerByName(self.iface, "MaxDistBuffer")
        min_buffer_layer = uf.getLegendLayerByName(self.iface, "MinDistBuffer")
        #diff_buffer_layer = processing.runandload('qgis:difference', max_buffer_layer, min_buffer_layer, None)

        #uf.selectFeaturesByIntersection(layer, diff_buffer_layer, True)
        #feat_max = uf.getFeaturesByIntersection(layer, max_buffer_layer, True)
        #feat_min = uf.getFeaturesByIntersection(layer, min_buffer_layer, True)
        #feat_end = []
        #for feat in feat_max:
        #    if feat not in feat_min:
        #        feat_end.append(feat)
        #uf.selectFeaturesByListValues(layer, 'id', feat_end)
        if max_buffer_layer and layer:
            uf.selectFeaturesByIntersection(layer, max_buffer_layer, True)
        #elif max_buffer_layer and layer and min_buffer_layer:
        #    uf.selectFeaturesByExpression(layer, uf.getFeaturesByIntersection(max_buffer_layer, min_buffer_layer, False))

        #elif max_buffer_layer and layer and min_buffer_layer:
        #    uf.selectFeaturesByIntersection(layer, uf.selectFeaturesByExpression(max_buffer_layer, min_buffer_layer, False), True

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
        layer = self.getSelectedLayer()
        uf.showMessage(self.iface, 'this is layer: {}'.format(layer), dur=10)
        summary = []
        # only use the first attribute in the list
        for feature in layer.getFeatures():
            summary.append((feature.id(), feature.attribute(attribute)))
        # send this to the table
        self.clearTable()
        self.updateTable(summary)

    # table window functions
    def updateTable(self, values):
        # takes a list of label / value pairs, can be tuples or lists. not dictionaries to control order
        self.locationTable.setColumnCount(2)
        self.locationTable.setHorizontalHeaderLabels(["Item","Value"])
        self.locationTable.setRowCount(len(values))
        for i, item in enumerate(values):
            # i is the table row, items must tbe added as QTableWidgetItems
            self.locationTable.setItem(i,0,QtGui.QTableWidgetItem(unicode(item[0])))
            self.locationTable.setItem(i,1,QtGui.QTableWidgetItem(unicode(item[1])))
        self.locationTable.horizontalHeader().setResizeMode(0, QtGui.QHeaderView.ResizeToContents)
        self.locationTable.horizontalHeader().setResizeMode(1, QtGui.QHeaderView.Stretch)
        self.locationTable.resizeRowsToContents()

    def clearTable(self):
        self.locationTable.clear()

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()

