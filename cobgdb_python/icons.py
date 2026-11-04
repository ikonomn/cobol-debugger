"""Desktop theme icons with portable Qt-style fallbacks."""
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QStyle


ICONS = {
    'executable': ('application-x-executable', QStyle.SP_ComputerIcon),
    'source': ('document-open', QStyle.SP_DialogOpenButton),
    'flowchart': ('view-flowchart', QStyle.SP_FileDialogListView),
    'compile': ('run-build', QStyle.SP_FileDialogDetailedView),
    'breakpoint': ('debug-breakpoint', QStyle.SP_DialogCancelButton),
    'run': ('media-playback-start', QStyle.SP_MediaPlay),
    'continue': ('debug-continue', QStyle.SP_MediaSkipForward),
    'next': ('debug-step-over', QStyle.SP_ArrowRight),
    'step': ('debug-step-into', QStyle.SP_ArrowDown),
    'finish': ('debug-step-out', QStyle.SP_ArrowUp),
    'pause': ('media-playback-pause', QStyle.SP_MediaPause),
    'variables': ('view-list-details', QStyle.SP_FileDialogDetailedView),
    'stack': ('view-list-tree', QStyle.SP_FileDialogListView),
    'debugger': ('debug-run', QStyle.SP_ComputerIcon),
    'output': ('utilities-terminal', QStyle.SP_ComputerIcon),
    'events': ('text-x-script', QStyle.SP_FileIcon),
    'input': ('mail-send', QStyle.SP_ArrowRight),
    'log': ('document-open', QStyle.SP_DialogOpenButton),
    'Zoom +': ('zoom-in', QStyle.SP_ArrowUp),
    'Zoom −': ('zoom-out', QStyle.SP_ArrowDown),
    'Reset zoom': ('zoom-original', QStyle.SP_BrowserReload),
    'Clear observed pauses': ('edit-clear', QStyle.SP_DialogResetButton),
    'Export PDF': ('document-export', QStyle.SP_DialogSaveButton),
}


def action_icon(key):
    theme, standard = ICONS[key]
    return QIcon.fromTheme(theme, QApplication.style().standardIcon(standard))
