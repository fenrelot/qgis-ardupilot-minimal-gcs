from __future__ import annotations

from typing import Any

from qgis.PyQt.QtCore import QVariant
from qgis.core import (
    QgsFeature,
    QgsField,
    QgsGeometry,
    QgsMarkerSymbol,
    QgsPointXY,
    QgsProject,
    QgsProperty,
    QgsSymbolLayer,
    QgsVectorLayer,
)

LAYER_NAME = "ArduBoat Live"
FIELD_NAMES = ["name", "mode", "heading_deg", "ground_speed_m_s"]


class LiveBoatLayer:
    def __init__(self) -> None:
        self.layer: QgsVectorLayer | None = None

    def ensure_layer(self) -> QgsVectorLayer:
        if self.layer is not None and self.layer.isValid():
            return self.layer

        matches = QgsProject.instance().mapLayersByName(LAYER_NAME)
        for layer in matches:
            if isinstance(layer, QgsVectorLayer) and layer.isValid():
                self.layer = layer
                self._ensure_fields(layer)
                self._style_layer(layer)
                return layer

        layer = QgsVectorLayer("Point?crs=EPSG:4326", LAYER_NAME, "memory")
        self._ensure_fields(layer)
        self._style_layer(layer)
        QgsProject.instance().addMapLayer(layer)
        self.layer = layer
        return layer

    def update_from_status(self, status: dict[str, Any]) -> None:
        lat = _as_float(status.get("lat"))
        lon = _as_float(status.get("lon"))
        if lat is None or lon is None:
            return

        layer = self.ensure_layer()
        provider = layer.dataProvider()
        existing_ids = [feature.id() for feature in layer.getFeatures()]
        if existing_ids:
            provider.deleteFeatures(existing_ids)

        feature = QgsFeature(layer.fields())
        feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(lon, lat)))
        feature.setAttributes(
            [
                "ArduBoat",
                status.get("mode") or "",
                _as_float(status.get("heading_deg")) or 0.0,
                _as_float(status.get("ground_speed_m_s")) or 0.0,
            ]
        )
        provider.addFeature(feature)
        layer.updateExtents()
        layer.triggerRepaint()

    def _ensure_fields(self, layer: QgsVectorLayer) -> None:
        existing = {field.name() for field in layer.fields()}
        fields = []
        if "name" not in existing:
            fields.append(QgsField("name", QVariant.String))
        if "mode" not in existing:
            fields.append(QgsField("mode", QVariant.String))
        if "heading_deg" not in existing:
            fields.append(QgsField("heading_deg", QVariant.Double))
        if "ground_speed_m_s" not in existing:
            fields.append(QgsField("ground_speed_m_s", QVariant.Double))
        if fields:
            layer.dataProvider().addAttributes(fields)
            layer.updateFields()

    def _style_layer(self, layer: QgsVectorLayer) -> None:
        symbol = QgsMarkerSymbol.createSimple(
            {
                "name": "triangle",
                "color": "0,122,204",
                "outline_color": "255,255,255",
                "outline_width": "0.4",
                "size": "6",
            }
        )
        symbol_layer = symbol.symbolLayer(0)
        if symbol_layer is not None:
            symbol_layer.setDataDefinedProperty(
                QgsSymbolLayer.PropertyAngle,
                QgsProperty.fromExpression('"heading_deg"'),
            )
        layer.renderer().setSymbol(symbol)
        layer.triggerRepaint()


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

