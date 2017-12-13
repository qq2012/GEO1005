# -*- coding: utf-8 -*-
"""
/***************************************************************************
 MoveConmanderCentral
                                 A QGIS plugin
 MoveConmanderCentral plugin
                             -------------------
        begin                : 2017-12-13
        copyright            : (C) 2017 by AnnaQuRob
        email                : wangqu1993@hotmail.com
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
    """Load MoveConmanderCentral class from file MoveConmanderCentral.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .move_conmander_central import MoveConmanderCentral
    return MoveConmanderCentral(iface)
