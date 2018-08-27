#!/usr/bin/python3
# Executable for this program.
# Naming style tries to be consistent with PyQt:
#   ClassDefinition
#   guiClass_Instance_Of_It
#   objectsAndFunctions

import sys
from PyQt5 import QtCore, QtGui, QtWidgets
import numpy
from matplotlib.backends import backend_qt5agg as mpl_qt5
from matplotlib import figure as mpl_figure

import os
if os.name == 'nt':
    myappid = u'WTFAmIDoingWithThis?JustToFixWindowsTaskBarIcon' # arbitrary string
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

# Don't modifie gui module by hand!
from pyqtsfplotter_gui import Ui_MainWindow
#
from pyqtsfplotter_models import DataFileObject, DataInSingleFileListModel, \
    DataFilesListModel, PlotListModel

def aboutMessage():
    QtWidgets.QMessageBox.information(None, 'About PyQt Stopped-Flow Simulator', \
"""Author: Jikun Li
Version: 0.99

The program is developed using the following open source tools and libraries:
    Python 3.5.3 <https://docs.python.org/3/license.html>
    PyQt 5.7 <https://www.riverbankcomputing.com/commercial/license-faq>
    Qt 5.7.1 <https://www1.qt.io/qt-licensing-terms/>
    NumPy 1.12.1 <https://docs.scipy.org/doc/numpy/license.html>
    Matplotlib 2.0.0 <http://matplotlib.org/users/license.html>
    
No warranty is provided for either performance or correctness of the program.
""", \
    QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Ok)

# Modifies QMainWindow class.
class QMainWindow_Modified(QtWidgets.QMainWindow):
    def closeEvent(self, event):
        reallyQuit = QtWidgets.QMessageBox.warning(self, 'Exit Program', \
            'All unsaved data will be lost! \nDo you really want to quit?', \
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, \
            QtWidgets.QMessageBox.No)
        if reallyQuit == QtWidgets.QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()
    windowSizeChanged = QtCore.pyqtSignal()
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.windowSizeChanged.emit()
        
class MPLToolbar_Modified(mpl_qt5.NavigationToolbar2QT):
    toolitems = [item for item in mpl_qt5.NavigationToolbar2QT.toolitems \
        if item[0] != 'Save']
    
    def __init__(self, canvas, parent, coordinates=True):        
        super().__init__(canvas, parent, coordinates)
        # Removes the save tool button.
              
# Adds matplotlib widget, and sets up event handlers for the UI.
class App_MainWindow(Ui_MainWindow):               
    def setupApp(self, MainWindow):
        # Sets up UI elements generated by Qt Designer.
        self.devicePixelRatio = MainWindow.devicePixelRatio()
        self.setupUi(MainWindow)
        MainWindow.showMaximized()
        
        # Raw data file import.
        self.fListModel = DataFilesListModel()
        self.comboBox_Select_File.setModel(self.fListModel)        
        self.comboBox_Select_File.setInsertPolicy(QtWidgets.QComboBox.NoInsert)
        self.toolButton_Import_Raw_Data.clicked.connect(self.importRawFiles)
        self.toolButton_Remove_File.clicked.connect(self.removeFileFromList)
        
        # Lets user pick time traces spectra from raw data files.
        self.__axisType = True
        self.toolButton_Toggle_Axis.clicked.connect(self.toggleAxis)
        self.listView_Raw_Traces.setSelectionMode(QtWidgets.QListView.MultiSelection)
        self.comboBox_Select_File.currentIndexChanged.connect(self.fileSelected)
        self.toolButton_Add_This_File.clicked.connect(self.addSelectedToPlot)
        self.toolButton_Add_All_Files.clicked.connect(self.addFromAllFilesToPlot)
        self.toolButton_SVD.clicked.connect(self.addSVDResultsToPlot)
        
        # Plot controls.
        self.__epsilon = 0.0001
        PlotListModel.fontSize = float(self.spinBox_Font_Size.value()) * self.devicePixelRatio
        PlotListModel.lineWidth = self.doubleSpinBox_Line_Width.value() * self.devicePixelRatio
        PlotListModel.markerRatio = self.doubleSpinBox_Marker_Size.value() * self.devicePixelRatio
        self.spinBox_Font_Size.valueChanged.connect(self.changeFontSize)
        self.doubleSpinBox_Line_Width.valueChanged.connect(self.changeLineWidth)
        self.doubleSpinBox_Marker_Size.valueChanged.connect(self.changeMarkerSize)
        self.spinBox_Markevery.valueChanged.connect(self.changeMarkEvery)
        self.checkBox_LogX.stateChanged.connect(self.setXScale)
        self.checkBox_LogY.stateChanged.connect(self.setYScale)
        self.checkBox_Grid.stateChanged.connect(self.setPlotGrid)
        self.checkBox_Legend.stateChanged.connect(self.setPlotLegend)
        self.toolButton_Apply_Range.clicked.connect(self.applyRange)
        self.toolButton_Auto_Range.clicked.connect(self.autoResizePlotRange)
        self.toolButton_Save_Figure.clicked.connect(self.saveFigure)
        self.doubleSpinBox_xMin.valueChanged.connect(self.xMinChanged)
        self.doubleSpinBox_xMax.valueChanged.connect(self.xMaxChanged)
        self.doubleSpinBox_yMin.valueChanged.connect(self.yMinChanged)
        self.doubleSpinBox_yMax.valueChanged.connect(self.yMaxChanged)
        self.toolButton_Remove_Selected_Traces.clicked.connect(self.removeSelectedTraces)
        self.toolButton_All_Traces.clicked.connect(self.selectAllTraces)
        self.toolButton_None_Traces.clicked.connect(self.selectNoneTraces)
        self.toolButton_Line.clicked.connect(self.linePlotSelected)
        self.toolButton_Scatter.clicked.connect(self.scatterPlotSelected)
        self.toolButton_Hide.clicked.connect(self.hidePlotSelected)
        self.toolButton_Export_Traces.clicked.connect(self.saveSelectedTracesToTxt)
        MainWindow.windowSizeChanged.connect(self.resizedWindowArea)  
        
        # Embeds matplotlib plots.        
        self.figures = [mpl_figure.Figure(), mpl_figure.Figure()]
        self.canvases = [mpl_qt5.FigureCanvasQTAgg(fig) for fig in self.figures]
        self.toolbars = [MPLToolbar_Modified(self.canvases[0], self.stackedWidget_Traces_Plot), \
            MPLToolbar_Modified(self.canvases[1], self.stackedWidget_Spectra_Plot)]
        self.toolbars[0].locLabel.setFont( \
            QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont))
        self.toolbars[0].locLabel.setAlignment( \
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.toolbars[1].locLabel.setFont( \
            QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont))
        self.toolbars[1].locLabel.setAlignment( \
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.verticalLayout_4.addWidget(self.canvases[0])
        self.verticalLayout_4.addWidget(self.toolbars[0])
        self.verticalLayout_5.addWidget(self.canvases[1])
        self.verticalLayout_5.addWidget(self.toolbars[1])
        self.plotListModels = [PlotListModel(fig) for fig in self.figures]
        self.tableView_Traces.setModel(self.plotListModels[0])
        self.tableView_Traces.horizontalHeader().setSectionResizeMode(0, \
            QtWidgets.QHeaderView.Stretch)
        self.tableView_Traces.horizontalHeader().setSectionResizeMode(1, \
            QtWidgets.QHeaderView.Fixed)
        self.tableView_Spectra.setModel(self.plotListModels[1])
        self.tableView_Spectra.horizontalHeader().setSectionResizeMode(0, \
            QtWidgets.QHeaderView.Stretch)
        self.tableView_Spectra.horizontalHeader().setSectionResizeMode(1, \
            QtWidgets.QHeaderView.Fixed)
        self.figures[0].axes[0].set_xlabel('Time (s)', fontsize = PlotListModel.fontSize)
        self.figures[0].axes[0].tick_params(labelsize=PlotListModel.fontSize)
        self.figures[1].axes[0].set_xlabel('Wavelength (nm)', fontsize = PlotListModel.fontSize)
        self.figures[1].axes[0].tick_params(labelsize=PlotListModel.fontSize)
        self.tabWidget.currentChanged.connect(self.tabSwitch)

        # Specials
        self.toolButton_Reset.clicked.connect(self.resetCurrentCanvas)
        self.pushButton_Exec.clicked.connect(self.execPlotCommand)
        self.lineEdit_Exec_Command.returnPressed.connect(self.execPlotCommand)
        self.pushButton_About.clicked.connect(aboutMessage)

    # Event handling function
    def execPlotCommand(self):
        invalidCommand = False
        if self.lineEdit_Exec_Command.text().count(';') > 0:
            invalidCommand = True
        try:
            exec('self.figures[self.stackedWidget_right.currentIndex()].axes[0].' \
                + self.lineEdit_Exec_Command.text())
        except:
            invalidCommand = True
        finally:
            if invalidCommand:
                msgBox = QtWidgets.QMessageBox.warning(self.centralwidget, 'Invalid Command', \
                        'Cannot execute this command. The command is limited to plot axes only.', \
                        QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Ok)
            else:
                self.autoResizePlotRange()
                self.pushButton_Exec.setText('exec() may have screwed stuff up!')
    
    def resetCurrentCanvas(self):
        j = self.tabWidget.currentIndex()
        # Not yet determined if this will cause memory leak.
        self.figures[j].axes[0].cla()
        self.figures[j].axes[0].remove()
        if j == 0:
            pTableView =  self.tableView_Traces
        elif j == 1:
            pTableView =  self.tableView_Spectra
        pTableView.clearSelection()
        newModel = PlotListModel(self.figures[j])
        self.plotListModels[j] = newModel
        pTableView.setModel(newModel)
        if j == 0:
            self.figures[0].axes[0].set_xlabel('Time (s)', fontsize = PlotListModel.fontSize)
            self.figures[0].axes[0].tick_params(labelsize=PlotListModel.fontSize)
        elif j == 1:
            self.figures[1].axes[0].set_xlabel('Wavelength (nm)', fontsize = PlotListModel.fontSize)
            self.figures[1].axes[0].tick_params(labelsize=PlotListModel.fontSize)        
        newModel.redrawAll()
            
    def setPlotGrid(self, state):
        self.plotListModels[self.stackedWidget_right.currentIndex()].setGrid( \
            True if state == QtCore.Qt.Checked else False)
        
    def setPlotLegend(self, state):
        self.plotListModels[self.stackedWidget_right.currentIndex()].setLegend( \
            True if state == QtCore.Qt.Checked else False)
                
    def setXScale(self, state):
        if self.stackedWidget_right.currentIndex() == 0:
            if state == QtCore.Qt.Checked:
                x0, x1 = self.figures[0].axes[0].get_xlim()
                if x0 < 0.0 and x1 > 0.0:
                    self.figures[0].axes[0].set_xlim(self.__epsilon, x1)
                    self.resetRangeSpinBoxes()
                self.figures[0].axes[0].set_xscale('log')
            elif state == QtCore.Qt.Unchecked:
                self.figures[0].axes[0].set_xscale('linear')                
            self.plotListModels[self.stackedWidget_right.currentIndex()].refreshLayout()
    
    def setYScale(self, state):
        if state == QtCore.Qt.Checked:
            y0, y1 = self.figures[self.stackedWidget_right.currentIndex()].axes[0].get_ylim()
            if y0 < 0.0 and y1 > 0.0:
                self.figures[self.stackedWidget_right.currentIndex()].axes[0].set_ylim(self.__epsilon, y1)
                self.resetRangeSpinBoxes()
            self.figures[self.stackedWidget_right.currentIndex()].axes[0].set_yscale('log')
        elif state == QtCore.Qt.Unchecked:
            self.figures[self.stackedWidget_right.currentIndex()].axes[0].set_yscale('linear')
        self.plotListModels[self.stackedWidget_right.currentIndex()].refreshLayout()
    
    def applyRange(self):
        self.figures[self.stackedWidget_right.currentIndex()].axes[0].set_xlim( \
            self.doubleSpinBox_xMin.value(), self.doubleSpinBox_xMax.value())
        self.figures[self.stackedWidget_right.currentIndex()].axes[0].set_ylim( \
            self.doubleSpinBox_yMin.value(), self.doubleSpinBox_yMax.value())
        self.plotListModels[self.stackedWidget_right.currentIndex()].refreshLegend()
        self.plotListModels[self.stackedWidget_right.currentIndex()].refreshLayout()
            
    def autoResizePlotRange(self):
        x0, x1, y0, y1 = self.plotListModels[self.stackedWidget_right.currentIndex()].redrawAll()
        if (x0, x1, y0, y1) != (0, 0, 0, 0):
            self.doubleSpinBox_xMin.setValue(x0)
            self.doubleSpinBox_xMax.setValue(x1)
            self.doubleSpinBox_yMin.setValue(y0)
            self.doubleSpinBox_yMax.setValue(y1)
        
    def resizedWindowArea(self):
        self.figures[self.stackedWidget_right.currentIndex()].tight_layout()
        
    def resetRangeSpinBoxes(self):
        x0, x1, y0, y1 = ( \
            *self.figures[self.stackedWidget_right.currentIndex()].axes[0].get_xlim(), \
            *self.figures[self.stackedWidget_right.currentIndex()].axes[0].get_ylim())
        self.doubleSpinBox_xMin.setValue(x0)
        self.doubleSpinBox_xMax.setValue(x1)
        self.doubleSpinBox_yMin.setValue(y0)
        self.doubleSpinBox_yMax.setValue(y1)
        
    def tabSwitch(self, j):
        self.stackedWidget_right.setCurrentIndex(j)
        self.figures[j].axes[0].set_yscale( \
            'log' if self.checkBox_LogY.isChecked() else 'linear')
        if j == 1:
            self.toolButton_Export_Traces.setDisabled(True)
            self.checkBox_LogX.setDisabled(True)
        else:
            self.toolButton_Export_Traces.setDisabled(False)
            self.checkBox_LogX.setDisabled(False)
        self.plotListModels[j].setGrid(self.checkBox_Grid.isChecked())
        self.plotListModels[j].setLegend(self.checkBox_Legend.isChecked())
        self.plotListModels[self.stackedWidget_right.currentIndex()].refreshLayout()
        self.resetRangeSpinBoxes()
                
    def changeFontSize(self, num):
        PlotListModel.fontSize = float(num) * self.devicePixelRatio
        for model in self.plotListModels:
            model.refreshStyle()
            model.refreshLayout()
        
    def changeLineWidth(self, num):
        PlotListModel.lineWidth = float(num) * self.devicePixelRatio
        for model in self.plotListModels:
            model.refreshStyle()
            model.refreshLayout()
            
    # Scatter plot dot density control.
    def changeMarkerSize(self, num):
        PlotListModel.markerRatio = float(num) * self.devicePixelRatio
        for model in self.plotListModels:
            model.refreshStyle()
            model.refreshLayout()
            
    def changeMarkEvery(self, num):
        PlotListModel.maxMarkers = num
        for model in self.plotListModels:
            model.refreshStyle()
            model.refreshLayout()
    
    def xMinChanged(self, num):
        if num > self.doubleSpinBox_xMax.value():
            self.doubleSpinBox_xMax.setValue(num + self.__epsilon)
    
    def xMaxChanged(self, num):
        if num < self.doubleSpinBox_xMin.value():
            self.doubleSpinBox_xMin.setValue(num - self.__epsilon)    
    
    def yMinChanged(self, num):
        if num > self.doubleSpinBox_yMax.value():
            self.doubleSpinBox_yMax.setValue(num + self.__epsilon)
    
    def yMaxChanged(self, num):
        if num < self.doubleSpinBox_yMin.value():
            self.doubleSpinBox_yMin.setValue(num - self.__epsilon) 
           
    def removeSelectedTraces(self):
        if self.tabWidget.currentIndex() == 0:
            pTableView = self.tableView_Traces
        elif self.tabWidget.currentIndex() == 1:
            pTableView = self.tableView_Spectra
        else:
            return
        if pTableView.selectedIndexes():
            removedAny = False
            for row in sorted([index.row() for index in pTableView.selectedIndexes()], reverse = True):
                removedAny |= pTableView.model().removeRows(row, 1)
            if removedAny:
                pTableView.model().redrawAll()
                self.autoResizePlotRange()
    
    def selectAllTraces(self):
        if self.tabWidget.currentIndex() == 0:
            self.tableView_Traces.selectAll()
        elif self.tabWidget.currentIndex() == 1:
            self.tableView_Spectra.selectAll()
        
    def selectNoneTraces(self):
        if self.tabWidget.currentIndex() == 0:
            self.tableView_Traces.clearSelection()
        elif self.tabWidget.currentIndex() == 1:
            self.tableView_Spectra.clearSelection()
            
    def linePlotSelected(self):
        if self.tabWidget.currentIndex() == 0:
            pTableView = self.tableView_Traces
        elif self.tabWidget.currentIndex() == 1:
            pTableView = self.tableView_Spectra
        else:
            return
        if pTableView.selectedIndexes():
            values = [QtCore.Qt.Checked] * len(pTableView.selectedIndexes())
            pTableView.model().setData( \
                pTableView.selectedIndexes(), values, role = QtCore.Qt.CheckStateRole)
            
    def scatterPlotSelected(self):
        if self.tabWidget.currentIndex() == 0:
            pTableView = self.tableView_Traces
        elif self.tabWidget.currentIndex() == 1:
            pTableView = self.tableView_Spectra
        else:
            return
        if pTableView.selectedIndexes():
            values = [QtCore.Qt.PartiallyChecked] * len(pTableView.selectedIndexes())
            pTableView.model().setData( \
                pTableView.selectedIndexes(), values, role = QtCore.Qt.CheckStateRole)
            
    def hidePlotSelected(self):
        if self.tabWidget.currentIndex() == 0:
            pTableView = self.tableView_Traces
        elif self.tabWidget.currentIndex() == 1:
            pTableView = self.tableView_Spectra
        else:
            return
        if pTableView.selectedIndexes():
            values = [QtCore.Qt.Unchecked] * len(pTableView.selectedIndexes())
            pTableView.model().setData( \
                pTableView.selectedIndexes(), values, role = QtCore.Qt.CheckStateRole) 

    def addSVDResultsToPlot(self):
        matrix = []
        rowXData = []
        columnXData = []
        j = 0 if self.__axisType else 1
        for index in self.listView_Raw_Traces.selectedIndexes(): 
            dataX, dataY = (self.listView_Raw_Traces.model().data(index, role = QtCore.Qt.UserRole))
            rowXData.append(self.listView_Raw_Traces.model().data(index, role = QtCore.Qt.DisplayRole))
            matrix.append(dataY)
            columnXData = dataX
        if matrix and self.spinBox_SVD.value() > 0:
            matrix = numpy.array(matrix)
            if matrix.shape[0] < self.spinBox_SVD.value() or matrix.shape[1] < self.spinBox_SVD.value():
                self.spinBox_SVD.setValue(min(matrix.shape))
            U, s, V = numpy.linalg.svd(numpy.array(matrix))
            rowYData = U[:, 0:self.spinBox_SVD.value()].transpose()
            columnYData = V[0:self.spinBox_SVD.value(), :]
            names = ['SVD' + str(self.comboBox_Select_File.currentIndex()) + ' : eig=' + str(s[k]) \
                for k in range(self.spinBox_SVD.value())]
            if self.checkBox_eigvalue.isChecked():
                rowYData = numpy.dot(numpy.diag(s[0:self.spinBox_SVD.value()]), rowYData)
                columnYData = numpy.dot(numpy.diag(s[0:self.spinBox_SVD.value()]), columnYData)
            self.plotListModels[1 - j].appendRow(names, [rowXData] * self.spinBox_SVD.value(), rowYData)
            self.tabWidget.setCurrentIndex(1 - j)
            self.autoResizePlotRange()
            self.plotListModels[j].appendRow(names, [columnXData] * self.spinBox_SVD.value(), columnYData)
            self.tabWidget.setCurrentIndex(j)
        
    # Add traces selected traces in listView_Raw_Traces to plot.
    def addSelectedToPlot(self):
        dataXs = []
        dataYs = []
        names = []
        j = 0 if self.__axisType else 1
        for index in self.listView_Raw_Traces.selectedIndexes():
            dataX, dataY = (self.listView_Raw_Traces.model().data(index, role = QtCore.Qt.UserRole))
            name1 = 'File' + str(self.comboBox_Select_File.currentIndex()) + ': ' \
                + ('l' if self.__axisType else 't') + '=' \
                + str(self.listView_Raw_Traces.model().data(index, role = QtCore.Qt.DisplayRole))
            dataXs.append(dataX)
            dataYs.append(dataY)
            names.append(name1)        
        self.plotListModels[j].appendRow(names, dataXs, dataYs)
        self.tabWidget.setCurrentIndex(j)
        self.autoResizePlotRange()

    # Same as above,
    # but also searches in every open file for selected wavelengths/timepoints and add them to plot.    
    def addFromAllFilesToPlot(self):
        dataXs = []
        dataYs = []
        names = []
        j = 0 if self.__axisType else 1
        for index0 in self.listView_Raw_Traces.selectedIndexes():
            dataX0, dataY0 = (self.listView_Raw_Traces.model().data(index0, role = QtCore.Qt.UserRole))
            name0 = 'File' + str(self.comboBox_Select_File.currentIndex()) + ': ' \
                + ('l' if self.__axisType else 't') + '=' \
                + str(self.listView_Raw_Traces.model().data(index0, role = QtCore.Qt.DisplayRole))
            dataXs.append(dataX0)
            dataYs.append(dataY0)
            names.append(name0)
            for k in range(self.fListModel.rowCount()):
                if k != self.comboBox_Select_File.currentIndex():
                    pFileObj = self.fListModel.data(self.fListModel.index(k, 0), role = QtCore.Qt.UserRole)
                    pAxis = pFileObj.w if self.__axisType else pFileObj.t
                    for i in range(len(pAxis)):
                        if pAxis[i] == self.listView_Raw_Traces.model().data(index0, role = QtCore.Qt.DisplayRole):
                            dataX1 = pFileObj.t if self.__axisType else pFileObj.w
                            dataY1 = pFileObj.z[i] if self.__axisType else [z1[i] for z1 in pFileObj.z]
                            name1 = 'File' + str(k) + ': ' + ('l' if self.__axisType else 't') \
                                + '=' + str(pAxis[i])
                            dataXs.append(dataX1)
                            dataYs.append(dataY1)
                            names.append(name1)
        self.plotListModels[j].appendRow(names, dataXs, dataYs)
        self.tabWidget.setCurrentIndex(j)
        x0, x1, y0, y1 = self.plotListModels[j].redrawAll()
        self.autoResizePlotRange()
        
    def removeFileFromList(self):
        self.fListModel.removeRows(self.comboBox_Select_File.currentIndex(), 1)
        
    def fileSelected(self, j):
        fileObj = self.fListModel.data(self.fListModel.index(j, 0), \
                    role = QtCore.Qt.UserRole)
        if fileObj:
            self.listView_Raw_Traces.setModel(fileObj.genModel(self.__axisType))
        else:
            self.listView_Raw_Traces.setModel(None)
            
    # Changes axis in listView_Raw_Traces.
    def toggleAxis(self):
        if self.listView_Raw_Traces.model():
            self.__axisType = not self.__axisType
            self.listView_Raw_Traces.model().setType(self.__axisType)
            if self.__axisType:
                self.label_Current_Axis.setText('Selection Axis: Wavelengths')
                self.label_Current_Axis.setToolTip('Time traces at different wavelengths.')
            else:
                self.label_Current_Axis.setText('Selection Axis: Timepoints')
                self.label_Current_Axis.setToolTip('Spectra at different timepoints.')
            self.listView_Raw_Traces.scrollToTop()
        
    # Imports a text file for raw data.    
    def importRawFiles(self):
        openTextFiles = QtWidgets.QFileDialog.getOpenFileNames(self.centralwidget, \
            'Import From .txt Or .csv Files', '', \
            'All Supported Formats (*.txt *.csv);;KinTek File (*.txt);;ProDataCSV File (*.csv)', \
            'All Supported Formats (*.txt *.csv)', \
            QtWidgets.QFileDialog.Options() | QtWidgets.QFileDialog.DontUseNativeDialog)
        if openTextFiles[0]:
            openedAtLeastOneFile = False
            for fileName in openTextFiles[0]:
                openedAtLeastOneFile |= self.fListModel.appendRow(fileName)
            if openedAtLeastOneFile:
                self.comboBox_Select_File.setCurrentIndex(self.comboBox_Select_File.model().rowCount() - 1)
    
    # Saves time traces to .txt file, compatible with above function.
    __savedTxtCount = 1
    def saveSelectedTracesToTxt(self):
        indices = self.tableView_Traces.selectedIndexes()
        n = len(indices)
        if n > 0:
            t, y0 = self.plotListModels[0].data(indices[0], role = QtCore.Qt.UserRole)
            y = [y0]
            # Needs to remove spaces in names.
            names = [self.plotListModels[0].data(indices[0], role = QtCore.Qt.DisplayRole).replace(' ', '')]
            count = 0
            for i in range(1, n):
                (x1, y1) = self.plotListModels[0].data(indices[i], role = QtCore.Qt.UserRole)
                name1 = self.plotListModels[0].data(indices[i], role = QtCore.Qt.DisplayRole).replace(' ', '')
                if numpy.array_equal(t, x1):
                    y.append(y1)
                    names.append(name1)
                else:
                    count += 1
            if count > 0:
                msgBox = QtWidgets.QMessageBox.question(self.centralwidget, 'Different Time Data', \
                    'Found ' + str(count) + ' selected time traces with different time points. They will be ignored when saving data.', \
                    QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
                if msgBox != QtWidgets.QMessageBox.Ok:
                    pass
                else:
                    return
            saveTxtFile = QtWidgets.QFileDialog.getSaveFileName(self.centralwidget, \
                'Save Data As Text File', 'data' + str(self.__savedTxtCount) + '.txt', \
                'KinTek File (*.txt)', 'KinTek File (*.txt)', \
                QtWidgets.QFileDialog.Options() | QtWidgets.QFileDialog.DontUseNativeDialog)
            if saveTxtFile[0]:
                with open(saveTxtFile[0], 'w') as file1:
                    file1.write('Time')
                    for name1 in names:
                        file1.write('\t{0}'.format(name1))
                    file1.write('\n')
                    for j in range(len(t)):
                        file1.write('{0}'.format(t[j]))
                        for k in range(len(y)):
                            file1.write('\t{0}'.format(y[k][j]))
                        file1.write('\n')
                    file1.close()
                    self.__savedTxtCount += 1
                
    # Exports figure area as 600dpi files.
    __savedFigureCount = 1
    def saveFigure(self):
        nameString = ['Time Traces', 'Spectra']
        saveFigFile = QtWidgets.QFileDialog.getSaveFileName(self.centralwidget, \
            'Save ' + nameString[self.stackedWidget_right.currentIndex()] + ' As Figure', \
            'Figure' + str(self.__savedFigureCount), \
            '.png Raster Graphic (*.png);;.jpg Raster Graphic (*.jpg);;.tif Raster Graphic (*.tif);;.svg Vector Graphic (*.svg);;.eps Vector Graphic (*.eps)', \
            '.png Raster Graphic (*.png)', \
            QtWidgets.QFileDialog.Options() | QtWidgets.QFileDialog.DontUseNativeDialog)
        if saveFigFile[0]:
            self.__savedFigureCount += 1
            self.figures[self.stackedWidget_right.currentIndex()].savefig(saveFigFile[0], \
                dpi = self.horizontalSlider_DPI.value())
 
# Main function.    
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    mainWindow = QMainWindow_Modified()
    ui = App_MainWindow()
    ui.setupApp(mainWindow)
    mainWindow.show()
    sys.exit(app.exec_())
