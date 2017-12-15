# -*- coding: utf-8 -*-
"""
/***************************************************************************
 LocatingTool
                                 A QGIS plugin
 Finds suitable areas for a mobile control center
                             -------------------
        begin                : 2017-12-15
        copyright            : (C) 2017 by Group 2
        email                : group2@group2company.enterprise
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load LocatingTool class from file LocatingTool.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .locating_tool import LocatingTool
    return LocatingTool(iface)
