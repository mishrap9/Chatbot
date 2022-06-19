#exec(open("sutime_parse.py").read())
from sutime import SUTime
import jpype
import datetime
import regex as re
from datetime import date,timedelta,datetime
from dateutil.rrule import rrule, DAILY
from flask import Flask, request, jsonify
from flask_restful import Api, Resource, reqparse

def parse_regex_date(qry):
	qry_replaced = {}
	month_dict = {"January":"01", "February":"02", "March":"03", "April": "04", "May":"05", "June":"06", "July":"07", "August":"08", "September":"09", "October":"10", "November":"11", "December":"12"}

	match=re.findall(r'[0-9]+[a-zA-Z]{3,10}[0-9]*',qry)
	for item in match:
		for month in month_dict.keys():
			if month.lower() in item.lower():
				start,end=[(m.start(0), m.end(0)) for m in re.finditer(month.lower(), item.lower())][0]
				new_item=item.replace(item[start:end]," "+month.lower()+" ")
				qry=qry.replace(item,new_item)
				qry_replaced[new_item]=item

	
	match = re.findall(r'(([0-9]{1,2}[a-z]{2})\sday\sof(\s[a-zA-Z0-9]+)(\s[0-9]{2,4})?)',qry)
	for item in match:
		string_tobe_replace,replace1,replace2,replace3 = item
		qry = qry.replace(string_tobe_replace, replace1+replace2+replace3)
		qry_replaced[replace1+replace2+replace3] = string_tobe_replace

	first_format_match = re.findall(r'\b(([0-9]{1}[a-z]*|[0-9]{2}[a-z]*)([-/\s]+)([0-9]{1,2}|[a-zA-Z]{3,10})\b[-/\s]*([0-9]{4}|[0-9]{2})*)\b', qry)
	second_format_match = re.findall(r'\b(([a-zA-Z]{3,10})\b([\s/-])([0-9]{1}[a-z]*|[0-9]{2}[a-z]*)\b[\s/-]*([0-9]{4}|[0-9]{2})*)\b', qry)
	date_replaced = {}

	if first_format_match != []:
		for match in first_format_match:
			date_to_replace, date_match, seperator, month_match, year_match = match
			day, month, year = get_date(date_match, month_match, year_match)
			new_qry = qry
			if month != None:
				new_date = year + "-" + month + "-" + day + " "
				new_qry = new_qry.replace(date_to_replace, new_date)
				date_replaced[new_date] = date_to_replace
			else:
				new_qry = qry
			qry = new_qry
	if second_format_match != []:
		for match in second_format_match:
			date_to_replace, month_match, seperator, date_match, year_match = match
			day, month, year = get_date(date_match, month_match, year_match)
			new_qry = qry
			if month != None:
				new_date = year + "-" + month + "-" + day + " "
				new_qry = new_qry.replace(date_to_replace, new_date)
				date_replaced[new_date] = date_to_replace
			else:
				new_qry = qry
			qry = new_qry
	else:
		new_qry = qry

	return(new_qry,date_replaced,qry_replaced)
    
def get_date(date_match, month_match, year_match):
    day_match = re.findall(r'[0-9]+', date_match)
    day = day_match[0]
    if len(day) == 1:
        day = "0" + day
    if len(year_match) == 0:
        year = "2018"
    elif len(year_match) == 2:
        year = "20" + year_match
    else:
        year = year_match    
    if len(month_match) >2:
        month = get_month(month_match)
    elif len(month_match) == 1:
        month = '0' + month_match
    elif len(month_match) == 2:
        month = month_match
    return day, month, year

def get_month(month_match):
    month_dict = {"Jan":"01", "Feb":"02", "Mar":"03", "Apr":"04", "May":"05", "Jun":"06", "Jul":"07", "Aug":"08", "Sep":"09", "Oct":"10", "Nov":"11", "Dec":"12", "January":"01", "February":"02", "March":"03", "April": "04", "May":"05", "June":"06", "July":"07", "August":"08", "September":"09", "October":"10", "November":"11", "December":"12"}
    for element in month_dict.keys():
        if element.lower() == month_match.lower():
            month = month_dict[element]
            return month
    return None

def parse_date(qry,timecomp,sutime):
	date_parsed=sutime.parse(qry)
	#print(date_parsed)
	parsed_results=[]
	for parsed_items in date_parsed:
		result={"Date": "", "String": "", "Operator": "","Probable Date":""}
		#print(parsed_items)
		result["Date"]=parsed_items['value'].replace("XXXX","2018")
		result["String"]=parsed_items['text']
		result["Operator"],type_op=get_op(parsed_items['text'],qry,timecomp)
		
		if "between "+parsed_items['text']+" and" in qry:
			qry=qry.replace("between "+parsed_items['text']+" and","between "+parsed_items['text']+" to")
		
		result["Probable Date"]=result["Date"]

		if is_weektype(result["Date"],result["String"]):
			result["Date"],probable_date=is_weektype(result["Date"],result["String"])
			result["Probable Date"]=probable_date

		if is_monthtype(result["Date"]):
			start_date,month_end=is_monthtype(result["Date"])
			result["Date"],probable_date=month_formatting(start_date,month_end,result["String"])
			result["Probable Date"]=probable_date

		result["Date"]=past_future(result["Date"])

		parsed_results.append(result)
	#print(parsed_results)
	return parsed_results

def clean_parse_date(parsed_results,date_replaced):
	for item in parsed_results:
		for isokey in date_replaced.keys():
			if isokey.strip() in item["String"]:
				item["String"]=re.sub(r'\b%s'%isokey.strip(),date_replaced[isokey].strip(),item["String"])
	return parsed_results

def getweekends(year,weekno):
	res=["",""]
	a,b=getweekrange(year, weekno)
	DayL = ['Mon','Tues','Wednes','Thurs','Fri','Satur','Sun']
	for dt in rrule(DAILY, dtstart=a, until=b):
		whichday=DayL[dt.weekday()] + 'day'
		if whichday=="Saturday":
			res[0]=dt.strftime("%Y-%m-%d")
		elif whichday=="Sunday":
			res[1]=dt.strftime("%Y-%m-%d")
	return res

def getweekrange(year, week,start,end):
    d = date(year,1,1)
    dlt = timedelta(days = (week-1)*7)
    return d + dlt+timedelta(days=start),  d + dlt + timedelta(days=end)

def is_weektype(text,string):
	week=re.findall("\d{4}-W[0-9]+",text)
	if(week):
		year=int(re.findall("\d{4}",text)[0])
		weekno=int(re.findall("W([0-9]+)",text)[0])
		weekend=re.findall("WE",text)
		
		if weekend:
		
			startdate,enddate=getweekrange(year, weekno,5,6)
		else:
			if "start" in string.lower() or "early" in string.lower():
				startdate,enddate=getweekrange(year, weekno,0,1)
				probable_date=startdate
			elif "end " in string.lower() or "late" in string.lower():
				startdate,enddate=getweekrange(year, weekno,5,6)
				probable_date=enddate
			elif "mid" in string.lower():
				startdate,enddate=getweekrange(year, weekno,2,4)
				probable_date=getweekrange(year, weekno,3,4)[0]
			else:
				startdate,enddate=getweekrange(year, weekno,0,6)
				probable_date=startdate

		startdate=startdate.strftime("%Y-%m-%d")
		enddate=enddate.strftime("%Y-%m-%d")
		probable_date=probable_date.strftime("%Y-%m-%d")
		return (startdate,enddate),probable_date
	return None

def is_monthtype(text):
	no_days = {}
	no_days.update(dict.fromkeys(['1', '3', '5','7','8','10','12'], 31))
	no_days.update(dict.fromkeys(['4', '6','9','11'],30))
	no_days.update(dict.fromkeys(['2'],28))
	try:
		dt=datetime.strptime(text,"%Y-%m")
		var=[str(dt.year),str(dt.month)]
		return(dt.strftime("%Y-%m-%d"),no_days[var[1]])
	except:
		return None

def month_formatting(start_date,month_end, found_string):
	date_add_dict = {'early': (0,9,0), 'start': (0,10,0), 'mid': (9,19,14), 'middle': (9,19,14), 'late':(19,month_end-1,month_end-1), 'end': (19,month_end-1,month_end-1)}
	date_1 = datetime.strptime(start_date, "%Y-%m-%d")
	flag=True
	for keyword in date_add_dict.keys():
		if keyword in found_string.lower():
			start, end, probable = date_add_dict[keyword] 
			start_date = date_1 + timedelta(days=start)
			end_date = date_1 + timedelta(days=end)
			probable_date = date_1 + timedelta(days=probable)
			flag=False
	if flag:	
		start_date = date_1 + timedelta(days=0)
		end_date = date_1 + timedelta(days=month_end-1)
		probable_date = date_1 + timedelta(days=0)
	return (start_date.strftime("%Y-%m-%d"),end_date.strftime("%Y-%m-%d")),past_future(probable_date.strftime("%Y-%m-%d"))
	
def get_datetime(date):
	types=['%Y','%Y-%m','%Y-%m-%d']
	for t in range(0,len(types)):
		try:
			dt=datetime.strptime(date, types[t])
			var=[str(dt.year),str(dt.month),str(dt.day)]
			break
		except:
			continue
	try:
		return dt
	except:
		return None

def past_future(dates):
	present=datetime.now()
	if isinstance(dates, tuple):
		startdate,enddate=dates
		if get_datetime(startdate) != None and get_datetime(enddate) != None:
			if get_datetime(startdate) < present and get_datetime(enddate) < present:
				return startdate.replace("2018","2019"), enddate.replace("2018","2019")
			else:
				return startdate, enddate
		else:
			return startdate, enddate
	else: 
		if get_datetime(dates) != None:
			if get_datetime(dates) < present:
				return dates.replace("2018","2019")
			else:
				return dates
		else:
				return dates

def get_op(text,qry,timecomp):
	default="=="
	type_op={">=":0,"<=":2,"==":1}
	for op in timecomp.keys():
		for prepo in timecomp[op]:
			if prepo+" "+text in qry:
				return (op,type_op[op])
				break
	return (default,type_op[default])

def modify_weeks(qry):
	week_dict = {'end of week':'end of this week', 'end of coming week':'end of next week', 'end of upcoming week':'end of next week', 'mid week': 'this mid week', 'coming week':'next week', 'upcoming week':'next week', 'start of week':'start of this week', 'after a week': 'next week', 'week after': 'next week'}
	all_matches = []
	week_replaced = {}
	for exist_phrase in week_dict.keys():
		matches = re.findall(r'\b%s\b'%exist_phrase, qry, re.IGNORECASE)
		if matches != []:
			all_matches = all_matches + matches
	for match in all_matches:
		new_qry = re.sub(r'\b%s\b'%match, week_dict[match.lower()], qry)
		if new_qry != qry:
			week_replaced[week_dict[match.lower()]] = match
		qry = new_qry	
	return(qry,week_replaced)

def get_aggregations_mappings(filename):
    with open(filename) as f:
        mappings = f.readlines()
    field_mappings = {}
    for mapping in mappings:
        mapping_tokens = mapping.split(':')
        mapping_synonyms = mapping_tokens[1].split(',')
        mapping_synonyms_clean = []
        for mapping_synonym in mapping_synonyms:
            mapping_synonyms_clean.append(mapping_synonym.replace('\n', '').strip())
        field_mappings[mapping_tokens[0].strip()] = mapping_synonyms_clean
    return field_mappings

def get_time_expression(qry,timecomp,sutime):
	qry,week_replaced=modify_weeks(qry)
	query,date_replaced,qry_replaced=parse_regex_date(qry)
	print(query)
	results=parse_date(query,timecomp,sutime)
	results=clean_parse_date(results,date_replaced)
	results=clean_parse_date(results,qry_replaced)
	results=clean_parse_date(results,week_replaced)
	return results

"""
if jpype.isJVMStarted():
	sutime = SUTime(jars='jars/', jvm_started=True, mark_time_ranges=False)
else:
	sutime = SUTime(jars='jars/', jvm_started=False, mark_time_ranges=False)

timecomp=get_aggregations_mappings("timecomparison.json")
"""
