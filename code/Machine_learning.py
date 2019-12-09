'''This file is the main file to execute, You have to run on you laptop the local mysql database
first and change the variable working directory (witch will be the directory where all the output at csv format will be registered)
second change the 'sytem.path.append(YOURFOLDER)' with the location of the python files'''
from datetime import date
import os
import sys

import pymysql.cursors

sys.path.append('C:\\Users\cocol\Desktop\memoire\Jéjé_work\code')
from Mostimportantfeature import *

Working_Directory = "C:\\Users\cocol\Desktop\memoire\Jéjé_work"





''' This fuction handle the '1A2A3' fromat to usefull features for the machine learning algorithm and split the cell
    into a certain number of column equals to the number_of_diffrerent_responses to the question asked and fill the column
    with one if the patient answered yes to a given question and with 0 otherwise. For example if there is 6 possibilities of
    answers (0, 1, 2, 3, 4, 5) and the cells show '1A2A3' you will have a [ 0 1 1 1 0 0] for this row.
Input: Table: A table with a column containing the 1A2A3 format
       number_of_different_responses: the number of different possibility of answers to the question asked to the patient (ex: 8)
       STring: the string reffered to the column in 'Table' (ex: 'AcHw1')
Output : A dataframe where each row contains 0 or 1 corresponding to the respective '1A2A3' format of the imput'''


def AAunwrap(Table, number_of_diffrerent_responses, STring):
    cname = [STring + '$' + str(i) for i in list(range(0, number_of_diffrerent_responses))]
    nbrow = len(Table[Table.columns[0]])
    Temporarytbl = pd.DataFrame(np.zeros(shape=(nbrow, len(cname)), dtype=int), columns=cname)

    Temporarytbl['String'] = Table[STring]
    '''This fuction is used for speed up everinthing and work with the apply function below'''

    def fastfill(TAble):
        if TAble['String'] is not None and  pd.isna(TAble['String'])==False:
            # split the 1A2A3 fromat into [1 2 3]
            Lst = list(map(int, list(filter(None, TAble['String'].split('A')))))
            for t in range(len(Lst)):
                TAble[Lst[t]] = 1
        return TAble

    # Fill the table composed with only 0 with the corresponding ones with respect to the answers of the patient
    Temporarytbl = Temporarytbl.apply(fastfill, axis=1).drop(['String'], axis=1)

    return Temporarytbl





# mysql connection to the cloud
# connection = pymysql.connect(host='173.31.240.35.bc.googleusercontent.com', user='', password='',
#                             db='moveup_dwh', charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)

# mysql connection to the local database
connection = pymysql.connect(host='127.0.0.1', user='root', password='root',db='moveup_dwh', charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)

# mysql connection to the moveUp database
#connection = pymysql.connect(host='35.240.31.173', user='root', password='aKkidLJ45hdturo3',db='moveup_dwh', charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)

# Select the exercise_scheme table and patient_daily_data table to build one big table useful for the machine learning
# Each row is a patient at a given day
'''This function uses a sql statement and a connection to a database to return a dataframe according to the sql_statement'''


def read_from_sql_server(Connection, sql_statement):
    return pd.read_sql(sql_statement, Connection, index_col=None, coerce_float=True, params=None, parse_dates=None,
                       columns=None,
                       chunksize=None)


# Load all the useful dataframe
sql = "select * from exercise_scheme;"
exercise_scheme = read_from_sql_server(connection, sql)

sql = "select * from patient_daily_data;"
patient_daily_data = read_from_sql_server(connection, sql)

sql = "SELECT * FROM moveup_dwh.mapping_exercises;"
mapping_exercises = read_from_sql_server(connection, sql)

sql = "SELECT * FROM moveup_dwh.mapping_questionnaires;"
mapping_questionnaires = read_from_sql_server(connection, sql)
sql = "SELECT * FROM moveup_dwh.mapping_answers;"
mapping_answers = read_from_sql_server(connection, sql)

sql = "SELECT * FROM moveup_dwh.patients;"
patient_data = read_from_sql_server(connection, sql)

patient_data.rename(columns={'id': 'patient_id'}, inplace=True)
patient_dt = patient_data[['patient_id', 'age', 'gender', 'limb']]



'''This part of the code is aimed to merge the columns of exercises that are exaclty the same between hip and knee'''
''''The function merge_exo take as argument two exercises number from the tbl table and merge them so it works with the rest of the
code and store it in the table df without changing the name of the old columns'''
def merge_exo(ex1,ex2,df):
    dataframe = df.copy()
    strexo1 = str(ex1)+'_frequency'
    strexo2 = str(ex2) + '_frequency'
    df = dataframe[[strexo1,strexo2]]
    newcolumn = pd.DataFrame({str(ex1)+'+'+strexo2:df[strexo1].notna() | df[strexo2].notna()}).astype(float).replace(0, np.nan)

    if ex2==2010:
        #only update exo for heel raise hip because it impove bcr
        dataframe[strexo2] = newcolumn
    else :
        dataframe[strexo1] = newcolumn

        dataframe[strexo2] = newcolumn
    return dataframe

merge_exo_list = [[1001,2001],[1019,2008],[1012,2010],[1011,2009],[1002,1003]]

for i in merge_exo_list:
    exercise_scheme = merge_exo(i[0],i[1],exercise_scheme)



# Get the different columns name for each exercises: frequency, intensity and actual
exsh_column = list(exercise_scheme.columns)

# Merge all the dataframe to get one big table

patient_daily_data.rename(columns={'diff': 'day'}, inplace=True)


# Store a table with the exercises of the day before
exercise_scheme_of_the_day_before = exercise_scheme.copy()

cols = exercise_scheme_of_the_day_before.columns.drop(
    list(exercise_scheme_of_the_day_before.filter(regex='intensity')) + list(
        exercise_scheme_of_the_day_before.filter(regex='actual')))
exercise_scheme_of_the_day_before = exercise_scheme_of_the_day_before[cols]
exercise_scheme_of_the_day_before = exercise_scheme_of_the_day_before.apply(
    lambda x: x.notnull().astype(int) if "frequency" in x.name else x)

#I would like to go through all the columns in a dataframe and rename (or map) columns if they contain certain strings.
#https://stackoverflow.com/questions/32621677/pandas-rename-column-if-contains-string
exercise_scheme_of_the_day_before.columns = exercise_scheme_of_the_day_before.columns.str.replace('frequency', 'Activated_yesterday')

# Handle the fact that the programation of physio is made from data from the day before
patient_daily_data_of_the_day_before = patient_daily_data.copy()
patient_daily_data_of_the_day_before['day'] += 1
#Add the exercices mades the day before
exercise_scheme_of_the_day_before['day'] += 1
# merge a big table with every data we need
tbl = pd.merge(exercise_scheme, patient_daily_data_of_the_day_before, on=['patient_id', 'day'], how='left')
tbl = pd.merge(patient_dt, tbl, on=['patient_id'], how='right')
tbl = pd.merge(exercise_scheme_of_the_day_before, tbl, on=['patient_id', 'day'], how='right')





# removing patient operated before 1 november 2017, the 3 in the lines of code are because the tbl doesnt contain the day of the operation.
#tbl['date'] = pd.to_datetime(tbl['date'])

#names = tbl['patient_id'][(tbl['date'] <= '2017-11-3')]
#tbl = tbl.loc[~tbl['patient_id'].isin(names.values)]

# Get the different columns name for each exercises: frequency, intensity and actual
exsh_column = list(exercise_scheme.columns)
exsh_column.remove('day')
exsh_column.remove('patient_id')
# Get the number of row of the final frame
nrow = len(tbl[tbl.columns[0]])



# Select from the big talbe the data usefull for the machine learning and drop the labels and patient id
worktbl = tbl.drop(exsh_column, axis=1)




# That part i remove it now but i will add it later because there is an issue with the 1A2A3 format and i will treat ti
worktbl = worktbl.drop(['AcWh1', 'InDo1', 'MeAr1_other', 'MeAr2_other', 'ExWh3', 'WeWh2'], axis=1)

# Transform some columns to a useful format (from string to number)
worktbl["gender"].replace({'Female': 0, 'Male': 1}, inplace=True)
worktbl["MeAr2"].replace(-1.0, np.nan, inplace=True)

worktbl = pd.concat([worktbl.drop(['limb'], axis=1), pd.get_dummies(worktbl['limb'])], axis=1)



'''Preprocessing string with 1A2A3A fromat'''

'''This function add to the workTbl a feature form the Bigtbl under the 1A2A3 fromat under the shape of multiple
columns filled with 0 or 1
Input : String: The name of the column in the Bigtbl
        worktbl: The table in which the features are added
        Bigtbl: A talbe with 1A2A3 format columns
        number_of_diffrerent_responses: for the question String, several possible answers exist,
        number_of_diffrerent_responses is the number of possible answers
Output : the above worktbl modified
'''


def add_to_work(String, workTbl, Bigtbl, number_of_diffrerent_responses):
    if not os.path.isfile(Working_Directory + "\\filled_" + String + ".csv"):
        Newtbl = AAunwrap(Bigtbl, number_of_diffrerent_responses, String)
        Newtbl.to_csv(Working_Directory + "\\filled_" + String + ".csv")
    df1 = pd.read_csv(Working_Directory + "\\filled_" + String + ".csv")
    workTbl = pd.concat([workTbl, df1], axis=1, sort=False)
    return workTbl.drop(['Unnamed: 0'], axis=1)


# AcWh1 (what's activity did you do today)?
worktbl = add_to_work('AcWh1', worktbl, tbl, 14)

# InDo1 (Do you experience swelling in other places than the index joint?  )
worktbl = add_to_work('InDo1', worktbl, tbl, 6)

#  'ExWh3'Why didn't you do your exercises
worktbl = add_to_work('ExWh3', worktbl, tbl, 4)

# 'WeWh2' Why didn't you wear your band all day??
worktbl = add_to_work('WeWh2', worktbl, tbl, 3)

# Select all the columns containing frequency in the table with the different exercise as columns for the label
matching = [s for s in exsh_column if "frequency" in s]
matching.remove("9999_frequency")
# Fill the null values
worktbl = worktbl.fillna(method='bfill')
worktbl = worktbl.fillna(method='ffill')

worktbl['date'] = pd.to_datetime(worktbl['date'])
#Add the trend of the pain
'''this function return a table that can be concatenated with the worktbl and contain trend of information about continous variable 
as the pain, the 'threshold' is the significant level of difference you need to asses. The number of past day 1 is the numer of days on which you want to
compute the average, the same goes for number_of_past_days2. number_of_past_days1 need to be greater than number_of_past_days2'''
def add_trend_to_worktbl(Variable,threshold,number_of_past_days1,number_of_past_days2,Worktbl):

    if number_of_past_days1 < number_of_past_days2:
        Paintbl = Worktbl[['patientnumber','date','day',Variable]]

        df = Paintbl.groupby('patientnumber').apply(lambda x: x.set_index('date').resample('1D').first())

        df1 = df.groupby(level=0)[Variable].apply(lambda x: x.shift().rolling(min_periods=1,window=number_of_past_days1).mean()).reset_index(name=Variable +'_Average_Past_'+str(number_of_past_days1)+'_days')
        medged_tbl = pd.merge(Paintbl, df1, on=['date', 'patientnumber'], how='left')


        df2 = df.groupby(level=0)[Variable].apply(lambda x: x.shift().rolling(min_periods=1,window=number_of_past_days2).mean()).reset_index(name=Variable +'_Average_Past_'+str(number_of_past_days2)+'_days')
        medged_tbl = pd.merge(medged_tbl, df2, on=['date', 'patientnumber'], how='left')
        medged_tbl[str('Average_pain_increase_for_' + Variable+'and_'+str(number_of_past_days1)+'for_'+str(number_of_past_days2)+'previousdays')] = np.where(
                medged_tbl[Variable +'_Average_Past_'+str(number_of_past_days2)+'_days'] - medged_tbl[str(Variable +'_Average_Past_'+str(number_of_past_days1)+'_days')] < -threshold, 1, 0)

        medged_tbl[str('Average_pain_decrease_for_' + Variable+'and_'+str(number_of_past_days1)+'for_'+str(number_of_past_days2)+'previousdays')] = np.where(
            medged_tbl[Variable + '_Average_Past_' + str(number_of_past_days2) + '_days'] - medged_tbl[
                str(Variable + '_Average_Past_' + str(number_of_past_days1) + '_days')] > threshold, 1, 0)
        medged_tbl = medged_tbl.drop([Variable +'_Average_Past_'+str(number_of_past_days1)+'_days',Variable +'_Average_Past_'+str(number_of_past_days2)+'_days'], axis=1)
    else :
        medged_tbl =0
        print('Wrong order of pain average days (number_of_past_days 1 and 2)')
    return medged_tbl

thresh = 0
var = 'PaIn1'
trend_tbl = add_trend_to_worktbl(var,thresh,3,7,worktbl)
worktbl = pd.concat([worktbl, trend_tbl], axis=1)
worktbl = worktbl.loc[:,~worktbl.columns.duplicated()]
trend_tbl = add_trend_to_worktbl(var,thresh,2,5,worktbl)
worktbl = pd.concat([worktbl, trend_tbl], axis=1)
worktbl = worktbl.loc[:,~worktbl.columns.duplicated()]
trend_tbl = add_trend_to_worktbl(var,thresh,3,10,worktbl)
worktbl = pd.concat([worktbl, trend_tbl], axis=1)
worktbl = worktbl.loc[:,~worktbl.columns.duplicated()]

var = 'PaIn2'
trend_tbl = add_trend_to_worktbl(var,thresh,3,7,worktbl)
worktbl = pd.concat([worktbl, trend_tbl], axis=1)
worktbl = worktbl.loc[:,~worktbl.columns.duplicated()]
trend_tbl = add_trend_to_worktbl(var,thresh,2,5,worktbl)
worktbl = pd.concat([worktbl, trend_tbl], axis=1)
worktbl = worktbl.loc[:,~worktbl.columns.duplicated()]
trend_tbl = add_trend_to_worktbl(var,thresh,3,10,worktbl)
worktbl = pd.concat([worktbl, trend_tbl], axis=1)
worktbl = worktbl.loc[:,~worktbl.columns.duplicated()]







#Replace all names of columns in the worktbl by their full names:
code_names = list(worktbl.columns)

for ft in code_names:

    message = ''
    if find_dolar(ft):
        feature_code, answer = ft.split("$")
        index1 = find_index(feature_code, mapping_questionnaires, "question_code")
        if index1 > -1:
            message = message + " " + feature_code + ": " + mapping_questionnaires['question'][index1] + " "
            index2 = find_index(feature_code, mapping_answers, "question_code")
            if index2 > -1:
                positions = return_index(feature_code, mapping_answers, "question_code")
                ans = mapping_answers[['value_text', 'value_code']].iloc[positions]
                message = message + " ANSWER: " + ans[ans.value_code == int(answer)]['value_text'].values[0] + " "
                worktbl.rename(columns={ft: message},inplace=True)
            else :
                worktbl.rename(columns={ft: message},inplace=True)
        else:
            message = message + ft + " "
            worktbl.rename(columns={ft: message},inplace=True)

    else:
        index3 = find_index(ft, mapping_questionnaires, "question_code")
        if index3 > -1:
            message = message + " " + ft + ": " + mapping_questionnaires['question'][index3] + " "
            worktbl.rename(columns={ft: message},inplace=True)


# Build a worktbl (able to enter the machine learning algorithm) of patient in the group knee or in the group hip
worktbl['day'] = worktbl['day'].astype(int)

#load protocol and merge it with exercise shceme
protocoltbl_hip = pd.read_csv("C:\\Users\cocol\Desktop\memoire\Jéjé_work\comparativetbl\protocol\protocol_hip.csv")
protocoltbl_hip.rename(columns={"Days": "day"}, inplace=True)
protocoltbl_knee = pd.read_csv("C:\\Users\cocol\Desktop\memoire\Jéjé_work\comparativetbl\protocol\protocol_knee.csv")
protocoltbl_knee.rename(columns={"Days": "day"}, inplace=True)
prot_pt_tbl_hip = pd.merge(exercise_scheme, protocoltbl_hip, on=['day'], how='right')
prot_pt_tbl_knee = pd.merge(exercise_scheme, protocoltbl_knee, on=['day'], how='right')



def compare_protocol_PT(prot_pt_tbl,hip_or_knee):
    Returntbl = prot_pt_tbl[['patient_id','day']].copy()
    Returntbl['day'] = prot_pt_tbl['day']

    exexcise_list = [s for s in prot_pt_tbl.columns if s.isdigit()]
    for ex_number in exexcise_list:
        Returntbl['PT_Protocol_difference_'+hip_or_knee+'_' + ex_number] = (prot_pt_tbl[ex_number + "_frequency"].notnull().astype(int).to_frame()[ex_number + "_frequency"] - prot_pt_tbl[ex_number]).abs()

    return Returntbl

compare_protocol_PT_hip =compare_protocol_PT(prot_pt_tbl_hip,'Hip')
compare_protocol_PT_knee =compare_protocol_PT(prot_pt_tbl_knee,'Knee')

compare_protocol_PT_hip['day'] = compare_protocol_PT_hip['day']+1
compare_protocol_PT_knee['day'] = compare_protocol_PT_knee['day']+1

worktbl = pd.merge(worktbl, compare_protocol_PT_hip, on=['day','patient_id'], how='left')
# Fill the null values
worktbl = pd.merge(worktbl, compare_protocol_PT_knee, on=['day','patient_id'], how='left')
# Fill the null values
worktbl = worktbl.fillna(method='bfill')
worktbl = worktbl.fillna(method='ffill')
# ------------------------
# ------------------------
from crossvalidation import crossval

#Results_cv = crossval(matching, mapping_exercises, tbl, worktbl)
# save the Results
#
#Results_cv.to_csv(Working_Directory+"\cv\Results_cv_"+str(date.today())+".csv")

#Results = importfeature(matching,mapping_exercises,tbl,worktbl,mapping_questionnaires, mapping_answers)
# save the Results
#
#Results.to_csv(Working_Directory+"\mostimportantfeature\Results_with_previousdexo"+str(date.today())+".csv")

