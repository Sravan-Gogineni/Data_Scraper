import pandas as pd 
import pyodbc
import csv

database_url="Driver={ODBC Driver 18 for SQL Server};Server=tcp:s14.everleap.com;Initial Catalog=DB_9608_mygradqa;UID=DB_9608_mygradqa_user;PWD=Simple2Use@123;Integrated Security=False;TrustServerCertificate=yes;"

connection=pyodbc.connect(database_url)
cursor=connection.cursor()

#ingest the new program names from the cleaned csv file the program name will be replaced with the  CleanedProgramName
# we actually need to update not insert

with open("programs_collegeid_97_Cleaned.csv", "r") as f:
    reader = csv.reader(f)
    next(reader)  # skip header row: ProgramName, CollegeId, CleanedProgramName
    for row in reader:
        college_id = int(row[1])
        original_name = row[0]
        cleaned_name = row[2]
        cursor.execute(
            "UPDATE CollegePrograms SET ProgramName = ? WHERE CollegeId = ? AND ProgramName = ?",
            cleaned_name, college_id, original_name
        )

#commit the changes
connection.commit()

#close the connection
cursor.close()
connection.close()
    