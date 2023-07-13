# -*- coding: utf-8 -*-

import arcpy


class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [LegalDescriptionToFeature]


class LegalDescriptionToFeature(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Update GIS Layer"
        self.description = "Updates the GIS layer from input spreadsheet data"
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        excelFile = arcpy.Parameter(
            displayName="Excel file input",
            name="excelFile",
            datatype="DEFile",
            parameterType="Required",
            direction="Input")

        gisLayer = arcpy.Parameter(
            displayName="GIS Layer to be updated",
            name="gisLayer",
            datatype='DEFeatureClass',
            parameterType="Required",
            direction="Input")
        gisLayer.filter.list = ["Polygon"]

        outputFolder = arcpy.Parameter(
            displayName="Folder to output reports and logs",
            name="outputFolder",
            datatype="DEFolder",
            parameterType="Required",
            direction="Input")

        return [excelFile, gisLayer, outputFolder]

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        arcpy.AddMessage('Importing modules for the tool')
        import legal_description_to_feature_v2 as tool_script

        excelFile = parameters[0].valueAsText
        gisLayer = parameters[1].value
        outputFolder = parameters[2].valueAsText

        gdb = arcpy.env.workspace

        tool_script.main(excelFile, gdb, gisLayer, outputFolder)

        return
