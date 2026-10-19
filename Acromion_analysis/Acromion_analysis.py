import logging
import os
import csv
from typing import Annotated, Optional

import vtk
import numpy as np
import qt
import ctk

import slicer
from slicer.i18n import tr as _
from slicer.i18n import translate
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
from slicer.parameterNodeWrapper import (
    parameterNodeWrapper,
    WithinRange,
)

from slicer import vtkMRMLScalarVolumeNode


#
# Acromion_analysis
#


class Acromion_analysis(ScriptedLoadableModule):
    """Uses ScriptedLoadableModule base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = _("Acromion_analysis")

        self.parent.categories = [ "Custome_model"]
        self.parent.dependencies = []
        self.parent.contributors = ["Elise Joulain (UNIGE)"]
        self.parent.helpText = _("""
This module assists with placing fiducials on acromion X-rays and computing various
metrics.""")
        self.parent.acknowledgementText = _("""
Developed at UNIGE. Based on ScriptedLoadableModule examples from 3D Slicer.
This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc., Andras Lasso, PerkLab,
and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
""")
        slicer.app.connect("startupCompleted()", registerSampleData)


#
# Register sample data sets in Sample Data module
#


def registerSampleData():
    """Add data sets to Sample Data module."""
    try:
        import SampleData
    except Exception:
        return

    iconsPath = os.path.join(os.path.dirname(__file__), "Resources/Icons")

    SampleData.SampleDataLogic.registerCustomSampleDataSource(
        category="Acromion_analysis",
        sampleName="Acromion_analysis1",
        thumbnailFileName=os.path.join(iconsPath, "Acromion_analysis1.png"),
        # Download URL and target file name
        uris="https://github.com/Slicer/SlicerTestingData/releases/download/SHA256/998cb522173839c78657f4bc0ea907cea09fd04e44601f17c82ea27927937b95",
        fileNames="Acromion_analysis1.nrrd",
        checksums="SHA256:998cb522173839c78657f4bc0ea907cea09fd04e44601f17c82ea27927937b95",
        nodeNames="Acromion_analysis1",
    )


    SampleData.SampleDataLogic.registerCustomSampleDataSource(
        category="Acromion_analysis",
        sampleName="Acromion_analysis2",
        thumbnailFileName=os.path.join(iconsPath, "Acromion_analysis2.png"),
        uris="https://github.com/Slicer/SlicerTestingData/releases/download/SHA256/1a64f3f422eb3d1c9b093d1a18da354b13bcf307907c66317e2463ee530b7a97",
        fileNames="Acromion_analysis2.nrrd",
        checksums="SHA256:1a64f3f422eb3d1c9b093d1a18da354b13bcf307907c66317e2463ee530b7a97",
        nodeNames="Acromion_analysis2",
    )


#
# Acromion_analysisParameterNode
#


@parameterNodeWrapper
class Acromion_analysisParameterNode:


    inputVolume: vtkMRMLScalarVolumeNode
    imageThreshold: Annotated[float, WithinRange(-100, 500)] = 100
    invertThreshold: bool = False
    thresholdedVolume: vtkMRMLScalarVolumeNode
    invertedVolume: vtkMRMLScalarVolumeNode


#
# Acromion_analysisWidget
#


class Acromion_analysisWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):


    def __init__(self, parent=None) -> None:
        """Called when the user opens the module the first time and the widget is initialized."""
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)
        self.logic = None
        self._parameterNode = None
        self._parameterNodeGuiTag = None

    def setup(self) -> None:
        ScriptedLoadableModuleWidget.setup(self)

        nativeLabels = {
            "P1": "TODO",
            "P2": "TODO",
            "P3": "TODO",

        }

        self.fiducialLabelsByMode = {
            "native": nativeLabels,
        }
        self._activeMode = "native"  # default
        self.fiducialLabels = self.fiducialLabelsByMode[self._activeMode]

        formLayout = qt.QFormLayout()
        self.layout.addLayout(formLayout)

        # Input volume selector
        self.inputVolumeSelector = slicer.qMRMLNodeComboBox()
        self.inputVolumeSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
        self.inputVolumeSelector.setMRMLScene(slicer.mrmlScene)
        self.inputVolumeSelector.currentNodeChanged.connect(self.onInputVolumeChanged)
        self.layout.addWidget(qt.QLabel("Choose the volume on which you want to work:"))
        self.layout.addWidget(self.inputVolumeSelector)

        # Cosmetic style
        self.inputVolumeSelector.setStyleSheet("""
                            QComboBox {
                                background-color: #587880;
                                color: #587880;
                                font-weight: bold;
                                border: 1px solid #00796B;
                                padding: 3px;
                                border-radius: 4px;
                            }
                        """)

        # Side selection
        self.selectionCollapsibleButton = ctk.ctkCollapsibleButton()
        self.selectionCollapsibleButton.text = "Enter the side of the inspected shoulder"
        self.layout.addWidget(self.selectionCollapsibleButton)
        self.selectionFormLayout = qt.QFormLayout(self.selectionCollapsibleButton)
        self.sideSelector = qt.QComboBox()
        self.sideSelector.addItem("Right")
        self.sideSelector.addItem("Left")
        self.selectionFormLayout.addRow("Select Side:", self.sideSelector)

        # Analysis type: native (default) or Reverse prosthesis - different landmarks and different computations.
        self.xrayTypeSelector = qt.QComboBox()
        self.xrayTypeSelector.addItem("native")
        self.xrayTypeSelector.addItem("Reverse prosthesis")
        self.xrayTypeSelector.setCurrentIndex(0)
        self.xrayTypeSelector.setToolTip(
            "native: 18 landmarks. Reverse prosthesis: 20 landmarks "
            "(humeral component, glenoid sphere base and peg points)."
        )
        self.selectionFormLayout.addRow("Analysis type:", self.xrayTypeSelector)
        self.xrayTypeSelector.currentIndexChanged.connect(self.onXrayTypeChanged)

        # Patient ID input
        self.patientIdLineEdit = qt.QLineEdit()
        self.patientIdLineEdit.setPlaceholderText("Enter patient ID")
        formLayout.addRow("Patient ID:", self.patientIdLineEdit)

        # Output folder selector
        self.outputDirectoryButton = ctk.ctkPathLineEdit()
        self.outputDirectoryButton.filters = ctk.ctkPathLineEdit.Dirs
        self.outputDirectoryButton.setToolTip("Select folder where results will be saved")
        self.outputDirectoryButton.currentPath = slicer.app.temporaryPath

        formLayout.addRow("Output folder:", self.outputDirectoryButton)

        # PDF for placement of the fiducial point
        self.instructionsButton = qt.QPushButton("View placement guide (PDF)")
        self.instructionsButton.setToolTip("Open the fiducial placement instructions")
        self.instructionsButton.clicked.connect(self.onOpenInstructionsPDF)
        self.layout.addWidget(self.instructionsButton)

        # Fiducial table
        self.fiducialTableCollapsible = ctk.ctkCollapsibleButton()
        self.fiducialTableCollapsible.text = "Here a table guiding the position of the needed fiducials nodes for the analysis"
        self.layout.addWidget(self.fiducialTableCollapsible)
        self.fiducialTableLayout = qt.QVBoxLayout(self.fiducialTableCollapsible)

        self.fiducialTable = qt.QTableWidget()
        self.fiducialTable.setRowCount(len(self.fiducialLabels))
        self.fiducialTable.setColumnCount(2)
        self.fiducialTable.setHorizontalHeaderLabels(["ID", "Description"])
        self.fiducialTable.horizontalHeader().setStretchLastSection(True)
        self.fiducialTable.verticalHeader().visible = False
        self.fiducialTable.setEditTriggers(qt.QAbstractItemView.NoEditTriggers)

        self.populateFiducialTable()

        self.fiducialTableLayout.addWidget(self.fiducialTable)

        # Analysis section
        self.acromion_spaceGroup = ctk.ctkCollapsibleButton()
        self.acromion_spaceGroup.text = "Analysis of the image"
        self.layout.addWidget(self.acromion_spaceGroup)
        self.acromion_spaceLayout = qt.QVBoxLayout(self.acromion_spaceGroup)
        self.acromion_spaceGroup.setStyleSheet("background-color: #587880; color: white;")

        self.acromion_spacePlaceButton = qt.QPushButton("Place fiducials nodes")
        self.acromion_spacePlaceButton.connect('clicked(bool)', lambda: self.onPlaceFiducial("acromion_space"))
        self.acromion_spaceLayout.addWidget(self.acromion_spacePlaceButton)

        self.acromion_spaceComputeButton = qt.QPushButton("Compute parameters")
        self.acromion_spaceComputeButton.connect('clicked(bool)', lambda: self.onCalculateMetrics("acromion_space"))
        self.acromion_spaceLayout.addWidget(self.acromion_spaceComputeButton)

        # --- Toggle fiducial labels ---
        self.toggleLabelsButton = qt.QPushButton("Hide/Show Fiducial Labels")
        self.toggleLabelsButton.setStyleSheet("background-color: green; color: white;")
        self.toggleLabelsButton.toolTip = "Hide or show all fiducial labels in the scene"
        self.toggleLabelsButton.connect('clicked(bool)', self.onToggleFiducialLabels)
        self.acromion_spaceLayout.addWidget(self.toggleLabelsButton)

        # Reset button
        self.resetFiducialsButton = qt.QPushButton("Reset fiducials nodes")
        self.resetFiducialsButton.toolTip = "Remove all fiducial nodes"
        self.resetFiducialsButton.connect('clicked(bool)', self.onResetFiducials)
        self.acromion_spaceLayout.addWidget(self.resetFiducialsButton)

        # Layout margins and spacing
        self.acromion_spaceLayout.setContentsMargins(2, 2, 2, 2)
        self.acromion_spaceLayout.setSpacing(3)
        self.layout.setSpacing(3)
        self.layout.setContentsMargins(2, 2, 2, 2)

        # Initialize logic
        self.logic = acromion_space_anaLogic()

    # ---------- Callbacks and helper methods ----------
    def onInputVolumeChanged(self, volumeNode):
        if volumeNode:
            slicer.util.setSliceViewerLayers(background=volumeNode, fit=True)

    def onLoadDICOM(self):
        slicer.util.selectModule("DICOM")
        qt.QMessageBox.information(slicer.util.mainWindow(), "DICOM Import",
                                   "The DICOM browser has been opened.\nLoad your X-ray image, then return here to place fiducials.")

    # ---------- Analysis type (native / Reverse prosthesis) ----------
    def currentXrayType(self):
        """Return 'native'."""
        if getattr(self, "xrayTypeSelector", None) is not None:
            return self.xrayTypeSelector.currentText
        return "native"

    def populateFiducialTable(self):
        """(Re)fill the guide table with the landmarks of the active analysis type."""
        self.fiducialTable.setRowCount(len(self.fiducialLabels))
        for i, (fidID, label) in enumerate(self.fiducialLabels.items()):
            self.fiducialTable.setItem(i, 0, qt.QTableWidgetItem(fidID))
            self.fiducialTable.setItem(i, 1, qt.QTableWidgetItem(label))

    def clearFiducialsAndOverlays(self):
        """Remove the placed fiducials and every drawn line / circle / arc."""
        scene = slicer.mrmlScene
        for node in list(scene.GetNodesByClass("vtkMRMLMarkupsFiducialNode")):
            if "acromion_space" in (node.GetName() or "").lower():
                scene.RemoveNode(node)
        for node in list(scene.GetNodesByClass("vtkMRMLMarkupsLineNode")):
            scene.RemoveNode(node)
        for node in list(scene.GetNodesByClass("vtkMRMLMarkupsCurveNode")):
            scene.RemoveNode(node)
        self.markupNode = None

    def onXrayTypeChanged(self, index):
        newMode = self.xrayTypeSelector.currentText
        if newMode == self._activeMode or not hasattr(self, "fiducialTable"):
            return

        node = slicer.mrmlScene.GetFirstNodeByName("Fiducials_acromion_space")
        hasWork = node is not None and node.GetNumberOfControlPoints() > 0
        if hasWork and not slicer.util.confirmYesNoDisplay(
                "The two analysis types use different landmarks.\n"
                "Changing it erases the fiducials placed so far and all drawn lines. Continue?"):
            # revert the selector without triggering this handler again
            self.xrayTypeSelector.blockSignals(True)
            self.xrayTypeSelector.setCurrentIndex(self.xrayTypeSelector.findText(self._activeMode))
            self.xrayTypeSelector.blockSignals(False)
            return

        self.clearFiducialsAndOverlays()
        self._activeMode = newMode
        self.fiducialLabels = self.fiducialLabelsByMode[newMode]
        self.populateFiducialTable()
        slicer.util.showStatusMessage(f"Analysis type: {newMode}", 3000)

    def onResetFiducials(self):
        scene = slicer.mrmlScene

        if not slicer.util.confirmYesNoDisplay("Are you sure you want to remove all fiducial nodes?"):
            return

        for node in list(scene.GetNodesByClass("vtkMRMLMarkupsFiducialNode")):
            name = node.GetName() or ""
            if "acromion_space" in name.lower():
                scene.RemoveNode(node)
        for node in scene.GetNodesByClass("vtkMRMLMarkupsLineNode"):
            scene.RemoveNode(node)
        for node in scene.GetNodesByClass("vtkMRMLMarkupsCurveNode"):
            scene.RemoveNode(node)

    def onPlaceFiducial(self, timepoint: str):
        """Clear any previous fiducials/overlays for this timepoint, then
                activate placement of a fresh set."""
        nodeName = f"Fiducials_{timepoint}"
        scene = slicer.mrmlScene

        # Remove the existing fiducial node for this timepoint, if any
        existingNode = scene.GetFirstNodeByName(nodeName)
        if existingNode:
            scene.RemoveNode(existingNode)

        # Remove all drawn overlays (axis/angle lines, circles, arcs)
        for node in list(scene.GetNodesByClass("vtkMRMLMarkupsLineNode")):
            scene.RemoveNode(node)
        for node in list(scene.GetNodesByClass("vtkMRMLMarkupsCurveNode")):
            scene.RemoveNode(node)

        # Create a fresh fiducial node
        self.markupNode = scene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode", nodeName)
        self.markupNode.AddObserver(slicer.vtkMRMLMarkupsNode.PointAddedEvent, self.onFiducialAdded)

        displayNode = self.markupNode.GetDisplayNode()
        displayNode.SetSelectedColor(0, 1, 0)  # green
        displayNode.SetUseGlyphScale(False)
        displayNode.SetGlyphSize(2)

        # Start place mode (1 point at a time)
        slicer.modules.markups.logic().StartPlaceMode(1)

    def onFiducialAdded(self, caller, event):
        """Automatically label new fiducials P1..PN up to the number of labels provided."""
        n = caller.GetNumberOfControlPoints()
        if n <= len(self.fiducialLabels):
            fidName = f"P{n}"
            caller.SetNthControlPointLabel(n - 1, fidName)

            # Guide line for the scapular neck point
            if self.currentXrayType() == "native" and n == len(self.fiducialLabels) - 1:
                self.drawGuideLineForNeckPoint(caller)

        else:
            # Stop placement if too many points
            interactionNode = slicer.app.applicationLogic().GetInteractionNode()
            interactionNode.SetCurrentInteractionMode(slicer.vtkMRMLInteractionNode.ViewTransform)
            slicer.util.showStatusMessage("Maximum fiducials placed — placement stopped.", 3000)

    def onExportFiducials(self, timepoint: str):

        nodeName = f"Fiducials_{timepoint}"
        node = slicer.mrmlScene.GetFirstNodeByName(nodeName)

        if not node:
            slicer.util.errorDisplay(f"No fiducials placed for {timepoint}")
            return

        # --- Check metrics exist ---
        if not hasattr(self, "currentMetrics"):
            slicer.util.errorDisplay("Please compute metrics before exporting.")
            return

        outputDir = qt.QFileDialog.getExistingDirectory(
            slicer.util.mainWindow(),
            "Select output folder"
        )

        if not outputDir:
            slicer.util.showStatusMessage("Export cancelled.", 2000)
            return

        # --- Patient ID ---
        patientID = self.patientIdLineEdit.text.strip()
        if not patientID:
            slicer.util.errorDisplay("Please enter a patient ID before exporting.")
            return

        try:
            self.logic.saveCombinedCSV(node, self.currentMetrics, patientID, timepoint, outputDir)

            slicer.util.showStatusMessage("Fiducials + metrics saved successfully!", 5000)

        except Exception as e:
            slicer.util.errorDisplay(f"Export failed: {e}")

    def onOpenInstructionsPDF(self):
        try:
            moduleDir = os.path.dirname(__file__)
            pdfName = "Guide_Placement.pdf"
            if self.currentXrayType() == "Reverse prosthesis":
                # optional dedicated guide; falls back to the standard one if absent
                if os.path.exists(os.path.join(moduleDir, "Resources", "Guide_Placement_Reverse.pdf")):
                    pdfName = "Guide_Placement_Reverse.pdf"
            pdfPath = os.path.join(moduleDir, "Resources", pdfName)

            if not os.path.exists(pdfPath):
                slicer.util.errorDisplay("PDF file not found.")
                return

            qt.QDesktopServices.openUrl(qt.QUrl.fromLocalFile(pdfPath))

        except Exception as e:
            slicer.util.errorDisplay(f"Failed to open PDF: {str(e)}")

    def onCalculateMetrics(self, timepoint: str):
        """Compute the metrics of the selected analysis type, show them and export.

        native (18 landmarks)        -> computenativeMetrics
        Reverse prosthesis (20 landmarks) -> computeReverseMetrics
        """
        nodeName = f"Fiducials_{timepoint}"
        scene = slicer.mrmlScene
        markupNode = scene.GetFirstNodeByName(nodeName)

        if not markupNode:
            slicer.util.errorDisplay(f"No fiducials placed for {timepoint}")
            return

        patientID = self.patientIdLineEdit.text.strip()
        if not patientID:
            slicer.util.errorDisplay("Please enter a patient ID.")
            return

        points = self.logic.get_fiducial_positions(markupNode)
        if len(points) < len(self.fiducialLabels):
            slicer.util.errorDisplay(f"Not enough fiducials (required: {len(self.fiducialLabels)}).")
            return
        for label in points:
            points[label]['z'] = 0

        # Remove all drawn overlays (axis/angle lines, circles, arcs)
        for node in list(scene.GetNodesByClass("vtkMRMLMarkupsLineNode")):
            scene.RemoveNode(node)
        for node in list(scene.GetNodesByClass("vtkMRMLMarkupsCurveNode")):
            scene.RemoveNode(node)

        if self.currentXrayType() == "Reverse prosthesis":
            metrics, text = self.computeReverseMetrics(points, patientID)
        else:
            metrics, text = self.computenativeMetrics(points, patientID)
        if metrics is None:
            return

        self.currentMetrics = metrics
        self.showTextInSliceViews(text)
        self.exportAfterCompute(markupNode, metrics, patientID, timepoint)

    def computenativeMetrics(self, points, patientID):
        try:
            P = {f"P{i}": np.array([points[f"P{i}"]['x'], points[f"P{i}"]['y'], 0.0])
                 for i in range(1, 24)}
            m = self.logic.compute_native_metrics(P)
        except Exception as e:
            slicer.util.errorDisplay(f"Native analysis failed: {e}\n"
                                     "Check the placement of the points.")
            return None, None

        text = (
            f"Patient: {patientID}  (native)\n"
            f"-------------------------\n"
            f"acromion_space : {_fmt(m['acromion_space'], '°')}\n"

        )
        return m, text

    def showTextInSliceViews(self, text):
        """Display the results in the corner of the slice views."""
        layoutManager = slicer.app.layoutManager()

        for viewName in ["Red", "Yellow", "Green"]:
            sliceWidget = layoutManager.sliceWidget(viewName)
            if sliceWidget:
                sliceView = sliceWidget.sliceView()
                cornerAnnotation = sliceView.cornerAnnotation()
                cornerAnnotation.SetText(vtk.vtkCornerAnnotation.UpperLeft, text)
                sliceView.forceRender()

    def exportAfterCompute(self, markupNode, metrics, patientID, timepoint):
        """Ask for a folder and save fiducials + metrics right after computing."""
        outputDir = qt.QFileDialog.getExistingDirectory(
            slicer.util.mainWindow(),
            "Select output folder",
            self.outputDirectoryButton.currentPath
        )

        if not outputDir:
            slicer.util.showStatusMessage("Export cancelled.", 2000)
            return

        try:
            self.logic.saveCombinedCSV(markupNode, metrics, patientID, timepoint, outputDir)
            slicer.util.showStatusMessage("Fiducials + metrics saved successfully!", 5000)
        except Exception as e:
            slicer.util.errorDisplay(f"Export failed: {e}")


    def onToggleFiducialLabels(self):
        """Toggle fiducial labels visibility."""
        # Check first node to decide current state
        scene = slicer.mrmlScene
        fidNodes = scene.GetNodesByClass("vtkMRMLMarkupsFiducialNode")
        if not fidNodes:
            slicer.util.showStatusMessage("No fiducial nodes in the scene.", 2000)
            return

        displayNode = fidNodes.GetItemAsObject(0).GetDisplayNode()
        if not displayNode:
            return

        currentVisibility = displayNode.GetPointLabelsVisibility()
        newVisibility = not currentVisibility

        self.setFiducialLabelsVisible(newVisibility)

        if newVisibility:
            slicer.util.showStatusMessage("Fiducial labels shown.", 2000)
        else:
            slicer.util.showStatusMessage("Fiducial labels hidden.", 2000)

    def setFiducialLabelsVisible(self, visible: bool = True):
        """Show or hide all fiducial labels in the scene."""
        scene = slicer.mrmlScene
        for node in scene.GetNodesByClass("vtkMRMLMarkupsFiducialNode"):
            displayNode = node.GetDisplayNode()
            if displayNode:
                displayNode.SetPointLabelsVisibility(visible)
                displayNode.SetPropertiesLabelVisibility(visible)
                node.Modified()

#
# Acromion_analysisLogic
#


class Acromion_analysisLogic(ScriptedLoadableModuleLogic):
    """Logic class for data processing, angle computation, and visualization."""

    def __init__(self):
        super().__init__()

    # --- Fiducial retrieval ---
    def get_fiducial_positions(self, markupNode):
        """Return a dict of fiducial positions keyed by label {P1: {x,y,z}, ...}."""
        points = {}
        if not markupNode:
            return points
        for i in range(markupNode.GetNumberOfControlPoints()):
            label = markupNode.GetNthControlPointLabel(i)
            pos = [0.0, 0.0, 0.0]
            markupNode.GetNthControlPointPosition(i, pos)
            points[label] = {"x": pos[0], "y": pos[1], "z": pos[2]}
        return points

    # --- Save fiducials + metrics together in a single CSV file ---
    def saveCombinedCSV(self, markupNode, metrics, patientID, timepoint, outputDir):
        """
        Write a single CSV file containing two sections:
          1) FIDUCIALS  - one row per fiducial point (ID, Label, X, Y, Z)
          2) PARAMETERS - one row per computed metric (Metric, Value)
        The two sections are separated by a blank line and a section header.
        """
        if not os.path.exists(outputDir):
            slicer.util.errorDisplay("Selected output folder does not exist.")
            return

        fileName = f"{patientID}_{timepoint}_combined.csv"
        filePath = os.path.join(outputDir, fileName)

        try:
            points = self.get_fiducial_positions(markupNode)

            with open(filePath, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)

                # --- Section 1: Fiducials ---
                writer.writerow(["FIDUCIALS"])
                writer.writerow(["ID", "Label", "X", "Y", "Z"])
                for i in range(markupNode.GetNumberOfControlPoints()):
                    label = markupNode.GetNthControlPointLabel(i)
                    pos = points.get(label, {"x": "", "y": "", "z": ""})
                    writer.writerow([i + 1, label, pos["x"], pos["y"], pos["z"]])

                # --- Blank line between sections ---
                writer.writerow([])

                # --- Section 2: Parameters ---
                writer.writerow(["PARAMETERS"])
                writer.writerow(["Metric", "Value"])
                for key, value in metrics.items():
                    if isinstance(value, (list, tuple, np.ndarray)):
                        value_str = ";".join(str(v) for v in np.array(value).flatten())
                    else:
                        value_str = str(value)
                    writer.writerow([key, value_str])

            slicer.util.showStatusMessage(f"Fiducials + metrics saved to: {filePath}", 5000)

        except PermissionError:
            slicer.util.errorDisplay("Permission denied. Please choose another folder.")
        except Exception as e:
            slicer.util.errorDisplay(f"Failed to save combined CSV: {e}")

    def compute_native_metrics(self, P):

        return {
            "xray_type": "Native",

        }


