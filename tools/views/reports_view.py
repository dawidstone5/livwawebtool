# import neccessary functions, libraries, and packages
from django.shortcuts import render
from django.http import HttpResponse
from docx import Document
from io import BytesIO
from reportlab.pdfgen import canvas
from django.contrib.auth.decorators import login_required

# __________________________________________________________________________________________________________REPORTS_VIEW____
@login_required
def reports(request):
    if request.user.is_authenticated:
        template_name = 'base_usr.html'
    else:
        template_name = 'base_all.html'

    if request.method == 'POST':
        # Get selected options from the form
        include_bias_correction = 'bias_correction' in request.POST
        include_water_levels = 'water_levels' in request.POST
        export_format = request.POST.get('export_format', 'pdf')

        # Generate the report content
        report_content = []
        if include_bias_correction:
            report_content.append("Bias Correction Analysis: Details about bias correction results.")
        if include_water_levels:
            report_content.append("Water Levels Prediction: Details about water level predictions.")

        # Export as Word document
        if export_format == 'word':
            document = Document()
            document.add_heading('Analysis Report', level=1)
            for section in report_content:
                document.add_paragraph(section)
            buffer = BytesIO()
            document.save(buffer)
            buffer.seek(0)
            response = HttpResponse(buffer, content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
            response['Content-Disposition'] = 'attachment; filename="analysis_report.docx"'
            return response

        # Export as PDF
        elif export_format == 'pdf':
            buffer = BytesIO()
            pdf = canvas.Canvas(buffer)
            pdf.setFont("Helvetica", 12)
            pdf.drawString(100, 800, "Analysis Report")
            y = 750
            for section in report_content:
                pdf.drawString(100, y, section)
                y -= 50
            pdf.save()
            buffer.seek(0)
            response = HttpResponse(buffer, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="analysis_report.pdf"'
            return response

    return render(request, 'tools/reports.html', {'template_name': template_name})
