"""
文档转换模块 - 支持 PDF/DOCX/PPT/TXT 转换为 Markdown
"""

import os
import re
import uuid
from pathlib import Path
from typing import Optional
from datetime import datetime

import aiofiles


class DocumentConverter:
    """文档格式转换器"""

    SUPPORTED_FORMATS = ['.pdf', '.docx', '.pptx', '.txt', '.md']

    def __init__(self, upload_dir: str = None):
        from gbrain.config import BASE_PATH
        if upload_dir is None:
            upload_dir = BASE_PATH / "data" / "uploads"
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    async def save_file(self, filename: str, content: bytes) -> Path:
        """保存上传文件"""
        file_path = self.upload_dir / filename
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        return file_path

    def convert_to_markdown(self, file_path: Path) -> str:
        """根据文件类型转换为 Markdown"""
        ext = file_path.suffix.lower()

        if ext == '.pdf':
            return self._convert_pdf_to_markdown(file_path)
        elif ext == '.docx':
            return self._convert_docx_to_markdown(file_path)
        elif ext == '.pptx':
            return self._convert_pptx_to_markdown(file_path)
        elif ext == '.txt':
            return self._convert_txt_to_markdown(file_path)
        elif ext == '.md':
            return self._convert_md_to_markdown(file_path)
        else:
            raise ValueError(f"不支持的文件格式: {ext}")

    def _convert_pdf_to_markdown(self, file_path: Path) -> str:
        """PDF 转 Markdown"""
        try:
            from pypdf import PdfReader
        except ImportError:
            # fallback: 直接读取文本
            with open(file_path, 'rb') as f:
                content = f.read()
                try:
                    return content.decode('utf-8')
                except:
                    return content.decode('gbk', errors='ignore')

        reader = PdfReader(str(file_path))
        markdown_parts = []

        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text.strip():
                markdown_parts.append(f"## 第 {i + 1} 页\n\n{text.strip()}")

        return "\n\n".join(markdown_parts)

    def _convert_docx_to_markdown(self, file_path: Path) -> str:
        """DOCX 转 Markdown"""
        from docx import Document

        doc = Document(str(file_path))
        markdown_parts = []

        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue

            # 根据样式判断标题级别
            style_name = para.style.name.lower() if para.style else ''
            if 'heading 1' in style_name or style_name == 'title':
                markdown_parts.append(f"# {text}")
            elif 'heading 2' in style_name:
                markdown_parts.append(f"## {text}")
            elif 'heading 3' in style_name:
                markdown_parts.append(f"### {text}")
            elif 'list' in style_name:
                markdown_parts.append(f"- {text}")
            else:
                markdown_parts.append(text)

        # 处理表格
        for table in doc.tables:
            table_text = []
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells]
                table_text.append("| " + " | ".join(cells) + " |")
            markdown_parts.append("\n".join(table_text))

        return "\n\n".join(markdown_parts)

    def _convert_pptx_to_markdown(self, file_path: Path) -> str:
        """PPTX 转 Markdown"""
        from pptx import Presentation

        prs = Presentation(str(file_path))
        markdown_parts = []

        for i, slide in enumerate(prs.slides):
            slide_title = ""
            slide_content = []

            # 获取标题
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    text = shape.text.strip()
                    if not text:
                        continue

                    if shape.has_text_frame:
                        # 判断是否是标题
                        if hasattr(shape, "is_placeholder") and shape.is_placeholder:
                            ph_type = str(shape.placeholder_format.type) if shape.placeholder_format else ""
                            if "TITLE" in ph_type or "CENTER_TITLE" in ph_type:
                                slide_title = f"## {text}\n"
                            else:
                                slide_content.append(text)
                        else:
                            slide_content.append(text)

            # 组合幻灯片内容
            if slide_title or slide_content:
                markdown_parts.append(f"## 幻灯片 {i + 1}\n")
                if slide_title:
                    markdown_parts.append(slide_title)
                if slide_content:
                    markdown_parts.append("\n".join(f"- {c}" for c in slide_content))
                markdown_parts.append("")

        return "\n".join(markdown_parts)

    def _convert_txt_to_markdown(self, file_path: Path) -> str:
        """TXT 转 Markdown（简单处理）"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 简单处理：保留段落结构
        paragraphs = content.split('\n\n')
        return '\n\n'.join(p.strip() for p in paragraphs if p.strip())

    def _convert_md_to_markdown(self, file_path: Path) -> str:
        """Markdown 文件直接读取"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()

    def extract_title_from_content(self, content: str) -> str:
        """从内容中提取标题"""
        # 尝试找到第一个标题
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('#'):
                # 去除 # 和空格
                return line.lstrip('#').strip()
        # 如果没有标题，使用前50个字符
        return content[:50].split('\n')[0].strip()


# 全局实例
_converter: Optional[DocumentConverter] = None


def get_document_converter() -> DocumentConverter:
    global _converter
    if _converter is None:
        _converter = DocumentConverter()
    return _converter
