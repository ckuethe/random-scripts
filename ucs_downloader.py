#!/usr/bin/env python
# vim: tabstop=4:softtabstop=4:shiftwidth=4:expandtab:

import sys
import os
import re
import io
import csv
import json
import requests
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
import logging
from dateutil.parser import parse as dp

def download_database(args):
    '''Download the most recent database from the Union of Concerned Scientists'''
    
    page = requests.get('http://www.ucsusa.org/nuclear-weapons/space-weapons/satellite-database', proxies=args.proxy).content
    dbfiles = re.findall(r'''(?:["'])(https?://s3.amazonaws.com/ucs-documents/nuclear-weapons/sat-database/.+?txt)(?:["'])''', page)

    for url in dbfiles:
        destfile = os.path.basename(url)
        if os.path.exists(destfile):
            print "{} is already downloaded".format(destfile)
            continue
        else:
            print url
            resp = requests.get(url, proxies=args.proxy)
            if resp.ok:
                with open(destfile, 'w') as fd:
                    fd.write(resp.content)
                
    return map(os.path.basename, dbfiles)

def get_sat_official_names(filename):
    '''UCS distributes two different versions of the database, one with official name and one with aliases
    
    Whyyyyyyyyyyyyyyyy?!

    Anyhoo, produce a map of COSPAR and NORAD numbers to the official name
    '''
    names = {'norad':{}, 'cospar':{}}
    with open(filename, 'r') as fd:
        rn_reader = csv.DictReader(fd, delimiter='\t')
        for row in rn_reader:
            cospar = row['COSPAR Number']
            norad = row['NORAD Number']    
            names['norad'][norad] = names['cospar'][cospar] = row['Current Official Name of Satellite']

    return names

def fix_names(row):
    ''''''
    name = row['Official Name']
    alias = row['Name of Satellite, Alternate Names'].replace(')', '').replace('(', ',').split(',')
    alias = map(lambda x: x.strip(), alias)
    return {'name':name, 'alias':alias}

def process_row(row, names):
    '''Convert the row to something more JSON friendly'''
    row.pop('', None) # due to the way the CSV is written, there is a blank trailing field
    
    # in case the number of sources changes
    sourcefields = filter(lambda x: x.startswith('source_'), row.keys())
    #Informational links
    sources = []
    for f in sourcefields:
        if len(row.get(f, '')):
            sources.append(row[f])
        row.pop(f, None)
    if len(row.get('Source', '')):
        sources.append(row['Source'])
        row.pop('Source', None)
    row['Sources'] = sources

    for k in row.keys():
        if row[k] == '':
            row[k] = None
    
    # Int conversions
    for i in ['Apogee (km)', 'NORAD Number', 'Perigee (km)', 'Power (watts)', 'Launch Mass (kg.)', 'Dry Mass (kg.)']:
        if row[i] == '':
            row[i] = None
        try:
            row[i] = int(row[i].replace(',', ''))
        except Exception:
            pass
    
    # Float conversions
    for f in ['Eccentricity', 'Longitude of GEO (degrees)', 'Inclination (degrees)', 'Period (minutes)', 'Power (watts)']:
        try:
            row[f] = float(row[f])
        except Exception:
            pass

    # Convert the somwhat ambiguous date to YYYY-MM-DD
    x = row['Date of Launch'].split('/')
    row['Date of Launch'] = '{}-{}-{}'.format(x[2], x[0], x[1])

    row['Official Name'] = names['cospar'][ row['COSPAR Number'] ]
    tmp = fix_names(row)
    row['Official Name'] = tmp['name']
    row['Alternate Names'] = tmp['alias']
    row.pop('Name of Satellite, Alternate Names', None)
    return row


def main():

    descr = 'Download the UCS database and convert it to JSON'
    parser = ArgumentParser(description=descr, formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument('-p', '--proxy', dest='proxy', metavar='URL', default=None, help='proxy, if necessary')
    parser.add_argument('-o', '--output', dest='output', metavar='FILENAME', default='ucs_database.json', help='name of output file')
    parser.add_argument('-n', '--nodownload', dest='nodownload', default='False', action='store_true', help='skip downloading the database')
    args = parser.parse_args()
    if args.proxy is None:
        args.proxy = {}

    # grab the latest database
    if args.nodownload is False:
        x = download_database(args)

    most_recent = filter(lambda x: x.startswith('UCS_Satellite_Database_officialname'), sorted(os.listdir('.'), reverse=True))[0]
    names = get_sat_official_names(most_recent)

    in_fd = open(most_recent.replace('_officialname', ''), 'r')
    reader = csv.DictReader(in_fd, delimiter='\t')

    # manipulate field names as necessary
    n = reader.fieldnames.index('Source Used for Orbital Data')
    for i in xrange(1,10):
        reader.fieldnames[n+i+1] = 'source_{}'.format(i)

# ------------------------------------------------------------------------------------

    sat_hash = {}
    sat_list = []
    for row in reader:
        try:
            x = process_row(row, names)
            sat_hash[x['COSPAR Number']] = x
            sat_list.append(x)
        except KeyError:
            pass

    in_fd.close()
# ------------------------------------------------------------------------------------

    with io.open(args.output, 'w', encoding='utf-8') as out_fd:
        out_fd.write(unicode(json.dumps(sat_list, encoding='latin-1', sort_keys=True, indent=4, separators=(',', ': '))))
    print "done"

if __name__ == '__main__':
    main()
