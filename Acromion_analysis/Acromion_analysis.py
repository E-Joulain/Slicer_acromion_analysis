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


def _fmt(v, unit=""):
    try:
        return f"{float(v):.1f}{unit}"
    except (TypeError, ValueError):
        return str(v)


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
            "P1": "point supérieur de la surface claviculaire SC",
            "P2": "point inférieur de la surface claviculaire SC",
            "P3": "Le point à mi-distance entre point 1 et point 2 (centre versant claviculaire Sc)",
            "P4": "point supérieur de la surface claviculaire AC",
            "P5": "point inférieur de la surface claviculaire AC",
            "P6": "point à mi-distance entre point 4 et point 5 sur le versant claviculaire l’AC",
            "P7": "point supérieur de la surface acromiale de l’AC ",
            "P8": "point inflrieur de la surface acromiale de l’AC",
            "P9": "point à mi-distance entre point 7 et point 9 sur le versant acromial de l’AC",
            "P10": "point sur la fosse supra-épineuse à l’intersection entre la coracoïde et la fosse sus-épineuse.",
            "P11": "Le point sur la partie médiale de la fosse sus-épineuse.",
            "P12": "point à mi-distance entre point 10 et point 11, sur la fosse sus-épineuse",
            "P13": "point de la coracoïde qui est le plus proche de la clavicule",
            "P14": "point à l’intersection avec le rebord inférieur de la clavicule et la ligne jaune qui est apparue sur l'image "
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

        # Analysis type: native (default) or native prosthesis - different landmarks and different computations.
        self.xrayTypeSelector = qt.QComboBox()
        self.xrayTypeSelector.addItem("native")
        self.xrayTypeSelector.addItem("native prosthesis")
        self.xrayTypeSelector.setCurrentIndex(0)
        self.xrayTypeSelector.setToolTip(
            "native: 18 landmarks. native prosthesis: 20 landmarks "
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

    # ---------- Analysis type (native / native prosthesis) ----------
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
        displayNode.SetGlyphSize(6)

        # Start place mode (1 point at a time)
        slicer.modules.markups.logic().StartPlaceMode(1)

    def onFiducialAdded(self, caller, event):
        """Automatically label new fiducials P1..PN up to the number of labels provided."""
        n = caller.GetNumberOfControlPoints()
        nMax = len(self.fiducialLabels)

        if n <= nMax:
            fidName = f"P{n}"
            caller.SetNthControlPointLabel(n - 1, fidName)

            # 13 points sur 14 : fit P10-P11-P12 + perpendiculaire passant par P13
            if self.currentXrayType() == "native" and n == nMax:
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
            if self.currentXrayType() == "native prosthesis":
                # optional dedicated guide; falls back to the standard one if absent
                if os.path.exists(os.path.join(moduleDir, "Resources", "Guide_Placement_native.pdf")):
                    pdfName = "Guide_Placement_native.pdf"
            pdfPath = os.path.join(moduleDir, "Resources", pdfName)

            if not os.path.exists(pdfPath):
                slicer.util.errorDisplay("PDF file not found.")
                return

            qt.QDesktopServices.openUrl(qt.QUrl.fromLocalFile(pdfPath))

        except Exception as e:
            slicer.util.errorDisplay(f"Failed to open PDF: {str(e)}")

    def onCalculateMetrics(self, timepoint: str):
        """Compute the metrics of the selected analysis type, show them and export.
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

        if self.currentXrayType() == "native":
            metrics, text = self.computenativeMetrics(points, patientID)
        else:
            return

        self.currentMetrics = metrics
        slicer.util.showStatusMessage(metrics, 5000)
        self.showTextInSliceViews(text)
        self.exportAfterCompute(markupNode, metrics, patientID, timepoint)

    def computenativeMetrics(self, points, patientID):
        try:
            P = {f"P{i}": np.array([points[f"P{i}"]['x'], points[f"P{i}"]['y'], 0.0])
                 for i in range(1, 15)}
            m = self.logic.compute_native_metrics(P)
        except Exception as e:
            slicer.util.errorDisplay(f"Native analysis failed: {e}\n"
                                     "Check the placement of the points.")
            return None, None

        text = (
            f"Patient: {patientID}  (native)\n"
            f"-------------------------\n"
            f"Angle axe scapulaire / axe claviculaire : {_fmt(m['angle_scap_clav'], '°')}\n"
            f"Longueur axe claviculaire : {_fmt(m['clavicular_axis_length'], ' px')}\n"
            f"SC (P1-P2-P3) : {m['SC_shape']} ({_fmt(m['SC_deviation'], ' px')})\n"
            f"AC claviculaire (P4-P5-P6) : {m['AC_clav_shape']} ({_fmt(m['AC_clav_deviation'], ' px')})\n"
            f"AC acromiale (P7-P8-P9) : {m['AC_acro_shape']} ({_fmt(m['AC_acro_deviation'], ' px')})\n"
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

    # --- add guide line ---
    def drawGuideLineForNeckPoint(self, markupNode):
        """Fit TLS sur P10-P11-P12, puis trace la perpendiculaire passant par P13
        pour guider le placement de P14."""
        pts = self.logic.get_fiducial_positions(markupNode)
        try:
            p10, p11, p12, p13 = (np.array([pts[k]["x"], pts[k]["y"]]) for k in ("P10", "P11", "P12", "P13"))
        except KeyError:
            slicer.util.errorDisplay("P10, P11, P12 and P13 are needed to draw the guide line.")
            return

        centroid, d = self.logic.fit_line_tls([p10, p11, p12])  # droite fittée (2D)
        perp = np.array([-d[1], d[0]])  # perpendiculaire (2D)
        z = pts["P13"]["z"]

        # longueur de la ligne : diagonale du volume, sinon valeur par défaut
        half = 500.0
        vol = self.inputVolumeSelector.currentNode()
        if vol:
            b = [0.0] * 6
            vol.GetBounds(b)
            half = max(b[1] - b[0], b[3] - b[2], 1.0)

        # droite fittée (cyan) et perpendiculaire par P13 (jaune)
        self._addGuideLine("Guide_fit_P10_P11_P12", centroid - d * half, centroid + d * half, (0.0, 1.0, 1.0), z)
        self._addGuideLine("Guide_perpendicular_P13", p13 - perp * half, p13 + perp * half, (1.0, 1.0, 0.0), z)

        self._guide = (p13.copy(), perp.copy())

        slicer.util.warningDisplay(
            "The guide line (perpendicular to the P10-P11-P12 fit, through P13) is now displayed.\n\n"
            "Place P14 on this line. It will be snapped onto it.\n\n"
            "WARNING: once P14 is placed, this perpendicular cannot be redrawn unless P10, P11 and P12 "
            "are placed again, together with ALL the other points. The whole landmark placement "
            "would then have to be redone.",
            windowTitle="Placement of P14")

        selectionNode = slicer.app.applicationLogic().GetSelectionNode()
        selectionNode.SetActivePlaceNodeClassName(markupNode.GetClassName())
        selectionNode.SetActivePlaceNodeID(markupNode.GetID())
        slicer.modules.markups.logic().StartPlaceMode(1)


    def _resumePlacement(self, markupNode):
            """Recréer des noeuds markups change le noeud actif de placement : on le restaure
            pour pouvoir continuer à poser P14 dans le noeud de fiducials."""
            appLogic = slicer.app.applicationLogic()
            selectionNode = appLogic.GetSelectionNode()
            selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")
            selectionNode.SetActivePlaceNodeID(markupNode.GetID())
            interactionNode = appLogic.GetInteractionNode()
            interactionNode.SetPlaceModePersistence(1)
            interactionNode.SetCurrentInteractionMode(interactionNode.Place)
            dn = markupNode.GetDisplayNode()
            if dn:
                dn.SetVisibility(True)
            markupNode.SetLocked(False)

    def _addGuideLine(self, name, p0, p1, color, z):
        node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsLineNode", name)
        node.AddControlPoint(float(p0[0]), float(p0[1]), float(z))
        node.AddControlPoint(float(p1[0]), float(p1[1]), float(z))
        node.SetLocked(True)  # pas déplaçable à la souris
        dn = node.GetDisplayNode()
        if dn:
            dn.SetSelectedColor(*color)
            dn.SetColor(*color)
            dn.SetPointLabelsVisibility(False)
            dn.SetPropertiesLabelVisibility(False)
        return node

    def drawScapClavAngle(self, m, z=0.0):
        """Trace les deux demi-droites et l'arc de l'angle scapulaire/claviculaire."""
        if m.get("axes_vertex") is None:
            slicer.util.showStatusMessage("Scapular and clavicular axes are parallel: no angle to draw.", 3000)
            return

        vertex = np.array(m["axes_vertex"], dtype=float)
        scap_center = np.array(m["scap_center"], dtype=float)
        scap_dir = np.array(m["scapular_axis_dir"], dtype=float)
        clav_dir = np.array(m["clavicular_axis_dir"], dtype=float)
        clav_mid = (np.array(m["clav_start"]) + np.array(m["clav_end"])) / 2.0

        # rayon 1 : de l'intersection vers le côté où se trouvent les points scapulaires
        u = scap_center - vertex
        u = u / np.linalg.norm(u) if np.linalg.norm(u) > 1e-9 else scap_dir
        # rayon 2 : direction claviculaire orientée pour que l'angle soit aigu
        v = clav_dir if np.dot(u, clav_dir) >= 0 else -clav_dir

        R = 0.3 * m["clavicular_axis_length"]  # rayon de l'arc
        L = max(np.linalg.norm(scap_center - vertex),
                np.linalg.norm(clav_mid - vertex), 1.5 * R)  # longueur des demi-droites

        V3 = lambda p: np.array([p[0], p[1], z])

        # demi-droites (axes)
        self._addGuideLine("Angle_scap_axis", vertex, vertex + u * L, (0.0, 1.0, 1.0), z)
        self._addGuideLine("Angle_clav_axis", vertex, vertex + v * L, (1.0, 0.5, 0.0), z)

        # arc : p1 / p2 à distance R du sommet, angle = angle aigu calculé
        self.logic.draw_arc(
            V3(vertex), V3(vertex + u * R), V3(vertex + v * R),
            m["angle_scap_clav"],
            name="Angle_scap_clav", color=(1, 1, 0), thickness=1.2, num_points=30,
        )


#
# Acromion_analysisLogic
#


class acromion_space_anaLogic(ScriptedLoadableModuleLogic):
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

    # --- Featuring of the parameters ---
    def fit_line_tls(self, points):
        """Total least-squares line fit. Returns (centroid, unit_direction)."""
        pts = np.asarray(points, dtype=float)
        centroid = pts.mean(axis=0)
        _, _, vt = np.linalg.svd(pts - centroid, full_matrices=False)
        direction = vt[0]
        return centroid, direction / np.linalg.norm(direction)

    def _curvature(self, p_a, p_b, p_mid, p_ref):
        """Détermine si la surface (p_a, p_mid, p_b) est convexe ou concave.

        p_mid est le point central de la surface, p_a / p_b ses extrémités.
        p_ref est un point situé à l'intérieur de l'os portant la surface.
        - convexe : p_mid est du côté opposé à p_ref par rapport à la corde a-b
                    (la surface bombe vers l'extérieur de l'os)
        - concave : p_mid est du même côté que p_ref
        Retourne (label, déviation_signée_mm) ; déviation > 0 => convexe.
        """
        a, b, m, r = (np.asarray(p, dtype=float)[:2] for p in (p_a, p_b, p_mid, p_ref))
        chord = b - a
        n = np.linalg.norm(chord)
        if n < 1e-9:
            return "indéterminé", 0.0

        def side(p):  # distance signée à la corde
            return (chord[0] * (p[1] - a[1]) - chord[1] * (p[0] - a[0])) / n

        s_mid, s_ref = side(m), side(r)
        dev = -np.sign(s_ref) * s_mid  # >0 : m est à l'opposé de ref
        if abs(dev) < 1e-6:
            return "plat", 0.0
        return ("convexe" if dev > 0 else "concave"), float(dev)


    def compute_native_metrics(self, P):
        P = {k: np.asarray(v, dtype=float) for k, v in P.items()}

        def mid(a, b):
            return (P[a] + P[b]) / 2.0

        # --- Axe scapulaire (fosse sus-épineuse) ---
        scap_center, scap_dir = self.fit_line_tls(
            [P["P11"][:2], P["P10"][:2], P["P12"][:2]]
        )

        # --- Axe claviculaire : milieu(P1,P2) -> milieu(P8,P9) ---
        clav_start = mid("P1", "P2")[:2]
        clav_end = mid("P8", "P9")[:2]
        clav_vec = clav_end - clav_start
        clav_len = float(np.linalg.norm(clav_vec))
        clav_dir = clav_vec / clav_len if clav_len > 1e-9 else np.array([1.0, 0.0])

        # --- Angle entre axe scapulaire et axe claviculaire ---
        cos_a = np.clip(np.dot(scap_dir, clav_dir), -1.0, 1.0)
        angle_0_180 = float(np.degrees(np.arccos(cos_a)))
        angle_axes = min(angle_0_180, 180.0 - angle_0_180)
        cross = scap_dir[0] * clav_dir[1] - scap_dir[1] * clav_dir[0]
        angle_signed = float(np.degrees(np.arctan2(cross, np.dot(scap_dir, clav_dir))))

        Mx = np.array([scap_dir, -clav_dir]).T
        if abs(np.linalg.det(Mx)) > 1e-9:
            t = np.linalg.solve(Mx, clav_start - scap_center)
            vertex = scap_center + t[0] * scap_dir

            # demi-droite 1 : vers les points scapulaires ; demi-droite 2 : axe claviculaire, angle aigu
            u = scap_center - vertex
            u = u / np.linalg.norm(u) if np.linalg.norm(u) > 1e-9 else scap_dir
            v = clav_dir if np.dot(u, clav_dir) >= 0 else -clav_dir

            R = 0.3 * clav_len
            z = 0.0
            V3 = lambda p: np.array([p[0], p[1], z])

          #  self.draw_arc(V3(vertex), V3(vertex + u * R), V3(vertex + v * R),
          #                angle_axes, name="Angle_scap_clav",
          #                color=(1, 1, 0), thickness=1.2, num_points=30)

            # --- Concavité / convexité ---
        # Point de référence "à l'intérieur de l'os" pour chaque surface :
        #   SC (clavicule)        -> milieu de la surface AC claviculaire (P4,P5)
        #   AC côté claviculaire  -> milieu de la surface SC claviculaire (P1,P2)
        #   AC côté acromial      -> point médial de la fosse sus-épineuse (P11)
        sc_shape, sc_dev = self._curvature(P["P1"], P["P2"], P["P3"], mid("P4", "P5"))
        acc_shape, acc_dev = self._curvature(P["P4"], P["P5"], P["P6"], mid("P1", "P2"))
        aca_shape, aca_dev = self._curvature(P["P7"], P["P8"], P["P9"], P["P11"])

        return {
            "xray_type": "Native",
            "scapular_axis_dir": scap_dir.tolist(),
            "clavicular_axis_dir": clav_dir.tolist(),
            "clavicular_axis_length": clav_len,
            "angle_scap_clav": angle_axes,  # angle aigu (0-90°)
            "angle_scap_clav_180": angle_0_180,  # angle orienté (0-180°)
            "angle_scap_clav_signed": angle_signed,
            "SC_shape": sc_shape,
            "SC_deviation": sc_dev,
            "AC_clav_shape": acc_shape,
            "AC_clav_deviation": acc_dev,
            "AC_acro_shape": aca_shape,
            "AC_acro_deviation": aca_dev,
        }

    # --- Draw in the UI ---

    def draw_arc(self, vertex, p1, p2, angle_deg, name="Arc", color=(1, 1, 0), thickness=1.2, num_points=30):
        """
        Draw an arc centered at `vertex`, starting at `p1` and spanning `angle_deg` toward `p2`.
        The arc is drawn in the XY plane.
        """
        for node in slicer.mrmlScene.GetNodesByClass("vtkMRMLMarkupsCurveNode"):
            if node.GetName() == name:
                slicer.mrmlScene.RemoveNode(node)

        v_start = p1 - vertex
        angle_rad = np.radians(angle_deg)
        points = []
        for t in np.linspace(0, 1, num_points):
            theta = t * angle_rad
            rot_matrix = np.array([[np.cos(theta), -np.sin(theta)],
                                   [np.sin(theta), np.cos(theta)]])
            arc_point_xy = vertex[:2] + rot_matrix @ v_start[:2]
            points.append([arc_point_xy[0], arc_point_xy[1], vertex[2]])

        curveNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsCurveNode", name)
        for pt in points:
            curveNode.AddControlPoint(pt)


        displayNode = curveNode.GetDisplayNode()
        if displayNode:
            displayNode.SetSelectedColor(*color)

            # Absolute line thickness (mm), independent of glyph size
            displayNode.SetCurveLineSizeMode(displayNode.UseLineDiameter)
            displayNode.SetLineDiameter(thickness)

            # Hide point markers - safe now the line doesn't depend on glyph size
            displayNode.SetGlyphScale(0.0)
            displayNode.SetVisibility2D(True)
            displayNode.SetVisibility3D(True)
            displayNode.SetPointLabelsVisibility(False)
            displayNode.SetPropertiesLabelVisibility(True)


