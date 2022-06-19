from sutime import SUTime
import jpype
import datetime
import regex as re
from datetime import date,timedelta
from dateutil.rrule import rrule, DAILY
from flask import Flask, request, jsonify
from flask_restful import Api, Resource, reqparse
from currency_extraction import *
from sutime_parse import *
"""
if jpype.isJVMStarted():
    sutime = SUTime(jars='/Users/.....', jvm_started=True, mark_time_ranges=False)
else:
    sutime = SUTime(jars='/Users/.........', jvm_started=False,mark_time_ranges=False)
"""

timecomp=get_aggregations_mappings("timecomparison.json")
currencycomp=get_aggregations_mappings("currencycomparision.json")

app = Flask(__name__)
api = Api(app)
app.debug = True
app.config['JSON_SORT_KEYS'] = False

@app.route("/")
def text2sql():
	if jpype.isJVMStarted():
		sutime = SUTime(jars='jars/', jvm_started=True, mark_time_ranges=False)
	else:
		sutime = SUTime(jars='jars/', jvm_started=False, mark_time_ranges=False)
	try:
		query= request.args['query']
	except:
		return "Welcome!! start typing your question as ip/?query=YOUR_QUESTION"

	results={"Query":query}
	results.update({"DateTime expression":get_time_expression(query,timecomp,sutime)})
	results.update({"Currency expression":get_result_currency(query,currencycomp)})

	return jsonify(results)

