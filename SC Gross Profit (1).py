#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Aug  3 12:41:13 2020

@author: prince
"""

#import data and remove duplicates

import pandas as pd
import numpy as np
import re
data = pd.read_csv('augsales.csv')

data = data[data['Year'] != 'Customer Total:']

def acc_num(row):
    if row['Year'] == 'Customer Number:':
        return  row['Prd.']
    else:
        return np.NaN

data['acc_num'] =  data.apply(lambda row: acc_num(row), axis = 1)   


def acc_name(row):
    if row['Year'] == 'Customer Number:':
        return row['Date']
    else:
        return np.NaN
        
    
data['Acc_name'] = data.apply(lambda row: acc_name(row), axis = 1)



def prod_name(row):
    if str(row['Year'])[3:4] == '/':
        return row['Prd.']
    else:
        return np.NaN
        
data['Product_name'] = data.apply(lambda row: prod_name(row), axis = 1)   


def prod_id(row):
    if str(row['Year'])[3:4] == '/':
        return row['Year']
    else: 
        return np.NaN
    
data['Product_num'] = data.apply(lambda row: prod_id(row), axis = 1)    
    

data.iloc[:, [-1,-2,-3,-4]] = data.iloc[:, [-1,-2,-3,-4]].fillna(method = 'ffill')

trial = data[data['Year'] == '2020']
trial = trial.drop(['Year', 'Prd.', 'Type', 'Cost of Sales', 'Percent'], axis = 1)




julysales = trial
julysales= julysales.drop_duplicates()
julyrates = pd.read_csv('Augrates.csv')
julyusd = pd.read_csv('Augusd.csv')

import re
cleaner = lambda k: float(re.sub(',','', str(k))) 


julysales[['Sales Amount', 'Sales Returns']] = julysales[['Sales Amount', 'Sales Returns']].applymap(cleaner)




julyrates['Date'] = julyrates['Date'].astype('datetime64[ns]')
julysales['Date'] = julysales['Date'].astype('datetime64[ns]')


julysales['Location'] =julysales['Location'].replace({'118ENT': 'RET118'})
julyusd['Location'] = julyusd['Location'].replace({'BYO': 'SCBYO'})

julyusd['Currency'] = 'USD'

serp = lambda i: str(i[7:]) if i[:2] == 'IN' else str(i[9:])

julysales['Transaction Number'] = julysales['Transaction Number'].map(serp)

julysales['Transaction Number'] = julysales['Transaction Number'].astype('int64')

julysales = pd.merge(julysales, julyusd, 
         how = 'left', 
         left_on = 'Transaction Number', right_on = 'Inv_num')
         

julysales = julysales.drop_duplicates()

julysales = julysales.drop(['Date_y', 'Location_y', 'Acc_num', 'Inv_num'], axis = 'columns')


currency = lambda z: 'RTGS' if z != 'USD' else z
julysales['Currency'] = julysales['Currency'].map(currency)
julysales['Currency'] = julysales['Currency'].astype('category')


julysales = pd.merge(julysales, julyrates, how = 'left',
                    left_on = 'Date_x',
                    right_on = 'Date')


purecosts = pd.read_csv('puremastercost.csv')

julysales = pd.merge(julysales, purecosts, how = 'left',
                    left_on = 'Product_num',
                    right_on = 'Product_id')


julysales = julysales.drop_duplicates()

def profit(row):
    if row['Currency'] == 'USD':
        return row['usd'] / 1.145
    else:
        return row['Sales Amount'] / row['SCrate']
    
julysales['Income'] = 0    

julysales['Income'] = julysales.apply(lambda row: profit(row), axis = 1)        

grouped_inv = julysales['Sales Amount'].groupby(julysales['Transaction Number']).sum()



grouped_inv = pd.DataFrame(grouped_inv)



grouped_inv =  grouped_inv.rename(columns = {'Sales Amount': 'Totals'})


julysales = pd.merge(julysales, grouped_inv, 
                    how = 'left',
                    left_on = 'Transaction Number',
                    right_index = True)

julysales = julysales.drop(['Product_id'], axis = 1)

def productinc(a):
    if a['Currency'] == 'USD':
        return ((a['Sales Amount'] / a['Totals']) * a['Income'])
    else:
        return a['Income']
    
   
julysales['individual_income']   = 0  
julysales['individual_income'] = julysales.apply(lambda a: productinc(a), axis = 1)

def real_cost(row):
    if str(row['Product_num'])[:3] == 'LAB':
            row['real_COST'] = 0
            return row['real_COST']
        
    
julysales['real_COST'] = julysales.apply(lambda row: real_cost(row), axis = 1)

julysales['Gross Profit'] = julysales['individual_income'] - julysales['real_COST']
julysales = julysales.drop(['Totals', 'Date'], axis = 1)

julysales.individual_income.sum()

julysales.to_csv('julysalesfinal.csv', index = False)


