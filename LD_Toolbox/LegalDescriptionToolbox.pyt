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
            displayName="Netsuite Excel File Input",
            name="excelFile",
            datatype="DEFile",
            parameterType="Required",
            direction="Input")

        gisLayer = arcpy.Parameter(
            displayName="GIS Layer to Update (SLB Leases)",
            name="gisLayer",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input")

        outputFolder = arcpy.Parameter(
            displayName="Folder to Output .csv Audit File",
            name="outputFolder",
            datatype="DEFolder",
            parameterType="Required",
            direction="Input")

        # return [excelFile, outputFileLoc, outputFile, dateTag, outputFolder]
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

        excelFile = arcpy.GetParameterAsText(0)
        gisLayer = arcpy.GetParameterAsText(1)
        outputFolder = arcpy.GetParameterAsText(2)

        gdb = arcpy.env.workspace

        tool_script.main(excelFile, gdb, gisLayer, outputFolder)

        return
