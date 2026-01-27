"""
Módulo de manejo de PDFs.
"""
from .analyzer import detect_pdf_type
from .text_extractor import extract_native_text_with_boxes
from .image_extractor import extract_images_from_pdf
from .converter import pdf_to_scaled_images
from .generator import create_annotated_pdf, create_searchable_pdf, create_editable_pdf

__all__ = [
    'detect_pdf_type',
    'extract_native_text_with_boxes',
    'extract_images_from_pdf',
    'pdf_to_scaled_images',
    'create_annotated_pdf',
    'create_searchable_pdf',
    'create_editable_pdf',
]
