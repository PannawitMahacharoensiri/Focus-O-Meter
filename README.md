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

#### 4. Run the development server
```
python manage.py runserver
```

**Then you can open these links in your web browser:** <br>
Server : http://127.0.0.1:8000/ <br>
Swagger : http://127.0.0.1:8000/docs/#/
