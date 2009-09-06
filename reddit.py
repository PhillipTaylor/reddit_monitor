#!/usr/bin/env python
#Reddit.py, a python lib capable of telling determining if you have a new reddit message.
#Written by Phillip (Philluminati) Taylor. Mail to: Phillip.Taylor@bcs.org.uk
#Licensed under the GNU General Public License version 3. Copies of the license can be found online.

import urllib
import urllib2
import os.path
import getopt
import getpass
import sys
import re
import simplejson
import datetime

REDDIT_USER_AGENT = { 'User-agent': 'Mozilla/4.0 (compatible; MSIE5.5; Windows NT' }
REDDIT_LOGIN_URL = 'http://www.reddit.com/api/login'
REDDIT_INBOX_PAGE = 'http://www.reddit.com/message/inbox/.json&mark=false'
REDDIT_PROFILE_PAGE = 'http://www.reddit.com/user/%s/about.json'

class RedditNotLoggedInException:
	pass

class Reddit:

	def __init__(self):

		#Because the login is an ajax post before we need cookies.
		#That's what made this code annoying to write.
		#This code should work against either cookielib or ClientCookie depending on
		#which ever one you have.
		try:
			import cookielib

			#Were taking references to functions / objects here
			#so later on we don't need to worry about which actual
			#import we used.
			self.Request = urllib2.Request
			self.urlopen = urllib2.urlopen

			cookie_jar = cookielib.LWPCookieJar()
			opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookie_jar))
			urllib2.install_opener(opener)

		except ImportError:
			try:
				import ClientCookie

				self.Request = ClientCookie.Request
				self.urlopen = ClientCookie.urlopen

				cookie_jar = ClientCookie.LWPCookieJar()
				opener = ClientCookie.build_opener(ClientCookie.HTTPCookieProcessor(cookie_jar))

			except ImportError:
				raise ImportError("""This code is dependent on either
						 \'cookielib\' or \'ClientCookie\'
						 #and you have neither.
						""")

		self.user = None

	def login(self, user, passwd):

		self.user = user

		params = urllib.urlencode({
			'id' : '#login_login-main',
			'op' : 'login-main',
			'passwd' : passwd,
			'user' : user
		})

		try:
			req = self.Request(REDDIT_LOGIN_URL, params, REDDIT_USER_AGENT)
			self.urlopen(req).read()
		except Exception, e:
			print "F*CK: %s", e.message
			return False

		return True

	#if user == None then it tells you your own karma (provided you called login())
	#Returns a tuple (karma, comment_karma)
	def get_karma(self, user=None):

		if user == None and not self.logged_in:
			raise RedditNotLoggedInException('Who is this? You haven\'t logged in')

		if user == None:
			user = self.user

		profile_page_to_fetch = REDDIT_PROFILE_PAGE % user

		try:
			req = self.Request(profile_page_to_fetch, None, REDDIT_USER_AGENT)
			json_data = self.urlopen(req).read()			

		except Exception, e:
			print 'Error is related to reading a profile page: %s', e.message
			raise e

		profile_info = simplejson.loads(json_data)

		karma         = profile_info['data']['link_karma']
		comment_karma = profile_info['data']['comment_karma']
		created       = datetime.datetime.fromtimestamp(profile_info['data']['created_utc'])
		days          = (datetime.datetime.now() - created).days

		return (karma, comment_karma, days)


	def get_new_mail(self):

		profile_page_to_fetch = REDDIT_INBOX_PAGE

		try:
			req = self.Request(profile_page_to_fetch, None, REDDIT_USER_AGENT)
			json_data = self.urlopen(req).read()

		except Exception, e:
			print 'Error is related to reading inbox page: %s', e.message
			raise e

		try:
			inbox = simplejson.loads(json_data)
			msgs = inbox['data']['children']
			newmsgs = [msg['data'] for msg in msgs if msg['data']['new'] == True]

		except Exception, e:
			dump = open('.dump','w')
			dump.write(json_data)
			dump.close()
			raise Exception('Bad JSON returned')

		return newmsgs

def run():

	if len(sys.argv) < 2:
		usage()
		sys.exit(2)

	try:
		(options, arguments) = getopt.getopt(sys.argv[1:], 'm')
	except optget.GetoptError, e:
		print e.message
		usage()
		sys.exit(2)

	if len(arguments) == 0:
		print "Username is mandatory"
		usage()
		sys.exit(2)
	else:
		username = arguments[0]

	Red = Reddit()

	if len(options) > 0: #must be the mail check option (because it's the only option)
		passwd = getpass.getpass('Your reddit password please: ')
		Red.login(username, passwd)
		print (len(Red.get_new_mail()) != 0)
	else:
		(karma, comment_karma, days) = Red.get_karma(username)
		print 'User %s has %s karma and %s comment karma. User for %s days' % (
			username,
			karma,
			comment_karma,
			days
		)
					

def usage():
	print """Usage: %s -m <reddit-username>\nTo see if you have
		 new mail use -m option. That operation requires a
		 password.""" % sys.argv[0]

if __name__=='__main__':
	run()
