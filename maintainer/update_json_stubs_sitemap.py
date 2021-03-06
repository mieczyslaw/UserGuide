# Adapted from mdtraj/devtools/travis-ci/update_versions_json.py,
# by Robert T McGibbon, under the LGPLv2.1 license
# Similarly by the terms of LGPL this is also in the public domain
# Lily Wang, 2020
#
# This script is called by deploy_docs_via_travis.sh to:
#  1. update versions.json
#  2. Write some redirect stubs
#  3. Write a sitemap.xml file for the root directory
#

import json
import os
import errno
import glob
import shutil
import textwrap
import xml.etree.ElementTree as ET

try:
    from urllib.request import Request, urlopen
except ImportError:
    from urllib2 import Request, urlopen

URL = os.environ['URL']
VERSION = os.environ['VERSION']


def get_web_file(filename, callback, default):
    url = os.path.join(URL, filename)
    try:
        page = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        data = urlopen(page).read().decode()
    except Exception as e:
        print(e)
        try:
            with open(filename, 'r') as f:
                return callback(f)
        except IOError as e:
            print(e)
            return default
    else:
        return callback(data)


# ========= WRITE HTML STUBS =========
# Add HTML files to redirect:
# index.html -> latest release
# latest/index.html -> latest release
# dev/index.html -> dev docs


def write_redirect(file, version='', outfile=None):
    if outfile is None:
        outfile = file
    url = os.path.join(URL, version, file)
    REDIRECT = textwrap.dedent(f"""
    <!DOCTYPE html>
    <meta charset="utf-8">
    <title>Redirecting to {url}</title>
    <meta http-equiv="refresh" content="0; URL={url}">
    <link rel="canonical" href="{url}">
    """)
    with open(outfile, 'w') as f:
        f.write(REDIRECT)


# ========= WRITE JSON =========
# Update $root/versions.json with links to the right version
versions = get_web_file('versions.json', json.loads, [])
existing = [item['version'] for item in versions]
already_exists = VERSION in existing

if not already_exists:
    latest = 'dev' not in VERSION
    if latest:
        for ver in versions:
            ver['latest'] = False

    versions.append({
        'version': VERSION,
        'display': VERSION,
        'url': os.path.join(URL, VERSION),
        'latest': latest
    })

with open("versions.json", 'w') as f:
    json.dump(versions, f, indent=2)

for ver in versions[::-1]:
    if ver['latest']:
        latest_version = ver['version']
        break
else:
    try:
        latest_version = versions[-1]['version']
    except IndexError:
        latest_version = None

for ver in versions[::-1]:
    if 'dev' in ver['version']:
        dev_version = ver['version']
        break
else:
    try:
        dev_version = versions[-1]['version']
    except IndexError:
        dev_version = None

if latest_version:
    html_files = glob.glob(f'{latest_version}/**/*.html', recursive=True)
    for file in html_files:
        outfile = file.strip(f'{latest_version}/')
        dirname = os.path.dirname(outfile)
        if dirname and not os.path.exists(dirname):
            try:
                os.makedirs(dirname)
            except OSError as exc:
                if exc.errno != errno.EEXIST:
                    raise

        write_redirect(file, '', outfile)
    write_redirect('index.html', latest_version, 'latest/index.html')

if dev_version:
    write_redirect('index.html', dev_version, 'dev/index.html')

# ========= WRITE SUPER SITEMAP.XML =========
# make one big sitemap.xml
ET.register_namespace('xhtml', "http://www.w3.org/1999/xhtml")

# so we could make 1 big sitemap as commented
# below, but they must be max 50 MB / 50k URL.
# Yes, this is 100+ releases, but who knows when
# that'll happen and who'll look at this then?
# bigroot = ET.Element("urlset")
# bigroot.set("xmlns", "http://www.sitemaps.org/schemas/sitemap/0.9")
# for ver in versions:
#     tree = get_web_file(ver['version']+'/sitemap.xml', ET.fromstring,
#                         ET.fromstring(''))
#     root = tree.getroot()
#     bigroot.extend(root.getchildren())
# ET.ElementTree(bigroot).write('sitemap.xml',
#                               xml_declaration=True,
#                               encoding='utf-8',
#                               method="xml")

# so instead we make a sitemap of sitemaps.
bigroot = ET.Element("sitemapindex")
bigroot.set("xmlns", "http://www.sitemaps.org/schemas/sitemap/0.9")
for ver in versions:
    path = os.path.join(URL, '{}/sitemap.xml'.format(ver['version']))
    sitemap = ET.SubElement(bigroot, 'sitemap')
    ET.SubElement(sitemap, 'loc').text = path

ET.ElementTree(bigroot).write('sitemap_index.xml',
                              xml_declaration=True,
                              encoding='utf-8',
                              method="xml")
