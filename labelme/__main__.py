import argparse
import codecs
import contextlib
import os
import os.path as osp
import sys
import traceback
import time

import yaml
from loguru import logger
from PyQt5 import QtCore
from PyQt5 import QtWidgets

from labelme import __appname__
from labelme import __version__
from labelme.app import MainWindow
from labelme.config import get_config
from labelme.utils import newIcon

# ============================================
# 单实例检测 - 使用QSharedMemory实现
# ============================================

# 唯一标识符，用于共享内存
SHARED_MEMORY_KEY = "B2E8F272-34FB-4465-8618-AC5619782F68"


def _get_app_dir():
    if getattr(sys, "frozen", False):
        return osp.dirname(sys.executable)
    package_dir = osp.dirname(osp.abspath(__file__))
    return osp.dirname(package_dir)


def check_single_instance():
    """
    Use QSharedMemory to check if an instance is already running
    
    Returns:
        tuple: (can_start, shared_memory_object)
    """
    try:
        shared_memory = QtCore.QSharedMemory(SHARED_MEMORY_KEY)

        if shared_memory.attach():
            shared_memory.detach()
            return False, None

        if shared_memory.create(1):
            return True, shared_memory

        if shared_memory.attach():
            shared_memory.detach()
            return False, None

        return True, None
    except Exception as e:
        logger.warning(f"Single instance check failed: {e}")
        return True, None


class _LoggerIO:
    """用于将 stderr 重定向到 loguru logger 的类"""
    def write(self, message):
        if message.strip():
            logger.error(message.strip())

    def flush(self):
        pass


def _setup_loguru(logger_level: str) -> None:
    try:
        logger.remove(handler_id=0)
    except ValueError:
        pass

    if sys.stderr:
        logger.add(sys.stderr, level=logger_level)

    cache_dir: str
    if os.name == "nt":
        cache_dir = os.path.join(os.environ["LOCALAPPDATA"], "labelme")
    else:
        cache_dir = os.path.expanduser("~/.cache/labelme")

    os.makedirs(cache_dir, exist_ok=True)

    log_file = os.path.join(cache_dir, "labelme.log")
    logger.add(
        log_file,
        colorize=True,
        level="DEBUG",
        rotation="10 MB",
        retention="30 days",
        compression="gz",
        enqueue=True,
        backtrace=True,
        diagnose=True,
    )


def _show_already_running_message():
    """显示应用程序已在运行的消息提示"""
    # 注释掉 user32 相关代码，避免可能的闪烁问题
    # import ctypes
    # from ctypes import wintypes
    # import os
    
    # # 加载 user32.dll
    # user32 = ctypes.WinDLL('user32', use_last_error=True)
    
    # # 定义 MessageBoxW 参数类型
    # user32.MessageBoxW.argtypes = [
    #     wintypes.HWND,      # hWnd
    #     wintypes.LPCWSTR,   # lpText
    #     wintypes.LPCWSTR,   # lpCaption
    #     wintypes.UINT       # uType
    # ]
    # user32.MessageBoxW.restype = wintypes.INT
    
    # # 显示消息框
    # # MB_ICONWARNING (0x30) | MB_OK (0x0) | MB_TOPMOST (0x40000) | MB_SETFOREGROUND (0x10000)
    # user32.MessageBoxW(
    #     0,
    #     "Labelme is already running!\n\nOnly one instance of Labelme can run at a time.",
    #     "Labelme Already Running",
    #     0x30 | 0x0 | 0x40000 | 0x10000  # MB_ICONWARNING | MB_OK | MB_TOPMOST | MB_SETFOREGROUND
    # )
    
    # 使用 Qt 弹窗替代 Windows 原生弹窗
    QtWidgets.QMessageBox.warning(
        None,
        "Labelme Already Running",
        "Labelme is already running!\n\nOnly one instance of Labelme can run at a time.",
        QtWidgets.QMessageBox.Ok
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", "-V", action="store_true", help="show version")
    parser.add_argument("--reset-config", action="store_true", help="reset qt config")
    parser.add_argument(
        "--logger-level",
        default="debug",
        choices=["debug", "info", "warning", "fatal", "error"],
        help="logger level",
    )
    parser.add_argument("filename", nargs="?", help="image or label filename")
    parser.add_argument(
        "--output",
        "-O",
        "-o",
        help="output file or directory (if it ends with .json it is "
        "recognized as file, else as directory)",
    )
    default_config_file = os.path.join(_get_app_dir(), ".labelmerc")
    parser.add_argument(
        "--config",
        dest="config",
        help="config file or yaml-format string (default: {})".format(
            default_config_file
        ),
        default=default_config_file,
    )
    # config for the gui
    parser.add_argument(
        "--nodata",
        dest="store_data",
        action="store_false",
        help="stop storing image data to JSON file",
        default=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--autosave",
        dest="auto_save",
        action="store_true",
        help="auto save",
        default=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--nosortlabels",
        dest="sort_labels",
        action="store_false",
        help="stop sorting labels",
        default=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--flags",
        help="comma separated list of flags OR file containing flags",
        default=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--labelflags",
        dest="label_flags",
        help=r"yaml string of label specific flags OR file containing json "
        r"string of label specific flags (ex. {person-\d+: [male, tall], "
        r"dog-\d+: [black, brown, white], .*: [occluded]})",  # NOQA
        default=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--labels",
        help="comma separated list of labels OR file containing labels",
        default=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--validatelabel",
        dest="validate_label",
        choices=["exact"],
        help="label validation types",
        default=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--keep-prev",
        action="store_true",
        help="keep annotation of previous frame",
        default=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--epsilon",
        type=float,
        help="epsilon to find nearest vertex on canvas",
        default=argparse.SUPPRESS,
    )
    args = parser.parse_args()

    if args.version:
        print("{0} {1}".format(__appname__, __version__))
        sys.exit(0)

    _setup_loguru(logger_level=args.logger_level.upper())

    if hasattr(args, "flags"):
        if os.path.isfile(args.flags):
            with codecs.open(args.flags, "r", encoding="utf-8") as f:
                args.flags = [line.strip() for line in f if line.strip()]
        else:
            args.flags = [line for line in args.flags.split(",") if line]

    if hasattr(args, "labels"):
        if os.path.isfile(args.labels):
            with codecs.open(args.labels, "r", encoding="utf-8") as f:
                args.labels = [line.strip() for line in f if line.strip()]
        else:
            args.labels = [line for line in args.labels.split(",") if line]

    if hasattr(args, "label_flags"):
        if os.path.isfile(args.label_flags):
            with codecs.open(args.label_flags, "r", encoding="utf-8") as f:
                args.label_flags = yaml.safe_load(f)
        else:
            args.label_flags = yaml.safe_load(args.label_flags)

    config_from_args = args.__dict__
    config_from_args.pop("version")
    reset_config = config_from_args.pop("reset_config")
    filename = config_from_args.pop("filename")
    output = config_from_args.pop("output")
    config_file_or_yaml = config_from_args.pop("config")
    config = get_config(config_file_or_yaml, config_from_args)

    if not config["labels"] and config["validate_label"]:
        logger.error(
            "--labels must be specified with --validatelabel or "
            "validate_label: true in the config file "
            "(ex. ~/.labelmerc)."
        )
        sys.exit(1)

    output_file = None
    output_dir = None
    if output is not None:
        if output.endswith(".json"):
            output_file = output
        else:
            output_dir = output

    translator = QtCore.QTranslator()
    translator.load(
        QtCore.QLocale.system().name(),
        osp.dirname(osp.abspath(__file__)) + "/translate",
    )
    app = QtWidgets.QApplication(sys.argv)
    
    # 检查是否已有实例在运行（必须在QApplication创建之后）
    can_start, shared_mem = check_single_instance()
    if not can_start:
        logger.error("Labelme instance is already running!")
        # 显示错误消息给用户（使用Windows原生API，不依赖Qt）
        _show_already_running_message()
        return 1
    
    app.setApplicationName(__appname__)
    app.setWindowIcon(newIcon("icon"))
    app.installTranslator(translator)
    win = MainWindow(
        config=config,
        filename=filename,
        output_file=output_file,
        output_dir=output_dir,
    )

    if reset_config:
        logger.info("Resetting Qt config: %s" % win.settings.fileName())
        win.settings.clear()
        sys.exit(0)

    # Install exception hook to catch all unhandled exceptions
    def exception_hook(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logger.exception(
            "Unhandled exception",
            exc_info=(exc_type, exc_value, exc_traceback)
        )
        # Show error dialog if QApplication exists
        try:
            if QtWidgets.QApplication.instance() is not None:
                error_msg = f"An error occurred:\n{exc_type.__name__}: {exc_value}"
                msg_box = QtWidgets.QMessageBox(None)  # 使用None作为父窗口
                msg_box.setIcon(QtWidgets.QMessageBox.Critical)
                msg_box.setWindowTitle("Error")
                msg_box.setText("An unhandled exception occurred")
                msg_box.setDetailedText(
                    "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
                )
                msg_box.exec_()
        except Exception:
            # If we can't show dialog, just print to stderr
            traceback.print_exception(exc_type, exc_value, exc_traceback)
    
    sys.excepthook = exception_hook

    with logger.catch(), contextlib.redirect_stderr(new_target=_LoggerIO()):
        try:
            win.show()
            win.raise_()
            sys.exit(app.exec_())
        except Exception as e:
            logger.exception("Exception in main event loop", exc_info=True)
            raise


# this main block is required to generate executable by pyinstaller
if __name__ == "__main__":
    try:
        exit_code = main()
        # 使用 os._exit 避免触发 SystemExit 异常（在调试时更友好）
        # 但只在显式返回错误码时使用
        if exit_code != 0:
            import os
            os._exit(exit_code)
    except SystemExit:
        raise  # 重新抛出，让 Python 正常处理
    except:
        import traceback
        traceback.print_exc()
        import os
        os._exit(1)
