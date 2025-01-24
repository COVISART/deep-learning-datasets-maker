from osgeo import gdal
import os.path as osp
import math
from qgis.core import (
    QgsTask,
    QgsMessageLog,
    Qgis,
    QgsApplication
)
import uuid
MESSAGE_CATEGORY = 'COVISART'

def scale_to_percentage(value, max_value):
    if max_value == 0:
        raise ValueError("max_value cannot be zero.")
    if value < 0 or value > max_value:
        raise ValueError("value must be between 0 and max_value.")
    return (value / max_value) * 100

class RasterSplittingTask(QgsTask):
    def __init__(self,op_name, fn_ras, cdpath, frmt_ext, imgfrmat, needed_out_x, needed_out_y, file_name):
        super().__init__("Raster Splitting Task: " + op_name, QgsTask.CanCancel)
        self.op_name = op_name,
        self.fn_ras = fn_ras
        self.cdpath = cdpath
        self.frmt_ext = frmt_ext
        self.imgfrmat = imgfrmat
        self.needed_out_x = needed_out_x
        self.needed_out_y = needed_out_y
        self.file_name = file_name

    def run(self):
        try:
            ds = gdal.Open(self.fn_ras)
            if not ds:
                QgsMessageLog.logMessage("Error: Cannot open file: " + self.fn_ras, MESSAGE_CATEGORY, Qgis.Critical)
                return False
            
            gt = ds.GetGeoTransform()
            if not gt:
                QgsMessageLog.logMessage("GetGeoTransform error", MESSAGE_CATEGORY, Qgis.Critical)
                return False

            # Raster özelliklerini hesaplama
            xmin, ymax, resx, resy = gt[0], gt[3], gt[1], abs(gt[5])
            xnotround = ds.RasterXSize / self.needed_out_x
            ynotround = ds.RasterYSize / self.needed_out_y
            xround, yround = math.ceil(xnotround), math.ceil(ynotround)

            QgsMessageLog.logMessage('xround {}'.format(xround),
                                MESSAGE_CATEGORY, Qgis.Success)
            QgsMessageLog.logMessage('yround {}'.format(yround),
                                MESSAGE_CATEGORY, Qgis.Success)
            
            pixtomX = self.needed_out_x * xround * resx
            pixtomy = self.needed_out_y * yround * resy
            xsize, ysize = pixtomX / xround, pixtomy / yround
            xsteps = [xmin + xsize * i for i in range(xround + 1)]
            ysteps = [ymax - ysize * i for i in range(yround + 1)]
            
            # Alt parçalara ayırma ve kaydetme
            for i in range(xround):
                if self.isCanceled():
                    QgsMessageLog.logMessage("Task was canceled during processing.", MESSAGE_CATEGORY, Qgis.Warning)
                    return False
                for j in range(yround):
                    if self.isCanceled():
                        QgsMessageLog.logMessage("Task was canceled during processing.", MESSAGE_CATEGORY, Qgis.Warning)
                        return False
                    xmin, xmax = xsteps[i], xsteps[i + 1]
                    ymax, ymin = ysteps[j], ysteps[j + 1]

                    savePath = osp.join(self.cdpath, f"{self.file_name}-{j}-{i}.{self.frmt_ext}")
                    kwargs = {
                        'projWin': (xmin, ymax, xmax, ymin),
                        'xRes': resx,
                        'yRes': resy,
                        'outputType': gdal.gdalconst.GDT_Byte,
                        'format': self.imgfrmat
                    }
                    gdal.Translate(savePath, ds, **kwargs)
                
                self.setProgress(scale_to_percentage(i, xround))

            ds = None  # Dataset'i kapatma
            return True  # Görev başarıyla tamamlandı
        except Exception as e:
            QgsMessageLog.logMessage(f"Error in task: {str(e)}", MESSAGE_CATEGORY, Qgis.Critical)
            return False

    def finished(self, result):
        if result:
            QgsMessageLog.logMessage("Task completed successfully!", MESSAGE_CATEGORY, Qgis.Success)
        else:
            QgsMessageLog.logMessage("Task failed or was canceled.", MESSAGE_CATEGORY, Qgis.Warning)

    def cancel(self):
        QgsMessageLog.logMessage("Task canceled by user.", MESSAGE_CATEGORY, Qgis.Warning)
        super().cancel()

# Görev başlatma
def start_task(op_name,fn_ras, cdpath, frmt_ext, imgfrmat, needed_out_x, needed_out_y, file_name):
    unique_task_name = f"Raster Splitting Task - {uuid.uuid4()}"
    task = RasterSplittingTask(op_name,fn_ras, cdpath, frmt_ext, imgfrmat, needed_out_x, needed_out_y, file_name)
    task.setDescription(unique_task_name)
    QgsApplication.taskManager().addTask(task)
    QgsMessageLog.logMessage(f"Task '{unique_task_name}' started: " + op_name, MESSAGE_CATEGORY, Qgis.Info)
