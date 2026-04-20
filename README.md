## Project Overview:
Have you ever been in class but found it difficult to focus?

This project aims to analyze specifically environmental factors (factors outside the student’s control) that can influence a student's class performance. By collecting environmental data inside the classroom, personal condition data from students, and contextual information such as weather, the system will build a model to predict the average focus level of the students in the class. The initial goal is to understand which factors affect the focus of the student. The second goal is to predict class focus on the environment and provide insights into improving the class's environment and condition.

## Data Collection:
#### Primary Data Source(s):
Hardware Collection During class:
- **Noise Level:** Measured using a sound sensor (KY-038) to detect the level of noise inside the class room.
- **Temperature:** Measured using a temperature sensor to record the classroom temperature during the class.
- **Humidity:** Measured using a humidity sensor to track air moisture levels inside the class room.
- **Light Level:** Measured using a photoresistor/light sensor (KY-018) to capture lighting conditions in the classroom.
- **Measurement** Timestamp: Timestamp when the data collected.
- **Attendance:** Sensor in the door for entry and exit.

#### Secondary Data Source(s):
On Class Day:
- **Weather Conditions:** Retrieved from weather APIs to capture environmental conditions outside the classroom.

## Information Report:
Reports from collected information:
- Conditions outside the classroom.
- Conditions inside the classroom.
- What factors influence student focus in class?
- How do environmental conditions affect focus levels?

## Knowledge Prediction:
predictions before the class and during/on the class days from live data:

#### Prediction Outputs:
- Predicted class focus (confidence level of student performing well for the class)

## Data Collection Equipment:
- Kidbright32 v1.5i x2
- Sound Sensor (KY-038) x1
- Temperature & Humidity Sensor (KY-015) x1
- Light Sensor (KY-018) x1
- Laser diode x4

## Basic setup instructions:
Assume you already have a working GitHub account.
#### 0. Go to any directory/folder you want to contain the file

#### 1. Clone  this repository to your local machine
```
https://github.com/PannawitMahacharoensiri/Focus-O-Meter.git
```
#### 2. Create and activate a virtual environment (optional)   
You may replace **venv_name** with any name that follows standard naming conventions (e.g., snake_case or camelCase).

(Window) command prompt :
```
# Create python vitual environment (only for the first time) 
python -m venv venv_name
# Run vitual environment 
venv_name\Scripts\activate
```
 (Mac/Linux) Terminal :
```
python3 -m venv venv_name 
source venv_name/bin/activate
```

#### 3. Install dependencies
```
cd Focus-O-Meter
pip install -r requirements.txt
```

#### 4. Apply database migrations
```
python backend/manage.py migrate
```

#### 5. Create a file named ".env" save as type All files inside the backend directory.
This file is used to store database credentials securely. <br>
Replace values inside < > with your actual database information.
```
DB_NAME_WEATHER=<your_db_name>
DB_USER_WEATHER=<your_db_username>
DB_PASSWORD_WEATHER=<your_db_password>
DB_HOST_WEATHER=localhost # or your database host
DB_PORT_WEATHER=3306       # or your MySQL port

DB_NAME_ATTENDANCE=<your_db_name>
DB_USER_ATTENDANCE=<your_db_username>
DB_PASSWORD_ATTENDANCE=<your_db_password>
DB_HOST_ATTENDANCE=localhost # or your database host
DB_PORT_ATTENDANCE=3306	  # or your MySQL port
```
**Additional info:** <br>
- First database contains table: **inclass_weather**
- Second database contains tables: **project_inclass_attendance**, **tmd** <br>
Table structure is described here: [Database table structure](https://github.com/PannawitMahacharoensiri/Focus-O-Meter/wiki/Table-Structure)

#### 6. Run the development server (Backend)
in project root, run:
```
python backend/manage.py runserver
```
**Then you can open these links in your web browser:** <br>
Server : http://127.0.0.1:8000/ <br>
Swagger : http://127.0.0.1:8000/docs/#/

#### 7. Run the Python frontend (Streamlit)
Open a second terminal at project root and activate the virtual environment, then run:
```
streamlit run frontend/app.py
```

Then open in your browser:
- Frontend dashboard: http://localhost:8501/

Keep backend and frontend running at the same time during development.

## Frontend Features:

The Focus-O-Meter analytics dashboard is a Streamlit-based web application that visualizes and analyzes collected environmental and attendance data in real-time.

**Main Visualization Tabs:**
- **Weather**: Displays temperature trends, environmental metrics (humidity, light, sound), and average sound levels by classroom with interactive time-series charts.
- **Attendance**: Shows cumulative building occupancy over time (treating entry as +1, exit as -1), bucketed IN/OUT movement counts, and entry/exit distribution statistics.
- **TMD**: Visualizes external weather data (temperature, humidity, rainfall) and meteorological station locations on an interactive map.
- **Correlation**: Analyzes relationships between sound levels and attendance activity with Pearson correlation coefficient, trend lines, and scatter plots.

**Filter Controls:**
- **Classroom Filter**: Automatically detects available classrooms from loaded data and allows filtering by specific classrooms.
- **Classroom Filter Scope**: Choose between "Common weather+attendance" (only classes in both datasets) or "All discovered" (all available classes).
- **Date Range**: Quick presets (Today, Last 7 Days, This Month) or custom date range selection.
- **Row Limit**: Control the number of records fetched per dataset (100-200,000 rows).
- **Performance Tuning**: Adjust max plot points for performance with large datasets.

**Data Export:**
- Download filtered data as CSV for each dataset (weather, attendance, TMD, combined, or correlation).

**Performance Optimizations:**
- API response caching to avoid redundant fetches.
- Automatic plot downsampling for large datasets.
- Optional raw data table rendering to control memory usage.
- Handles large attendance datasets efficiently without freezing.

## Databases:
All project databases are hosted and can be accessed via phpMyAdmin at: https://iot.cpe.ku.ac.th/pma/<br>
For testing and offline use, exported database data is available in CSV format in the collected_data directory

## Project Document:
- Presentation Slide : [DAQ-Group12 Focus-O-Meter](https://drive.google.com/file/d/1jM-HEhIX9o8zzaxOKpJdUtUecSzskpmd/view?usp=sharing)
- Presentation Video : [DAQ Focus-O-Meter Brainwpower 20/04/2026](https://youtu.be/iC7yIKHfZf8?si=QnalV9oKkUfcxxQD)
