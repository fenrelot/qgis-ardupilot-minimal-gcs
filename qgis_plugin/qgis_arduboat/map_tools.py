from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeatureRequest,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
    QgsRectangle,
    QgsVectorLayer,
    QgsWkbTypes,
)
from qgis.gui import QgsMapToolEmitPoint, QgsVertexMarker


@dataclass(frozen=True)
class SelectedTarget:
    lat: float
    lon: float
    project_x: float
    project_y: float
    source: str
    layer_name: str | None = None


class TargetMapTool(QgsMapToolEmitPoint):
    def __init__(
        self,
        canvas,
        on_target_selected: Callable[[SelectedTarget], None],
        iface=None,
    ) -> None:
        super().__init__(canvas)
        self.iface = iface
        self.on_target_selected = on_target_selected
        self.marker: QgsVertexMarker | None = None

    def canvasReleaseEvent(self, event) -> None:
        if event.button() != Qt.LeftButton:
            return

        project_point = self.toMapCoordinates(event.pos())
        target = self._target_from_active_layer(project_point)
        if target is None:
            target = self._target_from_project_point(project_point, "map click")

        self._set_marker(QgsPointXY(target.project_x, target.project_y))
        self.on_target_selected(target)

    def clear_marker(self) -> None:
        if self.marker is None:
            return
        self.canvas().scene().removeItem(self.marker)
        self.marker = None

    def _target_from_project_point(
        self,
        project_point: QgsPointXY,
        source: str,
        layer_name: str | None = None,
    ) -> SelectedTarget:
        wgs84_point = self._transform_point(
            project_point,
            self._project_crs(),
            QgsCoordinateReferenceSystem("EPSG:4326"),
        )
        return SelectedTarget(
            lat=wgs84_point.y(),
            lon=wgs84_point.x(),
            project_x=project_point.x(),
            project_y=project_point.y(),
            source=source,
            layer_name=layer_name,
        )

    def _target_from_active_layer(self, project_point: QgsPointXY) -> SelectedTarget | None:
        layer = self.iface.activeLayer() if self.iface is not None else None
        if not isinstance(layer, QgsVectorLayer) or not layer.isValid():
            return None
        if layer.geometryType() in (QgsWkbTypes.NullGeometry, QgsWkbTypes.UnknownGeometry):
            return None

        project_crs = self._project_crs()
        layer_crs = layer.crs()
        try:
            layer_point = self._transform_point(project_point, project_crs, layer_crs)
            search_rect = self._search_rect_in_layer_crs(
                project_point,
                project_crs,
                layer_crs,
            )
        except Exception:
            return None

        request = QgsFeatureRequest().setFilterRect(search_rect)
        best_point: QgsPointXY | None = None
        best_distance_sq: float | None = None
        best_source = ""

        for feature in layer.getFeatures(request):
            geometry = feature.geometry()
            if geometry is None or geometry.isEmpty():
                continue
            candidate_point, candidate_source = _candidate_point(
                geometry,
                layer_point,
                layer.geometryType(),
            )
            if candidate_point is None:
                continue
            distance_sq = _distance_sq(layer_point, candidate_point)
            if best_distance_sq is None or distance_sq < best_distance_sq:
                best_distance_sq = distance_sq
                best_point = candidate_point
                best_source = candidate_source

        if best_point is None:
            return None

        project_selected = self._transform_point(best_point, layer_crs, project_crs)
        return self._target_from_project_point(
            project_selected,
            best_source,
            layer.name(),
        )

    def _search_rect_in_layer_crs(
        self,
        project_point: QgsPointXY,
        project_crs: QgsCoordinateReferenceSystem,
        layer_crs: QgsCoordinateReferenceSystem,
    ) -> QgsRectangle:
        tolerance = self._search_tolerance_project_units()
        min_project = QgsPointXY(project_point.x() - tolerance, project_point.y() - tolerance)
        max_project = QgsPointXY(project_point.x() + tolerance, project_point.y() + tolerance)
        min_layer = self._transform_point(min_project, project_crs, layer_crs)
        max_layer = self._transform_point(max_project, project_crs, layer_crs)
        rect = QgsRectangle(
            min(min_layer.x(), max_layer.x()),
            min(min_layer.y(), max_layer.y()),
            max(min_layer.x(), max_layer.x()),
            max(min_layer.y(), max_layer.y()),
        )
        if rect.isEmpty():
            rect.grow(1e-9)
        return rect

    def _search_tolerance_project_units(self) -> float:
        canvas = self.canvas()
        width_px = max(canvas.width(), 1)
        extent = canvas.extent()
        return max(extent.width() / width_px * 10.0, 1e-9)

    def _project_crs(self) -> QgsCoordinateReferenceSystem:
        crs = self.canvas().mapSettings().destinationCrs()
        if crs.isValid():
            return crs
        return QgsCoordinateReferenceSystem("EPSG:4326")

    def _transform_point(
        self,
        point: QgsPointXY,
        source_crs: QgsCoordinateReferenceSystem,
        target_crs: QgsCoordinateReferenceSystem,
    ) -> QgsPointXY:
        if source_crs == target_crs:
            return QgsPointXY(point)
        transform = QgsCoordinateTransform(source_crs, target_crs, QgsProject.instance())
        return transform.transform(point)

    def _set_marker(self, project_point: QgsPointXY) -> None:
        if self.marker is None:
            self.marker = QgsVertexMarker(self.canvas())
            self.marker.setIconType(QgsVertexMarker.ICON_CIRCLE)
            self.marker.setIconSize(14)
            self.marker.setPenWidth(3)
            self.marker.setColor(QColor(230, 90, 25))
        self.marker.setCenter(project_point)


def _candidate_point(
    geometry: QgsGeometry,
    layer_point: QgsPointXY,
    geometry_type: QgsWkbTypes.GeometryType,
) -> tuple[QgsPointXY | None, str]:
    vertex = _closest_vertex(geometry, layer_point)
    if vertex is not None:
        if geometry_type == QgsWkbTypes.PointGeometry:
            return vertex, "active point feature"
        return vertex, "nearest active-layer vertex"

    centroid = geometry.centroid()
    if centroid is not None and not centroid.isEmpty():
        point = centroid.asPoint()
        return QgsPointXY(point.x(), point.y()), "active-layer centroid"
    return None, ""


def _closest_vertex(geometry: QgsGeometry, point: QgsPointXY) -> QgsPointXY | None:
    try:
        closest = geometry.closestVertex(point)
    except Exception:
        return None
    if not closest or closest[1] < 0:
        return None
    vertex = closest[0]
    return QgsPointXY(vertex.x(), vertex.y())


def _distance_sq(first: QgsPointXY, second: QgsPointXY) -> float:
    dx = first.x() - second.x()
    dy = first.y() - second.y()
    return dx * dx + dy * dy
