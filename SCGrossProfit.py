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
import seaborn as sns
import matplotlib.pylab as plt
data = pd.read_csv('novsales.csv')
from datetime import datetime

data = data[data['Year'] != 'Customer Total:']

def acc_num(row):                          
    if row['Year'] == 'Customer Number:':
        return  row['Prd.']
    else:
        return np.NaN

data['acc_num'] =  data.apply(lambda row: acc_num(row), axis = 1)    #sort


def acc_name(row):
    if row['Year'] == 'Customer Number:':
        return row['Date']
    else:
        return np.NaN
        
    
data['Acc_name'] = data.apply(lambda row: acc_name(row), axis = 1)  #sort



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
    
data['Product_num'] = data.apply(lambda row: prod_id(row), axis = 1)     #get product number
    

data.iloc[:, [-1,-2,-3,-4]] = data.iloc[:, [-1,-2,-3,-4]].fillna(method = 'ffill')  #forward fill na so we can filter by NA

trial = data[data['Year'] == '2020']
trial = trial.drop(['Year', 'Prd.', 'Type', 'Cost of Sales', 'Percent'], axis = 1)  #unncessary columns




novsales = trial
novsales= novsales.drop_duplicates()
novrates = pd.read_csv('novrates.csv')  #scrate
novusd = pd.read_csv('novusd.csv')   #usd transactions
purecosts = pd.read_csv('puremastercost.csv')  #product costs

purecosts = purecosts.drop_duplicates(['Product_id'], keep = 'last')   

import re
cleaner = lambda k: float(re.sub(',','', str(k))) 


novsales[['Sales Amount', 'Sales Returns']] = novsales[['Sales Amount', 'Sales Returns']].applymap(cleaner) #clean SA and SR into same format





novrates['Date'] = pd.to_datetime(novrates['Date'],format = '%d/%m/%Y')   #parse Date into date format
novsales['Date'] = pd.to_datetime(novsales['Date'],format = '%d/%m/%Y')   #parse Date into date format


novsales['Location'] =novsales['Location'].replace({'118ENT': 'RET118'})  #rename retail location
novusd['Location'] = novusd['Location'].replace({'BYO': 'SCBYO'})   #rename Bulawayo location

novusd['Currency'] = 'USD'    

serp = lambda i: str(i[7:]) if i[:2] == 'IN' else str(i[9:]) # function to separate credit notes and invoices

novsales['Transaction Number'] = novsales['Transaction Number'].map(serp)

novsales['Transaction Number'] = novsales['Transaction Number'].astype('int64')


novusd = novusd.drop_duplicates(['Inv_num'])

novsales = pd.merge(novsales, novusd, 
         how = 'left', 
         left_on = 'Transaction Number', right_on = 'Inv_num')  #allsales with usd invoices
         

novsales = novsales.drop_duplicates()

novsales = novsales.drop(['Date_y', 'Location_y', 'Acc_num', 'Inv_num'], axis = 'columns') 


currency = lambda z: 'RTGS' if z != 'USD' else z
novsales['Currency'] = novsales['Currency'].map(currency)
novsales['Currency'] = novsales['Currency'].astype('category')


novsales = pd.merge(novsales, novrates, how = 'left',    #get novsales wtih respective rates of the day
                    left_on = 'Date_x',
                    right_on = 'Date')



novsales = pd.merge(novsales, purecosts, how = 'left',
                    left_on = 'Product_num',
                    right_on = 'Product_id')         #merge with product costs


novsales = novsales.drop_duplicates()

def profit(row):
    if row['Currency'] == 'USD':
        return row['usd'] / 1.145
    else:
        return row['Sales Amount'] / row['Scrate']      #get net income after value added tax (VAT)
    
novsales['Income'] = 0    

novsales['Income'] = novsales.apply(lambda row: profit(row), axis = 1)        

grouped_inv = novsales['Sales Amount'].groupby(novsales['Transaction Number']).sum()  #Usd invoices report the total amount for each product, hence,
#need actual amount for specific product

grouped_inv = pd.DataFrame(grouped_inv)


grouped_inv =  grouped_inv.rename(columns = {'Sales Amount': 'Totals'})


novsales = pd.merge(novsales, grouped_inv, 
                    how = 'left',
                    left_on = 'Transaction Number',
                    right_index = True)                      

novsales = novsales.drop(['Product_id'], axis = 1)

def productinc(a):
    if a['Currency'] == 'USD':
        return ((a['Sales Amount'] / a['Totals']) * a['Income'])
    else:
        return a['Income']
#novsales = novsales[novsales['Transaction Number'] != 121131  ]
   
novsales['individual_income']   = 0  
novsales['individual_income'] = novsales.apply(lambda a: productinc(a), axis = 1)

def real_cost(row):
    if str(row['Product_num'])[:3] == 'LAB':
            row['real_cost'] = 0
            return row['real_cost']
    else:
        return row['real_cost']                        #cost of labour = 0 (actual costs is salary)
        
def credit_loss(row):
    if len(str(row['Transaction Number'])) < 5:
        row['individual_income'] = (row['Sales Returns'] / row['Scrate']) * -1       
        return row['individual_income']
    else:
        return row['individual_income']                   #negative income for credit notes

novsales['individual_income'] = novsales.apply(lambda row: credit_loss(row), axis = 1)    
    
novsales['real_cost'] = novsales.apply(lambda row: real_cost(row), axis = 1)


novsales['Gross Profit'] = novsales['individual_income'] - novsales['real_cost']

def real_gp(row):
    if len(str(row['Transaction Number'])) < 5:
        row['Gross Profit'] = 0
        return row['Gross Profit']
    else:
        return row['Gross Profit']
    
novsales['Real_Gross_Profit'] = 0
novsales['Real_Gross_Profit'] = novsales.apply(lambda row: real_gp(row), axis = 1)


novsales = novsales.drop(['Totals', 'Date', 'Gross Profit'], axis = 1)


zero_q = lambda i: i.replace('', np.NaN)

novsales['Quantity'] = novsales['Quantity'].fillna(0)   

novsales = novsales[novsales['Quantity'] != 0]    #remove invoices with no qnty
                      
def vat(row):
    if row['Currency'] == 'USD':
        return (row['individual_income'] * 1.145) - row['individual_income']
    else:
        return (row['Sales Amount'] * 1.145) - row['Sales Amount']                          #calculate VAT
    
    
novsales['VAT'] = 0

novsales['VAT'] = novsales.apply(lambda row: vat(row), axis =1 )           
    

novsales.to_csv('novsalesfinal.csv', index = False)       

novsales.individual_income.sum()
novsales.Real_Gross_Profit.sum()

novsales.groupby('Currency')['individual_income'].sum().sort_values(ascending = False)    #income by currency

location = novsales.groupby('Location_x')['individual_income'].sum().sort_values(ascending = False).reset_index()  #sorted income by location


sns.stripplot(x = 'Location_x',y = 'individual_income', data = location,
              hue = 'Location_x')



sns.countplot(x = 'Location_x', data = novsales)    #number of transactions

novsales.groupby('Salesprsn')['individual_income'].sum().sort_values(ascending = False)


duplicates = novsales[novsales.duplicated()]

novsales.groupby('Location_x')['Real_Gross_Profit'].sum().sort_values(ascending = False)

no_cost = novsales[novsales['real_cost'].isnull()]
no_cost = pd.DataFrame(no_cost.groupby('Product_num')['real_cost'].size())
no_cost.to_csv('missingcosts.csv', index = True)                         #products without a cost, confirm with producurement for cost-price



day_income = novsales.groupby('Date_x')['individual_income'].sum().reset_index()   #Income by day


day_income.Date_x = day_income.Date_x.map(lambda i: i.strftime('%d'))


sns.set_style('darkgrid')
sns.lineplot(x = 'Date_x', y = 'individual_income',
            markers = True, 
            dashes = False, data = day_income)
plt.xticks(rotation = 45)


#PROFIT BY LOCATION
profit = novsales.groupby('Location_x')['Real_Gross_Profit'].sum().reset_index()





