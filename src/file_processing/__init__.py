from .file_type_detector import FileTypeDetector

# FileProcessor 延迟导入以避免循环依赖
def get_file_processor():
    from .file_processor import FileProcessor
    return FileProcessor

__all__ = ['FileTypeDetector', 'get_file_processor']
