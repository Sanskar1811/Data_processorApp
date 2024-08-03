import pandas as pd
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.conf import settings
from .models import UploadedFile
from .forms import UploadFileForm
import matplotlib.pyplot as plt
import io
import urllib, base64
import os

def upload_file(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('process_file')
    else:
        form = UploadFileForm()
    return render(request, 'data_processor/upload.html', {'form': form})

def process_file(request):
    try:
        # Load the latest uploaded file
        uploaded_file = UploadedFile.objects.latest('uploaded_at')
        file_path = uploaded_file.file.path

        # Load the master file (fixed file in the backend)
        master_file_path = os.path.join(settings.BASE_DIR, 'master.xlsx')
        master_mapping = pd.read_excel(master_file_path)

        # Load the input file
        input_df = pd.read_excel(file_path)

        # Apply the master mapping
        for _, row in master_mapping.iterrows():
            input_df.replace(row['insurer'], row['clubbed_name'], inplace=True)

        # Reshape and format the data
        reshaped_data = []
        for index, row in input_df.iterrows():
            clubbed_name = row[0]
            if pd.notna(clubbed_name):
                for column in input_df.columns[1:]:
                    if pd.notna(row[column]):
                        reshaped_data.append([2022, 'Jan', 'PVT', clubbed_name, row[column]])

        output_df = pd.DataFrame(reshaped_data, columns=['Year', 'Month', 'category', 'clubbed_name', 'Value'])

        # Save to Output.xlsx
        output_file_path = os.path.join(settings.MEDIA_ROOT, 'output', 'Output.xlsx')
        output_df.to_excel(output_file_path, index=False)

        # Generate a plot
        fig, ax = plt.subplots()
        output_df.groupby('clubbed_name')['Value'].sum().plot(kind='bar', ax=ax)
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        string = base64.b64encode(buf.read())
        uri = urllib.parse.quote(string)

        # Construct the URL for the output file
        output_file_url = settings.MEDIA_URL + 'output/Output.xlsx'

        return render(request, 'data_processor/result.html', {'output_file': output_file_url, 'plot': uri})
    
    except Exception as e:
        # Handle exceptions and provide useful feedback
        return HttpResponse(f"An error occurred: {str(e)}")
