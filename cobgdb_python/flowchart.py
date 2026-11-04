"""Traditional flowchart popup driven by source and debugger pause events."""
import math
from pathlib import Path
import tempfile
import os
from PyQt5.QtCore import Qt, QPointF, QRectF, QMarginsF, pyqtSignal
from PyQt5.QtGui import QColor, QPen, QBrush, QPolygonF, QPainterPath, QPainter, QPdfWriter, QPageSize, QPageLayout, QFont
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                            QGraphicsView, QGraphicsScene, QGraphicsPolygonItem,
                            QGraphicsRectItem, QGraphicsEllipseItem, QFileDialog, QMessageBox)
from .flow_model import build_flow
from .flow_routes import route_edges
from .icons import action_icon

class FlowView(QGraphicsView):
    lineSelected = pyqtSignal(int)

    def mouseDoubleClickEvent(self, event):
        item = self.itemAt(event.pos())
        while item:
            line = item.data(0)
            if line:
                self.lineSelected.emit(int(line))
                return
            item = item.parentItem()
        super().mouseDoubleClickEvent(event)

class FlowchartDialog(QDialog):
    lineSelected = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('COBOL flowchart')
        self.resize(950, 750)
        self.model = None
        self.items = {}
        self.visited = set()
        self.source_path = None
        self.scene = QGraphicsScene(self)
        self.view = FlowView(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setDragMode(QGraphicsView.ScrollHandDrag)
        self.view.lineSelected.connect(self.lineSelected)
        layout = QVBoxLayout(self)
        self.caption = QLabel('Blocks: yellow = current pause; light blue = observed pause. Arrows: green Yes, orange No; other colors separate connections.')
        self.caption.setWordWrap(True)
        layout.addWidget(self.caption)
        self.status = QLabel('Double-click a block to display its COBOL line. Drag to pan; use +/− to zoom.')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        buttons = QHBoxLayout()
        for label, action in [('Zoom +', lambda: self.view.scale(1.2,1.2)),
                              ('Zoom −', lambda: self.view.scale(1/1.2,1/1.2)),
                              ('Reset zoom', lambda: self.view.resetTransform()),
                              ('Clear observed pauses', self.clear_history),
                              ('Export PDF', self.export_pdf)]:
            button = QPushButton(label)
            button.setIcon(action_icon(label))
            button.clicked.connect(action)
            buttons.addWidget(button)
        layout.addLayout(buttons)
        layout.addWidget(self.view)

    def load_source(self, path, text):
        if path == self.source_path and text == getattr(self, 'source_text', None):
            return
        self.source_path, self.source_text = path, text
        self.model = build_flow(text)
        self.visited.clear()
        self.scene.clear()
        self.items.clear()
        positions, self.connection_routes = route_edges(self.model)
        for route_index, connection in enumerate(self.connection_routes):
            points = [QPointF(x,y) for x,y in connection['points']]
            color = QColor(connection['color'])
            route = QPainterPath(points[0])
            for point in points[1:]:
                route.lineTo(point)
            # A white halo separates lines at crossings; tracks avoid shared spans.
            halo_pen = QPen(QColor('#ffffff'), 7)
            halo_pen.setJoinStyle(Qt.RoundJoin)
            halo = self.scene.addPath(route, halo_pen)
            halo.setZValue(-2*len(self.connection_routes)+2*route_index)
            pen = QPen(color, 2.4)
            pen.setJoinStyle(Qt.RoundJoin)
            edge = self.scene.addPath(route, pen)
            edge.setZValue(-2*len(self.connection_routes)+2*route_index+1)
            end = points[-1]
            previous = next(point for point in reversed(points[:-1]) if point != end)
            angle = math.atan2(end.y()-previous.y(),end.x()-previous.x())
            arrow = QPolygonF([end,QPointF(end.x()-11*math.cos(angle-.45),end.y()-11*math.sin(angle-.45)),
                                  QPointF(end.x()-11*math.cos(angle+.45),end.y()-11*math.sin(angle+.45))])
            arrow_item = self.scene.addPolygon(arrow,QPen(color),QBrush(color))
            arrow_item.setZValue(1)
            if connection['label']:
                tag = self.scene.addText(connection['label'])
                tag.setDefaultTextColor(color)
                tag.setPos(*connection['label_pos'])
                tag.setZValue(3)
                plate = self.scene.addRect(tag.sceneBoundingRect().adjusted(-2,0,2,0),
                                           QPen(Qt.NoPen),QBrush(QColor('#ffffff')))
                plate.setZValue(2)
        for n in self.model.nodes:
            x,y=positions[n.id]
            if n.kind=='decision':
                shape=QGraphicsPolygonItem(QPolygonF([QPointF(180,0),QPointF(360,50),QPointF(180,100),QPointF(0,50)]))
            elif n.kind=='io':
                shape=QGraphicsPolygonItem(QPolygonF([QPointF(24,0),QPointF(360,0),QPointF(336,100),QPointF(0,100)]))
            elif n.kind=='terminal':
                shape=QGraphicsEllipseItem(0,0,360,100)
            else:
                shape=QGraphicsRectItem(0,0,360,100)
            shape.setPos(x,y)
            shape.setPen(QPen(QColor('#31465f'),1.8))
            shape.setBrush(QBrush(QColor('#f0f5fb')))
            shape.setData(0,n.line)
            shape.setToolTip(f'Line {n.line}: {n.text}' if n.line else n.text)
            self.scene.addItem(shape)
            title=(f'L{n.line}: ' if n.line else '')+n.text
            if len(title)>115: title=title[:112]+'…'
            text_item=self.scene.addText(title)
            text_item.setParentItem(shape)
            text_item.setTextWidth(220 if n.kind=='decision' else 305)
            text_item.setDefaultTextColor(QColor('#172c43'))
            text_item.setPos(70 if n.kind=='decision' else 28, max(5, (100-text_item.boundingRect().height())/2))
            text_item.setData(0,n.line)
            self.items[n.id]=shape
        self.scene.setSceneRect(self.scene.itemsBoundingRect().adjusted(-30,-30,30,30))
        warning=' '.join(self.model.warnings[:4])
        self.status.setText(('Partial chart: '+warning) if warning else
                            'Source-derived paths. Double-click a block to show its COBOL line. +/− zoom; drag to pan.')
        self.view.resetTransform()
        self.view.scale(0.8, 0.8)
        self.view.centerOn(self.items[0])

    def export_pdf(self):
        if not self.model:
            return
        suggested = str(Path(self.source_path).with_suffix('.flowchart.pdf'))
        filename, _ = QFileDialog.getSaveFileName(self, 'Export flowchart to PDF', suggested, 'PDF files (*.pdf)')
        if not filename:
            return
        if not filename.lower().endswith('.pdf'):
            filename += '.pdf'
        try:
            pages = self.write_pdf(filename)
            QMessageBox.information(self, 'Flowchart exported', f'Exported {pages} page(s) to:\n{filename}')
        except (OSError, RuntimeError) as exc:
            QMessageBox.warning(self, 'PDF export failed', str(exc))

    def write_pdf(self, filename):
        """Vector PDF, tiled through row gaps so blocks are not split vertically."""
        if not self.model:
            raise RuntimeError('Open a source flowchart before exporting')
        destination = Path(filename).expanduser().resolve()
        with tempfile.NamedTemporaryFile(dir=destination.parent, suffix='.pdf', delete=False) as temp:
            temporary = Path(temp.name)
        painter = None
        try:
            writer = QPdfWriter(str(temporary))
            writer.setResolution(96)
            writer.setPageSize(QPageSize(QPageSize.A4))
            writer.setPageOrientation(QPageLayout.Portrait)
            writer.setPageMargins(QMarginsF(12,12,12,12))
            writer.setTitle('COBOL flowchart - ' + Path(self.source_path).name)
            writer.setCreator('cobgdb-python')
            width, height = writer.width(), writer.height()
            header, footer = 76, 32
            bounds = self.scene.itemsBoundingRect().adjusted(-30,-30,30,30)
            scale = min(1.0, width / bounds.width())
            # Wide charts use horizontal tiles instead of unreadably small labels.
            if scale < .85:
                scale = .85
                tile_width = max(500, math.floor(width / scale / 500) * 500)
            else:
                tile_width = bounds.width()
            tile_height = max(210, math.floor((height-header-footer) / scale / 210) * 210)
            columns = max(1, math.ceil(bounds.width()/tile_width))
            rows = max(1, math.ceil(bounds.height()/tile_height))
            painter = QPainter()
            if not painter.begin(writer):
                raise RuntimeError('Could not initialize PDF output')
            painter.setRenderHint(QPainter.Antialiasing)
            for row in range(rows):
                for col in range(columns):
                    number = row*columns+col+1
                    if number > 1 and not writer.newPage():
                        raise RuntimeError('Could not create PDF page')
                    painter.setPen(QColor('#172c43'))
                    painter.setFont(QFont('Sans Serif',12,QFont.Bold))
                    painter.drawText(QRectF(0,0,width,23), Qt.AlignLeft | Qt.AlignVCenter,
                                     'COBOL flowchart - ' + Path(self.source_path).name)
                    painter.setFont(QFont('Sans Serif',8))
                    painter.drawText(QRectF(0,25,width,20), Qt.AlignLeft | Qt.AlignVCenter,
                                     'Arrows: green Yes / orange No. Blocks: yellow current pause / light blue observed pause.')
                    painter.drawText(QRectF(0,45,width,25), Qt.AlignLeft | Qt.TextWordWrap,
                                     'Partial chart: unsupported control flow is not expanded.' if self.model.warnings else
                                     'Source-derived paths; debugger pauses do not constitute a complete execution trace.')
                    source = QRectF(bounds.left()+col*tile_width, bounds.top()+row*tile_height,
                                    tile_width, tile_height)
                    target = QRectF(0,header,tile_width*scale,tile_height*scale)
                    painter.save()
                    painter.setClipRect(QRectF(0,header,width,height-header-footer))
                    self.scene.render(painter,target,source,Qt.IgnoreAspectRatio)
                    painter.restore()
                    painter.setPen(QColor('#475569'))
                    painter.setFont(QFont('Sans Serif',8))
                    painter.drawText(QRectF(0,height-footer,width,footer), Qt.AlignLeft | Qt.AlignVCenter,
                                     f'Page {number}/{rows*columns} | row {row+1}/{rows}, column {col+1}/{columns} | Arrows at page edges continue on adjacent tiles.')
            if not painter.end():
                raise RuntimeError('Could not finish PDF output')
            painter = None
            del writer  # Close the file before replacement on Windows.
            if not temporary.exists() or temporary.stat().st_size == 0:
                raise RuntimeError('PDF output is empty')
            os.replace(temporary, destination)
            return rows*columns
        finally:
            if painter and painter.isActive():
                painter.end()
            if temporary.exists():
                temporary.unlink()

    def clear_history(self):
        self.visited.clear()
        self.highlight(None, observe=False)

    def highlight(self, line, observe=True):
        if not self.model:
            return
        current=self.model.at_line(line) if line else None
        if current and observe:
            self.visited.add(current.id)
        for key,item in self.items.items():
            color='#ffeb99' if current and key==current.id else '#cce5ff' if key in self.visited else '#f0f5fb'
            item.setBrush(QBrush(QColor(color)))
        if current:
            self.view.ensureVisible(self.items[current.id],60,60)
