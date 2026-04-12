# Frontend (Python)

This frontend is built with Streamlit and consumes the Django REST API from the backend.

## What this app does

- Loads weather, attendance, and TMD datasets into one analytics dashboard.
- Uses dataset-specific visualizations:
  - Weather: temperature/environment trends and average sound by class
  - Attendance: direction distribution, event timeline, count by class
  - TMD: external weather trends and location map (lat/lon)
- Adds cross-dataset correlation analysis:
  - Sound (`sound_adc`) vs attendance activity in time buckets
  - Pearson correlation score, trend plot, and scatter plot
- Applies classroom filter to every dataset that includes a `classroom` field.
- Supports optional date-range loading using `data_in_daterange`.
- Provides CSV downloads for:
  - filtered weather data
  - filtered attendance data
  - filtered TMD data
  - merged filtered datasets
  - correlation dataset

## Run steps

1. Start backend first:

```bash
cd backend
python manage.py runserver
```

2. In a second terminal, start frontend:

```bash
streamlit run frontend/app.py
```

3. Open the frontend URL shown by Streamlit (usually http://localhost:8501).

## Notes

- Default backend API base URL in UI: http://127.0.0.1:8000/api
- The sidebar has:
  - row limit
  - optional date range mode
  - quick date presets: Today, Last 7 Days, This Month, Custom
  - correlation time bucket control
  - a dashboard load button
- Classroom options are auto-detected from fetched data.
