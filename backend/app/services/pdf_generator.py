"""PDF Report Generation Service."""

import io
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ReportSection:
    """A section in the PDF report."""
    title: str
    content: str
    type: str = "text"  # text, code, table, chart
    metadata: Dict[str, Any] = None


class PDFReportGenerator:
    """
    Generate professional PDF reports from conversations.

    Uses reportlab for PDF generation (free, no API needed).
    Falls back to HTML if reportlab not available.
    """

    def __init__(self):
        self._reportlab_available = self._check_reportlab()

    def _check_reportlab(self) -> bool:
        """Check if reportlab is available."""
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate
            return True
        except ImportError:
            return False

    async def generate_conversation_report(
        self,
        messages: List[Dict],
        title: str = "IntelliStream Report",
        include_sources: bool = True,
        include_metadata: bool = True
    ) -> bytes:
        """
        Generate PDF report from conversation messages.

        Args:
            messages: List of conversation messages
            title: Report title
            include_sources: Include source citations
            include_metadata: Include timestamps and metadata

        Returns:
            PDF bytes
        """
        if self._reportlab_available:
            return await self._generate_with_reportlab(
                messages, title, include_sources, include_metadata
            )
        else:
            return await self._generate_html_pdf(
                messages, title, include_sources, include_metadata
            )

    async def _generate_with_reportlab(
        self,
        messages: List[Dict],
        title: str,
        include_sources: bool,
        include_metadata: bool
    ) -> bytes:
        """Generate PDF using reportlab."""
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib.colors import HexColor
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
            PageBreak, Image, HRFlowable
        )
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

        buffer = io.BytesIO()

        # Create document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )

        # Styles
        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=HexColor('#1a1a2e'),
            alignment=TA_CENTER
        )

        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Normal'],
            fontSize=12,
            textColor=HexColor('#666666'),
            alignment=TA_CENTER,
            spaceAfter=20
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=HexColor('#16213e'),
            spaceBefore=15,
            spaceAfter=10
        )

        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontSize=11,
            leading=16,
            textColor=HexColor('#333333'),
            alignment=TA_JUSTIFY
        )

        user_style = ParagraphStyle(
            'UserMessage',
            parent=body_style,
            backColor=HexColor('#e8f4f8'),
            borderPadding=10,
            spaceBefore=10,
            spaceAfter=10
        )

        assistant_style = ParagraphStyle(
            'AssistantMessage',
            parent=body_style,
            spaceBefore=5,
            spaceAfter=15
        )

        source_style = ParagraphStyle(
            'Source',
            parent=styles['Normal'],
            fontSize=9,
            textColor=HexColor('#666666'),
            leftIndent=20
        )

        # Build content
        story = []

        # Title
        story.append(Paragraph(title, title_style))

        # Subtitle with date
        date_str = datetime.now().strftime("%B %d, %Y at %H:%M")
        story.append(Paragraph(f"Generated on {date_str}", subtitle_style))

        # Horizontal line
        story.append(HRFlowable(
            width="100%",
            thickness=1,
            color=HexColor('#cccccc'),
            spaceBefore=10,
            spaceAfter=20
        ))

        # Conversation
        story.append(Paragraph("Conversation", heading_style))

        for i, msg in enumerate(messages):
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            sources = msg.get('sources', [])

            # Clean content for PDF
            content = self._clean_for_pdf(content)

            if role == 'user':
                story.append(Paragraph(f"<b>You:</b>", body_style))
                story.append(Paragraph(content, user_style))
            else:
                story.append(Paragraph(f"<b>Assistant:</b>", body_style))
                story.append(Paragraph(content, assistant_style))

                # Sources
                if include_sources and sources:
                    story.append(Paragraph("<b>Sources:</b>", source_style))
                    for source in sources[:5]:
                        source_title = source.get('title', 'Unknown')
                        source_url = source.get('url', '')
                        story.append(Paragraph(
                            f"• {source_title}" + (f" - {source_url}" if source_url else ""),
                            source_style
                        ))

            story.append(Spacer(1, 10))

        # Footer
        story.append(Spacer(1, 30))
        story.append(HRFlowable(
            width="100%",
            thickness=1,
            color=HexColor('#cccccc'),
            spaceBefore=10,
            spaceAfter=10
        ))

        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=9,
            textColor=HexColor('#999999'),
            alignment=TA_CENTER
        )
        story.append(Paragraph(
            "Generated by IntelliStream - Real-Time Agentic RAG Intelligence Platform",
            footer_style
        ))

        # Build PDF
        doc.build(story)

        pdf_bytes = buffer.getvalue()
        buffer.close()

        return pdf_bytes

    async def _generate_html_pdf(
        self,
        messages: List[Dict],
        title: str,
        include_sources: bool,
        include_metadata: bool
    ) -> bytes:
        """Generate HTML that can be converted to PDF (fallback)."""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{title}</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Arial, sans-serif;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 40px;
                    color: #333;
                    line-height: 1.6;
                }}
                h1 {{
                    color: #1a1a2e;
                    text-align: center;
                    border-bottom: 2px solid #4ECDC4;
                    padding-bottom: 20px;
                }}
                .subtitle {{
                    text-align: center;
                    color: #666;
                    margin-bottom: 30px;
                }}
                .message {{
                    margin: 20px 0;
                    padding: 15px;
                    border-radius: 8px;
                }}
                .user {{
                    background: #e8f4f8;
                    border-left: 4px solid #4ECDC4;
                }}
                .assistant {{
                    background: #f9f9f9;
                    border-left: 4px solid #45B7D1;
                }}
                .role {{
                    font-weight: bold;
                    margin-bottom: 10px;
                    color: #1a1a2e;
                }}
                .sources {{
                    font-size: 0.9em;
                    color: #666;
                    margin-top: 10px;
                    padding-top: 10px;
                    border-top: 1px solid #eee;
                }}
                .footer {{
                    margin-top: 40px;
                    text-align: center;
                    color: #999;
                    font-size: 0.9em;
                    border-top: 1px solid #eee;
                    padding-top: 20px;
                }}
            </style>
        </head>
        <body>
            <h1>{title}</h1>
            <div class="subtitle">Generated on {datetime.now().strftime("%B %d, %Y at %H:%M")}</div>
        """

        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '').replace('\n', '<br>')
            sources = msg.get('sources', [])

            role_class = 'user' if role == 'user' else 'assistant'
            role_label = 'You' if role == 'user' else 'Assistant'

            html += f"""
            <div class="message {role_class}">
                <div class="role">{role_label}</div>
                <div class="content">{content}</div>
            """

            if include_sources and sources and role == 'assistant':
                html += '<div class="sources"><strong>Sources:</strong><ul>'
                for source in sources[:5]:
                    source_title = source.get('title', 'Unknown')
                    html += f'<li>{source_title}</li>'
                html += '</ul></div>'

            html += '</div>'

        html += """
            <div class="footer">
                Generated by IntelliStream - Real-Time Agentic RAG Intelligence Platform
            </div>
        </body>
        </html>
        """

        return html.encode('utf-8')

    def _clean_for_pdf(self, text: str) -> str:
        """Clean text for PDF rendering."""
        # Replace markdown-style formatting
        import re

        # Bold
        text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
        # Italic
        text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
        # Code blocks - convert to monospace
        text = re.sub(r'```[\w]*\n(.+?)```', r'<font face="Courier">\1</font>', text, flags=re.DOTALL)
        # Inline code
        text = re.sub(r'`(.+?)`', r'<font face="Courier">\1</font>', text)
        # Links
        text = re.sub(r'\[(.+?)\]\((.+?)\)', r'\1 (\2)', text)
        # Headers
        text = re.sub(r'^#{1,6}\s+(.+)$', r'<b>\1</b>', text, flags=re.MULTILINE)
        # Line breaks
        text = text.replace('\n', '<br/>')

        return text

    async def generate_analysis_report(
        self,
        query: str,
        response: str,
        sources: List[Dict],
        agent_trace: List[Dict],
        knowledge_graph: Optional[Dict] = None
    ) -> bytes:
        """Generate a detailed analysis report."""
        messages = [
            {'role': 'user', 'content': query},
            {'role': 'assistant', 'content': response, 'sources': sources}
        ]

        return await self.generate_conversation_report(
            messages=messages,
            title=f"Analysis Report: {query[:50]}...",
            include_sources=True,
            include_metadata=True
        )


# Singleton instance
pdf_generator = PDFReportGenerator()
