"""
Módulo del motor OCR.
"""
from .engine import init_ocr, run_ocr
from .word_splitter import split_line_box_into_words, apply_word_splitting

__all__ = [
    'init_ocr',
    'run_ocr',
    'split_line_box_into_words',
    'apply_word_splitting',
]
