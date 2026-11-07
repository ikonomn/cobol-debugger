"""Standalone PyQt5 protocol viewer; no debugger internals imported."""
import argparse
import re
import json
import sys
from pathlib import Path
from . import __version__
from .session_log import SessionLog, default_log_directory
from .ide_project import build_plan, project_root
from .flowchart import FlowchartDialog
from .icons import action_icon
from PyQt5.QtCore import QProcess, QProcessEnvironment, Qt, pyqtSignal, QRect, QUrl, QSize, QTimer
from PyQt5.QtGui import QTextCursor, QColor, QTextFormat, QSyntaxHighlighter, QTextCharFormat, QFont, QFontDatabase, QPainter, QDesktopServices, QGuiApplication, QCursor, QIcon
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                            QPushButton, QPlainTextEdit, QFileDialog, QInputDialog, QTabWidget, QLineEdit, QLabel, QSplitter, QTextEdit, QStyle, QStyleOptionButton, QTableWidget, QTableWidgetItem, QHeaderView, QDialog, QGridLayout, QLayout, QSizePolicy, QDialogButtonBox, QMessageBox, QTextBrowser)

SHOW_BREAKPOINT_BUTTON = False
RESOURCES = Path(__file__).with_name('resources')


def examples_directory():
    if getattr(sys, 'frozen', False):
        candidates = [Path(sys.executable).resolve().parent / 'examples']
    else:
        candidates = [
            Path(__file__).resolve().parents[1] / 'examples',
            Path(sys.prefix) / 'share/doc/cobgdb-python/examples',
            Path('/usr/share/doc/cobgdb-python/examples'),
        ]
    return next((folder for folder in candidates if folder.is_dir()), None)


class CobolHighlighter(QSyntaxHighlighter):
    """Color fixed-format COBOL without changing source text or line numbers."""
    keywords = set(('ACCEPT ADD ASSIGN CALL CLOSE COMPUTE CONTINUE COPY DATA DECLARATIVES '
        'DELETE DISPLAY DIVIDE ELSE END END-ACCEPT END-ADD END-CALL END-COMPUTE '
        'END-DISPLAY END-DIVIDE END-EVALUATE END-IF END-MULTIPLY END-PERFORM END-READ '
        'END-SEARCH END-STRING END-SUBTRACT END-WRITE ENVIRONMENT EVALUATE EXIT FD '
        'FILE FILE-CONTROL GIVING GOBACK IDENTIFICATION IF INITIALISE INITIALIZE '
        'INPUT-OUTPUT INSPECT MOVE MULTIPLY OPEN ORGANIZATION PERFORM PROCEDURE '
        'PROGRAM-ID READ REDEFINES REWRITE SEARCH SECTION SELECT SPECIAL-NAMES '
        'STOP STRING SUBTRACT UNSTRING UNTIL VARYING WHEN WORKING-STORAGE WRITE').split())
    clauses = set(('ACCESS ADVANCING ALL AND ARE ASCENDING BY COMMA CONFIGURATION '
        'CONTAINS DECIMAL-POINT DESCENDING DISK DIVISION FROM INDEXED INPUT INTO IS '
        'LINE NOT OCCURS OF ON OR OUTPUT PIC PICTURE RECORD RECORDS SEQUENTIAL '
        'THEN THROUGH THRU TIMES TO USAGE USING VALUE VALUES WITH').split())
    constants = set(('FALSE TRUE ZERO ZEROS ZEROES SPACE SPACES HIGH-VALUES LOW-VALUES '
        'COMMAND-LINE FUNCTION MOD INTEGER-OF-DAY DATE-OF-INTEGER').split())

    @staticmethod
    def style(color, bold=False):
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        if bold:
            fmt.setFontWeight(QFont.Bold)
        return fmt

    def highlightBlock(self, text):
        marker = self.style('#c62828', True)
        self.setFormat(0, 8, self.style('#718096'))
        if text.startswith('●'):
            self.setFormat(0, 1, marker)
        # Display prefix is 8 characters: marker, space, five digits, space.
        # Actual prefix includes two spaces following the number (9 characters).
        start = 9
        content = text[start:]
        comment = self.style('#637c4b')
        if len(content) > 6 and content[6] in ('*', '/'):
            self.setFormat(start, len(content), comment)
            return
        token_pattern = r"\*>.*|\"(?:[^\"]|\"\")*\"|'(?:[^']|'')*'|[A-Za-z][A-Za-z0-9-]*|\b\d+(?:[.,]\d+)?\b"
        for match in re.finditer(token_pattern, content):
            token = match.group()
            upper = token.upper()
            if token.startswith('*>'):
                fmt = comment
            elif token.startswith(('\"', "'")):
                fmt = self.style('#a34b12')
            elif upper in self.keywords:
                fmt = self.style('#1659ad', True)
            elif upper in self.clauses:
                fmt = self.style('#7746a2')
            elif upper in self.constants:
                fmt = self.style('#007e83', True)
            elif token[0].isdigit():
                fmt = self.style('#007e83')
            else:
                continue
            self.setFormat(start + match.start(), len(token), fmt)

class BreakpointGutter(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor
        self.setToolTip('Click a checkbox to add or remove a breakpoint')
        self.setCursor(Qt.PointingHandCursor)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(event.rect(), QColor('#edf1f7'))
        for line, top, height in self.editor.visible_lines():
            option = QStyleOptionButton()
            option.initFrom(self)
            size = self.style().pixelMetric(QStyle.PM_IndicatorWidth)
            option.rect = QRect((self.width() - size) // 2, top + (height-size)//2, size, size)
            option.state |= QStyle.State_Enabled
            option.state |= QStyle.State_On if line in self.editor.checked_lines else QStyle.State_Off
            self.style().drawControl(QStyle.CE_CheckBox, option, painter, self)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            for line, top, height in self.editor.visible_lines():
                if top <= event.pos().y() < top + height:
                    self.editor.breakpointRequested.emit(line)
                    event.accept()
                    return
        super().mousePressEvent(event)

class SourceView(QPlainTextEdit):
    breakpointRequested = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.checked_lines = set()
        self.gutter = BreakpointGutter(self)
        self.gutter_width = 90
        self.setViewportMargins(self.gutter_width, 0, 0, 0)
        self.updateRequest.connect(lambda *_: self.gutter.update())
        self.blockCountChanged.connect(lambda *_: self.gutter.update())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        rect = self.contentsRect()
        self.gutter.setGeometry(QRect(rect.left(), rect.top(), self.gutter_width, rect.height()))

    def visible_lines(self):
        block = self.firstVisibleBlock()
        while block.isValid():
            top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
            height = round(self.blockBoundingRect(block).height())
            if top > self.viewport().height():
                break
            if block.isVisible() and top + height >= 0:
                yield block.blockNumber() + 1, top, height
            block = block.next()

    def on_line_number(self, position):
        left = self.document().documentMargin() - self.horizontalScrollBar().value()
        right = left + self.fontMetrics().horizontalAdvance(' ' * 9)
        return left <= position.x() < right

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.on_line_number(event.pos()):
            self.breakpointRequested.emit(self.cursorForPosition(event.pos()).blockNumber() + 1)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            if not self.on_line_number(event.pos()):
                self.breakpointRequested.emit(self.cursorForPosition(event.pos()).blockNumber() + 1)
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)

class SourceHeader(QWidget):
    """Use the same geometry as the editor, rather than layout approximations."""
    def __init__(self, editor):
        super().__init__()
        self.editor = editor
        self.setFixedHeight(30)
        editor.horizontalScrollBar().valueChanged.connect(lambda _: self.update())
        editor.updateRequest.connect(lambda *_: self.update())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor('#e5ebf3'))
        painter.setPen(QColor('#253d57'))
        font = self.font()
        font.setBold(True)
        painter.setFont(font)
        editor = self.editor
        gutter = editor.gutter.geometry()
        painter.drawText(QRect(gutter.left(), 0, gutter.width(), self.height()),
                         Qt.AlignCenter, 'Breakpoint')
        # Match the document's left margin, fixed-width display prefix and scroll.
        origin = editor.viewport().geometry().left() + round(editor.document().documentMargin())
        origin -= editor.horizontalScrollBar().value()
        metrics = editor.fontMetrics()
        number_left = origin + metrics.horizontalAdvance('  ')
        number_right = origin + metrics.horizontalAdvance('      1')
        painter.save()
        painter.setClipRect(QRect(editor.viewport().geometry().left(), 0,
                                  editor.viewport().width(), self.height()))
        number_font = painter.font()
        number_font.setPointSize(9)
        painter.setFont(number_font)
        painter.drawText(QRect(editor.viewport().geometry().left(), 0,
                               number_right-editor.viewport().geometry().left(), self.height()),
                         Qt.AlignRight | Qt.AlignVCenter, 'Line number')
        painter.setFont(font)
        # Fixed-format COBOL has seven leading columns before its source area.
        source_left = origin + metrics.horizontalAdvance(' ' * 16)
        painter.drawText(QRect(source_left, 0, max(200,self.width()-source_left), self.height()),
                         Qt.AlignLeft | Qt.AlignVCenter, 'COBOL source line')
        painter.restore()

class WrappingToolbar(QWidget):
    """Keep every control reachable without imposing a screen-wide minimum."""
    def __init__(self):
        super().__init__()
        self.buttons = []
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def sizeHint(self):
        return QSize(600,self.minimumHeight())

    def minimumSizeHint(self):
        return QSize(0,30)

    def addWidget(self, button):
        button.setParent(self)
        self.buttons.append(button)
        self.reflow()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.reflow()

    def reflow(self):
        width = max(1,self.width())
        row = used = 0
        row_height = max((b.sizeHint().height() for b in self.buttons), default=25) + 6
        for button in self.buttons:
            size = button.sizeHint().width()
            if used and used + size > width:
                row += 1
                used = 0
            button.setGeometry(used,row*row_height,min(size,width),row_height-6)
            used += size + 6
        needed = (row+1)*row_height-6
        if self.height() != needed:
            self.setFixedHeight(needed)

class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('cobgdb-python — standalone debugger')
        self.setWindowIcon(QIcon(str(RESOURCES / 'cobgdb.svg')))
        help_menu = self.menuBar().addMenu('&Help')
        help_action = help_menu.addAction('Help Contents')
        help_action.setShortcut('F1')
        help_action.triggered.connect(self.show_help)
        help_menu.addAction('About COBGDB', self.show_about)
        self.resize(1000, 700)
        self.counter = 0
        self.buffer = b''
        self.variable_requests = set()
        self.previous_values = {}
        self.execution_state = 'idle'
        self.session_loaded = False
        self.terminal_mode = None
        self.workflow_started = False
        self.requests = {}
        self.buttons = {}
        self.build_active = False
        self.source_path = None
        self.breakpoints = {}
        self.pending_breakpoints = {}
        self.source_lines = []
        self.paused_line = None
        self.compile_reset_id = None
        self.compile_arguments = None
        self.compile_plan = None
        self.compile_program = 'cobc'
        self.current_executable = None
        self.compiled_executable = None
        self.compiler = QProcess(self)
        self.compiler.setProcessChannelMode(QProcess.MergedChannels)
        self.compiler.readyReadStandardOutput.connect(self.compiler_output)
        self.compiler.finished.connect(self.compile_finished)
        self.compiler.errorOccurred.connect(self.compiler_error)
        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self.receive)
        self.process.readyReadStandardError.connect(self.receive_errors)
        self.process.errorOccurred.connect(lambda _: self.append(self.messages, self.process.errorString() + '\n'))
        self.process.finished.connect(self.finished)
        layout = QVBoxLayout()
        toolbar = WrappingToolbar()
        self.toolbar = toolbar
        for key, title, callback in [('executable', 'Executable', self.launch), ('source', 'Source', self.open_source), ('flowchart', 'Flowchart', self.open_flowchart), ('compile', 'Compile with debug', self.compile_debug), ('breakpoint', 'Toggle breakpoint', self.breakpoint)]:
            button = QPushButton(title)
            button.setIcon(action_icon(key))
            self.buttons[key] = button
            button.clicked.connect(callback)
            if key == 'breakpoint' and not SHOW_BREAKPOINT_BUTTON:
                button.setParent(self)
                button.hide()
            else:
                toolbar.addWidget(button)
        for op in ['run', 'continue', 'next', 'step', 'finish', 'pause', 'variables', 'stack']:
            button = QPushButton('Next COBOL line' if op == 'next' else 'Step into external CALL' if op == 'step' else op.title())
            button.setIcon(action_icon(op))
            if op == 'step':
                button.setToolTip('Enter an external COBOL program invoked by CALL when debug metadata is available. Internal PERFORM step-into is not implemented. On ordinary statements this behaves like Next COBOL line.')
            if op == 'next':
                button.setToolTip('Advance over a COBOL operation. Separate statements or loop visits may stop on the same line. Breakpoints and signals are preserved.')
            self.buttons[op] = button
            button.clicked.connect(lambda checked=False, command=op: self.request_variables() if command == 'variables' else self.send(command))
            toolbar.addWidget(button)
        layout.addWidget(toolbar)
        tabs = QTabWidget()
        self.tabs = tabs
        self.messages = QPlainTextEdit()
        self.program_output = QPlainTextEdit()
        self.log = QPlainTextEdit()
        for title, pane, key in [('Debugger', self.messages, 'debugger'),
                                 ('Program output', self.program_output, 'output'),
                                 ('JSON events', self.log, 'events')]:
            pane.setReadOnly(True)
            pane.setFont(QFontDatabase.systemFont(QFontDatabase.FixedFont))
            tabs.addTab(pane, action_icon(key), title)
        self.build_output = QPlainTextEdit()
        self.build_output.setReadOnly(True)
        self.build_output.setFont(QFontDatabase.systemFont(QFontDatabase.FixedFont))
        tabs.addTab(self.build_output, action_icon('compile'), 'Compiler')
        self.program_output.setStyleSheet('QPlainTextEdit { background: #12212b; color: #b8efc5; }')
        self.messages.setStyleSheet('QPlainTextEdit { background: #f3f6fb; color: #234361; }')
        self.log.setStyleSheet('QPlainTextEdit { background: #18212e; color: #bdcce5; }')
        self.source = SourceView()
        self.source.breakpointRequested.connect(self.toggle_breakpoint)
        fixed_font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        fixed_font.setPointSize(11)
        self.source.setFont(fixed_font)
        self.highlighter = CobolHighlighter(self.source.document())
        self.source.setStyleSheet('QPlainTextEdit { background: #fafbfd; color: #202b3a; selection-background-color: #c8def9; selection-color: #16253a; }')
        self.source.setToolTip('Click a checkbox or line number to toggle a breakpoint. Double-click a source line also works.')
        self.source.setReadOnly(True)
        self.source.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.source_label = QLabel('')
        self.source_label.setWordWrap(True)
        self.source_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        source_panel = QWidget()
        source_layout = QVBoxLayout(source_panel)
        self.source_info_row = QHBoxLayout()
        self.source_info_row.setSpacing(12)
        self.source_info_row.addWidget(self.source_label, 3)
        source_layout.addLayout(self.source_info_row)
        self.source_header = SourceHeader(self.source)
        source_layout.addWidget(self.source_header)
        source_layout.addWidget(self.source)
        source_layout.setSpacing(2)
        splitter = QSplitter(Qt.Vertical)
        self.variables_table = QTableWidget(0, 3)
        self.variables_table.setHorizontalHeaderLabels(['COBOL variable', 'Value', 'Format'])
        self.variables_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.variables_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.variables_table.horizontalHeader().setStretchLastSection(True)
        variables_panel = QWidget()
        variables_layout = QVBoxLayout(variables_panel)
        self.variables_label = QLabel('COBOL variables — refresh when paused')
        variables_layout.addWidget(self.variables_label)
        variables_layout.addWidget(self.variables_table)
        self.flowchart = FlowchartDialog(self)
        self.flowchart.lineSelected.connect(self.select_flow_line)
        self.variables_dialog = QDialog(self)
        self.variables_dialog.setWindowTitle('COBOL variables')
        self.variables_dialog.resize(700, 500)
        popup_layout = QVBoxLayout(self.variables_dialog)
        popup_layout.addWidget(variables_panel)
        splitter.addWidget(source_panel)
        splitter.addWidget(tabs)
        layout.addWidget(splitter)
        input_row = QHBoxLayout()
        self.input_text = QLineEdit()
        self.input_text.setPlaceholderText('Program input (for example: 2026) — Enter to send')
        self.input_text.returnPressed.connect(self.send_input)
        send_button = QPushButton('Send input')
        send_button.setIcon(action_icon('input'))
        self.buttons['input'] = send_button
        send_button.clicked.connect(self.send_input)
        input_row.addWidget(self.input_text)
        input_row.addWidget(send_button)
        layout.addLayout(input_row)
        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)
        self.session_log = None
        try:
            self.session_log = SessionLog(default_log_directory())
            self.log_path_label = QLabel('Log: ' + self.session_log.path.name)
            self.log_path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            self.log_path_label.setWordWrap(True)
            self.log_path_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
            self.log_path_label.setToolTip(str(self.session_log.path))
            self.source_info_row.addWidget(self.log_path_label, 2)
            open_log = QPushButton('Open log file')
            open_log.setIcon(action_icon('log'))
            self.buttons['log'] = open_log
            open_log.clicked.connect(self.open_log_file)
            self.source_info_row.addWidget(open_log)
            self.append(self.messages, 'Debug log file: ' + str(self.session_log.path) + '\n')
        except OSError as exc:
            self.append(self.messages, f'Could not create session log: {exc}\n')
        self.update_controls()
        self.fit_screen(initial=True)
        arguments = ['--cobgdb-backend'] if getattr(sys, 'frozen', False) else ['-u', '-m', 'cobgdb_python.backend']
        self.process.start(sys.executable, arguments)

    def fit_screen(self, screen=None, initial=False):
        screen = screen or (QGuiApplication.screenAt(QCursor.pos()) if initial else self.screen()) or QGuiApplication.primaryScreen()
        if not screen:
            return
        available = screen.availableGeometry()
        # Allow for native window borders/title bar, not included in widget size.
        frame = self.frameGeometry()
        border_width = max(8, frame.width()-self.width())
        border_height = max(36, frame.height()-self.height())
        width = max(1, available.width()-border_width-16)
        height = max(1, available.height()-border_height-16)
        self.setMaximumSize(width,height)
        self.resize(min(1000 if initial else self.width(),width),
                    min(700 if initial else self.height(),height))
        if initial:
            self.move(available.left()+8,available.top()+8)
        else:
            self.move(max(available.left(),min(self.x(),available.right()-self.frameGeometry().width()+1)),
                      max(available.top(),min(self.y(),available.bottom()-self.frameGeometry().height()+1)))

    def showEvent(self, event):
        super().showEvent(event)
        if not getattr(self, '_screen_hooked', False) and self.windowHandle():
            self._screen_hooked = True
            self.windowHandle().screenChanged.connect(lambda screen: self.fit_screen(screen))
            for screen in QGuiApplication.screens():
                screen.availableGeometryChanged.connect(lambda _: self.fit_screen())
        QTimer.singleShot(0, self.fit_screen)

    def update_controls(self):
        busy = self.build_active or self.compile_reset_id is not None
        loaded = self.session_loaded and not busy
        paused = loaded and self.execution_state == 'paused'
        running = loaded and self.execution_state == 'running'
        source = self.workflow_started and bool(self.source_path) and not busy
        pending = any(op in ('run', 'continue', 'next', 'finish', 'pause', 'launch', 'reset')
                      for op in self.requests.values())
        allowed = {
            'executable': not self.session_loaded and not busy and not pending,
            'source': self.workflow_started and not busy and not running and not pending,
            'flowchart': source,
            'compile': source and not running and not pending,
            'breakpoint': source and loaded and not running and not pending,
            'run': source and loaded and self.execution_state in ('ready', 'exited') and not pending,
            'continue': paused and not pending,
            'next': paused and not pending,
            'step': paused and not pending,
            'finish': paused and not pending,
            'pause': running and not any(op == 'pause' for op in self.requests.values()),
            'variables': paused and not pending,
            'stack': paused and not pending,
            'input': (paused or running) and self.terminal_mode == 'embedded',
            'log': self.session_loaded,
        }
        for key, button in self.buttons.items():
            button.setEnabled(allowed.get(key, False))
        self.buttons['compile'].setText('Compile with debug')
        self.buttons['compile'].setToolTip(
            'Build independently using config/project.json and its Debug compilation setting.'
            if self.source_path and project_root(self.source_path) else
            'Compile a standalone source with debugging options.')
        self.input_text.setEnabled(allowed['input'])
        self.source.gutter.setEnabled(allowed['breakpoint'])
        self.toolbar.reflow()

    def show_help(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('COBGDB Help')
        dialog.resize(640, 520)
        layout = QVBoxLayout(dialog)
        browser = QTextBrowser(dialog)
        browser.setMarkdown((RESOURCES / 'help.md').read_text(encoding='utf-8'))
        layout.addWidget(browser)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.exec_()

    def show_about(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('About COBGDB')
        layout = QVBoxLayout(dialog)
        heading = QLabel(dialog)
        heading.setPixmap(self.windowIcon().pixmap(48, 48))
        layout.addWidget(heading)
        layout.addWidget(QLabel(f'COBGDB {__version__}'))
        layout.addWidget(QLabel('Independent graphical debugger for GnuCOBOL using GDB.'))
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        examples = buttons.addButton('Examples', QDialogButtonBox.ActionRole)
        examples.setIcon(action_icon('source'))
        examples.clicked.connect(self.open_examples)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.exec_()

    def open_examples(self):
        folder = examples_directory()
        if folder is None:
            QMessageBox.information(self, 'Examples', 'No COBGDB examples directory was found.')
        elif not QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder))):
            QMessageBox.warning(self, 'Examples', 'Could not open ' + str(folder))

    def open_log_file(self):
        if self.session_log:
            if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.session_log.path))):
                self.append(self.messages, 'Could not open log file: ' + str(self.session_log.path) + '\n')

    def record_log(self, kind, data):
        if self.session_log:
            try:
                self.session_log.write(kind, data)
            except OSError as exc:
                self.append(self.messages, f'Log write failed: {exc}\n')
                try:
                    self.session_log.file.close()
                except OSError:
                    pass
                self.session_log = None

    def send(self, command, arguments=None):
        self.counter += 1
        self.requests[self.counter] = command
        logged_arguments = dict(arguments or {})
        if 'environment' in logged_arguments:
            logged_arguments['environment'] = {key: '<redacted>' for key in logged_arguments['environment']}
        self.record_log('command', {'id': self.counter, 'command': command, 'arguments': logged_arguments})
        self.append(self.messages, '> ' + command + '\n')
        self.process.write((json.dumps({'id': self.counter, 'command': command,
                                       'arguments': arguments or {}}) + '\n').encode())
        self.update_controls()
        return self.counter

    def launch(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Choose executable')
        if path:
            self.load_executable(path)

    def load_executable(self, path, source=None):
        """Load from either the chooser or command line, without running it."""
        try:
            plan = build_plan(source, path) if source and project_root(source) else None
            arguments = self.launch_arguments(path, plan)
            if source:
                self.show_source(source)
            self.send('launch', arguments)
        except (ValueError, RuntimeError, OSError) as exc:
            self.append(self.messages, 'Project configuration error: ' + str(exc) + '\n')
            self.tabs.setCurrentWidget(self.messages)

    def launch_arguments(self, path, plan=None):
        if plan is None and project_root(path):
            plan = build_plan(path)
        result = {'executable': str(path)}
        if plan:
            if plan.module:
                raise ValueError('This is a callable module. Select the caller executable to debug it.')
            result.update(cwd=plan.runtime_cwd, environment=plan.runtime_environment)
        return result

    def open_flowchart(self):
        if not self.source_path:
            self.open_source()
        if not self.source_path:
            return
        self.flowchart.load_source(self.source_path, '\n'.join(self.source_lines))
        self.flowchart.highlight(self.paused_line)
        self.flowchart.show()
        self.flowchart.raise_()

    def select_flow_line(self, line):
        if self.flowchart.source_path:
            paused = self.paused_line
            self.show_source(self.flowchart.source_path)
            self.paused_line = paused
            self.render_source()
            block = self.source.document().findBlockByNumber(line - 1)
            if block.isValid():
                self.source.setTextCursor(QTextCursor(block))
                self.source.centerCursor()

    def request_variables(self):
        self.variables_dialog.show()
        if self.execution_state != 'paused':
            self.variables_label.setText('Values refresh at the next pause; program is ' + self.execution_state)
            return
        if not self.variable_requests:
            self.variable_requests.add(self.send('cobol_variables'))

    def display_variables(self, rows):
        self.variables_table.setRowCount(len(rows))
        current = {}
        for index, row in enumerate(rows):
            key = row['name']
            current[key] = row['value']
            changed = key in self.previous_values and self.previous_values[key] != row['value']
            for column, value in enumerate([key, row['value'], row['format']]):
                item = QTableWidgetItem(str(value))
                if changed:
                    item.setBackground(QColor('#fff0a8'))
                if row.get('error'):
                    item.setToolTip(row['error'])
                self.variables_table.setItem(index, column, item)
        self.previous_values = current
        self.variables_label.setText(f'COBOL variables ({len(rows)}) — changed values highlighted')

    def compile_debug(self):
        if self.compiler.state() != QProcess.NotRunning or self.compile_reset_id is not None:
            return
        if not self.source_path:
            self.open_source()
        if not self.source_path:
            return
        source = Path(self.source_path).resolve()
        self.compile_plan = None
        try:
            self.compile_plan = build_plan(source, self.current_executable)
            if self.compile_plan:
                plan = self.compile_plan
                source = plan.source
                self.compiled_executable = plan.output
                self.compile_program = plan.program
                arguments = plan.arguments
                build = plan.root
                environment = QProcessEnvironment()
                for key, value in plan.environment.items():
                    environment.insert(key, value)
                self.compiler.setProcessEnvironment(environment)
            else:
                if source.suffix.lower() in ('.cbsql', '.cpy'):
                    raise ValueError('Select the original COBOL source or an OpenCobolIDE project; this file needs its project build pipeline.')
                build = source.parent / 'build'
                build.mkdir(exist_ok=True)
                self.compiled_executable = build / (source.stem + ('.exe' if sys.platform == 'win32' else ''))
                self.compile_program = 'cobc'
                arguments = ['-g', '-fsource-location', '-ftraceall', '-O0', '-save-temps',
                             '-x', '-o', str(self.compiled_executable), str(source)]
                self.compiler.setProcessEnvironment(QProcessEnvironment.systemEnvironment())
        except (OSError, ValueError, RuntimeError) as exc:
            self.append(self.messages, 'Build configuration error: ' + str(exc) + '\n')
            self.tabs.setCurrentWidget(self.messages)
            return
        self.build_active = True
        self.build_output.clear()
        self.tabs.setCurrentWidget(self.build_output)
        self.append(self.build_output, 'Compiling: ' + str(source) + '\n')
        if self.compile_plan:
            self.append(self.build_output, 'Using internal project compiler and config/project.json. Project root: ' + str(build) + '\n')
            if self.compile_plan.missing_debug_flags:
                self.append(self.build_output, 'Warning: project settings omit debug options: ' + ' '.join(self.compile_plan.missing_debug_flags) + '. Settings are preserved; enable debug compilation in the project configuration if required.\n')
        self.compiler.setWorkingDirectory(str(build))
        self.statusBar().showMessage('Compiling…')
        self.compile_arguments = arguments
        self.compile_reset_id = self.send('reset')
        self.breakpoints.clear()
        self.pending_breakpoints.clear()
        self.paused_line = None
        self.render_source()

    def compiler_output(self):
        text = bytes(self.compiler.readAllStandardOutput()).decode('utf-8', errors='replace')
        if text:
            self.record_log('compiler_output', text)
            self.append(self.build_output, text)

    def compiler_error(self, error):
        self.build_active = False
        self.update_controls()
        self.append(self.build_output, self.compiler.errorString() + '\n')
        self.statusBar().showMessage('Compiler error — see Compiler tab')

    def compile_finished(self, code, status):
        self.build_active = False
        self.update_controls()
        self.record_log('compiler_finished', {'code': code, 'status': int(status)})
        self.compiler_output()
        if code == 0 and status == QProcess.NormalExit:
            self.append(self.build_output, f'Build succeeded: {self.compiled_executable}\n')
            if self.compile_plan and self.compile_plan.module:
                self.append(self.build_output, 'Callable module built. Select its caller executable to debug; a module is not launched directly.\n')
                self.statusBar().showMessage('Project module build complete')
            else:
                self.append(self.build_output, 'Debug session loading. Add breakpoints, then click Run.\n')
                self.statusBar().showMessage('Build succeeded — loading debug session')
                self.send('launch', self.launch_arguments(self.compiled_executable, self.compile_plan))
        else:
            self.append(self.build_output, f'Build failed (exit {code}).\n')
            self.statusBar().showMessage('Build failed — see Compiler tab')

    @staticmethod
    def source_key(path):
        return str(Path(path).resolve()).casefold() if sys.platform == 'win32' else str(Path(path).resolve())

    def breakpoint(self):
        if not self.source_path:
            self.open_source()
        if self.source_path:
            self.toggle_breakpoint(self.source.textCursor().blockNumber() + 1)

    def toggle_breakpoint(self, line):
        if not self.buttons['breakpoint'].isEnabled():
            return
        if not self.source_path or not 1 <= line <= len(self.source_lines):
            return
        key = (self.source_key(self.source_path), line)
        if key in self.pending_breakpoints.values():
            return
        if key in self.breakpoints:
            request = self.send('remove_breakpoint', {'number': self.breakpoints[key]})
        else:
            request = self.send('add_breakpoint', {'file': self.source_path, 'line': line})
        self.pending_breakpoints[request] = key

    def render_source(self):
        if not self.source_path:
            return
        scroll = self.source.verticalScrollBar().value()
        cursor_line = self.source.textCursor().blockNumber()
        file_key = self.source_key(self.source_path)
        self.source.checked_lines = {n for (file, n) in self.breakpoints if file == file_key}
        self.source.setPlainText('\n'.join(
            f"  {n:5}  {content}"
            for n, content in enumerate(self.source_lines, 1)))
        self.source.setExtraSelections([])
        block = self.source.document().findBlockByNumber(cursor_line)
        if block.isValid():
            self.source.setTextCursor(QTextCursor(block))
        if self.paused_line:
            block = self.source.document().findBlockByNumber(self.paused_line - 1)
            if block.isValid():
                selection = QTextEdit.ExtraSelection()
                selection.cursor = QTextCursor(block)
                selection.format.setBackground(QColor('#ffeb99'))
                selection.format.setProperty(QTextFormat.FullWidthSelection, True)
                self.source.setExtraSelections([selection])
        self.source.verticalScrollBar().setValue(scroll)
        self.source.gutter.update()

    def send_input(self):
        self.send('input', {'text': self.input_text.text()})
        self.input_text.clear()

    def open_source(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Choose COBOL source', '', 'COBOL (*.cob *.cbl *.cbsql);;All files (*)')
        if path:
            self.show_source(path)

    def show_source(self, path, line=None):
        try:
            raw = Path(path).read_bytes()
            try:
                text = raw.decode('utf-8-sig')
            except UnicodeDecodeError:
                text = raw.decode('cp1253', errors='replace')
            self.source_lines = text.splitlines()
            self.source_path = path
            self.paused_line = int(line) if line else None
            self.source_label.setText(str(path) + (f' — line {line}' if line else ''))
            self.source_label.setToolTip(str(path) + '\nClick a checkbox or line number to toggle a breakpoint.')
            self.render_source()
            self.update_controls()
            if line:
                block = self.source.document().findBlockByNumber(int(line) - 1)
                if block.isValid():
                    self.source.setTextCursor(QTextCursor(block))
                    self.source.centerCursor()
        except (OSError, UnicodeError) as exc:
            self.source.setExtraSelections([])
            self.source_label.setText(f'Source unavailable: {path}')
            self.append(self.messages, str(exc) + '\n')

    def receive(self):
        self.buffer += bytes(self.process.readAllStandardOutput())
        while b'\n' in self.buffer:
            line, self.buffer = self.buffer.split(b'\n', 1)
            self.handle_line(line)

    @staticmethod
    def append(pane, text):
        cursor = pane.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)
        pane.setTextCursor(cursor)
        pane.ensureCursorVisible()

    def receive_errors(self):
        text = bytes(self.process.readAllStandardError()).decode('utf-8', errors='replace')
        if text:
            self.record_log('backend_stderr', text)
            self.append(self.messages, text)

    def handle_line(self, line):
        text = line.decode('utf-8', errors='replace')
        self.append(self.log, text + '\n')
        try:
            message = json.loads(text)
        except ValueError:
            self.record_log('backend_unparsed', text)
            self.append(self.messages, text + '\n')
            return
        self.record_log('backend_message', message)
        operation = self.requests.pop(message.get('id'), None)
        if operation == 'launch' and message.get('ok'):
            self.session_loaded = True
            self.workflow_started = True
            self.execution_state = 'ready'
            result = message.get('result', {})
            self.current_executable = result.get('executable')
            self.terminal_mode = result.get('terminal_mode')
            self.program_output.clear()
            source = result.get('source')
            if source:
                self.show_source(source)
                self.append(self.messages, 'Source opened automatically: ' + source + '\n')
            else:
                self.source_path = None
                self.source_lines = []
                self.source.clear()
                self.source_label.setText('Select Source — automatic source selection unavailable')
                self.append(self.messages, result.get('source_notice', 'Select Source manually') + '\n')
        elif operation == 'reset' and message.get('ok'):
            self.session_loaded = False
            self.execution_state = 'idle'
        elif message.get('event') == 'backend_gdb_exited':
            self.session_loaded = False
            self.execution_state = 'idle'

        if self.compile_reset_id is not None and message.get('id') == self.compile_reset_id:
            self.compile_reset_id = None
            if message.get('ok'):
                self.record_log('compiler_started', {'program': self.compile_program, 'arguments': self.compile_arguments, 'cwd': self.compiler.workingDirectory()})
                self.compiler.start(self.compile_program, self.compile_arguments)
            else:
                self.build_active = False
                self.append(self.build_output, 'Could not stop debugger; build canceled.\n')
        if message.get('id') in self.variable_requests:
            self.variable_requests.discard(message['id'])
            if message.get('ok'):
                self.display_variables(message.get('result', {}).get('variables', []))
            else:
                self.variables_table.setRowCount(0)
                self.variables_label.setText('Variables unavailable at this stop')
        request_key = self.pending_breakpoints.pop(message.get('id'), None)
        if request_key and message.get('ok'):
            bkpt = message.get('result', {}).get('bkpt')
            if bkpt:
                self.breakpoints[request_key] = bkpt['number']
                if bkpt.get('addr') == '<PENDING>':
                    self.append(self.messages, 'Breakpoint pending: source location not yet resolved.\n')
            else:
                self.breakpoints.pop(request_key, None)
            self.render_source()
        if message.get('event') == 'stopped':
            self.execution_state = 'paused'
            self.variables_table.setEnabled(True)
            self.variables_label.setText('Refreshing values at current pause…')
            self.request_variables()
            location = message.get('location')
            if location:
                self.show_source(location['file'], location['line'])
                if self.flowchart.isVisible():
                    self.flowchart.load_source(self.source_path, '\n'.join(self.source_lines))
                    self.flowchart.highlight(location['line'])
                self.statusBar().showMessage(f"Paused: {location['file']} — COBOL line {location['line']}")
            else:
                self.source.setExtraSelections([])
                self.statusBar().showMessage('Paused outside mapped COBOL source')
        elif message.get('event') == 'running':
            self.execution_state = 'running'
            self.variable_requests.clear()
            self.variables_table.setEnabled(False)
            self.paused_line = None
            self.source.setExtraSelections([])
            self.flowchart.highlight(None, observe=False)
            self.variables_label.setText('Running — showing values from previous pause')
            self.statusBar().showMessage('Running')
        elif message.get('event') == 'exited':
            self.execution_state = 'exited'
            self.variable_requests.clear()
            self.variables_table.setEnabled(False)
            self.paused_line = None
            self.source.setExtraSelections([])
            self.flowchart.highlight(None, observe=False)
            self.variables_label.setText('Program exited — showing last paused values')
            self.statusBar().showMessage('Program exited')
        if message.get('event') == 'output':
            pane = self.program_output if message.get('channel') in ('@', 'output', 'program') else self.messages
            self.append(pane, message.get('text', ''))
        elif message.get('ok') is False:
            self.append(self.messages, 'Error: ' + message.get('error', '') + '\n')
        else:
            self.append(self.messages, json.dumps(message, indent=2, ensure_ascii=False) + '\n')

        self.update_controls()

    def finished(self, code, status):
        self.receive()
        self.receive_errors()
        if self.buffer:
            self.handle_line(self.buffer)
            self.buffer = b''
        self.append(self.messages, f'Backend exited ({code}).\n')

    def closeEvent(self, event):
        self.variables_dialog.close()
        self.flowchart.close()
        if self.compiler.state() != QProcess.NotRunning:
            self.compiler.kill()
            self.compiler.waitForFinished(1000)
        self.send('shutdown')
        if not self.process.waitForFinished(3000):
            self.process.kill()
            self.process.waitForFinished(1000)
        if self.session_log:
            try:
                self.session_log.close()
            except OSError:
                pass
        event.accept()

def parse_launch_arguments(argv=None):
    parser = argparse.ArgumentParser(description='Independent graphical GnuCOBOL debugger')
    parser.add_argument('executable', nargs='?', help='compiled executable to load (optional)')
    parser.add_argument('--source', help='original COBOL source for the executable')
    args = parser.parse_args(argv)
    if args.source and not args.executable:
        parser.error('--source requires an executable')
    for name in ('executable', 'source'):
        value = getattr(args, name)
        if value:
            path = Path(value).expanduser().resolve()
            if not path.is_file():
                parser.error(f'{name} does not exist: {path}')
            setattr(args, name, str(path))
    return args


def main(argv=None):
    args = parse_launch_arguments(argv)
    app = QApplication([sys.argv[0]])
    window = Window()
    window.show()
    if args.executable:
        def load():
            window.load_executable(args.executable, args.source)
        if window.process.state() == QProcess.Running:
            QTimer.singleShot(0, load)
        else:
            window.process.started.connect(load)
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
