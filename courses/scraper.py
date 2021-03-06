#!/usr/bin/env python
"""
Python routines for scraping data from Princeton's registrar.
by Alex Ogier '13.

Kept limping along by Brian Kernighan, with bandaids every year
as the registrar makes format changes.

Additional modifications made by ReCourse team to suit ReCourse's needs

Further additional modification made by CourseComb team to suit CourseComb's needs

If run as a python script, the module will dump information on all the courses available
on the registrar website as a JSON format.

Check out LIST_URL to adjust what courses are scraped.

Useful functions are scrape_page() and scrape_all().
"""

from datetime import datetime
import json
import re
import string
import sqlite3
import sys
import urllib2
from BeautifulSoup import BeautifulSoup
from scrape_evals import course_eval

TERM_CODE = 1122  # seems to be fall 11-12
TERM_CODE = 1124  # so 1124 would be spring 11-12
TERM_CODE = 1134  # 1134 is definitely spring 13 (course offerings link)
TERM_CODE = 1142  # fall 2013; spring 2014 will be 1144
TERM_CODE = 1144  # spring 2014
TERM_CODE = 1154  # spring 2015
TERM_CODE = 1174  # spring 2017
TERM_CODE = 1182  # fall 2017, added by ReCourse
TERM_CODE = 1184  # spring 2018, added by CourseComb
TERM_CODE = 1192  # fall 2018, added by CourseComb

URL_PREFIX = "http://registrar.princeton.edu/course-offerings/"
LIST_URL = URL_PREFIX + "search_results.xml?term={term}"
COURSE_URL = URL_PREFIX + "course_details.xml?courseid={courseid}&term={term}"

# modified by ReCourse to remove duplicates for main course page
COURSE_LIST_REGEX = re.compile(r'course_details.xml\?courseid=(?P<id>\d+)')

# added by ReCourse to deal with different formatting on details course page
COURSE_DETAILS_REGEX = re.compile(r'courseid=(?P<id>\d+)')

PROF_URL_REGEX = re.compile(r'dirinfo\.xml\?uid=(?P<id>\d+)')

# changed by ReCourse to allow matching with weirder course numbers like CEE
# 262A (letter at end of number)
LISTING_REGEX = re.compile(r'(?P<dept>[A-Z]{3})\s+(?P<num>\d+[A-Z]?)')

def get_course_list(search_page):
  "Grep through the document for a list of course ids."
  soup = BeautifulSoup(search_page)
  soup.__str__(encoding='utf-8')
  links = soup('a', href=COURSE_LIST_REGEX)
  courseids = [COURSE_LIST_REGEX.search(a['href']).group('id') for a in links]
  return courseids

def clean(s):
  "Return a string with leading and trailing whitespace gone and all other whitespace condensed to a single space."
  return re.sub('\s+', ' ', s.strip())

# Modified by CourseComb to not scrape for unneeded descrip, prereqs
def get_course_details(soup):
  "Returns a dict of {courseid, area, title, descrip, prereqs}."

  area = clean(soup('strong')[1].findAllNext(text=True)[1])  # balanced on a pinhead
  if re.match(r'^\((LA|SA|HA|EM|EC|QR|STN|STL)\)$', area):
    area = area[1:-1]
  else:
    area = ''
  pdf_audit = clean(soup('em')[0].findAllNext(text=True)[0])  # copied from area - jz

  return {
    'courseid': COURSE_DETAILS_REGEX.search(soup.find('a', href=COURSE_DETAILS_REGEX)['href']).group('id'),
    'area': area, #bwk: this was wrong[1:-1],    # trim parens #  match.group(1) if match != None else ''
    'title': clean(soup('h2')[0].string),  # was [1]
    'pdfaudit': pdf_audit,
  }

def flatten(dd):
  s = ""
  try:
    for i in dd.contents:
      try:
        s += i
      except:
        s += flatten(i)
  except:
    s += "oh, dear"
  return s

def get_course_listings(soup):
  "Return a list of {dept, number} dicts under which the course is listed."
  listings = soup('strong')[1].string
  return [{'dept': match.group('dept'), 'number': match.group('num')} for match in LISTING_REGEX.finditer(listings)]

def get_single_class(row):
  "Helper function to turn table rows into class tuples."
  cells = row('td')
  time = cells[2].string.split("-")
  if len(time) != 2: # ReCourse -- allowed TBA classes to get scraped
    time = ["TBA", "TBA"]
  bldg_link = cells[4].strong.a

  # <td><strong>Enrolled:</strong>0
  # <strong> Limit:</strong>11</td>
  enroll = ''
  limit = ''
  if cells[5] != None:    # bwk
    enroll = cells[5].strong.nextSibling.string.strip()

    limit = cells[5].strong.nextSibling.nextSibling.nextSibling
    if limit != None:
      limit = limit.string.strip()
    else:
      limit = "0"
  days = 'TBA' # added TBA days for use in ReCourse
  if cells[3].strong.string != None:
    days = re.sub(r'\s+', '', cells[3].strong.string)
  return {
    'classnum': cells[0].strong.string,
    'section': cells[1].strong.string,
    'days': days,
    'starttime': time[0].strip(),
    'endtime': time[1].strip(),
    'bldg': bldg_link.string.strip(),
    'roomnum': bldg_link.nextSibling.string.replace('&nbsp;', ' ').strip(),
    'enroll': enroll, # bwk
    'limit': limit   #bwk
  }

def get_course_classes(soup):
  "Return a list of {classnum, days, starttime, endtime, bldg, roomnum} dicts for classes in this course."
  class_rows = soup('tr')[1:] # the first row is actually just column headings
  # This next bit tends to cause problems because the registrar includes precepts and canceled
  # classes. Having text in both 1st and 4th columns (class number and day of the week)
  # currently indicates a valid class.
  # ^Edit by Recourse squad: removed the 1st/4th reqs to get ALL classes,
  # even if TBA
  # return [get_single_class(row) for row in class_rows if row('td')[0].strong and row('td')[3].strong.string]
  return [get_single_class(row) for row in class_rows]

def get_url(courseid):
  return COURSE_URL.format(term=TERM_CODE, courseid=courseid)

def scrape_page(page, courseid):
  "Returns a dict containing as much course info as possible from the HTML contained in page."
  soup = BeautifulSoup(page, convertEntities=BeautifulSoup.HTML_ENTITIES).find('div', id='timetable') # was contentcontainer
  course = get_course_details(soup)
  course['listings'] = get_course_listings(soup)
  #course['profs'] = get_course_profs(soup)
  course['classes'] = get_course_classes(soup)

  # *** NEED TO CHANGE TO TAKE AVERAGE OF COURSE RATINGS **** 
  course['evaluation'] = course_eval(TERM_CODE, courseid)
  course['url'] = get_url(courseid)
  return course

def scrape_id(courseid):
  page = urllib2.urlopen(COURSE_URL.format(term=TERM_CODE, courseid=courseid))
  return scrape_page(page, courseid)

def scrape_all():
  """
  Return an iterator over all courses listed on the registrar's site.

  Which courses are retrieved are governed by the globals at the top of this module,
  most importantly LIST_URL and TERM_CODE.

  To be robust in case the registrar breaks a small subset of courses, we trap
  all exceptions and log them to stdout so that the rest of the program can continue.
  """
  search_page = urllib2.urlopen(LIST_URL.format(term=TERM_CODE))
  courseids = sorted(set(get_course_list(search_page)))

  n = 0
  for id in courseids:
    try:
      if n > 99999:
        return
      n += 1
      yield scrape_id(id)
    except Exception:
      import traceback
      traceback.print_exc(file=sys.stderr)
      sys.stderr.write('Error processing course id {0}\n'.format(id))

if __name__ == "__main__":
  first = True
  for course in scrape_all():
    if first:
      first = False
      print '['
    else:
      print ','
    json.dump(course, sys.stdout)
  print ']'
