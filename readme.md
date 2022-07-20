To run:
1. enter the repo folder 'cd path/to/repo'
2. install all necessary packages 'pip install -r requirements.txt' (or use pip3)
3.Import dump into mysql through mysql workbench
    3a.Server->Data Import->Import from Self Contained File
    3b.Select dump.sql
	3c.Create new schema named "tanningscheduler". Select this Schema as Default Target schema  
    3d.Select dump structure Only
    3e.Click "Start Import"
4. open app.py using your favorite editor, change 'os.environ.get("api-token")' in 'app.config['MYSQL_DATABASE_PASSWORD'] = os.environ.get("api-token")' to your MySQL root password. You need to put quotations around your root password
5. back to the terminal, run the app 'python -m flask run' (or use python3)
6. open your browser, and open the local website 'localhost:5000'
