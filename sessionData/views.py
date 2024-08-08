import os
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from .forms import UploadFileForm
from .models import UserSession, SessionData
from django.contrib.auth.decorators import login_required
from django.core.files.storage import FileSystemStorage
import logging
from datetime import datetime
from .tasks import process_session_data
import pandas as pd

logger = logging.getLogger(__name__)

project_path = os.path.dirname(os.path.abspath(__file__))

@login_required
def upload_session_data(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # Process the uploaded file
                uploaded_file = request.FILES['file']
                fs = FileSystemStorage()
                file_name = fs.save(uploaded_file.name, uploaded_file)
                file_path = fs.path(file_name) # fs.url(file_name)
                logger.info(f'File path: {file_path}')
                
                # For demonstration, setting the session start and stop times to the current time
                # In a real scenario, these would be determined based on the uploaded data
                session_start = datetime.now()
                session_stop = datetime.now()
                
                # Assuming user is logged in, create a new UserSession instance
                user_session = UserSession.objects.create(
                    user=request.user,
                    session_start=session_start,
                    session_stop=session_stop,
                    smartwatch_data_file_path=file_path
                )
                logger.info(f"File {file_name} uploaded successfully.")
                
                # Trigger the Celery task for processing the uploaded session data
                process_session_data.delay(user_session.id)
                
                return HttpResponseRedirect(reverse('session_upload_success'))  # Redirect to a new URL
            except Exception as e:
                logger.error("Error uploading file: %s", e, exc_info=True)
                return render(request, 'sessionData/upload_error.html', {'error': str(e)})
    else:
        form = UploadFileForm()
    return render(request, 'sessionData/upload.html', {'form': form})

def upload_success(request):
    return render(request, 'sessionData/upload_success.html')

@login_required
def session_results(request, session_id):
    try:
        session_data = SessionData.objects.get(session__id=session_id, type='processed')
        
        data = pd.read_json(session_data.data, convert_dates=['Time'])
        data.index = data['Time']
        data = data.dropna()
        # Columns: Time, Latitude, Longitude, Altitude, Speed, Direction, Heart Rate, Distance Delta, Acceleration
        #print(data)
        # Assuming sessionData is an array of {lat, lng, intensity} objects

        data_for_map = data[['Latitude', 'Longitude', 'Speed']]
        data_for_map = data_for_map.rename(columns={'Latitude': 'lat', 'Longitude': 'lng', 'Speed': 'intensity'})
        data_for_map['intensity'] = data_for_map['intensity'] / data_for_map['intensity'].max() * 50
        data_for_map = data_for_map.to_dict(orient='records')

        return render(request, 'sessionData/session_results.html', {'session_data': data_for_map})
    except SessionData.DoesNotExist as e:
        logger.error("Session data not found for session_id {}: {}".format(session_id, e), exc_info=True)
        return HttpResponse("Session data not found.", status=404)