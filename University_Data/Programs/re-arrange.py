import pandas as pd  
import os

ug_file_path = "/home/sravan/Downloads/Data_Scraper/University_Data/Programs/undergraduate_programs/Undergrad_prog_outputs/undergraduate_programs_final.csv"
grad_file_path = "/home/sravan/Downloads/Data_Scraper/University_Data/Programs/graduate_programs/Grad_prog_outputs/graduate_programs_final.csv"

ug_df = pd.read_csv(ug_file_path)
grad_df = pd.read_csv(grad_file_path)

#merge the dataframes
merged_df = pd.concat([ug_df, grad_df], ignore_index=True)

#save the merged dataframe to a csv file
merged_df.to_csv("University_Data/Programs/merged_programs.csv", index=False)