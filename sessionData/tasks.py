from celery import shared_task
from .models import UserSession, SessionData
from django.conf import settings
import logging
from .data_processor import ProcessSessionData

# wait function
import time

logger = logging.getLogger(__name__)

@shared_task
def process_session_data(session_id):
    # wait for 2 seconds for the file to be saved
    time.sleep(2)
    try:
        session = UserSession.objects.get(id=session_id)
        # Example of data refurbishing logic (to be expanded based on actual data structure)
        API_KEY = settings.OPENWEATHERMAP_API_KEY
        data_processor = ProcessSessionData(openweathermap_api_key=API_KEY)
        data_processor.read_tcx(session.smartwatch_data_file_path)

        raw_session_data = SessionData.objects.create(
            session=session,
            data=data_processor.data.to_json(),
            type='smartwatch_raw'
        )
        raw_session_data.save()

        session.session_start = data_processor.data.index[0]
        session.session_stop = data_processor.data.index[-1]

        data_processor.calculate_derivables()
        data_processor.smooth_data()
        data_processor.filter_outliers()
        #data_processor.append_weather()
        #data_processor.calculate_relative_surf_direction()

        processed_session_data = SessionData.objects.create(
            session=session,
            data=data_processor.data.to_json(),
            type='processed'
        )
        processed_session_data.save()


        session.save()
        logger.info(f"Session data processed for session {session_id}")
    except UserSession.DoesNotExist:
        logger.error(f"UserSession with id {session_id} does not exist.")
    except Exception as e:
        logger.error(f"Error processing session data for session {session_id}: {str(e)}", exc_info=True)