import pandas as pd
import os


file_path = "/Users/sravan19/projects/Scraper_UI/University_Data/Programs/University-of-Findlay.csv"
df = pd.read_csv(file_path)

# Fill NaN values to avoid errors
df['Level'] = df['Level'].fillna('')
df['ProgramName'] = df['ProgramName'].fillna('')

# Create a boolean mask where Level is not empty
mask = df['Level'].str.strip() != ""

# Update ProgramName only for rows where Level is present
df.loc[mask, 'ProgramName'] = df.loc[mask, 'ProgramName'] + " - " + df.loc[mask, 'Level']

df['Level'] = ""

#csv name is UF.csv
df.to_csv("UniversityofFindlay.csv", index=False)
