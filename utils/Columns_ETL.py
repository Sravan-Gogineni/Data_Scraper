import pandas as pd 
import pyodbc
import csv

database_url="Driver={ODBC Driver 18 for SQL Server};Server=tcp:s14.everleap.com;Initial Catalog=DB_9608_mygradqa;UID=DB_9608_mygradqa_user;PWD=Simple2Use@123;Integrated Security=False;TrustServerCertificate=yes;"

connection=pyodbc.connect(database_url)
cursor=connection.cursor()

#get all programs from Collegeprograms table the columns will be ProgramName with CollegeId =93
cursor.execute("SELECT ProgramName,CollegeId FROM CollegePrograms where CollegeId =97")

fetched_programs = cursor.fetchall()
#save in a csv file
with open("programs_collegeid_97.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["ProgramName", "CollegeId"])
    for row in fetched_programs:
        writer.writerow(row)

#close the connection
cursor.close()
connection.close()