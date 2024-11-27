from qgis.core import (
    QgsProject, QgsVectorLayer, QgsFeature, QgsGeometry,
    QgsPointXY, QgsRasterLayer, QgsField, QgsWkbTypes, edit, QgsMarkerSymbol, QgsCoordinateTransform, QgsGraduatedSymbolRenderer, QgsFillSymbol, QgsRuleBasedRenderer, QgsExpression, QgsFeatureRequest
)
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QPushButton, QLabel, QLineEdit, QListWidget, QComboBox, QMessageBox, QAction, QFormLayout
)
from qgis.PyQt.QtCore import QVariant
import random


class AccuracyAssessment:
    def __init__(self, iface):
        self.iface = iface
        self.dialog_generate = None
        self.dialog_merge = None
        self.dialog_assessment = None
        self.dialog_text_mapping = None
        self.dialog_statistics = None
        self.action_generate = None
        self.action_merge = None
        self.action_assessment = None
        self.action_text_mapping = None
        self.action_statistics = None

    def initGui(self):
        # Генерация случайных точек
        self.action_generate = QAction("1. Генерация случайных точек", self.iface.mainWindow())
        self.action_generate.triggered.connect(self.open_generate_dialog)
        self.iface.addPluginToMenu("Accuracy Assessment Assistant", self.action_generate)

        # Объединение точечных слоев
        self.action_merge = QAction("2. Запись значений из растра (если точки сгенерированны не методами модуля!)", self.iface.mainWindow())
        self.action_merge.triggered.connect(self.open_merge_dialog)
        self.iface.addPluginToMenu("Accuracy Assessment Assistant", self.action_merge)

        # Добавление названий классов
        self.action_text_mapping = QAction("3. Добавление названий классов", self.iface.mainWindow())
        self.action_text_mapping.triggered.connect(self.open_text_mapping_dialog)
        self.iface.addPluginToMenu("Accuracy Assessment Assistant", self.action_text_mapping)

        # Оценка точек
        self.action_assessment = QAction("4. Оценка точности классификации", self.iface.mainWindow())
        self.action_assessment.triggered.connect(self.open_assessment_dialog)
        self.iface.addPluginToMenu("Accuracy Assessment Assistant", self.action_assessment)

        # Рассчёт статистики 
        self.action_statistics = QAction("5. Статистика оценки точности", self.iface.mainWindow())
        self.action_statistics.triggered.connect(self.open_statistics_dialog)
        self.iface.addPluginToMenu("Accuracy Assessment Assistant", self.action_statistics)
    

    def unload(self): # Выгрузка пунктов меню при закрытии модуля
        self.iface.removePluginMenu("Accuracy Assessment Assistant", self.action_generate)
        self.iface.removePluginMenu("Accuracy Assessment Assistant", self.action_merge)
        self.iface.removePluginMenu("Accuracy Assessment Assistant", self.action_assessment)
        self.iface.removePluginMenu("Accuracy Assessment Assistant", self.action_text_mapping)
        self.iface.removePluginMenu("Accuracy Assessment Assistant", self.action_statistics)

    # Открытие различных пунктов меню
    def open_generate_dialog(self):
        self.dialog_generate = RandomPointGeneratorDialog(self.iface)
        self.dialog_generate.exec_()

    def open_merge_dialog(self):
        self.dialog_merge = PointLayerMergerDialog(self.iface)
        self.dialog_merge.exec_()

    def open_assessment_dialog(self):
        self.dialog_assessment = PointAssessmentDialog(self.iface)
        self.dialog_assessment.exec_()

    def open_text_mapping_dialog(self):
        self.dialog_text_mapping = RasterValueTextMappingDialog(self.iface)
        self.dialog_text_mapping.exec_()

    def open_statistics_dialog(self):
        self.dialog_statistics = AssessmentStatisticsDialog(self.iface)
        self.dialog_statistics.exec_()


class RandomPointGeneratorDialog(QDialog):
    def __init__(self, iface):
        super().__init__()
        self.iface = iface
        self.setWindowTitle("Генерация случайных точек")
        self.layout = QVBoxLayout()

        self.vector_layer = QComboBox()
        self.raster_layer = QComboBox()
        self.point_count_input = QLineEdit()
        self.upload_button = QPushButton("Создать точки")

        self.layout.addWidget(QLabel("Выберите векторный слой:"))
        self.layout.addWidget(self.vector_layer)
        self.layout.addWidget(QLabel("Выберите растровый слой:"))
        self.layout.addWidget(self.raster_layer)
        self.layout.addWidget(QLabel("Введите количество точек:"))
        self.layout.addWidget(self.point_count_input)
        self.layout.addWidget(self.upload_button)

        self.setLayout(self.layout)

        self.upload_button.clicked.connect(self.generate_random_points)
        self.load_layers()

    def load_layers(self):
        layers = QgsProject.instance().mapLayers().values()
        for layer in layers:
            if isinstance(layer, QgsVectorLayer) and layer.geometryType() == QgsWkbTypes.PolygonGeometry:
                self.vector_layer.addItem(layer.name(), layer.id())
            elif isinstance(layer, QgsRasterLayer):
                self.raster_layer.addItem(layer.name(), layer.id())

    def generate_random_points(self):
        vector_layer_id = self.vector_layer.currentData()
        raster_layer_id = self.raster_layer.currentData()
        if not vector_layer_id or not raster_layer_id:
            QMessageBox.warning(self, "Ошибка", "Выберите векторный и растровый слои.")
            return

        vector_layer = QgsProject.instance().mapLayer(vector_layer_id)
        raster_layer = QgsProject.instance().mapLayer(raster_layer_id)
        point_count = int(self.point_count_input.text())

        project_crs = QgsProject.instance().crs()
        point_layer = QgsVectorLayer(f"Point?crs={project_crs.authid()}", "Случайные точки", "memory")
        provider = point_layer.dataProvider()
        provider.addAttributes([QgsField("ID", QVariant.Int), QgsField("RasterValue", QVariant.Double)])
        point_layer.updateFields()

        for i in range(point_count):
            extent = vector_layer.extent()
            x = random.uniform(extent.xMinimum(), extent.xMaximum())
            y = random.uniform(extent.yMinimum(), extent.yMaximum())
            point = QgsFeature()
            point.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(x, y)))
            raster_value = self.get_raster_value(raster_layer, x, y)
            point.setAttributes([i + 1, raster_value])
            provider.addFeature(point)

        point_layer.updateExtents()
        QgsProject.instance().addMapLayer(point_layer)

        # Применение стиля
        self.apply_style_to_layer(point_layer)

    def apply_style_to_layer(self, layer):
        # Создаем символ для точек
        symbol = QgsMarkerSymbol.createSimple({
            'color': 'orange',       # Цвет заливки (прозрачный)
            'outline_color': 'black',     # Цвет окантовки
            'outline_width': '0.5'        # Толщина окантовки
        })

        # Проверяем, что слой валиден
        if layer and layer.renderer():
            layer.renderer().setSymbol(symbol)
            layer.triggerRepaint()

    def get_raster_value(self, raster_layer, x, y):
        if raster_layer.isValid():
            provider = raster_layer.dataProvider()
            value = provider.sample(QgsPointXY(x, y), 1)
            return value[0] if value else None
        return None

class PointLayerMergerDialog(QDialog):
    def __init__(self, iface):
        super().__init__()
        self.iface = iface
        self.setWindowTitle("Запись значений из растра")
        self.layout = QVBoxLayout()

        self.point_layers_list = QListWidget()
        self.raster_layer_combo = QComboBox()
        self.merge_button = QPushButton("Объединить и заполнить точки")

        self.point_layers_list.setSelectionMode(QListWidget.MultiSelection)

        self.layout.addWidget(QLabel("Выберите точечные слои:"))
        self.layout.addWidget(self.point_layers_list)
        self.layout.addWidget(QLabel("Выберите растровый слой:"))
        self.layout.addWidget(self.raster_layer_combo)
        self.layout.addWidget(self.merge_button)

        self.setLayout(self.layout)

        self.merge_button.clicked.connect(self.merge_layers)
        self.load_layers()

    def load_layers(self):
        layers = QgsProject.instance().mapLayers().values()
        for layer in layers:
            if isinstance(layer, QgsVectorLayer) and layer.geometryType() == QgsWkbTypes.PointGeometry:
                self.point_layers_list.addItem(layer.name())
                self.point_layers_list.item(self.point_layers_list.count() - 1).setData(1, layer.id())
            elif isinstance(layer, QgsRasterLayer):
                self.raster_layer_combo.addItem(layer.name(), layer.id())

    def merge_layers(self):
        selected_point_layer_ids = [
            self.point_layers_list.item(i).data(1)
            for i in range(self.point_layers_list.count())
            if self.point_layers_list.item(i).isSelected()
        ]
        raster_layer_id = self.raster_layer_combo.currentData()
        if not selected_point_layer_ids or not raster_layer_id:
            QMessageBox.warning(self, "Ошибка", "Выберите точечные и растровый слой.")
            return

        raster_layer = QgsProject.instance().mapLayer(raster_layer_id)
        project_crs = QgsProject.instance().crs()
        raster_crs = raster_layer.crs()
        crs_transform = QgsCoordinateTransform(project_crs, raster_crs, QgsProject.instance())

        merged_layer = QgsVectorLayer(f"Point?crs={project_crs.authid()}", "Объединенные точки", "memory")
        provider = merged_layer.dataProvider()
        provider.addAttributes([QgsField("RasterValue", QVariant.Double)])
        merged_layer.updateFields()

        for layer_id in selected_point_layer_ids:
            point_layer = QgsProject.instance().mapLayer(layer_id)
            for feature in point_layer.getFeatures():
                new_feature = QgsFeature()
                new_feature.setGeometry(feature.geometry())
                point_geom = feature.geometry().asPoint()
                transformed_point = crs_transform.transform(QgsPointXY(point_geom.x(), point_geom.y()))
                raster_value = self.get_raster_value(raster_layer, transformed_point.x(), transformed_point.y())
                new_feature.setAttributes([raster_value])
                provider.addFeature(new_feature)

        merged_layer.updateExtents()
        QgsProject.instance().addMapLayer(merged_layer)
        self.apply_style_to_layer(merged_layer)

    def get_raster_value(self, raster_layer, x, y):
        if raster_layer.isValid():
            provider = raster_layer.dataProvider()
            value = provider.sample(QgsPointXY(x, y), 1)
            if value[1]:  # Проверяем, успешно ли выполнено чтение
                return value[0]
        return None

    def apply_style_to_layer(self, layer):
    # Создаем символ с оранжевым кругом и чёрной окантовкой
        symbol = QgsMarkerSymbol.createSimple({
            'color': 'orange',         # Цвет заливки
            'outline_color': 'black',  # Цвет окантовки
            'outline_width': '0.5',    # Толщина окантовки
        })

    # Применяем символ к слою
        if layer and layer.renderer():
            layer.renderer().setSymbol(symbol)
            layer.triggerRepaint()

class PointAssessmentDialog(QDialog):
    def __init__(self, iface):
        super().__init__()
        self.iface = iface
        self.setWindowTitle("Оценка точек")
        self.layout = QVBoxLayout()

        self.layer_combo = QComboBox()
        self.start_button = QPushButton("Начать оценку")
        self.layout.addWidget(QLabel("Выберите точечный слой:"))
        self.layout.addWidget(self.layer_combo)
        self.layout.addWidget(self.start_button)
        self.setLayout(self.layout)

        self.start_button.clicked.connect(self.start_assessment)
        self.load_layers()

    def load_layers(self):
        layers = QgsProject.instance().mapLayers().values()
        for layer in layers:
            if isinstance(layer, QgsVectorLayer) and layer.geometryType() == QgsWkbTypes.PointGeometry:
                self.layer_combo.addItem(layer.name(), layer.id())

    def start_assessment(self):
        layer_id = self.layer_combo.currentData()
        if not layer_id:
            QMessageBox.warning(self, "Ошибка", "Выберите точечный слой.")
            return

        point_layer = QgsProject.instance().mapLayer(layer_id)
        self.hide()  # Скрытие основного окна
        self.add_assessment_column(point_layer)

        features = list(point_layer.getFeatures())
        for feature in features:
            self.evaluate_point(point_layer, feature)

        QMessageBox.information(self, "Готово", "Оценка завершена!")
        self.close()

    def add_assessment_column(self, layer):
        provider = layer.dataProvider()
        if 'Assessment' not in [field.name() for field in provider.fields()]:
            provider.addAttributes([QgsField('Assessment', QVariant.Int)])
            layer.updateFields()

    def evaluate_point(self, layer, feature):
        canvas = self.iface.mapCanvas()
        canvas.setInteractive(False)
        canvas.setCenter(feature.geometry().asPoint())
        canvas.zoomScale(7500)
        canvas.refresh()

        # Выделение точки
        self.highlight_feature(layer, feature)

        # Получение значения для отображения
        fields = [field.name() for field in layer.fields()]
        if 'RasterText' in fields:
            display_value = feature['RasterText']
        elif 'RasterValue' in fields:
            display_value = feature['RasterValue']
        else:
            last_field = fields[-1] if fields else None
            display_value = feature[last_field] if last_field else "Нет данных"

        if display_value is None or display_value == "":
            display_value = "Нет данных"

        # Показ диалога оценки
        reply = self.show_custom_dialog(display_value)

        # Сохранение оценки
        with edit(layer):
            feature['Assessment'] = 1 if reply == QMessageBox.Yes else 0
            layer.updateFeature(feature)

        # Удаление выделения
        self.remove_highlight(layer)
        canvas.setInteractive(True)

    def highlight_feature(self, layer, feature):
        """Выделяет точку на карте."""
        layer.removeSelection()  # Убираем предыдущее выделение
        layer.select(feature.id())  # Выделяем текущую точку
        layer.triggerRepaint()

    def remove_highlight(self, layer):
        """Снимает выделение с точки."""
        layer.removeSelection()
        layer.triggerRepaint()

    def show_custom_dialog(self, raster_value):
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Оценка точки")
        dialog.setText(f"Совпадение точки? (Значение: {raster_value})")
        dialog.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        dialog.setDefaultButton(QMessageBox.Yes)

        # Смещение окна для удобства
        screen = self.iface.mainWindow().screen().geometry()
        dialog.move(screen.width() // 2 + 150, screen.height() // 2 - 100)

        reply = dialog.exec_()
        return reply

class RasterValueTextMappingDialog(QDialog):
    def __init__(self, iface):
        super().__init__()
        self.iface = iface
        self.setWindowTitle("Сопоставление текстовых значений")
        self.layout = QVBoxLayout()

        self.layer_combo = QComboBox()
        self.start_button = QPushButton("Сопоставить значения")
        self.layout.addWidget(QLabel("Выберите точечный слой:"))
        self.layout.addWidget(self.layer_combo)
        self.layout.addWidget(self.start_button)
        self.setLayout(self.layout)

        self.start_button.clicked.connect(self.map_raster_values)
        self.load_layers()

    def load_layers(self):
        layers = QgsProject.instance().mapLayers().values()
        for layer in layers:
            if isinstance(layer, QgsVectorLayer) and layer.geometryType() == QgsWkbTypes.PointGeometry:
                self.layer_combo.addItem(layer.name(), layer.id())

    def map_raster_values(self):
        layer_id = self.layer_combo.currentData()
        if not layer_id:
            QMessageBox.warning(self, "Ошибка", "Выберите точечный слой.")
            return

        point_layer = QgsProject.instance().mapLayer(layer_id)
        raster_values = self.get_unique_raster_values(point_layer)

        if not raster_values:
            QMessageBox.warning(self, "Ошибка", "В слое отсутствует столбец RasterValue или данные.")
            return

        mappings = self.get_user_mappings(raster_values)
        if mappings:
            self.apply_text_mappings(point_layer, mappings)
            QMessageBox.information(self, "Готово", "Сопоставление выполнено!")
            self.close()

    def get_unique_raster_values(self, layer):
        raster_values = set()
        for feature in layer.getFeatures():
            value = feature['RasterValue']
            if value is not None:
                raster_values.add(value)
        return sorted(raster_values)

    def get_user_mappings(self, raster_values):
        dialog = QDialog(self)
        dialog.setWindowTitle("Сопоставление значений")
        dialog_layout = QFormLayout()
        inputs = {}

        for value in raster_values:
            line_edit = QLineEdit()
            dialog_layout.addRow(f"Значение {value}:", line_edit)
            inputs[value] = line_edit

        ok_button = QPushButton("OK")
        dialog_layout.addWidget(ok_button)
        dialog.setLayout(dialog_layout)
        ok_button.clicked.connect(dialog.accept)

        if dialog.exec_() == QDialog.Accepted:
            return {value: line_edit.text() for value, line_edit in inputs.items()}
        return None

    def apply_text_mappings(self, layer, mappings):
        provider = layer.dataProvider()

        if 'RasterText' not in [field.name() for field in provider.fields()]:
            provider.addAttributes([QgsField('RasterText', QVariant.String)])
            layer.updateFields()

        with edit(layer):
            for feature in layer.getFeatures():
                raster_value = feature['RasterValue']
                if raster_value in mappings:
                    feature['RasterText'] = mappings[raster_value]
                    layer.updateFeature(feature)

class AssessmentStatisticsDialog(QDialog):
    def __init__(self, iface):
        super().__init__()
        self.iface = iface
        self.setWindowTitle("Статистика оценки")
        self.layout = QVBoxLayout()

        self.layer_combo = QComboBox()
        self.calculate_button = QPushButton("Рассчитать статистику")
        self.result_label = QLabel("")

        self.layout.addWidget(QLabel("Выберите точечный слой:"))
        self.layout.addWidget(self.layer_combo)
        self.layout.addWidget(self.calculate_button)
        self.layout.addWidget(self.result_label)
        self.setLayout(self.layout)

        self.calculate_button.clicked.connect(self.calculate_statistics)
        self.load_layers()

    def load_layers(self):
        layers = QgsProject.instance().mapLayers().values()
        for layer in layers:
            if isinstance(layer, QgsVectorLayer) and layer.geometryType() == QgsWkbTypes.PointGeometry:
                self.layer_combo.addItem(layer.name(), layer.id())

    def calculate_statistics(self):
        layer_id = self.layer_combo.currentData()
        if not layer_id:
            QMessageBox.warning(self, "Ошибка", "Выберите точечный слой.")
            return

        point_layer = QgsProject.instance().mapLayer(layer_id)
        total_points, matched_points = 0, 0
        class_stats = {}

        for feature in point_layer.getFeatures():
            raster_value = feature['RasterText']
            assessment = feature['Assessment']

            if raster_value is None or assessment is None:
                continue

            total_points += 1
            if assessment == 1:
                matched_points += 1

            if raster_value not in class_stats:
                class_stats[raster_value] = {"total": 0, "matched": 0}

            class_stats[raster_value]["total"] += 1
            if assessment == 1:
                class_stats[raster_value]["matched"] += 1

        if total_points == 0:
            QMessageBox.warning(self, "Ошибка", "В слое отсутствуют данные для анализа.")
            return

        overall_percentage = (matched_points / total_points) * 100
        result_text = f"Общий процент совпадения: {overall_percentage:.2f}%\n\n"

        for raster_value, stats in class_stats.items():
            percentage = (stats["matched"] / stats["total"]) * 100 if stats["total"] > 0 else 0
            result_text += f"Значение {raster_value}: {percentage:.2f}% совпадений\n"

        self.result_label.setText(result_text)













